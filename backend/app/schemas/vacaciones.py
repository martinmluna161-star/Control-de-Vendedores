import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class VacacionesPlanIn(BaseModel):
    vendedor_codigo: str
    fecha_desde: datetime.date
    fecha_hasta: datetime.date


class VacacionesPlanClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cliente_codigo: str
    cliente_razon_social: str
    localidad: str | None
    origenes: list[str]
    familias_ids: list[int]
    observaciones: str | None


class VacacionesPlanDiaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fecha: datetime.date
    zona_codigo: str
    zona_nombre: str
    vendedor_reemplazo_codigo: str | None
    vendedor_reemplazo_nombre: str | None
    clientes: list[VacacionesPlanClienteOut]


class VacacionesPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vendedor_codigo: str
    vendedor_nombre: str
    fecha_desde: datetime.date
    fecha_hasta: datetime.date
    creado_en: datetime.datetime
    dias: list[VacacionesPlanDiaOut]


class VacacionesPlanResumenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vendedor_codigo: str
    vendedor_nombre: str
    fecha_desde: datetime.date
    fecha_hasta: datetime.date
    creado_en: datetime.datetime


class AsignarReemplazoIn(BaseModel):
    vendedor_reemplazo_codigo: str | None = None


class AgregarClienteIn(BaseModel):
    cliente_codigo: str = Field(min_length=1)
