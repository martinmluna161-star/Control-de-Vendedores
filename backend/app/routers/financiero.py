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
    NOMBRES_ESCENARIO,
    FinancieroCheque,
    FinancieroCierreEstructural,
    FinancieroCompra,
    FinancieroCuotaBancaria,
    FinancieroEscenarioProyeccion,
    FinancieroGastoMensual,
    FinancieroIIBBSaldoFavor,
    FinancieroImpuesto,
    FinancieroMarkupLinea,
    FinancieroParametros,
    FinancieroProveedor,
)
from app.models.objetivo import ObjetivoMensual
from app.models.venta import VentaDetalle
from app.models.zona import Zona
from app.routers.cuentas_corrientes import LIMITE_CODIGO_CLIENTE_EMPLEADO, _ultima_carga_por_zona, _vendedor_resuelto_expr
from app.services.cuentas_corrientes import calcular_vencido_por_vencer
from app.schemas.financiero import (
    AntiguedadTramoOut,
    CajaMesOut,
    CajaResumenOut,
    CashflowKpisOut,
    CashflowResumenOut,
    ChequeIn,
    ChequeOut,
    ChequePatch,
    CierreEstructuralIn,
    CierreEstructuralOut,
    CobranzasResumenOut,
    CompraIn,
    CompraOut,
    CompraPatch,
    CuotaBancariaIn,
    CuotaBancariaOut,
    CuotaBancariaPatch,
    DeudaCalendarioMesOut,
    DeudaPorAcreedorOut,
    DeudaResumenOut,
    EscenarioProyeccionIn,
    EscenarioProyeccionOut,
    EstadoResultadosMesOut,
    FilaCashflowOut,
    FilaProyeccionOut,
    GastoMensualIn,
    GastoMensualOut,
    GastoMensualPatch,
    IIBBSaldoFavorIn,
    IIBBSaldoFavorOut,
    ImpuestoIn,
    ImpuestoOut,
    ImpuestoPatch,
    MarkupLineaIn,
    MarkupLineaOut,
    MarkupLineaPatch,
    MensualHistoricoOut,
    MensualResumenOut,
    ParametrosIn,
    ParametrosOut,
    ProveedorIn,
    ProveedorOut,
    ProveedorPatch,
    ProveedorSaldoOut,
    ProyeccionResumenOut,
    VentaEquilibrioOut,
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
from app.services.financiero_mensual import (
    calcular_cobertura,
    calcular_estado_resultados_mes,
    calcular_proyeccion_escenario,
    calcular_venta_equilibrio,
    etiqueta_mes,
    meses_del_rango,
    tramo_antiguedad,
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


async def _cartera_por_cliente(db: AsyncSession) -> tuple[dict[str, float], dict[str, list]]:
    """Última carga de Cta Cte por zona, resuelta en vivo, sumando todo
    (vista de administración, no de cartera por vendedor) -- mismo criterio
    que /cuentas-corrientes. Reutilizado por los KPIs del cashflow semanal y
    por el resumen de Cobranzas del tablero mensual."""
    ultimo = _ultima_carga_por_zona()
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
            & ultimo.c.vendedor_resuelto.is_not_distinct_from(vendedor_resuelto)
            & ultimo.c.zona_actual.is_not_distinct_from(Cliente.zona_codigo),
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
    return por_cliente_total, por_cliente_comprobantes


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

    por_cliente_total, por_cliente_comprobantes = await _cartera_por_cliente(db)

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


# ==================================================================
# Tablero mensual: Estado de Resultados, Deuda, Cobranzas, Caja, Proyección
# ==================================================================
#
# Modelo complementario al cashflow semanal de arriba: éste responde "¿la
# empresa gana o pierde plata, y aguanta la deuda?" con una mirada mensual
# tipo Estado de Resultados / EBITDA, en vez de "¿me alcanza la plata esta
# semana?" con cada factura y cheque. Reutiliza los mismos datos de origen
# (ventas_detalle, financiero_compras, financiero_cuotas_bancarias,
# financiero_impuestos, cuentas_corrientes) -- no duplica nada.

ALICUOTA_GANANCIAS_DEFAULT = 0.35


def _rango_mes(anio: int, mes: int) -> tuple[datetime.date, datetime.date]:
    desde = datetime.date(anio, mes, 1)
    anio_sig, mes_sig = (anio + 1, 1) if mes == 12 else (anio, mes + 1)
    hasta = datetime.date(anio_sig, mes_sig, 1) - datetime.timedelta(days=1)
    return desde, hasta


async def _gasto_del_mes(db: AsyncSession, anio: int, mes: int) -> FinancieroGastoMensual | None:
    return (
        await db.execute(
            select(FinancieroGastoMensual).where(FinancieroGastoMensual.anio == anio, FinancieroGastoMensual.mes == mes)
        )
    ).scalar_one_or_none()


async def _ventas_del_mes(db: AsyncSession, anio: int, mes: int) -> float:
    desde, hasta = _rango_mes(anio, mes)
    total = (
        await db.execute(
            select(func.coalesce(func.sum(VentaDetalle.importe), 0)).where(
                VentaDetalle.fecha >= desde, VentaDetalle.fecha <= hasta
            )
        )
    ).scalar_one()
    return float(total)


async def _costo_mercaderia_del_mes(db: AsyncSession, anio: int, mes: int) -> float:
    """Provisorio: usa el total de financiero_compras (con IVA, tal como
    viene del libro IVA compras) como proxy del costo de mercadería neto --
    sobreestima el costo en el % de IVA. Para un margen bruto exacto haría
    falta cargar el neto gravado por comprobante, que hoy no se guarda."""
    desde, hasta = _rango_mes(anio, mes)
    total = (
        await db.execute(
            select(func.coalesce(func.sum(FinancieroCompra.monto), 0)).where(
                FinancieroCompra.fecha_compra >= desde, FinancieroCompra.fecha_compra <= hasta
            )
        )
    ).scalar_one()
    return -float(total)


async def _cuotas_del_mes(db: AsyncSession, anio: int, mes: int) -> tuple[float, float | None, float | None]:
    """Cuota total del mes (cuotas bancarias + impuestos/planes con
    vencimiento ese mes) y, si está cargada la apertura capital/interés de
    TODAS las cuotas del mes, el interés y el capital por separado -- si
    falta la apertura de alguna, se devuelve None (no se inventa el
    faltante como 0)."""
    desde, hasta = _rango_mes(anio, mes)
    cuotas = (
        await db.execute(
            select(FinancieroCuotaBancaria).where(
                FinancieroCuotaBancaria.fecha_vencimiento >= desde, FinancieroCuotaBancaria.fecha_vencimiento <= hasta
            )
        )
    ).scalars().all()
    impuestos = (
        await db.execute(
            select(FinancieroImpuesto).where(
                FinancieroImpuesto.fecha_vencimiento >= desde,
                FinancieroImpuesto.fecha_vencimiento <= hasta,
                FinancieroImpuesto.pagado.is_(False),
            )
        )
    ).scalars().all()
    cuota_total = sum(float(c.monto) for c in cuotas) + sum(float(i.monto) for i in impuestos)
    if cuotas and all(c.interes_monto is not None for c in cuotas):
        intereses = sum(float(c.interes_monto) for c in cuotas)
        capital = sum(float(c.capital_monto or 0) for c in cuotas)
        return cuota_total, intereses, capital
    return cuota_total, None, None


async def _alicuota_ganancias_configurada(db: AsyncSession) -> float:
    base = (
        await db.execute(select(FinancieroEscenarioProyeccion).where(FinancieroEscenarioProyeccion.nombre == "base"))
    ).scalar_one_or_none()
    return float(base.alicuota_ganancias) if base else ALICUOTA_GANANCIAS_DEFAULT


async def _calcular_mes(db: AsyncSession, anio: int, mes: int, alicuota_ganancias: float) -> tuple[EstadoResultadosMesOut, list[str]]:
    ventas = await _ventas_del_mes(db, anio, mes)
    costo_mercaderia = await _costo_mercaderia_del_mes(db, anio, mes)
    gasto_mes = await _gasto_del_mes(db, anio, mes)

    faltantes: list[str] = []

    def _campo(nombre: str, valor: float | None, label: str) -> float:
        if valor is None:
            faltantes.append(label)
            return 0.0
        return -abs(float(valor))

    sueldos_y_cargas = -abs(float(gasto_mes.sueldos_monto)) if gasto_mes else 0.0
    if gasto_mes is None:
        faltantes.append("Sueldos y cargas")
    gastos_variables = _campo("gastos_variables", gasto_mes.gastos_variables_monto if gasto_mes else None, "Gastos variables")
    gastos_fijos = _campo("gastos_fijos", gasto_mes.gastos_fijos_monto if gasto_mes else None, "Gastos fijos")
    casilla = _campo("casilla", gasto_mes.casilla_monto if gasto_mes else None, "Casilla")
    ingresos_brutos = _campo("ingresos_brutos", gasto_mes.ingresos_brutos_monto if gasto_mes else None, "Ingresos Brutos")
    retiros_socios = _campo("retiros_socios", gasto_mes.retiros_socios_monto if gasto_mes else None, "Retiros de socios")
    iva = _campo("iva", gasto_mes.iva_monto if gasto_mes else None, "IVA")

    cuota_total, intereses_pos, _capital = await _cuotas_del_mes(db, anio, mes)
    if intereses_pos is None:
        intereses = 0.0
        faltantes.append("Intereses (apertura capital/interés de las cuotas)")
    else:
        intereses = -abs(intereses_pos)

    calc = calcular_estado_resultados_mes(
        anio=anio,
        mes=mes,
        ventas=ventas,
        costo_mercaderia=costo_mercaderia,
        gastos_variables=gastos_variables,
        gastos_fijos=gastos_fijos,
        sueldos_y_cargas=sueldos_y_cargas,
        casilla=casilla,
        ingresos_brutos=ingresos_brutos,
        retiros_socios=retiros_socios,
        iva=iva,
        intereses=intereses,
        alicuota_ganancias=alicuota_ganancias,
    )

    hoy = datetime.date.today()
    tipo = "real" if (anio, mes) < (hoy.year, hoy.month) else "estimado"

    salida = EstadoResultadosMesOut(
        anio=anio,
        mes=mes,
        etiqueta=etiqueta_mes(anio, mes),
        tipo=tipo,
        ventas=calc.ventas,
        costo_mercaderia=calc.costo_mercaderia,
        margen_bruto=calc.margen_bruto,
        margen_bruto_pct=calc.margen_bruto_pct,
        gastos_variables=calc.gastos_variables,
        gastos_fijos=calc.gastos_fijos,
        sueldos_y_cargas=calc.sueldos_y_cargas,
        casilla=calc.casilla,
        ingresos_brutos=calc.ingresos_brutos,
        retiros_socios=calc.retiros_socios,
        iva=calc.iva,
        gastos_operativos=calc.gastos_operativos,
        ebitda=calc.ebitda,
        ebitda_pct=calc.ebitda_pct,
        intereses=calc.intereses,
        antes_ganancias=calc.antes_ganancias,
        impuesto_ganancias=calc.impuesto_ganancias,
        resultado_neto=calc.resultado_neto,
        cuota_bancaria_mes=cuota_total,
    )
    return salida, faltantes


@router.get("/mensual/resumen", response_model=MensualResumenOut)
async def obtener_resumen_mensual(
    anio: int = Query(...),
    mes: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    """"Cómo me fue": Estado de Resultados de un mes puntual + punto de
    equilibrio. Todo derivado de lo ya cargado (ventas_detalle, compras,
    gastos, cuotas) -- lo que falte se lista en ``faltan_campos`` en vez de
    completarse con un supuesto silencioso."""
    alicuota_ganancias = await _alicuota_ganancias_configurada(db)
    estado, faltantes = await _calcular_mes(db, anio, mes, alicuota_ganancias)
    eq = calcular_venta_equilibrio(
        ventas=estado.ventas,
        costo_mercaderia=estado.costo_mercaderia,
        gastos_variables=estado.gastos_variables or 0.0,
        gastos_fijos=estado.gastos_fijos or 0.0,
        sueldos_y_cargas=estado.sueldos_y_cargas,
        casilla=estado.casilla or 0.0,
        ingresos_brutos=estado.ingresos_brutos or 0.0,
        iva=estado.iva or 0.0,
        intereses=estado.intereses,
        retiros_socios=estado.retiros_socios or 0.0,
    )
    return MensualResumenOut(mes=estado, venta_equilibrio=VentaEquilibrioOut(**eq), faltan_campos=faltantes)


@router.get("/mensual/historico", response_model=MensualHistoricoOut)
async def obtener_historico_mensual(
    meses: int = Query(default=12, ge=1, le=36),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    """"Todos los meses": serie de Estados de Resultados terminando en el
    mes en curso."""
    alicuota_ganancias = await _alicuota_ganancias_configurada(db)
    hoy = datetime.date.today()
    anio_desde, mes_desde = hoy.year, hoy.month
    for _ in range(meses - 1):
        anio_desde, mes_desde = (anio_desde - 1, 12) if mes_desde == 1 else (anio_desde, mes_desde - 1)
    lista_meses = meses_del_rango(anio_desde, mes_desde, meses)
    filas = []
    for anio, mes in lista_meses:
        estado, _ = await _calcular_mes(db, anio, mes, alicuota_ganancias)
        filas.append(estado)
    return MensualHistoricoOut(meses=filas)


# ---------------- Deuda ----------------


@router.get("/deuda/resumen", response_model=DeudaResumenOut)
async def obtener_resumen_deuda(
    meses: int = Query(default=12, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    """Calendario de cuotas bancarias + planes de ARCA agrupado por mes y
    por acreedor, y dónde el EBITDA del mes no alcanza a cubrir la cuota."""
    alicuota_ganancias = await _alicuota_ganancias_configurada(db)
    hoy = datetime.date.today()
    lista_meses = meses_del_rango(hoy.year, hoy.month, meses)

    cuotas = (await db.execute(select(FinancieroCuotaBancaria))).scalars().all()
    impuestos = (
        await db.execute(select(FinancieroImpuesto).where(FinancieroImpuesto.pagado.is_(False)))
    ).scalars().all()

    cuota_por_mes: dict[tuple[int, int], float] = {}
    por_acreedor_monto: dict[str, float] = {}
    for c in cuotas:
        clave = (c.fecha_vencimiento.year, c.fecha_vencimiento.month)
        cuota_por_mes[clave] = cuota_por_mes.get(clave, 0.0) + float(c.monto)
        por_acreedor_monto[c.banco] = por_acreedor_monto.get(c.banco, 0.0) + float(c.monto)
    for i in impuestos:
        clave = (i.fecha_vencimiento.year, i.fecha_vencimiento.month)
        cuota_por_mes[clave] = cuota_por_mes.get(clave, 0.0) + float(i.monto)
        por_acreedor_monto["Impuestos / ARCA"] = por_acreedor_monto.get("Impuestos / ARCA", 0.0) + float(i.monto)

    total_deuda = sum(por_acreedor_monto.values())
    por_acreedor = sorted(
        (
            DeudaPorAcreedorOut(acreedor=k, monto=v, pct=(v / total_deuda * 100) if total_deuda else 0.0)
            for k, v in por_acreedor_monto.items()
        ),
        key=lambda x: -x.monto,
    )

    calendario = []
    for anio, mes in lista_meses:
        cuota_total = cuota_por_mes.get((anio, mes), 0.0)
        estado, _ = await _calcular_mes(db, anio, mes, alicuota_ganancias)
        faltante = (cuota_total - estado.ebitda) if cuota_total > estado.ebitda else None
        calendario.append(
            DeudaCalendarioMesOut(
                anio=anio, mes=mes, etiqueta=etiqueta_mes(anio, mes),
                cuota_total=cuota_total, ebitda_mes=estado.ebitda, faltante=faltante,
            )
        )

    mes_mas_pesado = max(cuota_por_mes.items(), key=lambda kv: kv[1], default=None)

    return DeudaResumenOut(
        falta_pagar_12_meses=sum(cuota_por_mes.get(m, 0.0) for m in lista_meses),
        obligaciones_activas=len(cuotas) + len(impuestos),
        mes_mas_pesado_etiqueta=etiqueta_mes(*mes_mas_pesado[0]) if mes_mas_pesado else None,
        mes_mas_pesado_monto=mes_mas_pesado[1] if mes_mas_pesado else None,
        por_acreedor=por_acreedor,
        calendario=calendario,
    )


# ---------------- Cobranzas ----------------


@router.get("/cobranzas/resumen", response_model=CobranzasResumenOut)
async def obtener_resumen_cobranzas(
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    """Antigüedad de la cartera por tramos, a quién le debe la empresa, y
    markup/IIBB cargados a mano (no hay costo por producto en el sistema
    para derivarlos solos)."""
    por_cliente_total, por_cliente_comprobantes = await _cartera_por_cliente(db)
    hoy = datetime.date.today()
    le_deben_bruto = sum(por_cliente_total.values())

    tramos: dict[str, dict] = {t: {"clientes": set(), "saldo": 0.0} for t in (
        "Al día", "1 a 15 días", "16 a 30 días", "31 a 60 días", "61 a 90 días", "Más de 90 días"
    )}
    for codigo, total in por_cliente_total.items():
        comprobantes = por_cliente_comprobantes.get(codigo, [])
        if comprobantes:
            for cp in comprobantes:
                dias = (hoy - cp.fecha_vencimiento).days if cp.fecha_vencimiento else 0
                tramo = tramo_antiguedad(dias)
                tramos[tramo]["clientes"].add(codigo)
                tramos[tramo]["saldo"] += float(cp.monto)
        else:
            # Saldo consolidado sin comprobantes: sin fecha no hay cómo
            # probar que está vencido (mismo criterio que Cta Cte).
            tramos["Al día"]["clientes"].add(codigo)
            tramos["Al día"]["saldo"] += total

    antiguedad = [
        AntiguedadTramoOut(
            tramo=t, clientes=len(v["clientes"]), saldo=v["saldo"],
            pct=(v["saldo"] / le_deben_bruto * 100) if le_deben_bruto else 0.0,
        )
        for t, v in tramos.items()
    ]
    dudoso = tramos["Más de 90 días"]["saldo"]

    compras = (await db.execute(select(FinancieroCompra))).scalars().all()
    por_proveedor: dict[str, float] = {}
    for compra in compras:
        fecha_resuelta = await _resolver_fecha_pago_compra(db, compra)
        if fecha_resuelta is None or fecha_resuelta >= hoy:
            por_proveedor[compra.proveedor_nombre] = por_proveedor.get(compra.proveedor_nombre, 0.0) + float(compra.monto)
    debe_a_proveedores = sum(v for v in por_proveedor.values() if v > 0)
    proveedores_saldo = sorted(
        (
            ProveedorSaldoOut(
                proveedor=k, saldo=v,
                pct=(v / debe_a_proveedores * 100) if (debe_a_proveedores and v > 0) else None,
            )
            for k, v in por_proveedor.items()
        ),
        key=lambda x: -x.saldo,
    )

    markup_rows = (
        await db.execute(select(FinancieroMarkupLinea).order_by(FinancieroMarkupLinea.markup_pct.desc()))
    ).scalars().all()
    markup_lineas = [
        MarkupLineaOut(
            id=m.id, proveedor_o_linea=m.proveedor_o_linea, markup_pct=float(m.markup_pct),
            margen_pct=float(m.markup_pct) / (1 + float(m.markup_pct)),
        )
        for m in markup_rows
    ]

    iibb_row = (
        await db.execute(select(FinancieroIIBBSaldoFavor).order_by(FinancieroIIBBSaldoFavor.fecha_corte.desc()).limit(1))
    ).scalar_one_or_none()
    iibb_ultimo = (
        IIBBSaldoFavorOut(
            id=iibb_row.id, fecha_corte=iibb_row.fecha_corte, saldo_a_favor=float(iibb_row.saldo_a_favor),
            impuesto_determinado_12m=float(iibb_row.impuesto_determinado_12m), retenido_12m=float(iibb_row.retenido_12m),
        )
        if iibb_row
        else None
    )

    return CobranzasResumenOut(
        le_deben_bruto=le_deben_bruto,
        le_deben_neto=le_deben_bruto,
        anticipos_clientes=0.0,
        dudoso_mas_90_dias=dudoso,
        dudoso_pct=(dudoso / le_deben_bruto * 100) if le_deben_bruto else None,
        dias_promedio_cartera=None,
        debe_a_proveedores=debe_a_proveedores,
        le_financian=debe_a_proveedores - le_deben_bruto,
        antiguedad=antiguedad,
        proveedores_saldo=proveedores_saldo,
        markup_lineas=markup_lineas,
        iibb_ultimo=iibb_ultimo,
    )


@router.get("/cobranzas/markup", response_model=list[MarkupLineaOut])
async def listar_markup_lineas(db: AsyncSession = Depends(get_db), usuario: UsuarioActual = Depends(requerir_admin)):
    rows = (await db.execute(select(FinancieroMarkupLinea).order_by(FinancieroMarkupLinea.proveedor_o_linea))).scalars().all()
    return [
        MarkupLineaOut(id=m.id, proveedor_o_linea=m.proveedor_o_linea, markup_pct=float(m.markup_pct), margen_pct=float(m.markup_pct) / (1 + float(m.markup_pct)))
        for m in rows
    ]


@router.post("/cobranzas/markup", response_model=MarkupLineaOut, status_code=status.HTTP_201_CREATED)
async def crear_markup_linea(
    body: MarkupLineaIn, db: AsyncSession = Depends(get_db), usuario: UsuarioActual = Depends(requerir_admin)
):
    existente = (
        await db.execute(select(FinancieroMarkupLinea).where(FinancieroMarkupLinea.proveedor_o_linea == body.proveedor_o_linea))
    ).scalar_one_or_none()
    if existente is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe ese proveedor/línea")
    fila = FinancieroMarkupLinea(**body.model_dump())
    db.add(fila)
    await db.commit()
    await db.refresh(fila)
    return MarkupLineaOut(id=fila.id, proveedor_o_linea=fila.proveedor_o_linea, markup_pct=float(fila.markup_pct), margen_pct=float(fila.markup_pct) / (1 + float(fila.markup_pct)))


@router.patch("/cobranzas/markup/{markup_id}", response_model=MarkupLineaOut)
async def editar_markup_linea(
    markup_id: uuid.UUID, body: MarkupLineaPatch, db: AsyncSession = Depends(get_db), usuario: UsuarioActual = Depends(requerir_admin)
):
    fila = await db.get(FinancieroMarkupLinea, markup_id)
    if fila is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    for campo, valor in body.model_dump(exclude_unset=True).items():
        setattr(fila, campo, valor)
    await db.commit()
    await db.refresh(fila)
    return MarkupLineaOut(id=fila.id, proveedor_o_linea=fila.proveedor_o_linea, markup_pct=float(fila.markup_pct), margen_pct=float(fila.markup_pct) / (1 + float(fila.markup_pct)))


@router.delete("/cobranzas/markup/{markup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_markup_linea(
    markup_id: uuid.UUID, db: AsyncSession = Depends(get_db), usuario: UsuarioActual = Depends(requerir_admin)
):
    fila = await db.get(FinancieroMarkupLinea, markup_id)
    if fila is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    await db.delete(fila)
    await db.commit()


@router.get("/cobranzas/iibb", response_model=list[IIBBSaldoFavorOut])
async def listar_iibb_saldo_favor(db: AsyncSession = Depends(get_db), usuario: UsuarioActual = Depends(requerir_admin)):
    rows = (await db.execute(select(FinancieroIIBBSaldoFavor).order_by(FinancieroIIBBSaldoFavor.fecha_corte.desc()))).scalars().all()
    return [
        IIBBSaldoFavorOut(id=r.id, fecha_corte=r.fecha_corte, saldo_a_favor=float(r.saldo_a_favor), impuesto_determinado_12m=float(r.impuesto_determinado_12m), retenido_12m=float(r.retenido_12m))
        for r in rows
    ]


@router.post("/cobranzas/iibb", response_model=IIBBSaldoFavorOut, status_code=status.HTTP_201_CREATED)
async def crear_iibb_saldo_favor(
    body: IIBBSaldoFavorIn, db: AsyncSession = Depends(get_db), usuario: UsuarioActual = Depends(requerir_admin)
):
    fila = FinancieroIIBBSaldoFavor(**body.model_dump())
    db.add(fila)
    await db.commit()
    await db.refresh(fila)
    return IIBBSaldoFavorOut(id=fila.id, fecha_corte=fila.fecha_corte, saldo_a_favor=float(fila.saldo_a_favor), impuesto_determinado_12m=float(fila.impuesto_determinado_12m), retenido_12m=float(fila.retenido_12m))


@router.delete("/cobranzas/iibb/{iibb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def borrar_iibb_saldo_favor(
    iibb_id: uuid.UUID, db: AsyncSession = Depends(get_db), usuario: UsuarioActual = Depends(requerir_admin)
):
    fila = await db.get(FinancieroIIBBSaldoFavor, iibb_id)
    if fila is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")
    await db.delete(fila)
    await db.commit()


# ---------------- Caja ----------------


@router.get("/caja/resumen", response_model=CajaResumenOut)
async def obtener_resumen_caja(
    meses: int = Query(default=12, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    """Cascada mensual de caja, arrancando del EBITDA (no del resultado
    neto, para no restar dos veces las amortizaciones) menos retiros y
    capital de deuda -- sin stock/CxC/impuestos pagados/financiación/
    inversión, que este sistema no trackea todavía."""
    alicuota_ganancias = await _alicuota_ganancias_configurada(db)
    cierre = (await db.execute(select(FinancieroCierreEstructural).limit(1))).scalar_one_or_none()
    hoy = datetime.date.today()
    anio_desde, mes_desde = hoy.year, hoy.month
    for _ in range(meses - 1):
        anio_desde, mes_desde = (anio_desde - 1, 12) if mes_desde == 1 else (anio_desde, mes_desde - 1)
    lista_meses = meses_del_rango(anio_desde, mes_desde, meses)

    banco = float(cierre.saldo_caja_bancos) if cierre else 0.0
    filas = []
    for anio, mes in lista_meses:
        estado, _ = await _calcular_mes(db, anio, mes, alicuota_ganancias)
        _, _, capital_pos = await _cuotas_del_mes(db, anio, mes)
        capital = capital_pos or 0.0
        la_caja_crecio = estado.ebitda + estado.retiros_socios - capital
        banco += la_caja_crecio
        filas.append(
            CajaMesOut(
                anio=anio, mes=mes, etiqueta=etiqueta_mes(anio, mes),
                ebitda=estado.ebitda, retiros_socios=estado.retiros_socios,
                capital_deuda=-capital, la_caja_crecio=la_caja_crecio, banco_acumulado=banco,
            )
        )
    return CajaResumenOut(meses=filas)


# ---------------- Escenarios de proyección ----------------

_ESCENARIOS_DEFAULT = {
    "base": dict(crecimiento_ventas_mensual=0.02, margen_bruto=0.27, inflacion_gastos_mensual=0.02),
    "ideal": dict(crecimiento_ventas_mensual=0.03, margen_bruto=0.28, inflacion_gastos_mensual=0.02),
    "optimo": dict(crecimiento_ventas_mensual=0.04, margen_bruto=0.29, inflacion_gastos_mensual=0.02),
    "pesimista": dict(crecimiento_ventas_mensual=0.01, margen_bruto=0.25, inflacion_gastos_mensual=0.03),
}


async def _asegurar_escenarios(db: AsyncSession) -> None:
    existentes = (await db.execute(select(FinancieroEscenarioProyeccion.nombre))).scalars().all()
    faltan = set(NOMBRES_ESCENARIO) - set(existentes)
    if not faltan:
        return
    for nombre in faltan:
        db.add(FinancieroEscenarioProyeccion(nombre=nombre, **_ESCENARIOS_DEFAULT[nombre]))
    await db.commit()


@router.get("/escenarios", response_model=list[EscenarioProyeccionOut])
async def listar_escenarios(db: AsyncSession = Depends(get_db), usuario: UsuarioActual = Depends(requerir_admin)):
    await _asegurar_escenarios(db)
    rows = (await db.execute(select(FinancieroEscenarioProyeccion).order_by(FinancieroEscenarioProyeccion.nombre))).scalars().all()
    return [
        EscenarioProyeccionOut(
            id=r.id, nombre=r.nombre, crecimiento_ventas_mensual=float(r.crecimiento_ventas_mensual),
            margen_bruto=float(r.margen_bruto), inflacion_gastos_mensual=float(r.inflacion_gastos_mensual),
            alicuota_iva=float(r.alicuota_iva), alicuota_ganancias=float(r.alicuota_ganancias),
        )
        for r in rows
    ]


@router.put("/escenarios/{nombre}", response_model=EscenarioProyeccionOut)
async def guardar_escenario(
    nombre: str, body: EscenarioProyeccionIn, db: AsyncSession = Depends(get_db), usuario: UsuarioActual = Depends(requerir_admin)
):
    if nombre not in NOMBRES_ESCENARIO:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escenario inválido")
    await _asegurar_escenarios(db)
    fila = (
        await db.execute(select(FinancieroEscenarioProyeccion).where(FinancieroEscenarioProyeccion.nombre == nombre))
    ).scalar_one()
    for campo, valor in body.model_dump().items():
        setattr(fila, campo, valor)
    await db.commit()
    await db.refresh(fila)
    return EscenarioProyeccionOut(
        id=fila.id, nombre=fila.nombre, crecimiento_ventas_mensual=float(fila.crecimiento_ventas_mensual),
        margen_bruto=float(fila.margen_bruto), inflacion_gastos_mensual=float(fila.inflacion_gastos_mensual),
        alicuota_iva=float(fila.alicuota_iva), alicuota_ganancias=float(fila.alicuota_ganancias),
    )


# ---------------- Proyección a 10 meses ----------------


@router.get("/proyeccion", response_model=ProyeccionResumenOut)
async def obtener_proyeccion(
    escenario: str = Query(default="base"),
    meses: int = Query(default=10, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    usuario: UsuarioActual = Depends(requerir_admin),
):
    if escenario not in NOMBRES_ESCENARIO:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escenario inválido")
    await _asegurar_escenarios(db)
    fila_escenario = (
        await db.execute(select(FinancieroEscenarioProyeccion).where(FinancieroEscenarioProyeccion.nombre == escenario))
    ).scalar_one()

    cierre = (await db.execute(select(FinancieroCierreEstructural).limit(1))).scalar_one_or_none()
    if cierre is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Todavía no se cargó el Cierre Estructural")

    hoy = datetime.date.today()
    anio_arranque, mes_arranque = hoy.year, hoy.month - 1 if hoy.month > 1 else 12
    if hoy.month == 1:
        anio_arranque -= 1
    ventas_mes_base = await _ventas_del_mes(db, anio_arranque, mes_arranque)
    if not ventas_mes_base:
        ventas_mes_base = monto_plan_semanal(float(cierre.ventas_netas_mes_real)) * (52 / 12)

    gasto_base = await _gasto_del_mes(db, anio_arranque, mes_arranque)
    gastos_variables_base = abs(float(gasto_base.gastos_variables_monto)) if gasto_base and gasto_base.gastos_variables_monto else 0.0
    gastos_fijos_base = abs(float(gasto_base.gastos_fijos_monto)) if gasto_base and gasto_base.gastos_fijos_monto else 0.0
    retiros_pct_ventas = (
        abs(float(gasto_base.retiros_socios_monto)) / ventas_mes_base
        if (gasto_base and gasto_base.retiros_socios_monto and ventas_mes_base)
        else 0.0
    )

    meses_lista = meses_del_rango(hoy.year, hoy.month, meses)

    fijos_por_mes: dict[tuple[int, int], dict] = {}
    cuota_por_mes: dict[tuple[int, int], float] = {}
    intereses_por_mes: dict[tuple[int, int], float] = {}
    capital_por_mes: dict[tuple[int, int], float] = {}
    for anio, mes in meses_lista:
        gasto_mes = await _gasto_del_mes(db, anio, mes)
        fijos_por_mes[(anio, mes)] = {
            "sueldos_y_cargas": -abs(float(gasto_mes.sueldos_monto)) if gasto_mes else 0.0,
            "casilla": -abs(float(gasto_mes.casilla_monto)) if gasto_mes and gasto_mes.casilla_monto else 0.0,
            "ingresos_brutos": -abs(float(gasto_mes.ingresos_brutos_monto)) if gasto_mes and gasto_mes.ingresos_brutos_monto else 0.0,
            "iva": -abs(float(gasto_mes.iva_monto)) if gasto_mes and gasto_mes.iva_monto else 0.0,
        }
        cuota_total, intereses_pos, capital_pos = await _cuotas_del_mes(db, anio, mes)
        cuota_por_mes[(anio, mes)] = cuota_total
        intereses_por_mes[(anio, mes)] = intereses_pos or 0.0
        capital_por_mes[(anio, mes)] = capital_pos or 0.0

    filas = calcular_proyeccion_escenario(
        meses_lista,
        ventas_mes_base=ventas_mes_base,
        saldo_caja_inicial=float(cierre.saldo_caja_bancos),
        crecimiento_ventas_mensual=float(fila_escenario.crecimiento_ventas_mensual),
        margen_bruto=float(fila_escenario.margen_bruto),
        inflacion_gastos_mensual=float(fila_escenario.inflacion_gastos_mensual),
        alicuota_ganancias=float(fila_escenario.alicuota_ganancias),
        retiros_pct_ventas=retiros_pct_ventas,
        gastos_variables_base=gastos_variables_base,
        gastos_fijos_base=gastos_fijos_base,
        fijos_por_mes=fijos_por_mes,
        cuota_deuda_por_mes=cuota_por_mes,
        intereses_por_mes=intereses_por_mes,
        capital_por_mes=capital_por_mes,
    )
    cobertura = calcular_cobertura(filas)

    return ProyeccionResumenOut(
        escenario=escenario,
        supuestos=EscenarioProyeccionOut(
            id=fila_escenario.id, nombre=fila_escenario.nombre,
            crecimiento_ventas_mensual=float(fila_escenario.crecimiento_ventas_mensual),
            margen_bruto=float(fila_escenario.margen_bruto),
            inflacion_gastos_mensual=float(fila_escenario.inflacion_gastos_mensual),
            alicuota_iva=float(fila_escenario.alicuota_iva), alicuota_ganancias=float(fila_escenario.alicuota_ganancias),
        ),
        ebitda_total=cobertura["ebitda_total"],
        servicio_deuda_total=cobertura["servicio_deuda_total"],
        cobertura=cobertura["cobertura"],
        deficit=cobertura["deficit"],
        filas=[
            FilaProyeccionOut(etiqueta=etiqueta_mes(f.anio, f.mes), **dataclasses.asdict(f))
            for f in filas
        ],
    )
