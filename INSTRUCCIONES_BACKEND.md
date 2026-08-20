# Backend compartido para la Base de zonas — Instrucciones

Esto conecta la pestaña "Base de zonas" del HTML a un Google Sheet compartido, usando el mismo patrón que ya usás en tus otras herramientas (Apps Script Web App). Es el primer paso del backend — arranca por Zonas porque fue lo que pediste ahora; visitas y ventas semanales pueden sumarse después con el mismo patrón, cuando quieras.

## 1. Crear la planilla y pegar el código

1. Andá a [sheets.google.com](https://sheets.google.com) y creá una planilla nueva. Nombrala, por ejemplo, "Congelados Puntanos - Backend Zonas".
2. **Extensiones → Apps Script**.
3. Borrá todo el contenido de `Code.gs` y pegá el contenido completo de `Backend_AppsScript_Zonas.gs`.
4. Guardá (Ctrl+S / ícono de disco).

## 2. Poblar la hoja con las 40 zonas actuales

1. Arriba, en el selector de funciones (al lado del botón ▶ Ejecutar), elegí **`setupInicial`**.
2. Hacé clic en ▶ Ejecutar.
3. La primera vez te va a pedir autorización — es tu propia cuenta autorizando tu propio script, es seguro. Aceptá los permisos.
4. Volvé a la planilla: debería haber una hoja llamada "Zonas" con las 40 filas ya cargadas.

## 3. Publicar como aplicación web

1. En el editor de Apps Script: **Implementar → Nueva implementación**.
2. Tipo: **Aplicación web**.
3. Configurá:
   - Ejecutar como: **Yo** (tu cuenta)
   - Quién tiene acceso: **Cualquier usuario**
4. **Implementar**. Te va a pedir autorizar de nuevo — aceptá.
5. Copiá la URL que termina en `/exec`. Esa es la que necesitás.

## 4. Conectar el HTML

1. Abrí `Reporte_Visitas_Eficiencia.html` en el navegador.
2. Pestaña **"Base de zonas"**.
3. Arriba de todo, en el panel azul "⚙ Backend compartido", pegá la URL `/exec` en el campo y tocá **"💾 Guardar"**.
4. Debería aparecer "● Conectado" y la tabla se actualiza con lo que hay en el Sheet.

Repetí el paso 4 en la compu de cada persona que vaya a usar la herramienta, pegando la misma URL — así todos leen y escriben en el mismo Google Sheet.

## Cómo queda funcionando

- **Al abrir el archivo**, si hay una URL de backend guardada en ese navegador, sincroniza automáticamente antes de mostrar la tabla.
- **Al editar cualquier celda** de la Base de zonas, se guarda localmente y además se manda al Sheet en el momento.
- **Al borrar una zona**, se borra también en el Sheet.
- **Al usar "Cargar lista completa de zonas"**, reemplaza todo el Sheet de una vez.
- **Al asignar una zona desde "Zonas sin asignar"**, también se sube al Sheet.
- Si el backend no responde (sin internet, URL mal copiada, etc.), la herramienta **no se rompe**: sigue funcionando con los datos locales y te avisa con el punto en rojo en vez de bloquear la pantalla.

Las visitas diarias y las ventas semanales, por ahora, siguen guardándose solo localmente (localStorage) en cada navegador — no comparten backend todavía. Es la parte lógica para sumar en una segunda vuelta si querés que todo el equipo vea lo mismo, no solo las zonas.

## Si vas a seguir esto en Claude Code

Este mismo Apps Script (`Backend_AppsScript_Zonas.gs`) y el patrón de `fetch` que ya quedó en el HTML (`sincronizarZonasDesdeBackend`, `backendUpsertZona`, `backendDeleteZona`, `backendBulkReplace`) son el punto de partida directo. Los próximos pasos naturales para una versión más robusta:

- Repetir el mismo patrón (hoja + Web App + funciones de sync) para **visitas diarias** y **ventas semanales**, que hoy siguen siendo 100% locales.
- Migrar de "un HTML gigante con todo el JS inline" a una estructura de proyecto más manejable (separar parseo, UI y capa de datos en archivos), algo que Claude Code hace mucho mejor que ir armando todo en un solo archivo.
- Pensar autenticación básica si el Sheet va a tener datos sensibles (hoy "Cualquier usuario" puede leer/escribir si tiene la URL — para uso interno del equipo alcanza, pero es lo primero a robustecer).
- Considerar mover de Apps Script a un backend más tradicional (Node/Cloud Functions) si el volumen de datos o la cantidad de usuarios concurrentes crece mucho — Apps Script tiene límites de cuota diaria que vale la pena tener en el radar.
