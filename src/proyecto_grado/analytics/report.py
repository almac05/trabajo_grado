"""CLI/report generation for post-ETL analytics."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from proyecto_grado.analytics.etl_diagnostics import (
    DatasetPaths,
    build_etl_diagnostics,
    load_etl_datasets,
)
from proyecto_grado.analytics.kpis import build_kpi_tables
from proyecto_grado.analytics.plots import save_standard_plots
from proyecto_grado.etl.config import REPORTS_DIR, inicializar_entorno

logger = logging.getLogger(__name__)

TABLES_DIR = Path(REPORTS_DIR) / "eda"
FIGURES_DIR = Path(REPORTS_DIR).parent / "figures" / "eda"


def write_tables(
    tables: dict[str, pd.DataFrame], output_dir: str | Path = TABLES_DIR
) -> list[Path]:
    """Write report tables as CSV files."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for name, df in tables.items():
        path = output_dir / f"{name}.csv"
        df.to_csv(path, index=False, encoding="utf-8")
        saved.append(path)
    return saved


def build_post_etl_report(
    paths: DatasetPaths | None = None,
    tables_dir: str | Path = TABLES_DIR,
    figures_dir: str | Path = FIGURES_DIR,
    make_plots: bool = True,
) -> dict[str, list[Path]]:
    """Generate post-ETL diagnostics, KPI tables and optional figures."""
    inicializar_entorno(verbose=False)
    datasets = load_etl_datasets(paths)
    tables = {}
    tables.update(build_etl_diagnostics(datasets))
    tables.update(build_kpi_tables(datasets))

    saved_tables = write_tables(tables, tables_dir)
    saved_figures = save_standard_plots(tables, figures_dir) if make_plots else []
    return {"tables": saved_tables, "figures": saved_figures}


def main() -> None:
    """CLI entry point for the post-ETL analytics report."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    outputs = build_post_etl_report()
    logger.info("Reporte post-ETL generado")
    logger.info("Tablas:")
    for path in outputs["tables"]:
        logger.info("  %s", path)
    logger.info("Figuras:")
    for path in outputs["figures"]:
        logger.info("  %s", path)


if __name__ == "__main__":
    main()
