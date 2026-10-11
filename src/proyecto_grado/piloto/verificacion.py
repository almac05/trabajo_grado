"""Vigilante de las 05:00 ("dead man's switch").

Comprueba que exista una corrida nocturna terminada con recomendacion valida
(estado OK; en la fase 2 tambien ADVERTENCIA o CONTINGENCIA) cuya jornada
objetivo sea hoy (hora de Colombia). Si no la hay, alerta por SNS: asi se
detecta tambien que el temporizador ni siquiera se disparo. Despues de la
alerta publica JornadaCubierta (1 o 0) en CloudWatch si PILOTO_METRICAS=1; un
fallo de CloudWatch no cambia el codigo de salida.

    python -m proyecto_grado.piloto.verificacion

Codigos de salida: 0 hay corrida valida; 1 no la hay (se alerto); 2 no la hay y
la alerta no se pudo enviar.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from proyecto_grado.modeling.config import PROJECT_ROOT
from proyecto_grado.piloto import avisos, metricas
from proyecto_grado.piloto.config import cargar_configuracion
from proyecto_grado.piloto.fechas import ahora_bogota
from proyecto_grado.piloto.registro import ocultar, registrar_variables_sensibles

ESTADOS_VALIDOS = ("OK", "ADVERTENCIA", "CONTINGENCIA")


def manifiestos(salidas: Path) -> list[dict]:
    salida = []
    for ruta in sorted(Path(salidas).glob("ejecuciones/*/manifiesto.json")):
        try:
            salida.append(json.loads(ruta.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return salida


def corrida_valida(salidas: Path, hoy: date) -> dict | None:
    """La ultima corrida nocturna con estado valido para la jornada ``hoy``."""
    validas = [
        m
        for m in manifiestos(salidas)
        if m.get("modo") == "nocturno"
        and m.get("estado") in ESTADOS_VALIDOS
        and (m.get("objetivo") or {}).get("d_mas_1") == hoy.isoformat()
    ]
    return validas[-1] if validas else None


def resumen_ultima(salidas: Path) -> str:
    todos = manifiestos(salidas)
    if not todos:
        return "No hay ninguna ejecucion registrada."
    m = todos[-1]
    return (
        f"Ultima ejecucion: {m.get('id_ejecucion')} modo {m.get('modo')} estado "
        f"{m.get('estado')} jornada {(m.get('objetivo') or {}).get('d_mas_1')}"
    )


def publicar_jornada_cubierta(cubierta: bool, ahora, fabrica_cliente=None) -> dict:
    """Publica JornadaCubierta; nunca lanza excepciones ni cambia el codigo de salida."""
    r = metricas.publicar_metricas(
        [metricas.dato_jornada_cubierta(cubierta)], ahora, fabrica_cliente
    )
    if r["metricas_publicadas"]:
        print(f"JornadaCubierta={int(cubierta)} publicada en CloudWatch.")
    else:
        print(ocultar(f"JornadaCubierta no publicada: {r['motivo']}"), file=sys.stderr)
    return r


def main(argv: list[str] | None = None, cliente=None, ahora=None, cliente_cw=None) -> int:
    p = argparse.ArgumentParser(description="Vigilante de la corrida nocturna.")
    p.add_argument("--directorio-salidas", default=None)
    args = p.parse_args(argv)
    cfg = cargar_configuracion()
    registrar_variables_sensibles(cfg.variables_sensibles)
    salidas = (
        PROJECT_ROOT / args.directorio_salidas
        if args.directorio_salidas
        else cfg.directorio_salidas
    )
    ahora = ahora or ahora_bogota()
    hoy = ahora.date()
    m = corrida_valida(salidas, hoy)
    if m is not None:
        print(f"Jornada {hoy}: corrida {m['id_ejecucion']} en estado {m['estado']}.")
        publicar_jornada_cubierta(True, ahora, cliente_cw)
        return 0
    cuerpo = "\n".join(
        [
            f"No hay corrida nocturna valida para la jornada {hoy}.",
            f"Hora de la verificacion (Colombia): {ahora.isoformat(timespec='seconds')}",
            resumen_ultima(salidas),
            "",
            "== ESTADO_ULTIMA_EJECUCION.txt ==",
            avisos.texto_estado_ultima(salidas),
            "",
            "Revisar: systemctl list-timers despacho-nocturno.timer ; "
            "journalctl -u despacho-nocturno.service -n 100",
            "Mientras tanto: operar como de costumbre.",
        ]
    )
    try:
        avisos.publicar(f"ALERTA piloto despacho: sin corrida para {hoy}", cuerpo, cliente=cliente)
        print(f"Sin corrida valida para {hoy}: alerta enviada.", file=sys.stderr)
        codigo = 1
    except avisos.ErrorAviso as exc:
        print(ocultar(f"Sin corrida valida y no se pudo alertar: {exc}"), file=sys.stderr)
        codigo = 2
    publicar_jornada_cubierta(False, ahora, cliente_cw)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
