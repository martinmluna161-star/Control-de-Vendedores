"""Parseo de los reportes que baja el administrador desde Axum (ventas y
recorridos/visitas) y su aplicación a la base.

Los dos formatos son bien distintos entre sí y no tienen nada que ver con el
Excel "limpio" del catálogo de productos:

- Ventas: un .xls binario (BIFF) con un reporte impreso jerárquico
  (Vendedor > Zona > Cliente > Comprobante > líneas de artículo), no una
  tabla plana. Hay que caminarlo fila por fila llevando el contexto actual.
- Visitas/recorrido (reporte_19): en realidad es HTML (Axum lo exporta con
  extensión .xls), con una tabla plana zona/codigo/tiempo/razon_social/
  horaMin/horaMax/fecha. Una fila por cliente-evento; "NoVisito" en
  horaMin/horaMax/fecha indica que el cliente estaba en el recorrido
  proyectado pero no fue visitado ese día.
"""

import datetime
import io
import re
from dataclasses import dataclass, field

import openpyxl
import xlrd
from lxml import etree
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente
from app.models.objetivo import ObjetivoSugerido
from app.models.producto import ProductoFamilia
from app.models.vendedor import Vendedor
from app.models.venta import VentaDetalle
from app.models.visita import VisitaReal
from app.models.zona import Zona
from app.services.metrics import hora_a_segundos


def _normalizar_codigo(valor: object) -> str:
    """Los códigos (cliente/vendedor/zona) a veces vienen con puntos como
    separador de miles (ej. "3.608") o como float de Excel (ej. 2.0);
    siempre los guardamos como el entero "puro" en string (ej. "3608", "2")."""
    if isinstance(valor, float):
        return str(int(valor)) if valor == int(valor) else str(valor).strip()
    texto = str(valor).strip()
    if re.fullmatch(r"\d[\d.]*", texto):
        return texto.replace(".", "")
    return texto


# ---------------------------------------------------------------------------
# Ventas
# ---------------------------------------------------------------------------


@dataclass
class LineaVenta:
    fecha: datetime.date
    vendedor_codigo: str
    zona_codigo: str | None
    zona_nombre: str | None
    cliente_codigo: str
    cliente_razon_social: str
    cliente_localidad: str | None
    comprobante_tipo: str | None
    comprobante_numero: str | None
    codigo_articulo: str
    descripcion_articulo: str
    unidades: float
    importe: float
    descuento: float


_RE_CLIENTE_CODIGO = re.compile(r"^\d[\d.]*$")
_RE_COMPROBANTE = re.compile(r"^([A-Za-z]+)(\d+)$")


