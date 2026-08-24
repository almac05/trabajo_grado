"""Evalua una LSTM con secuencias alineadas a una grilla horaria fija.

Compara el modelo ordinal enmascarado del analisis anterior con una variante
que conserva cada observacion en su franja real, representa explicitamente los
huecos e incorpora seno y coseno de la hora en cada paso recurrente.

Uso:
    python analisis/22_lstm_grilla_horaria.py
"""

import time
from copy import deepcopy
from itertools import pairwise
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn

PARQUET = "data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
SALIDA = Path("analisis/salidas")
RUTAS = (1, 3)
TARGET = "pasajeros_total"
INICIO_TEST = pd.Timestamp("2026-04-02")
FIN_TEST = pd.Timestamp("2026-06-10")
SEMANAS_ENTRENAMIENTO = 52
PARADA_SEMANAS = 2
MIN_FRANJAS = 8

PASOS_ORDINAL = 28
MINUTO_INICIO = 4 * 60
MINUTO_FIN = 18 * 60
MINUTOS_GRILLA = np.arange(MINUTO_INICIO, MINUTO_FIN + 1, 30)
PASOS_GRILLA = len(MINUTOS_GRILLA)
HORA_GRILLA = np.column_stack([
    np.sin(2 * np.pi * MINUTOS_GRILLA / (24 * 60)),
    np.cos(2 * np.pi * MINUTOS_GRILLA / (24 * 60)),
]).astype(np.float32)

CALENDARIO = [
    "dia_semana", "es_fin_semana", "es_festivo",
    "dia_semana_sin", "dia_semana_cos",
]
UNIDADES = 64
EPOCAS = 3000
PACIENCIA = 30
LR = 0.001
SEMILLA = 42
DISPOSITIVO = torch.device("cuda" if torch.cuda.is_available() else "cpu")

