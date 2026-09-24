"""Safety filters: deterministic pre/post guardrails. Zero LLM calls, 0ms path.
Privacy: PII redacted before planning. Security: prompt-injection + blocklist
reject. Writes (ticket/email) require explicit confirmation token via MCP.
"""
from __future__ import annotations

import re

_BLOCK = ("drop table", "delete from", "ignore policy", "ignore previous",
          "system prompt", "jailbreak", "bypass policy", "<script")
_PII = ((re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "<EMAIL>"),
        (re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"), "<PHONE>"),
        (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "<SSN>"))

_OUT_OF_CORPUS = ("cake", "weather", "sports", "movie", "recipe", "bake", "python", "scrape")


def redact_pii(text: str) -> str:
    for rx, tok in _PII:
        text = rx.sub(tok, text)
    return text


def filter_input(text: str) -> dict:
    t = text.lower()
    if any(b in t for b in _BLOCK):
        return {"decision": "reject", "reason": "injection_or_rules_violation"}
    if any(w in t for w in _OUT_OF_CORPUS):
        return {"decision": "redirect", "reason": "out_of_corpus"}
    return {"decision": "pass", "redacted": redact_pii(text)}


def check_answer(answer: str, citations: list, claims: list) -> dict:
    ok = len(citations) > 0 if claims else True
    leaked = bool(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", answer or ""))
    return {"citations_present": len(citations) > 0, "claims": len(claims),
            "cited": len(citations), "pass": bool(ok) and not leaked,
            "pii_leak": leaked}
