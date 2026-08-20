/**
 * ═══════════════════════════════════════════════════════════════════
 * BACKEND — Base de Zonas (Congelados Puntanos)
 * ══════════════════════════════════════════════════════════════════
 * Google Apps Script Web App que expone la Base de zonas como API,
 * usando una hoja de Google Sheets como base de datos compartida.
 *
 * INSTALACIÓN (una sola vez):
 * 1. Andá a https://sheets.google.com y creá una planilla nueva.
 *    Nombrala, por ejemplo, "Congelados Puntanos - Backend Zonas".
 * 2. Dentro de la planilla: Extensiones → Apps Script.
 * 3. Borrá el contenido de Code.gs que aparece por defecto y pegá
 *    TODO este archivo en su lugar.
 * 4. Arriba a la izquierda, en el selector de funciones, elegí
 *    "setupInicial" y hacé clic en ▶ Ejecutar. La primera vez te va
 *    a pedir autorización — dále permiso a tu propia cuenta.
 *    Esto crea la hoja "Zonas" y la llena con las 40 zonas actuales.
 * 5. Desplegar → Nueva implementación → tipo "Aplicación web".
 *      - Ejecutar como: Yo (tu cuenta)
 *      - Quién tiene acceso: Cualquier usuario
 *    Desplegar, autorizar de nuevo si lo pide, y copiar la URL que
 *    termina en /exec. Esa es la URL que vas a pegar en el HTML,
 *    en la pestaña "Base de zonas" → "⚙ Configurar backend".
 * 6. Cada vez que edites este código en el futuro, tenés que volver
 *    a "Desplegar → Administrar implementaciones → ✎ editar →
 *    Nueva versión" para que los cambios entren en vigencia en la
 *    URL /exec (guardar el archivo solo no alcanza).
 * ══════════════════════════════════════════════════════════════════
 */

const NOMBRE_HOJA = 'Zonas';
const ENCABEZADOS = ['Zona', 'Nombre', 'Vendedor', 'CodAxum', 'DiaVenta', 'DiaEntrega'];

const ZONAS_SEMILLA = [
    ['203','Barrios Nuevos','LORENA','26','Lunes/Jueves','Martes/Viernes'],
    ['207','Amppya','RUBEN','7','Lunes/Jueves','Martes/Viernes'],
    ['211','Centro II','LORENA','26','Miércoles/Sábado','Jueves/Lunes'],
    ['212','Norte','CHINO','12','Miércoles/Sábado','Jueves/Lunes'],
    ['202','Eva Perón','LORENA','26','Lunes/Jueves','Martes/Viernes'],
    ['204','Sur','CHINO','12','Martes/Viernes','Miércoles/Sábado'],
    ['205','Sur II','LORENA','26','Martes/Viernes','Miércoles/Sábado'],
    ['208','Centro Norte','RUBEN','7','Miércoles/Sábado','Jueves/Lunes'],
    ['210','Centro','RUBEN','7','Martes/Viernes','Miércoles/Sábado'],
    ['201','Juana Koslay','CHINO','12','Lunes/Jueves','Martes/Viernes'],
    ['209','La Punta','VERONICA','31','Lunes/Martes/Viernes/Sábado','Miércoles/Lunes'],
    ['10','Circuito','VERONICA','31','Jueves','Viernes'],
    ['1','ZONA 1','ARIEL','36','Lunes','Martes'],
    ['2','ZONA 2','EMANUEL','35','Lunes','Martes'],
    ['3','ZONA 3','ARIEL','36','Martes','Miércoles'],
    ['4','ZONA 4','EMANUEL','35','Martes','Miércoles'],
    ['5','ZONA 5','ARIEL','36','Miércoles','Jueves'],
    ['6','ZONA 6','EMANUEL','35','Miércoles','Jueves'],
    ['7','ZONA 7','ARIEL','36','Jueves','Viernes'],
    ['8','ZONA 8','EMANUEL','35','Jueves','Viernes'],
    ['9','ZONA 9','ARIEL','36','Viernes','Lunes'],
    ['110','ZONA 110','EMANUEL','35','Viernes','Lunes'],
    ['11','ZONA 11','EMANUEL','35','Sábado','Lunes'],
    ['120','San Francisco','DIEGO','27','Jueves/Viernes','Lunes'],
    ['121','Quines','DIEGO','27','Jueves/Viernes','Lunes'],
    ['122','San Martín','DIEGO','27','Lunes/Martes/Miércoles','Jueves/Viernes'],
    ['123','Luján','DIEGO','27','Jueves/Viernes','Lunes'],
    ['124','Nogolí','DIEGO','27','Jueves/Viernes','Lunes'],
    ['134','V. de la Quebrada','DIEGO','27','Jueves/Viernes','Lunes'],
    ['125','Merlo','DAYANA','25','Lunes/Martes/Miércoles','Jueves/Viernes'],
    ['126','Carpintería / Los Molles','DAYANA','25','Lunes/Martes/Miércoles','Jueves/Viernes'],
    ['127','Villa Larca - Cortaderas','DAYANA','25','Lunes/Martes/Miércoles','Jueves/Viernes'],
    ['128','La Toma','DIEGO','27','Lunes/Martes/Miércoles','Jueves/Viernes'],
    ['130','Naschel','DIEGO','27','Lunes/Martes/Miércoles','Jueves/Viernes'],
    ['131','Tilisarao','DIEGO','27','Lunes/Martes/Miércoles','Jueves/Viernes'],
    ['132','Concarán','DIEGO','27','Lunes/Martes/Miércoles','Jueves/Viernes'],
    ['133','Santa Rosa','DAYANA','25','Lunes/Martes/Miércoles','Jueves/Viernes'],
    ['86','Gastronómicos Villa Mercedes','EZEQUIEL','28','',''],
    ['150','Gastronómicos Villa Mercedes','JUAN PABLO','39','','']
];

