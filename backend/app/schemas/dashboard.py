import datetime

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
    monto_objetivo_semanal: float | None
    monto_objetivo_diario: float | None
    monto_real: float
    avance_objetivo_pct: float | None
    clientes_proyectados: int
    visitas_efectivas: int
    efectividad_ruta_pct: float | None
    cobertura_por_familia: list[CoberturaFamiliaOut]
    ventas_ayer: float
    horas_trabajadas_ayer: float | None


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
    ventas_hoy: float
    clientes_proyectados_periodo: int
    clientes_visitados_periodo: int
    clientes_con_venta_periodo: int
    pct_proyectado_visitado: float | None
    pct_visitado_vendio: float | None
    pct_proyectado_vendio: float | None


class ObservacionProyeccionOut(BaseModel):
    vendedor_codigo: str
    vendedor_nombre: str
    fecha: datetime.date
    cliente_codigo: str
    cliente_razon_social: str | None
    observaciones: str


class ClienteSinVisitarOut(BaseModel):
    vendedor_codigo: str
    vendedor_nombre: str
    cliente_codigo: str
    cliente_razon_social: str
    zona_codigo: str


class MatrizFamiliaOut(BaseModel):
    familia_id: int | None
    familia_desc: str | None
    monto_vendido: float
    veces_proyectada: int


class EquipoResumenOut(BaseModel):
    monto_objetivo_total: float
    monto_real_total: float
    avance_objetivo_pct: float | None
    ventas_hoy_total: float


class Supervisor360Out(BaseModel):
    anio: int
    mes: int
    equipo: EquipoResumenOut
    vendedores: list[VendedorResumenOut]
    matriz_familia: list[MatrizFamiliaOut]
    observaciones: list[ObservacionProyeccionOut]
    clientes_sin_visitar: list[ClienteSinVisitarOut]