def parse_ventas_xls(contenido: bytes) -> list[LineaVenta]:
    try:
        wb = xlrd.open_workbook(file_contents=contenido)
    except Exception as exc:
        raise ValueError("No pude leer el archivo de ventas (.xls)") from exc

    sh = wb.sheet_by_index(0)
    lineas: list[LineaVenta] = []

    vendedor_codigo: str | None = None
    zona_codigo: str | None = None
    zona_nombre: str | None = None
    cliente_codigo: str | None = None
    cliente_razon_social: str | None = None
    cliente_localidad: str | None = None
    fecha: datetime.date | None = None
    comprobante_tipo: str | None = None
    comprobante_numero: str | None = None

    for r in range(sh.nrows):
        row = sh.row_values(r)
        col0 = row[0]

        if col0 == "Vendedor :":
            vendedor_codigo = _normalizar_codigo(row[1])
            continue

        if isinstance(col0, str) and col0.strip() == "Zona":
            zona_codigo = _normalizar_codigo(row[1])
            zona_nombre = str(row[2]).strip() or None if len(row) > 2 else None
            continue

        if isinstance(col0, str) and col0.strip().startswith("Cod Ven"):
            continue  # ya tenemos el vendedor del bloque "Vendedor :"

        # Fila de cierre del reporte entero (pie de página, una sola vez al
        # final): tiene la misma forma que una fila de subtotal de
        # comprobante (mismas columnas de unidades/importe/descuento), pero
        # "Total General" cae en la columna que normalmente trae el código
        # de artículo -- sin este chequeo se cuela como una línea de venta
        # gigante para el último cliente/fecha vistos.
        if len(row) > 2 and isinstance(row[2], str) and row[2].strip().lower().startswith("total general"):
            continue

        if isinstance(col0, str) and _RE_CLIENTE_CODIGO.match(col0.strip()) and str(row[2]).strip():
            cliente_codigo = _normalizar_codigo(col0)
            cliente_razon_social = str(row[2]).strip()
            cliente_localidad = str(row[8]).strip() or None if len(row) > 8 else None
            continue

        if isinstance(col0, float) and col0 > 30000 and isinstance(row[1], str) and row[1].strip():
            fecha = xlrd.xldate.xldate_as_datetime(col0, wb.datemode).date()
            match = _RE_COMPROBANTE.match(row[1].strip())
            comprobante_tipo, comprobante_numero = (match.group(1), match.group(2)) if match else (None, row[1].strip())
            continue

        # Línea de artículo: código en col2, descripción en col3, unidades en
        # col8, importe en col9, descuento en col10. Las filas de subtotal
        # tienen la misma forma pero sin código de artículo -> se ignoran.
        codigo_articulo = str(row[2]).strip() if len(row) > 2 else ""
        if codigo_articulo and vendedor_codigo and cliente_codigo and fecha:
            descripcion = str(row[3]).strip() if len(row) > 3 else ""
            unidades = float(row[8]) if len(row) > 8 and row[8] not in ("", None) else 0.0
            importe = float(row[9]) if len(row) > 9 and row[9] not in ("", None) else 0.0
            descuento = float(row[10]) if len(row) > 10 and row[10] not in ("", None) else 0.0
            lineas.append(
                LineaVenta(
                    fecha=fecha,
                    vendedor_codigo=vendedor_codigo,
                    zona_codigo=zona_codigo,
                    zona_nombre=zona_nombre,
                    cliente_codigo=cliente_codigo,
                    cliente_razon_social=cliente_razon_social or f"Cliente {cliente_codigo}",
                    cliente_localidad=cliente_localidad,
                    comprobante_tipo=comprobante_tipo,
                    comprobante_numero=comprobante_numero,
                    codigo_articulo=codigo_articulo,
                    descripcion_articulo=descripcion,
                    unidades=unidades,
                    importe=importe,
                    descuento=descuento,
                )
            )

    return lineas


@dataclass
class ResumenImportacion:
    filas_importadas: int = 0
    vendedores_nuevos: list[str] = field(default_factory=list)
    zonas_nuevas: list[str] = field(default_factory=list)
    clientes_nuevos: list[str] = field(default_factory=list)
    clientes_actualizados: list[str] = field(default_factory=list)