/** Ejecutar UNA VEZ manualmente desde el editor de Apps Script para crear y poblar la hoja. */
function setupInicial() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let hoja = ss.getSheetByName(NOMBRE_HOJA);
  if (!hoja) hoja = ss.insertSheet(NOMBRE_HOJA);
  hoja.clear();
  hoja.getRange(1, 1, 1, ENCABEZADOS.length).setValues([ENCABEZADOS]);
  hoja.getRange(1, 1, 1, ENCABEZADOS.length).setFontWeight('bold');
  if (ZONAS_SEMILLA.length) {
    hoja.getRange(2, 1, ZONAS_SEMILLA.length, ENCABEZADOS.length).setValues(ZONAS_SEMILLA);
  }
  hoja.setFrozenRows(1);
  hoja.autoResizeColumns(1, ENCABEZADOS.length);
  Logger.log('Listo: hoja "%s" creada con %s zonas.', NOMBRE_HOJA, ZONAS_SEMILLA.length);
}

function getHoja_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let hoja = ss.getSheetByName(NOMBRE_HOJA);
  if (!hoja) {
    hoja = ss.insertSheet(NOMBRE_HOJA);
    hoja.getRange(1, 1, 1, ENCABEZADOS.length).setValues([ENCABEZADOS]);
  }
  return hoja;
}

function leerTodasLasZonas_() {
  const hoja = getHoja_();
  const filas = hoja.getDataRange().getValues();
  if (filas.length < 2) return [];
  const encabezados = filas[0].map(h => String(h).trim());
  const idx = {
    zona: encabezados.indexOf('Zona'),
    nombre: encabezados.indexOf('Nombre'),
    vendedor: encabezados.indexOf('Vendedor'),
    codAxum: encabezados.indexOf('CodAxum'),
    diaVenta: encabezados.indexOf('DiaVenta'),
    diaEntrega: encabezados.indexOf('DiaEntrega')
  };
  const out = [];
  for (let i = 1; i < filas.length; i++) {
    const f = filas[i];
    if (!f[idx.zona] && !f[idx.nombre]) continue; // fila vacía
    out.push({
      zona: String(f[idx.zona] || '').trim(),
      nombre: String(f[idx.nombre] || '').trim(),
      vendedor: String(f[idx.vendedor] || '').trim(),
      codAxum: String(f[idx.codAxum] || '').trim(),
      diaVenta: String(f[idx.diaVenta] || '').trim(),
      diaEntrega: String(f[idx.diaEntrega] || '').trim(),
      _fila: i + 1 // fila real en la hoja (1-indexed, con encabezado en la fila 1)
    });
  }
  return out;
}

function jsonResponse_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

/** GET /exec — devuelve todas las zonas actuales. */
function doGet(e) {
  try {
    const zonas = leerTodasLasZonas_().map(z => { const c = {...z}; delete c._fila; return c; });
    return jsonResponse_({ ok: true, zonas: zonas });
  } catch (err) {
    return jsonResponse_({ ok: false, error: String(err) });
  }
}

/**
 * POST /exec — body en texto plano con JSON:
 *   { action: 'upsert', zona: {zona,nombre,vendedor,codAxum,diaVenta,diaEntrega} }
 *   { action: 'delete', zona: '1203' }
 *   { action: 'bulkReplace', zonas: [ {...}, {...} ] }
 * Devuelve siempre la lista completa actualizada, igual que doGet.
 */
function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const body = JSON.parse(e.postData.contents);
    const hoja = getHoja_();

    if (body.action === 'upsert') {
      const z = body.zona;
      if (!z || !z.zona) throw new Error('Falta el código de zona');
      const actuales = leerTodasLasZonas_();
      const existente = actuales.find(x => x.zona === z.zona);
      const fila = [z.zona, z.nombre||'', z.vendedor||'', z.codAxum||'', z.diaVenta||'', z.diaEntrega||''];
      if (existente) {
        hoja.getRange(existente._fila, 1, 1, ENCABEZADOS.length).setValues([fila]);
      } else {
        hoja.appendRow(fila);
      }
    } else if (body.action === 'delete') {
      const actuales = leerTodasLasZonas_();
      const existente = actuales.find(x => x.zona === body.zona);
      if (existente) hoja.deleteRow(existente._fila);
    } else if (body.action === 'bulkReplace') {
      hoja.clear();
      hoja.getRange(1, 1, 1, ENCABEZADOS.length).setValues([ENCABEZADOS]);
      hoja.getRange(1, 1, 1, ENCABEZADOS.length).setFontWeight('bold');
      const lista = (body.zonas || []).map(z => [z.zona, z.nombre||'', z.vendedor||'', z.codAxum||'', z.diaVenta||'', z.diaEntrega||'']);
      if (lista.length) hoja.getRange(2, 1, lista.length, ENCABEZADOS.length).setValues(lista);
      hoja.setFrozenRows(1);
    } else {
      throw new Error('Acción desconocida: ' + body.action);
    }

    const zonasFinal = leerTodasLasZonas_().map(z => { const c = {...z}; delete c._fila; return c; });
    return jsonResponse_({ ok: true, zonas: zonasFinal });
  } catch (err) {
    return jsonResponse_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}
