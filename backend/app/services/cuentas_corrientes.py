"""Parseo y aplicación de los reportes 'Saldos Detallados por cliente y
comprobante' de Axum (Cuenta Corriente) -- tanto el filtrado por vendedor
como el filtrado por zona comparten el mismo formato jerárquico:

  Fila de nombre:        [Razón social, Domicilio, '', '']
  Fila de código+saldo:  [Código, '', '', Monto total adeudado]
  (0 o más filas de metadata: alias comercial/ciudad/teléfono o una nota
   libre -- no vuelven a traer el código, así que se ignoran para la
   identidad del cliente, que ya quedó fijada)
  (0 o más comprobantes): [FechaMov, FechaVenc, Comprobante, Monto], cada
   uno opcionalmente precedido por una nota "INTERES DIARIO X% - N DIAS
   (d/m)" cuando el comprobante es una Nota de Débito (NDX) por interés.

El archivo cierra con una fila "Total General:" que hay que ignorar (mismo
problema que ya tuvimos con el reporte de ventas: si no se filtra, se cuela
como un comprobante gigante del último cliente)."""

import datetime
import hashlib
import re
import uuid
from dataclasses import dataclass, field

import xlrd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente
from app.models.cuenta_corriente import CuentaCorrienteCarga, CuentaCorrienteComprobante
from app.models.zona import Zona
from app.services.importers import _normalizar_codigo

_RE_CODIGO = re.compile(r"^\d[\d.]*$")
_RE_COMPROBANTE = re.compile(r"^([A-Za-z]+)(\d+)$")
_RE_FILTRO = re.compile(r"(vendedor|zona)\s+en\s*\((.+)\)", re.IGNORECASE)


def _es_fecha_excel(valor: object) -> bool:
    return isinstance(valor, float) and valor > 20000


def _a_fecha(valor: float, datemode: int) -> datetime.date:
    return xlrd.xldate.xldate_as_datetime(valor, datemode).date()


def calcular_hash_archivo(contenido: bytes) -> str:
    """Hash del contenido crudo del archivo, para detectar que ya se subió
    este mismo archivo antes (sin importar el nombre con el que se lo suba)."""
    return hashlib.sha256(contenido).hexdigest()


