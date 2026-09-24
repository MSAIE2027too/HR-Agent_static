"""MCP tool surface. All agent tool use goes through mcp_list_tools / mcp_call_tool.

Backends: policy RAG (app.vector_store) + mock JSON (mock_data/). Errors are
returned as {ok:false, error, hint} — never raised across the transport.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_DIR = Path(os.environ.get("POLICY_DIR", REPO_ROOT / "policy_docs"))
DB_PATH = Path(os.environ.get("RAG_DB", REPO_ROOT / "data" / "rag.db"))
MOCK_DIR = Path(os.environ.get("MOCK_DIR", REPO_ROOT / "mock_data"))

TOOL_SCHEMAS = [
    {"name": "search_policy_documents", "args": ["query", "k"]},
    {"name": "get_policy_section", "args": ["doc_id", "section"]},
    {"name": "lookup_employee_profile", "args": ["employee_id"]},
    {"name": "check_pto_balance", "args": ["employee_id"]},
    {"name": "create_mock_hr_ticket", "args": ["employee_id", "summary", "confirmation"]},
]


def mcp_list_tools() -> list[dict]:
    return [{"name": t["name"], "args": t["args"]} for t in TOOL_SCHEMAS]


def _ensure_index():
    from app import vector_store

    if vector_store.doc_count(DB_PATH) == 0:
        vector_store.build_index(POLICY_DIR, DB_PATH)


def _load_mock(name: str) -> list[dict]:
    with open(MOCK_DIR / name) as f:
        return json.load(f)


def mcp_call_tool(name: str, args: dict) -> dict:
    args = args or {}
    try:
        if name == "search_policy_documents":
            from app import vector_store

            _ensure_index()
            hits = vector_store.search(DB_PATH, args.get("query", ""),
                                       k=int(args.get("k", 4)))
            if not hits:
                return {"ok": False, "error": "no_evidence",
                        "hint": "No policy chunks matched; escalate."}
            return {"ok": True, "result": hits}

        if name == "get_policy_section":
            from app import vector_store

            _ensure_index()
            hits = vector_store.search(
                DB_PATH,
                f"{args.get('doc_id', '')} {args.get('section', '')}", k=10)
            for h in hits:
                if h["doc_id"] == args.get("doc_id") and args.get("section", "").lower() in h["section"].lower():
                    return {"ok": True, "result": h}
            return {"ok": False, "error": "section_not_found",
                    "hint": "Use search_policy_documents to find valid doc_id/section."}

        if name == "lookup_employee_profile":
            for e in _load_mock("employees.json"):
                if e["id"] == args.get("employee_id"):
                    return {"ok": True, "result": e}
            return {"ok": False, "error": "unknown_employee",
                    "hint": "Ask the user for a valid employee ID."}

        if name == "check_pto_balance":
            for b in _load_mock("pto_balances.json"):
                if b["employee_id"] == args.get("employee_id"):
                    return {"ok": True, "result": b}
            return {"ok": False, "error": "unknown_employee",
                    "hint": "Ask the user for a valid employee ID."}

        if name == "create_mock_hr_ticket":
            if not args.get("confirmation"):
                return {"ok": False, "error": "needs_confirmation",
                        "hint": "Ask user for explicit confirmation, then retry with confirmation token."}
            import hashlib as _hl

            seq = _hl.sha256(
                f"{args.get('employee_id')}|{args.get('summary')}".encode()
            ).hexdigest()[:6].upper()
            ticket = {"ticket_id": f"MOCK-{seq}",
                      "employee_id": args.get("employee_id"),
                      "summary": args.get("summary"), "status": "mock-created"}
            return {"ok": True, "result": ticket}

        return {"ok": False, "error": "unknown_tool",
                "hint": f"Available: {[t['name'] for t in TOOL_SCHEMAS]}"}
    except FileNotFoundError as e:
        return {"ok": False, "error": "backend_missing", "hint": str(e)}
    except Exception as e:  # transport must never throw
        return {"ok": False, "error": "tool_failed", "hint": str(e)}
