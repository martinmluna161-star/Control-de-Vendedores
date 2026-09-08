import datetime

from app.services.vacaciones import (
    fechas_de_referencia,
    fechas_del_rango,
    nombre_dia,
    zona_trabaja_ese_dia,
)


def test_nombre_dia():
    assert nombre_dia(datetime.date(2026, 9, 8)) == "Martes"  # confirmado: hoy es martes
    assert nombre_dia(datetime.date(2026, 9, 7)) == "Lunes"
    assert nombre_dia(datetime.date(2026, 9, 12)) == "Sábado"


def test_zona_trabaja_ese_dia_con_un_solo_dia():
    assert zona_trabaja_ese_dia("Lunes", "Lunes") is True
    assert zona_trabaja_ese_dia("Lunes", "Martes") is False


def test_zona_trabaja_ese_dia_con_varios_dias():
    assert zona_trabaja_ese_dia("Lunes/Martes/Viernes/Sábado", "Viernes") is True
    assert zona_trabaja_ese_dia("Lunes/Martes/Viernes/Sábado", "Miércoles") is False


def test_zona_trabaja_ese_dia_vacio_o_none():
    assert zona_trabaja_ese_dia("", "Lunes") is False
    assert zona_trabaja_ese_dia(None, "Lunes") is False


def test_fechas_del_rango_incluye_ambos_extremos():
    fechas = fechas_del_rango(datetime.date(2026, 9, 7), datetime.date(2026, 9, 9))
    assert fechas == [datetime.date(2026, 9, 7), datetime.date(2026, 9, 8), datetime.date(2026, 9, 9)]


def test_fechas_del_rango_invertido_da_vacio():
    assert fechas_del_rango(datetime.date(2026, 9, 9), datetime.date(2026, 9, 7)) == []


def test_fechas_del_rango_un_solo_dia():
    fecha = datetime.date(2026, 9, 8)
    assert fechas_del_rango(fecha, fecha) == [fecha]


def test_fechas_de_referencia_retrocede_de_a_semanas():
    fechas = fechas_de_referencia(datetime.date(2026, 9, 8))
    assert fechas == [
        datetime.date(2026, 9, 1),
        datetime.date(2026, 8, 25),
        datetime.date(2026, 8, 18),
        datetime.date(2026, 8, 11),
    ]
    # Todas caen el mismo día de la semana que la fecha original.
    assert all(nombre_dia(f) == "Martes" for f in fechas)
