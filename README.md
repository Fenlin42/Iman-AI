# ProduktWerk

Von der Nische zum verkaufsfertigen PDF in fünf Schritten:

1. **Unique Value Zone** – 10 Mikro-Nischen aus deinen Interessen oder eine konkrete Idee schärfen
2. **Transformation Map** – Produktkonzepte mit Preisempfehlung, Vorher/Nachher und Meilensteine
3. **Wissen** – eigene Notizen, Transkripte und Links als Grundlage
4. **Struktur** – Titel, Preis, Kapitel, Unterkapitel und Boni, frei editierbar
5. **Produkt & PDF** – Kapitel für Kapitel schreiben lassen, in der Vorschau prüfen, als PDF herunterladen

Technik: FastAPI, SQLite, React, Tailwind, WeasyPrint, Anthropic API.

## Zwei Arten, die Texte zu erzeugen

- **Automatisch (API):** Die App ruft die Anthropic API auf. Braucht `ANTHROPIC_API_KEY`, kostet pro Produkt API-Guthaben.
- **Kopier-Modus:** Pro Schritt kopierst du einen fertigen Prompt in deinen eigenen Claude-Chat (z. B. mit einem Claude-Abo auf claude.ai) und fügst die Antwort in die App ein. Kostet kein API-Guthaben und braucht keinen Key. Bei zehn Kapiteln und drei Boni sind das etwa 17 Kopiervorgänge.

Umschalten kannst du oben rechts. Ohne API-Key ist automatisch der Kopier-Modus aktiv.

## Lokal starten mit Docker (empfohlen)

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) installieren und starten.
2. Diesen Ordner öffnen und starten:
   - **Windows:** Doppelklick auf `start.bat`
   - **Mac:** Doppelklick auf `start.command`
   - **oder im Terminal:**

```bash
docker compose up --build -d
```

3. Im Browser http://localhost:8000 öffnen. Der erste Start dauert ein paar Minuten.

Die Projekte liegen im Ordner `data/` und bleiben erhalten. Beenden:

```bash
docker compose down
```

Ohne weitere Einrichtung läuft die App im Kopier-Modus. Für den automatischen Modus `.env.example` nach `.env` kopieren, dort `ANTHROPIC_API_KEY` eintragen und neu starten.

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
2. Wenn Render nach Werten fragt: `APP_PASSWORD` eintragen (frei wählbar; damit meldest du dich an). `ANTHROPIC_API_KEY` nur, wenn du den automatischen Modus nutzen willst; sonst leer lassen.
3. **Apply** klicken. Nach dem Build ist die App unter der angezeigten `onrender.com`-Adresse erreichbar.

Hinweise:

- `APP_PASSWORD` ist auf Render Pflicht. Ohne Passwort startet die App dort nicht, weil sonst jeder mit der Adresse sie benutzen könnte.
- `render.yaml` nutzt den kostenlosen Tarif. Der hat keine dauerhafte Festplatte: Nach jedem Neustart (auch nach dem Einschlafen bei Inaktivität) hat der Server die Projekte vergessen.
- Deshalb sichert die App jedes Projekt automatisch in deinem Browser und stellt es beim nächsten Öffnen wieder her. Das gilt nur für denselben Browser auf demselben Gerät. Für alles andere gibt es im Projekt „Sicherung herunterladen" und in der Übersicht „Sicherung importieren".
- Nach längerer Pause braucht der erste Aufruf im kostenlosen Tarif etwa eine Minute.
- Für dauerhafte Speicherung auf dem Server: bezahlten Tarif wählen und eine Disk unter `/data` einhängen.
- Der Dienst läuft mit genau einer Instanz. Bitte nicht hochskalieren: Schreibjobs laufen im Prozess.

## Einstellungen

| Variable | Bedeutung | Standard |
|---|---|---|
| `ANTHROPIC_API_KEY` | API-Key, nur für den automatischen Modus | leer (Kopier-Modus) |
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
