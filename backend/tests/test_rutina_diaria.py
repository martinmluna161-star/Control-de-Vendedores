import datetime

from app.models.rutina_diaria import RutinaDiariaTarea
from app.services.rutina_diaria import filtrar_tareas_del_dia, tarea_aplica


def _tarea(dias_semana, **overrides):
    datos = dict(
        orden=1,
        bloque_horario="Bloque",
        hora_inicio="08:00",
        hora_fin="09:00",
        dias_semana=dias_semana,
        tipo_dia_texto="",
        actividad_principal="Actividad",
    )
    datos.update(overrides)
    return RutinaDiariaTarea(**datos)


def test_tarea_aplica_el_dia_correcto():
    martes = datetime.date(2026, 9, 8)  # confirmado martes
    assert tarea_aplica(["Martes", "Jueves"], martes) is True
    assert tarea_aplica(["Lunes", "Miércoles", "Viernes"], martes) is False


def test_tarea_aplica_sin_dias_es_false():
    lunes = datetime.date(2026, 9, 7)
    assert tarea_aplica([], lunes) is False
    assert tarea_aplica(None, lunes) is False


def test_filtrar_tareas_del_dia_separa_variantes_del_mismo_horario():
    lunes = datetime.date(2026, 9, 7)
    martes = datetime.date(2026, 9, 8)
    reunion_grupal = _tarea(["Lunes", "Miércoles", "Viernes"], bloque_horario="Gestión de Equipo")
    coaching = _tarea(["Martes", "Jueves"], bloque_horario="Gestión de Equipo")

    assert filtrar_tareas_del_dia([reunion_grupal, coaching], lunes) == [reunion_grupal]
    assert filtrar_tareas_del_dia([reunion_grupal, coaching], martes) == [coaching]


def test_filtrar_tareas_del_dia_sin_coincidencias():
    domingo = datetime.date(2026, 9, 13)
    tarea = _tarea(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
    assert filtrar_tareas_del_dia([tarea], domingo) == []
