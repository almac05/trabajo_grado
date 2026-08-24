"""Evalua una LSTM con decodificador horario compartido y fallback festivo.

La demanda previa se codifica sobre la grilla fija de 04:00 a 18:00. En vez de
emitir 29 valores mediante neuronas de salida independientes, el decodificador
aplica la misma red a cada hora objetivo. Los festivos y festivos puente usan
como prediccion operativa la media historica por tipo de dia y hora, debido a
su escasa representacion en las ventanas de entrenamiento.

Uso:
    python analisis/23_lstm_decoder_compartido.py
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

MINUTO_INICIO = 4 * 60
MINUTO_FIN = 18 * 60
MINUTOS_GRILLA = np.arange(MINUTO_INICIO, MINUTO_FIN + 1, 30)
PASOS = len(MINUTOS_GRILLA)
HORA_GRILLA = np.column_stack([
    np.sin(2 * np.pi * MINUTOS_GRILLA / (24 * 60)),
    np.cos(2 * np.pi * MINUTOS_GRILLA / (24 * 60)),
]).astype(np.float32)

TIPOS_DIA = ["LABORAL", "SABADO", "DOMINGO", "FESTIVO", "FESTIVO_PUENTE"]
TIPOS_RAROS = {"FESTIVO", "FESTIVO_PUENTE"}
COLUMNAS_TIPO = [f"tipo_{tipo.lower()}" for tipo in TIPOS_DIA]
CALENDARIO = [
    "dia_semana", "es_fin_semana", "es_festivo",
    "dia_semana_sin", "dia_semana_cos", *COLUMNAS_TIPO,
]

UNIDADES = 64
UNIDADES_DECODER = 64
EPOCAS = 3000
PACIENCIA = 30
LR = 0.001
SEMILLA = 42
DISPOSITIVO = torch.device("cuda" if torch.cuda.is_available() else "cpu")

if torch.cuda.is_available():
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def secuencia_grilla(grupo: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    valores = np.zeros(PASOS, dtype=np.float32)
    mascara = np.zeros(PASOS, dtype=np.float32)
    minutos = grupo["timestamp"].dt.hour * 60 + grupo["timestamp"].dt.minute
    indices = ((minutos - MINUTO_INICIO) // 30).to_numpy(dtype=int)
    validos = (indices >= 0) & (indices < PASOS)
    indices = indices[validos]
    if len(np.unique(indices)) != len(indices):
        raise ValueError("Hay timestamps duplicados dentro de una jornada")
    valores[indices] = grupo.loc[validos, TARGET].to_numpy(dtype=np.float32)
    mascara[indices] = 1.0
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
        seq, msk_seq = secuencia_grilla(prev)
        obj, msk_obj = secuencia_grilla(curr)
        x_seq.append(seq)
        x_msk.append(msk_seq)
        x_cal.append(curr.iloc[0][CALENDARIO].to_numpy(dtype=np.float32))
        y.append(obj)
        y_msk.append(msk_obj)

    return tuple(
        np.asarray(v, dtype=np.float32)
        for v in (x_seq, x_msk, x_cal, y, y_msk)
    )


class RedLSTMDecoder(nn.Module):
    """Codifica la jornada previa y comparte el decoder entre todas las horas."""

    def __init__(self):
        super().__init__()
        self.codificador = nn.LSTM(4, UNIDADES, batch_first=True)
        self.decoder = nn.Sequential(
            nn.Linear(UNIDADES + len(CALENDARIO) + 2, UNIDADES_DECODER),
            nn.ReLU(),
            nn.Linear(UNIDADES_DECODER, 1),
        )
        self.register_buffer("hora_grilla", torch.tensor(HORA_GRILLA))

    def forward(self, seq, mascara, calendario):
        hora_entrada = self.hora_grilla.unsqueeze(0).expand(len(seq), -1, -1)
        entrada = torch.cat([
            torch.stack([seq, mascara], dim=-1),
            hora_entrada,
        ], dim=-1)
        _, (estado, _) = self.codificador(entrada)
        contexto = estado[-1].unsqueeze(1).expand(-1, PASOS, -1)
        cal = calendario.unsqueeze(1).expand(-1, PASOS, -1)
        entrada_decoder = torch.cat([contexto, cal, hora_entrada], dim=-1)
        return self.decoder(entrada_decoder).squeeze(-1)


def mae_equilibrado_por_jornada(pred, real, mascara):
    """Da el mismo peso a cada jornada, independientemente de su longitud."""
    error_dia = (torch.abs(pred - real) * mascara).sum(dim=1) / mascara.sum(dim=1)
    return error_dia.mean()


def tensorizar(ejemplos, media, desv):
    xs, xm, xc, y, ym = ejemplos
    xs_escalada = np.where(xm == 1, (xs - media) / desv, 0.0)

    def t(valor):
        return torch.tensor(valor, dtype=torch.float32, device=DISPOSITIVO)

    return t(xs_escalada), t(xm), t(xc), t((y - media) / desv), t(ym)


def entrenar(ajuste, parada):
    torch.manual_seed(SEMILLA)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEMILLA)
    modelo = RedLSTMDecoder().to(DISPOSITIVO)
    optimizador = torch.optim.Adam(modelo.parameters(), lr=LR)
    mejor, mejor_epoca, sin_mejora, mejor_estado = float("inf"), 0, 0, None
    inicio = time.perf_counter()

    for epoca in range(EPOCAS):
        modelo.train()
        optimizador.zero_grad()
        perdida = mae_equilibrado_por_jornada(
            modelo(ajuste[0], ajuste[1], ajuste[2]), ajuste[3], ajuste[4]
        )
        perdida.backward()
        optimizador.step()

        modelo.eval()
        with torch.no_grad():
            validacion = mae_equilibrado_por_jornada(
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


def predecir(modelo, seq, mascara, calendario, media, desv):
    seq_escalada = np.where(mascara == 1, (seq - media) / desv, 0.0)
    modelo.eval()
    with torch.no_grad():
        pred = modelo(
            torch.tensor(seq_escalada[None, :], device=DISPOSITIVO),
            torch.tensor(mascara[None, :], device=DISPOSITIVO),
            torch.tensor(calendario[None, :], device=DISPOSITIVO),
        )
    return pred.cpu().numpy()[0] * desv + media


def resumen_ponderado(grupo: pd.DataFrame) -> pd.Series:
    metricas = ["mae_densa", "mae_decoder", "mae_hibrido", "mae_media"]
    valores = {m: np.average(grupo[m], weights=grupo["n"]) for m in metricas}
    return pd.Series({
        "jornadas": len(grupo),
        "observaciones": grupo["n"].sum(),
        **valores,
        "decoder_vs_densa_pct": 100 * (
            valores["mae_decoder"] / valores["mae_densa"] - 1
        ),
        "hibrido_vs_densa_pct": 100 * (
            valores["mae_hibrido"] / valores["mae_densa"] - 1
        ),
        "hibrido_vs_media_pct": 100 * (
            valores["mae_hibrido"] / valores["mae_media"] - 1
        ),
        "jornadas_gana_decoder": int(
            (grupo["mae_decoder"] < grupo["mae_densa"]).sum()
        ),
        "jornadas_gana_hibrido": int(
            (grupo["mae_hibrido"] < grupo["mae_densa"]).sum()
        ),
    })


def main():
    print(f"Dispositivo: {DISPOSITIVO}")
    referencia_path = SALIDA / "lstm_grilla_horaria.csv"
    if not referencia_path.exists():
        raise FileNotFoundError(
            "Ejecute primero analisis/22_lstm_grilla_horaria.py"
        )
    referencia = pd.read_csv(referencia_path)
    referencia["dia_op"] = pd.to_datetime(referencia["dia_op"]).dt.date
    referencia = referencia[["route", "dia_op", "mae_grilla"]].rename(
        columns={"mae_grilla": "mae_densa"}
    )

    df = pd.read_parquet(PARQUET)
    resultados, predicciones = [], []
    inicio_total = time.perf_counter()

    for ruta in RUTAS:
        d = df[(df["FK_RUTA"] == ruta) & df[TARGET].notna()].copy()
        d = d.sort_values("timestamp").reset_index(drop=True)
        d["dia_op"] = (d["timestamp"] - pd.Timedelta(hours=4)).dt.date
        d["hora"] = d["timestamp"].dt.strftime("%H:%M")
        for tipo, columna in zip(TIPOS_DIA, COLUMNAS_TIPO, strict=True):
            d[columna] = (d["tipo_dia"] == tipo).astype(np.float32)
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
            modelo, mejor_epoca, epocas, segundos = entrenar(
                tensorizar(ea, media, desv), tensorizar(ep, media, desv)
            )
            seq, msk = secuencia_grilla(prev)
            real, msk_real = secuencia_grilla(test)
            calendario = test.iloc[0][CALENDARIO].to_numpy(dtype=np.float32)
            pred_decoder = predecir(modelo, seq, msk, calendario, media, desv)

            historico = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < inicio_dia)]
            medias = historico.groupby(["tipo_dia", "hora"])[TARGET].mean()
            indice = pd.MultiIndex.from_arrays([test["tipo_dia"], test["hora"]])
            pred_media_obs = medias.reindex(indice).to_numpy()
            pred_media_obs = (
                pd.Series(pred_media_obs)
                .fillna(historico[TARGET].mean())
                .to_numpy()
            )
            posiciones = np.flatnonzero(msk_real == 1)
            real_obs = real[posiciones]
            pred_decoder_obs = pred_decoder[posiciones]
            tipo = test["tipo_dia"].iloc[0]
            pred_hibrido = (
                pred_media_obs if tipo in TIPOS_RAROS else pred_decoder_obs
            )
            mae_decoder = np.abs(pred_decoder_obs - real_obs).mean()
            mae_hibrido = np.abs(pred_hibrido - real_obs).mean()
            mae_media = np.abs(pred_media_obs - real_obs).mean()
            mae_densa = referencia.loc[
                (referencia["route"] == ruta) & (referencia["dia_op"] == dia),
                "mae_densa",
            ].iloc[0]

            resultados.append({
                "route": ruta,
                "dia_op": dia,
                "tipo_dia": tipo,
                "n": len(real_obs),
                "mae_densa": mae_densa,
                "mae_decoder": mae_decoder,
                "mae_hibrido": mae_hibrido,
                "mae_media": mae_media,
                "sesgo_decoder": (pred_decoder_obs - real_obs).mean(),
                "sesgo_hibrido": (pred_hibrido - real_obs).mean(),
                "usa_fallback_festivo": tipo in TIPOS_RAROS,
                "epoca_mejor": mejor_epoca,
                "epocas": epocas,
                "segundos": segundos,
            })
            predicciones.append(pd.DataFrame({
                "route": ruta,
                "dia_op": dia,
                "tipo_dia": tipo,
                "hora": [
                    f"{MINUTOS_GRILLA[j] // 60:02d}:{MINUTOS_GRILLA[j] % 60:02d}"
                    for j in posiciones
                ],
                "real": real_obs,
                "pred_decoder": pred_decoder_obs,
                "pred_hibrido": pred_hibrido,
                "pred_media": pred_media_obs,
            }))
            print(
                f"  [{i:3d}/{len(dias)}] {dia} {tipo:14s} "
                f"densa {mae_densa:6.2f} | decoder {mae_decoder:6.2f} | "
                f"hibrido {mae_hibrido:6.2f}"
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
    detalle.to_csv(SALIDA / "lstm_decoder_compartido.csv", index=False)
    pred.to_csv(SALIDA / "lstm_decoder_compartido_predicciones.csv", index=False)
    resumen.to_csv(SALIDA / "lstm_decoder_compartido_resumen.csv", index=False)
    print("\nResumen:")
    print(resumen.to_string(index=False))
    print(f"\nTiempo total: {(time.perf_counter() - inicio_total) / 60:.1f} min")


if __name__ == "__main__":
    main()
