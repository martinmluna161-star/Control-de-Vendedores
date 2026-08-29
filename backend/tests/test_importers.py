import io

import openpyxl
import pytest

from app.services.importers import parse_objetivos_sugeridos_xlsx, parse_visitas_html

HTML_EJEMPLO = """<html><body>
<table id="gw_Reporte">
<tr><th>zona</th><th>codigo</th><th>Tiempo (mm:ss)</th><th>razon_social</th><th>HoraMin</th><th>HoraMax</th><th>Fecha</th></tr>
<tr><td>01</td><td>472</td><td>0</td><td>CLIENTE NO VISITADO</td><td>NoVisito</td><td>NoVisito</td><td>NoVisito</td></tr>
<tr><td>1</td><td>3.608</td><td>5:30</td><td>CLIENTE VISITADO</td><td>09:00:00</td><td>09:05:30</td><td>08/19/2026</td></tr>
</table>
</body></html>"""


def test_parse_visitas_html_distingue_visitado_de_no_visitado():
    filas = parse_visitas_html(HTML_EJEMPLO.encode("utf-8"))
    assert len(filas) == 2

    no_visitada, visitada = filas
    assert no_visitada.visitado is False
    assert no_visitada.hora_min is None
    assert no_visitada.tiempo_seg == 0

    assert visitada.visitado is True
    assert visitada.cliente_codigo == "3608"  # el punto de miles se limpia
    assert visitada.tiempo_seg == 5 * 60 + 30
    assert visitada.hora_min == "09:00:00"


def test_parse_visitas_html_sin_tabla_esperada_da_error_claro():
    import pytest

    with pytest.raises(ValueError):
        parse_visitas_html(b"<html><body>sin tabla</body></html>")


HTML_VISITA_CORTA = """<html><body>
<table id="gw_Reporte">
<tr><th>zona</th><th>codigo</th><th>Tiempo</th><th>razon_social</th><th>HoraMin</th><th>HoraMax</th><th>Fecha</th></tr>
<tr><td>1</td><td>500</td><td>0:40</td><td>CLIENTE VISITA CORTA</td><td>10:00:00</td><td>10:00:40</td><td>08/19/2026</td></tr>
</table>
</body></html>"""


HTML_TEXTO_TIEMPO_AMBIGUO = """<html><body>
<table id="gw_Reporte">
<tr><th>zona</th><th>codigo</th><th>Tiempo</th><th>razon_social</th><th>HoraMin</th><th>HoraMax</th><th>Fecha</th></tr>
<tr><td>1</td><td>501</td><td>79:25:00</td><td>CLIENTE VISITA LARGA</td><td>08:00:00</td><td>08:35:00</td><td>08/19/2026</td></tr>
</table>
</body></html>"""


def test_parse_visitas_html_deriva_duracion_de_horamin_horamax_no_del_texto():
    # El texto "Tiempo" de Axum puede venir en un formato ambiguo para
    # visitas largas (ej. "79:25:00" en vez de una duración real); HoraMin/
    # HoraMax es la fuente confiable y debe ganarle al texto.
    filas = parse_visitas_html(HTML_TEXTO_TIEMPO_AMBIGUO.encode("utf-8"))
    assert filas[0].tiempo_seg == 35 * 60  # 08:35:00 - 08:00:00, no lo que diga "79:25:00"


def test_parse_visitas_html_visita_de_menos_de_un_minuto():
    filas = parse_visitas_html(HTML_VISITA_CORTA.encode("utf-8"))
    assert filas[0].visitado is True
    assert filas[0].tiempo_seg == 40


def _xlsx_objetivos_sugeridos(filas: list[tuple]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Congelados Puntanos S.A. — Proyectado"])
    ws.append(["Escenario de máxima"])
    ws.append([])
    ws.append(
        [
            "Vendedor",
            "Objetivo mes anterior",
            "Real mes anterior",
            "% Cumplim.",
            "Piso recuperado",
            "Crecimiento aplicado",
            "Objetivo sugerido",
            "vs. Objetivo anterior",
        ]
    )
    for fila in filas:
        ws.append(list(fila))
    ws.append(["TOTAL", 100, 100, 1.0, 100, None, 100, 0.0])
    ws.append([])
    ws.append(["Metodología: nota al pie irrelevante para el parser."])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def test_parse_objetivos_sugeridos_mapea_nombre_a_codigo_y_convierte_porcentajes():
    contenido = _xlsx_objetivos_sugeridos(
        [
            ("Cardozo Emmanuel", 84_450_728.54, 72_020_617.70, 0.8528, 82_584_935.61, 0.08, 89_191_730.47, 0.0561),
            ("Lucero Jonathan", 60_824_435.19, 44_956_662.97, 0.7391, 55_717_510.11, 0.08, 60_174_910.92, -0.0107),
        ]
    )
    filas = parse_objetivos_sugeridos_xlsx(contenido)

    assert len(filas) == 2
    emanuel = filas[0]
    assert emanuel.vendedor_codigo == "35"
    assert emanuel.objetivo_sugerido == 89_191_730.47
    assert emanuel.pct_cumplimiento_mes_anterior == 85.28
    assert emanuel.crecimiento_aplicado_pct == 8.0

    chino = filas[1]
    assert chino.vendedor_codigo == "12"  # "Lucero Jonathan" = "Chino" en el sistema


def test_parse_objetivos_sugeridos_nombre_desconocido_falla_claro():
    contenido = _xlsx_objetivos_sugeridos([("Vendedor Fantasma", 1, 1, 1.0, 1, 0.08, 1, 0.0)])
    with pytest.raises(ValueError, match="Vendedor Fantasma"):
        parse_objetivos_sugeridos_xlsx(contenido)
