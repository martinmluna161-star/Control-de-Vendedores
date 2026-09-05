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


def _ultima_carga_por_vendedor():
    """Subquery: para cada vendedor (resuelto EN VIVO vía la zona actual del
    cliente, no la foto guardada al cargar), el ``carga_id`` de la carga más
    reciente que tocó a alguno de sus clientes.

    La cuenta corriente se actualiza en el ERP y acá solo se sube lo
    pendiente ese día: cuando entra un archivo nuevo para un vendedor, TODO
    lo de una carga anterior de ese vendedor queda superado -- no solo los
    clientes que se repiten. Por eso se agrupa por vendedor y no por
    cliente: si hoy Lorena tiene 5 clientes en el archivo nuevo (de los 10
    que tenía antes), tiene que ver esos 5 y ninguno de los otros 5 viejos."""
    resueltas = (
        select(
            CuentaCorrienteComprobante.carga_id.label("carga_id"),
            Zona.vendedor_codigo.label("vendedor_resuelto"),
            CuentaCorrienteCarga.creado_en.label("creado_en"),
        )
        .join(CuentaCorrienteCarga, CuentaCorrienteCarga.id == CuentaCorrienteComprobante.carga_id)
        .outerjoin(Cliente, Cliente.codigo == CuentaCorrienteComprobante.cliente_codigo)
        .outerjoin(Zona, Zona.codigo == Cliente.zona_codigo)
        .distinct()
        .subquery()
    )
    rankeado = (
        select(
            resueltas.c.vendedor_resuelto,
            resueltas.c.carga_id,
            func.row_number()
            .over(partition_by=resueltas.c.vendedor_resuelto, order_by=resueltas.c.creado_en.desc())
            .label("rn"),
        )
    ).subquery()
    return (
        select(rankeado.c.vendedor_resuelto, rankeado.c.carga_id)
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
    siempre con la carga más reciente DE CADA VENDEDOR (no del cliente
    individual): el archivo que se sube es la foto completa de lo pendiente
    de ese vendedor ese día, así que una carga nueva reemplaza en pantalla
    a TODOS los clientes de la carga anterior de ese vendedor, aparezcan o
    no en la nueva. El vendedor solo ve los clientes de sus zonas ACTUALES
    (resueltas en vivo contra clientes/zonas, no contra la foto guardada al
    cargar, para reflejar reasignaciones de zona posteriores); supervisor/
    admin ven todo, opcionalmente filtrado a un vendedor puntual."""
    if not (vendedor_codigo and usuario.es_supervisor):
        vendedor_codigo = None if usuario.es_supervisor else usuario.vendedor.codigo_axum

    ultimo = _ultima_carga_por_vendedor()
    stmt = (
        select(
            CuentaCorrienteComprobante,
            Cliente.zona_codigo.label("zona_actual"),
            Zona.vendedor_codigo.label("vendedor_actual"),
            Vendedor.nombre.label("vendedor_nombre"),
            CuentaCorrienteCarga.creado_en.label("carga_fecha"),
        )
        .join(CuentaCorrienteCarga, CuentaCorrienteCarga.id == CuentaCorrienteComprobante.carga_id)
        .outerjoin(Cliente, Cliente.codigo == CuentaCorrienteComprobante.cliente_codigo)
        .outerjoin(Zona, Zona.codigo == Cliente.zona_codigo)
        .outerjoin(Vendedor, Vendedor.codigo_axum == Zona.vendedor_codigo)
        .join(
            ultimo,
            (ultimo.c.carga_id == CuentaCorrienteComprobante.carga_id)
            & ultimo.c.vendedor_resuelto.is_not_distinct_from(Zona.vendedor_codigo),
        )
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

    def _clave_orden(cliente: ClienteCCOut) -> tuple[int, int | str]:
        try:
            return (0, int(cliente.cliente_codigo))
        except ValueError:
            return (1, cliente.cliente_codigo)

    return sorted(por_cliente.values(), key=_clave_orden)
