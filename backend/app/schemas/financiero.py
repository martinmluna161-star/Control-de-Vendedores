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
    fecha_pago_real: datetime.date | None = None


class CompraPatch(BaseModel):
    fecha_compra: datetime.date | None = None
    proveedor_id: uuid.UUID | None = None
    proveedor_nombre: str | None = None
    comprobante_numero: str | None = None
    monto: float | None = None
    forma_pago: str | None = None
    fecha_pago_real: datetime.date | None = None


class CompraOut(CompraIn):
    id: uuid.UUID
    # Fecha de pago resuelta (la cargada a mano, o calculada contra el
    # plazo del proveedor). None si es Cta Cte y el proveedor no tiene
    # plazo confirmado -- queda afuera del cálculo hasta confirmarlo.
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


class CuotaBancariaPatch(BaseModel):
    banco: str | None = None
    nro_cuota: str | None = None
    monto: float | None = None
    fecha_vencimiento: datetime.date | None = None


class CuotaBancariaOut(CuotaBancariaIn):
    id: uuid.UUID


class GastoMensualIn(BaseModel):
    anio: int
    mes: int
    sueldos_monto: float = 0
    semana_pago_sueldos: int = 1
    gastos_generales_monto: float = 0


class GastoMensualPatch(BaseModel):
    sueldos_monto: float | None = None
    semana_pago_sueldos: int | None = None
    gastos_generales_monto: float | None = None


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
