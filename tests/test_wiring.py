"""Wiring tests: ingest metadata, retrieval citations, /health, demo traces.

Uses FakeLLM (no network, no key) plus the real RAG + mock backends.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import ingest, vector_store  # noqa: E402
from app.agent import run  # noqa: E402
from app.llm import FINAL_JSON, FakeLLM, tool_call_json  # noqa: E402
from mcp.server import DB_PATH, POLICY_DIR  # noqa: E402

os.environ.setdefault("RAG_DB", str(DB_PATH))


def _ensure_index(tmp_path=None):
    db = str(tmp_path / "t.db") if tmp_path else str(DB_PATH)
    if vector_store.doc_count(db) == 0:
        vector_store.build_index(POLICY_DIR, db)
    return db


def test_ingest_keeps_citation_metadata():
    chunks = ingest.ingest_dir(POLICY_DIR)
    assert len(chunks) >= 6
    for c in chunks:
        assert c.doc_id and c.title and c.section and c.snippet_hash


def test_retrieval_returns_doc_section_citations(tmp_path):
    import mcp.server as srv

    db = _ensure_index(tmp_path)
    old = srv.DB_PATH
    srv.DB_PATH = db
    try:
        out = srv.mcp_call_tool("search_policy_documents",
                                {"query": "remote work six weeks", "k": 3})
    finally:
        srv.DB_PATH = old
    assert out["ok"] is True
    assert all(h["doc_id"] and h["section"] for h in out["result"])


def test_health_reports_real_tool_count():
    from fastapi.testclient import TestClient

    from app.main import app

    r = TestClient(app).get("/health")
    assert r.status_code == 200
    assert r.json()["mcp_tools"] == 5


def test_chat_returns_spec_wire_contract():
    """Spec 6: /chat returns answer, citations, snippets, tool-call trace."""
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from app.main import app

    canned = {"answer": "x", "citations": [], "snippets": [], "tool_trace": [],
              "escalation": None, "needs_confirmation": False}
    with patch("app.agent.run", return_value=canned):
        r = TestClient(app).post("/chat", json={"message": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert {"answer", "citations", "snippets", "tool_trace"} <= set(body)


def test_demo_task_a_trace_order():
    llm = FakeLLM([
        tool_call_json("lookup_employee_profile", {"employee_id": "E001"}),
        tool_call_json("search_policy_documents",
                       {"query": "remote work security tax", "k": 4}),
        tool_call_json("get_policy_section",
                       {"doc_id": "remote-work", "section": "Approval"}),
        FINAL_JSON,
    ])
    out = run("Can I work remotely for six weeks? ID E001", llm=llm)
    trace = [t["tool"] for t in out["tool_trace"]]
    assert trace[0] == "lookup_employee_profile"
    assert "search_policy_documents" in trace
    assert out["citations"], "demo answer must carry citations"
    for cite in out["citations"]:
        assert cite in out["answer"], f"citation {cite} must appear in answer"
    assert out["snippets"], "demo answer must carry source snippets"
    for s in out["snippets"]:
        assert s["doc_id"] and s["section"] and s["snippet"]
    assert "SYNTHETIC" not in out["answer"], "profile rows must not pose as citations"


def test_demo_task_b_ticket_gated():
    llm = FakeLLM([
        tool_call_json("check_pto_balance", {"employee_id": "E002"}),
        tool_call_json("search_policy_documents", {"query": "PTO approval", "k": 4}),
        tool_call_json("create_mock_hr_ticket",
                       {"employee_id": "E002", "summary": "3 days PTO"}),
        FINAL_JSON,
    ])
    out = run("Can I take 3 days PTO? ID E002", llm=llm)
    assert out["needs_confirmation"] is True
    assert not any(t["tool"] == "create_mock_hr_ticket" and t["ok"]
                   for t in out["tool_trace"])


def test_model_error_stays_out_of_user_answer():
    class _Boom:
        def complete(self, messages):
            raise RuntimeError("OPENROUTER_API_KEY is not set")

    out = run("How many PTO days?", llm=_Boom())
    assert "OPENROUTER_API_KEY" not in out["answer"]
    assert out["escalation"] and "planner_parse_failed" in out["escalation"]


def test_mcp_http_bridge_lists_and_calls():
    from fastapi.testclient import TestClient

    from app.main import app

    c = TestClient(app)
    r = c.post("/mcp", json={"action": "list_tools"})
    assert r.status_code == 200
    assert {t["name"] for t in r.json()["tools"]} >= {
        "search_policy_documents", "get_policy_section",
        "lookup_employee_profile", "check_pto_balance",
        "create_mock_hr_ticket"}
    r = c.post("/mcp", json={"action": "call_tool", "tool": "lookup_employee_profile",
                              "args": {"employee_id": "E001"}})
    assert r.json()["ok"] is True
    r = c.post("/mcp", json={"action": "bogus"})
    assert r.status_code == 400


def test_follow_up_reuses_thread_evidence():
    llm1 = FakeLLM([
        tool_call_json("search_policy_documents", {"query": "PTO days", "k": 2}),
        FINAL_JSON,
    ])
    out1 = run("How many PTO days?", session_id="followup", llm=llm1)
    assert out1["citations"]
    llm2 = FakeLLM([FINAL_JSON])
    out2 = run("And who approves it?", session_id="followup", llm=llm2)
    assert llm2.calls == 1
    assert out2["citations"] == out1["citations"]