async def aplicar_ventas(db: AsyncSession, lineas: list[LineaVenta]) -> ResumenImportacion:
    resumen = ResumenImportacion()
    if not lineas:
        return resumen

    vendedores_existentes = set((await db.execute(select(Vendedor.codigo_axum))).scalars().all())
    zonas_existentes = set((await db.execute(select(Zona.codigo))).scalars().all())
    clientes_existentes = set((await db.execute(select(Cliente.codigo))).scalars().all())
    familias = {
        codigo: (fid, fdesc)
        for codigo, fid, fdesc in (
            await db.execute(select(ProductoFamilia.codigo, ProductoFamilia.familia_id, ProductoFamilia.familia_desc))
        ).all()
    }

    # Vendedores nuevos: se crean con nombre placeholder, el supervisor los
    # renombra después (mismo patrón que "cliente fuera de zona").
    vendedores_vistos: dict[str, None] = {}
    zonas_vistas: dict[str, tuple[str | None, str]] = {}
    clientes_vistos: dict[str, tuple[str, str | None, str | None]] = {}
    for linea in lineas:
        vendedores_vistos.setdefault(linea.vendedor_codigo, None)
        if linea.zona_codigo:
            zonas_vistas.setdefault(linea.zona_codigo, (linea.vendedor_codigo, linea.zona_nombre or f"Zona {linea.zona_codigo}"))
        clientes_vistos.setdefault(
            linea.cliente_codigo, (linea.cliente_razon_social, linea.zona_codigo, linea.cliente_localidad)
        )

    for codigo in vendedores_vistos:
        if codigo in vendedores_existentes:
            continue
        await db.execute(
            pg_insert(Vendedor)
            .values(codigo_axum=codigo, nombre=f"Vendedor {codigo}", rol="vendedor", activo=True)
            .on_conflict_do_nothing(index_elements=["codigo_axum"])
        )
        vendedores_existentes.add(codigo)
        resumen.vendedores_nuevos.append(codigo)

    for codigo, (vendedor_codigo, nombre) in zonas_vistas.items():
        if codigo in zonas_existentes:
            continue
        await db.execute(
            pg_insert(Zona)
            .values(codigo=codigo, nombre=nombre, vendedor_codigo=vendedor_codigo, dia_venta="", dia_entrega="")
            .on_conflict_do_nothing(index_elements=["codigo"])
        )
        zonas_existentes.add(codigo)
        resumen.zonas_nuevas.append(codigo)

    for codigo, (razon_social, zona_codigo, localidad) in clientes_vistos.items():
        if codigo in clientes_existentes:
            continue
        # Nunca pisamos la zona de un cliente ya existente (el listado de
        # clientes x zona es la fuente de verdad); para uno nuevo, la zona de
        # este reporte es mejor que nada.
        zona_valida = zona_codigo if zona_codigo in zonas_existentes else None
        await db.execute(
            pg_insert(Cliente)
            .values(codigo=codigo, razon_social=razon_social, zona_codigo=zona_valida, localidad=localidad)
            .on_conflict_do_nothing(index_elements=["codigo"])
        )
        clientes_existentes.add(codigo)
        resumen.clientes_nuevos.append(codigo)

    # Reemplaza lo ya cargado para cada (vendedor, fecha) del archivo, para
    # que reimportar el mismo reporte sea idempotente.
    pares_vendedor_fecha = {(linea.vendedor_codigo, linea.fecha) for linea in lineas}
    for vendedor_codigo, fecha in pares_vendedor_fecha:
        await db.execute(
            delete(VentaDetalle).where(VentaDetalle.vendedor_codigo == vendedor_codigo, VentaDetalle.fecha == fecha)
        )

    for linea in lineas:
        familia_id, familia_desc = familias.get(linea.codigo_articulo, (None, None))
        db.add(
            VentaDetalle(
                fecha=linea.fecha,
                vendedor_codigo=linea.vendedor_codigo,
                cliente_codigo=linea.cliente_codigo,
                comprobante_tipo=linea.comprobante_tipo,
                comprobante_numero=linea.comprobante_numero,
                codigo_articulo=linea.codigo_articulo,
                descripcion_articulo=linea.descripcion_articulo,
                familia=familia_desc,
                familia_id=familia_id,
                unidades=linea.unidades,
                importe=linea.importe,
                descuento=linea.descuento,
            )
        )
        resumen.filas_importadas += 1

    await db.commit()
    return resumen


# ---------------------------------------------------------------------------
# Clientes x zona (padrón completo de clientes activos)
# ---------------------------------------------------------------------------


@dataclass
class FilaClienteZona:
    cliente_codigo: str
    razon_social: str
    localidad: str | None
    zona_codigo: str
    zona_nombre: str


