@echo off
rem Windows: Doppelklick startet ProduktWerk. Docker Desktop muss laufen.
cd /d "%~dp0"
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker laeuft nicht. Bitte Docker Desktop starten und diese Datei erneut oeffnen.
  pause
  exit /b 1
)
docker compose up --build -d
if errorlevel 1 (
  echo Start fehlgeschlagen.
  pause
  exit /b 1
)
echo ProduktWerk laeuft: http://localhost:8000
timeout /t 3 >nul
start http://localhost:8000
