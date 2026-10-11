"""Alerta por SNS cuando falla una unidad de systemd de la piloto.

La invoca ``despacho-alerta@.service`` (OnFailure=) con el nombre de la unidad:

    python -m proyecto_grado.piloto.alerta --unidad despacho-nocturno.service

Incluye la unidad, la hora de Colombia, el equipo, el contenido de
ESTADO_ULTIMA_EJECUCION.txt y las ultimas 30 lineas del journal de la unidad,
todo pasado por el filtro de secretos. Sale con 1 si no pudo publicar.
"""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.piloto import avisos
from proyecto_grado.piloto.config import cargar_configuracion
from proyecto_grado.piloto.fechas import ahora_bogota
from proyecto_grado.piloto.registro import ocultar, registrar_variables_sensibles

LINEAS_JOURNAL = 30


def leer_journal(unidad: str, lineas: int = LINEAS_JOURNAL) -> str:
    try:
        r = subprocess.run(
            ["journalctl", "-u", unidad, "-n", str(lineas), "--no-pager", "-o", "short-iso"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"(no se pudo leer el journal: {exc})"
    return r.stdout.strip() or f"(journal vacio; {r.stderr.strip()})"


def construir_alerta(unidad: str, salidas: Path, journal: str, ahora=None) -> tuple[str, str]:
    ahora = ahora or ahora_bogota()
    cuerpo = "\n".join(
        [
            f"Fallo la unidad {unidad}",
            f"Hora (Colombia): {ahora.isoformat(timespec='seconds')}",
            f"Equipo: {platform.node()}",
            "",
            "== ESTADO_ULTIMA_EJECUCION.txt ==",
            avisos.texto_estado_ultima(salidas),
            "",
            f"== Ultimas {LINEAS_JOURNAL} lineas del journal ==",
            journal,
            "",
            "Si no hay recomendacion valida para la jornada: operar como de costumbre.",
        ]
    )
    return f"ALERTA piloto despacho: fallo {unidad}", cuerpo


def main(argv: list[str] | None = None, cliente=None, journal=leer_journal) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--unidad", required=True)
    p.add_argument("--directorio-salidas", default=None)
    args = p.parse_args(argv)
    cfg = cargar_configuracion()
    registrar_variables_sensibles(cfg.variables_sensibles)
    salidas = (
        PROJECT_ROOT / args.directorio_salidas
        if args.directorio_salidas
        else cfg.directorio_salidas
    )
    asunto, cuerpo = construir_alerta(args.unidad, salidas, journal(args.unidad))
    try:
        avisos.publicar(asunto, cuerpo, cliente=cliente)
    except avisos.ErrorAviso as exc:
        print(f"No se pudo enviar la alerta: {exc}", file=sys.stderr)
        print(ocultar(cuerpo), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
