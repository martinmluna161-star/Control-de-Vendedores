from pydantic import BaseModel, ConfigDict, Field


class ObjetivoIn(BaseModel):
    vendedor_codigo: str
    anio: int = Field(ge=2000, le=2100)
    mes: int = Field(ge=1, le=12)
    monto: float = Field(ge=0)


class ObjetivoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vendedor_codigo: str
    anio: int
    mes: int
    monto: float


class ResumenImportacionOut(BaseModel):
    filas_importadas: int
    vendedores_nuevos: list[str]
    zonas_nuevas: list[str]
    clientes_nuevos: list[str]
    clientes_actualizados: list[str] = []
