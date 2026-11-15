# ProduktWerk

Von der Nische zum verkaufsfertigen PDF in fünf Schritten:

1. **Unique Value Zone** – 10 Mikro-Nischen aus deinen Interessen oder eine konkrete Idee schärfen
2. **Transformation Map** – Produktkonzepte mit Preisempfehlung, Vorher/Nachher und Meilensteine
3. **Wissen** – eigene Notizen, Transkripte und Links als Grundlage
4. **Struktur** – Titel, Preis, Kapitel, Unterkapitel und Boni, frei editierbar
5. **Produkt & PDF** – Kapitel für Kapitel schreiben lassen, in der Vorschau prüfen, als PDF herunterladen

Technik: FastAPI, SQLite, React, Tailwind, WeasyPrint, Anthropic API.

## Einrichten

```bash
cp .env.example .env
```

Trage in `.env` deinen `ANTHROPIC_API_KEY` ein.

## Lokal starten mit Docker

```bash
docker compose up --build
```

Danach: http://localhost:8000

## Lokal starten ohne Docker

Voraussetzungen: Python 3.11+, Node 20+, Pango (macOS: `brew install pango`, Debian/Ubuntu: `apt install libpango-1.0-0 libpangoft2-1.0-0`). Die Schriften Inter und JetBrains Mono sollten installiert sein, sonst nutzt das PDF Ersatzschriften.

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -r requirements.txt
```

```bash
cd frontend && npm install && npm run build && cd ..
```

```bash
.venv/bin/uvicorn backend.main:app --port 8000
```

Danach: http://localhost:8000

Ohne API-Key ausprobieren: `MOCK_AI=1` in `.env` setzen. Dann liefert die App Beispieltexte.

## Auf Render deployen

1. Bei [Render](https://dashboard.render.com) **New → Blueprint** wählen und dieses Repository verbinden. Render liest `render.yaml`.
2. Zwei Werte eingeben, wenn Render danach fragt: `ANTHROPIC_API_KEY` und `APP_PASSWORD` (frei wählbar; damit meldest du dich an).
3. **Apply** klicken. Nach dem Build ist die App unter der angezeigten `onrender.com`-Adresse erreichbar.

Hinweise:

- `APP_PASSWORD` ist auf Render Pflicht. Ohne Passwort startet die App dort nicht, weil sonst jeder mit der Adresse dein API-Guthaben verbrauchen könnte.
- Die Projekte liegen auf einer persistenten Disk (`/data`). Die braucht einen bezahlten Tarif; `render.yaml` nutzt `starter`. Aktuelle Preise stehen bei Render.
- Der Dienst läuft mit genau einer Instanz. Bitte nicht hochskalieren: Schreibjobs laufen im Prozess.

## Einstellungen

| Variable | Bedeutung | Standard |
|---|---|---|
| `ANTHROPIC_API_KEY` | API-Key | – |
| `ANTHROPIC_MODEL` | Modell für alle Schritte | `claude-opus-5-5` |
| `APP_PASSWORD` | Passwort für die Oberfläche | leer (lokal ohne Anmeldung) |
| `DATA_DIR` | Ordner der SQLite-Datenbank | `./data` |
| `MOCK_AI` | `1` = Beispieltexte ohne API | `0` |

## Tests

```bash
.venv/bin/pip install pytest pypdf && .venv/bin/python -m pytest tests -q
```

## Gut zu wissen

- Preise, Zahlungsbereitschaft und Marktaussagen sind Einschätzungen des Modells, keine Marktdaten.
- Lies das fertige Produkt gegen, bevor du es verkaufst. Jeder Teil lässt sich einzeln neu schreiben oder von Hand bearbeiten.
- Bei einem Neustart des Servers bricht ein laufender Schreibjob ab. Fertige Kapitel bleiben erhalten; mit „Fehlende Teile schreiben" geht es weiter.
