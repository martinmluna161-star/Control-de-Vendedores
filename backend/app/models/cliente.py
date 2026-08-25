from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    codigo: Mapped[str] = mapped_column(String(20), primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    zona_codigo: Mapped[str | None] = mapped_column(String(10), ForeignKey("zonas.codigo"), nullable=True)
    localidad: Mapped[str | None] = mapped_column(String(120), nullable=True)