if torch.cuda.is_available():
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def secuencia_ordinal(grupo: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    valores = np.zeros(PASOS_ORDINAL, dtype=np.float32)
    mascara = np.zeros(PASOS_ORDINAL, dtype=np.float32)
    n = min(len(grupo), PASOS_ORDINAL)
    valores[:n] = grupo[TARGET].to_numpy()[:n]
    mascara[:n] = 1.0
    return valores, mascara


def secuencia_grilla(grupo: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Ubica cada valor en su franja real entre 04:00 y 18:00."""
    valores = np.zeros(PASOS_GRILLA, dtype=np.float32)
    mascara = np.zeros(PASOS_GRILLA, dtype=np.float32)
    minutos = grupo["timestamp"].dt.hour * 60 + grupo["timestamp"].dt.minute
    indices = ((minutos - MINUTO_INICIO) // 30).to_numpy(dtype=int)
    validos = (indices >= 0) & (indices < PASOS_GRILLA)
    indices = indices[validos]
    if len(np.unique(indices)) != len(indices):
        raise ValueError("Hay timestamps duplicados dentro de una jornada")
    valores[indices] = grupo.loc[validos, TARGET].to_numpy(dtype=np.float32)
    mascara[indices] = 1.0
    return valores, mascara


def construir_ejemplos(datos: pd.DataFrame, grilla: bool) -> tuple[np.ndarray, ...]:
    creador = secuencia_grilla if grilla else secuencia_ordinal
    dias = sorted(datos["dia_op"].unique())
    x_seq, x_msk, x_cal, y, y_msk = [], [], [], [], []

    for anterior, actual in pairwise(dias):
        if (pd.Timestamp(actual) - pd.Timestamp(anterior)).days != 1:
            continue
        prev = datos[datos["dia_op"] == anterior]
        curr = datos[datos["dia_op"] == actual]
        if len(prev) < MIN_FRANJAS or len(curr) < MIN_FRANJAS:
            continue
        seq, msk_seq = creador(prev)
        obj, msk_obj = creador(curr)
        x_seq.append(seq)
        x_msk.append(msk_seq)
        x_cal.append(curr.iloc[0][CALENDARIO].to_numpy(dtype=np.float32))
        y.append(obj)
        y_msk.append(msk_obj)

    return tuple(
        np.asarray(v, dtype=np.float32)
        for v in (x_seq, x_msk, x_cal, y, y_msk)
    )


class RedLSTM(nn.Module):
    def __init__(self, grilla: bool):
        super().__init__()
        self.grilla = grilla
        pasos = PASOS_GRILLA if grilla else PASOS_ORDINAL
        canales = 4 if grilla else 2
        self.lstm = nn.LSTM(canales, UNIDADES, batch_first=True)
        self.salida = nn.Sequential(
            nn.Linear(UNIDADES + len(CALENDARIO), UNIDADES),
            nn.ReLU(),
            nn.Linear(UNIDADES, pasos),
        )
        if grilla:
            self.register_buffer("hora_grilla", torch.tensor(HORA_GRILLA))

    def forward(self, seq, mascara, calendario):
        entrada = torch.stack([seq, mascara], dim=-1)
        if self.grilla:
            hora = self.hora_grilla.unsqueeze(0).expand(len(seq), -1, -1)
            entrada = torch.cat([entrada, hora], dim=-1)
        _, (estado, _) = self.lstm(entrada)
        return self.salida(torch.cat([estado[-1], calendario], dim=1))


def mae_enmascarado(pred, real, mascara):
    return (torch.abs(pred - real) * mascara).sum() / mascara.sum()


def tensorizar(ejemplos, media, desv, neutralizar_huecos: bool):
    xs, xm, xc, y, ym = ejemplos
    xs_escalada = (xs - media) / desv
    if neutralizar_huecos:
        xs_escalada = np.where(xm == 1, xs_escalada, 0.0)

    def t(valor):
        return torch.tensor(valor, dtype=torch.float32, device=DISPOSITIVO)

    return t(xs_escalada), t(xm), t(xc), t((y - media) / desv), t(ym)


def entrenar(ajuste, parada, grilla: bool):
    torch.manual_seed(SEMILLA)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEMILLA)
    modelo = RedLSTM(grilla).to(DISPOSITIVO)
    optimizador = torch.optim.Adam(modelo.parameters(), lr=LR)
    mejor, mejor_epoca, sin_mejora, mejor_estado = float("inf"), 0, 0, None
    inicio = time.perf_counter()

    for epoca in range(EPOCAS):
        modelo.train()
        optimizador.zero_grad()
        perdida = mae_enmascarado(
            modelo(ajuste[0], ajuste[1], ajuste[2]), ajuste[3], ajuste[4]
        )
        perdida.backward()
        optimizador.step()

        modelo.eval()
        with torch.no_grad():
            validacion = mae_enmascarado(
                modelo(parada[0], parada[1], parada[2]), parada[3], parada[4]
            ).item()
        if validacion < mejor:
            mejor = validacion
            mejor_epoca = epoca + 1
            sin_mejora = 0
            mejor_estado = deepcopy(modelo.state_dict())
        else:
            sin_mejora += 1
            if sin_mejora >= PACIENCIA:
                break

    modelo.load_state_dict(mejor_estado)
    return modelo, mejor_epoca, epoca + 1, time.perf_counter() - inicio


def predecir(modelo, seq, mascara, calendario, media, desv, grilla: bool):
    seq_escalada = (seq - media) / desv
    if grilla:
        seq_escalada = np.where(mascara == 1, seq_escalada, 0.0)
    modelo.eval()
    with torch.no_grad():
        pred = modelo(
            torch.tensor(seq_escalada[None, :], device=DISPOSITIVO),
            torch.tensor(mascara[None, :], device=DISPOSITIVO),
            torch.tensor(calendario[None, :], device=DISPOSITIVO),
        )
    return pred.cpu().numpy()[0] * desv + media


def resumen_ponderado(grupo: pd.DataFrame) -> pd.Series:
    mae_o = np.average(grupo["mae_ordinal"], weights=grupo["n"])
    mae_g = np.average(grupo["mae_grilla"], weights=grupo["n"])
    mae_m = np.average(grupo["mae_media"], weights=grupo["n"])
    return pd.Series({
        "jornadas": len(grupo),
        "observaciones": grupo["n"].sum(),
        "mae_ordinal": mae_o,
        "mae_grilla": mae_g,
        "mae_media": mae_m,
        "cambio_grilla_vs_ordinal_pct": 100 * (mae_g / mae_o - 1),
        "cambio_grilla_vs_media_pct": 100 * (mae_g / mae_m - 1),
        "jornadas_gana_grilla": int((grupo["delta_mae"] > 0).sum()),
    })


def main():
    print(f"Dispositivo: {DISPOSITIVO}")
    print(
        f"Grilla: {PASOS_GRILLA} pasos, "
        f"{MINUTO_INICIO // 60:02d}:00-{MINUTO_FIN // 60:02d}:00"
    )
    df = pd.read_parquet(PARQUET)
    resultados, predicciones = [], []
    inicio_total = time.perf_counter()

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
        print(f"\nRuta {ruta}: {len(dias)} jornadas")

        for i, dia in enumerate(dias, start=1):
            inicio_dia = pd.Timestamp(dia) + pd.Timedelta(hours=4)
            fin_dia = inicio_dia + pd.Timedelta(days=1)
            corte = inicio_dia - pd.Timedelta(weeks=PARADA_SEMANAS)
            inicio_train = inicio_dia - pd.Timedelta(weeks=SEMANAS_ENTRENAMIENTO)
            ajuste = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < corte)]
            parada = d[(d["timestamp"] >= corte) & (d["timestamp"] < inicio_dia)]
            test = d[(d["timestamp"] >= inicio_dia) & (d["timestamp"] < fin_dia)]
            eo_a = construir_ejemplos(ajuste, grilla=False)
            eo_p = construir_ejemplos(parada, grilla=False)
            eg_a = construir_ejemplos(ajuste, grilla=True)
            eg_p = construir_ejemplos(parada, grilla=True)
            if len(eo_a[3]) < 50 or len(eo_p[3]) < 3:
                continue
            prev = d[d["dia_op"] == dia - pd.Timedelta(days=1)]
            if len(prev) < MIN_FRANJAS:
                continue

            media = eg_a[3][eg_a[4] == 1].mean()
            desv = eg_a[3][eg_a[4] == 1].std()
            to_a = tensorizar(eo_a, media, desv, neutralizar_huecos=False)
            to_p = tensorizar(eo_p, media, desv, neutralizar_huecos=False)
            tg_a = tensorizar(eg_a, media, desv, neutralizar_huecos=True)
            tg_p = tensorizar(eg_p, media, desv, neutralizar_huecos=True)
            ordinal = entrenar(to_a, to_p, grilla=False)
            grilla = entrenar(tg_a, tg_p, grilla=True)

            seq_o, msk_o = secuencia_ordinal(prev)
            seq_g, msk_g = secuencia_grilla(prev)
            real_g, real_msk = secuencia_grilla(test)
            calendario = test.iloc[0][CALENDARIO].to_numpy(dtype=np.float32)
            pred_o = predecir(
                ordinal[0], seq_o, msk_o, calendario, media, desv, grilla=False
            )
            pred_g = predecir(
                grilla[0], seq_g, msk_g, calendario, media, desv, grilla=True
            )

            # El ordinal se evalua en el orden original; la grilla, en horas reales.
            n = min(len(test), PASOS_ORDINAL)
            real_o = test[TARGET].to_numpy()[:n]
            error_o = pred_o[:n] - real_o
            error_g = pred_g[real_msk == 1] - real_g[real_msk == 1]

            historico = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]
            medias = historico.groupby(["tipo_dia", "hora"])[TARGET].mean()
            indice = pd.MultiIndex.from_arrays([test["tipo_dia"], test["hora"]])
            pred_media = medias.reindex(indice).to_numpy()
            pred_media = pd.Series(pred_media).fillna(historico[TARGET].mean()).to_numpy()
            error_media = pred_media - test[TARGET].to_numpy()

            resultados.append({
                "route": ruta,
                "dia_op": dia,
                "tipo_dia": test["tipo_dia"].iloc[0],
                "n": len(error_g),
                "mae_ordinal": np.abs(error_o).mean(),
                "mae_grilla": np.abs(error_g).mean(),
                "mae_media": np.abs(error_media).mean(),
                "delta_mae": np.abs(error_o).mean() - np.abs(error_g).mean(),
                "sesgo_ordinal": error_o.mean(),
                "sesgo_grilla": error_g.mean(),
                "epoca_mejor_ordinal": ordinal[1],
                "epoca_mejor_grilla": grilla[1],
                "epocas_ordinal": ordinal[2],
                "epocas_grilla": grilla[2],
                "segundos_ordinal": ordinal[3],
                "segundos_grilla": grilla[3],
                "huecos_previos": int(PASOS_GRILLA - msk_g.sum()),
                "huecos_objetivo": int(PASOS_GRILLA - real_msk.sum()),
            })

            posiciones = np.flatnonzero(real_msk == 1)
            predicciones.append(pd.DataFrame({
                "route": ruta,
                "dia_op": dia,
                "tipo_dia": test["tipo_dia"].iloc[0],
                "hora": [f"{MINUTOS_GRILLA[j] // 60:02d}:{MINUTOS_GRILLA[j] % 60:02d}" for j in posiciones],
                "real": real_g[posiciones],
                "pred_grilla": pred_g[posiciones],
            }))
            print(
                f"  [{i:3d}/{len(dias)}] {dia} "
                f"ordinal {np.abs(error_o).mean():6.2f} | "
                f"grilla {np.abs(error_g).mean():6.2f} | "
                f"media {np.abs(error_media).mean():6.2f}"
            )

    detalle = pd.DataFrame(resultados)
    pred = pd.concat(predicciones, ignore_index=True)
    por_ruta = (
        detalle.groupby("route")
        .apply(resumen_ponderado, include_groups=False)
        .reset_index()
    )
    global_ = resumen_ponderado(detalle).to_frame().T
    global_.insert(0, "route", "GLOBAL")
    resumen = pd.concat([por_ruta, global_], ignore_index=True)

    SALIDA.mkdir(parents=True, exist_ok=True)
    detalle.to_csv(SALIDA / "lstm_grilla_horaria.csv", index=False)
    pred.to_csv(SALIDA / "lstm_grilla_horaria_predicciones.csv", index=False)
    resumen.to_csv(SALIDA / "lstm_grilla_horaria_resumen.csv", index=False)
    print("\nResumen:")
    print(resumen.to_string(index=False))
    print(f"\nTiempo total: {(time.perf_counter() - inicio_total) / 60:.1f} min")


if __name__ == "__main__":
    main()
