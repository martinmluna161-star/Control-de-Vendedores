from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import UsuarioActual, get_usuario_actual
from app.config import settings
from app.routers import (
    admin,
    clientes,
    comunicados,
    dashboard,
    desarrollo_cliente,
    productos,
    proyeccion,
    visitas,
    zonas,
)
from app.schemas.vendedor import VendedorOut

app = FastAPI(title="Control de Vendedores API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(zonas.router)
app.include_router(clientes.router)
app.include_router(proyeccion.router)
app.include_router(productos.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(visitas.router)
app.include_router(comunicados.router)
app.include_router(desarrollo_cliente.router)


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/me", response_model=VendedorOut)
async def me(usuario: UsuarioActual = Depends(get_usuario_actual)):
    return usuario.vendedor
