"""Turn a project into one HTML document; WeasyPrint prints the same document as PDF."""
import re
from pathlib import Path

import markdown as md
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, select_autoescape

HERE = Path(__file__).parent
_env = Environment(loader=FileSystemLoader(HERE), autoescape=select_autoescape(["html"]))

CALLOUTS = {
    "TIP": ("tip", {"de": "Tipp", "en": "Tip"}),
    "WARNING": ("warning", {"de": "Achtung", "en": "Watch out"}),
    "EXAMPLE": ("example", {"de": "Beispiel", "en": "Example"}),
    "KEY": ("key", {"de": "Das Wichtigste", "en": "Key point"}),
    "NOTE": ("tip", {"de": "Hinweis", "en": "Note"}),
}
LABELS = {
    "de": {"toc": "Inhalt", "chapter": "Kapitel", "bonus": "Bonus", "bonuses": "Bonusmaterial", "by": "von",
           "pending": "Dieser Teil ist noch nicht geschrieben."},
    "en": {"toc": "Contents", "chapter": "Chapter", "bonus": "Bonus", "bonuses": "Bonus material", "by": "by",
           "pending": "This part has not been written yet."},
}
ACCENTS = {"indigo": "#4338ca", "emerald": "#047857", "rose": "#be123c", "amber": "#b45309", "slate": "#334155"}


def _tint(hex_color: str, amount: float = 0.08) -> str:
    """Mix a colour into white (WeasyPrint has no color-mix())."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(255 - (255 - c) * amount):02x}" for c in (r, g, b))


def items_of(project: dict) -> list[dict]:
    """Chapters and bonuses in writing order."""
    charter = project.get("charter") or {}
    out = []
    for i, ch in enumerate(charter.get("chapters", []), 1):
        out.append({**ch, "kind": "chapter", "number": i})
    for i, b in enumerate(charter.get("bonuses", []), 1):
        out.append({**b, "kind": "bonus", "number": i})
    return out


def markdown_to_html(text: str, anchor: str, language: str) -> tuple[str, list[dict]]:
    """Render Markdown; returns (html, sections) where sections are the h2 headings with ids."""
    # A stray H1 would compete with the chapter title.
    text = re.sub(r"^# (?!#)", "## ", text, flags=re.M)
    # Two callouts separated only by a blank line would merge into one blockquote.
    text = re.sub(r"(^>.*\n)\s*\n(?=> ?\[!)", r"\1\n<!-- -->\n\n", text, flags=re.M)
    html = md.markdown(text, extensions=["tables", "fenced_code", "sane_lists", "attr_list"])
    html = html.replace("[PRÜFEN]", '<mark class="check">[PRÜFEN]</mark>')
    soup = BeautifulSoup(html, "html.parser")

    for bq in soup.find_all("blockquote"):
        first = bq.find("p")
        m = first and re.match(r"\s*\[!(\w+)\]\s*([^\n]*)\n?", first.decode_contents())
        if not m or m.group(1).upper() not in CALLOUTS:
            continue
        cls, names = CALLOUTS[m.group(1).upper()]
        rest = first.decode_contents()[m.end():]
        if rest.strip():
            first.clear()
            first.append(BeautifulSoup(rest, "html.parser"))
        else:
            first.decompose()
        title = soup.new_tag("div", attrs={"class": "callout-title"})
        title.append(BeautifulSoup(m.group(2).strip() or names.get(language, names["en"]), "html.parser"))
        bq.name = "div"
        bq["class"] = f"callout callout-{cls}"
        bq.insert(0, title)

    for li in soup.find_all("li"):
        target = li.find("p", recursive=False) or li
        first = next((c for c in target.contents if str(c).strip()), None)
        m = isinstance(first, str) and re.match(r"\s*\[([ xX])\]\s+", first)
        if not m:
            continue
        first.replace_with(first[m.end():])
        box = soup.new_tag("span", attrs={"class": "box" + (" checked" if m.group(1) != " " else "")})
        target.insert(0, box)
        li["class"] = "task"
        if li.parent and li.parent.name == "ul":
            li.parent["class"] = "tasks"

    # Model- or reference-derived HTML must stay inert.
    for tag in soup.find_all(["script", "style", "iframe", "object", "embed", "link", "meta", "form", "img", "svg"]):
        tag.decompose()
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr.startswith("on") or attr in ("style", "srcdoc"):
                del tag[attr]
        if tag.name == "a":
            href = tag.get("href", "")
            if not href.startswith(("http://", "https://", "mailto:")):
                tag.attrs.pop("href", None)

    sections = []
    for i, h in enumerate(soup.find_all("h2"), 1):
        h["id"] = f"{anchor}-s{i}"
        sections.append({"id": h["id"], "title": h.get_text(" ", strip=True)})
    for table in soup.find_all("table"):
        table.wrap(soup.new_tag("div", attrs={"class": "table-wrap"}))
    return str(soup), sections


def build_html(project: dict) -> str:
    language = project.get("language", "de")
    labels = LABELS.get(language, LABELS["de"])
    charter = project.get("charter") or {}
    design = project.get("design") or {}
    contents = project.get("contents") or {}
    parts = []
    for item in items_of(project):
        anchor = f"{item['kind']}-{item['number']}"
        text = (contents.get(item["id"]) or {}).get("markdown", "").strip()
        html, sections = markdown_to_html(text, anchor, language) if text else ("", [])
        parts.append({**item, "anchor": anchor, "html": html, "sections": sections})
    css = (HERE / "book.css").read_text()
    accent = ACCENTS.get(design.get("accent"), ACCENTS["indigo"])
    return _env.get_template("book.html").render(
        css=css,
        lang=language,
        labels=labels,
        accent=accent,
        tint=_tint(accent),
        author=design.get("author", ""),
        charter=charter,
        chapters=[p for p in parts if p["kind"] == "chapter"],
        bonuses=[p for p in parts if p["kind"] == "bonus"],
    )


def build_pdf(project: dict) -> bytes:
    from weasyprint import HTML  # imported lazily: slow import, only needed for export

    def no_fetch(url, *args, **kwargs):  # nothing in the book needs the network
        raise ValueError(f"external resource blocked: {url}")

    return HTML(string=build_html(project), url_fetcher=no_fetch).write_pdf()
