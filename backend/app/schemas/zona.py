from pydantic import BaseModel, ConfigDict


class ZonaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    nombre: str
    vendedor_codigo: str | None
    dia_venta: str
    dia_entrega: str
