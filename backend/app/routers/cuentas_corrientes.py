from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, get_usuario_actual, requerir_cargador_cc
from app.database import get_db
from app.models.cliente import Cliente
from app.models.cuenta_corriente import CuentaCorrienteCarga, CuentaCorrienteComprobante
from app.models.vendedor import Vendedor
from app.models.zona import Zona
from app.schemas.cuenta_corriente import (
    BitacoraCargaCCOut,
    ClienteCCOut,
    ComprobanteCCOut,
    ResumenCargaCCOut,
)
from app.services.cuentas_corrientes import (
    aplicar_cuenta_corriente,
    buscar_carga_duplicada,
    calcular_hash_archivo,
    parse_cuenta_corriente_xls,
    registrar_carga_duplicada,
    registrar_carga_fallida,
)

router = APIRouter(tags=["cuentas-corrientes"])


async def _importar(
    db: AsyncSession, archivo: UploadFile, tipo_archivo: str, usuario: UsuarioActual
) -> ResumenCargaCCOut:
    contenido = await archivo.read()
    nombre_archivo = archivo.filename or f"cuenta_corriente_{tipo_archivo}.xls"
    contenido_hash = calcular_hash_archivo(contenido)

    # Mismo contenido exacto que una carga ya procesada con éxito: se
    # bloquea antes de tocar nada, para no duplicar comprobantes por un
    # archivo subido dos veces por error.
    duplicada = await buscar_carga_duplicada(db, contenido_hash)
    if duplicada is not None:
        await registrar_carga_duplicada(
            db,
            nombre_archivo=nombre_archivo,
            tipo_archivo=tipo_archivo,
            usuario_auth_id=usuario.auth_id,
            usuario_nombre=usuario.vendedor.nombre,
            contenido_hash=contenido_hash,
            carga_original=duplicada,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Este archivo ya se cargó el {duplicada.creado_en.strftime('%d/%m/%Y %H:%M')} "
                f"como '{duplicada.nombre_archivo}' (por {duplicada.usuario_nombre}). No se volvió a procesar."
            ),
        )

    try:
        carga = parse_cuenta_corriente_xls(contenido, tipo_archivo)
    except ValueError as exc:
        # La bitácora tiene que ver también los intentos fallidos, no solo
        # las cargas exitosas -- por eso se registra antes de devolver el 400.
        await registrar_carga_fallida(
            db,
            nombre_archivo=nombre_archivo,
            tipo_archivo=tipo_archivo,
            usuario_auth_id=usuario.auth_id,
            usuario_nombre=usuario.vendedor.nombre,
            error=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return await aplicar_cuenta_corriente(
        db,
        carga,
        nombre_archivo=nombre_archivo,
        usuario_auth_id=usuario.auth_id,
        usuario_nombre=usuario.vendedor.nombre,
        contenido_hash=contenido_hash,
    )


@router.post("/admin/cuentas-corrientes/importar-vendedor", response_model=ResumenCargaCCOut)
async def importar_cuenta_corriente_vendedor(
    archivo: UploadFile,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_cargador_cc),
):
    """Carga 'Saldos Detallados por cliente y comprobante' de Axum, filtrado
    por vendedor. Nunca reemplaza una carga anterior: cada archivo es una
    foto fechada y la vista de cuenta corriente siempre muestra la más
    reciente por cliente, conservando el historial completo."""
    return await _importar(db, archivo, "vendedor", usuario)


@router.post("/admin/cuentas-corrientes/importar-zona", response_model=ResumenCargaCCOut)
async def importar_cuenta_corriente_zona(
    archivo: UploadFile,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_cargador_cc),
):
    """Igual que /admin/cuentas-corrientes/importar-vendedor, pero para el
    mismo reporte filtrado por zona en vez de por vendedor."""
    return await _importar(db, archivo, "zona", usuario)


@router.get("/admin/cuentas-corrientes/bitacora", response_model=list[BitacoraCargaCCOut])
async def bitacora_cuentas_corrientes(
    limite: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_cargador_cc),
):
    """Auditoría de cargas de cuenta corriente (exitosas y fallidas), más
    recientes primero."""
    result = await db.execute(
        select(CuentaCorrienteCarga).order_by(CuentaCorrienteCarga.creado_en.desc()).limit(limite)
    )
    return result.scalars().all()


