# Entrega para revisión experto

## Resumen

| Opción | Requisito en PC del revisor | Esfuerzo tuyo |
|--------|----------------------------|---------------|
| **Paquete ZIP + Docker** (recomendado) | Solo [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Empaquetar una vez |
| **Demo en la nube** | Navegador | Desplegar (Render, Fly, etc.) |
| **Cero instalación real** | No existe para esta stack completa | Solo vía URL pública |

La app usa PostgreSQL, API Python y frontend Next.js. **Docker** es la forma estándar de empaquetarlo sin pedirle al experto que instale Node, Python ni bases de datos.

---

## Pasos para armar el paquete (tú)

### 1. Deja la base lista en tu máquina

Con la app corriendo y los datos cargados (discover → ingest → extract → link-notes):

```bash
docker compose up -d postgres
# ... asegúrate de tener conceptos en la BD local
./scripts/export_review_seed.sh
```

Eso crea `data/review-seed.sql` con conceptos, apuntes y progreso precargados.

### 2. Genera el ZIP de revisión

```bash
chmod +x scripts/package_review_bundle.sh scripts/export_review_seed.sh scripts/review_up.sh
./scripts/package_review_bundle.sh
```

Salida: **`dist/examen-grado-revision.zip`**

Incluye:
- App (API + web) vía Docker
- Materiales `Derecho Civil` + Cedulario (si existen en la raíz)
- Base precargada (`data/review-seed.sql`)
- `checklist-revision-experto.xlsx`
- `Iniciar-Revision.bat` / `iniciar-revision.sh`
- `LEEME.txt`

### 3. Envía al experto

- **Adjunto 1:** `examen-grado-revision.zip` (WeTransfer, Drive, etc.)
- **Adjunto 2 (opcional):** solo el Excel, por comodidad
- **Mensaje:** instalar Docker Desktop, descomprimir, ejecutar `Iniciar-Revision.bat`, abrir http://localhost:3000

---

## Pasos para el experto

1. Instalar **Docker Desktop** y abrirlo (debe quedar en verde).
2. Descomprimir el ZIP.
3. **Windows:** doble clic en `Iniciar-Revision.bat`  
   **Mac/Linux:** `./iniciar-revision.sh`
4. Esperar 5–15 min la primera vez (descarga imágenes + build).
5. Navegador → **http://localhost:3000**
6. Completar **`checklist-revision-experto.xlsx`**

Detener: `docker compose -f docker-compose.review.yml down`

---

## Checklist Excel

Generar solo el Excel:

```bash
cd apps/api && source .venv/bin/activate
pip install openpyxl
python ../../scripts/generate_checklist_excel.py ../../dist/checklist-revision-experto.xlsx
```

Hojas: Instrucciones, Checklist, Conceptos, Emparejar, Hallazgos, Cobertura, Veredicto.

---

## Alternativa: demo online (sin Docker para el experto)

Si Docker le resulta pesado:

1. Despliega `web` + `api` + Postgres en un servicio (Railway, Render, Fly.io).
2. Carga la BD con el mismo `review-seed.sql`.
3. Envía solo la **URL** + Excel.

Ventaja: cero instalación. Desventaja: requiere hosting y configurar variables de entorno.

---

## Tamaño aproximado del ZIP

- Sin modelos de IA pesados: ~50–200 MB (PDFs de Derecho Civil dominan).
- Primera ejecución en Docker del revisor: descarga adicional de imágenes (~1–2 GB).

El paquete de revisión **no incluye** Whisper ni LLM local; el simulacro oral por **texto** funciona; **audio** puede no estar disponible en el paquete ligero (STT requiere modelos extra).
