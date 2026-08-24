"""LSTM sobre una jornada, para medir el costo de entrenamiento.

Objetivo inmediato: determinar si el reentrenamiento diario --274 modelos entre
las dos rutas-- es viable con el equipo disponible. De ello depende que la
comparacion con los metodos anteriores mantenga un protocolo homogeneo.

Diseno de entrada. Una red recurrente espera secuencias. La restriccion de
consolidacion impide usar las franjas inmediatamente anteriores, de modo que
la secuencia se construye con las franjas del dia previo completo, cuyos
registros si estan disponibles al momento de decidir el despacho. A esa
secuencia se anaden las variables de calendario del dia objetivo, conocidas de
antemano.
"""

import time

import numpy as np
import pandas as pd
import torch
from torch import nn

DISPOSITIVO = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Dispositivo: {DISPOSITIVO}")

torch.manual_seed(42)
np.random.seed(42)

PARQUET = "data/processed/modeling/modeling_dataset_pasajeros_total_sin_oferta_g30min.parquet"
RUTA = 1
TARGET = "pasajeros_total"

DIA = pd.Timestamp("2026-04-15")
SEMANAS_ENTRENAMIENTO = 26
PARADA_SEMANAS = 2

# Longitud de la secuencia de entrada: las franjas de una jornada operativa.
PASOS = 28

# Variables de calendario, conocidas de antemano para cualquier fecha.
CALENDARIO = [
    "hora_del_dia", "dia_semana", "es_fin_semana", "es_festivo",
    "hora_sin", "hora_cos", "dia_semana_sin", "dia_semana_cos",
]

UNIDADES = 64        # tamano del estado oculto de la LSTM
EPOCAS = 3000         # techo; decide la parada temprana
PACIENCIA = 20       # epocas sin mejora antes de detener
LR = 0.001

df = pd.read_parquet(PARQUET)
d = df[(df["FK_RUTA"] == RUTA) & df[TARGET].notna()].copy()
d = d.sort_values("timestamp").reset_index(drop=True)
d["dia_op"] = (d["timestamp"] - pd.Timedelta(hours=4)).dt.date

print(f"Ruta {RUTA}: {len(d)} observaciones")

# Imprime las columnas de d
print("Columnas de d:")
for col in d.columns:
    print(f"  {col}")

# Imprime los primeros registros de d
print("\nPrimeros registros de d:")
print(d.head())

def construir_ejemplos(datos: pd.DataFrame) -> tuple:
    """Convierte la tabla en pares (dia previo, dia objetivo).

    Cada ejemplo asocia la secuencia de demanda del dia anterior con la
    secuencia de demanda del dia siguiente. Los dias con distinto numero de
    franjas se recortan o rellenan a PASOS para que las secuencias sean
    homogeneas, requisito de las capas recurrentes.
    """
    dias = sorted(datos["dia_op"].unique())
    X_seq, X_cal, Y = [], [], []

    for anterior, actual in zip(dias[:-1], dias[1:], strict=False):
        # Solo se emparejan dias consecutivos: un salto indicaria ausencia de
        # operacion, y la secuencia dejaria de representar "el dia anterior".
        if (pd.Timestamp(actual) - pd.Timestamp(anterior)).days != 1:
            continue

        prev = datos[datos["dia_op"] == anterior]
        curr = datos[datos["dia_op"] == actual]
        if len(prev) < 8 or len(curr) < 8:
            continue

        seq = np.zeros(PASOS)
        n = min(len(prev), PASOS)
        seq[:n] = prev[TARGET].to_numpy()[:n]

        obj = np.zeros(PASOS)
        m = min(len(curr), PASOS)
        obj[:m] = curr[TARGET].to_numpy()[:m]

        # Calendario del dia objetivo: se toma de su primera franja, dado que
        # las variables de tipo de dia son constantes dentro de la jornada.
        cal = curr.iloc[0][["dia_semana", "es_fin_semana", "es_festivo",
                            "dia_semana_sin", "dia_semana_cos"]].to_numpy(dtype=float)

        X_seq.append(seq)
        X_cal.append(cal)
        Y.append(obj)

    return np.array(X_seq), np.array(X_cal), np.array(Y)

class RedLSTM(nn.Module):
    """LSTM que predice una jornada completa a partir de la anterior.

    La capa recurrente procesa la secuencia del dia previo y produce un estado
    que resume su comportamiento. Ese estado se concatena con las variables de
    calendario del dia objetivo --que la red no puede inferir de la serie-- y
    una capa densa emite las PASOS predicciones de la jornada.
    """

    def __init__(self, n_calendario: int, unidades: int = UNIDADES):
        super().__init__()
        self.lstm = nn.LSTM(input_size=1, hidden_size=unidades, batch_first=True)
        self.salida = nn.Sequential(
            nn.Linear(unidades + n_calendario, unidades),
            nn.ReLU(),
            nn.Linear(unidades, PASOS),
        )

    def forward(self, seq, cal):
        # seq llega como (lote, PASOS); la LSTM espera (lote, PASOS, features)
        _, (estado, _) = self.lstm(seq.unsqueeze(-1))
        return self.salida(torch.cat([estado[-1], cal], dim=1))

