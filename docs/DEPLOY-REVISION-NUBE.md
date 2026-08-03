# Despliegue en la nube — revisión sin instalar nada

El experto solo abre un **link** en el navegador. La app corre en **Render** con la base de datos en **Neon**.

## URLs actuales

| Servicio | URL |
|----------|-----|
| Web (la del experto) | https://examen-web-ip7x.onrender.com |
| API | https://examen-api-03dx.onrender.com |
| API docs | https://examen-api-03dx.onrender.com/docs |

Render añade un sufijo aleatorio al nombre. Si algún día borras y recreas los servicios, las URLs cambian y hay que actualizar `render.yaml`.

---

## Arquitectura

```
Navegador → examen-web (Next.js) → examen-api (FastAPI) → Neon (PostgreSQL + pgvector)
```

El navegador nunca llama a la API directamente: pide `/api/v1/...` a la web y esta lo reenvía. Ese reenvío vive en `apps/web/src/app/api/v1/[...path]/route.ts` y lee `API_PROXY_TARGET` en cada petición.

**Importante:** no usar `rewrites` de `next.config.js` para esto. Next.js los resuelve durante el build, así que la URL de destino queda congelada en la imagen y ninguna variable de entorno posterior la cambia.

---

## Variables de entorno

### examen-api

| Variable | Valor |
|----------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://neondb_owner:PASS@ep-...-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require` |
| `DATABASE_URL_SYNC` | `postgresql://neondb_owner:PASS@ep-....sa-east-1.aws.neon.tech/neondb?sslmode=require` |
| `CORS_ORIGINS` | `https://examen-web-ip7x.onrender.com` |

`sslmode` y `channel_binding` se eliminan automáticamente de la URL asíncrona (`apps/api/src/config/settings.py`), porque `asyncpg` no los acepta como parámetros de conexión; el SSL se activa por `connect_args`.

### examen-web

| Variable | Valor |
|----------|-------|
| `API_PROXY_TARGET` | `https://examen-api-03dx.onrender.com` |

---

## Verificar que todo está bien

```bash
# API viva (no depende de la base de datos)
curl https://examen-api-03dx.onrender.com/healthz

# API + Neon
curl https://examen-web-ip7x.onrender.com/health

# Datos reales a través del proxy
curl https://examen-web-ip7x.onrender.com/api/v1/catalog/subjects
```

El último debe devolver **Derecho Civil**.

`"neo4j": "error"` en `/health` es esperado: Neo4j no está desplegado en la nube. Solo limita el mapa de conceptos.

---

## Limitaciones del plan free

- La app **se duerme** tras ~15 min sin uso; la primera carga tarda ~30–60 s
- **Simulacro oral con audio:** la transcripción (Whisper) no está incluida en este despliegue; el flujo oral por texto sí funciona
- **Mapa de conceptos:** limitado sin Neo4j

---

## Actualizar tras cambios

```bash
git push origin main   # Render redespliega automáticamente
```

Si cambias variables en `render.yaml`, haz **Manual Sync** en el Blueprint. Un "Manual Deploy" del servicio no las aplica.

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
> **https://examen-web-ip7x.onrender.com**
>
> Completa la planilla adjunta **checklist-revision-experto.xlsx**.
>
> Nota: si la app estuvo inactiva, la primera carga puede tardar ~1 minuto.
>
> Gracias.

Adjunta: `dist/checklist-revision-experto.xlsx`

---

## Seguridad

- El link es público para quien lo tenga: compártelo solo por correo directo
- Al terminar la revisión, resetea la contraseña de la base en Neon → **Settings** → **Reset password**
- Puedes borrar los servicios en Render cuando ya no los necesites

---

## Alternativa sin Render

Si alguna vez necesitas una demo rápida desde tu Mac: `docs/DEMO-NGROK.md`.
