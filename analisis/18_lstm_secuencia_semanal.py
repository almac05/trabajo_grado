"""LSTM con secuencia del dia previo y del mismo dia de la semana anterior.

La version anterior alimentaba la red unicamente con la jornada precedente.
Ese diseno presenta una carencia identificable: la jornada previa comparte
proximidad temporal con la objetivo pero no necesariamente su tipo de dia --el
lunes sucede al domingo, y sus niveles de demanda difieren en un factor de
cuatro-- mientras que la jornada de hace siete dias comparte tipo de dia y
perfil operativo. En el ensamble de arboles, el rezago semanal resulto la
variable de rezago mas relevante.

Esta version incorpora ambas secuencias como canales paralelos, alineados por
franja horaria: la posicion octava recibe simultaneamente la demanda de esa
franja el dia anterior y hace una semana.

Uso:
    python analisis/18_lstm_secuencia_semanal.py
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn

# ---------------------------------------------------------------
# 1. Configuracion
# ---------------------------------------------------------------

PARQUET = "data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
SALIDA = Path("analisis/salidas")

RUTAS = (1, 3)
TARGET = "pasajeros_total"

INICIO_TEST = pd.Timestamp("2026-04-02")
FIN_TEST = pd.Timestamp("2026-06-10")
SEMANAS_ENTRENAMIENTO = 52
PARADA_SEMANAS = 2
MIN_FRANJAS = 8

PASOS = 28
CALENDARIO = ["dia_semana", "es_fin_semana", "es_festivo",
              "dia_semana_sin", "dia_semana_cos"]

UNIDADES = 64
EPOCAS = 3000
PACIENCIA = 30
LR = 0.001
SEMILLA = 42

SUFIJO = f"semanal_{SEMANAS_ENTRENAMIENTO}s"

DISPOSITIVO = torch.device("cuda" if torch.cuda.is_available() else "cpu")
TIPOS_RAROS = ["FESTIVO", "FESTIVO_PUENTE"]

print(f"Dispositivo: {DISPOSITIVO}")

# ---------------------------------------------------------------
# 2. Construccion de secuencias
# ---------------------------------------------------------------


def secuencia_de(grupo: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Devuelve la demanda de una jornada y su mascara de posiciones validas.

    Las jornadas difieren en numero de franjas operativas. Se homogeneizan a
    longitud fija mediante relleno, y la mascara permite que la red distinga
    las posiciones rellenadas de las observadas.
    """
    valores = np.zeros(PASOS)
    mascara = np.zeros(PASOS)
    n = min(len(grupo), PASOS)
    valores[:n] = grupo[TARGET].to_numpy()[:n]
    mascara[:n] = 1.0
    return valores, mascara


def construir_ejemplos(datos: pd.DataFrame) -> tuple:
    """Empareja cada jornada con la previa y con la de hace siete dias.

    Se exige que ambas jornadas de referencia existan y tengan operacion
    suficiente; en caso contrario el ejemplo se descarta, dado que una
    secuencia ausente no puede sustituirse sin introducir informacion falsa.
    """
    por_dia = {dia: g for dia, g in datos.groupby("dia_op")}
    dias = sorted(por_dia)

    x_prev, m_prev, x_sem, m_sem, x_cal, y, y_msk = [], [], [], [], [], [], []

    for actual in dias:
        anterior = actual - pd.Timedelta(days=1)
        semana = actual - pd.Timedelta(days=7)

        if anterior not in por_dia or semana not in por_dia:
            continue

        curr = por_dia[actual]
        if (len(curr) < MIN_FRANJAS
                or len(por_dia[anterior]) < MIN_FRANJAS
                or len(por_dia[semana]) < MIN_FRANJAS):
            continue

        sp, mp = secuencia_de(por_dia[anterior])
        ss, ms = secuencia_de(por_dia[semana])
        obj, mo = secuencia_de(curr)

        x_prev.append(sp)
        m_prev.append(mp)
        x_sem.append(ss)
        m_sem.append(ms)
        x_cal.append(curr.iloc[0][CALENDARIO].to_numpy(dtype=float))
        y.append(obj)
        y_msk.append(mo)

    return (np.array(x_prev), np.array(m_prev), np.array(x_sem), np.array(m_sem),
            np.array(x_cal), np.array(y), np.array(y_msk))


# ---------------------------------------------------------------
# 3. Modelo
# ---------------------------------------------------------------


