# Despliegue en la nube — revisión sin instalar nada

El experto solo abre un **link** en el navegador. Tú despliegas una vez en **Render** (app) + **Neon** (base de datos).

Tiempo estimado: **45–60 min** la primera vez.

---

## Resumen

| Componente | Servicio | Costo |
|------------|----------|-------|
| Base de datos (PostgreSQL + pgvector) | [Neon](https://neon.tech) | Gratis |
| API + Web | [Render](https://render.com) | Gratis* |

\* Plan free: la app **se duerme** tras ~15 min sin uso; el primer acceso tarda ~30–60 s en despertar.

---

## Paso 1 — Base de datos en Neon

1. Crea cuenta en https://neon.tech  
2. **New Project** → región cercana (ej. US East / São Paulo)  
3. En el SQL Editor ejecuta:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

4. Copia la **connection string** (PostgreSQL, con `?sslmode=require`).

5. En tu Mac, importa tu base actual:

```bash
cd "/Users/user/Documents/Proyectos/Exámen de Grado"
# Si aún no exportaste:
./scripts/export_review_seed.sh

export NEON_DATABASE_URL='postgresql://USUARIO:PASS@HOST/neondb?sslmode=require'
chmod +x scripts/import_seed_neon.sh
./scripts/import_seed_neon.sh
```

Deberías ver cientos/miles de conceptos al final.

6. Guarda dos URLs para Render:

```bash
# Async (FastAPI)
postgresql+asyncpg://USUARIO:PASS@HOST/neondb?sslmode=require

# Sync (Alembic / psql)
postgresql://USUARIO:PASS@HOST/neondb?sslmode=require
```

(Solo cambia el prefijo `postgresql+asyncpg://` vs `postgresql://`.)

---

## Paso 2 — Crear repositorio en GitHub (nuevo, no reutilizar otro)

Este proyecto **aún no está en Git**. Crea un repo **nuevo** en GitHub (no uses el repo de otro proyecto).

### 2a. En GitHub (navegador)

1. https://github.com/new  
2. **Repository name:** `examen-grado` (o el nombre que prefieras)  
3. **Private** (recomendado — incluye materiales de estudio)  
4. **No** marques “Add a README” ni “Add .gitignore” (ya existen en el proyecto)  
5. Clic en **Create repository**  
6. Copia la URL que aparece, algo como:  
   `https://github.com/TU_USUARIO/examen-grado.git`

### 2b. En tu Mac (Terminal)

```bash
cd "/Users/user/Documents/Proyectos/Exámen de Grado"

git init
git branch -M main
git add .
git status   # revisa que NO aparezcan .env, node_modules, .venv, data/
git commit -m "Initial commit — plataforma examen de grado"

git remote add origin https://github.com/TU_USUARIO/examen-grado.git
git push -u origin main
```

GitHub pedirá login (usuario + token o SSH).

---

## Paso 3 — Desplegar en Render (Blueprint)

1. https://dashboard.render.com → **New** → **Blueprint**  
2. Conecta el repositorio **Exámen de Grado**  
3. Render detecta `render.yaml` con dos servicios: `examen-api` y `examen-web`  
4. Al crear, te pedirá valores **sync: false**. Configura:

| Variable | Servicio | Valor |
|----------|----------|-------|
| `DATABASE_URL` | examen-api | `postgresql+asyncpg://...` (Neon) |
| `DATABASE_URL_SYNC` | examen-api | `postgresql://...` (Neon) |
| `CORS_ORIGINS` | examen-api | Se configura solo vía `render.yaml` (host de examen-web) |
| `RESTORE_SEED` | examen-api | `false` (ya importaste en Neon) |

5. Espera el build (~10–20 min la primera vez).  
6. URL del experto: **`https://examen-web.onrender.com`** (o el nombre que asigne Render).

---

## Paso 4 — Verificar

1. Abre `https://examen-web.onrender.com`  
2. Debe cargar **Derecho Civil** con conceptos (datos de Neon)  
3. Prueba flashcards y un juego  
4. API docs (opcional): `https://examen-api.onrender.com/docs`

**Limitaciones en la demo nube (plan free):**

- **Simulacro oral con audio:** la transcripción (Whisper) no está incluida en este despliegue; el resto del flujo oral con texto sí funciona.
- **Mapa de conceptos:** puede estar vacío o limitado sin Neo4j (no incluido en la nube).
- **Primera carga:** ~30–60 s si el servicio estuvo dormido.

Si la web carga pero no hay datos → revisa import en Neon y variables `DATABASE_URL`.

---

## Paso 5 — Enviar al experto

**Asunto:** Revisión app Examen de Grado — solo navegador

> Hola,  
>  
> Puedes revisar la app aquí (no requiere instalar nada):  
> **https://examen-web.onrender.com**  
>  
> Completa la planilla adjunta **checklist-revision-experto.xlsx**.  
>  
> Nota: si la app estuvo inactiva, la primera carga puede tardar ~1 minuto.  
>  
> Gracias.

Adjunta: `dist/checklist-revision-experto.xlsx`

---

## Actualizar después de cambios

```bash
git push   # Render redespliega automáticamente
```

Para actualizar solo datos:

```bash
./scripts/export_review_seed.sh
./scripts/import_seed_neon.sh   # sobrescribe tablas según el dump
```

---

## Seguridad (recomendado)

La demo free es **pública** si alguien tiene el URL. Opciones:

- En Render → **examen-web** → Settings → **Password protection** (si disponible en tu plan)  
- O compartir el link solo por correo directo al experto  
- Borrar el servicio en Render cuando termine la revisión  

---

## Alternativa rápida (sin Render)

Si solo necesitas **2–3 días** de revisión:

```bash
# Con la app local corriendo:
ngrok http 3000
```

Envías el link `https://xxxx.ngrok-free.app` — aún más rápido, pero depende de tu Mac encendida.

---

## Archivos relacionados

- `render.yaml` — blueprint Render  
- `apps/api/Dockerfile.cloud` — imagen API con materiales  
- `data/review-seed.sql` — dump de conceptos  
- `scripts/import_seed_neon.sh` — importar a Neon  