def _ultima_carga_por_cliente():
    """Subquery: para cada cliente, el ``carga_id`` de su carga más reciente
    (por ``creado_en``) -- la vista de cuenta corriente es siempre esa foto,
    nunca una mezcla de cargas distintas para el mismo cliente."""
    pares = (
        select(
            CuentaCorrienteComprobante.cliente_codigo.label("cliente_codigo"),
            CuentaCorrienteComprobante.carga_id.label("carga_id"),
            CuentaCorrienteCarga.creado_en.label("creado_en"),
        )
        .join(CuentaCorrienteCarga, CuentaCorrienteCarga.id == CuentaCorrienteComprobante.carga_id)
        .distinct()
        .subquery()
    )
    rankeado = (
        select(
            pares.c.cliente_codigo,
            pares.c.carga_id,
            pares.c.creado_en,
            func.row_number()
            .over(partition_by=pares.c.cliente_codigo, order_by=pares.c.creado_en.desc())
            .label("rn"),
        )
    ).subquery()
    return (
        select(rankeado.c.cliente_codigo, rankeado.c.carga_id, rankeado.c.creado_en)
        .where(rankeado.c.rn == 1)
        .subquery()
    )


@router.get("/cuentas-corrientes", response_model=list[ClienteCCOut])
async def listar_cuentas_corrientes(
    vendedor_codigo: str | None = Query(
        default=None, description="Solo supervisor/admin: ver la cartera de un solo vendedor"
    ),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Cuenta corriente vigente por cliente (encabezado + comprobantes),
    siempre con la carga más reciente de cada uno. El vendedor solo ve los
    clientes de sus zonas ACTUALES (resueltas en vivo contra clientes/zonas,
    no contra la foto de vendedor/zona guardada en el momento de la carga,
    para reflejar reasignaciones de zona posteriores); supervisor/admin ven
    todo, opcionalmente filtrado a un vendedor puntual."""
    if not (vendedor_codigo and usuario.es_supervisor):
        vendedor_codigo = None if usuario.es_supervisor else usuario.vendedor.codigo_axum

    ultimo = _ultima_carga_por_cliente()
    stmt = (
        select(
            CuentaCorrienteComprobante,
            Cliente.zona_codigo.label("zona_actual"),
            Zona.vendedor_codigo.label("vendedor_actual"),
            Vendedor.nombre.label("vendedor_nombre"),
            ultimo.c.creado_en.label("carga_fecha"),
        )
        .join(
            ultimo,
            (ultimo.c.cliente_codigo == CuentaCorrienteComprobante.cliente_codigo)
            & (ultimo.c.carga_id == CuentaCorrienteComprobante.carga_id),
        )
        .outerjoin(Cliente, Cliente.codigo == CuentaCorrienteComprobante.cliente_codigo)
        .outerjoin(Zona, Zona.codigo == Cliente.zona_codigo)
        .outerjoin(Vendedor, Vendedor.codigo_axum == Zona.vendedor_codigo)
    )
    if vendedor_codigo:
        stmt = stmt.where(Zona.vendedor_codigo == vendedor_codigo)

    filas = (await db.execute(stmt)).all()

    por_cliente: dict[str, ClienteCCOut] = {}
    for comp, zona_actual, vendedor_actual, vendedor_nombre, carga_fecha in filas:
        cliente_out = por_cliente.get(comp.cliente_codigo)
        if cliente_out is None:
            cliente_out = ClienteCCOut(
                cliente_codigo=comp.cliente_codigo,
                cliente_razon_social=comp.cliente_razon_social,
                cliente_direccion=comp.cliente_direccion,
                zona_codigo=zona_actual,
                vendedor_codigo=vendedor_actual,
                vendedor_nombre=vendedor_nombre,
                monto_total_adeudado=float(comp.monto_total_cliente),
                carga_fecha=carga_fecha,
                comprobantes=[],
            )
            por_cliente[comp.cliente_codigo] = cliente_out
        if comp.comprobante_numero is not None or comp.comprobante_tipo is not None:
            cliente_out.comprobantes.append(
                ComprobanteCCOut(
                    comprobante_numero=comp.comprobante_numero,
                    comprobante_tipo=comp.comprobante_tipo,
                    fecha_comprobante=comp.fecha_comprobante,
                    fecha_vencimiento=comp.fecha_vencimiento,
                    monto=float(comp.monto),
                    es_interes=comp.es_interes,
                    fecha_interes=comp.fecha_interes,
                    nd_numero=comp.nd_numero,
                    detalle_interes=comp.detalle_interes,
                )
            )

    return sorted(por_cliente.values(), key=lambda c: c.monto_total_adeudado, reverse=True)
