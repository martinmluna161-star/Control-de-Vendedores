import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class ProyeccionItemIn(BaseModel):
    cliente_codigo: str
    fuera_de_zona: bool = False
    familias_ids: list[int] = []
    observaciones: str | None = None


class ProyeccionDiariaIn(BaseModel):
    fecha: datetime.date
    clientes: list[ProyeccionItemIn]


class ProyeccionDiariaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vendedor_codigo: str
    fecha: datetime.date
    cliente_codigo: str
    fuera_de_zona: bool
    familias_ids: list[int]
    observaciones: str | None


class ProyeccionClienteEquipoOut(BaseModel):
    cliente_codigo: str
    cliente_razon_social: str
    zona_codigo: str | None
    fuera_de_zona: bool
    familias: list[str]
    observaciones: str | None


class ProyeccionVendedorEquipoOut(BaseModel):
    vendedor_codigo: str
    vendedor_nombre: str
    clientes_proyectados: int
    clientes: list[ProyeccionClienteEquipoOut]


class ProyeccionEquipoOut(BaseModel):
    fecha: datetime.date
    vendedores: list[ProyeccionVendedorEquipoOut]
