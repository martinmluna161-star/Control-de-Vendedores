import datetime
import uuid

from pydantic import BaseModel


class CierreEstructuralIn(BaseModel):
    fecha_corte: datetime.date
    ventas_netas_mes_real: float
    compras_netas_mes_real: float
    ar_bruto: float = 0
    ar_neto: float = 0
    deuda_proveedores: float = 0
    deuda_financiera: float = 0
    saldo_caja_bancos: float


class CierreEstructuralOut(CierreEstructuralIn):
    id: uuid.UUID
    actualizado_en: datetime.datetime


class ParametrosIn(BaseModel):
    pct_cobro_contado: float = 0.70
    dias_cobro_ctacte: int = 7
    credito_total_disponible: float = 0
    umbral_riesgo: float = 5_000_000
    umbral_ajustado: float = 30_000_000


class ParametrosOut(ParametrosIn):
    id: uuid.UUID
    actualizado_en: datetime.datetime


class ProveedorIn(BaseModel):
    nombre: str
    plazo_dias: int | None = None
    forma_pago_habitual: str = "cta_cte"
    confirmado: bool = False


class ProveedorPatch(BaseModel):
    nombre: str | None = None
    plazo_dias: int | None = None
    forma_pago_habitual: str | None = None
    confirmado: bool | None = None


class ProveedorOut(ProveedorIn):
    id: uuid.UUID


class CompraIn(BaseModel):
    fecha_compra: datetime.date
    proveedor_id: uuid.UUID | None = None
    proveedor_nombre: str
    comprobante_numero: str | None = None
    monto: float
    forma_pago: str = "cta_cte"
    # Vencimiento real impreso en la factura, cuando se conoce (pisa el
    # plazo genérico del proveedor). Dejar vacío usa fecha_compra + plazo.
    fecha_vencimiento: datetime.date | None = None
    fecha_pago_real: datetime.date | None = None


class CompraPatch(BaseModel):
    fecha_compra: datetime.date | None = None
    proveedor_id: uuid.UUID | None = None
    proveedor_nombre: str | None = None
    comprobante_numero: str | None = None
    monto: float | None = None
    forma_pago: str | None = None
    fecha_vencimiento: datetime.date | None = None
    fecha_pago_real: datetime.date | None = None


class CompraOut(CompraIn):
    id: uuid.UUID
    # Fecha de pago resuelta (la cargada a mano, el vencimiento real de la
    # factura, o calculada contra el plazo del proveedor). None si es Cta
    # Cte y no hay ninguno de los tres -- queda afuera del cálculo hasta
    # cargar uno.
    fecha_pago_resuelta: datetime.date | None = None


class ChequeIn(BaseModel):
    numero: str | None = None
    proveedor_nombre: str | None = None
    monto: float
    fecha_pago: datetime.date
    estado: str = "pendiente"


class ChequePatch(BaseModel):
    numero: str | None = None
    proveedor_nombre: str | None = None
    monto: float | None = None
    fecha_pago: datetime.date | None = None
    estado: str | None = None


class ChequeOut(ChequeIn):
    id: uuid.UUID


class CuotaBancariaIn(BaseModel):
    banco: str
    nro_cuota: str | None = None
    monto: float
    fecha_vencimiento: datetime.date
    # Apertura opcional capital/interés -- solo la usa el Estado de
    # Resultados mensual (el interés es gasto financiero, el capital no).
    capital_monto: float | None = None
    interes_monto: float | None = None


class CuotaBancariaPatch(BaseModel):
    banco: str | None = None
    nro_cuota: str | None = None
    monto: float | None = None
    fecha_vencimiento: datetime.date | None = None
    capital_monto: float | None = None
    interes_monto: float | None = None


class CuotaBancariaOut(CuotaBancariaIn):
    id: uuid.UUID


