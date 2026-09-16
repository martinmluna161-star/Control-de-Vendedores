import dataclasses
import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import UsuarioActual, requerir_admin
from app.database import get_db
from app.models.cliente import Cliente
from app.models.cuenta_corriente import CuentaCorrienteCarga, CuentaCorrienteComprobante
from app.models.financiero import (
    FinancieroCheque,
    FinancieroCierreEstructural,
    FinancieroCompra,
    FinancieroCuotaBancaria,
    FinancieroGastoMensual,
    FinancieroImpuesto,
    FinancieroParametros,
    FinancieroProveedor,
)
from app.models.objetivo import ObjetivoMensual
from app.models.venta import VentaDetalle
from app.models.zona import Zona
from app.routers.cuentas_corrientes import LIMITE_CODIGO_CLIENTE_EMPLEADO, _ultima_carga_por_vendedor, _vendedor_resuelto_expr
from app.services.cuentas_corrientes import calcular_vencido_por_vencer
from app.schemas.financiero import (
    CashflowKpisOut,
    CashflowResumenOut,
    ChequeIn,
    ChequeOut,
    ChequePatch,
    CierreEstructuralIn,
    CierreEstructuralOut,
    CompraIn,
    CompraOut,
    CompraPatch,
    CuotaBancariaIn,
    CuotaBancariaOut,
    CuotaBancariaPatch,
    FilaCashflowOut,
    GastoMensualIn,
    GastoMensualOut,
    GastoMensualPatch,
    ImpuestoIn,
    ImpuestoOut,
    ImpuestoPatch,
    ParametrosIn,
    ParametrosOut,
    ProveedorIn,
    ProveedorOut,
    ProveedorPatch,
)
from app.services.financiero import (
    calcular_cashflow_semanal,
    construir_ventas_plan_semanal,
    fecha_pago_compra,
    gastos_generales_semanal,
    lunes_de_semana,
    monto_plan_semanal,
    semanas_del_rango,
)

router = APIRouter(prefix="/financiero", tags=["financiero"])


# ---------------- Cierre estructural (singleton) ----------------


