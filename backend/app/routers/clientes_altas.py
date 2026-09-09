import datetime
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, get_usuario_actual, requerir_supervisor
from app.database import get_db
from app.models.cliente_alta import SolicitudAltaCliente
from app.models.zona import Zona
from app.schemas.cliente_alta import SolicitudAltaClienteOut
from app.services.clientes_altas import campos_faltantes, esta_completo
from app.services.email import enviar_email

router = APIRouter(prefix="/clientes-altas", tags=["clientes-altas"])

# "administración" para este módulo: recepción, Gauna y Ezequiel (depósito).
EMAILS_ADMINISTRACION = (
    "recepcion.congeladospuntanos@gmail.com",
    "jgauna.congeladospuntanos@gmail.com",
    "ezecuri@hotmail.com.ar",
)

def _out(s: SolicitudAltaCliente) -> SolicitudAltaClienteOut:
    return SolicitudAltaClienteOut(
        id=s.id,
        fecha=s.fecha,
        razon_social=s.razon_social,
        direccion=s.direccion,
        zona_codigo=s.zona_codigo,
        condicion_iva=s.condicion_iva,
        cuit_cuil=s.cuit_cuil,
        ingresos_brutos_numero=s.ingresos_brutos_numero,
        ramo=s.ramo,
        telefono=s.telefono,
        email=s.email,
        horario=s.horario,
        observaciones=s.observaciones,
        tiene_constancia_iva=bool(s.constancia_iva_archivo),
        constancia_iva_nombre=s.constancia_iva_nombre,
        tiene_constancia_ingresos_brutos=bool(s.constancia_ingresos_brutos_archivo),
        constancia_ingresos_brutos_nombre=s.constancia_ingresos_brutos_nombre,
        completo=s.completo,
        completado_en=s.completado_en,
        creado_por=s.creado_por,
        creado_en=s.creado_en,
        faltantes=campos_faltantes(s),
    )


async def _aplicar_adjunto(db: AsyncSession, solicitud: SolicitudAltaCliente, campo: str, archivo: UploadFile | None):
    if archivo is None:
        return
    contenido = await archivo.read()
    if not contenido:
        return
    setattr(solicitud, f"constancia_{campo}_archivo", contenido)
    setattr(solicitud, f"constancia_{campo}_nombre", archivo.filename)
    setattr(solicitud, f"constancia_{campo}_tipo", archivo.content_type)


async def _validar_zona(db: AsyncSession, zona_codigo: str | None) -> None:
    if zona_codigo and (await db.get(Zona, zona_codigo)) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zona no encontrada")


async def _avisar_nueva_carga(solicitud: SolicitudAltaCliente, vendedor_nombre: str) -> None:
    faltantes = campos_faltantes(solicitud)
    estado = "Completa" if not faltantes else f"Pendiente — falta: {', '.join(faltantes)}"
    await enviar_email(
        list(EMAILS_ADMINISTRACION),
        asunto=f"Alta de cliente nuevo — {solicitud.razon_social} (carga {vendedor_nombre})",
        cuerpo=(
            f"Vendedor: {vendedor_nombre}\n"
            f"Fecha: {solicitud.fecha}\n"
            f"Razón social: {solicitud.razon_social}\n"
            f"Dirección: {solicitud.direccion or '—'}\n"
            f"Zona: {solicitud.zona_codigo or '—'}\n"
            f"Condición IVA: {solicitud.condicion_iva or '—'}\n"
            f"CUIT/CUIL: {solicitud.cuit_cuil or '—'}\n"
            f"Ingresos Brutos: {solicitud.ingresos_brutos_numero or '—'}\n"
            f"Ramo: {solicitud.ramo or '—'}\n"
            f"Teléfono: {solicitud.telefono or '—'}\n"
            f"Email: {solicitud.email or '—'}\n"
            f"Horario: {solicitud.horario or '—'}\n"
            f"Observaciones: {solicitud.observaciones or '—'}\n\n"
            f"Estado: {estado}"
        ),
    )


async def _enviar_cortesia_cliente(solicitud: SolicitudAltaCliente) -> None:
    if not solicitud.email:
        return
    await enviar_email(
        [solicitud.email],
        asunto="Alta exitosa en Congelados Puntanos",
        cuerpo=(
            f"Estimado/a {solicitud.razon_social}:\n\n"
            "Le confirmamos que su alta como cliente en Congelados Puntanos fue exitosa. "
            "Próximamente le enviaremos novedades por este canal.\n\n"
            "Saludos,\nCongelados Puntanos"
        ),
    )