class GastoMensualIn(BaseModel):
    anio: int
    mes: int
    sueldos_monto: float = 0
    semana_pago_sueldos: int = 1
    gastos_generales_monto: float = 0
    # Apertura fina opcional para el Estado de Resultados mensual; no la usa
    # el cashflow semanal.
    gastos_variables_monto: float | None = None
    gastos_fijos_monto: float | None = None
    casilla_monto: float | None = None
    ingresos_brutos_monto: float | None = None
    retiros_socios_monto: float | None = None
    iva_monto: float | None = None


class GastoMensualPatch(BaseModel):
    sueldos_monto: float | None = None
    semana_pago_sueldos: int | None = None
    gastos_generales_monto: float | None = None
    gastos_variables_monto: float | None = None
    gastos_fijos_monto: float | None = None
    casilla_monto: float | None = None
    ingresos_brutos_monto: float | None = None
    retiros_socios_monto: float | None = None
    iva_monto: float | None = None


class GastoMensualOut(GastoMensualIn):
    id: uuid.UUID


class ImpuestoIn(BaseModel):
    nombre: str
    monto: float
    fecha_vencimiento: datetime.date
    pagado: bool = False


class ImpuestoPatch(BaseModel):
    nombre: str | None = None
    monto: float | None = None
    fecha_vencimiento: datetime.date | None = None
    pagado: bool | None = None


class ImpuestoOut(ImpuestoIn):
    id: uuid.UUID


class FilaCashflowOut(BaseModel):
    semana_inicio: datetime.date
    ventas_plan: float
    ventas_real: float | None
    ventas_usada: float
    cobro_contado: float
    cobro_ctacte: float
    compras_plan: float
    compras_real: float | None
    compras_usada: float
    pago_proveedores: float
    pago_cheques: float
    cuotas_bancarias: float
    sueldos_y_gastos: float
    total_ingresos: float
    total_egresos: float
    flujo_neto: float
    flujo_acum_bruto: float
    credito_usado: float
    flujo_acum_neto: float
    # Misma mecánica, pero corrida solo con Plan (sin mezclar ningún dato
    # Real) -- sirve para graficar "Acum. Plan" vs "Acum. Real" lado a lado.
    flujo_acum_neto_plan: float
    estado: str


class CashflowKpisOut(BaseModel):
    ventas_ultimo_dia: float | None
    ventas_ultimo_dia_fecha: datetime.date | None
    cobrado_ultimo_dia: float | None
    plata_en_la_calle: float
    plata_en_la_calle_pct_vencido: float | None
    deuda_proveedores: float
    credito_total: float
    credito_usado: float
    credito_disponible: float
    credito_pct_usado: float | None


class CashflowResumenOut(BaseModel):
    kpis: CashflowKpisOut
    filas: list[FilaCashflowOut]


# ---------------- Tablero mensual (Estado de Resultados / Deuda / Cobranzas / Caja / Proyección) ----------------


class EstadoResultadosMesOut(BaseModel):
    anio: int
    mes: int
    etiqueta: str
    tipo: str  # "real" | "estimado" -- para marcar "(est.)" en el frontend
    ventas: float
    costo_mercaderia: float
    margen_bruto: float
    margen_bruto_pct: float | None
    gastos_variables: float | None
    gastos_fijos: float | None
    sueldos_y_cargas: float
    casilla: float | None
    ingresos_brutos: float | None
    retiros_socios: float | None
    iva: float | None
    gastos_operativos: float
    ebitda: float
    ebitda_pct: float | None
    intereses: float
    antes_ganancias: float
    impuesto_ganancias: float
    resultado_neto: float
    cuota_bancaria_mes: float


class VentaEquilibrioOut(BaseModel):
    margen_contribucion_pct: float | None
    costos_fijos_totales: float
    venta_equilibrio: float | None
    pct_de_la_venta: float | None
    faltante: float | None
    venta_equilibrio_con_retiros: float | None


