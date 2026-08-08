import pandas as pd

# 1. Columnas del model_ready
mr = pd.read_parquet("data/processed/model_ready/despachos_model_ready.parquet")
print("=== MODEL_READY ===")
print(mr.dtypes)
print(f"Filas: {len(mr)}")
print(f"HORA_INICIAL_REAL sample: {mr['HORA_INICIAL_REAL'].head(3).tolist()}")
print(f"FECHA_INICIAL sample: {mr['FECHA_INICIAL'].head(3).tolist()}")

# 2. Columnas de la serie temporal 60min ruta 1
ts = pd.read_parquet("data/processed/time_series/ts_ruta1_g60min.parquet")
print("\n=== TIME SERIES 60min Ruta 1 ===")
print(ts.dtypes)
print(f"Filas: {len(ts)}")
print(f"timestamp sample: {ts['timestamp'].head(3).tolist()}")

# 3. Verificar si tiene dentro_horario_operativo y gap_tipo
cols_op = ["dentro_horario_operativo", "gap_tipo", "is_gap", "tipo_dia", "franja_horaria"]
for col in cols_op:
    presente = col in ts.columns
    print(f"  {col}: {'✅' if presente else '❌'}")

# 4. Valores únicos de tipo_dia y franja_horaria
if "tipo_dia" in ts.columns:
    print(f"\ntipo_dia valores: {ts['tipo_dia'].unique().tolist()}")
if "franja_horaria" in ts.columns:
    print(f"franja_horaria valores: {ts['franja_horaria'].unique().tolist()}")
