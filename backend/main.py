"""ProduktWerk: five-step workflow from niche to finished, sellable PDF."""
import asyncio
import hashlib
import hmac
import json
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import ai, config, db, jobs, manual, prompts, references, schemas
from .pdf import render


@asynccontextmanager
async def lifespan(_: FastAPI):
    if config.ON_RENDER and not config.APP_PASSWORD:
        raise RuntimeError("APP_PASSWORD must be set on a public host, otherwise anyone can spend your API credit.")
    db.init()
    yield


app = FastAPI(title="ProduktWerk", lifespan=lifespan, docs_url=None, redoc_url=None)

# ---------- Password gate ----------

COOKIE = "pw_session"


def _token() -> str:
    return hashlib.sha256(f"produktwerk:{config.APP_PASSWORD}".encode()).hexdigest()


def _authenticated(request: Request) -> bool:
    if not config.APP_PASSWORD:
        return True
    return hmac.compare_digest(request.cookies.get(COOKIE, ""), _token())


@app.middleware("http")
async def gate(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and path not in ("/api/status", "/api/login") and not _authenticated(request):
        return JSONResponse({"detail": "Nicht angemeldet."}, status_code=401)
    return await call_next(request)


class Login(BaseModel):
    password: str


@app.post("/api/login")
async def login(body: Login, request: Request):
    if not hmac.compare_digest(body.password.encode(), config.APP_PASSWORD.encode()):
        await asyncio.sleep(1)  # slows down guessing
        raise HTTPException(401, "Falsches Passwort.")
    resp = JSONResponse({"ok": True})
    resp.set_cookie(COOKIE, _token(), httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30,
                    secure=request.url.scheme == "https" or config.ON_RENDER)
    return resp


@app.get("/api/status")
def status(request: Request):
    return {
        "auth_required": bool(config.APP_PASSWORD),
        "authenticated": _authenticated(request),
        "has_key": config.has_api_key() or config.MOCK_AI,
        "mock": config.MOCK_AI,
        "model": config.MODEL,
    }


# ---------- Projects ----------

def _project(pid: str) -> dict:
    p = db.get_project(pid)
    if not p:
        raise HTTPException(404, "Projekt nicht gefunden.")
    p["generating"] = jobs.is_running(pid)
    return p


def _require(p: dict, *keys: str) -> None:
    missing = [k for k in keys if not p.get(k)]
    if missing:
        raise HTTPException(409, f"Vorheriger Schritt fehlt: {', '.join(missing)}.")


def _spec(kind: str, p: dict, *, mode: str = "", text: str = "", concept: dict | None = None) -> tuple[str, str, dict]:
    """(mock kind, user prompt, schema) for a structured step. One source for API and copy mode."""
    if kind == "niches":
        if mode == "specific":
            return "specific", prompts.specific(text), schemas.NICHES
        return "niches", prompts.niches(text), schemas.NICHES
    if kind == "concepts":
        _require(p, "uvz")
        return kind, prompts.concepts(p["uvz"]), schemas.CONCEPTS
    if kind == "transformation":
        _require(p, "uvz")
        if not concept:
            raise HTTPException(422, "Bitte zuerst ein Konzept waehlen.")
        return kind, prompts.transformation(p["uvz"], concept), schemas.TRANSFORMATION
    if kind == "charter":
        _require(p, "uvz", "concept", "transformation")
        return kind, prompts.charter(p), schemas.CHARTER
    raise HTTPException(422, "Unbekannter Schritt.")


async def _ai(p: dict, spec: tuple[str, str, dict], pasted: str | None = None) -> dict:
    """Run a structured step through the API, or take the answer the user pasted in copy mode."""
    kind, user, schema = spec
    if pasted is not None:
        try:
            return manual.parse_structured(pasted, schema)
        except manual.ManualError as e:
            raise HTTPException(422, str(e)) from e
    try:
        return await ai.structured(kind, prompts.system(p.get("language", "de")), user, schema)
    except ai.AIError as e:
        raise HTTPException(502, str(e)) from e


class NewProject(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    language: str = "de"


class PatchProject(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    language: str | None = None
    step: int | None = Field(default=None, ge=1, le=5)


@app.get("/api/projects")
def list_projects():
    return db.list_projects()


@app.post("/api/projects")
def create_project(body: NewProject):
    return db.create_project(body.name.strip(), body.language if body.language in ("de", "en") else "de")


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    return _project(pid)


@app.patch("/api/projects/{pid}")
def patch_project(pid: str, body: PatchProject):
    _project(pid)
    if body.name:
        db.rename_project(pid, body.name.strip())
    changes = {k: v for k, v in (("language", body.language), ("step", body.step)) if v is not None}
    if changes:
        db.update_state(pid, **changes)
    return _project(pid)


@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    jobs.cancel(pid)
    db.delete_project(pid)
    return {"ok": True}


# ---------- Step 1: Unique Value Zone ----------

class NichesIn(BaseModel):
    mode: str
    input: str = Field(min_length=3, max_length=8000)
    manual: str | None = None


class ManualIn(BaseModel):
    manual: str | None = None


class UvzIn(BaseModel):
    niche: dict


@app.post("/api/projects/{pid}/niches")
async def make_niches(pid: str, body: NichesIn):
    p = _project(pid)
    data = await _ai(p, _spec("niches", p, mode=body.mode, text=body.input), body.manual)
    db.update_state(pid, mode=body.mode, input=body.input, niches=data["niches"])
    return _project(pid)


@app.post("/api/projects/{pid}/uvz")
def choose_uvz(pid: str, body: UvzIn):
    p = _project(pid)
    if p.get("uvz") != body.niche:  # a different niche invalidates what was built on the old one
        db.update_state(pid, uvz=body.niche, concepts=None, concept=None, transformation=None)
    db.update_state(pid, step=max(p.get("step", 1), 2))
    return _project(pid)


# ---------- Step 2: Transformation map ----------

class ConceptIn(BaseModel):
    concept: dict
    manual: str | None = None


@app.post("/api/projects/{pid}/concepts")
async def make_concepts(pid: str, body: ManualIn | None = None):
    p = _project(pid)
    data = await _ai(p, _spec("concepts", p), body.manual if body else None)
    db.update_state(pid, concepts=data["concepts"])
    return _project(pid)


@app.post("/api/projects/{pid}/transformation")
async def make_transformation(pid: str, body: ConceptIn):
    p = _project(pid)
    data = await _ai(p, _spec("transformation", p, concept=body.concept), body.manual)
    db.update_state(pid, concept=body.concept, transformation=data)
    return _project(pid)


# ---------- Step 3: References ----------

class ReferenceIn(BaseModel):
    type: str
    title: str = Field(default="", max_length=200)
    content: str = ""
    url: str = Field(default="", max_length=2000)


@app.post("/api/projects/{pid}/references")
async def add_reference(pid: str, body: ReferenceIn):
    p = _project(pid)
    refs = p.get("references", [])
    if body.type == "url":
        try:
            title, text = await references.fetch_url(body.url.strip())
        except references.ReferenceError as e:
            raise HTTPException(422, str(e)) from e
        ref = {"type": "url", "url": body.url.strip(), "title": body.title.strip() or title, "content": text}
    else:
        if len(body.content.strip()) < 10:
            raise HTTPException(422, "Bitte etwas Text einfuegen.")
        ref = {"type": "note", "title": body.title.strip() or "Notiz", "content": body.content.strip()}
    total = sum(len(r["content"]) for r in refs) + len(ref["content"])
    if total > references.MAX_TOTAL_CHARS:
        raise HTTPException(
            422,
            f"Zu viel Referenzmaterial ({total:,} Zeichen, erlaubt sind {references.MAX_TOTAL_CHARS:,}). "
            "Bitte kuerzen oder eine andere Referenz entfernen.",
        )
    ref["id"] = db.new_id()
    ref["title"] = re.sub(r'["<>]', "", ref["title"])[:200]
    db.update_state(pid, references=refs + [ref])
    return _project(pid)


@app.delete("/api/projects/{pid}/references/{rid}")
def delete_reference(pid: str, rid: str):
    p = _project(pid)
    db.update_state(pid, references=[r for r in p.get("references", []) if r["id"] != rid])
    return _project(pid)


# ---------- Step 4: Charter ----------

class Chapter(BaseModel):
    id: str = ""
    title: str = Field(min_length=1, max_length=300)
    summary: str = ""
    sections: list[str] = []


class Bonus(BaseModel):
    id: str = ""
    title: str = Field(min_length=1, max_length=300)
    description: str = ""


class Charter(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    subtitle: str = ""
    target_price: str = ""
    reading_time: str = ""
    chapters: list[Chapter] = Field(min_length=1, max_length=40)
    bonuses: list[Bonus] = Field(default=[], max_length=20)


def _save_charter(pid: str, charter: dict) -> dict:
    for item in charter["chapters"] + charter["bonuses"]:
        item["id"] = item.get("id") or db.new_id()
        if "sections" in item:
            item["sections"] = [s.strip() for s in item["sections"] if s.strip()]
    db.update_state(pid, charter=charter)
    db.delete_contents(pid, {i["id"] for i in charter["chapters"] + charter["bonuses"]})
    return _project(pid)


@app.post("/api/projects/{pid}/charter")
async def make_charter(pid: str, body: ManualIn | None = None):
    p = _project(pid)
    spec = _spec("charter", p)
    if p["generating"]:
        raise HTTPException(409, "Waehrend der Generierung kann die Struktur nicht neu erstellt werden.")
    data = await _ai(p, spec, body.manual if body else None)
    return _save_charter(pid, data)


@app.put("/api/projects/{pid}/charter")
def put_charter(pid: str, body: Charter):
    p = _project(pid)
    if p["generating"]:
        raise HTTPException(409, "Waehrend der Generierung kann die Struktur nicht geaendert werden.")
    return _save_charter(pid, body.model_dump())


class Design(BaseModel):
    author: str = Field(default="", max_length=120)
    accent: str = "indigo"


@app.put("/api/projects/{pid}/design")
def put_design(pid: str, body: Design):
    _project(pid)
    db.update_state(pid, design=body.model_dump())
    return _project(pid)


# ---------- Step 5: Writing, preview, PDF ----------

class GenerateIn(BaseModel):
    item_ids: list[str] | None = None  # None = everything that is not written yet
    instruction: str = Field(default="", max_length=4000)


class ContentIn(BaseModel):
    markdown: str


@app.post("/api/projects/{pid}/generate")
async def generate(pid: str, body: GenerateIn):
    p = _project(pid)
    _require(p, "charter")
    if not (config.has_api_key() or config.MOCK_AI):
        raise HTTPException(502, "Kein ANTHROPIC_API_KEY gesetzt. Trage ihn in der .env-Datei ein und starte die App neu.")
    order = [i["id"] for i in render.items_of(p)]
    if body.item_ids is None:
        ids = [i for i in order if p["contents"].get(i, {}).get("status") != "done"]
    else:
        ids = [i for i in order if i in set(body.item_ids)]
    if not ids:
        raise HTTPException(409, "Es gibt nichts zu schreiben.")
    try:
        jobs.start(pid, ids, body.instruction.strip())
    except RuntimeError:
        raise HTTPException(409, "Die Generierung laeuft bereits.")
    return _project(pid)


@app.post("/api/projects/{pid}/cancel")
async def cancel(pid: str):
    jobs.cancel(pid)
    await asyncio.sleep(0.1)
    return _project(pid)


@app.get("/api/projects/{pid}/events")
async def events(pid: str, request: Request):
    _project(pid)

    async def stream():
        q = jobs.subscribe(pid)
        try:
            yield "retry: 2000\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                if await request.is_disconnected():
                    break
        finally:
            jobs.unsubscribe(pid, q)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.put("/api/projects/{pid}/contents/{item_id}")
def put_content(pid: str, item_id: str, body: ContentIn):
    p = _project(pid)
    if p["generating"]:
        raise HTTPException(409, "Waehrend der Generierung kann nicht bearbeitet werden.")
    if item_id not in {i["id"] for i in render.items_of(p)}:
        raise HTTPException(404, "Teil nicht gefunden.")
    db.set_content(pid, item_id, markdown=manual.parse_markdown(body.markdown), status="done")
    return _project(pid)


# ---------- Copy mode: prompts to run in the user's own Claude chat ----------

class PromptIn(BaseModel):
    kind: str
    mode: str = ""
    input: str = Field(default="", max_length=8000)
    concept: dict | None = None
    item_id: str = ""
    instruction: str = Field(default="", max_length=4000)


@app.post("/api/projects/{pid}/prompt")
def make_prompt(pid: str, body: PromptIn):
    p = _project(pid)
    system = prompts.system(p.get("language", "de"))
    if body.kind == "write":
        _require(p, "charter")
        items = render.items_of(p)
        item = next((i for i in items if i["id"] == body.item_id), None)
        if not item:
            raise HTTPException(404, "Teil nicht gefunden.")
        previous = []
        for other in items:
            if other["id"] == item["id"]:
                break
            c = p["contents"].get(other["id"])
            if c and c["status"] == "done" and c["markdown"].strip():
                previous.append((other["title"], c["markdown"]))
        user = prompts.write_item(p, item, previous, body.instruction.strip())
        return {"prompt": manual.writing_prompt(system, prompts.project_context(p), user)}
    if body.kind == "niches" and len(body.input.strip()) < 3:
        raise HTTPException(422, "Bitte zuerst etwas eingeben.")
    _, user, schema = _spec(body.kind, p, mode=body.mode, text=body.input, concept=body.concept)
    return {"prompt": manual.structured_prompt(system, user, schema)}


@app.get("/api/projects/{pid}/preview")
def preview(pid: str):
    p = _project(pid)
    _require(p, "charter")
    # The document contains model-written HTML; it must not be able to run scripts or load anything.
    return HTMLResponse(render.build_html(p), headers={
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
        "Cache-Control": "no-store",
    })


@app.get("/api/projects/{pid}/pdf")
async def pdf(pid: str):
    p = _project(pid)
    _require(p, "charter")
    data = await asyncio.to_thread(render.build_pdf, p)
    name = re.sub(r"[^A-Za-z0-9]+", "-", p["charter"]["title"].encode("ascii", "ignore").decode()).strip("-") or "produkt"
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{name[:80]}.pdf"', "Cache-Control": "no-store"})


# ---------- Frontend ----------

if config.FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=config.FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        file = (config.FRONTEND_DIST / path).resolve()
        if path and file.is_file() and config.FRONTEND_DIST.resolve() in file.parents:
            return FileResponse(file)
        return FileResponse(config.FRONTEND_DIST / "index.html")
