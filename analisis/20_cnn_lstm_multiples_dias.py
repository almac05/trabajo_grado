"""Evaluacion del hibrido CNN-LSTM sobre el conjunto de prueba.

Ultimo de los modelos de aprendizaje profundo previstos en el anteproyecto.
Antepone una capa convolucional unidimensional a la recurrente: la convolucion
recorre la secuencia con una ventana de tres franjas --hora y media-- y produce
representaciones que resumen el comportamiento local (pendientes de subida,
mesetas, descensos), sobre las cuales opera despues la capa recurrente en lugar
de hacerlo sobre los valores individuales.

Se emplea el mismo protocolo que en los metodos anteriores: horizonte de una
jornada completa, ventana de cincuenta y dos semanas --la mejor configuracion
identificada para las arquitecturas recurrentes-- reentrenamiento diario y las
mismas jornadas de evaluacion.

Uso:
    python analisis/20_cnn_lstm_multiples_dias.py
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
FILTROS = 32          # canales de salida de la capa convolucional
NUCLEO = 3            # ventana de tres franjas: hora y media
EPOCAS = 3000
PACIENCIA = 30
LR = 0.001
SEMILLA = 42

DISPOSITIVO = torch.device("cuda" if torch.cuda.is_available() else "cpu")
TIPOS_RAROS = ["FESTIVO", "FESTIVO_PUENTE"]

print(f"Dispositivo: {DISPOSITIVO}")

# ---------------------------------------------------------------
# 2. Construccion de secuencias
# ---------------------------------------------------------------


def secuencia_de(grupo: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Devuelve la demanda de una jornada y su mascara de posiciones validas."""
    valores = np.zeros(PASOS)
    mascara = np.zeros(PASOS)
    n = min(len(grupo), PASOS)
    valores[:n] = grupo[TARGET].to_numpy()[:n]
    mascara[:n] = 1.0
    return valores, mascara


def construir_ejemplos(datos: pd.DataFrame) -> tuple:
    """Empareja cada jornada con la inmediatamente anterior.

    Solo se emparejan jornadas consecutivas: un salto en el calendario
    indicaria ausencia de operacion, y la secuencia dejaria de representar la
    jornada previa.
    """
    dias = sorted(datos["dia_op"].unique())
    x_seq, x_msk, x_cal, y, y_msk = [], [], [], [], []

    for anterior, actual in zip(dias[:-1], dias[1:], strict=False):
        if (pd.Timestamp(actual) - pd.Timestamp(anterior)).days != 1:
            continue

        prev = datos[datos["dia_op"] == anterior]
        curr = datos[datos["dia_op"] == actual]
        if len(prev) < MIN_FRANJAS or len(curr) < MIN_FRANJAS:
            continue

        s, ms = secuencia_de(prev)
        o, mo = secuencia_de(curr)

        x_seq.append(s)
        x_msk.append(ms)
        x_cal.append(curr.iloc[0][CALENDARIO].to_numpy(dtype=float))
        y.append(o)
        y_msk.append(mo)

    return (np.array(x_seq), np.array(x_msk), np.array(x_cal),
            np.array(y), np.array(y_msk))


# ---------------------------------------------------------------
# 3. Modelo
# ---------------------------------------------------------------


