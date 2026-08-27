import datetime

from pydantic import BaseModel


class JornadaVendedorOut(BaseModel):
    vendedor_codigo: str
    vendedor_nombre: str
    fecha: datetime.date
    hora_inicio: str
    cliente_inicio: str
    hora_fin: str
    cliente_fin: str
    visitas: int
    horas_trabajadas: float


class VisitaDetalleOut(BaseModel):
    fecha: datetime.date
    cliente_codigo: str
    cliente_nombre: str
    zona_codigo: str
    vendedor_nombre: str
    duracion_seg: int
    hora_min: str | None
    hora_max: str | None


class ReporteVisitasOut(BaseModel):
    desde: datetime.date
    hasta: datetime.date
    total_visitas_validas: int
    horas_trabajadas_total: float
    visitas_cortas_descartadas: int
    visitas_largas_a_revisar: int
    jornadas: list[JornadaVendedorOut]
    detalle_cortas: list[VisitaDetalleOut]
    detalle_largas: list[VisitaDetalleOut]
