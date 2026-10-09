"""Jornada objetivo y horario sin base de datos, siempre en hora de Colombia."""

from datetime import UTC, date, datetime, timedelta

import pytest

from proyecto_grado.piloto.fechas import (
    ZONA,
    ErrorFecha,
    horario_bd_permitido,
    id_ejecucion,
    jornada_de,
    jornada_objetivo,
    objetivo_fijado,
)


def bog(*args):
    return datetime(*args, tzinfo=ZONA)


@pytest.mark.unit
def test_corrida_normal_a_las_0030_predice_el_dia_con_la_vispera_completa():
    o = jornada_objetivo(bog(2026, 10, 13, 0, 30))
    assert (o.d, o.d_mas_1) == (date(2026, 10, 12), date(2026, 10, 13))
    assert not o.tardia and not o.anticipada and not o.fijada


@pytest.mark.unit
def test_corrida_a_las_0359_no_es_tardia():
    o = jornada_objetivo(bog(2026, 10, 13, 3, 59))
    assert o.d_mas_1 == date(2026, 10, 13) and not o.tardia


@pytest.mark.unit
@pytest.mark.parametrize("hora", [(4, 0), (4, 1), (9, 30), (11, 59)])
def test_corrida_tardia_despues_de_las_0400_sigue_prediciendo_el_dia(hora):
    o = jornada_objetivo(bog(2026, 10, 13, *hora))
    assert (o.d, o.d_mas_1) == (date(2026, 10, 12), date(2026, 10, 13))
    assert o.tardia and not o.anticipada


@pytest.mark.unit
@pytest.mark.parametrize("hora", [(12, 0), (21, 0), (23, 0), (23, 59)])
def test_corrida_desde_las_1200_es_anticipada_y_predice_el_dia_siguiente(hora):
    o = jornada_objetivo(bog(2026, 10, 13, *hora))
    assert (o.d, o.d_mas_1) == (date(2026, 10, 13), date(2026, 10, 14))
    assert o.anticipada and not o.tardia


@pytest.mark.unit
def test_hora_utc_de_ec2_se_convierte_a_bogota():
    # 05:30 UTC del 13 = 00:30 del 13 en Bogota (UTC-5): la jornada es la del 13.
    o = jornada_objetivo(datetime(2026, 10, 13, 5, 30, tzinfo=UTC))
    assert o.d_mas_1 == date(2026, 10, 13) and not o.tardia
    # 03:00 UTC del 13 = 22:00 del 12 en Bogota: anticipada, objetivo el 13.
    o = jornada_objetivo(datetime(2026, 10, 13, 3, 0, tzinfo=UTC))
    assert o.d_mas_1 == date(2026, 10, 13) and o.anticipada


@pytest.mark.unit
def test_cambio_de_anio():
    o = jornada_objetivo(bog(2027, 1, 1, 0, 30))
    assert (o.d, o.d_mas_1) == (date(2026, 12, 31), date(2027, 1, 1))


@pytest.mark.unit
def test_hora_sin_zona_se_rechaza():
    with pytest.raises(ErrorFecha):
        jornada_objetivo(datetime(2026, 10, 13, 0, 30))


@pytest.mark.unit
def test_objetivo_fijado():
    o = objetivo_fijado(date(2026, 10, 1))
    assert (o.d, o.d_mas_1, o.fijada) == (date(2026, 9, 30), date(2026, 10, 1), True)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("hora", "permitido"),
    [
        ((3, 59), True),
        ((4, 0), False),
        ((12, 0), False),
        ((20, 59), False),
        ((21, 0), True),
        ((0, 30), True),
    ],
)
def test_horario_bd(hora, permitido):
    assert horario_bd_permitido(bog(2026, 10, 13, *hora)) is permitido


@pytest.mark.unit
def test_horario_bd_con_hora_utc():
    # 02:30 UTC = 21:30 Bogota (permitido); 14:00 UTC = 09:00 Bogota (bloqueado).
    assert horario_bd_permitido(datetime(2026, 10, 13, 2, 30, tzinfo=UTC))
    assert not horario_bd_permitido(datetime(2026, 10, 13, 14, 0, tzinfo=UTC))


@pytest.mark.unit
def test_jornada_de_un_instante():
    assert jornada_de(bog(2026, 10, 13, 3, 59)) == date(2026, 10, 12)
    assert jornada_de(bog(2026, 10, 13, 4, 0)) == date(2026, 10, 13)


@pytest.mark.unit
def test_id_ejecucion_en_hora_de_bogota():
    instante = datetime(2026, 10, 13, 5, 30, 7, tzinfo=UTC)
    assert id_ejecucion(instante) == "20261013_003007"
    assert id_ejecucion(instante + timedelta(seconds=1)) == "20261013_003008"
