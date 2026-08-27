import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, requerir_supervisor
from app.database import get_db
from app.models.cliente import Cliente
from app.models.vendedor import Vendedor
from app.models.visita import VisitaReal
from app.schemas.visita import JornadaVendedorOut, ReporteVisitasOut, VisitaDetalleOut
from app.services.metrics import hora_a_segundos

router = APIRouter(prefix="/visitas", tags=["visitas"])


@router.get("/reporte", response_model=ReporteVisitasOut)
async def reporte_visitas(
    desde: datetime.date = Query(...),
    hasta: datetime.date = Query(...),
    vendedor_codigo: str | None = Query(default=None, description="Filtrar a un solo vendedor"),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Reporte de visitas y eficiencia para supervisión: descarta del conteo
    las visitas de menos de 1 minuto (probable error de carga), detalla las
    de más de 30 minutos para revisar, y arma por vendedor/día el horario de
    inicio y fin de la jornada (primer y último cliente con check-in válido)
    y las horas trabajadas resultantes."""
    stmt = (
        select(VisitaReal, Cliente.razon_social, Vendedor.nombre)
        .join(Cliente, Cliente.codigo == VisitaReal.cliente_codigo)
        .outerjoin(Vendedor, Vendedor.codigo_axum == VisitaReal.vendedor_codigo)
        .where(VisitaReal.fecha.between(desde, hasta))
    )
    if vendedor_codigo:
        stmt = stmt.where(VisitaReal.vendedor_codigo == vendedor_codigo)
    filas = (await db.execute(stmt)).all()

    validas = [f for f in filas if f[0].valida]
    cortas = [f for f in filas if f[0].corta]
    largas = [f for f in filas if f[0].larga]

    grupos: dict[tuple[str, datetime.date], list] = {}
    for visita, razon, vendedor_nombre in validas:
        clave = (visita.vendedor_codigo or "SIN_ASIGNAR", visita.fecha)
        grupos.setdefault(clave, []).append((visita, razon, vendedor_nombre))

    jornadas: list[JornadaVendedorOut] = []
    horas_trabajadas_total = 0.0
    for (vendedor_cod, fecha), items in grupos.items():
        con_horario = [
            (visita, razon, nombre, hora_a_segundos(visita.hora_min), hora_a_segundos(visita.hora_max))
            for visita, razon, nombre in items
        ]
        con_horario = [t for t in con_horario if t[3] is not None and t[4] is not None]
        if not con_horario:
            continue
        apertura = min(con_horario, key=lambda t: t[3])
        cierre = max(con_horario, key=lambda t: t[4])
        horas = round(max(cierre[4] - apertura[3], 0) / 3600, 2)
        horas_trabajadas_total += horas
        jornadas.append(
            JornadaVendedorOut(
                vendedor_codigo=vendedor_cod,
                vendedor_nombre=apertura[2] or f"Vendedor {vendedor_cod}",
                fecha=fecha,
                hora_inicio=apertura[0].hora_min,
                cliente_inicio=apertura[1],
                hora_fin=cierre[0].hora_max,
                cliente_fin=cierre[1],
                visitas=len(items),
                horas_trabajadas=horas,
            )
        )
    jornadas.sort(key=lambda j: (j.vendedor_nombre, j.fecha))

    def _detalle(items: list) -> list[VisitaDetalleOut]:
        return [
            VisitaDetalleOut(
                fecha=visita.fecha,
                cliente_codigo=visita.cliente_codigo,
                cliente_nombre=razon,
                zona_codigo=visita.zona_codigo,
                vendedor_nombre=nombre or "Sin asignar",
                duracion_seg=visita.tiempo_seg,
                hora_min=visita.hora_min,
                hora_max=visita.hora_max,
            )
            for visita, razon, nombre in items
        ]

    detalle_cortas = sorted(_detalle(cortas), key=lambda d: d.fecha)
    detalle_largas = sorted(_detalle(largas), key=lambda d: d.duracion_seg, reverse=True)

    return ReporteVisitasOut(
        desde=desde,
        hasta=hasta,
        total_visitas_validas=len(validas),
        horas_trabajadas_total=round(horas_trabajadas_total, 2),
        visitas_cortas_descartadas=len(cortas),
        visitas_largas_a_revisar=len(largas),
        jornadas=jornadas,
        detalle_cortas=detalle_cortas,
        detalle_largas=detalle_largas,
    )
