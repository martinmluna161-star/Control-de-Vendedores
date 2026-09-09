import datetime
import uuid

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

CONDICIONES_IVA = ("responsable_inscripto", "monotributo", "exento", "consumidor_final")


class SolicitudAltaCliente(Base):
    """Alta de un cliente nuevo cargada por un vendedor desde el módulo de
    gestión de clientes. Si falta algún dato obligatorio o el adjunto
    correspondiente, la carga queda "pendiente" hasta que se complete y se
    le sigue recordando a supervisor/admin en la bitácora de información. Al
    completarse se le manda un mail de cortesía al cliente."""

    __tablename__ = "clientes_altas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fecha: Mapped[datetime.date] = mapped_column(Date, nullable=False, server_default=func.current_date())

    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    direccion: Mapped[str | None] = mapped_column(String(300), nullable=True)
    zona_codigo: Mapped[str | None] = mapped_column(String(10), ForeignKey("zonas.codigo"), nullable=True)
    condicion_iva: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cuit_cuil: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ingresos_brutos_numero: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ramo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    horario: Mapped[str | None] = mapped_column(String(120), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    constancia_iva_archivo: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    constancia_iva_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    constancia_iva_tipo: Mapped[str | None] = mapped_column(String(100), nullable=True)

    constancia_ingresos_brutos_archivo: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    constancia_ingresos_brutos_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    constancia_ingresos_brutos_tipo: Mapped[str | None] = mapped_column(String(100), nullable=True)

    completo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completado_en: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mail_cortesia_enviado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    creado_por: Mapped[str] = mapped_column(String(10), ForeignKey("vendedores.codigo_axum"), nullable=False)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
