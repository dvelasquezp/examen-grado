@echo off
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
  echo ERROR: Instala Docker Desktop desde https://www.docker.com/products/docker-desktop/
  pause
  exit /b 1
)

echo Construyendo e iniciando (primera vez puede tardar 10-15 min)...
docker compose -f docker-compose.review.yml up --build -d

echo.
echo ============================================
echo   App de revision: http://localhost:3000
echo   API (docs):      http://localhost:8000/docs
echo ============================================
echo.
echo Para detener: docker compose -f docker-compose.review.yml down
pause