@router.post("", response_model=SolicitudAltaClienteOut, status_code=status.HTTP_201_CREATED)
async def crear_alta_cliente(
    razon_social: str = Form(...),
    direccion: str | None = Form(None),
    zona_codigo: str | None = Form(None),
    condicion_iva: str | None = Form(None),
    cuit_cuil: str | None = Form(None),
    ingresos_brutos_numero: str | None = Form(None),
    ramo: str | None = Form(None),
    telefono: str | None = Form(None),
    email: str | None = Form(None),
    horario: str | None = Form(None),
    observaciones: str | None = Form(None),
    constancia_iva: UploadFile | None = File(None),
    constancia_ingresos_brutos: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """El vendedor carga el alta de un cliente nuevo. Se avisa siempre por
    mail a administración apenas se carga -- si falta algún dato o adjunto
    obligatorio, la carga queda "pendiente" y sigue apareciendo como tal
    hasta que se complete (ver PATCH). Al quedar completa se le manda un
    mail de cortesía al cliente."""
    await _validar_zona(db, zona_codigo)

    solicitud = SolicitudAltaCliente(
        fecha=datetime.date.today(),
        razon_social=razon_social,
        direccion=direccion,
        zona_codigo=zona_codigo,
        condicion_iva=condicion_iva,
        cuit_cuil=cuit_cuil,
        ingresos_brutos_numero=ingresos_brutos_numero,
        ramo=ramo,
        telefono=telefono,
        email=email,
        horario=horario,
        observaciones=observaciones,
        creado_por=usuario.vendedor.codigo_axum,
    )
    await _aplicar_adjunto(db, solicitud, "iva", constancia_iva)
    await _aplicar_adjunto(db, solicitud, "ingresos_brutos", constancia_ingresos_brutos)

    solicitud.completo = esta_completo(solicitud)
    if solicitud.completo:
        solicitud.completado_en = datetime.datetime.now(datetime.timezone.utc)

    db.add(solicitud)
    await db.commit()
    await db.refresh(solicitud)

    await _avisar_nueva_carga(solicitud, usuario.vendedor.nombre)
    if solicitud.completo and not solicitud.mail_cortesia_enviado:
        await _enviar_cortesia_cliente(solicitud)
        solicitud.mail_cortesia_enviado = True
        await db.commit()
        await db.refresh(solicitud)

    return _out(solicitud)


@router.get("", response_model=list[SolicitudAltaClienteOut])
async def listar_altas_cliente(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Bandeja de altas de clientes nuevos para supervisor/admin, más
    recientes primero -- las pendientes de completar quedan visibles acá
    hasta que se terminen de cargar."""
    result = await db.execute(select(SolicitudAltaCliente).order_by(SolicitudAltaCliente.creado_en.desc()))
    return [_out(s) for s in result.scalars().all()]


@router.get("/mias", response_model=list[SolicitudAltaClienteOut])
async def listar_mis_altas_cliente(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Altas de clientes que cargó el propio vendedor, para que pueda
    retomar y completar las que quedaron pendientes."""
    result = await db.execute(
        select(SolicitudAltaCliente)
        .where(SolicitudAltaCliente.creado_por == usuario.vendedor.codigo_axum)
        .order_by(SolicitudAltaCliente.creado_en.desc())
    )
    return [_out(s) for s in result.scalars().all()]


async def _obtener_alta_con_permiso(
    db: AsyncSession, alta_id: uuid.UUID, usuario: UsuarioActual
) -> SolicitudAltaCliente:
    solicitud = await db.get(SolicitudAltaCliente, alta_id)
    if solicitud is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alta no encontrada")
    if not usuario.es_supervisor and solicitud.creado_por != usuario.vendedor.codigo_axum:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No podés ver esta alta")
    return solicitud


@router.patch("/{alta_id}", response_model=SolicitudAltaClienteOut)
async def completar_alta_cliente(
    alta_id: uuid.UUID,
    razon_social: str | None = Form(None),
    direccion: str | None = Form(None),
    zona_codigo: str | None = Form(None),
    condicion_iva: str | None = Form(None),
    cuit_cuil: str | None = Form(None),
    ingresos_brutos_numero: str | None = Form(None),
    ramo: str | None = Form(None),
    telefono: str | None = Form(None),
    email: str | None = Form(None),
    horario: str | None = Form(None),
    observaciones: str | None = Form(None),
    constancia_iva: UploadFile | None = File(None),
    constancia_ingresos_brutos: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Completa o corrige una carga pendiente: solo el vendedor que la cargó
    o supervisor/admin. Si con esto queda completa, dispara el mail de
    cortesía al cliente (una sola vez)."""
    solicitud = await _obtener_alta_con_permiso(db, alta_id, usuario)

    if razon_social is not None:
        solicitud.razon_social = razon_social
    if zona_codigo is not None:
        await _validar_zona(db, zona_codigo)
        solicitud.zona_codigo = zona_codigo
    for campo, valor in {
        "direccion": direccion,
        "condicion_iva": condicion_iva,
        "cuit_cuil": cuit_cuil,
        "ingresos_brutos_numero": ingresos_brutos_numero,
        "ramo": ramo,
        "telefono": telefono,
        "email": email,
        "horario": horario,
        "observaciones": observaciones,
    }.items():
        if valor is not None:
            setattr(solicitud, campo, valor)

    await _aplicar_adjunto(db, solicitud, "iva", constancia_iva)
    await _aplicar_adjunto(db, solicitud, "ingresos_brutos", constancia_ingresos_brutos)

    ya_estaba_completo = solicitud.completo
    solicitud.completo = esta_completo(solicitud)
    if solicitud.completo and not ya_estaba_completo:
        solicitud.completado_en = datetime.datetime.now(datetime.timezone.utc)

    await db.commit()
    await db.refresh(solicitud)

    if solicitud.completo and not solicitud.mail_cortesia_enviado:
        await _enviar_cortesia_cliente(solicitud)
        solicitud.mail_cortesia_enviado = True
        await db.commit()
        await db.refresh(solicitud)

    return _out(solicitud)


@router.get("/{alta_id}/adjunto/{campo}")
async def descargar_adjunto_alta_cliente(
    alta_id: uuid.UUID,
    campo: str,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    if campo not in ("iva", "ingresos_brutos"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjunto no encontrado")
    solicitud = await _obtener_alta_con_permiso(db, alta_id, usuario)
    contenido = getattr(solicitud, f"constancia_{campo}_archivo")
    if not contenido:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Esta alta no tiene ese adjunto cargado")
    tipo = getattr(solicitud, f"constancia_{campo}_tipo") or "application/octet-stream"
    nombre = getattr(solicitud, f"constancia_{campo}_nombre") or "adjunto"
    return Response(
        content=contenido,
        media_type=tipo,
        headers={"Content-Disposition": f'inline; filename="{nombre}"'},
    )
