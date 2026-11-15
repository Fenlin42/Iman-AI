"""End-to-end API test in mock mode: all five steps, editing, PDF."""
import io
import os
import time

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from backend import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "MOCK_AI", True)
    monkeypatch.setattr(config, "APP_PASSWORD", "")
    from backend.main import app
    with TestClient(app) as c:
        yield c


def wait_done(client, pid):
    for _ in range(200):
        p = client.get(f"/api/projects/{pid}").json()
        if not p["generating"]:
            return p
        time.sleep(0.05)
    raise AssertionError("generation did not finish")


def build_to_charter(client):
    pid = client.post("/api/projects", json={"name": "Test"}).json()["id"]
    p = client.post(f"/api/projects/{pid}/niches", json={"mode": "explore", "input": "Physiotherapie"}).json()
    assert len(p["niches"]) == 10
    client.post(f"/api/projects/{pid}/uvz", json={"niche": p["niches"][2]})
    p = client.post(f"/api/projects/{pid}/concepts").json()
    assert len(p["concepts"]) == 5
    p = client.post(f"/api/projects/{pid}/transformation", json={"concept": p["concepts"][1]}).json()
    assert len(p["transformation"]["milestones"]) >= 6
    p = client.post(f"/api/projects/{pid}/references",
                    json={"type": "note", "title": "Meine Methode", "content": "Schritt eins, zwei, drei."}).json()
    assert len(p["references"]) == 1
    p = client.post(f"/api/projects/{pid}/charter").json()
    assert all(c["id"] for c in p["charter"]["chapters"])
    return pid, p


def test_full_workflow(client):
    pid, p = build_to_charter(client)
    charter = p["charter"]

    # Edit the structure: delete one chapter, rename one, add one.
    removed = charter["chapters"].pop(1)
    charter["chapters"][0]["title"] = "Umbenannt"
    charter["chapters"].append({"title": "Neu", "summary": "", "sections": ["A", "B"]})
    p = client.put(f"/api/projects/{pid}/charter", json=charter).json()
    titles = [c["title"] for c in p["charter"]["chapters"]]
    assert titles[0] == "Umbenannt" and titles[-1] == "Neu" and removed["title"] not in titles[1:2]

    client.post(f"/api/projects/{pid}/generate", json={})
    p = wait_done(client, pid)
    ids = [c["id"] for c in p["charter"]["chapters"] + p["charter"]["bonuses"]]
    assert all(p["contents"][i]["status"] == "done" and len(p["contents"][i]["markdown"]) > 200 for i in ids)
    assert client.post(f"/api/projects/{pid}/generate", json={}).status_code == 409  # nothing left

    # Manual edit and single regeneration.
    p = client.put(f"/api/projects/{pid}/contents/{ids[0]}", json={"markdown": "## Eigener Text\n\nHallo."}).json()
    assert p["contents"][ids[0]]["markdown"].startswith("## Eigener Text")
    client.post(f"/api/projects/{pid}/generate", json={"item_ids": [ids[1]], "instruction": "kuerzer"})
    wait_done(client, pid)

    html = client.get(f"/api/projects/{pid}/preview")
    assert "Eigener Text" in html.text and "callout-warning" in html.text and "sandbox" in html.headers["content-security-policy"]

    pdf = client.get(f"/api/projects/{pid}/pdf")
    assert pdf.headers["content-type"] == "application/pdf"
    reader = PdfReader(io.BytesIO(pdf.content))
    assert len(reader.pages) >= 6
    toc = reader.pages[1].extract_text()
    assert "Inhalt" in toc and "Umbenannt" in toc

    # Stored on disk: a fresh read returns everything.
    assert client.get("/api/projects").json()[0]["title"] == p["charter"]["title"]


def test_requires_previous_steps(client):
    pid = client.post("/api/projects", json={"name": "Leer"}).json()["id"]
    assert client.post(f"/api/projects/{pid}/concepts").status_code == 409
    assert client.post(f"/api/projects/{pid}/charter").status_code == 409
    assert client.get(f"/api/projects/{pid}/pdf").status_code == 409
    assert client.get("/api/projects/nope").status_code == 404


def test_new_niche_resets_downstream(client):
    pid, p = build_to_charter(client)
    p = client.post(f"/api/projects/{pid}/uvz", json={"niche": p["niches"][5]}).json()
    assert "concept" not in p and "transformation" not in p


def test_password_gate(client, monkeypatch):
    from backend import config
    monkeypatch.setattr(config, "APP_PASSWORD", "geheim")
    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/status").json() == {
        "auth_required": True, "authenticated": False, "has_key": True, "mock": True, "model": config.MODEL}
    monkeypatch.setattr("asyncio.sleep", lambda *_: _noop())
    assert client.post("/api/login", json={"password": "falsch"}).status_code == 401
    assert client.post("/api/login", json={"password": "geheim"}).status_code == 200
    assert client.get("/api/projects").status_code == 200


async def _noop():
    return None


def test_content_is_sanitised():
    from backend.pdf.render import markdown_to_html
    html, _ = markdown_to_html('Hi <script>alert(1)</script> <img src="http://x/a.png" onerror="x()"> [l](javascript:alert(1))', "c", "de")
    assert "script" not in html and "<img" not in html and "javascript:" not in html


def test_adjacent_callouts_stay_separate():
    from backend.pdf.render import markdown_to_html
    html, _ = markdown_to_html("> [!TIP] A\n> eins\n\n> [!WARNING] B\n> zwei\n", "c", "de")
    assert html.count('class="callout ') == 2 and "[!" not in html


def test_internal_urls_are_blocked():
    import asyncio
    from backend import references
    for url in ("http://127.0.0.1:8000/x", "http://localhost/x", "http://169.254.169.254/latest", "file:///etc/passwd"):
        with pytest.raises(references.ReferenceError):
            asyncio.run(references.fetch_url(url))