inicio_dia = DIA + pd.Timedelta(hours=4)
corte_parada = inicio_dia - pd.Timedelta(weeks=PARADA_SEMANAS)
inicio_train = inicio_dia - pd.Timedelta(weeks=SEMANAS_ENTRENAMIENTO)

# imprime los periodos de entrenamiento y parada temprana
print(f"Periodo de entrenamiento: {inicio_train} a {corte_parada}")
print(f"Periodo de parada temprana: {corte_parada} a {inicio_dia}")


train = d[(d["timestamp"] >= inicio_train) & (d["timestamp"] < corte_parada)]
stop = d[(d["timestamp"] >= corte_parada) & (d["timestamp"] < inicio_dia)]

Xs_tr, Xc_tr, Y_tr = construir_ejemplos(train)
Xs_st, Xc_st, Y_st = construir_ejemplos(stop)

print(f"Ejemplos de ajuste: {len(Y_tr)} | parada temprana: {len(Y_st)}")

# El escalado se ajusta unicamente con datos de ajuste. Aplicar estadisticos
# calculados sobre el periodo completo constituiria fuga de informacion.
media, desv = Y_tr.mean(), Y_tr.std()
print(f"Escalado: media {media:.1f}, desviacion {desv:.1f}")


def a_tensor(xs, xc, y):
    return (
        torch.tensor((xs - media) / desv, dtype=torch.float32, device=DISPOSITIVO),
        torch.tensor(xc, dtype=torch.float32, device=DISPOSITIVO),
        torch.tensor((y - media) / desv, dtype=torch.float32, device=DISPOSITIVO),
    )


xs_tr, xc_tr, y_tr = a_tensor(Xs_tr, Xc_tr, Y_tr)
xs_st, xc_st, y_st = a_tensor(Xs_st, Xc_st, Y_st)

modelo = RedLSTM(n_calendario=xc_tr.shape[1]).to(DISPOSITIVO)
optimizador = torch.optim.Adam(modelo.parameters(), lr=LR)
perdida = nn.L1Loss()   # error absoluto, coherente con la metrica de evaluacion

print(f"\nParametros entrenables: {sum(p.numel() for p in modelo.parameters()):,}")
print("Entrenando ...")

t0 = time.perf_counter()
mejor, mejor_epoca, sin_mejora = float("inf"), 0, 0
mejor_estado = None

for epoca in range(EPOCAS):
    modelo.train()
    optimizador.zero_grad()
    loss = perdida(modelo(xs_tr, xc_tr), y_tr)
    loss.backward()
    optimizador.step()

    # La parada temprana se evalua sobre las dos semanas reservadas, igual que
    # en los modelos anteriores.
    modelo.eval()
    with torch.no_grad():
        val = perdida(modelo(xs_st, xc_st), y_st).item()

    if val < mejor:
        mejor, mejor_epoca, sin_mejora = val, epoca, 0
        mejor_estado = {k: v.clone() for k, v in modelo.state_dict().items()}
    else:
        sin_mejora += 1
        if sin_mejora >= PACIENCIA:
            break

segundos = time.perf_counter() - t0
modelo.load_state_dict(mejor_estado)

print(f"Detenido en la epoca {epoca + 1}; mejor en la {mejor_epoca + 1}")
print(f"Tiempo de entrenamiento: {segundos:.1f} s")
print(f"\nProyeccion para 274 entrenamientos: {274 * segundos / 60:.1f} min")


# La secuencia de entrada es la jornada previa al dia a predecir.
dia_previo = (DIA - pd.Timedelta(days=1)).date()
prev = d[d["dia_op"] == dia_previo]
curr = d[d["dia_op"] == DIA.date()]

seq = np.zeros(PASOS)
seq[:min(len(prev), PASOS)] = prev[TARGET].to_numpy()[:PASOS]
cal = curr.iloc[0][["dia_semana", "es_fin_semana", "es_festivo",
                    "dia_semana_sin", "dia_semana_cos"]].to_numpy(dtype=float)

modelo.eval()
with torch.no_grad():
    pred = modelo(
        torch.tensor((seq - media) / desv, dtype=torch.float32,
                     device=DISPOSITIVO).unsqueeze(0),
        torch.tensor(cal, dtype=torch.float32, device=DISPOSITIVO).unsqueeze(0),
    ).cpu().numpy()[0] * desv + media

n = min(len(curr), PASOS)
real = curr[TARGET].to_numpy()[:n]
error = pred[:n] - real

print(f"\nMAE:   {np.abs(error).mean():.2f}")
print(f"Sesgo: {error.mean():+.2f}")
print(f"Amplitud predicha: {pred[:n].max() - pred[:n].min():.1f} | "
      f"observada: {real.max() - real.min():.1f}")
