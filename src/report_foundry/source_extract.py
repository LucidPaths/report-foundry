"""Readable text normalization for already-observed source payloads.

Lattice: RF-P1 Source Sovereignty; RF-P4 Gates Fail Closed.
"""

from __future__ import annotations

import html
import re

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