async def buscar_carga_duplicada(db: AsyncSession, contenido_hash: str) -> CuentaCorrienteCarga | None:
    """Carga exitosa más reciente con exactamente el mismo contenido, si
    existe. Los intentos fallidos o ya marcados como duplicados no cuentan
    -- solo importa si ESE archivo ya se procesó de verdad alguna vez."""
    return (
        await db.execute(
            select(CuentaCorrienteCarga)
            .where(CuentaCorrienteCarga.contenido_hash == contenido_hash, CuentaCorrienteCarga.estado == "exitoso")
            .order_by(CuentaCorrienteCarga.creado_en.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


@dataclass
class LineaComprobanteCC:
    comprobante_numero: str | None
    comprobante_tipo: str | None
    fecha_comprobante: datetime.date | None
    fecha_vencimiento: datetime.date | None
    monto: float
    es_interes: bool
    fecha_interes: datetime.date | None
    nd_numero: str | None
    detalle_interes: str | None


@dataclass
class ClienteCC:
    cliente_codigo: str
    cliente_razon_social: str
    cliente_direccion: str | None
    monto_total_cliente: float
    comprobantes: list[LineaComprobanteCC] = field(default_factory=list)


@dataclass
class CargaCCParseada:
    tipo_archivo: str  # "vendedor" | "zona"
    filtro_original: str | None
    clientes: list[ClienteCC] = field(default_factory=list)


def parse_cuenta_corriente_xls(contenido: bytes, tipo_archivo: str) -> CargaCCParseada:
    try:
        wb = xlrd.open_workbook(file_contents=contenido)
    except Exception as exc:
        raise ValueError("No pude leer el archivo de cuenta corriente (.xls)") from exc

    sh = wb.sheet_by_index(0)

    filtro_original: str | None = None
    for r in range(min(sh.nrows, 6)):
        celda = sh.cell_value(r, 2) if sh.ncols > 2 else ""
        if isinstance(celda, str):
            m = _RE_FILTRO.search(celda)
            if m:
                filtro_original = m.group(2).strip()
                break

    clientes: list[ClienteCC] = []
    actual: ClienteCC | None = None
    nombre_pendiente: str | None = None
    direccion_pendiente: str | None = None
    nota_interes_pendiente: str | None = None

    for r in range(sh.nrows):
        row = list(sh.row_values(r))
        while len(row) < 4:
            row.append("")
        col0, col1, col2, col3 = row[0], row[1], row[2], row[3]

        # Pie de página del reporte entero: no es un comprobante de nadie.
        if isinstance(col2, str) and col2.strip().lower().startswith("total general"):
            continue

        # Comprobante: dos fechas de Excel seguidas del código de comprobante.
        if _es_fecha_excel(col0) and _es_fecha_excel(col1) and isinstance(col2, str) and col2.strip():
            if actual is None:
                continue  # todavía no vimos ningún cliente (basura de encabezado)
            comprobante = col2.strip()
            match = _RE_COMPROBANTE.match(comprobante)
            tipo, numero = (match.group(1), match.group(2)) if match else (None, comprobante)
            monto = float(col3) if isinstance(col3, (int, float)) else 0.0
            es_interes = tipo == "NDX"
            actual.comprobantes.append(
                LineaComprobanteCC(
                    comprobante_numero=numero,
                    comprobante_tipo=tipo,
                    fecha_comprobante=_a_fecha(col0, wb.datemode),
                    fecha_vencimiento=_a_fecha(col1, wb.datemode),
                    monto=monto,
                    es_interes=es_interes,
                    fecha_interes=_a_fecha(col0, wb.datemode) if es_interes else None,
                    nd_numero=numero if es_interes else None,
                    detalle_interes=nota_interes_pendiente if es_interes else None,
                )
            )
            nota_interes_pendiente = None
            continue

        # Código + saldo total del cliente: única fila con columnas 1 y 2
        # vacías y un monto numérico en la 3, con el código en la 0. Cierra
        # (si había) al cliente anterior y abre uno nuevo con el nombre
        # "pendiente" más reciente.
        if (
            isinstance(col0, str)
            and _RE_CODIGO.match(col0.strip())
            and not str(col1).strip()
            and not str(col2).strip()
            and isinstance(col3, (int, float))
        ):
            if actual is not None:
                clientes.append(actual)
            codigo = _normalizar_codigo(col0)
            actual = ClienteCC(
                cliente_codigo=codigo,
                cliente_razon_social=nombre_pendiente or f"Cliente {codigo}",
                cliente_direccion=direccion_pendiente,
                monto_total_cliente=float(col3),
            )
            nombre_pendiente = None
            direccion_pendiente = None
            nota_interes_pendiente = None
            continue

        # Nota de interés: precede al comprobante NDX que le sigue.
        if not str(col0).strip() and isinstance(col1, str) and col1.strip().upper().startswith("INTERES"):
            nota_interes_pendiente = col1.strip()
            continue

        # Candidato a nombre de cliente (o alias comercial de uno ya
        # confirmado -- si no lo sigue una fila de código+saldo, queda
        # pisado por el próximo nombre real sin afectar nada).
        if isinstance(col0, str) and col0.strip() and not _RE_CODIGO.match(col0.strip()):
            nombre_pendiente = col0.strip()
            direccion_pendiente = str(col1).strip() or None
            continue

        # Ciudad/teléfono, tag de antigüedad, nota libre sin interés: no
        # aportan ningún dato que necesitemos.

    if actual is not None:
        clientes.append(actual)

    if not clientes:
        raise ValueError("El archivo no tiene ningún cliente con saldo (¿formato inesperado?)")

    return CargaCCParseada(tipo_archivo=tipo_archivo, filtro_original=filtro_original, clientes=clientes)


@dataclass
class ResumenCargaCC:
    carga_id: uuid.UUID
    cantidad_registros: int
    clientes_procesados: int
    clientes_nuevos: list[str]
    vendedores_codigos: list[str]
    zonas_codigos: list[str]


async def aplicar_cuenta_corriente(
    db: AsyncSession,
    carga: CargaCCParseada,
    *,
    nombre_archivo: str,
    usuario_auth_id: uuid.UUID | None,
    usuario_nombre: str,
    contenido_hash: str,
) -> ResumenCargaCC:
    """Inserta una nueva carga (nunca reemplaza una anterior: cada archivo es
    una foto fechada, y la vista de cuenta corriente siempre muestra la foto
    más reciente por cliente) y su bitácora. Da de alta clientes que
    aparezcan por primera vez (sin zona, igual que hacen ventas/visitas);
    nunca crea zonas nuevas -- si el cliente no tiene zona asignada en nuestro
    padrón, su deuda queda cargada pero sin vendedor resuelto hasta que se
    lo asigne por el importador de clientes-por-zona."""
    clientes_existentes = dict((await db.execute(select(Cliente.codigo, Cliente.zona_codigo))).all())
    zonas_por_codigo = dict((await db.execute(select(Zona.codigo, Zona.vendedor_codigo))).all())

    clientes_nuevos: list[str] = []
    vendedores_tocados: set[str] = set()
    zonas_tocadas: set[str] = set()
    filas_db: list[CuentaCorrienteComprobante] = []
    carga_id = uuid.uuid4()

    for cliente in carga.clientes:
        if cliente.cliente_codigo not in clientes_existentes:
            await db.execute(
                pg_insert(Cliente)
                .values(
                    codigo=cliente.cliente_codigo,
                    razon_social=cliente.cliente_razon_social,
                    zona_codigo=None,
                    localidad=None,
                )
                .on_conflict_do_nothing(index_elements=["codigo"])
            )
            clientes_existentes[cliente.cliente_codigo] = None
            clientes_nuevos.append(cliente.cliente_codigo)

        zona_codigo = clientes_existentes.get(cliente.cliente_codigo)
        vendedor_codigo = zonas_por_codigo.get(zona_codigo) if zona_codigo else None
        if zona_codigo:
            zonas_tocadas.add(zona_codigo)
        if vendedor_codigo:
            vendedores_tocados.add(vendedor_codigo)

        # Cliente sin ningún comprobante detallado (el archivo solo trae su
        # saldo consolidado): igual necesita una fila para no perder el
        # monto adeudado, así que se guarda un placeholder sin comprobante.
        comprobantes = cliente.comprobantes or [None]
        for comp in comprobantes:
            filas_db.append(
                CuentaCorrienteComprobante(
                    id=uuid.uuid4(),
                    carga_id=carga_id,
                    cliente_codigo=cliente.cliente_codigo,
                    cliente_razon_social=cliente.cliente_razon_social,
                    cliente_direccion=cliente.cliente_direccion,
                    zona_codigo=zona_codigo,
                    vendedor_codigo=vendedor_codigo,
                    monto_total_cliente=cliente.monto_total_cliente,
                    comprobante_numero=comp.comprobante_numero if comp else None,
                    comprobante_tipo=comp.comprobante_tipo if comp else None,
                    fecha_comprobante=comp.fecha_comprobante if comp else None,
                    fecha_vencimiento=comp.fecha_vencimiento if comp else None,
                    monto=comp.monto if comp else 0.0,
                    es_interes=comp.es_interes if comp else False,
                    fecha_interes=comp.fecha_interes if comp else None,
                    nd_numero=comp.nd_numero if comp else None,
                    detalle_interes=comp.detalle_interes if comp else None,
                )
            )

    db.add(
        CuentaCorrienteCarga(
            id=carga_id,
            usuario_auth_id=usuario_auth_id,
            usuario_nombre=usuario_nombre,
            nombre_archivo=nombre_archivo,
            tipo_archivo=carga.tipo_archivo,
            filtro_original=carga.filtro_original,
            cantidad_registros=len(filas_db),
            clientes_procesados=len(carga.clientes),
            vendedores_codigos=sorted(vendedores_tocados),
            zonas_codigos=sorted(zonas_tocadas),
            estado="exitoso",
            contenido_hash=contenido_hash,
        )
    )
    db.add_all(filas_db)
    await db.commit()

    return ResumenCargaCC(
        carga_id=carga_id,
        cantidad_registros=len(filas_db),
        clientes_procesados=len(carga.clientes),
        clientes_nuevos=clientes_nuevos,
        vendedores_codigos=sorted(vendedores_tocados),
        zonas_codigos=sorted(zonas_tocadas),
    )


async def registrar_carga_fallida(
    db: AsyncSession,
    *,
    nombre_archivo: str,
    tipo_archivo: str,
    usuario_auth_id: uuid.UUID | None,
    usuario_nombre: str,
    error: str,
) -> None:
    """Deja constancia en la bitácora de un intento de carga que falló al
    parsear -- la auditoría de cobranzas necesita ver también los intentos
    fallidos, no solo los exitosos."""
    db.add(
        CuentaCorrienteCarga(
            id=uuid.uuid4(),
            usuario_auth_id=usuario_auth_id,
            usuario_nombre=usuario_nombre,
            nombre_archivo=nombre_archivo,
            tipo_archivo=tipo_archivo,
            filtro_original=None,
            cantidad_registros=0,
            clientes_procesados=0,
            vendedores_codigos=[],
            zonas_codigos=[],
            estado="error",
            detalle_error=error,
        )
    )
    await db.commit()


async def registrar_carga_duplicada(
    db: AsyncSession,
    *,
    nombre_archivo: str,
    tipo_archivo: str,
    usuario_auth_id: uuid.UUID | None,
    usuario_nombre: str,
    contenido_hash: str,
    carga_original: CuentaCorrienteCarga,
) -> None:
    """Deja constancia en la bitácora de un intento de subir un archivo que
    ya se había cargado con éxito antes (mismo contenido exacto) -- se
    bloquea la carga para no duplicar comprobantes, pero el intento igual
    queda registrado para la auditoría."""
    db.add(
        CuentaCorrienteCarga(
            id=uuid.uuid4(),
            usuario_auth_id=usuario_auth_id,
            usuario_nombre=usuario_nombre,
            nombre_archivo=nombre_archivo,
            tipo_archivo=tipo_archivo,
            filtro_original=None,
            cantidad_registros=0,
            clientes_procesados=0,
            vendedores_codigos=[],
            zonas_codigos=[],
            estado="duplicado",
            detalle_error=(
                f"Ya se había cargado este mismo archivo el "
                f"{carga_original.creado_en.strftime('%d/%m/%Y %H:%M')} "
                f"como '{carga_original.nombre_archivo}' (cargado por {carga_original.usuario_nombre})."
            ),
            contenido_hash=contenido_hash,
        )
    )
    await db.commit()
