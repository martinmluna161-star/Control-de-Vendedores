from pydantic import BaseModel


class CoberturaFamiliaOut(BaseModel):
    familia_id: int | None
    familia_desc: str | None
    monto: float
    porcentaje: float


class SellerDashboardOut(BaseModel):
    anio: int
    mes: int
    monto_objetivo: float | None
    monto_real: float
    avance_objetivo_pct: float | None
    clientes_proyectados: int
    visitas_efectivas: int
    efectividad_ruta_pct: float | None
    cobertura_por_familia: list[CoberturaFamiliaOut]


class VendedorResumenOut(BaseModel):
    vendedor_codigo: str
    nombre: str
    monto_objetivo: float | None
    monto_real: float
    avance_objetivo_pct: float | None
    visitas_proyectadas: int
    visitas_efectivas: int
    efectividad_ruta_pct: float | None
    ventas_concretadas: int
    ratio_conversion_pct: float | None


class MatrizFamiliaOut(BaseModel):
    familia_id: int | None
    familia_desc: str | None
    monto_vendido: float
    veces_proyectada: int


class EquipoResumenOut(BaseModel):
    monto_objetivo_total: float
    monto_real_total: float
    avance_objetivo_pct: float | None


class Supervisor360Out(BaseModel):
    anio: int
    mes: int
    equipo: EquipoResumenOut
    vendedores: list[VendedorResumenOut]
    matriz_familia: list[MatrizFamiliaOut]
