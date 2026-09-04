import datetime
import uuid

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CuentaCorrienteCarga(Base):
    """Bitácora de cada archivo de Cuenta Corriente (por vendedor o por zona)
    subido desde Axum: quién lo cargó, cuándo, cuántos registros trajo y a
    qué vendedores/zonas quedó asignada la información."""

    __tablename__ = "cuentas_corrientes_cargas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    usuario_auth_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    usuario_nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(String(300), nullable=False)
    tipo_archivo: Mapped[str] = mapped_column(String(20), nullable=False)  # "vendedor" | "zona"
    filtro_original: Mapped[str | None] = mapped_column(String(300), nullable=True)
    cantidad_registros: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clientes_procesados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vendedores_codigos: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    zonas_codigos: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)  # "exitoso" | "error"
    detalle_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class CuentaCorrienteComprobante(Base):
    """Línea de comprobante (o interés) de una carga de Cuenta Corriente.

    ``monto_total_cliente`` repite, en cada línea del cliente, el saldo total
    tal cual figura en el encabezado del archivo fuente -- no se recalcula
    sumando las líneas, porque el ERP puede aplicar pagos/ajustes a nivel de
    cuenta que no siempre bajan como comprobantes individuales."""

    __tablename__ = "cuentas_corrientes_comprobantes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    carga_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cuentas_corrientes_cargas.id", ondelete="CASCADE"), nullable=False
    )
    cliente_codigo: Mapped[str] = mapped_column(String(20), ForeignKey("clientes.codigo"), nullable=False)
    cliente_razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    cliente_direccion: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Zona/vendedor resueltos AL MOMENTO DE LA CARGA (foto para la bitácora).
    # La vista del vendedor resuelve la visibilidad en vivo contra
    # clientes/zonas, para reflejar reasignaciones de zona posteriores.
    zona_codigo: Mapped[str | None] = mapped_column(String(10), ForeignKey("zonas.codigo"), nullable=True)
    vendedor_codigo: Mapped[str | None] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=True)
    monto_total_cliente: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    # Nulo cuando el cliente no tiene ningún comprobante detallado en el
    # archivo (solo trae su saldo consolidado) -- esta fila existe para no
    # perder ese monto, no representa un documento real.
    comprobante_numero: Mapped[str | None] = mapped_column(String(40), nullable=True)
    comprobante_tipo: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fecha_comprobante: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    fecha_vencimiento: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    monto: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    es_interes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fecha_interes: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    nd_numero: Mapped[str | None] = mapped_column(String(40), nullable=True)
    detalle_interes: Mapped[str | None] = mapped_column(String(300), nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
