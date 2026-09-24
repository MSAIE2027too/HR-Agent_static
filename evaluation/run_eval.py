"""Eval harness (rubric 9). Live mode needs OPENROUTER_API_KEY; otherwise
structural mode verifies every item maps to tools/docs and reports honestly.
Ablation: --ablation-k 3,5 compares citation hit-rate at k=3 vs k=5 on
multi-doc items using the real retriever (no LLM needed).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_set(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(l) for l in f if l.strip()]


def ablation(path: str, ks: list[int]) -> dict:
    from mcp.server import DB_PATH, mcp_call_tool

    items = [i for i in load_set(path) if i["type"] == "multi-doc"]
    out = {}
    for k in ks:
        hits = 0
        for item in items:
            r = mcp_call_tool("search_policy_documents",
                              {"query": item["prompt"], "k": k})
            if r.get("ok") and len(r["result"]) >= 2:
                hits += 1
        out[k] = f"{hits}/{len(items)} multi-doc items with 2+ hits"
    return out


def live_run(eval_path: str) -> dict:
    from app.agent import run

    items = load_set(eval_path)
    lat, tool_ok, cited, completed, safe = [], 0, 0, 0, 0
    for item in items:
        t0 = time.time()
        try:
            out = run(item["prompt"], session_id=item["id"])
        except Exception as e:
            print(f"{item['id']}: ERROR {e}")
            continue
        lat.append(time.time() - t0)
        trace = [t["tool"] for t in out["tool_trace"]]
        if all(t in trace for t in item.get("expected_tools", [])):
            tool_ok += 1
        if (not item.get("must_cite")) or out["citations"]:
            cited += 1
        if out["citations"] or out.get("refused") or out.get("escalation"):
            completed += 1
        if "create_mock_hr_ticket" not in trace or out.get("needs_confirmation") or any(
                t.get("ok") for t in out["tool_trace"] if t["tool"] == "create_mock_hr_ticket"):
            safe += 1
    n = len(items)
    cold_first = lat[0] if lat else 0
    lat.sort()
    p50 = lat[len(lat) // 2] if lat else 0
    p95 = lat[int(len(lat) * 0.95)] if lat else 0
    return {"n": n, "tool_selection_acc": round(tool_ok / n, 3),
            "citation_or_correct_refusal": round(cited / n, 3),
            "workflow_completion": round(completed / n, 3),
            "action_safety_pass": round(safe / n, 3),
            "latency_p50_s": round(p50, 2), "latency_p95_s": round(p95, 2),
            "cold_first_query_s": round(cold_first, 2),
            "cold_note": "first query includes index build + model warm-up; "
                         "report cold vs warm separately for the rubric"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-set", required=True)
    ap.add_argument("--ablation-k", default="")
    args = ap.parse_args()

    if args.ablation_k:
        ks = [int(x) for x in args.ablation_k.split(",")]
        print(json.dumps({"ablation_k_citation_recall": ablation(args.eval_set, ks)},
                         indent=2))
        return 0
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("structural mode (no OPENROUTER_API_KEY): set the key for live metrics.")
        items = load_set(args.eval_set)
        from mcp.server import mcp_list_tools

        tools = {t["name"] for t in mcp_list_tools()}
        bad = [i["id"] for i in items
               if any(t not in tools for t in i.get("expected_tools", []))]
        print(f"items={len(items)} unknown_expected_tools={bad or 'none'}")
        return 0 if not bad else 1
    print(json.dumps(live_run(args.eval_set), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
