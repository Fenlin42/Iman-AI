"""Canned content for MOCK_AI=1 (tests and trying the UI without an API key)."""
import asyncio
import re


def structured(kind: str) -> dict:
    if kind in ("niches", "specific"):
        n = 10 if kind == "niches" else 1
        return {"niches": [{
            "name": f"Beispiel-Nische {i}",
            "problem": f"Beispielproblem {i}: Die Zielgruppe verliert jede Woche Stunden mit einer wiederkehrenden Aufgabe.",
            "audience": f"Selbststaendige in Situation {i}, die allein arbeiten.",
            "willingness_to_pay": "Geschaetzt 29-79 EUR, weil das Problem direkt Umsatz kostet.",
            "why_profitable": "Bestehende Angebote sind breit und nicht auf diese Gruppe zugeschnitten.",
            "demand_signal": "Schaetzung: Es gibt bezahlte Kurse und aktive Foren zu diesem Thema.",
        } for i in range(1, n + 1)]}
    if kind == "concepts":
        names = ["7-Tage-Sprint", "21-Tage-Aktionsplan", "30-Tage-Blueprint", "Toolkit", "Feldhandbuch"]
        return {"concepts": [{
            "name": f"{n} Beispiel",
            "format": f"{n} mit taeglichen Aufgaben",
            "promise": "Am Ende steht ein funktionierendes System.",
            "duration": "21 Tage",
            "price": f"{27 + 10 * i} EUR",
            "price_reasoning": "Passt zur Zahlungsbereitschaft der Zielgruppe (Schaetzung).",
        } for i, n in enumerate(names)]}
    if kind == "transformation":
        state = lambda h: {"headline": h, "situation": "Beispielsituation in zwei Saetzen. Noch ein Satz.",
                           "feelings": ["Gefuehl A", "Gefuehl B", "Gefuehl C"], "daily_reality": "Eine Szene aus dem Alltag."}
        return {"before": state("Vorher: Chaos"), "after": state("Nachher: System"),
                "milestones": [{"title": f"Meilenstein {i}", "timeframe": f"Tag {i * 3 - 2}-{i * 3}",
                                "description": "Was die Person tut.", "outcome": "Was danach sichtbar ist."}
                               for i in range(1, 7)]}
    if kind == "charter":
        return {
            "title": "Das Beispiel-System", "subtitle": "In 21 Tagen vom Chaos zum funktionierenden Ablauf",
            "target_price": "47 EUR", "reading_time": "ca. 3 Stunden",
            "chapters": [{"title": f"Kapitel {i}: Beispielthema", "summary": "Danach kann der Leser Schritt X.",
                          "sections": ["Ausgangslage", "Schritt fuer Schritt", "Typische Fehler"]} for i in range(1, 5)],
            "bonuses": [{"title": f"Bonus {i}: Checkliste", "description": "Eine fertige Checkliste."} for i in range(1, 3)],
        }
    raise ValueError(kind)


_SAMPLE = """Dieser Beispieltext steht fuer den Inhalt von **{title}**. Im echten Betrieb schreibt hier das Modell.

## Ausgangslage

Ein Absatz mit genug Text, damit der Satzspiegel im PDF sichtbar wird. Noch ein Satz, und ein dritter, damit der Absatz ueber mehrere Zeilen laeuft und Blocksatz sowie Silbentrennung geprueft werden koennen.

> [!KEY] Das Wichtigste
> Eine Kernaussage in einer hervorgehobenen Box.

## Schritt fuer Schritt

1. Erster Schritt mit einer genauen Anweisung.
2. Zweiter Schritt mit einer Entscheidung.
3. Dritter Schritt mit einem Ergebnis.

| Option | Aufwand | Wirkung |
|---|---|---|
| A | gering | mittel |
| B | hoch | hoch |

> [!EXAMPLE] Beispiel
> Ein ausgefuelltes Beispiel, als Beispiel gekennzeichnet.

### Unterschritt

Ein kurzer Absatz zu einem Detail.

> [!TIP] Tipp
> Ein praktischer Hinweis.

> [!WARNING] Achtung
> Ein typischer Fehler an dieser Stelle.

## Typische Fehler

- Fehler eins und wie man ihn vermeidet.
- Fehler zwei und wie man ihn erkennt.

## Checkliste

- [ ] Erster Punkt erledigt
- [ ] Zweiter Punkt erledigt
- [ ] Dritter Punkt erledigt
"""


async def write(user: str):
    m = re.findall(r'(?:chapter \d+: |bonus )"([^"]+)"', user)
    text = _SAMPLE.format(title=m[-1] if m else "diesem Teil")
    for i in range(0, len(text), 120):
        await asyncio.sleep(0.01)
        yield text[i:i + 120]
