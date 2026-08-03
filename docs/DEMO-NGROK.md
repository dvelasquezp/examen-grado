# Demo online — alternativa a Render (funciona en 15 min)

Render en plan free está dando problemas. **Esta opción sí funciona** y el experto no instala nada.

---

## Opción recomendada: ngrok + Docker (tu Mac)

El experto abre un link `https://xxxx.ngrok-free.app` en el navegador.

### Requisitos (solo tú)

- Docker Desktop (ya lo tienes)
- Cuenta gratis en [ngrok.com](https://ngrok.com)

### Pasos

**1. Instalar ngrok (una vez)**

```bash
brew install ngrok
```

Regístrate en https://dashboard.ngrok.com → copia tu **Authtoken** →

```bash
ngrok config add-authtoken TU_TOKEN_AQUI
```

**2. Arrancar demo pública**

```bash
cd "/Users/user/Documents/Proyectos/Exámen de Grado"
chmod +x scripts/demo-ngrok.sh
./scripts/demo-ngrok.sh
```

**3. Copiar el link**

Ngrok mostrará algo como:

```
Forwarding   https://abc123.ngrok-free.app -> http://localhost:3000
```

Esa URL **`https://abc123.ngrok-free.app`** se la envías al experto.

**4. Enviar al experto**

> Hola,  
> Puedes revisar la app aquí (solo navegador, sin instalar nada):  
> **https://abc123.ngrok-free.app**  
>  
> Completa la planilla adjunta **checklist-revision-experto.xlsx**.  
>  
> Nota: la primera carga puede tardar unos segundos.  
> Gracias.

Adjunto: `dist/checklist-revision-experto.xlsx`

### Importante

| Tema | Detalle |
|------|---------|
| Mac encendida | Mientras el experto revisa, tu Mac debe estar prendida con el script corriendo |
| Link temporal | En plan free de ngrok el link cambia si reinicias el script |
| Detener | Ctrl+C en la terminal de ngrok; `docker compose -f docker-compose.review.yml down` para apagar todo |

---

## Opción local sin link (solo prueba tuya)

```bash
./scripts/review_up.sh
```

Abre http://localhost:3000 — no sirve para el experto remoto.

---

## ¿Por qué falló Render?

- Plan free se duerme y a veces no levanta bien
- Builds de Next.js + Docker mezclados fallan por memoria y dependencias
- Configuración frágil entre API y Web

Ngrok evita todo eso: la app corre **igual que en tu Mac**, solo se expone un túnel HTTPS.

---

## Cuando termine la revisión

```bash
docker compose -f docker-compose.review.yml down
```

Puedes borrar los servicios en Render si los creaste (ya no hacen falta).
