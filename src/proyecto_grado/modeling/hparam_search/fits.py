"""Ajuste y prediccion de una jornada, por metodo, parametrizado por
hiperparametros.

Cada funcion reproduce exactamente la logica de ajuste/prediccion del script
de evaluacion comparativa correspondiente (scripts/run_<metodo>_comparative_
evaluation.py), sustituyendo los valores fijos por los del diccionario
``params`` que entrega la busqueda. No se modifica ningun script de
evaluacion; estas funciones son la unica pieza compartida.
"""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import torch
import xgboost as xgb
from prophet import Prophet
from statsmodels.tsa.statespace.sarimax import SARIMAX
from torch import nn

from proyecto_grado.modeling.hparam_search.spaces import (
    RED_FIJOS,
    SARIMA_FIJOS,
    XGBOOST_FIJOS,
)

PASOS = RED_FIJOS["pasos"]
CALENDARIO = ["dia_semana", "es_fin_semana", "es_festivo", "dia_semana_sin", "dia_semana_cos"]


# ---------------------------------------------------------------------------
# SARIMA
# ---------------------------------------------------------------------------


def ajustar_predecir_sarima(
    train_target: pd.Series, n_pasos: int, params: dict
) -> tuple[np.ndarray, float]:
    """Devuelve (prediccion, aic). aic se usa solo para reporte diagnostico."""
    orden = (int(params["p"]), int(SARIMA_FIJOS["d"]), int(params["q"]))
    orden_estacional = (
        int(params["P"]),
        int(SARIMA_FIJOS["D"]),
        int(params["Q"]),
        int(SARIMA_FIJOS["s"]),
    )
    ajuste = SARIMAX(
        train_target.reset_index(drop=True),
        order=orden,
        seasonal_order=orden_estacional,
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(disp=False)
    return ajuste.forecast(steps=n_pasos).to_numpy(), float(ajuste.aic)


# ---------------------------------------------------------------------------
# Prophet
# ---------------------------------------------------------------------------


def ajustar_predecir_prophet(
    train: pd.DataFrame,
    test: pd.DataFrame,
    festivos: pd.DataFrame,
    target: str,
    params: dict,
) -> np.ndarray:
    modelo = Prophet(
        holidays=festivos,
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=False,
        changepoint_prior_scale=params["changepoint_prior_scale"],
        seasonality_prior_scale=params["seasonality_prior_scale"],
        holidays_prior_scale=params["holidays_prior_scale"],
        seasonality_mode=params["seasonality_mode"],
        changepoint_range=params["changepoint_range"],
    )
    modelo.fit(train[["timestamp", target]].rename(columns={"timestamp": "ds", target: "y"}))
    pronostico = modelo.predict(test[["timestamp"]].rename(columns={"timestamp": "ds"}))
    return pronostico["yhat"].to_numpy()


# ---------------------------------------------------------------------------
# XGBoost
# ---------------------------------------------------------------------------


def ajustar_predecir_xgboost(
    fit_df: pd.DataFrame,
    stop_df: pd.DataFrame,
    test_df: pd.DataFrame,
    features: list[str],
    target: str,
    params: dict,
) -> tuple[np.ndarray, int]:
    params_completos = {**XGBOOST_FIJOS, **params}
    modelo = xgb.XGBRegressor(**params_completos)
    modelo.fit(
        fit_df[features],
        fit_df[target],
        eval_set=[(stop_df[features], stop_df[target])],
        verbose=False,
    )
    pred = modelo.predict(test_df[features])
    return pred, modelo.best_iteration + 1


# ---------------------------------------------------------------------------
# LSTM / GRU / CNN-LSTM
# ---------------------------------------------------------------------------


def secuencia_de(grupo: pd.DataFrame, target: str) -> tuple[np.ndarray, np.ndarray]:
    """Devuelve la demanda de una jornada y su mascara de posiciones validas."""
    valores = np.zeros(PASOS)
    mascara = np.zeros(PASOS)
    n = min(len(grupo), PASOS)
    valores[:n] = grupo[target].to_numpy()[:n]
    mascara[:n] = 1.0
    return valores, mascara


def construir_ejemplos(datos: pd.DataFrame, target: str, min_franjas: int) -> tuple:
    """Empareja cada jornada con la inmediatamente anterior (identico al
    script de evaluacion comparativa)."""
    dias = sorted(datos["dia_op"].unique())
    x_seq, x_msk, x_cal, y, y_msk = [], [], [], [], []

    for anterior, actual in itertools.pairwise(dias):
        if (pd.Timestamp(actual) - pd.Timestamp(anterior)).days != 1:
            continue

        prev = datos[datos["dia_op"] == anterior]
        curr = datos[datos["dia_op"] == actual]
        if len(prev) < min_franjas or len(curr) < min_franjas:
            continue

        s, ms = secuencia_de(prev, target)
        o, mo = secuencia_de(curr, target)

        x_seq.append(s)
        x_msk.append(ms)
        x_cal.append(curr.iloc[0][CALENDARIO].to_numpy(dtype=float))
        y.append(o)
        y_msk.append(mo)

    return (
        np.array(x_seq),
        np.array(x_msk),
        np.array(x_cal),
        np.array(y),
        np.array(y_msk),
    )


class RedGenerica(nn.Module):
    """LSTM, GRU o CNN-LSTM segun ``tipo``; misma arquitectura que los tres
    scripts de evaluacion comparativa, con unidades/filtros/nucleo
    parametrizables."""

    def __init__(
        self,
        tipo: str,
        n_calendario: int,
        unidades: int,
        filtros: int | None = None,
        nucleo: int | None = None,
    ):
        super().__init__()
        self.tipo = tipo
        if tipo == "cnn_lstm":
            self.conv = nn.Sequential(
                nn.Conv1d(
                    in_channels=2, out_channels=filtros, kernel_size=nucleo, padding=nucleo // 2
                ),
                nn.ReLU(),
            )
            entrada_rnn = filtros
        else:
            entrada_rnn = 2
        rnn_cls = nn.GRU if tipo == "gru" else nn.LSTM
        self.rnn = rnn_cls(input_size=entrada_rnn, hidden_size=unidades, batch_first=True)
        self.salida = nn.Sequential(
            nn.Linear(unidades + n_calendario, unidades),
            nn.ReLU(),
            nn.Linear(unidades, PASOS),
        )

    def forward(self, seq, msk, cal):
        if self.tipo == "cnn_lstm":
            entrada = torch.stack([seq, msk], dim=1)
            rasgos = self.conv(entrada).transpose(1, 2)
            salida_rnn = self.rnn(rasgos)
        else:
            entrada = torch.stack([seq, msk], dim=-1)
            salida_rnn = self.rnn(entrada)

        if self.tipo == "gru":
            _, estado = salida_rnn
        else:
            _, (estado, _) = salida_rnn
        return self.salida(torch.cat([estado[-1], cal], dim=1))


def perdida_enmascarada(pred, real, mascara):
    return (torch.abs(pred - real) * mascara).sum() / mascara.sum()


def entrenar_predecir_red(
    tipo: str,
    ajuste_arrays: tuple,
    parada_arrays: tuple,
    seq_test: np.ndarray,
    msk_test: np.ndarray,
    cal_test: np.ndarray,
    n_calendario: int,
    params: dict,
    dispositivo: torch.device,
) -> tuple[np.ndarray, int]:
    xs_a, xm_a, xc_a, y_a, ym_a = ajuste_arrays
    xs_p, xm_p, xc_p, y_p, ym_p = parada_arrays

    unidades = int(params["unidades"])
    lr = float(params["lr"])
    paciencia = int(params["paciencia"])
    filtros = int(params["filtros"]) if "filtros" in params else None
    nucleo = int(params["nucleo"]) if "nucleo" in params else None

    media = y_a[ym_a == 1].mean()
    desv = y_a[ym_a == 1].std()

    def t(x, escalar: bool = False):
        v = (x - media) / desv if escalar else x
        return torch.tensor(v, dtype=torch.float32, device=dispositivo)

    torch.manual_seed(RED_FIJOS["semilla_init"])
    modelo = RedGenerica(tipo, n_calendario, unidades, filtros, nucleo).to(dispositivo)
    optimizador = torch.optim.Adam(modelo.parameters(), lr=lr)

    ta = (t(xs_a, True), t(xm_a), t(xc_a), t(y_a, True), t(ym_a))
    tp = (t(xs_p, True), t(xm_p), t(xc_p), t(y_p, True), t(ym_p))

    mejor, sin_mejora, mejor_estado = float("inf"), 0, None
    epocas_techo = RED_FIJOS["epocas"]

    epoca = 0
    for epoca in range(epocas_techo):  # noqa: B007 - se usa tras el bucle
        modelo.train()
        optimizador.zero_grad()
        perdida_enmascarada(modelo(ta[0], ta[1], ta[2]), ta[3], ta[4]).backward()
        optimizador.step()

        modelo.eval()
        with torch.no_grad():
            val = perdida_enmascarada(modelo(tp[0], tp[1], tp[2]), tp[3], tp[4]).item()

        if val < mejor:
            mejor, sin_mejora = val, 0
            mejor_estado = {k: v.clone() for k, v in modelo.state_dict().items()}
        else:
            sin_mejora += 1
            if sin_mejora >= paciencia:
                break

    modelo.load_state_dict(mejor_estado)
    modelo.eval()
    with torch.no_grad():
        pred = (
            modelo(t(seq_test[None, :], True), t(msk_test[None, :]), t(cal_test[None, :]))
            .cpu()
            .numpy()[0]
            * desv
            + media
        )
    return pred, epoca + 1
