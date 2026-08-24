"""Compara el efecto del relleno en la LSTM sobre todo el periodo de prueba.

Se entrenan, para cada ruta y jornada, dos variantes bajo la misma particion
temporal, arquitectura base, hiperparametros y semilla:

* original: un canal de demanda y MAE sobre las 28 posiciones, incluidos ceros;
* enmascarada: demanda + indicador de validez y MAE solo sobre datos observados.

Uso:
    python analisis/21_lstm_comparacion_relleno.py
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
PASOS = 28
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


def secuencia_de(grupo: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    valores = np.zeros(PASOS, dtype=np.float32)
    mascara = np.zeros(PASOS, dtype=np.float32)
    n = min(len(grupo), PASOS)
    valores[:n] = grupo[TARGET].to_numpy()[:n]
    mascara[:n] = 1.0
    return valores, mascara


def construir_ejemplos(datos: pd.DataFrame) -> tuple[np.ndarray, ...]:
    dias = sorted(datos["dia_op"].unique())
    x_seq, x_msk, x_cal, y, y_msk = [], [], [], [], []

    for anterior, actual in pairwise(dias):
        if (pd.Timestamp(actual) - pd.Timestamp(anterior)).days != 1:
            continue
        prev = datos[datos["dia_op"] == anterior]
        curr = datos[datos["dia_op"] == actual]
        if len(prev) < MIN_FRANJAS or len(curr) < MIN_FRANJAS:
            continue

        seq, msk_seq = secuencia_de(prev)
        obj, msk_obj = secuencia_de(curr)
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
    def __init__(self, usar_mascara_entrada: bool):
        super().__init__()
        self.usar_mascara_entrada = usar_mascara_entrada
        canales = 2 if usar_mascara_entrada else 1
        self.lstm = nn.LSTM(canales, UNIDADES, batch_first=True)
        self.salida = nn.Sequential(
            nn.Linear(UNIDADES + len(CALENDARIO), UNIDADES),
            nn.ReLU(),
            nn.Linear(UNIDADES, PASOS),
        )

    def forward(self, seq, msk, cal):
        if self.usar_mascara_entrada:
            entrada = torch.stack([seq, msk], dim=-1)
        else:
            entrada = seq.unsqueeze(-1)
        _, (estado, _) = self.lstm(entrada)
        return self.salida(torch.cat([estado[-1], cal], dim=1))


def mae(pred, real, mascara=None):
    error = torch.abs(pred - real)
    if mascara is None:
        return error.mean()
    return (error * mascara).sum() / mascara.sum()


def entrenar(ta, tp, enmascarada: bool):
    torch.manual_seed(SEMILLA)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEMILLA)
    modelo = RedLSTM(usar_mascara_entrada=enmascarada).to(DISPOSITIVO)
    optimizador = torch.optim.Adam(modelo.parameters(), lr=LR)
    mascara_a = ta[4] if enmascarada else None
    mascara_p = tp[4] if enmascarada else None
    mejor, mejor_epoca, sin_mejora, mejor_estado = float("inf"), 0, 0, None
    inicio = time.perf_counter()

    for epoca in range(EPOCAS):
        modelo.train()
        optimizador.zero_grad()
        perdida = mae(modelo(ta[0], ta[1], ta[2]), ta[3], mascara_a)
        perdida.backward()
        optimizador.step()

        modelo.eval()
        with torch.no_grad():
            validacion = mae(
                modelo(tp[0], tp[1], tp[2]), tp[3], mascara_p
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


def diagnostico_parada(modelo, tp):
    modelo.eval()
    with torch.no_grad():
        errores = torch.abs(modelo(tp[0], tp[1], tp[2]) - tp[3])
    observada = tp[4].bool()
    relleno = ~observada
    suma_total = errores.sum().item()
    return {
        "mae_stop_observado_original": errores[observada].mean().item(),
        "mae_stop_relleno_original": errores[relleno].mean().item(),
        "aporte_relleno_loss_original": (
            errores[relleno].sum().item() / suma_total if suma_total else 0.0
        ),
    }


def tensorizar(ejemplos, media, desv):
    xs, xm, xc, y, ym = ejemplos

    def t(valor):
        return torch.tensor(valor, dtype=torch.float32, device=DISPOSITIVO)

    return t((xs - media) / desv), t(xm), t(xc), t((y - media) / desv), t(ym)


def predecir(modelo, seq, msk, cal, media, desv):
    modelo.eval()
    with torch.no_grad():
        pred = modelo(
            torch.tensor(((seq - media) / desv)[None, :], device=DISPOSITIVO),
            torch.tensor(msk[None, :], device=DISPOSITIVO),
            torch.tensor(cal[None, :], device=DISPOSITIVO),
        )
    return pred.cpu().numpy()[0] * desv + media


def main():
    print(f"Dispositivo: {DISPOSITIVO}")
    df = pd.read_parquet(PARQUET)
    resultados = []
    inicio_total = time.perf_counter()

    for ruta in RUTAS:
        d = df[(df["FK_RUTA"] == ruta) & df[TARGET].notna()].copy()
        d = d.sort_values("timestamp").reset_index(drop=True)
        d["dia_op"] = (d["timestamp"] - pd.Timedelta(hours=4)).dt.date
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
            ea, ep = construir_ejemplos(ajuste), construir_ejemplos(parada)
            if len(ea[3]) < 50 or len(ep[3]) < 3:
                continue
            prev = d[d["dia_op"] == dia - pd.Timedelta(days=1)]
            if len(prev) < MIN_FRANJAS:
                continue

            media = ea[3][ea[4] == 1].mean()
            desv = ea[3][ea[4] == 1].std()
            ta, tp = tensorizar(ea, media, desv), tensorizar(ep, media, desv)
            original = entrenar(ta, tp, enmascarada=False)
            corregido = entrenar(ta, tp, enmascarada=True)

            seq, msk = secuencia_de(prev)
            cal = test.iloc[0][CALENDARIO].to_numpy(dtype=np.float32)
            pred_o = predecir(original[0], seq, msk, cal, media, desv)
            pred_m = predecir(corregido[0], seq, msk, cal, media, desv)
            n = min(len(test), PASOS)
            real = test[TARGET].to_numpy()[:n]
            error_o, error_m = pred_o[:n] - real, pred_m[:n] - real
            diag = diagnostico_parada(original[0], tp)

            resultados.append({
                "route": ruta,
                "dia_op": dia,
                "tipo_dia": test["tipo_dia"].iloc[0],
                "n": n,
                "relleno_objetivo_ajuste_pct": 100 * (1 - ea[4].mean()),
                "relleno_objetivo_stop_pct": 100 * (1 - ep[4].mean()),
                "mae_original": np.abs(error_o).mean(),
                "mae_enmascarada": np.abs(error_m).mean(),
                "delta_mae": np.abs(error_o).mean() - np.abs(error_m).mean(),
                "sesgo_original": error_o.mean(),
                "sesgo_enmascarada": error_m.mean(),
                "epoca_mejor_original": original[1],
                "epoca_mejor_enmascarada": corregido[1],
                "epocas_original": original[2],
                "epocas_enmascarada": corregido[2],
                "segundos_original": original[3],
                "segundos_enmascarada": corregido[3],
                **diag,
            })
            print(
                f"  [{i:3d}/{len(dias)}] {dia} "
                f"original {np.abs(error_o).mean():6.2f} | "
                f"mascara {np.abs(error_m).mean():6.2f} | "
                f"delta {resultados[-1]['delta_mae']:+6.2f}"
            )

    salida = pd.DataFrame(resultados)
    SALIDA.mkdir(parents=True, exist_ok=True)
    detalle = SALIDA / "lstm_comparacion_relleno.csv"
    salida.to_csv(detalle, index=False)

    resumen = (
        salida.groupby("route")
        .apply(lambda g: pd.Series({
            "jornadas": len(g),
            "mae_original_ponderado": np.average(g["mae_original"], weights=g["n"]),
            "mae_enmascarada_ponderado": np.average(g["mae_enmascarada"], weights=g["n"]),
            "mejora_mae_pct": 100 * (
                1 - np.average(g["mae_enmascarada"], weights=g["n"])
                / np.average(g["mae_original"], weights=g["n"])
            ),
            "jornadas_gana_enmascarada": int((g["delta_mae"] > 0).sum()),
            "aporte_relleno_loss_original_pct": 100 * g["aporte_relleno_loss_original"].mean(),
        }), include_groups=False)
        .reset_index()
    )
    resumen.to_csv(SALIDA / "lstm_comparacion_relleno_resumen.csv", index=False)
    print("\nResumen por ruta:")
    print(resumen.to_string(index=False))
    print(f"\nTiempo total: {(time.perf_counter() - inicio_total) / 60:.1f} min")
    print(f"Detalle: {detalle}")


if __name__ == "__main__":
    main()
