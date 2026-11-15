#!/bin/bash
# Mac: Doppelklick startet ProduktWerk. Docker Desktop muss laufen.
cd "$(dirname "$0")" || exit 1
if ! docker info >/dev/null 2>&1; then
  echo "Docker laeuft nicht. Bitte Docker Desktop starten und diese Datei erneut oeffnen."
  read -r -p "Enter zum Schliessen"
  exit 1
fi
docker compose up --build -d || { read -r -p "Start fehlgeschlagen. Enter zum Schliessen"; exit 1; }
echo "ProduktWerk laeuft: http://localhost:8000"
sleep 3
open http://localhost:8000 2>/dev/null || xdg-open http://localhost:8000 2>/dev/null
