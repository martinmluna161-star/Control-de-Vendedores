import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Vendedor(Base):
    __tablename__ = "vendedores"

    # Código Axum: el mismo identificador que ya se usa en la Base de zonas
    # y en los reportes de ventas/visitas (ej. "26", "36").
    codigo_axum: Mapped[str] = mapped_column(String(10), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False, default="vendedor")
    # id del usuario en Supabase Auth (auth.users.id). Nulo hasta que se le crea el login.
    usuario_auth_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, unique=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