def parse_clientes_zona_xls(contenido: bytes) -> list[FilaClienteZona]:
    """Carga el 'Listado de detalle de clientes activos' de Axum (.xls): el
    padrón completo, con la zona y localidad de cada cliente. A diferencia de
    ventas/visitas, acá SÍ pisamos la zona de un cliente ya existente -- este
    listado es la fuente de verdad de zona/localidad, no una atribución
    incidental sacada de una transacción."""
    try:
        wb = xlrd.open_workbook(file_contents=contenido)
    except Exception as exc:
        raise ValueError("No pude leer el listado de clientes por zona (.xls)") from exc

    sh = wb.sheet_by_index(0)
    filas: list[FilaClienteZona] = []
    for r in range(sh.nrows):
        row = sh.row_values(r)
        if len(row) < 8:
            continue
        codigo_raw, razon_social_raw, localidad_raw, zona_nombre_raw, zona_num_raw = (
            row[1],
            row[2],
            row[5],
            row[6],
            row[7],
        )
        if codigo_raw in ("", None) or zona_num_raw in ("", None):
            continue
        codigo = _normalizar_codigo(codigo_raw)
        if not codigo or not codigo[0].isdigit():
            continue  # descarta la fila de encabezado ("Cód.")
        razon_social = str(razon_social_raw).strip()
        if not razon_social:
            continue
        filas.append(
            FilaClienteZona(
                cliente_codigo=codigo,
                razon_social=razon_social,
                localidad=str(localidad_raw).strip() or None,
                zona_codigo=_normalizar_codigo(zona_num_raw),
                zona_nombre=str(zona_nombre_raw).strip() or f"Zona {_normalizar_codigo(zona_num_raw)}",
            )
        )
    return filas


async def aplicar_clientes_zona(db: AsyncSession, filas: list[FilaClienteZona]) -> ResumenImportacion:
    """Aplica el padrón de clientes x zona: crea zonas nuevas que aparezcan
    (sin vendedor asignado, para que el supervisor lo complete), crea
    clientes nuevos con su zona, y actualiza la zona/localidad de clientes
    ya existentes cuando el listado trae un valor distinto. Nunca toca
    nombre/vendedor de una zona ya existente -- esos datos los administra el
    supervisor a mano y este listado no los conoce."""
    resumen = ResumenImportacion()
    if not filas:
        return resumen

    zonas_existentes = set((await db.execute(select(Zona.codigo))).scalars().all())
    clientes_actuales = dict((await db.execute(select(Cliente.codigo, Cliente.zona_codigo))).all())

    # Si el listado trae el mismo código más de una vez, se queda con la
    # última aparición (son filas de un padrón, no eventos independientes).
    por_cliente: dict[str, FilaClienteZona] = {}
    zonas_vistas: dict[str, str] = {}
    for fila in filas:
        por_cliente[fila.cliente_codigo] = fila
        zonas_vistas.setdefault(fila.zona_codigo, fila.zona_nombre)

    for codigo, nombre in zonas_vistas.items():
        if codigo in zonas_existentes:
            continue
        await db.execute(
            pg_insert(Zona)
            .values(codigo=codigo, nombre=nombre, vendedor_codigo=None, dia_venta="", dia_entrega="")
            .on_conflict_do_nothing(index_elements=["codigo"])
        )
        zonas_existentes.add(codigo)
        resumen.zonas_nuevas.append(codigo)

    for codigo, fila in por_cliente.items():
        if codigo not in clientes_actuales:
            await db.execute(
                pg_insert(Cliente)
                .values(
                    codigo=codigo,
                    razon_social=fila.razon_social,
                    zona_codigo=fila.zona_codigo,
                    localidad=fila.localidad,
                )
                .on_conflict_do_nothing(index_elements=["codigo"])
            )
            clientes_actuales[codigo] = fila.zona_codigo
            resumen.clientes_nuevos.append(codigo)
            resumen.filas_importadas += 1
            continue
        if clientes_actuales[codigo] != fila.zona_codigo:
            await db.execute(
                update(Cliente)
                .where(Cliente.codigo == codigo)
                .values(zona_codigo=fila.zona_codigo, localidad=fila.localidad)
            )
            clientes_actuales[codigo] = fila.zona_codigo
            resumen.clientes_actualizados.append(codigo)
            resumen.filas_importadas += 1

    await db.commit()
    return resumen


