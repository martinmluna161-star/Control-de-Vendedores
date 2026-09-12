import datetime
import uuid

from pydantic import BaseModel


class RutinaDiariaTareaIn(BaseModel):
    orden: int = 0
    bloque_horario: str
    hora_inicio: str
    hora_fin: str
    dias_semana: list[str] = []
    tipo_dia_texto: str = ""
    actividad_principal: str
    enfoque_detalle: str | None = None
    entregables_kpis: str | None = None


class RutinaDiariaTareaPatch(BaseModel):
    orden: int | None = None
    bloque_horario: str | None = None
    hora_inicio: str | None = None
    hora_fin: str | None = None
    dias_semana: list[str] | None = None
    tipo_dia_texto: str | None = None
    actividad_principal: str | None = None
    enfoque_detalle: str | None = None
    entregables_kpis: str | None = None


class RutinaDiariaTareaOut(BaseModel):
    id: uuid.UUID
    orden: int
    bloque_horario: str
    hora_inicio: str
    hora_fin: str
    dias_semana: list[str]
    tipo_dia_texto: str
    actividad_principal: str
    enfoque_detalle: str | None = None
    entregables_kpis: str | None = None


class RutinaDiariaEjecucionIn(BaseModel):
    estado: str | None = None  # null = volver a "pendiente"
    observaciones: str | None = None


class RutinaDiariaDiaItemOut(RutinaDiariaTareaOut):
    fecha: datetime.date
    estado: str | None = None
    observaciones: str | None = None
    marcado_por: str | None = None
    marcado_por_nombre: str | None = None
    marcado_en: datetime.datetime | None = None
