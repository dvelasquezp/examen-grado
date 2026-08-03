# Despliegue en la nube — revisión sin instalar nada

El experto solo abre un **link** en el navegador. La web corre en **Vercel**, la API en **Render** y la base de datos en **Neon**.

## URLs actuales

| Servicio | Dónde | URL |
|----------|-------|-----|
| Web (la del experto) | Vercel | https://examen-grado-five.vercel.app |
| API | Render | https://examen-api-03dx.onrender.com |
| API docs | Render | https://examen-api-03dx.onrender.com/docs |

Render añade un sufijo aleatorio al nombre. Si algún día borras y recreas el servicio, la URL cambia y hay que actualizar `API_PROXY_TARGET` en Vercel.

### Por qué la web no está en Render

Render reparte **750 horas de instancia al mes entre todos los servicios gratuitos** de la cuenta, y suspende todo si se agotan. Con la web y la API allí, mantener ambas despiertas costaría ~1.460 horas: imposible. Vercel no cobra horas por el frontend, así que la cuota entera queda para la API y alcanza para tenerla despierta casi todo el día.

---

## Arquitectura

```
Navegador → Vercel (Next.js) → examen-api (FastAPI) → Neon (PostgreSQL + pgvector)
```

El navegador nunca llama a la API directamente: pide `/api/v1/...` a la web y esta lo reenvía. Ese reenvío vive en `apps/web/src/app/api/v1/[...path]/route.ts` y lee `API_PROXY_TARGET` en cada petición. Como las llamadas a la API salen del servidor y no del navegador, no hay CORS de por medio.

**Importante:** no usar `rewrites` de `next.config.js` para esto. Next.js los resuelve durante el build, así que la URL de destino queda congelada en la imagen y ninguna variable de entorno posterior la cambia.

El proxy reintenta mientras la API despierta, pero se rinde a los 45 s: Vercel corta las funciones al minuto, y conviene devolver un mensaje propio antes de que lo haga la plataforma.

---

## Variables de entorno

### examen-api

| Variable | Valor |
|----------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://neondb_owner:PASS@ep-...-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require` |
| `DATABASE_URL_SYNC` | `postgresql://neondb_owner:PASS@ep-....sa-east-1.aws.neon.tech/neondb?sslmode=require` |
| `CORS_ORIGINS` | `https://examen-grado-five.vercel.app` |

`sslmode` y `channel_binding` se eliminan automáticamente de la URL asíncrona (`apps/api/src/config/settings.py`), porque `asyncpg` no los acepta como parámetros de conexión; el SSL se activa por `connect_args`.

### Web (Vercel)

Proyecto importado desde GitHub con **Root Directory `apps/web`**; desde la raíz del repositorio Vercel no encuentra el `package.json` y el build falla.

| Variable | Valor |
|----------|-------|
| `API_PROXY_TARGET` | `https://examen-api-03dx.onrender.com` |

---

## Verificar que todo está bien

```bash
# API viva (no depende de la base de datos)
curl https://examen-api-03dx.onrender.com/healthz

# API + Neon
curl https://examen-grado-five.vercel.app/health

# Datos reales a través del proxy
curl https://examen-grado-five.vercel.app/api/v1/catalog/subjects
```

El último debe devolver **Derecho Civil**.

`"neo4j": "error"` en `/health` es esperado: Neo4j no está desplegado en la nube. Solo limita el mapa de conceptos.

---

## Limitaciones del plan free

- La web **no se duerme**: Vercel la sirve por CDN y carga siempre al instante
- La **API sí se duerme** tras 15 min sin tráfico y tarda cerca de un minuto en volver. Mientras despierta, la interfaz avisa y reintenta sola
- **Simulacro oral con audio:** la transcripción (Whisper) no está incluida en este despliegue; el flujo oral por texto sí funciona
- **Mapa de conceptos:** limitado sin Neo4j

### Mantener la API despierta

Un ping periódico a `/healthz` evita que se duerma. El límite real no es el sueño sino las **750 horas de instancia al mes**: pasarse suspende el servicio hasta el mes siguiente, así que no conviene cubrir las 24 horas (744 h en un mes de 31 días deja sólo 6 de margen).

Configuración usada, con un servicio gratuito tipo [cron-job.org](https://cron-job.org) o UptimeRobot:

| Ajuste | Valor |
|--------|-------|
| URL | `https://examen-api-03dx.onrender.com/healthz` |
| Intervalo | cada 10 min (Render duerme a los 15) |
| Franja | 06:00–03:59, hora de Chile |

Son ~682 horas al mes, con holgura. La API sólo duerme entre las 04:00 y las 06:00; si alguien entra en esa franja, espera el minuto de arranque una sola vez.

`/healthz` no toca la base de datos, así que el ping no despierta el cómputo de Neon sin necesidad.

---

## Actualizar tras cambios

```bash
git push origin main   # Vercel y Render redespliegan automáticamente
```

Si cambias variables en `render.yaml`, haz **Manual Sync** en el Blueprint. Un "Manual Deploy" del servicio no las aplica. Las variables de Vercel se editan en **Settings → Environment Variables** y exigen un redespliegue para tomar efecto.

Para actualizar solo los datos:

```bash
./scripts/export_review_seed.sh
NEON_DATABASE_URL='postgresql://...' ./scripts/import_seed_neon.sh
```

---

## Enviar al experto

**Asunto:** Revisión app Examen de Grado — solo navegador

> Hola,
>
> Puedes revisar la app aquí (no requiere instalar nada):
> **https://examen-grado-five.vercel.app**
>
> Completa la planilla adjunta **checklist-revision-experto.xlsx**.
>
> Gracias.

Adjunta: `dist/checklist-revision-experto.xlsx`

---

## Seguridad

- El link es público para quien lo tenga: compártelo solo por correo directo
- Al terminar la revisión, resetea la contraseña de la base en Neon → **Settings** → **Reset password**
- Puedes borrar el servicio en Render y el proyecto en Vercel cuando ya no los necesites; acuérdate de desactivar también el ping
- El plan Hobby de Vercel es gratis pero exige **uso personal, no comercial**

---

## Alternativa sin Render

Si alguna vez necesitas una demo rápida desde tu Mac: `docs/DEMO-NGROK.md`.