class RedLSTM(nn.Module):
    """Predice una jornada a partir de la previa y la de hace siete dias.

    Cada paso temporal aporta cuatro canales: demanda y mascara de la jornada
    previa, y demanda y mascara de la jornada de hace una semana. El estado
    final de la capa recurrente se concatena con las variables de calendario
    de la jornada objetivo, que la red no puede inferir de las series.
    """

    def __init__(self, n_calendario: int, unidades: int = UNIDADES):
        super().__init__()
        self.lstm = nn.LSTM(input_size=4, hidden_size=unidades, batch_first=True)
        self.salida = nn.Sequential(
            nn.Linear(unidades + n_calendario, unidades),
            nn.ReLU(),
            nn.Linear(unidades, PASOS),
        )

    def forward(self, prev, m_prev, sem, m_sem, cal):
        entrada = torch.stack([prev, m_prev, sem, m_sem], dim=-1)
        _, (estado, _) = self.lstm(entrada)
        return self.salida(torch.cat([estado[-1], cal], dim=1))


def perdida_enmascarada(pred, real, mascara):
    """Error absoluto medio sobre las posiciones observadas."""
    return (torch.abs(pred - real) * mascara).sum() / mascara.sum()


# ---------------------------------------------------------------
# 4. Evaluacion
# ---------------------------------------------------------------

df = pd.read_parquet(PARQUET)
resumen, predicciones = [], []
t_inicio = time.perf_counter()

for ruta in RUTAS:
    d = df[(df["FK_RUTA"] == ruta) & df[TARGET].notna()].copy()
    d = d.sort_values("timestamp").reset_index(drop=True)
    d["dia_op"] = (d["timestamp"] - pd.Timedelta(hours=4)).dt.date
    d["hora"] = d["timestamp"].dt.strftime("%H:%M")

    conteo = d.groupby("dia_op").size()
    dias = sorted(
        dia for dia, n in conteo.items()
        if INICIO_TEST.date() <= dia <= FIN_TEST.date() and n >= MIN_FRANJAS
    )

    print(f"\n{'=' * 60}")
    print(f"Ruta {ruta}: {len(dias)} jornadas")

    for i, dia in enumerate(dias, start=1):
        inicio_dia = pd.Timestamp(dia) + pd.Timedelta(hours=4)
        fin_dia = inicio_dia + pd.Timedelta(days=1)
        corte_parada = inicio_dia - pd.Timedelta(weeks=PARADA_SEMANAS)
        inicio_train = inicio_dia - pd.Timedelta(weeks=SEMANAS_ENTRENAMIENTO)

        ajuste = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < corte_parada)]
        parada = d[(d["timestamp"] >= corte_parada) & (d["timestamp"] < inicio_dia)]
        test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]

        if len(test) < MIN_FRANJAS:
            continue

        # Las dos jornadas de referencia deben existir para poder predecir.
        prev_g = d[d["dia_op"] == dia - pd.Timedelta(days=1)]
        sem_g = d[d["dia_op"] == dia - pd.Timedelta(days=7)]
        if len(prev_g) < MIN_FRANJAS or len(sem_g) < MIN_FRANJAS:
            print(f"  [{i:3d}/{len(dias)}] {dia}  falta jornada de referencia, se omite")
            continue

        ea = construir_ejemplos(ajuste)
        ep = construir_ejemplos(parada)

        if len(ea[5]) < 50 or len(ep[5]) < 3:
            print(f"  [{i:3d}/{len(dias)}] {dia}  ejemplos insuficientes, se omite")
            continue

        tipo = test["tipo_dia"].iloc[0]

        # El escalado se ajusta solo con datos de ajuste; emplear estadisticos
        # del periodo completo constituiria fuga de informacion.
        y_a, ym_a = ea[5], ea[6]
        media = y_a[ym_a == 1].mean()
        desv = y_a[ym_a == 1].std()

        def t(x, escalar=False):
            v = (x - media) / desv if escalar else x
            return torch.tensor(v, dtype=torch.float32, device=DISPOSITIVO)

        # Orden: prev, mascara prev, semanal, mascara semanal, calendario,
        # objetivo, mascara objetivo. Solo se escalan las series de demanda.
        ta = (t(ea[0], True), t(ea[1]), t(ea[2], True), t(ea[3]),
              t(ea[4]), t(ea[5], True), t(ea[6]))
        tp = (t(ep[0], True), t(ep[1]), t(ep[2], True), t(ep[3]),
              t(ep[4]), t(ep[5], True), t(ep[6]))

        torch.manual_seed(SEMILLA)
        modelo = RedLSTM(n_calendario=len(CALENDARIO)).to(DISPOSITIVO)
        optimizador = torch.optim.Adam(modelo.parameters(), lr=LR)

        t0 = time.perf_counter()
        mejor, sin_mejora, mejor_estado = float("inf"), 0, None

        for epoca in range(EPOCAS):
            modelo.train()
            optimizador.zero_grad()
            perdida_enmascarada(
                modelo(ta[0], ta[1], ta[2], ta[3], ta[4]), ta[5], ta[6]
            ).backward()
            optimizador.step()

            modelo.eval()
            with torch.no_grad():
                val = perdida_enmascarada(
                    modelo(tp[0], tp[1], tp[2], tp[3], tp[4]), tp[5], tp[6]
                ).item()

            if val < mejor:
                mejor, sin_mejora = val, 0
                mejor_estado = {k: v.clone() for k, v in modelo.state_dict().items()}
            else:
                sin_mejora += 1
                if sin_mejora >= PACIENCIA:
                    break

        segundos = time.perf_counter() - t0
        modelo.load_state_dict(mejor_estado)

        # --- Prediccion de la jornada objetivo ---
        seq_p, msk_p = secuencia_de(prev_g)
        seq_s, msk_s = secuencia_de(sem_g)
        cal = test.iloc[0][CALENDARIO].to_numpy(dtype=float)

        modelo.eval()
        with torch.no_grad():
            pred = modelo(
                t(seq_p[None, :], True), t(msk_p[None, :]),
                t(seq_s[None, :], True), t(msk_s[None, :]),
                t(cal[None, :]),
            ).cpu().numpy()[0] * desv + media

        n = min(len(test), PASOS)
        real = test[TARGET].to_numpy()[:n]
        pred = pred[:n]
        error = pred - real

        # --- Referencia: media historica por tipo de dia y franja ---
        entrenamiento = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]
        medias = entrenamiento.groupby(["tipo_dia", "hora"])[TARGET].mean()
        idx = pd.MultiIndex.from_arrays([test["tipo_dia"][:n], test["hora"][:n]])
        pred_media = medias.reindex(idx).to_numpy()
        n_sin = pd.isna(pred_media).sum()
        pred_media = pd.Series(pred_media).fillna(entrenamiento[TARGET].mean()).to_numpy()
        err_media = pred_media - real

        resumen.append({
            "route": ruta, "dia_op": dia, "tipo_dia": tipo, "n": n,
            "demanda_media": real.mean(),
            "mae_lstm": np.abs(error).mean(),
            "sesgo_lstm": error.mean(),
            "rango_pred_lstm": pred.max() - pred.min(),
            "rango_real": real.max() - real.min(),
            "mae_media": np.abs(err_media).mean(),
            "sesgo_media": err_media.mean(),
            "celdas_sin_media": int(n_sin),
            "epocas": epoca + 1,
            "ejemplos_ajuste": len(ea[5]),
            "segundos": segundos,
        })

        predicciones.append(pd.DataFrame({
            "route": ruta, "dia_op": dia, "tipo_dia": tipo,
            "hora": test["hora"].to_numpy()[:n], "real": real,
            "pred_lstm": pred, "pred_media": pred_media,
        }))

        print(f"  [{i:3d}/{len(dias)}] {dia} {tipo:14s} "
              f"MAE LSTM {np.abs(error).mean():6.2f} | "
              f"media {np.abs(err_media).mean():6.2f} | "
              f"{epoca + 1:4d} ep | {segundos:4.1f}s")

