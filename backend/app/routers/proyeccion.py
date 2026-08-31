import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, get_usuario_actual, requerir_supervisor
from app.database import get_db
from app.models.cliente import Cliente
from app.models.novedad_zona import NovedadZona
from app.models.producto import ProductoFamilia
from app.models.proyeccion import ProyeccionDiaria
from app.models.vendedor import Vendedor
from app.schemas.proyeccion import (
    ProyeccionClienteEquipoOut,
    ProyeccionDiariaIn,
    ProyeccionDiariaOut,
    ProyeccionEquipoOut,
    ProyeccionVendedorEquipoOut,
)

router = APIRouter(prefix="/proyeccion", tags=["proyeccion"])


@router.get("", response_model=list[ProyeccionDiariaOut])
async def obtener_proyeccion(
    fecha: datetime.date,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    result = await db.execute(
        select(ProyeccionDiaria).where(
            ProyeccionDiaria.vendedor_codigo == usuario.vendedor.codigo_axum,
            ProyeccionDiaria.fecha == fecha,
        )
    )
    return result.scalars().all()


@router.get("/equipo", response_model=ProyeccionEquipoOut)
async def obtener_proyeccion_equipo(
    fecha: datetime.date,
    vendedor_codigo: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_supervisor),
):
    """Lo que cada vendedor (o uno puntual) tiene proyectado para una fecha,
    con nombre de cliente/zona/familias ya resueltos -- a diferencia del
    endpoint del propio vendedor, el supervisor no tiene cargado en el
    frontend el caché de clientes/zonas de vendedores ajenos."""
    stmt_vendedores = select(Vendedor).where(Vendedor.activo.is_(True)).order_by(Vendedor.nombre)
    if vendedor_codigo:
        stmt_vendedores = stmt_vendedores.where(Vendedor.codigo_axum == vendedor_codigo)
    vendedores = (await db.execute(stmt_vendedores)).scalars().all()
    codigos = [v.codigo_axum for v in vendedores]

    filas = (
        await db.execute(
            select(ProyeccionDiaria, Cliente.razon_social, Cliente.zona_codigo)
            .join(Cliente, Cliente.codigo == ProyeccionDiaria.cliente_codigo, isouter=True)
            .where(ProyeccionDiaria.vendedor_codigo.in_(codigos), ProyeccionDiaria.fecha == fecha)
        )
    ).all()

    nombres_familia = dict(
        (
            await db.execute(
                select(ProductoFamilia.familia_id, ProductoFamilia.familia_desc).where(
                    ProductoFamilia.familia_id.is_not(None)
                )
            )
        ).all()
    )

    por_vendedor: dict[str, list[ProyeccionClienteEquipoOut]] = {codigo: [] for codigo in codigos}
    for proy, razon_social, zona_codigo in filas:
        por_vendedor[proy.vendedor_codigo].append(
            ProyeccionClienteEquipoOut(
                cliente_codigo=proy.cliente_codigo,
                cliente_razon_social=razon_social or f"Cliente {proy.cliente_codigo}",
                zona_codigo=zona_codigo,
                fuera_de_zona=proy.fuera_de_zona,
                familias=[nombres_familia.get(fid, f"Familia {fid}") for fid in proy.familias_ids],
                observaciones=proy.observaciones,
            )
        )

    vendedores_out = [
        ProyeccionVendedorEquipoOut(
            vendedor_codigo=v.codigo_axum,
            vendedor_nombre=v.nombre,
            clientes_proyectados=len(por_vendedor[v.codigo_axum]),
            clientes=por_vendedor[v.codigo_axum],
        )
        for v in vendedores
    ]
    return ProyeccionEquipoOut(fecha=fecha, vendedores=vendedores_out)


@router.put("", response_model=list[ProyeccionDiariaOut])
async def guardar_proyeccion(
    body: ProyeccionDiariaIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(get_usuario_actual),
):
    """Reemplaza por completo la proyección del vendedor logueado para esa
    fecha (mismo patrón que 'guardarDia' en el backend de zonas/visitas)."""
    vendedor_codigo = usuario.vendedor.codigo_axum

    await db.execute(
        delete(ProyeccionDiaria).where(
            ProyeccionDiaria.vendedor_codigo == vendedor_codigo,
            ProyeccionDiaria.fecha == body.fecha,
        )
    )

    nuevas = [
        ProyeccionDiaria(
            vendedor_codigo=vendedor_codigo,
            fecha=body.fecha,
            cliente_codigo=item.cliente_codigo,
            fuera_de_zona=item.fuera_de_zona,
            familias_ids=item.familias_ids,
            observaciones=item.observaciones,
        )
        for item in body.clientes
    ]
    db.add_all(nuevas)

    # Toda alta fuera de zona genera (o reutiliza) una novedad pendiente para el supervisor.
    for item in body.clientes:
        if not item.fuera_de_zona:
            continue
        ya_existe = await db.execute(
            select(NovedadZona).where(
                NovedadZona.cliente_codigo == item.cliente_codigo,
                NovedadZona.vendedor_codigo == vendedor_codigo,
                NovedadZona.estado == "pendiente",
            )
        )
        if ya_existe.scalar_one_or_none() is None:
            db.add(
                NovedadZona(
                    cliente_codigo=item.cliente_codigo,
                    vendedor_codigo=vendedor_codigo,
                    fecha=body.fecha,
                    estado="pendiente",
                )
            )

    await db.commit()

    result = await db.execute(
        select(ProyeccionDiaria).where(
            ProyeccionDiaria.vendedor_codigo == vendedor_codigo,
            ProyeccionDiaria.fecha == body.fecha,
        )
    )
    return result.scalars().all()