@router.get("/cierre-estructural", response_model=CierreEstructuralOut | None)
async def obtener_cierre_estructural(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    return (await db.execute(select(FinancieroCierreEstructural).limit(1))).scalar_one_or_none()


@router.put("/cierre-estructural", response_model=CierreEstructuralOut)
async def guardar_cierre_estructural(
    body: CierreEstructuralIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    """Fila única: si no existe la crea, si existe la reemplaza (esto es lo
    que hay que usar para "re-anclar" el modelo contra un saldo de banco más
    reciente)."""
    cierre = (await db.execute(select(FinancieroCierreEstructural).limit(1))).scalar_one_or_none()
    if cierre is None:
        cierre = FinancieroCierreEstructural(**body.model_dump())
        db.add(cierre)
    else:
        for campo, valor in body.model_dump().items():
            setattr(cierre, campo, valor)
    await db.commit()
    await db.refresh(cierre)
    return cierre


# ---------------- Parámetros (singleton) ----------------


@router.get("/parametros", response_model=ParametrosOut)
async def obtener_parametros(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    parametros = (await db.execute(select(FinancieroParametros).limit(1))).scalar_one_or_none()
    if parametros is None:
        parametros = FinancieroParametros()
        db.add(parametros)
        await db.commit()
        await db.refresh(parametros)
    return parametros


@router.put("/parametros", response_model=ParametrosOut)
async def guardar_parametros(
    body: ParametrosIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    parametros = (await db.execute(select(FinancieroParametros).limit(1))).scalar_one_or_none()
    if parametros is None:
        parametros = FinancieroParametros(**body.model_dump())
        db.add(parametros)
    else:
        for campo, valor in body.model_dump().items():
            setattr(parametros, campo, valor)
    await db.commit()
    await db.refresh(parametros)
    return parametros


# ---------------- Proveedores (plazo de pago) ----------------


@router.get("/proveedores", response_model=list[ProveedorOut])
async def listar_proveedores(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    result = await db.execute(select(FinancieroProveedor).order_by(FinancieroProveedor.nombre))
    return result.scalars().all()


@router.post("/proveedores", response_model=ProveedorOut, status_code=status.HTTP_201_CREATED)
async def crear_proveedor(
    body: ProveedorIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    existente = (
        await db.execute(select(FinancieroProveedor).where(FinancieroProveedor.nombre == body.nombre))
    ).scalar_one_or_none()
    if existente is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un proveedor con ese nombre")
    proveedor = FinancieroProveedor(**body.model_dump())
    db.add(proveedor)
    await db.commit()
    await db.refresh(proveedor)
    return proveedor


@router.patch("/proveedores/{proveedor_id}", response_model=ProveedorOut)
async def editar_proveedor(
    proveedor_id: uuid.UUID,
    body: ProveedorPatch,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    proveedor = await db.get(FinancieroProveedor, proveedor_id)
    if proveedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(proveedor, campo, valor)
    await db.commit()
    await db.refresh(proveedor)
    return proveedor


@router.delete("/proveedores/{proveedor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_proveedor(
    proveedor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    proveedor = await db.get(FinancieroProveedor, proveedor_id)
    if proveedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    await db.delete(proveedor)
    await db.commit()


# ---------------- Compras ----------------


async def _resolver_fecha_pago_compra(db: AsyncSession, compra: FinancieroCompra) -> datetime.date | None:
    if compra.fecha_pago_real is not None:
        return compra.fecha_pago_real
    if compra.forma_pago == "cheque":
        # Manda el cronograma real del banco (FinancieroCheque), no una
        # fecha estimada acá -- se resuelve en el motor de cashflow.
        return None
    if compra.forma_pago == "contado":
        return compra.fecha_compra
    if compra.fecha_vencimiento is not None:
        # Vencimiento real de la factura: pisa el plazo genérico del
        # proveedor cuando se conoce puntualmente.
        return compra.fecha_vencimiento
    proveedor = await db.get(FinancieroProveedor, compra.proveedor_id) if compra.proveedor_id else None
    if proveedor is None:
        proveedor = (
            await db.execute(select(FinancieroProveedor).where(FinancieroProveedor.nombre == compra.proveedor_nombre))
        ).scalar_one_or_none()
    if proveedor is None or not proveedor.confirmado or proveedor.plazo_dias is None:
        return None
    return fecha_pago_compra(compra.fecha_compra, proveedor.plazo_dias)


def _compra_out(compra: FinancieroCompra, fecha_resuelta: datetime.date | None) -> CompraOut:
    return CompraOut(
        id=compra.id,
        fecha_compra=compra.fecha_compra,
        proveedor_id=compra.proveedor_id,
        proveedor_nombre=compra.proveedor_nombre,
        comprobante_numero=compra.comprobante_numero,
        monto=float(compra.monto),
        forma_pago=compra.forma_pago,
        fecha_vencimiento=compra.fecha_vencimiento,
        fecha_pago_real=compra.fecha_pago_real,
        fecha_pago_resuelta=fecha_resuelta,
    )


@router.get("/compras", response_model=list[CompraOut])
async def listar_compras(
    desde: datetime.date | None = Query(default=None),
    hasta: datetime.date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    stmt = select(FinancieroCompra).order_by(FinancieroCompra.fecha_compra.desc())
    if desde:
        stmt = stmt.where(FinancieroCompra.fecha_compra >= desde)
    if hasta:
        stmt = stmt.where(FinancieroCompra.fecha_compra <= hasta)
    compras = (await db.execute(stmt)).scalars().all()
    salida = []
    for compra in compras:
        fecha_resuelta = await _resolver_fecha_pago_compra(db, compra)
        salida.append(_compra_out(compra, fecha_resuelta))
    return salida


@router.post("/compras", response_model=CompraOut, status_code=status.HTTP_201_CREATED)
async def crear_compra(
    body: CompraIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    compra = FinancieroCompra(**body.model_dump())
    db.add(compra)
    await db.commit()
    await db.refresh(compra)
    fecha_resuelta = await _resolver_fecha_pago_compra(db, compra)
    return _compra_out(compra, fecha_resuelta)


@router.patch("/compras/{compra_id}", response_model=CompraOut)
async def editar_compra(
    compra_id: uuid.UUID,
    body: CompraPatch,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    compra = await db.get(FinancieroCompra, compra_id)
    if compra is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compra no encontrada")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(compra, campo, valor)
    await db.commit()
    await db.refresh(compra)
    fecha_resuelta = await _resolver_fecha_pago_compra(db, compra)
    return _compra_out(compra, fecha_resuelta)


@router.delete("/compras/{compra_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_compra(
    compra_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    compra = await db.get(FinancieroCompra, compra_id)
    if compra is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compra no encontrada")
    await db.delete(compra)
    await db.commit()


# ---------------- Cheques ----------------


@router.get("/cheques", response_model=list[ChequeOut])
async def listar_cheques(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    result = await db.execute(select(FinancieroCheque).order_by(FinancieroCheque.fecha_pago))
    return result.scalars().all()


@router.post("/cheques", response_model=ChequeOut, status_code=status.HTTP_201_CREATED)
async def crear_cheque(
    body: ChequeIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    cheque = FinancieroCheque(**body.model_dump())
    db.add(cheque)
    await db.commit()
    await db.refresh(cheque)
    return cheque


@router.patch("/cheques/{cheque_id}", response_model=ChequeOut)
async def editar_cheque(
    cheque_id: uuid.UUID,
    body: ChequePatch,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    cheque = await db.get(FinancieroCheque, cheque_id)
    if cheque is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cheque no encontrado")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(cheque, campo, valor)
    await db.commit()
    await db.refresh(cheque)
    return cheque


@router.delete("/cheques/{cheque_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_cheque(
    cheque_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    cheque = await db.get(FinancieroCheque, cheque_id)
    if cheque is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cheque no encontrado")
    await db.delete(cheque)
    await db.commit()


# ---------------- Cuotas bancarias ----------------


@router.get("/cuotas-bancarias", response_model=list[CuotaBancariaOut])
async def listar_cuotas_bancarias(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    result = await db.execute(select(FinancieroCuotaBancaria).order_by(FinancieroCuotaBancaria.fecha_vencimiento))
    return result.scalars().all()


@router.post("/cuotas-bancarias", response_model=CuotaBancariaOut, status_code=status.HTTP_201_CREATED)
async def crear_cuota_bancaria(
    body: CuotaBancariaIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    cuota = FinancieroCuotaBancaria(**body.model_dump())
    db.add(cuota)
    await db.commit()
    await db.refresh(cuota)
    return cuota


@router.patch("/cuotas-bancarias/{cuota_id}", response_model=CuotaBancariaOut)
async def editar_cuota_bancaria(
    cuota_id: uuid.UUID,
    body: CuotaBancariaPatch,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    cuota = await db.get(FinancieroCuotaBancaria, cuota_id)
    if cuota is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuota no encontrada")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(cuota, campo, valor)
    await db.commit()
    await db.refresh(cuota)
    return cuota


@router.delete("/cuotas-bancarias/{cuota_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_cuota_bancaria(
    cuota_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    cuota = await db.get(FinancieroCuotaBancaria, cuota_id)
    if cuota is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuota no encontrada")
    await db.delete(cuota)
    await db.commit()


# ---------------- Gastos mensuales ----------------


@router.get("/gastos-mensuales", response_model=list[GastoMensualOut])
async def listar_gastos_mensuales(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    result = await db.execute(
        select(FinancieroGastoMensual).order_by(FinancieroGastoMensual.anio.desc(), FinancieroGastoMensual.mes.desc())
    )
    return result.scalars().all()


@router.post("/gastos-mensuales", response_model=GastoMensualOut, status_code=status.HTTP_201_CREATED)
async def crear_gasto_mensual(
    body: GastoMensualIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    existente = (
        await db.execute(
            select(FinancieroGastoMensual).where(
                FinancieroGastoMensual.anio == body.anio, FinancieroGastoMensual.mes == body.mes
            )
        )
    ).scalar_one_or_none()
    if existente is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una carga para ese mes")
    gasto = FinancieroGastoMensual(**body.model_dump())
    db.add(gasto)
    await db.commit()
    await db.refresh(gasto)
    return gasto


@router.patch("/gastos-mensuales/{gasto_id}", response_model=GastoMensualOut)
async def editar_gasto_mensual(
    gasto_id: uuid.UUID,
    body: GastoMensualPatch,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    gasto = await db.get(FinancieroGastoMensual, gasto_id)
    if gasto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gasto mensual no encontrado")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(gasto, campo, valor)
    await db.commit()
    await db.refresh(gasto)
    return gasto


@router.delete("/gastos-mensuales/{gasto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_gasto_mensual(
    gasto_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    gasto = await db.get(FinancieroGastoMensual, gasto_id)
    if gasto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gasto mensual no encontrado")
    await db.delete(gasto)
    await db.commit()


# ---------------- Impuestos ----------------


@router.get("/impuestos", response_model=list[ImpuestoOut])
async def listar_impuestos(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    result = await db.execute(select(FinancieroImpuesto).order_by(FinancieroImpuesto.fecha_vencimiento))
    return result.scalars().all()


@router.post("/impuestos", response_model=ImpuestoOut, status_code=status.HTTP_201_CREATED)
async def crear_impuesto(
    body: ImpuestoIn,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    impuesto = FinancieroImpuesto(**body.model_dump())
    db.add(impuesto)
    await db.commit()
    await db.refresh(impuesto)
    return impuesto


@router.patch("/impuestos/{impuesto_id}", response_model=ImpuestoOut)
async def editar_impuesto(
    impuesto_id: uuid.UUID,
    body: ImpuestoPatch,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    impuesto = await db.get(FinancieroImpuesto, impuesto_id)
    if impuesto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Impuesto no encontrado")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(impuesto, campo, valor)
    await db.commit()
    await db.refresh(impuesto)
    return impuesto


@router.delete("/impuestos/{impuesto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_impuesto(
    impuesto_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    impuesto = await db.get(FinancieroImpuesto, impuesto_id)
    if impuesto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Impuesto no encontrado")
    await db.delete(impuesto)
    await db.commit()


# ---------------- Motor de cashflow ----------------


async def _kpis(db: AsyncSession, parametros: FinancieroParametros) -> CashflowKpisOut:
    ultima_venta = (
        await db.execute(select(func.max(VentaDetalle.fecha)))
    ).scalar_one_or_none()
    ventas_ultimo_dia = None
    if ultima_venta is not None:
        ventas_ultimo_dia = float(
            (
                await db.execute(
                    select(func.coalesce(func.sum(VentaDetalle.importe), 0)).where(VentaDetalle.fecha == ultima_venta)
                )
            ).scalar_one()
        )

    # "Plata en la calle": mismo criterio que /cuentas-corrientes (última
    # carga por vendedor, resuelta en vivo), pero acá se suma todo -- es una
    # vista de administración, no de cartera por vendedor.
    ultimo = _ultima_carga_por_vendedor()
    vendedor_resuelto = _vendedor_resuelto_expr()
    codigo_numerico = CuentaCorrienteComprobante.cliente_codigo.op("~")(r"^\d+$")
    stmt = (
        select(CuentaCorrienteComprobante)
        .join(CuentaCorrienteCarga, CuentaCorrienteCarga.id == CuentaCorrienteComprobante.carga_id)
        .outerjoin(Cliente, Cliente.codigo == CuentaCorrienteComprobante.cliente_codigo)
        .outerjoin(Zona, Zona.codigo == Cliente.zona_codigo)
        .join(
            ultimo,
            (ultimo.c.carga_id == CuentaCorrienteComprobante.carga_id)
            & ultimo.c.vendedor_resuelto.is_not_distinct_from(vendedor_resuelto),
        )
        .where(
            ~codigo_numerico
            | (cast(CuentaCorrienteComprobante.cliente_codigo, Integer) <= LIMITE_CODIGO_CLIENTE_EMPLEADO)
        )
    )
    filas = (await db.execute(stmt)).scalars().all()
    por_cliente_total: dict[str, float] = {}
    por_cliente_comprobantes: dict[str, list] = {}
    for comp in filas:
        por_cliente_total[comp.cliente_codigo] = float(comp.monto_total_cliente)
        if comp.comprobante_numero is not None or comp.comprobante_tipo is not None:
            por_cliente_comprobantes.setdefault(comp.cliente_codigo, []).append(comp)

    hoy = datetime.date.today()
    plata_en_la_calle = sum(por_cliente_total.values())
    vencido_total = 0.0
    for codigo, total in por_cliente_total.items():
        comprobantes = por_cliente_comprobantes.get(codigo, [])
        if comprobantes:
            vencido, _ = calcular_vencido_por_vencer(comprobantes, hoy)
            vencido_total += vencido
    pct_vencido = (vencido_total / plata_en_la_calle) if plata_en_la_calle else None

    # Deuda a proveedores: provisorio -- suma de compras cargadas cuya fecha
    # de pago (resuelta) todavía no llegó, o no se pudo resolver todavía.
    # OJO: esto NO es "todo lo facturado", según la advertencia del cliente
    # de no asumir facturado = deuda pendiente.
    compras = (await db.execute(select(FinancieroCompra))).scalars().all()
    deuda_proveedores = 0.0
    for compra in compras:
        fecha_resuelta = await _resolver_fecha_pago_compra(db, compra)
        if fecha_resuelta is None or fecha_resuelta >= hoy:
            deuda_proveedores += float(compra.monto)

    credito_total = float(parametros.credito_total_disponible)
    # El crédito usado real hoy sale de la última fila del motor de
    # cashflow hasta la fecha de hoy -- se resuelve en /financiero/cashflow,
    # acá solo se informa el total configurado.
    return CashflowKpisOut(
        ventas_ultimo_dia=ventas_ultimo_dia,
        ventas_ultimo_dia_fecha=ultima_venta,
        cobrado_ultimo_dia=None,
        plata_en_la_calle=plata_en_la_calle,
        plata_en_la_calle_pct_vencido=pct_vencido,
        deuda_proveedores=deuda_proveedores,
        credito_total=credito_total,
        credito_usado=0.0,
        credito_disponible=credito_total,
        credito_pct_usado=None,
    )


@router.get("/cashflow", response_model=CashflowResumenOut)
async def obtener_cashflow(
    semanas: int = Query(default=13, ge=1, le=52),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    """El motor de la sección 2.6: arma la tabla semanal completa al vuelo,
    combinando ventas reales (ya cargadas), compras/cheques/cuotas/gastos
    cargados en este módulo, y el cierre estructural como punto de partida."""
    cierre = (await db.execute(select(FinancieroCierreEstructural).limit(1))).scalar_one_or_none()
    if cierre is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Todavía no se cargó el Cierre Estructural (punto de partida del modelo)",
        )
    parametros = (await db.execute(select(FinancieroParametros).limit(1))).scalar_one_or_none()
    if parametros is None:
        parametros = FinancieroParametros()

    lista_semanas = semanas_del_rango(cierre.fecha_corte, semanas)
    fin = lista_semanas[-1] + datetime.timedelta(days=6)

    # Ventas reales por semana, desde ventas_detalle.
    ventas_rows = (
        await db.execute(
            select(VentaDetalle.fecha, VentaDetalle.importe).where(
                VentaDetalle.fecha >= lista_semanas[0], VentaDetalle.fecha <= fin
            )
        )
    ).all()
    ventas_por_semana: dict[datetime.date, float] = {}
    for fecha, importe in ventas_rows:
        semana = lunes_de_semana(fecha)
        ventas_por_semana[semana] = ventas_por_semana.get(semana, 0.0) + float(importe)
    # Solo semanas completamente transcurridas cuentan como "Real" -- la
    # semana en curso todavía no cerró, se sigue proyectando con Plan.
    hoy = datetime.date.today()
    ventas_reales_por_semana = {
        semana: monto for semana, monto in ventas_por_semana.items() if semana + datetime.timedelta(days=6) < hoy
    }

    # Compras: se usan solo como referencia informativa (compras_real), el
    # pago real sale de fecha_pago_resuelta más abajo.
    compras = (await db.execute(select(FinancieroCompra))).scalars().all()
    compras_por_semana: dict[datetime.date, float] = {}
    pago_proveedores_por_semana: dict[datetime.date, float] = {}
    for compra in compras:
        semana_compra = lunes_de_semana(compra.fecha_compra)
        compras_por_semana[semana_compra] = compras_por_semana.get(semana_compra, 0.0) + float(compra.monto)
        if compra.forma_pago != "cheque":
            fecha_resuelta = await _resolver_fecha_pago_compra(db, compra)
            if fecha_resuelta is not None:
                semana_pago = lunes_de_semana(fecha_resuelta)
                pago_proveedores_por_semana[semana_pago] = (
                    pago_proveedores_por_semana.get(semana_pago, 0.0) + float(compra.monto)
                )

    cheques = (await db.execute(select(FinancieroCheque).where(FinancieroCheque.estado != "anulado"))).scalars().all()
    pago_cheques_por_semana: dict[datetime.date, float] = {}
    for cheque in cheques:
        semana = lunes_de_semana(cheque.fecha_pago)
        pago_cheques_por_semana[semana] = pago_cheques_por_semana.get(semana, 0.0) + float(cheque.monto)

    cuotas = (await db.execute(select(FinancieroCuotaBancaria))).scalars().all()
    cuotas_por_semana: dict[datetime.date, float] = {}
    for cuota in cuotas:
        semana = lunes_de_semana(cuota.fecha_vencimiento)
        cuotas_por_semana[semana] = cuotas_por_semana.get(semana, 0.0) + float(cuota.monto)

    impuestos = (await db.execute(select(FinancieroImpuesto))).scalars().all()
    for impuesto in impuestos:
        semana = lunes_de_semana(impuesto.fecha_vencimiento)
        cuotas_por_semana[semana] = cuotas_por_semana.get(semana, 0.0) + float(impuesto.monto)

    gastos = (await db.execute(select(FinancieroGastoMensual))).scalars().all()
    gastos_por_mes = {(g.anio, g.mes): g for g in gastos}
    sueldos_y_gastos_por_semana: dict[datetime.date, float] = {}
    for semana in lista_semanas:
        gasto_mes = gastos_por_mes.get((semana.year, semana.month))
        if gasto_mes is None:
            continue
        monto = gastos_generales_semanal(float(gasto_mes.gastos_generales_monto), float(gasto_mes.sueldos_monto))
        # Semana N del mes = semana de pago de sueldos configurada.
        primera_semana_del_mes = lunes_de_semana(datetime.date(semana.year, semana.month, 1))
        numero_semana_del_mes = ((semana - primera_semana_del_mes).days // 7) + 1
        if numero_semana_del_mes == gasto_mes.semana_pago_sueldos:
            monto += float(gasto_mes.sueldos_monto)
        sueldos_y_gastos_por_semana[semana] = monto

    ventas_plan = monto_plan_semanal(float(cierre.ventas_netas_mes_real))
    compras_plan = monto_plan_semanal(float(cierre.compras_netas_mes_real))

    # VentasPlanSemanal no queda congelado en el número derivado del Cierre
    # Estructural (eso es historia de julio): cada semana usa el objetivo
    # mensual vigente de ese mes si está cargado, o si no el promedio de las
    # últimas semanas de Ventas Real -- el Cierre Estructural es el último
    # recurso, solo para el arranque del plan antes de tener objetivo o Real.
    objetivos_rows = (
        await db.execute(
            select(ObjetivoMensual.anio, ObjetivoMensual.mes, func.sum(ObjetivoMensual.monto)).group_by(
                ObjetivoMensual.anio, ObjetivoMensual.mes
            )
        )
    ).all()
    objetivos_por_mes = {(anio, mes): float(total) for anio, mes, total in objetivos_rows}
    plan_por_semana = construir_ventas_plan_semanal(
        lista_semanas,
        objetivos_por_mes=objetivos_por_mes,
        ventas_reales_por_semana=ventas_reales_por_semana,
        fallback_mensual=ventas_plan,
    )

    filas = calcular_cashflow_semanal(
        lista_semanas,
        ventas_reales_por_semana=ventas_reales_por_semana,
        ventas_plan_semanal_monto=ventas_plan,
        ventas_plan_por_semana=plan_por_semana,
        compras_reales_por_semana=compras_por_semana,
        compras_plan_semanal_monto=compras_plan,
        pago_proveedores_por_semana=pago_proveedores_por_semana,
        pago_cheques_por_semana=pago_cheques_por_semana,
        cuotas_por_semana=cuotas_por_semana,
        sueldos_y_gastos_por_semana=sueldos_y_gastos_por_semana,
        saldo_caja_inicial=float(cierre.saldo_caja_bancos),
        credito_total=float(parametros.credito_total_disponible),
        pct_cobro_contado=float(parametros.pct_cobro_contado),
        umbral_riesgo=float(parametros.umbral_riesgo),
        umbral_ajustado=float(parametros.umbral_ajustado),
    )

    # Misma mecánica pero sin mezclar ningún dato Real (ventas/compras 100%
    # Plan), para poder graficar "Acum. Plan" vs "Acum. Real" una al lado de
    # la otra -- son dos corridas del mismo motor, no un cálculo aparte.
    filas_plan = calcular_cashflow_semanal(
        lista_semanas,
        ventas_reales_por_semana={},
        ventas_plan_semanal_monto=ventas_plan,
        ventas_plan_por_semana=plan_por_semana,
        compras_reales_por_semana={},
        compras_plan_semanal_monto=compras_plan,
        pago_proveedores_por_semana=pago_proveedores_por_semana,
        pago_cheques_por_semana=pago_cheques_por_semana,
        cuotas_por_semana=cuotas_por_semana,
        sueldos_y_gastos_por_semana=sueldos_y_gastos_por_semana,
        saldo_caja_inicial=float(cierre.saldo_caja_bancos),
        credito_total=float(parametros.credito_total_disponible),
        pct_cobro_contado=float(parametros.pct_cobro_contado),
        umbral_riesgo=float(parametros.umbral_riesgo),
        umbral_ajustado=float(parametros.umbral_ajustado),
    )

    kpis = await _kpis(db, parametros)
    # Completar crédito usado/disponible "hoy" con la fila de la semana
    # actual (o la última calculada si hoy cae después del rango pedido).
    fila_actual = next((f for f in filas if f.semana_inicio <= hoy < f.semana_inicio + datetime.timedelta(days=7)), None)
    if fila_actual is None and filas:
        fila_actual = filas[-1]
    if fila_actual is not None:
        kpis.credito_usado = fila_actual.credito_usado
        kpis.credito_disponible = kpis.credito_total - fila_actual.credito_usado
        kpis.credito_pct_usado = (fila_actual.credito_usado / kpis.credito_total) if kpis.credito_total else None

    return CashflowResumenOut(
        kpis=kpis,
        filas=[
            FilaCashflowOut(**dataclasses.asdict(f), flujo_acum_neto_plan=fp.flujo_acum_neto)
            for f, fp in zip(filas, filas_plan)
        ],
    )
