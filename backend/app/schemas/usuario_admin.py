import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Rol = Literal["vendedor", "supervisor", "cobranzas", "data_entry", "admin"]


class UsuarioAdminOut(BaseModel):
    codigo_axum: str
    nombre: str
    rol: str
    activo: bool
    email: str | None = None
    ultimo_acceso: datetime.datetime | None = None


class UsuarioCrearIn(BaseModel):
    codigo_axum: str = Field(min_length=1, max_length=10)
    nombre: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6)
    rol: Rol
    # Solo tiene sentido para rol="vendedor": reasigna estas zonas (ya
    # existentes, cargadas por el padrón) a este vendedor nuevo.
    zonas_codigos: list[str] = []


class UsuarioActualizarIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    rol: Rol | None = None
    activo: bool | None = None
