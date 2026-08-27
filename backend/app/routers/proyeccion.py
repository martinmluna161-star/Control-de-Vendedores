import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, get_usuario_actual
from app.database import get_db
from app.models.novedad_zona import NovedadZona
from app.models.proyeccion import ProyeccionDiaria
from app.schemas.proyeccion import ProyeccionDiariaIn, ProyeccionDiariaOut

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
