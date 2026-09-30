import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    codigo: Mapped[str] = mapped_column(String(20), primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    zona_codigo: Mapped[str | None] = mapped_column(String(10), ForeignKey("zonas.codigo"), nullable=True)
    localidad: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Rubro del padrón de Axum (SUPERMERCADOS, ALMACENES, KIOSCOS, etc.) --
    # de acá se deriva el "Tipo de PDV" (AASS/Almacenes) para paneles de
    # cobertura por proveedor como el de QuickFoods.
    ramo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Cuándo se dio de alta en el sistema (no cuándo empezó a comprar en el
    # ERP) -- se usa para resaltarlo como "cliente nuevo" en la proyección
    # durante sus primeros días. Los clientes previos a este campo quedan con
    # una fecha vieja (backfill de la migración), no la de hoy.
    creado_en: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
