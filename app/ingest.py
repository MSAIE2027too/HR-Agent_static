"""Deterministic heading-aware ingestion. MD + TXT + HTML + PDF. No network."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


@dataclass
class Chunk:
    doc_id: str
    title: str
    section: str
    text: str
    snippet_hash: str


def _split_sections(doc_id: str, title: str, body: str) -> list[tuple[str, str]]:
    parts: list[tuple[str, str]] = []
    current_section = "overview"
    current_lines: list[str] = []
    for line in body.splitlines():
        m = re.match(r"##\s+(.*)", line)
        if m:
            if current_lines:
                parts.append((current_section, "\n".join(current_lines).strip()))
            current_section = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        parts.append((current_section, "\n".join(current_lines).strip()))
    return [(s, t) for s, t in parts if t]


def _window(text: str) -> list[str]:
    if len(text) <= CHUNK_SIZE:
        return [text]
    out, start = [], 0
    while start < len(text):
        out.append(text[start:start + CHUNK_SIZE])
        if start + CHUNK_SIZE >= len(text):
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return out


def ingest_file(path: Path) -> list[Chunk]:
    doc_id = path.stem
    suffix = path.suffix.lower()
    if suffix == ".html":
        raw = _html_to_text(path.read_text(encoding="utf-8"))
    elif suffix == ".pdf":
        raw = _pdf_to_text(path)
        if not raw:
            return []
    else:
        raw = path.read_text(encoding="utf-8")
    title = doc_id
    body = raw
    m = re.match(r"#\s+(.*)", raw)
    if m:
        title = m.group(1).strip()
        body = raw[m.end():]
    chunks = []
    for section, text in _split_sections(doc_id, title, body):
        for window in _window(text):
            h = hashlib.sha256(f"{doc_id}|{section}|{window}".encode()).hexdigest()[:16]
            chunks.append(Chunk(doc_id, title, section, window, h))
    return chunks


class _TextHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        t = data.strip()
        if t:
            self.parts.append(t)


def _html_to_text(html: str) -> str:
    p = _TextHTML()
    p.feed(html)
    return "\n".join(p.parts)


def _pdf_to_text(path: Path) -> str:
    try:
        from pypdf import PdfReader  # optional; skip gracefully if absent
    except Exception:
        return ""
    try:
        return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(path)).pages)
    except Exception:
        return ""


def ingest_dir(policy_dir: str | Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(Path(policy_dir).glob("*")):
        if path.suffix.lower() in {".md", ".txt", ".html", ".pdf"}:
            chunks.extend(ingest_file(path))
    return chunks
