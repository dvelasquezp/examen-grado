# Render — último intento (checklist exacto)

Neon **no suele ser el problema** si ya importaste el seed. El fallo típico es Render con servicios viejos mezclados (Node/Python/Docker).

---

## Antes de empezar — Neon (solo verificar)

1. https://console.neon.tech → SQL Editor:

```sql
SELECT COUNT(*) FROM public.concepts;
```

Debe dar **~1500+**. Si sí, Neon está bien. **No cambies nada.**

---

## Paso 1 — Subir código

```bash
cd "/Users/user/Documents/Proyectos/Exámen de Grado"
git push origin main
```

---

## Paso 2 — Borrar TODO en Render (obligatorio)

En https://dashboard.render.com:

1. **examen-api** → Settings → **Delete Web Service**
2. **examen-web** → Settings → **Delete Web Service**
3. Si hay un **Blueprint** / **Project** viejo, bórralo también

Espera 1 minuto. Si no borras, Render reutiliza config rota.

---

## Paso 3 — Blueprint nuevo

1. **New** → **Blueprint**
2. Repo: **`dvelasquezp/examen-grado`**
3. Branch: **`main`**
4. Blueprint name: el que quieras (no afecta)
5. Render pide **2 variables** — pega exactamente (tu password `npg_...`, **sin** `channel_binding`):

**`DATABASE_URL`**
```
postgresql+asyncpg://neondb_owner:TU_PASSWORD@ep-wild-haze-acsu5bsw-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require
```

**`DATABASE_URL_SYNC`**
```
postgresql://neondb_owner:TU_PASSWORD@ep-wild-haze-acsu5bsw.sa-east-1.aws.neon.tech/neondb?sslmode=require
```

6. **Apply** → espera **15–20 min**

---

## Paso 4 — Copiar las URLs REALES

**No asumas** `examen-api.onrender.com`. Ese nombre puede estar ocupado por otra cuenta de Render, y entonces tus servicios reciben un sufijo (ej. `examen-api-a1b2.onrender.com`).

1. Render → **examen-api** → copia la URL que aparece arriba
2. Render → **examen-web** → copia su URL

Usa **esas** URLs en las pruebas siguientes.

---

## Paso 5 — Probar en este orden

### A) API viva (sin base de datos)

```
https://TU-URL-API.onrender.com/healthz
```

Debe mostrar: `{"status":"ok"}`

Si ves **"Cannot GET"** → estás mirando el servicio de otra persona, o el tuyo no arrancó. Revisa la URL real en el dashboard.

### B) API + Neon

```
https://TU-URL-API.onrender.com/health
```

Debe mostrar JSON con `"postgres": "ok"`.

Si `"postgres": "error"` → revisa las 2 variables en examen-api → Environment.

### C) Web

```
https://TU-URL-WEB.onrender.com
```

Primera carga puede tardar **~1 min** (plan free).

La web habla con la API por un proxy interno (`API_PROXY_TARGET`), así que no hay que configurar URLs a mano.

---

## Paso 6 — Enviar al experto

- URL: la de **examen-web** (la real del dashboard)
- Adjunto: `dist/checklist-revision-experto.xlsx`

---

## Si falla otra vez

Render → **examen-api** → **Logs** → copia las últimas 20 líneas.

| Log | Causa |
|-----|--------|
| `Cannot GET` en /healthz | Servicio viejo; borrar y recrear |
| `postgres: error` | Variables Neon mal pegadas |
| Build failed (web) | Copia log de examen-web |
| Deploy timed out | Plan free; reintenta Manual Deploy |

---

## Plan B (si Render falla de nuevo)

```bash
./scripts/demo-ngrok.sh
```

Ver `docs/DEMO-NGROK.md`.
