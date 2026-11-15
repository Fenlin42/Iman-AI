"""Background writing jobs with live events for the browser."""
import asyncio
import time

from . import ai, db, prompts
from .pdf.render import items_of

_tasks: dict[str, asyncio.Task] = {}
_subscribers: dict[str, set[asyncio.Queue]] = {}


def is_running(pid: str) -> bool:
    t = _tasks.get(pid)
    return bool(t and not t.done())


def subscribe(pid: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(pid, set()).add(q)
    return q


def unsubscribe(pid: str, q: asyncio.Queue) -> None:
    _subscribers.get(pid, set()).discard(q)


def _emit(pid: str, event: dict) -> None:
    for q in _subscribers.get(pid, set()):
        q.put_nowait(event)


def start(pid: str, item_ids: list[str], instruction: str = "") -> None:
    if is_running(pid):
        raise RuntimeError("running")
    for item_id in item_ids:
        db.set_content(pid, item_id, status="queued")
    _tasks[pid] = asyncio.create_task(_run(pid, item_ids, instruction))


def cancel(pid: str) -> None:
    t = _tasks.get(pid)
    if t and not t.done():
        t.cancel()


async def _run(pid: str, item_ids: list[str], instruction: str) -> None:
    current = None
    try:
        for item_id in item_ids:
            current = item_id
            project = db.get_project(pid)
            items = items_of(project)
            item = next((i for i in items if i["id"] == item_id), None)
            if item is None:  # removed from the structure in the meantime
                continue
            # Everything already written that comes before this item in the book.
            previous = []
            for other in items:
                if other["id"] == item_id:
                    break
                c = project["contents"].get(other["id"])
                if c and c["status"] == "done" and c["markdown"].strip():
                    previous.append((other["title"], c["markdown"]))
            db.set_content(pid, item_id, markdown="", status="running")
            _emit(pid, {"type": "start", "item_id": item_id})
            text, last_save = "", time.monotonic()
            async for chunk in ai.write(
                prompts.project_context(project),
                prompts.system(project.get("language", "de")),
                prompts.write_item(project, item, previous, instruction),
            ):
                text += chunk
                _emit(pid, {"type": "delta", "item_id": item_id, "text": chunk})
                if time.monotonic() - last_save > 2:
                    db.set_content(pid, item_id, markdown=text)
                    last_save = time.monotonic()
            db.set_content(pid, item_id, markdown=text.strip(), status="done")
            _emit(pid, {"type": "done", "item_id": item_id})
        _emit(pid, {"type": "finished"})
    except asyncio.CancelledError:
        _mark_unfinished(pid, item_ids, "Abgebrochen")
        _emit(pid, {"type": "finished", "cancelled": True})
    except Exception as e:  # noqa: BLE001 - reported to the user
        message = str(e) if isinstance(e, ai.AIError) else f"Unerwarteter Fehler: {e}"
        if current:
            db.set_content(pid, current, status="error", error=message)
        _mark_unfinished(pid, item_ids, "Nicht gestartet")
        _emit(pid, {"type": "error", "item_id": current, "message": message})
        _emit(pid, {"type": "finished"})


def _mark_unfinished(pid: str, item_ids: list[str], reason: str) -> None:
    contents = db.get_project(pid)["contents"]
    for item_id in item_ids:
        if contents.get(item_id, {}).get("status") in ("queued", "running"):
            db.set_content(pid, item_id, status="error", error=reason)
