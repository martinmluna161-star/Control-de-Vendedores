import datetime
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

MARCAS_FREEZER = ("frigor", "mccain", "paty")


class ClienteFreezer(Base):
    """Cliente con freezer puesto por una marca (Frigor/McCain/Paty), según el
    informe de ranking de compras que carga administración. Un cliente puede
    tener freezers de más de una marca. Se usa en la pantalla de proyección
    para que el vendedor sepa qué productos ofrecerle según de quién es el
    freezer que tiene puesto."""

    __tablename__ = "clientes_freezers"
    __table_args__ = (UniqueConstraint("cliente_codigo", "marca", name="uq_cliente_freezer_marca"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_codigo: Mapped[str] = mapped_column(String(20), ForeignKey("clientes.codigo"), nullable=False)
    marca: Mapped[str] = mapped_column(String(10), nullable=False)  # frigor | mccain | paty
    cantidad_freezers: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    detalle_equipos: Mapped[str | None] = mapped_column(Text, nullable=True)
    ramo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    total_facturado: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    meses_activos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ultima_compra: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    ranking: Mapped[int | None] = mapped_column(Integer, nullable=True)
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
