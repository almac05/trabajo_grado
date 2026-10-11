"""Latencia de los registros de registradora (seccion 0 del diseno de la piloto).

Para los despachos de las rutas 1 y 3 de los ultimos N dias (por defecto 30),
mide que fraccion de sus registros de ``tbl_informacion_registradora`` se creo
despues de cada umbral, respecto a la jornada del despacho (FECHA_INICIAL):

- despues de las 21:00 de la jornada (opcion A del diseno);
- despues de las 23:42 de la jornada (cierre automatico observado en abril);
- despues de las 00:30 del dia siguiente (lo que la corrida de las 00:30 no ve);
- despues de las 04:00 del dia siguiente (inicio de la jornada siguiente).

Solo lectura (sesion READ ONLY), con la proteccion de horario del orquestador:
no consulta la base entre las 04:00 y las 21:00 de Colombia salvo
--forzar-horario. La columna con la hora de creacion del registro se detecta con
SHOW COLUMNS entre nombres candidatos o se indica con --columna-creacion.

Salidas nuevas (nunca sobrescribe) en data/piloto/diagnosticos/:
    latencia_registros_<id>.csv   por jornada
    latencia_registros_<id>.md    resumen por jornada y total

Uso (en EC2, con el tunel arriba):
    uv run --frozen python scripts/piloto/latencia_registros.py [--dias 30]
        [--columna-creacion NOMBRE] [--forzar-horario]
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.piloto.fechas import ahora_bogota, horario_bd_permitido, id_ejecucion
from proyecto_grado.piloto.registro import ocultar

TABLA = "tbl_informacion_registradora"
CANDIDATOS = (
    "FECHA_CREACION",
    "FECHA_HORA_CREACION",
    "FECHA_REGISTRO",
    "FECHA_INSERCION",
    "FECHA_SISTEMA",
    "CREATED_AT",
)
TIPOS_FECHA_HORA = ("datetime", "timestamp")
UMBRALES = {
    "despues_21_00": timedelta(hours=21),
    "despues_23_42": timedelta(hours=23, minutes=42),
    "despues_00_30_dia_siguiente": timedelta(days=1, minutes=30),
    "despues_04_00_dia_siguiente": timedelta(days=1, hours=4),
}
DIRECTORIO = PROJECT_ROOT / "data" / "piloto" / "diagnosticos"


class ErrorLatencia(RuntimeError):  # noqa: N818
    pass


def detectar_columna(columnas: list[tuple[str, str]], forzada: str | None) -> str:
    """Columna de fecha y hora de creacion del registro.

    ``columnas``: (nombre, tipo) de SHOW COLUMNS. Con ``forzada`` se valida que
    exista y sea de fecha y hora; si no, se toma el primer candidato presente.
    """
    tipos = {n.upper(): t.lower() for n, t in columnas}
    con_hora = sorted(n for n, t in tipos.items() if t.startswith(TIPOS_FECHA_HORA))
    if forzada is not None:
        nombre = forzada.upper()
        if nombre not in tipos:
            raise ErrorLatencia(f"{TABLA} no tiene la columna {forzada}.")
        if not tipos[nombre].startswith(TIPOS_FECHA_HORA):
            raise ErrorLatencia(f"{forzada} es {tipos[nombre]}, no fecha y hora.")
        return nombre
    for nombre in CANDIDATOS:
        if nombre in tipos and tipos[nombre].startswith(TIPOS_FECHA_HORA):
            return nombre
    raise ErrorLatencia(
        "No se encontro la columna de creacion entre los candidatos "
        f"{list(CANDIDATOS)}. Columnas de fecha y hora de {TABLA}: {con_hora}. "
        "Indiquela con --columna-creacion."
    )


def consulta(columna: str) -> str:
    """SQL de solo lectura. El nombre de columna viene de SHOW COLUMNS y se valida."""
    if not re.fullmatch(r"[A-Z0-9_]+", columna):
        raise ErrorLatencia(f"Nombre de columna invalido: {columna!r}.")
    return (
        "SELECT d.PK_INTERVALO_DESPACHO AS pk, d.FECHA_INICIAL AS jornada, d.FK_RUTA AS ruta, "
        f"r.`{columna}` AS creado "
        "FROM tbl_intervalo_despacho d "
        "INNER JOIN tbl_informacion_registradora r "
        "ON r.FK_INTERVALO_DESPACHO = d.PK_INTERVALO_DESPACHO "
        "WHERE d.FECHA_INICIAL BETWEEN %s AND %s AND d.ESTADO = 1 AND d.FK_RUTA IN (1, 3) "
        "AND r.FECHA_SALIDA_BASE_SALIDA BETWEEN %s AND %s"
    )


def resumir(registros: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Por jornada y en total: registros y fraccion creada despues de cada umbral."""
    df = registros.copy()
    df["jornada"] = pd.to_datetime(df["jornada"]).dt.normalize()
    df["creado"] = pd.to_datetime(df["creado"], errors="coerce")
    for nombre, desfase in UMBRALES.items():
        df[nombre] = df["creado"] > df["jornada"] + desfase
    df["sin_hora_creacion"] = df["creado"].isna()
    columnas = [*UMBRALES, "sin_hora_creacion"]
    por_dia = df.groupby(df["jornada"].dt.date)[columnas].agg(["sum", "mean"])
    por_dia.columns = [f"{c}_{'n' if a == 'sum' else 'fraccion'}" for c, a in por_dia.columns]
    por_dia.insert(0, "registros", df.groupby(df["jornada"].dt.date).size())
    por_dia.insert(1, "despachos", df.groupby(df["jornada"].dt.date)["pk"].nunique())
    por_dia.index.name = "jornada"
    total = {"registros": len(df), "despachos": int(df["pk"].nunique())}
    for c in columnas:
        total[f"{c}_n"] = int(df[c].sum())
        total[f"{c}_fraccion"] = float(df[c].mean()) if len(df) else float("nan")
    return por_dia.reset_index(), total