print(f"\nTiempo total: {(time.perf_counter() - t_inicio) / 60:.1f} min")

# ---------------------------------------------------------------
# 5. Resultados
# ---------------------------------------------------------------

r = pd.DataFrame(resumen)
p = pd.concat(predicciones, ignore_index=True)

SALIDA.mkdir(parents=True, exist_ok=True)
r.to_csv(SALIDA / f"lstm_{SUFIJO}.csv", index=False)
p.to_csv(SALIDA / f"lstm_predicciones_{SUFIJO}.csv", index=False)

print("\n" + "=" * 70)
print("RESUMEN POR RUTA")
print(
    r.groupby("route")
    .agg(
        jornadas=("dia_op", "count"),
        ejemplos=("ejemplos_ajuste", "mean"),
        demanda_media=("demanda_media", "mean"),
        mae_lstm=("mae_lstm", "mean"),
        sesgo_lstm=("sesgo_lstm", "mean"),
        mae_media=("mae_media", "mean"),
        sesgo_media=("sesgo_media", "mean"),
        epocas=("epocas", "mean"),
        segundos=("segundos", "mean"),
    )
    .round(2)
    .to_string()
)

print("\nPOR TIPO DE DIA")
print(
    r.groupby(["route", "tipo_dia"])
    .agg(
        jornadas=("dia_op", "count"),
        demanda_media=("demanda_media", "mean"),
        mae_lstm=("mae_lstm", "mean"),
        sesgo_lstm=("sesgo_lstm", "mean"),
        mae_media=("mae_media", "mean"),
    )
    .round(2)
    .to_string()
)

print("\nAMPLITUD DE LA PREDICCION FRENTE A LA OBSERVADA")
amp = r.groupby("route")[["rango_pred_lstm", "rango_real"]].mean().round(1)
amp["proporcion"] = (amp["rango_pred_lstm"] / amp["rango_real"]).round(3)
print(amp.to_string())

print(f"\nLSTM supera a la referencia en "
      f"{(r['mae_lstm'] < r['mae_media']).sum()} de {len(r)} jornadas")
print(f"\nDetalle guardado en {SALIDA} con sufijo '{SUFIJO}'")
