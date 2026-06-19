"""Readable source extraction utilities for connector/runtime source payloads.

Lattice: RF-P1 Source Sovereignty; RF-P4 Gates Fail Closed.
"""

from __future__ import annotations

import html
import ipaddress
import re
from urllib.parse import urlparse

_BLOCK_RE = re.compile(r"<(script|style|noscript|svg|canvas)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"[ \t\r\f\v]+")
_BLANK_RE = re.compile(r"\n{3,}")


def readable_text_from_html(payload: str, *, max_chars: int = 24_000) -> str:
    """Extract readable text from an HTML-ish payload without JS/CSS noise."""
    without_blocks = _BLOCK_RE.sub("\n", payload)
    with_breaks = re.sub(r"</(p|div|section|article|main|li|tr|h[1-6])>", "\n", without_blocks, flags=re.IGNORECASE)
    text = _TAG_RE.sub(" ", with_breaks)
    text = html.unescape(text)
    lines = []
    for raw_line in text.splitlines():
        line = _SPACE_RE.sub(" ", raw_line).strip()
        if line:
            lines.append(line)
    readable = _BLANK_RE.sub("\n\n", "\n".join(lines)).strip()
    return readable[:max_chars]


def fetch_readable_text(url: str, *, timeout: int = 20, max_chars: int = 24_000) -> str:
    """Network fetching is connector-owned; normalize already-observed payloads here."""
    _validate_fetch_url(url)
    _ = timeout, max_chars
    raise RuntimeError("network source fetching requires a connector policy; pass observed payloads to readable_text_from_html")


def _validate_fetch_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("source URL must use http or https")
    if not parsed.hostname:
        raise ValueError("source URL must include a host")
    if parsed.username or parsed.password:
        raise ValueError("source URL must not include credentials")
    if parsed.hostname == "localhost":
        raise ValueError("source URL resolves to a non-public address")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        return
    if address.is_private or address.is_loopback or address.is_link_local or address.is_multicast or address.is_reserved:
        raise ValueError("source URL resolves to a non-public address")
