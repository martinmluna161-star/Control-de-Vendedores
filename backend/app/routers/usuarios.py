from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, requerir_admin
from app.database import get_db
from app.models.vendedor import Vendedor
from app.models.zona import Zona
from app.schemas.usuario_admin import UsuarioActualizarIn, UsuarioAdminOut, UsuarioCrearIn
from app.services.supabase_admin import SupabaseAdminError, crear_usuario_auth, enviar_reset_password

router = APIRouter(prefix="/admin/usuarios", tags=["usuarios"])


async def _usuario_out(db: AsyncSession, vendedor: Vendedor) -> UsuarioAdminOut:
    fila = None
    if vendedor.usuario_auth_id is not None:
        result = await db.execute(
            text("select email, last_sign_in_at from auth.users where id = :id"),
            {"id": vendedor.usuario_auth_id},
        )
        fila = result.first()
    return UsuarioAdminOut(
        codigo_axum=vendedor.codigo_axum,
        nombre=vendedor.nombre,
        rol=vendedor.rol,
        activo=vendedor.activo,
        email=fila.email if fila else None,
        ultimo_acceso=fila.last_sign_in_at if fila else None,
    )


@router.get("", response_model=list[UsuarioAdminOut])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    """Listado de cuentas para Gestión de Usuarios: cruza cada vendedor con
    su email y último acceso en Supabase Auth. Exclusivo de admin."""
    result = await db.execute(
        text(
            """
            select v.codigo_axum, v.nombre, v.rol, v.activo, u.email, u.last_sign_in_at
            from vendedores v
            left join auth.users u on u.id = v.usuario_auth_id
            order by v.nombre
            """
        )
    )
    return [
        UsuarioAdminOut(
            codigo_axum=fila.codigo_axum,
            nombre=fila.nombre,
            rol=fila.rol,
            activo=fila.activo,
            email=fila.email,
            ultimo_acceso=fila.last_sign_in_at,
        )
        for fila in result
    ]


@router.post("", response_model=UsuarioAdminOut, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    body: UsuarioCrearIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    """Crea el login en Supabase Auth y el Vendedor correspondiente en un
    solo paso. Si se pasan zonas_codigos, esas zonas (ya existentes) quedan
    reasignadas a este código -- pensado para un rol="vendedor" nuevo."""
    if await db.get(Vendedor, body.codigo_axum) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un usuario con ese código")

    try:
        auth_id = await crear_usuario_auth(body.email, body.password)
    except SupabaseAdminError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"No se pudo crear el login: {exc}"
        ) from exc

    vendedor = Vendedor(
        codigo_axum=body.codigo_axum,
        nombre=body.nombre,
        rol=body.rol,
        usuario_auth_id=auth_id,
        activo=True,
    )
    db.add(vendedor)
    if body.zonas_codigos:
        await db.execute(
            Zona.__table__.update()
            .where(Zona.codigo.in_(body.zonas_codigos))
            .values(vendedor_codigo=body.codigo_axum)
        )
    await db.commit()
    return UsuarioAdminOut(
        codigo_axum=vendedor.codigo_axum,
        nombre=vendedor.nombre,
        rol=vendedor.rol,
        activo=vendedor.activo,
        email=body.email,
        ultimo_acceso=None,
    )


@router.put("/{codigo_axum}", response_model=UsuarioAdminOut)
async def actualizar_usuario(
    codigo_axum: str,
    body: UsuarioActualizarIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    """Cambia nombre/rol/estado de una cuenta existente. Desactivar alcanza
    con activo=false: get_usuario_actual ya bloquea a cualquier vendedor
    inactivo, sin necesidad de tocar nada en Supabase Auth."""
    vendedor = await db.get(Vendedor, codigo_axum)
    if vendedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    if body.nombre is not None:
        vendedor.nombre = body.nombre
    if body.rol is not None:
        vendedor.rol = body.rol
    if body.activo is not None:
        vendedor.activo = body.activo
    await db.commit()
    await db.refresh(vendedor)
    return await _usuario_out(db, vendedor)


@router.post("/{codigo_axum}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def resetear_password(
    codigo_axum: str,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    """Manda el mail estándar de 'restablecer contraseña' de Supabase Auth
    al email que tiene cargado esta cuenta."""
    vendedor = await db.get(Vendedor, codigo_axum)
    if vendedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    result = await db.execute(
        text("select email from auth.users where id = :id"), {"id": vendedor.usuario_auth_id}
    )
    fila = result.first()
    if fila is None or not fila.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta cuenta no tiene login con email")

    try:
        await enviar_reset_password(fila.email)
    except SupabaseAdminError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"No se pudo enviar el mail: {exc}"
        ) from exc
