"""
scripts/build_productivity.py
Genera el reporte de productividad por despacho (semana x ruta).
"""

import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from proyecto_grado.analytics.vehicle_productivity import ProductivityAnalyzer  # noqa: E402


def main():
    df = pd.read_parquet(ROOT / "data/processed/model_ready/despachos_model_ready.parquet")

    analyzer = ProductivityAnalyzer(df)

    print("\n=== RESUMEN POR RUTA ===")
    print(analyzer.summary().to_string(index=False))

    print("\n=== PRIMERAS 12 SEMANAS DE LA SERIE (formato long) ===")
    print(analyzer.serie_semanal().head(12).to_string(index=False))

    print("\n=== ULTIMAS 12 SEMANAS DE LA SERIE ===")
    print(analyzer.serie_semanal().tail(12).to_string(index=False))

    analyzer.save()
    logger.info("Reporte de productividad completado")


if __name__ == "__main__":
    main()
