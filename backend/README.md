# Backend — Control de Vendedores (API)

API en Python (FastAPI) + PostgreSQL, pensada para reemplazar de a poco el
Google Sheet compartido por una base de datos real, con login por vendedor.

Por ahora cubre: zonas (con control de acceso por vendedor), clientes por
zona con última visita y venta promedio, y la carga de la Proyección diaria
(con la novedad automática cuando se agrega un cliente fuera de zona). El
resto (importar reportes de visitas/ventas, objetivos, dashboard del
supervisor, familias de producto) se suma en las próximas iteraciones sobre
esta misma base.

## 1. Crear el proyecto en Supabase (base de datos + login)

1. Andá a [supabase.com](https://supabase.com) → **New project**.
2. Elegí un nombre (ej. "control-vendedores"), una contraseña para la base
   (guardala, la vas a necesitar) y la región más cercana (South America
   si está disponible). Plan **Free**.
3. Esperá 1-2 minutos a que termine de crearse.
4. **Project Settings → Database → Connection string → URI**: copiá esa
   URL, es tu `DATABASE_URL` (empieza con `postgresql://postgres:...`).
5. **Project Settings → API**: copiá la **Project URL** (`SUPABASE_URL`) y,
   más abajo, en **JWT Settings**, el **JWT Secret** (`SUPABASE_JWT_SECRET`).
6. **Authentication → Users → Add user**: creá un usuario (email + contraseña)
   para cada vendedor y para el supervisor. Anotá el **UUID** de cada uno
   (columna `UID` de la tabla de usuarios) — lo vamos a necesitar para
   vincular cada login con su fila en la tabla `vendedores`.

## 2. Correrlo localmente (opcional, para probar antes de desplegar)

```bash
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env   # completar con los datos reales de Supabase
./venv/bin/alembic upgrade head      # crea todas las tablas
./venv/bin/uvicorn app.main:app --reload
```

Con eso corriendo, `http://localhost:8000/health` debería devolver `{"ok":true}`.

## 3. Desplegar en Render

1. Andá a [render.com](https://render.com) y creá una cuenta (podés entrar
   directo con tu cuenta de GitHub).
2. **New + → Blueprint**, elegí el repositorio `Control-de-Vendedores`.
   Render va a detectar el archivo `backend/render.yaml` automáticamente.
   (Si preferís no usar Blueprint: **New + → Web Service**, elegís el repo,
   y en "Root Directory" ponés `backend` — el build/start command ya están
   en `render.yaml` si necesitás copiarlos a mano.)
3. Cuando te pida las variables de entorno, completá con los valores reales
   que sacaste de Supabase en el paso 1:
   - `DATABASE_URL`
   - `SUPABASE_URL`
   - `SUPABASE_JWT_SECRET`
   - `CORS_ORIGINS` (por ahora podés dejarlo en `*`; más adelante lo
     restringimos a la URL real del frontend)
4. **Create Web Service** (o el botón de deploy del Blueprint). El primer
   deploy tarda unos minutos: instala dependencias, corre las migraciones
   (`alembic upgrade head`, que crea todas las tablas en Supabase) y levanta
   el servidor.
5. Cuando termine, Render te da una URL fija tipo
   `https://control-de-vendedores-api.onrender.com`. Probá
   `https://.../health` — debería devolver `{"ok":true}`.

**Nota sobre el plan free de Render:** el servicio "se duerme" después de
15 minutos sin uso, y la primera request después de eso tarda ~30-60
segundos en responder mientras arranca de nuevo. Para este volumen de uso
(unos pocos vendedores, no todo el día pegándole a la API) no debería ser un
problema, pero es bueno saberlo de antemano.

## 4. Cargar los datos iniciales

Con la base ya creada mediante las migraciones, faltan dos cosas antes de
que el equipo pueda usarlo:

- Migrar los datos que ya tenés en el Google Sheet (zonas, clientes/padrón)
  a las tablas nuevas.
- Vincular cada vendedor de la tabla `vendedores` con el UUID de su usuario
  de Supabase Auth (paso 1.6), completando la columna `usuario_auth_id`.

Este es el paso lógico siguiente — armamos juntos un script de migración
cuando quieras avanzar.

## Estructura del proyecto

```
backend/
  app/
    main.py          — arranque de la app, rutas
    config.py         — variables de entorno
    database.py        — conexión async a Postgres
    auth.py             — valida el login (JWT de Supabase)
    models/              — tablas (SQLAlchemy)
    schemas/               — formas de entrada/salida de la API (Pydantic)
    routers/                — endpoints (zonas, clientes, proyección)
  alembic/                    — migraciones de base de datos
  render.yaml                  — configuración de despliegue en Render
```
