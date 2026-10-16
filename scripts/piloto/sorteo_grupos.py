"""Sorteo de grupos MODULO / CONTROL de la piloto (19 al 30 de octubre de 2026).

Aleatorizacion en bloques por dia de la semana con semilla fija 20261019,
definida antes del sorteo. El sorteo se hizo el 2026-10-12 y su resultado esta
en configs/piloto/asignacion_grupos.yaml; este script lo reproduce (versionado
en piloto-v1.4, 2026-10-15). No se vuelve a sortear.

Regla:
- dias laborales en orden lunes -> viernes (weekday 0..4): el par son las dos
  fechas de ese dia de la semana; si rng.random() < 0.5 la primera es MODULO y
  la segunda CONTROL; si no, al reves;
- despues, el par sabado 24 / domingo 25 con la misma regla (sabado = primera).

Solo biblioteca estandar. Imprime la asignacion en formato YAML y el conteo.

Uso:
    python scripts/piloto/sorteo_grupos.py
"""

from __future__ import annotations

import random
from collections import Counter
from datetime import date, timedelta

SEMILLA = 20261019
INICIO = date(2026, 10, 19)
FIN = date(2026, 10, 30)


def sortear(semilla: int = SEMILLA) -> dict[date, str]:
    """Mapa fecha -> grupo, en orden de fecha."""
    rng = random.Random(semilla)
    dias = [INICIO + timedelta(days=i) for i in range((FIN - INICIO).days + 1)]
    pares = [[d for d in dias if d.weekday() == wd] for wd in range(5)]
    pares.append([date(2026, 10, 24), date(2026, 10, 25)])
    asignacion = {}
    for primera, segunda in pares:
        if rng.random() < 0.5:
            asignacion[primera], asignacion[segunda] = "MODULO", "CONTROL"
        else:
            asignacion[primera], asignacion[segunda] = "CONTROL", "MODULO"
    return dict(sorted(asignacion.items()))


def como_yaml(asignacion: dict[date, str]) -> str:
    return "".join(f"{d.isoformat()}: {g}\n" for d, g in asignacion.items())


def main() -> None:
    asignacion = sortear()
    print(como_yaml(asignacion), end="")
    conteo = Counter(asignacion.values())
    print(f"# MODULO: {conteo['MODULO']}, CONTROL: {conteo['CONTROL']}")


if __name__ == "__main__":
    main()
