from pydantic import BaseModel, ConfigDict


class VendedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo_axum: str
    nombre: str
    rol: str
    activo: bool
