from pydantic import BaseModel, ConfigDict


class ProductoFamiliaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    descripcion: str
    familia_id: int | None
    familia_desc: str | None
    baja: bool


class CargaCatalogoResumen(BaseModel):
    total_productos: int
    total_familias: int
    sin_familia: int


class FamiliaOut(BaseModel):
    familia_id: int
    familia_desc: str | None
