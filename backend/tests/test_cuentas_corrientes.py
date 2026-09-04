import io

import xlwt

from app.services.cuentas_corrientes import parse_cuenta_corriente_xls


def _armar_xls(filas: list[list], filtro: str) -> bytes:
    """Arma un .xls sintético con la misma forma que 'Saldos Detallados por
    cliente y comprobante' de Axum: 5 filas de encabezado (la 3ª -- índice 2
    -- trae 'vendedor en (...)' o 'zona en (...)' en la columna 2) y después
    las filas de datos tal cual las escribe el reporte real."""
    wb = xlwt.Workbook()
    ws = wb.add_sheet("Hoja1")
    encabezado = [
        ["", "", "Saldos Detallados por cliente y comprobante", ""],
        ["", "", "", ""],
        ["", "", filtro, ""],
        ["", "", "Fecha Limite: 30/9/2026", ""],
        ["", "", "", "Acumulado"],
        ["Fecha Mov.", "FechaVenc", "Comprobante", "Tot"],
        ["", "", "", ""],
    ]
    for r, fila in enumerate(encabezado + filas):
        for c, valor in enumerate(fila):
            ws.write(r, c, valor)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_cliente_simple_con_un_comprobante():
    contenido = _armar_xls(
        [
            ["NACHAR JORGE LUIS", "QUINES", "", ""],
            ["759", "", "", 406362.38],
            ["", "QUINES", "", "2664-730857"],
            ["", "", "", "07CC"],
            [46258.0, 46263.0, "FAA000500218931", 406362.38],
        ],
        " vendedor en (CABAÑEZ DIEGO) ",
    )
    carga = parse_cuenta_corriente_xls(contenido, "vendedor")

    assert carga.tipo_archivo == "vendedor"
    assert carga.filtro_original == "CABAÑEZ DIEGO"
    assert len(carga.clientes) == 1

    cliente = carga.clientes[0]
    assert cliente.cliente_codigo == "759"
    assert cliente.cliente_razon_social == "NACHAR JORGE LUIS"
    assert cliente.cliente_direccion == "QUINES"
    assert cliente.monto_total_cliente == 406362.38
    assert len(cliente.comprobantes) == 1

    comp = cliente.comprobantes[0]
    assert comp.comprobante_tipo == "FAA"
    assert comp.comprobante_numero == "000500218931"
    assert comp.monto == 406362.38
    assert comp.es_interes is False


def test_parse_interes_nda_captura_dias_fecha_y_nd():
    contenido = _armar_xls(
        [
            ["NACHAR JORGE LUIS", "QUINES", "", ""],
            ["759", "", "", 414489.62],
            ["", "QUINES", "", "2664-730857"],
            ["", "", "", "07CC"],
            [46258.0, 46263.0, "FAA000500218931", 406362.38],
            ["", "INTERES DIARIO 1% - 2 DIAS (2/9)", "", ""],
            [46258.0, 46258.0, "NDX000100218931", 8127.24],
        ],
        " vendedor en (CABAÑEZ DIEGO) ",
    )
    carga = parse_cuenta_corriente_xls(contenido, "vendedor")

    assert len(carga.clientes) == 1
    comprobantes = carga.clientes[0].comprobantes
    assert len(comprobantes) == 2

    interes = comprobantes[1]
    assert interes.es_interes is True
    assert interes.comprobante_tipo == "NDX"
    assert interes.nd_numero == "000100218931"
    assert interes.detalle_interes == "INTERES DIARIO 1% - 2 DIAS (2/9)"
    assert interes.fecha_interes is not None
    assert interes.monto == 8127.24

    # La factura (no-interés) no debe heredar la nota.
    assert comprobantes[0].es_interes is False
    assert comprobantes[0].detalle_interes is None


def test_parse_alias_comercial_no_crea_cliente_extra():
    # Mismo caso real que "GARRAZA JULIETA IRENE" (4344) / "ALMACEN JULIETA":
    # la fila de alias no vuelve a traer código, así que sus comprobantes
    # tienen que quedar en el cliente ya abierto, no en uno nuevo.
    contenido = _armar_xls(
        [
            ["GARRAZA JULIETA IRENE", "Bº V PRODUCTIVAS M 42 C3 LA TOMA", "", ""],
            ["4.344", "", "", -640.03],
            ["ALMACEN JULIETA", "LA TOMA", "", "2665-132250"],
            ["", "", "", "CON"],
            [46262.0, 46260.0, "FAB000500239491", 37607.82],
            ["", "", "", ""],
            [46266.0, 46266.0, "RXX000100366361", -39000.0],
        ],
        " vendedor en (CABAÑEZ DIEGO) ",
    )
    carga = parse_cuenta_corriente_xls(contenido, "vendedor")

    assert len(carga.clientes) == 1
    cliente = carga.clientes[0]
    assert cliente.cliente_codigo == "4344"
    assert cliente.cliente_razon_social == "GARRAZA JULIETA IRENE"  # no "ALMACEN JULIETA"
    assert len(cliente.comprobantes) == 2


def test_parse_cliente_sin_comprobantes_detallados_conserva_el_saldo():
    contenido = _armar_xls(
        [
            ["SLOTS MACHINES S.A.", "SAN MARTIN Nº578", "", ""],
            ["107", "", "", 333316.78],
            ["ZAVALA ALBERTO", "MARIANO MORENO 441 CONCARAN", "", ""],
            ["460", "", "", -349900.0],
            [46263.0, 46263.0, "RXX000100366044", -349900.0],
        ],
        " vendedor en (CABAÑEZ DIEGO) ",
    )
    carga = parse_cuenta_corriente_xls(contenido, "vendedor")

    assert len(carga.clientes) == 2
    slots = carga.clientes[0]
    assert slots.cliente_codigo == "107"
    assert slots.monto_total_cliente == 333316.78
    assert slots.comprobantes == []


def test_parse_ignora_total_general_final():
    contenido = _armar_xls(
        [
            ["NACHAR JORGE LUIS", "QUINES", "", ""],
            ["759", "", "", 406362.38],
            [46258.0, 46263.0, "FAA000500218931", 406362.38],
            ["", "", "Total General:", 406362.38],
        ],
        " zona en (\"1202\",\"202\") ",
    )
    carga = parse_cuenta_corriente_xls(contenido, "zona")

    assert carga.filtro_original == '"1202","202"'
    assert len(carga.clientes) == 1
    assert len(carga.clientes[0].comprobantes) == 1  # el "Total General" no se cuela como comprobante


def test_parse_archivo_vacio_da_error_claro():
    import pytest

    contenido = _armar_xls([], " vendedor en (NADIE) ")
    with pytest.raises(ValueError):
        parse_cuenta_corriente_xls(contenido, "vendedor")
