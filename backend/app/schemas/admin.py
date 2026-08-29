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


class ObjetivoSugeridoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vendedor_codigo: str
    anio: int
    mes: int
    objetivo_mes_anterior: float | None
    real_mes_anterior: float | None
    pct_cumplimiento_mes_anterior: float | None
    piso_recuperado: float | None
    crecimiento_aplicado_pct: float | None
    objetivo_sugerido: float
    variacion_vs_objetivo_anterior_pct: float | None


class ResumenObjetivosSugeridosOut(BaseModel):
    anio: int
    mes: int
    filas_importadas: int