# ---------------------------------------------------------------------------
# Visitas / recorrido (reporte_19)
# ---------------------------------------------------------------------------


@dataclass
class FilaVisita:
    zona_codigo: str
    cliente_codigo: str
    cliente_razon_social: str
    tiempo_seg: int
    hora_min: str | None
    hora_max: str | None
    visitado: bool


def _parsear_tiempo(texto: str) -> int:
    texto = texto.strip()
    if not texto or texto == "0":
        return 0
    partes = texto.split(":")
    try:
        minutos, segundos = int(partes[0]), int(partes[1])
    except (ValueError, IndexError):
        return 0
    return minutos * 60 + segundos


def parse_visitas_html(contenido: bytes) -> list[FilaVisita]:
    try:
        tree = etree.parse(io.BytesIO(contenido), etree.HTMLParser())
    except Exception as exc:
        raise ValueError("No pude leer el reporte de visitas") from exc

    filas_html = tree.xpath("//table[@id='gw_Reporte']//tr")
    if not filas_html:
        raise ValueError("El reporte no tiene la tabla 'gw_Reporte' esperada")

    resultado: list[FilaVisita] = []
    for tr in filas_html[1:]:  # la primera es el encabezado
        celdas = [td.text.strip() if td.text else "" for td in tr.xpath(".//td")]
        if len(celdas) < 7:
            continue
        zona, codigo, tiempo, razon_social, hora_min, hora_max, fecha = celdas[:7]
        visitado = fecha.strip() != "NoVisito"
        # La duración real sale de HoraMin/HoraMax (más confiable que el texto
        # "Tiempo", que en visitas largas puede venir en un formato ambiguo
        # tipo "79:25:00"); si no se puede derivar, cae al texto.
        inicio_seg = hora_a_segundos(hora_min) if visitado else None
        fin_seg = hora_a_segundos(hora_max) if visitado else None
        if visitado and inicio_seg is not None and fin_seg is not None and fin_seg >= inicio_seg:
            tiempo_seg = fin_seg - inicio_seg
        else:
            tiempo_seg = _parsear_tiempo(tiempo) if visitado else 0
        resultado.append(
            FilaVisita(
                zona_codigo=zona.strip() or "SIN_ZONA",
                cliente_codigo=_normalizar_codigo(codigo),
                cliente_razon_social=razon_social,
                tiempo_seg=tiempo_seg,
                hora_min=hora_min if visitado else None,
                hora_max=hora_max if visitado else None,
                visitado=visitado,
            )
        )
    return resultado


# Una visita con check-in pero de menos de 1 minuto es, con altísima
# probabilidad, un error de carga del vendedor (pasó y marcó sin atender al
# cliente) -- no cuenta como visitada. Una de más de 30 minutos se marca para
# que el supervisor la revise (puede ser una demora real o un olvido de cierre).
UMBRAL_VISITA_CORTA_SEG = 60
UMBRAL_VISITA_LARGA_SEG = 1800