class RedCNNLSTM(nn.Module):
    """Convolucion unidimensional seguida de capa recurrente.

    La convolucion opera sobre los dos canales de entrada --demanda observada e
    indicador de posicion valida-- y produce FILTROS canales por paso temporal.
    El relleno conserva la longitud de la secuencia, de modo que la capa
    recurrente recibe los mismos PASOS con una representacion mas rica.
    """

    def __init__(self, n_calendario: int, unidades: int = UNIDADES,
                 filtros: int = FILTROS):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(in_channels=2, out_channels=filtros,
                      kernel_size=NUCLEO, padding=NUCLEO // 2),
            nn.ReLU(),
        )
        self.lstm = nn.LSTM(input_size=filtros, hidden_size=unidades,
                            batch_first=True)
        self.salida = nn.Sequential(
            nn.Linear(unidades + n_calendario, unidades),
            nn.ReLU(),
            nn.Linear(unidades, PASOS),
        )

    def forward(self, seq, msk, cal):
        # Conv1d espera (lote, canales, longitud); la capa recurrente espera
        # (lote, longitud, features), de ahi la transposicion intermedia.
        entrada = torch.stack([seq, msk], dim=1)
        rasgos = self.conv(entrada).transpose(1, 2)
        _, (estado, _) = self.lstm(rasgos)
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

        prev_g = d[d["dia_op"] == dia - pd.Timedelta(days=1)]
        if len(prev_g) < MIN_FRANJAS:
            print(f"  [{i:3d}/{len(dias)}] {dia}  sin jornada previa, se omite")
            continue

        xs_a, xm_a, xc_a, y_a, ym_a = construir_ejemplos(ajuste)
        xs_p, xm_p, xc_p, y_p, ym_p = construir_ejemplos(parada)

        if len(y_a) < 50 or len(y_p) < 3:
            print(f"  [{i:3d}/{len(dias)}] {dia}  ejemplos insuficientes, se omite")
            continue

        tipo = test["tipo_dia"].iloc[0]

        # El escalado se ajusta solo con datos de ajuste; emplear estadisticos
        # del periodo completo constituiria fuga de informacion.
        media = y_a[ym_a == 1].mean()
        desv = y_a[ym_a == 1].std()

        def t(x, escalar=False):
            v = (x - media) / desv if escalar else x
            return torch.tensor(v, dtype=torch.float32, device=DISPOSITIVO)

        torch.manual_seed(SEMILLA)
        modelo = RedCNNLSTM(n_calendario=len(CALENDARIO)).to(DISPOSITIVO)
        optimizador = torch.optim.Adam(modelo.parameters(), lr=LR)

        ta = (t(xs_a, True), t(xm_a), t(xc_a), t(y_a, True), t(ym_a))
        tp = (t(xs_p, True), t(xm_p), t(xc_p), t(y_p, True), t(ym_p))

        t0 = time.perf_counter()
        mejor, sin_mejora, mejor_estado = float("inf"), 0, None

        for epoca in range(EPOCAS):
            modelo.train()
            optimizador.zero_grad()
            perdida_enmascarada(modelo(ta[0], ta[1], ta[2]), ta[3], ta[4]).backward()
            optimizador.step()

            modelo.eval()
            with torch.no_grad():
                val = perdida_enmascarada(
                    modelo(tp[0], tp[1], tp[2]), tp[3], tp[4]
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
        seq, msk = secuencia_de(prev_g)
        cal = test.iloc[0][CALENDARIO].to_numpy(dtype=float)

        modelo.eval()
        with torch.no_grad():
            pred = modelo(
                t(seq[None, :], True), t(msk[None, :]), t(cal[None, :])
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
            "mae_cnn_lstm": np.abs(error).mean(),
            "sesgo_cnn_lstm": error.mean(),
            "rango_pred_cnn_lstm": pred.max() - pred.min(),
            "rango_real": real.max() - real.min(),
            "mae_media": np.abs(err_media).mean(),
            "sesgo_media": err_media.mean(),
            "celdas_sin_media": int(n_sin),
            "epocas": epoca + 1,
            "ejemplos_ajuste": len(y_a),
            "segundos": segundos,
        })

        predicciones.append(pd.DataFrame({
            "route": ruta, "dia_op": dia, "tipo_dia": tipo,
            "hora": test["hora"].to_numpy()[:n], "real": real,
            "pred_cnn_lstm": pred, "pred_media": pred_media,
        }))

        print(f"  [{i:3d}/{len(dias)}] {dia} {tipo:14s} "
              f"MAE CNN-LSTM {np.abs(error).mean():6.2f} | "
              f"media {np.abs(err_media).mean():6.2f} | "
              f"{epoca + 1:4d} ep | {segundos:4.1f}s")

print(f"\nTiempo total: {(time.perf_counter() - t_inicio) / 60:.1f} min")

# ---------------------------------------------------------------
# 5. Resultados
# ---------------------------------------------------------------

r = pd.DataFrame(resumen)
p = pd.concat(predicciones, ignore_index=True)

SALIDA.mkdir(parents=True, exist_ok=True)
r.to_csv(SALIDA / "cnn_lstm_multiples_dias.csv", index=False)
p.to_csv(SALIDA / "cnn_lstm_predicciones.csv", index=False)

print("\n" + "=" * 70)
print("RESUMEN POR RUTA")
print(
    r.groupby("route")
    .agg(
        jornadas=("dia_op", "count"),
        ejemplos=("ejemplos_ajuste", "mean"),
        demanda_media=("demanda_media", "mean"),
        mae_cnn_lstm=("mae_cnn_lstm", "mean"),
        sesgo_cnn_lstm=("sesgo_cnn_lstm", "mean"),
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
        mae_cnn_lstm=("mae_cnn_lstm", "mean"),
        sesgo_cnn_lstm=("sesgo_cnn_lstm", "mean"),
        mae_media=("mae_media", "mean"),
    )
    .round(2)
    .to_string()
)

print("\nAMPLITUD DE LA PREDICCION FRENTE A LA OBSERVADA")
amp = r.groupby("route")[["rango_pred_cnn_lstm", "rango_real"]].mean().round(1)
amp["proporcion"] = (amp["rango_pred_cnn_lstm"] / amp["rango_real"]).round(3)
print(amp.to_string())

print(f"\nCNN-LSTM supera a la referencia en "
      f"{(r['mae_cnn_lstm'] < r['mae_media']).sum()} de {len(r)} jornadas")
print(f"\nDetalle guardado en {SALIDA}")
