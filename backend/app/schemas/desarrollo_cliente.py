import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class DesarrolloClienteIn(BaseModel):
    fecha: datetime.date
    nombre_lugar: str = Field(min_length=1, max_length=200)
    zona_codigo: str | None = None
    direccion: str | None = Field(default=None, max_length=300)


class DesarrolloClienteCompletarIn(BaseModel):
    detalle_visita: str = Field(min_length=1, max_length=1000)
    fotos: list[str] = Field(default_factory=list, max_length=10)


class DesarrolloClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vendedor_codigo: str
    vendedor_nombre: str
    fecha: datetime.date
    nombre_lugar: str
    zona_codigo: str | None
    direccion: str | None
    fotos: list[str]
    detalle_visita: str | None
    completado: bool
    creado_en: datetime.datetime
    completado_en: datetime.datetime | None
