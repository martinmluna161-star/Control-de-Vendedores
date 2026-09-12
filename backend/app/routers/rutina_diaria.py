import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, requerir_supervisor
from app.database import get_db
from app.models.rutina_diaria import ESTADOS_EJECUCION_RUTINA, RutinaDiariaEjecucion, RutinaDiariaTarea
from app.models.vendedor import Vendedor
from app.schemas.rutina_diaria import (
    RutinaDiariaDiaItemOut,
    RutinaDiariaEjecucionIn,
    RutinaDiariaTareaIn,
    RutinaDiariaTareaOut,
    RutinaDiariaTareaPatch,
)
from app.services.rutina_diaria import filtrar_tareas_del_dia

router = APIRouter(prefix="/rutina-diaria", tags=["rutina-diaria"])


@router.get("/tareas", response_model=list[RutinaDiariaTareaOut])
async def listar_tareas(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Plantilla completa de la hoja de ruta, editable libremente."""
    result = await db.execute(
        select(RutinaDiariaTarea).order_by(RutinaDiariaTarea.hora_inicio, RutinaDiariaTarea.orden)
    )
    return result.scalars().all()


@router.post("/tareas", response_model=RutinaDiariaTareaOut, status_code=status.HTTP_201_CREATED)
async def crear_tarea(
    body: RutinaDiariaTareaIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    tarea = RutinaDiariaTarea(**body.model_dump())
    db.add(tarea)
    await db.commit()
    await db.refresh(tarea)
    return tarea


@router.patch("/tareas/{tarea_id}", response_model=RutinaDiariaTareaOut)
async def editar_tarea(
    tarea_id: uuid.UUID,
    body: RutinaDiariaTareaPatch,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    tarea = await db.get(RutinaDiariaTarea, tarea_id)
    if tarea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(tarea, campo, valor)
    await db.commit()
    await db.refresh(tarea)
    return tarea


@router.delete("/tareas/{tarea_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_tarea(
    tarea_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    tarea = await db.get(RutinaDiariaTarea, tarea_id)
    if tarea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    await db.delete(tarea)
    await db.commit()


def _item_out(
    tarea: RutinaDiariaTarea,
    fecha: datetime.date,
    ejecucion: RutinaDiariaEjecucion | None = None,
    marcado_por_nombre: str | None = None,
) -> RutinaDiariaDiaItemOut:
    return RutinaDiariaDiaItemOut(
        id=tarea.id,
        orden=tarea.orden,
        bloque_horario=tarea.bloque_horario,
        hora_inicio=tarea.hora_inicio,
        hora_fin=tarea.hora_fin,
        dias_semana=tarea.dias_semana,
        tipo_dia_texto=tarea.tipo_dia_texto,
        actividad_principal=tarea.actividad_principal,
        enfoque_detalle=tarea.enfoque_detalle,
        entregables_kpis=tarea.entregables_kpis,
        fecha=fecha,
        estado=ejecucion.estado if ejecucion else None,
        observaciones=ejecucion.observaciones if ejecucion else None,
        marcado_por=ejecucion.marcado_por if ejecucion else None,
        marcado_por_nombre=marcado_por_nombre,
        marcado_en=ejecucion.marcado_en if ejecucion else None,
    )


@router.get("/dia", response_model=list[RutinaDiariaDiaItemOut])
async def hoja_de_ruta_del_dia(
    fecha: datetime.date = Query(default_factory=datetime.date.today),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Hoja de ruta de un día puntual: solo las tareas de la plantilla cuyo
    ``dias_semana`` incluye el día de esa fecha, en orden horario, con el
    estado de ejecución que tengan cargado ese día (o pendiente si no se
    marcó nada todavía)."""
    tareas = (
        (await db.execute(select(RutinaDiariaTarea).order_by(RutinaDiariaTarea.hora_inicio, RutinaDiariaTarea.orden)))
        .scalars()
        .all()
    )
    tareas_del_dia = filtrar_tareas_del_dia(tareas, fecha)
    if not tareas_del_dia:
        return []

    tarea_ids = [t.id for t in tareas_del_dia]
    filas = (
        await db.execute(
            select(RutinaDiariaEjecucion, Vendedor.nombre)
            .outerjoin(Vendedor, Vendedor.codigo_axum == RutinaDiariaEjecucion.marcado_por)
            .where(RutinaDiariaEjecucion.tarea_id.in_(tarea_ids), RutinaDiariaEjecucion.fecha == fecha)
        )
    ).all()
    ejecucion_por_tarea = {e.tarea_id: (e, nombre) for e, nombre in filas}

    return [
        _item_out(t, fecha, *ejecucion_por_tarea.get(t.id, (None, None)))
        for t in tareas_del_dia
    ]


@router.put("/dia/{tarea_id}", response_model=RutinaDiariaDiaItemOut)
async def marcar_ejecucion(
    tarea_id: uuid.UUID,
    body: RutinaDiariaEjecucionIn,
    fecha: datetime.date = Query(...),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Marca (o vuelve a "pendiente" si ``estado`` viene null) el estado de
    una tarea puntual para una fecha: realizada, a replanificar, o no
    realizada."""
    tarea = await db.get(RutinaDiariaTarea, tarea_id)
    if tarea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    if body.estado is not None and body.estado not in ESTADOS_EJECUCION_RUTINA:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estado inválido")

    ejecucion = (
        await db.execute(
            select(RutinaDiariaEjecucion).where(
                RutinaDiariaEjecucion.tarea_id == tarea_id, RutinaDiariaEjecucion.fecha == fecha
            )
        )
    ).scalar_one_or_none()

    if body.estado is None:
        if ejecucion is not None:
            await db.delete(ejecucion)
            await db.commit()
        return _item_out(tarea, fecha)

    if ejecucion is None:
        ejecucion = RutinaDiariaEjecucion(
            tarea_id=tarea_id,
            fecha=fecha,
            estado=body.estado,
            observaciones=body.observaciones,
            marcado_por=usuario.vendedor.codigo_axum,
        )
        db.add(ejecucion)
    else:
        ejecucion.estado = body.estado
        ejecucion.observaciones = body.observaciones
        ejecucion.marcado_por = usuario.vendedor.codigo_axum

    await db.commit()
    await db.refresh(ejecucion)
    return _item_out(tarea, fecha, ejecucion, usuario.vendedor.nombre)