async def aplicar_visitas(db: AsyncSession, fecha: datetime.date, filas: list[FilaVisita]) -> ResumenImportacion:
    resumen = ResumenImportacion()
    if not filas:
        return resumen

    clientes_existentes = set((await db.execute(select(Cliente.codigo))).scalars().all())
    zonas_por_codigo = dict((await db.execute(select(Zona.codigo, Zona.vendedor_codigo))).all())

    for fila in filas:
        zona_normalizada = _normalizar_codigo(fila.zona_codigo) if fila.zona_codigo != "SIN_ZONA" else "SIN_ZONA"
        if zona_normalizada != "SIN_ZONA" and zona_normalizada not in zonas_por_codigo:
            await db.execute(
                pg_insert(Zona)
                .values(codigo=zona_normalizada, nombre=f"Zona {zona_normalizada}", vendedor_codigo=None, dia_venta="", dia_entrega="")
                .on_conflict_do_nothing(index_elements=["codigo"])
            )
            zonas_por_codigo[zona_normalizada] = None
            resumen.zonas_nuevas.append(zona_normalizada)

        if fila.cliente_codigo not in clientes_existentes:
            zona_cliente = zona_normalizada if zona_normalizada != "SIN_ZONA" else None
            await db.execute(
                pg_insert(Cliente)
                .values(
                    codigo=fila.cliente_codigo,
                    razon_social=fila.cliente_razon_social or f"Cliente {fila.cliente_codigo}",
                    zona_codigo=zona_cliente,
                    localidad=None,
                )
                .on_conflict_do_nothing(index_elements=["codigo"])
            )
            clientes_existentes.add(fila.cliente_codigo)
            resumen.clientes_nuevos.append(fila.cliente_codigo)

    await db.execute(delete(VisitaReal).where(VisitaReal.fecha == fecha))

    for fila in filas:
        zona_normalizada = _normalizar_codigo(fila.zona_codigo) if fila.zona_codigo != "SIN_ZONA" else "SIN_ZONA"
        vendedor_codigo = zonas_por_codigo.get(zona_normalizada)
        corta = fila.visitado and fila.tiempo_seg < UMBRAL_VISITA_CORTA_SEG
        valida = fila.visitado and not corta
        db.add(
            VisitaReal(
                zona_codigo=zona_normalizada,
                vendedor_codigo=vendedor_codigo,
                cliente_codigo=fila.cliente_codigo,
                fecha=fecha,
                hora_min=fila.hora_min,
                hora_max=fila.hora_max,
                tiempo_seg=fila.tiempo_seg,
                valida=valida,
                corta=corta,
                larga=valida and fila.tiempo_seg >= UMBRAL_VISITA_LARGA_SEG,
            )
        )
        resumen.filas_importadas += 1

    await db.commit()
    return resumen


# ---------------------------------------------------------------------------
# Objetivos sugeridos (proyección optimista/realista armada fuera del sistema)
# ---------------------------------------------------------------------------

# El archivo trae el nombre "de fantasía" del vendedor (a veces "Apellido
# Nombre", a veces solo el nombre), no su código Axum. Como este dato define
# el objetivo de venta de cada uno, preferimos fallar fuerte ante un nombre
# desconocido antes que adivinar por similitud de texto -- si cambia el
# plantel, hay que sumar la fila acá.
MAPEO_VENDEDOR_PROYECCION: dict[str, str] = {
    "Cardozo Emmanuel": "35",
    "Grisanti Dayana": "25",
    "Curi Ezequiel": "28",
    "Cabañez Diego": "27",
    "Alfonso Ariel": "36",
    "Lucero Jonathan": "12",  # "Chino" en el sistema
    "Miraglia Hugo Gastronomico": "32",
    "Lucero Ruben": "7",
    "Sotille Lorena": "26",
    "Deposito San Luis": "2",
    "Olave Veronica": "31",
    "Juan Pablo": "39",
}


@dataclass
class FilaObjetivoSugerido:
    vendedor_codigo: str
    objetivo_mes_anterior: float | None
    real_mes_anterior: float | None
    pct_cumplimiento_mes_anterior: float | None
    piso_recuperado: float | None
    crecimiento_aplicado_pct: float | None
    objetivo_sugerido: float
    variacion_vs_objetivo_anterior_pct: float | None


def _num(valor: object) -> float | None:
    return float(valor) if isinstance(valor, (int, float)) else None


def _pct(valor: object) -> float | None:
    numero = _num(valor)
    return round(numero * 100, 2) if numero is not None else None


