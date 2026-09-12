import datetime

from app.models.rutina_diaria import RutinaDiariaTarea
from app.services.vacaciones import nombre_dia


def tarea_aplica(dias_semana: list[str] | None, fecha: datetime.date) -> bool:
    return nombre_dia(fecha) in (dias_semana or [])


def filtrar_tareas_del_dia(tareas: list[RutinaDiariaTarea], fecha: datetime.date) -> list[RutinaDiariaTarea]:
    return [t for t in tareas if tarea_aplica(t.dias_semana, fecha)]
