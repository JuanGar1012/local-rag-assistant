from __future__ import annotations

import ipaddress
import re
import socket
from pathlib import PurePosixPath
from urllib.parse import urlparse

import httpx

from app.core.config import Settings
from app.rag.ingestion import text_from_bytes

TEXT_LIKE_CONTENT_TYPES = (
    "text/plain",
    "text/markdown",
    "text/html",
    "application/pdf",
)

DEFAULT_FETCH_HEADERS = {
    # Some public sites block generic non-browser clients.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
}


def _extract_text_from_html(html: str) -> str:
    no_script = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    plain = re.sub(r"<[^>]+>", " ", no_script)
    return " ".join(plain.split())


def _infer_filename_from_url(url: str, content_type: str) -> str:
    parsed = urlparse(url)
    leaf = PurePosixPath(parsed.path).name or "document"
    ext = PurePosixPath(leaf).suffix.lower()
    if ext in {".pdf", ".md", ".txt"}:
        return leaf
    if "pdf" in content_type.lower():
        return f"{leaf}.pdf"
    if "markdown" in content_type.lower():
        return f"{leaf}.md"
    return f"{leaf}.txt"


def _looks_like_text(raw: bytes, max_check: int = 2048) -> bool:
    sample = raw[:max_check]
    if not sample:
        return False
    if b"\x00" in sample:
        return False
    printable = sum(1 for b in sample if b in b"\t\n\r" or 32 <= b <= 126)
    return (printable / len(sample)) > 0.85


def _is_private_or_local(hostname: str) -> bool:
    if hostname.lower() in {"localhost"}:
        return True
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip_raw = info[4][0]
        ip = ipaddress.ip_address(ip_raw)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return True
    return False


def validate_ingest_url(url: str, settings: Settings) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http/https links are supported.")
    if not parsed.hostname:
        raise ValueError("URL is missing host.")
    host = parsed.hostname.lower()
    if settings.ingest_allowed_hosts and host not in settings.ingest_allowed_hosts:
        raise ValueError("Host not in allowlist.")
    if host in settings.ingest_blocked_hosts:
        raise ValueError("Host is blocked.")
    if not settings.INGEST_ALLOW_PRIVATE_IPS and _is_private_or_local(host):
        raise ValueError("Private or local network hosts are blocked.")


def fetch_link_text(url: str, settings: Settings) -> tuple[str, str]:
    validate_ingest_url(url, settings)
    response = httpx.get(url, timeout=20.0, follow_redirects=True, headers=DEFAULT_FETCH_HEADERS)
    if response.status_code in {403, 429}:
        raise ValueError(
            f"Source denied automated fetch (HTTP {response.status_code}). "
            "Try a raw text/markdown URL (for example raw.githubusercontent.com) or upload the file directly."
        )
    response.raise_for_status()
    raw = response.content
    if len(raw) > settings.INGEST_MAX_UPLOAD_BYTES:
        raise ValueError(f"Fetched content too large. Limit is {settings.INGEST_MAX_UPLOAD_BYTES} bytes.")

    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    filename = _infer_filename_from_url(url, content_type)
    if "html" in content_type:
        text = _extract_text_from_html(response.text)
    elif content_type in TEXT_LIKE_CONTENT_TYPES or content_type == "":
        try:
            text = text_from_bytes(filename, raw)
        except ValueError:
            if _looks_like_text(raw):
                text = raw.decode("utf-8", errors="ignore")
            else:
                raise ValueError(f"Unsupported content type: {content_type or 'unknown'}")
    else:
        raise ValueError(f"Unsupported content type: {content_type}")
    if not text.strip():
        raise ValueError("No extractable text from link.")
    return filename, text
