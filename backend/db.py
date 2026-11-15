"""SQLite storage: one JSON state document per project, one row per written content item."""
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS contents (
    project_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    markdown TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT NOT NULL DEFAULT '',
    updated_at REAL NOT NULL,
    PRIMARY KEY (project_id, item_id)
);
"""


@contextmanager
def connect():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DATA_DIR / "produktwerk.db", timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init():
    with connect() as c:
        c.executescript(SCHEMA)
        # A restart kills in-flight generation; mark those items so they can be retried.
        c.execute("UPDATE contents SET status='error', error='Abgebrochen (Neustart)' WHERE status='running'")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def create_project(name: str, language: str) -> dict:
    pid, now = new_id(), time.time()
    state = {"language": language, "step": 1, "references": []}
    with connect() as c:
        c.execute("INSERT INTO projects VALUES (?,?,?,?,?)", (pid, name, json.dumps(state), now, now))
    return get_project(pid)


def list_projects() -> list[dict]:
    with connect() as c:
        rows = c.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
    out = []
    for r in rows:
        s = json.loads(r["state"])
        out.append({
            "id": r["id"], "name": r["name"], "step": s.get("step", 1),
            "title": (s.get("charter") or {}).get("title", ""), "updated_at": r["updated_at"],
        })
    return out


def get_project(pid: str) -> dict | None:
    with connect() as c:
        r = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        if not r:
            return None
        rows = c.execute("SELECT * FROM contents WHERE project_id=?", (pid,)).fetchall()
    state = json.loads(r["state"])
    contents = {x["item_id"]: {"markdown": x["markdown"], "status": x["status"], "error": x["error"]} for x in rows}
    return {"id": r["id"], "name": r["name"], **state, "contents": contents}


def update_state(pid: str, **changes) -> dict:
    """Merge keys into the project state. A value of None removes the key."""
    with connect() as c:
        r = c.execute("SELECT state FROM projects WHERE id=?", (pid,)).fetchone()
        state = json.loads(r["state"])
        for k, v in changes.items():
            if v is None:
                state.pop(k, None)
            else:
                state[k] = v
        c.execute("UPDATE projects SET state=?, updated_at=? WHERE id=?", (json.dumps(state), time.time(), pid))
    return get_project(pid)


def import_project(pid: str, name: str, state: dict, contents: dict) -> bool:
    """Restore a project from a backup. Returns False (and changes nothing) if the id already exists."""
    now = time.time()
    with connect() as c:
        if c.execute("SELECT 1 FROM projects WHERE id=?", (pid,)).fetchone():
            return False
        c.execute("INSERT INTO projects VALUES (?,?,?,?,?)", (pid, name, json.dumps(state), now, now))
        for item_id, item in contents.items():
            c.execute("INSERT INTO contents VALUES (?,?,?,?,?,?)",
                      (pid, item_id, item["markdown"], item["status"], "", now))
    return True


def rename_project(pid: str, name: str):
    with connect() as c:
        c.execute("UPDATE projects SET name=?, updated_at=? WHERE id=?", (name, time.time(), pid))


def delete_project(pid: str):
    with connect() as c:
        c.execute("DELETE FROM contents WHERE project_id=?", (pid,))
        c.execute("DELETE FROM projects WHERE id=?", (pid,))


def set_content(pid: str, item_id: str, *, markdown: str | None = None, status: str | None = None, error: str = ""):
    with connect() as c:
        c.execute(
            "INSERT OR IGNORE INTO contents (project_id, item_id, updated_at) VALUES (?,?,?)",
            (pid, item_id, time.time()),
        )
        if markdown is not None:
            c.execute("UPDATE contents SET markdown=? WHERE project_id=? AND item_id=?", (markdown, pid, item_id))
        if status is not None:
            c.execute(
                "UPDATE contents SET status=?, error=?, updated_at=? WHERE project_id=? AND item_id=?",
                (status, error, time.time(), pid, item_id),
            )


def delete_contents(pid: str, keep_ids: set[str]):
    with connect() as c:
        rows = c.execute("SELECT item_id FROM contents WHERE project_id=?", (pid,)).fetchall()
        for r in rows:
            if r["item_id"] not in keep_ids:
                c.execute("DELETE FROM contents WHERE project_id=? AND item_id=?", (pid, r["item_id"]))
