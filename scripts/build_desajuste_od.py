from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TS = ROOT / "data/processed/time_series"
OUT = ROOT / "reports/tables/baseline"
OUTPUT_CSV = OUT / "desajuste_oferta_demanda.csv"

RUTAS = {
    1: TS / "ts_ruta1_g30min.parquet",
    3: TS / "ts_ruta3_g30min.parquet",
}

REQUIRED_COLUMNS = {
    "timestamp",
    "pasajeros_total",
    "despachos_count",
    "tipo_dia",
    "dentro_horario_operativo",
}


def _calcular_ruta(ruta: int, path: Path) -> dict:
    ts = pd.read_parquet(path)
    missing = REQUIRED_COLUMNS.difference(ts.columns)
    if missing:
        missing_cols = ", ".join(sorted(missing))
        raise ValueError(f"{path} no contiene columnas requeridas: {missing_cols}")

    ts = ts.copy()
    ts["timestamp"] = pd.to_datetime(ts["timestamp"])

    lab = ts[ts["tipo_dia"].eq("LABORAL") & ts["dentro_horario_operativo"].eq(True)].copy()
    if lab.empty:
        raise ValueError(f"Ruta {ruta}: no hay filas LABORAL dentro de horario operativo")

    lab["despachos_count"] = lab["despachos_count"].fillna(0)
    lab["pasajeros_total"] = lab["pasajeros_total"].fillna(0)
    lab["tod"] = lab["timestamp"].dt.strftime("%H:%M")

    perfil = (
        lab.groupby("tod", as_index=False)[["despachos_count", "pasajeros_total"]]
        .mean()
        .sort_values("tod")
        .reset_index(drop=True)
    )

    suma_oferta = perfil["despachos_count"].sum()
    suma_demanda = perfil["pasajeros_total"].sum()
    if suma_oferta <= 0 or suma_demanda <= 0:
        raise ValueError(
            f"Ruta {ruta}: suma no positiva en oferta={suma_oferta} o demanda={suma_demanda}"
        )

    perfil["oferta_share"] = perfil["despachos_count"] / suma_oferta
    perfil["demanda_share"] = perfil["pasajeros_total"] / suma_demanda
    oferta_sum = float(perfil["oferta_share"].sum())
    demanda_sum = float(perfil["demanda_share"].sum())

    if abs(oferta_sum - 1.0) > 0.001:
        raise ValueError(f"Ruta {ruta}: oferta_share suma {oferta_sum:.6f}")
    if abs(demanda_sum - 1.0) > 0.001:
        raise ValueError(f"Ruta {ruta}: demanda_share suma {demanda_sum:.6f}")

    dif_abs = (perfil["oferta_share"] - perfil["demanda_share"]).abs()
    indice_disimilitud = float(0.5 * dif_abs.sum())
    if not 0 <= indice_disimilitud <= 1:
        raise ValueError(f"Ruta {ruta}: indice_disimilitud fuera de rango {indice_disimilitud:.6f}")

    return {
        "FK_RUTA": ruta,
        "indice_disimilitud": round(indice_disimilitud, 4),
        "pct_despachos_a_reubicar": round(indice_disimilitud * 100, 1),
        "mad_por_franja": round(float(dif_abs.mean()), 4),
        "n_franjas": int(perfil.shape[0]),
        "_oferta_share_sum": oferta_sum,
        "_demanda_share_sum": demanda_sum,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    filas = [_calcular_ruta(ruta, path) for ruta, path in RUTAS.items()]
    checks = pd.DataFrame(filas)
    result = checks[
        [
            "FK_RUTA",
            "indice_disimilitud",
            "pct_despachos_a_reubicar",
            "mad_por_franja",
            "n_franjas",
        ]
    ]
    result.to_csv(OUTPUT_CSV, index=False)

    print("\n=== KPI 4: desajuste oferta-demanda (LABORAL, horario operativo) ===")
    print(result.to_string(index=False))
    print("\nVerificacion de distribuciones:")
    print(checks[["FK_RUTA", "_oferta_share_sum", "_demanda_share_sum"]].to_string(index=False))
    print(f"\nCSV escrito:\n  {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