def parse_objetivos_sugeridos_xlsx(contenido: bytes) -> list[FilaObjetivoSugerido]:
    """Parsea la planilla de proyección de objetivos (una fila por vendedor,
    con el nombre en la primera columna y el resto de las columnas en el
    orden: objetivo del mes anterior, real del mes anterior, % de
    cumplimiento, piso recuperado, % de crecimiento aplicado, objetivo
    sugerido para el mes nuevo, variación vs. el objetivo anterior).

    Ubica la fila de encabezado buscando la celda "Vendedor" en vez de asumir
    un número de fila fijo, porque el archivo trae título/subtítulo arriba
    (y notas metodológicas variables abajo)."""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True)
    except Exception as exc:
        raise ValueError("No pude leer el archivo de proyección (.xlsx)") from exc

    filas_crudas = list(wb.worksheets[0].iter_rows(values_only=True))
    inicio = next(
        (i for i, fila in enumerate(filas_crudas) if fila and str(fila[0] or "").strip().lower() == "vendedor"),
        None,
    )
    if inicio is None:
        raise ValueError("No encontré la fila de encabezado ('Vendedor') en el archivo")

    resultado: list[FilaObjetivoSugerido] = []
    for fila in filas_crudas[inicio + 1 :]:
        nombre = str(fila[0] or "").strip() if fila else ""
        if not nombre:
            break
        if nombre.upper() == "TOTAL":
            break
        codigo = MAPEO_VENDEDOR_PROYECCION.get(nombre)
        if codigo is None:
            raise ValueError(
                f"No reconozco al vendedor '{nombre}' del archivo de proyección. "
                "Sumalo a MAPEO_VENDEDOR_PROYECCION en app/services/importers.py con su código Axum."
            )
        if _num(fila[6]) is None:
            raise ValueError(f"Falta el objetivo sugerido para '{nombre}' (columna 7)")
        resultado.append(
            FilaObjetivoSugerido(
                vendedor_codigo=codigo,
                objetivo_mes_anterior=_num(fila[1]),
                real_mes_anterior=_num(fila[2]),
                pct_cumplimiento_mes_anterior=_pct(fila[3]),
                piso_recuperado=_num(fila[4]),
                crecimiento_aplicado_pct=_pct(fila[5]),
                objetivo_sugerido=_num(fila[6]),
                variacion_vs_objetivo_anterior_pct=_pct(fila[7]),
            )
        )

    if not resultado:
        raise ValueError("El archivo no tiene filas de vendedores")
    return resultado


async def aplicar_objetivos_sugeridos(
    db: AsyncSession, anio: int, mes: int, filas: list[FilaObjetivoSugerido]
) -> int:
    """Guarda (o reemplaza) los objetivos sugeridos de un período. Es solo
    informativo para supervisor/admin -- no toca ``ObjetivoMensual``, que es
    el objetivo real que ve el vendedor y que se sigue definiendo a mano."""
    for fila in filas:
        stmt = (
            pg_insert(ObjetivoSugerido)
            .values(
                vendedor_codigo=fila.vendedor_codigo,
                anio=anio,
                mes=mes,
                objetivo_mes_anterior=fila.objetivo_mes_anterior,
                real_mes_anterior=fila.real_mes_anterior,
                pct_cumplimiento_mes_anterior=fila.pct_cumplimiento_mes_anterior,
                piso_recuperado=fila.piso_recuperado,
                crecimiento_aplicado_pct=fila.crecimiento_aplicado_pct,
                objetivo_sugerido=fila.objetivo_sugerido,
                variacion_vs_objetivo_anterior_pct=fila.variacion_vs_objetivo_anterior_pct,
            )
            .on_conflict_do_update(
                index_elements=["vendedor_codigo", "anio", "mes"],
                set_={
                    "objetivo_mes_anterior": fila.objetivo_mes_anterior,
                    "real_mes_anterior": fila.real_mes_anterior,
                    "pct_cumplimiento_mes_anterior": fila.pct_cumplimiento_mes_anterior,
                    "piso_recuperado": fila.piso_recuperado,
                    "crecimiento_aplicado_pct": fila.crecimiento_aplicado_pct,
                    "objetivo_sugerido": fila.objetivo_sugerido,
                    "variacion_vs_objetivo_anterior_pct": fila.variacion_vs_objetivo_anterior_pct,
                },
            )
        )
        await db.execute(stmt)
    await db.commit()
    return len(filas)
