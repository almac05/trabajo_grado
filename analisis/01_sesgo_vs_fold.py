import pandas as pd

p = "reports/tables/modeling/predictions_multitarget_xgboost_20260729.parquet"
df = pd.read_parquet(p)

# ver el contenido del DataFrame
print(df.head())
