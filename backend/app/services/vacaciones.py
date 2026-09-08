"""Lógica de armado del plan de cobertura de vacaciones: qué zonas le tocan
al vendedor que se va cada día del período, y qué clientes proponerle al
reemplazante en base a la última vez que se trabajó esa zona ese mismo día
de la semana (unión de lo proyectado, lo visitado y lo vendido)."""

import datetime

DIAS_SEMANA_ES = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")

# Cuántas semanas hacia atrás se busca una ocurrencia con datos del mismo
# día de semana, si la semana inmediata anterior no tiene nada cargado.
OFFSETS_SEMANAS_REFERENCIA = (7, 14, 21, 28)


def nombre_dia(fecha: datetime.date) -> str:
    return DIAS_SEMANA_ES[fecha.weekday()]


def zona_trabaja_ese_dia(dia_venta: str | None, nombre_dia_buscado: str) -> bool:
    """``dia_venta`` guarda uno o más días separados por "/" (ej. "Lunes/Jueves").
    Vacío o None = la zona no tiene día de venta cargado, no se cubre."""
    dias = [d.strip() for d in (dia_venta or "").split("/") if d.strip()]
    return nombre_dia_buscado in dias


def fechas_del_rango(fecha_desde: datetime.date, fecha_hasta: datetime.date) -> list[datetime.date]:
    if fecha_hasta < fecha_desde:
        return []
    cantidad_dias = (fecha_hasta - fecha_desde).days + 1
    return [fecha_desde + datetime.timedelta(days=i) for i in range(cantidad_dias)]


def fechas_de_referencia(fecha: datetime.date) -> list[datetime.date]:
    """Candidatas (de la más a la menos reciente) para basar la propuesta:
    la misma fecha, retrocedida de a una semana. Quien llama se queda con la
    primera que tenga algún dato cargado."""
    return [fecha - datetime.timedelta(days=offset) for offset in OFFSETS_SEMANAS_REFERENCIA]