def informe_md(por_dia: pd.DataFrame, total: dict, columna: str, desde: date, hasta: date) -> str:
    def pct(x):
        return "—" if pd.isna(x) else f"{100 * x:.1f} %"

    lineas = [
        "# Latencia de los registros de registradora",
        "",
        f"Jornadas del {desde} al {hasta}, rutas 1 y 3, `ESTADO = 1`. Hora de creacion: "
        f"`{TABLA}.{columna}`.",
        "",
        f"**Total:** {total['registros']} registros de {total['despachos']} despachos.",
        "",
        "| Creado despues de | Registros | Fraccion |",
        "|---|---|---|",
    ]
    for nombre in [*UMBRALES, "sin_hora_creacion"]:
        lineas.append(f"| {nombre} | {total[f'{nombre}_n']} | {pct(total[f'{nombre}_fraccion'])} |")
    lineas += [
        "",
        "## Por jornada",
        "",
        "| Jornada | Registros | " + " | ".join(UMBRALES) + " |",
        "|---|---|" + "---|" * len(UMBRALES),
    ]
    for _, f in por_dia.iterrows():
        lineas.append(
            f"| {f['jornada']} | {f['registros']} | "
            + " | ".join(pct(f[f"{u}_fraccion"]) for u in UMBRALES)
            + " |"
        )
    return "\n".join(lineas) + "\n"


def _texto(valor) -> str:
    """mysql-connector puede devolver bytes en SHOW COLUMNS."""
    return valor.decode("utf-8") if isinstance(valor, bytes | bytearray) else str(valor)


def nuevo(ruta: Path) -> Path:
    if ruta.exists():
        raise FileExistsError(f"No se sobrescribe: {ruta}")
    return ruta


def main(argv: list[str] | None = None, conectar=None, ahora=None) -> int:
    p = argparse.ArgumentParser(description="Latencia de los registros de registradora.")
    p.add_argument("--dias", type=int, default=30)
    p.add_argument("--columna-creacion", default=None)
    p.add_argument("--forzar-horario", action="store_true")
    p.add_argument("--directorio-salidas", default=None)
    args = p.parse_args(argv)

    ahora = ahora or ahora_bogota()
    if not horario_bd_permitido(ahora) and not args.forzar_horario:
        print(
            f"Son las {ahora:%H:%M} en Colombia: no se consulta la base entre las 04:00 y las "
            "21:00 (use --forzar-horario para una excepcion autorizada).",
            file=sys.stderr,
        )
        return 1
    hasta = ahora.date() - timedelta(days=1)
    desde = hasta - timedelta(days=args.dias - 1)
    salida = PROJECT_ROOT / args.directorio_salidas if args.directorio_salidas else DIRECTORIO
    ident = id_ejecucion(ahora)
    rutas = {
        "csv": nuevo(salida / f"latencia_registros_{ident}.csv"),
        "md": nuevo(salida / f"latencia_registros_{ident}.md"),
    }

    if conectar is None:
        from proyecto_grado.etl.db import conectar_bd as conectar
    conexion = conectar("bd_montebello_rdw")
    if conexion is None:
        print("No se pudo conectar a bd_montebello_rdw.", file=sys.stderr)
        return 1
    try:
        cursor = conexion.cursor()
        cursor.execute("SET SESSION TRANSACTION READ ONLY")
        cursor.execute(f"SHOW COLUMNS FROM {TABLA}")
        columna = detectar_columna(
            [(_texto(f[0]), _texto(f[1])) for f in cursor.fetchall()], args.columna_creacion
        )
        cursor.execute(consulta(columna), (desde, hasta, desde, hasta))
        filas = cursor.fetchall()
        cursor.close()
    except ErrorLatencia as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        conexion.close()

    registros = pd.DataFrame(filas, columns=["pk", "jornada", "ruta", "creado"])
    por_dia, total = resumir(registros)
    salida.mkdir(parents=True, exist_ok=True)
    por_dia.to_csv(rutas["csv"], index=False)
    rutas["md"].write_text(informe_md(por_dia, total, columna, desde, hasta), encoding="utf-8")
    print(ocultar(f"Columna de creacion: {columna}. Jornadas {desde} a {hasta}."))
    for nombre in UMBRALES:
        print(
            f"  {nombre}: {total[f'{nombre}_n']} de {total['registros']} "
            f"({100 * total[f'{nombre}_fraccion']:.1f} %)"
            if total["registros"]
            else nombre
        )
    print(f"Salidas: {rutas['csv']} y {rutas['md']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
