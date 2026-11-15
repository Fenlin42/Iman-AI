"""Fetch a URL and reduce it to readable text. Blocks internal addresses (the app may run on a public host)."""
import ipaddress
import os
import socket
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

MAX_BYTES = 3_000_000
MAX_TOTAL_CHARS = 600_000  # all references of one project together


class ReferenceError(Exception):
    pass


def _check_host(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ReferenceError("Nur http(s)-Adressen sind erlaubt.")
    host = parsed.hostname
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        # Behind an outbound proxy local DNS may not resolve public names; the proxy does the lookup.
        if os.getenv("HTTPS_PROXY") or os.getenv("https_proxy"):
            if host == "localhost" or host.endswith((".local", ".internal")):
                raise ReferenceError("Interne Adressen sind nicht erlaubt.")
            return
        raise ReferenceError("Adresse nicht gefunden.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ReferenceError("Interne Adressen sind nicht erlaubt.")


async def fetch_url(url: str) -> tuple[str, str]:
    """Return (title, text)."""
    async with httpx.AsyncClient(timeout=20, follow_redirects=False,
                                 headers={"User-Agent": "Mozilla/5.0 (compatible; reference-fetcher)"}) as http:
        for _ in range(5):
            _check_host(url)
            try:
                resp = await http.get(url)
            except httpx.HTTPError as e:
                raise ReferenceError(f"Seite nicht erreichbar: {type(e).__name__}") from e
            if resp.is_redirect and resp.headers.get("location"):
                url = urljoin(url, resp.headers["location"])
                continue
            break
        else:
            raise ReferenceError("Zu viele Weiterleitungen.")
    if resp.status_code >= 400:
        raise ReferenceError(f"Seite antwortet mit Status {resp.status_code}.")
    if len(resp.content) > MAX_BYTES:
        raise ReferenceError("Seite ist zu gross (ueber 3 MB).")
    ctype = resp.headers.get("content-type", "")
    if "html" not in ctype and "text" not in ctype:
        raise ReferenceError(f"Dieser Inhaltstyp wird nicht unterstuetzt ({ctype or 'unbekannt'}).")
    if "html" not in ctype:
        return url, resp.text.strip()
    soup = BeautifulSoup(resp.text, "html.parser")
    title = (soup.title.string or "").strip() if soup.title else ""
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "form", "svg", "iframe"]):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup.body or soup
    lines = [ln.strip() for ln in main.get_text("\n").splitlines()]
    text = "\n".join(ln for ln in lines if ln)
    if len(text) < 200:
        raise ReferenceError("Auf der Seite wurde kaum lesbarer Text gefunden (evtl. per JavaScript geladen).")
    return title or url, text
