@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Instale Python 3.12 ou superior e marque Add Python to PATH.
  pause
  exit /b 1
)
set ADMIN_NAME=admin
set ADMIN_PASSWORD=ImperialLocal2026
set COOKIE_SECURE=0
set PORT=8000
set DATABASE_PATH=data/local.db
echo Chancelaria Imperial - modo local
echo Abra http://localhost:8000
echo Usuario: admin
echo Senha inicial: ImperialLocal2026
echo Mantenha esta janela aberta. Ctrl+C para encerrar.
start "" "http://localhost:8000"
python server.py
pause
