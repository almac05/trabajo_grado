"""ACF y PACF de la serie a 30 minutos, solo horario operativo.

El analisis previo incluia las franjas sin operacion, cuyos valores nulos o
cero distorsionan la estructura de autocorrelacion. Aqui se restringe a las
franjas con operacion real para determinar el periodo estacional de SARIMA.
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf  # noqa: E402

P = "data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
TARGET = "pasajeros_total"
LAGS = 60   # cubre mas de dos ciclos diarios de 28 franjas

df = pd.read_parquet(P)

for ruta in (1, 3):
    d = df[(df["FK_RUTA"] == ruta) & df[TARGET].notna()].sort_values("timestamp")
    s = d[TARGET]

    print(f"\nRuta {ruta}: {len(s)} observaciones operativas")
    print(f"Franjas por dia operativo (mediana): "
          f"{d.groupby((d['timestamp'] - pd.Timedelta(hours=4)).dt.date).size().median():.0f}")

    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    plot_acf(s, lags=LAGS, ax=axes[0], title=None)
    plot_pacf(s, lags=LAGS, ax=axes[1], method="ywm", title=None)
    axes[0].set_xlabel("Rezago (franjas de 30 min)")
    axes[1].set_xlabel("Rezago (franjas de 30 min)")
    axes[0].set_ylabel("ACF")
    axes[1].set_ylabel("PACF")
    fig.tight_layout()
    fig.savefig(f"analisis/salidas/acf_operativo_r{ruta}.png", dpi=130)
    plt.close(fig)

    # Valores numericos de los rezagos candidatos
    from statsmodels.tsa.stattools import acf
    valores = acf(s, nlags=LAGS)
    print("Rezagos candidatos:")
    for k in (1, 2, 3, 12, 13, 14, 24, 26, 27, 28, 29, 30, 48, 56):
        if k <= LAGS:
            print(f"  lag {k:3d}: {valores[k]:+.3f}")
