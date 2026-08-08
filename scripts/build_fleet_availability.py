"""
scripts/build_fleet_availability.py
Genera el reporte de disponibilidad de flota para el baseline.

Uso:
    python scripts/build_fleet_availability.py
    python scripts/build_fleet_availability.py --n-dias 20
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from proyecto_grado.analytics.fleet_availability import FleetAvailabilityAnalyzer  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-dias", type=int, default=15)
    args = parser.parse_args()

    df = pd.read_parquet(ROOT / "data/processed/model_ready/despachos_model_ready.parquet")

    analyzer = FleetAvailabilityAnalyzer(df)
    resultado = analyzer.run(n_dias=args.n_dias)

    print("\n=== RESULTADO POR DÍA ===")
    print(resultado.to_string())

    print("\n=== CONCLUSIÓN AGREGADA ===")
    for k, v in analyzer.conclusion_agregada().items():
        print(f"  {k}: {v}")

    analyzer.save()
    logger.info("Reporte de disponibilidad de flota completado")


if __name__ == "__main__":
    main()
