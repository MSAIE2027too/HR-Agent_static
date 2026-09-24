"""SQLite vector store. Cosine top-k over normalized embeddings. stdlib only."""
from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path

from . import embeddings as emb_mod
from .ingest import Chunk, ingest_dir


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _connect(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def build_index(policy_dir: str | Path, db_path: str | Path,
                provider=None) -> dict:
    provider = provider or emb_mod.get_provider()
    chunks = ingest_dir(policy_dir)
    texts = [f"{c.title} {c.section} {c.text}" for c in chunks]
    vecs = provider.embed(texts)
    con = _connect(db_path)
    con.execute("DROP TABLE IF EXISTS chunks")
    con.execute(
        "CREATE TABLE chunks (doc_id TEXT, title TEXT, section TEXT, "
        "text TEXT, snippet_hash TEXT, embedding TEXT)"
    )
    con.executemany(
        "INSERT INTO chunks VALUES (?,?,?,?,?,?)",
        [(c.doc_id, c.title, c.section, c.text, c.snippet_hash,
          json.dumps(v)) for c, v in zip(chunks, vecs)],
    )
    con.commit()
    count = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    con.close()
    return {"chunks": count, "docs": len({c.doc_id for c in chunks}),
            "provider": provider.name}


def search(db_path: str | Path, query: str, k: int = 4,
           provider=None) -> list[dict]:
    provider = provider or emb_mod.get_provider()
    q = provider.embed([query])[0]
    con = _connect(db_path)
    rows = con.execute(
        "SELECT doc_id, title, section, text, snippet_hash, embedding "
        "FROM chunks").fetchall()
    con.close()
    scored = []
    for doc_id, title, section, text, h, ejs in rows:
        s = _cosine(q, json.loads(ejs))
        if any(t in f"{title} {section} {text}".lower()
               for t in query.lower().split() if len(t) > 3):
            s += 0.05
        scored.append((s, doc_id, title, section, text, h))
    scored.sort(key=lambda r: -r[0])
    return [{"doc_id": d, "title": t, "section": s, "snippet": x, "hash": h,
             "score": round(score, 4)}
            for score, d, t, s, x, h in scored[:k]]


def doc_count(db_path: str | Path) -> int:
    if not Path(db_path).exists():
        return 0
    con = _connect(db_path)
    try:
        n = con.execute("SELECT COUNT(DISTINCT doc_id) FROM chunks").fetchone()[0]
    except sqlite3.OperationalError:
        n = 0
    con.close()
    return n
