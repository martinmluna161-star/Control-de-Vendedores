import datetime
import uuid

from pydantic import BaseModel, ConfigDict


class ProyeccionItemIn(BaseModel):
    cliente_codigo: str
    fuera_de_zona: bool = False


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
