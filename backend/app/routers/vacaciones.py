import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, requerir_supervisor
from app.database import get_db
from app.models.cliente import Cliente
from app.models.proyeccion import ProyeccionDiaria
from app.models.vacaciones import VacacionesPlan, VacacionesPlanCliente, VacacionesPlanDia
from app.models.vendedor import Vendedor
from app.models.venta import VentaDetalle
from app.models.visita import VisitaReal
from app.models.zona import Zona
from app.schemas.vacaciones import (
    AgregarClienteIn,
    AsignarReemplazoIn,
    VacacionesPlanClienteOut,
    VacacionesPlanDiaOut,
    VacacionesPlanIn,
    VacacionesPlanOut,
    VacacionesPlanResumenOut,
)
from app.services.vacaciones import fechas_de_referencia, fechas_del_rango, nombre_dia, zona_trabaja_ese_dia

router = APIRouter(prefix="/vacaciones", tags=["vacaciones"])


async def _proponer_clientes(
    db: AsyncSession, *, zona_codigo: str, vendedor_codigo: str, fecha
) -> dict[str, tuple[set[str], list[int], str | None]]:
    """Candidatos para un día+zona: la última vez (buscando hacia atrás de a
    semanas enteras) que esa combinación tuvo algún dato entre lo proyectado,
    lo visitado (válido) o lo vendido, unidos en un solo set por cliente."""
    for fecha_ref in fechas_de_referencia(fecha):
        proyectados = (
            await db.execute(
                select(ProyeccionDiaria.cliente_codigo, ProyeccionDiaria.familias_ids, ProyeccionDiaria.observaciones)
                .join(Cliente, Cliente.codigo == ProyeccionDiaria.cliente_codigo)
                .where(
                    ProyeccionDiaria.vendedor_codigo == vendedor_codigo,
                    ProyeccionDiaria.fecha == fecha_ref,
                    Cliente.zona_codigo == zona_codigo,
                )
            )
        ).all()
        visitados = set(
            (
                await db.execute(
                    select(VisitaReal.cliente_codigo).where(
                        VisitaReal.zona_codigo == zona_codigo,
                        VisitaReal.fecha == fecha_ref,
                        VisitaReal.valida.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )
        vendidos = {
            codigo
            for codigo in (
                await db.execute(
                    select(VentaDetalle.cliente_codigo)
                    .join(Cliente, Cliente.codigo == VentaDetalle.cliente_codigo)
                    .where(VentaDetalle.vendedor_codigo == vendedor_codigo, VentaDetalle.fecha == fecha_ref, Cliente.zona_codigo == zona_codigo)
                )
            )
            .scalars()
            .all()
            if codigo is not None
        }

        if not proyectados and not visitados and not vendidos:
            continue

        candidatos: dict[str, tuple[set[str], list[int], str | None]] = {}
        for codigo, familias_ids, observaciones in proyectados:
            candidatos[codigo] = ({"proyectado"}, list(familias_ids or []), observaciones)
        for codigo in visitados:
            if codigo in candidatos:
                candidatos[codigo][0].add("visita")
            else:
                candidatos[codigo] = ({"visita"}, [], None)
        for codigo in vendidos:
            if codigo in candidatos:
                candidatos[codigo][0].add("venta")
            else:
                candidatos[codigo] = ({"venta"}, [], None)
        return candidatos

    return {}


async def _quitar_proyeccion_de_dia(db: AsyncSession, dia: VacacionesPlanDia) -> None:
    if not dia.vendedor_reemplazo_codigo:
        return
    codigos = (
        (await db.execute(select(VacacionesPlanCliente.cliente_codigo).where(VacacionesPlanCliente.plan_dia_id == dia.id)))
        .scalars()
        .all()
    )
    if codigos:
        await db.execute(
            delete(ProyeccionDiaria).where(
                ProyeccionDiaria.vendedor_codigo == dia.vendedor_reemplazo_codigo,
                ProyeccionDiaria.fecha == dia.fecha,
                ProyeccionDiaria.cliente_codigo.in_(codigos),
            )
        )


async def _escribir_proyeccion_de_dia(db: AsyncSession, dia: VacacionesPlanDia, vendedor_codigo: str) -> None:
    clientes = (
        (await db.execute(select(VacacionesPlanCliente).where(VacacionesPlanCliente.plan_dia_id == dia.id)))
        .scalars()
        .all()
    )
    for c in clientes:
        await db.execute(
            pg_insert(ProyeccionDiaria)
            .values(
                vendedor_codigo=vendedor_codigo,
                fecha=dia.fecha,
                cliente_codigo=c.cliente_codigo,
                fuera_de_zona=False,
                familias_ids=c.familias_ids,
                observaciones=c.observaciones,
            )
            .on_conflict_do_update(
                index_elements=["vendedor_codigo", "fecha", "cliente_codigo"],
                set_={"familias_ids": c.familias_ids, "observaciones": c.observaciones, "fuera_de_zona": False},
            )
        )


async def _dia_out(db: AsyncSession, dia: VacacionesPlanDia) -> VacacionesPlanDiaOut:
    zona = await db.get(Zona, dia.zona_codigo)
    reemplazo = await db.get(Vendedor, dia.vendedor_reemplazo_codigo) if dia.vendedor_reemplazo_codigo else None
    filas = (
        await db.execute(
            select(VacacionesPlanCliente, Cliente.razon_social, Cliente.localidad)
            .join(Cliente, Cliente.codigo == VacacionesPlanCliente.cliente_codigo)
            .where(VacacionesPlanCliente.plan_dia_id == dia.id)
            .order_by(Cliente.razon_social)
        )
    ).all()
    clientes = [
        VacacionesPlanClienteOut(
            id=vc.id,
            cliente_codigo=vc.cliente_codigo,
            cliente_razon_social=razon,
            localidad=localidad,
            origenes=vc.origenes,
            familias_ids=vc.familias_ids,
            observaciones=vc.observaciones,
        )
        for vc, razon, localidad in filas
    ]
    return VacacionesPlanDiaOut(
        id=dia.id,
        fecha=dia.fecha,
        zona_codigo=dia.zona_codigo,
        zona_nombre=zona.nombre if zona else dia.zona_codigo,
        vendedor_reemplazo_codigo=dia.vendedor_reemplazo_codigo,
        vendedor_reemplazo_nombre=reemplazo.nombre if reemplazo else None,
        clientes=clientes,
    )


async def _plan_out(db: AsyncSession, plan: VacacionesPlan) -> VacacionesPlanOut:
    vendedor = await db.get(Vendedor, plan.vendedor_codigo)
    dias = (
        (
            await db.execute(
                select(VacacionesPlanDia)
                .where(VacacionesPlanDia.plan_id == plan.id)
                .order_by(VacacionesPlanDia.fecha, VacacionesPlanDia.zona_codigo)
            )
        )
        .scalars()
        .all()
    )
    dias_out = [await _dia_out(db, dia) for dia in dias]
    return VacacionesPlanOut(
        id=plan.id,
        vendedor_codigo=plan.vendedor_codigo,
        vendedor_nombre=vendedor.nombre if vendedor else plan.vendedor_codigo,
        fecha_desde=plan.fecha_desde,
        fecha_hasta=plan.fecha_hasta,
        creado_en=plan.creado_en,
        dias=dias_out,
    )


async def _obtener_dia_o_404(db: AsyncSession, plan_id: uuid.UUID, dia_id: uuid.UUID) -> VacacionesPlanDia:
    dia = await db.get(VacacionesPlanDia, dia_id)
    if dia is None or dia.plan_id != plan_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Día del plan no encontrado")
    return dia


@router.post("/planes", response_model=VacacionesPlanOut, status_code=status.HTTP_201_CREATED)
async def crear_plan(
    body: VacacionesPlanIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Arma el plan de cobertura para el período de vacaciones de un
    vendedor: por cada día del rango, detecta qué zona(s) le tocan según el
    "día de venta" cargado en cada una, y le propone a cada zona los
    clientes de la última vez que se trabajó ese mismo día de la semana
    (proyectado + visitado + vendido). Nada se asigna todavía -- eso se hace
    después, día por zona, con PATCH .../reemplazo."""
    vendedor = await db.get(Vendedor, body.vendedor_codigo)
    if vendedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendedor no encontrado")
    if body.fecha_hasta < body.fecha_desde:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La fecha hasta no puede ser anterior a la fecha desde")

    plan = VacacionesPlan(
        vendedor_codigo=body.vendedor_codigo,
        fecha_desde=body.fecha_desde,
        fecha_hasta=body.fecha_hasta,
        creado_por=usuario.vendedor.codigo_axum,
    )
    db.add(plan)
    await db.flush()

    zonas = (await db.execute(select(Zona).where(Zona.vendedor_codigo == body.vendedor_codigo))).scalars().all()

    for fecha in fechas_del_rango(body.fecha_desde, body.fecha_hasta):
        dia_semana = nombre_dia(fecha)
        for zona in zonas:
            if not zona_trabaja_ese_dia(zona.dia_venta, dia_semana):
                continue
            plan_dia = VacacionesPlanDia(plan_id=plan.id, fecha=fecha, zona_codigo=zona.codigo)
            db.add(plan_dia)
            await db.flush()
            candidatos = await _proponer_clientes(
                db, zona_codigo=zona.codigo, vendedor_codigo=body.vendedor_codigo, fecha=fecha
            )
            for cliente_codigo, (origenes, familias_ids, observaciones) in candidatos.items():
                db.add(
                    VacacionesPlanCliente(
                        plan_dia_id=plan_dia.id,
                        cliente_codigo=cliente_codigo,
                        origenes=sorted(origenes),
                        familias_ids=familias_ids,
                        observaciones=observaciones,
                    )
                )

    await db.commit()
    return await _plan_out(db, plan)


@router.get("/planes", response_model=list[VacacionesPlanResumenOut])
async def listar_planes(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    filas = (
        await db.execute(
            select(VacacionesPlan, Vendedor.nombre)
            .join(Vendedor, Vendedor.codigo_axum == VacacionesPlan.vendedor_codigo)
            .order_by(VacacionesPlan.fecha_desde.desc())
        )
    ).all()
    return [
        VacacionesPlanResumenOut(
            id=p.id,
            vendedor_codigo=p.vendedor_codigo,
            vendedor_nombre=nombre,
            fecha_desde=p.fecha_desde,
            fecha_hasta=p.fecha_hasta,
            creado_en=p.creado_en,
        )
        for p, nombre in filas
    ]


@router.get("/planes/{plan_id}", response_model=VacacionesPlanOut)
async def obtener_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    plan = await db.get(VacacionesPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado")
    return await _plan_out(db, plan)


@router.delete("/planes/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    plan = await db.get(VacacionesPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado")
    dias = (await db.execute(select(VacacionesPlanDia).where(VacacionesPlanDia.plan_id == plan_id))).scalars().all()
    for dia in dias:
        await _quitar_proyeccion_de_dia(db, dia)
    await db.delete(plan)
    await db.commit()


@router.patch("/planes/{plan_id}/dias/{dia_id}/reemplazo", response_model=VacacionesPlanDiaOut)
async def asignar_reemplazo(
    plan_id: uuid.UUID,
    dia_id: uuid.UUID,
    body: AsignarReemplazoIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Asigna (o desasigna, con ``vendedor_reemplazo_codigo: null``) quién
    cubre esta zona ese día. Al asignar, los clientes propuestos/agregados
    para este día+zona se escriben como proyección diaria real de ese
    vendedor para esa fecha -- la ve directo en su pantalla de Proyección.
    Reasignar mueve esa proyección del vendedor anterior al nuevo."""
    dia = await _obtener_dia_o_404(db, plan_id, dia_id)

    if body.vendedor_reemplazo_codigo and body.vendedor_reemplazo_codigo != dia.vendedor_reemplazo_codigo:
        reemplazo = await db.get(Vendedor, body.vendedor_reemplazo_codigo)
        if reemplazo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendedor de reemplazo no encontrado")

    if body.vendedor_reemplazo_codigo != dia.vendedor_reemplazo_codigo:
        await _quitar_proyeccion_de_dia(db, dia)
        dia.vendedor_reemplazo_codigo = body.vendedor_reemplazo_codigo
        if dia.vendedor_reemplazo_codigo:
            await _escribir_proyeccion_de_dia(db, dia, dia.vendedor_reemplazo_codigo)
        await db.commit()

    return await _dia_out(db, dia)


@router.post("/planes/{plan_id}/dias/{dia_id}/clientes", response_model=VacacionesPlanDiaOut, status_code=status.HTTP_201_CREATED)
async def agregar_cliente(
    plan_id: uuid.UUID,
    dia_id: uuid.UUID,
    body: AgregarClienteIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Suma a mano un cliente a la propuesta de este día+zona (cualquier
    cliente, no necesariamente de esta zona -- por si hay que cubrir algo
    puntual). Si el día ya tiene reemplazante asignado, se le agrega también
    a su proyección real de esa fecha."""
    dia = await _obtener_dia_o_404(db, plan_id, dia_id)
    cliente = await db.get(Cliente, body.cliente_codigo)
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    existente = (
        await db.execute(
            select(VacacionesPlanCliente).where(
                VacacionesPlanCliente.plan_dia_id == dia.id, VacacionesPlanCliente.cliente_codigo == body.cliente_codigo
            )
        )
    ).scalar_one_or_none()
    if existente is None:
        db.add(
            VacacionesPlanCliente(
                plan_dia_id=dia.id, cliente_codigo=body.cliente_codigo, origenes=["manual"], familias_ids=[], observaciones=None
            )
        )
    elif "manual" not in existente.origenes:
        existente.origenes = sorted({*existente.origenes, "manual"})

    if dia.vendedor_reemplazo_codigo:
        await db.execute(
            pg_insert(ProyeccionDiaria)
            .values(
                vendedor_codigo=dia.vendedor_reemplazo_codigo,
                fecha=dia.fecha,
                cliente_codigo=body.cliente_codigo,
                fuera_de_zona=False,
                familias_ids=[],
                observaciones=None,
            )
            .on_conflict_do_nothing(index_elements=["vendedor_codigo", "fecha", "cliente_codigo"])
        )

    await db.commit()
    return await _dia_out(db, dia)


@router.delete("/planes/{plan_id}/dias/{dia_id}/clientes/{cliente_codigo}", response_model=VacacionesPlanDiaOut)
async def quitar_cliente(
    plan_id: uuid.UUID,
    dia_id: uuid.UUID,
    cliente_codigo: str,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    dia = await _obtener_dia_o_404(db, plan_id, dia_id)
    await db.execute(
        delete(VacacionesPlanCliente).where(
            VacacionesPlanCliente.plan_dia_id == dia.id, VacacionesPlanCliente.cliente_codigo == cliente_codigo
        )
    )
    if dia.vendedor_reemplazo_codigo:
        await db.execute(
            delete(ProyeccionDiaria).where(
                ProyeccionDiaria.vendedor_codigo == dia.vendedor_reemplazo_codigo,
                ProyeccionDiaria.fecha == dia.fecha,
                ProyeccionDiaria.cliente_codigo == cliente_codigo,
            )
        )
    await db.commit()
    return await _dia_out(db, dia)
