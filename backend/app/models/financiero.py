import datetime
import uuid

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

FORMAS_PAGO_PROVEEDOR = ("cta_cte", "cheque", "contado")
ESTADOS_CHEQUE = ("pendiente", "pagado", "anulado")


class FinancieroCierreEstructural(Base):
    """Punto de partida fijo del cashflow: foto de la situación a una fecha
    de corte. No se recalcula semana a semana -- si se necesita "re-anclar"
    el modelo más adelante, se edita esta misma fila (PUT), lo que corre el
    día 0 de la proyección hacia esa nueva fecha."""

    __tablename__ = "financiero_cierre_estructural"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fecha_corte: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    ventas_netas_mes_real: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    compras_netas_mes_real: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    ar_bruto: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    ar_neto: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    deuda_proveedores: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    deuda_financiera: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    # El dato más crítico del modelo (sección 2.6): sin esto, el acumulado
    # arranca de $0 y todo el resto de la proyección queda artificialmente
    # pesimista.
    saldo_caja_bancos: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    actualizado_en: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FinancieroParametros(Base):
    """Parámetros generales del modelo -- fila única, editable."""

    __tablename__ = "financiero_parametros"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pct_cobro_contado: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.70)
    dias_cobro_ctacte: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    credito_total_disponible: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    umbral_riesgo: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=5_000_000)
    umbral_ajustado: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=30_000_000)
    actualizado_en: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FinancieroProveedor(Base):
    """Plazo de pago pactado por proveedor, para poder calcular la fecha de
    pago real de cada factura automáticamente. Si ``confirmado`` es False,
    el proveedor queda excluido del cálculo automático hasta confirmar el
    dato -- nunca se inventa un plazo."""

    __tablename__ = "financiero_proveedores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    plazo_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    forma_pago_habitual: Mapped[str] = mapped_column(String(20), nullable=False, default="cta_cte")
    confirmado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FinancieroCompra(Base):
    """Una fila por comprobante de compra. La fecha de pago se resuelve en
    este orden: ``fecha_pago_real`` (ya se pagó, dato definitivo) >
    ``fecha_vencimiento`` (vencimiento real impreso en la factura, cuando se
    conoce y no coincide con el plazo parejo del proveedor) > plazo del
    proveedor (fecha_compra + plazo_dias, el fallback genérico) -- salvo que
    la forma de pago sea cheque, en cuyo caso manda el cronograma real de
    FinancieroCheque, no ninguna de estas fechas."""

    __tablename__ = "financiero_compras"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fecha_compra: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    proveedor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financiero_proveedores.id"), nullable=True
    )
    proveedor_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    comprobante_numero: Mapped[str | None] = mapped_column(String(60), nullable=True)
    monto: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    forma_pago: Mapped[str] = mapped_column(String(20), nullable=False, default="cta_cte")
    # Vencimiento real de la factura, cuando se conoce puntualmente (pisa el
    # plazo genérico del proveedor, pero no una fecha_pago_real ya cargada).
    fecha_vencimiento: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    # Si es null y forma_pago no es cheque, se calcula en el momento contra
    # fecha_vencimiento o el plazo del proveedor; se puede fijar a mano para
    # un caso puntual (ej. ya se pagó anticipado).
    fecha_pago_real: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FinancieroCheque(Base):
    """Cronograma real de cheques diferidos (fuente: eCheq del banco). La
    fecha de pago acá SIEMPRE manda por sobre cualquier estimación por plazo
    pactado -- puede no tener relación directa con una compra puntual
    (puede ser una refinanciación de deuda vieja)."""

    __tablename__ = "financiero_cheques"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero: Mapped[str | None] = mapped_column(String(60), nullable=True)
    proveedor_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    monto: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    fecha_pago: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FinancieroCuotaBancaria(Base):
    """Cronograma de cuotas de un préstamo ya desembolsado (capital+interés
    conocido) -- distinto de una línea de crédito disponible todavía no
    usada, que se maneja como colchón vía FinancieroParametros."""

    __tablename__ = "financiero_cuotas_bancarias"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    banco: Mapped[str] = mapped_column(String(120), nullable=False)
    nro_cuota: Mapped[str | None] = mapped_column(String(40), nullable=True)
    monto: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    fecha_vencimiento: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FinancieroGastoMensual(Base):
    """Gastos fijos/variables de un mes, con sueldos separado del resto
    (los sueldos se pagan de una sola vez en ``semana_pago_sueldos``, el
    resto se prorratea parejo entre semanas)."""

    __tablename__ = "financiero_gastos_mensuales"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    mes: Mapped[int] = mapped_column(Integer, nullable=False)
    sueldos_monto: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    # 1 = primera semana del mes (la más habitual), 2 = segunda, etc.
    semana_pago_sueldos: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    gastos_generales_monto: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FinancieroImpuesto(Base):
    """Impuesto con su fecha de vencimiento real -- sin fecha no se puede
    ubicar en ninguna semana, así que este campo es obligatorio."""

    __tablename__ = "financiero_impuestos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    monto: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    fecha_vencimiento: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    pagado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
