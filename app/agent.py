"""Agent orchestrator. LangGraph: filter -> planner -> execute -> finalize.

Loop cap 3, then escalate. Trace is operational only (tool, args, output
summary, sources). Single LLM call site so tests inject FakeLLM.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from .llm import PLANNER_SYSTEM
from .safety import check_answer, filter_input

MAX_LOOPS = 3


class AgentState(TypedDict, total=False):
    question: str
    session_id: str
    decision: str
    evidence: list[dict]
    tool_trace: list[dict]
    loops: int
    done: bool
    escalate: str
    refused: bool
    needs_confirmation: bool
    answer: str
    citations: list[str]
    snippets: list[dict]


def _node_filter(state: AgentState) -> AgentState:
    verdict = filter_input(state["question"])
    state["decision"] = verdict["decision"]
    if verdict["decision"] != "pass":
        state["refused"] = True
        state["escalate"] = verdict.get("reason", verdict["decision"])
    return state


def _make_planner(llm):
    def _node_planner(state: AgentState) -> AgentState:
        from mcp.server import mcp_call_tool

        if state.get("loops", 0) >= MAX_LOOPS:
            print("[Agent Orchestrator] Loop cap reached. Proceeding to finalize.")
            state["done"] = True
            return state

        trace = state.get("tool_trace", [])
        evidence = state.get("evidence", [])
        redacted = filter_input(state["question"]).get("redacted", state["question"])
        messages = [{"role": "system", "content": PLANNER_SYSTEM},
                    {"role": "user", "content": redacted}]
        if evidence:
            messages.append({"role": "user", "content":
                             f"EVIDENCE so far: {json.dumps(evidence)}"})
        raw = ""
        try:
            raw = llm.complete(messages)
            reply = json.loads(raw)
        except Exception as e:
            fix_turn = ([{"role": "assistant", "content": raw},
                         {"role": "user", "content":
                          f"That was not valid JSON ({e}). Reply with exactly "
                          f"one corrected JSON object and nothing else."}]
                        if raw else
                        [{"role": "user", "content":
                          f"Planner call failed ({e}). Reply with exactly one "
                          f"JSON object and nothing else."}])
            try:
                reply = json.loads(llm.complete(messages + fix_turn))
            except Exception as e2:
                state["escalate"] = f"planner_parse_failed: {e2}"
                return state
        if reply.get("final"):
            print("[Agent Orchestrator] LLM emitted final: true. Proceeding to finalize.")
            state["done"] = True
            return state
        if state.get("loops", 0) >= MAX_LOOPS:
            print("[Agent Orchestrator] Loop cap reached. Escalating.")
            state["escalate"] = "max_loops_reached"
            return state
        tool_name = reply.get("tool", "")
        tool_args = reply.get("args", {})
        print(f"[Agent Orchestrator] Dispatching MCP tool: '{tool_name}' with args {tool_args}")
        out = mcp_call_tool(tool_name, tool_args)
        trace.append({"tool": tool_name, "args": tool_args,
                      "ok": out.get("ok"), "error": out.get("error")})
        state["tool_trace"] = trace
        if out.get("ok"):
            res = out["result"]
            evidence.extend(res if isinstance(res, list) else [res])
            state["evidence"] = evidence
        elif out.get("error") == "needs_confirmation":
            print("[Agent Orchestrator] State-changing action requires confirmation. Pausing execution.")
            state["needs_confirmation"] = True
            return state
        else:
            state["escalate"] = out.get("error", "tool_failed")
            return state
        state["loops"] = state.get("loops", 0) + 1
        return state

    return _node_planner


def _node_finalize(state: AgentState) -> AgentState:
    if state.get("refused"):
        state["answer"] = ("Out of scope for HR policy help. "
                           f"Reason: {state.get('escalate')}.")
        state["citations"] = []
        state["snippets"] = []
        return state
    cites = [f"[{e.get('doc_id')}:{e.get('section')}]"
             for e in state.get("evidence", []) if e.get("doc_id")]
    state["citations"] = cites
    state["snippets"] = [{"doc_id": e["doc_id"], "section": e["section"],
                          "snippet": e["snippet"]}
                         for e in state.get("evidence", []) if e.get("doc_id")]
    state["citation_check"] = check_answer("answer", cites,
                                           claims=["answer"] if cites else [])
    if state.get("escalate") and not cites:
        if state["escalate"].startswith("planner_parse_failed"):
            state["answer"] = ("The assistant hit a model error and stopped "
                               "instead of guessing. Escalated.")
        else:
            state["answer"] = ("Insufficient policy evidence. Escalated "
                               f"({state['escalate']}).")
    elif not cites:
        state["answer"] = "Insufficient policy evidence. Escalated."
        state["escalate"] = "no_evidence"
    else:
        cited_items = [e for e in state["evidence"] if e.get("doc_id")]
        lines = [f"- {e.get('snippet', '')[:200]} {c}"
                 for e, c in zip(cited_items, cites)]
        state["answer"] = "Grounded answer:\n" + "\n".join(lines)
    leak = check_answer(state.get("answer", ""), cites,
                        claims=["answer"] if cites else [])
    state["citation_check"] = leak
    if leak.get("pii_leak"):
        state["answer"] = "Insufficient policy evidence. Escalated (pii_leak)."
        state["escalate"] = "pii_leak"
        state["citations"] = []
        state["snippets"] = []
    return state


def build_graph(llm, checkpointer=None):
    g = StateGraph(AgentState)
    g.add_node("filter", _node_filter)
    g.add_node("planner", _make_planner(llm))
    g.add_node("finalize", _node_finalize)
    g.set_entry_point("filter")
    g.add_conditional_edges(
        "filter", lambda s: "finalize" if s.get("refused") else "planner",
        {"finalize": "finalize", "planner": "planner"})
    g.add_conditional_edges(
        "planner",
        lambda s: "finalize" if (s.get("done") or s.get("escalate")
                                 or s.get("needs_confirmation")) else "planner",
        {"finalize": "finalize", "planner": "planner"})
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)


def _threads_db() -> str:
    default = Path(__file__).resolve().parent.parent / "data" / "threads.db"
    return os.environ.get("THREADS_DB", str(default))


def run(question: str, session_id: str = "local", llm=None) -> dict[str, Any]:
    from langgraph.checkpoint.sqlite import SqliteSaver

    from .llm import OpenRouterClient

    llm = llm or OpenRouterClient()
    db = _threads_db()
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    with SqliteSaver.from_conn_string(db) as cp:
        # Control flags reset per question; evidence/tool_trace persist in the
        # thread so follow-ups reuse prior retrieval without re-calling tools.
        out = build_graph(llm, checkpointer=cp).invoke(
            {"question": question, "session_id": session_id,
             "loops": 0, "done": False, "refused": False,
             "escalate": None, "needs_confirmation": False},
            config={"configurable": {"thread_id": session_id}})
    return {"answer": out.get("answer", ""), "citations": out.get("citations", []),
            "snippets": out.get("snippets", []),
            "tool_trace": out.get("tool_trace", []),
            "escalation": out.get("escalate"),
            "needs_confirmation": out.get("needs_confirmation", False),
            "refused": out.get("refused", False)}