class MensualResumenOut(BaseModel):
    mes: EstadoResultadosMesOut
    venta_equilibrio: VentaEquilibrioOut
    faltan_campos: list[str]


class MensualHistoricoOut(BaseModel):
    meses: list[EstadoResultadosMesOut]


class DeudaPorAcreedorOut(BaseModel):
    acreedor: str
    monto: float
    pct: float


class DeudaCalendarioMesOut(BaseModel):
    anio: int
    mes: int
    etiqueta: str
    cuota_total: float
    ebitda_mes: float | None
    faltante: float | None


class DeudaResumenOut(BaseModel):
    falta_pagar_12_meses: float
    obligaciones_activas: int
    mes_mas_pesado_etiqueta: str | None
    mes_mas_pesado_monto: float | None
    por_acreedor: list[DeudaPorAcreedorOut]
    calendario: list[DeudaCalendarioMesOut]


class AntiguedadTramoOut(BaseModel):
    tramo: str
    clientes: int
    saldo: float
    pct: float


class ProveedorSaldoOut(BaseModel):
    proveedor: str
    saldo: float
    pct: float | None


class MarkupLineaOut(BaseModel):
    id: uuid.UUID
    proveedor_o_linea: str
    markup_pct: float
    margen_pct: float


class MarkupLineaIn(BaseModel):
    proveedor_o_linea: str
    markup_pct: float


class MarkupLineaPatch(BaseModel):
    proveedor_o_linea: str | None = None
    markup_pct: float | None = None


class IIBBSaldoFavorIn(BaseModel):
    fecha_corte: datetime.date
    saldo_a_favor: float
    impuesto_determinado_12m: float = 0
    retenido_12m: float = 0


class IIBBSaldoFavorOut(IIBBSaldoFavorIn):
    id: uuid.UUID


class CobranzasResumenOut(BaseModel):
    le_deben_bruto: float
    le_deben_neto: float
    anticipos_clientes: float
    dudoso_mas_90_dias: float
    dudoso_pct: float | None
    dias_promedio_cartera: float | None
    debe_a_proveedores: float
    le_financian: float
    antiguedad: list[AntiguedadTramoOut]
    proveedores_saldo: list[ProveedorSaldoOut]
    markup_lineas: list[MarkupLineaOut]
    iibb_ultimo: IIBBSaldoFavorOut | None


class CajaMesOut(BaseModel):
    anio: int
    mes: int
    etiqueta: str
    ebitda: float
    retiros_socios: float
    capital_deuda: float
    la_caja_crecio: float
    banco_acumulado: float | None


class CajaResumenOut(BaseModel):
    meses: list[CajaMesOut]


class EscenarioProyeccionIn(BaseModel):
    crecimiento_ventas_mensual: float
    margen_bruto: float
    inflacion_gastos_mensual: float
    alicuota_iva: float = 0.21
    alicuota_ganancias: float = 0.35


class EscenarioProyeccionOut(EscenarioProyeccionIn):
    id: uuid.UUID
    nombre: str


class FilaProyeccionOut(BaseModel):
    anio: int
    mes: int
    etiqueta: str
    ventas: float
    costo_mercaderia: float
    margen_bruto: float
    margen_bruto_pct: float
    gastos_variables: float
    gastos_fijos: float
    sueldos_y_cargas: float
    retiros_socios: float
    casilla: float
    ingresos_brutos: float
    iva: float
    gastos_operativos: float
    ebitda: float
    ebitda_pct: float
    cuota_deuda: float
    intereses_pagados: float
    capital_amortizado: float
    resultado_despues_deuda: float
    antes_ganancias: float
    impuesto_ganancias: float
    resultado_neto: float
    banco_acumulado: float


class ProyeccionResumenOut(BaseModel):
    escenario: str
    supuestos: EscenarioProyeccionOut
    ebitda_total: float
    servicio_deuda_total: float
    cobertura: float | None
    deficit: float
    filas: list[FilaProyeccionOut]
