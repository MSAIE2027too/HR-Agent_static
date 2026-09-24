"""LLM clients. OpenRouter free path at runtime; scripted fakes in tests/eval."""
from __future__ import annotations

import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
load_dotenv()

PLANNER_SYSTEM = """You are an HR policy agent. You must reply with strictly ONE raw JSON object and nothing else.
Format:
Either {"tool": "<tool_name>", "args": {<arguments>}}
or {"final": true}

Allowed tools: search_policy_documents, get_policy_section, lookup_employee_profile, check_pto_balance, create_mock_hr_ticket (args: employee_id, summary, confirmation).

Rules:
1. Always search company policies using search_policy_documents to verify approval rules, notice periods, and policy limits before finalizing. All answers require cited policy documents.
2. When EVIDENCE so far contains sufficient policy snippets or answers to address the query, output {"final": true} immediately. Do not perform repetitive searches.
3. For stateful actions: Only call create_mock_hr_ticket after checking policy and balances. When the user explicitly confirms creation, pass confirmation="user_confirmed" along with employee_id and summary.
4. Start your response with { and end with }. Never output markdown or conversational filler."""


def clean_llm_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    if "<|tool_call_start|>" in raw or "<tool_call>" in raw:
        import re
        m = re.search(r"([a-zA-Z0-9_]+)\((.*?)\)", raw)
        if m:
            tool_name = m.group(1)
            arg_str = m.group(2)
            args = {}
            for k, v in re.findall(r"([a-zA-Z0-9_]+)=['\"]([^'\"]*)['\"]", arg_str):
                args[k] = v
            return json.dumps({"tool": tool_name, "args": args})

    if not raw.startswith("{") and "{" in raw:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw = raw[start:end + 1]

    return raw.strip()


class OpenRouterClient:
    def __init__(self, model: str | None = None, temperature: float = 0.0):
        self.model = model or os.environ.get("OPENROUTER_MODEL",
                                             "openrouter/free")
        self.temperature = temperature
        self.key = os.environ.get("OPENROUTER_API_KEY", "")

    def complete(self, messages: list[dict]) -> str:
        import httpx

        if not self.key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        r = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.key}"},
            json={"model": self.model, "temperature": self.temperature,
                  "messages": messages},
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
        r.raise_for_status()
        return clean_llm_json(r.json()["choices"][0]["message"]["content"])


class FakeLLM:
    """Scripted planner for tests: maps turn index to canned JSON replies."""

    def __init__(self, script: list[str]):
        self._script = script
        self.calls = 0

    def complete(self, messages: list[dict]) -> str:
        out = self._script[min(self.calls, len(self._script) - 1)]
        self.calls += 1
        return out


def tool_call_json(name: str, args: dict) -> str:
    return json.dumps({"tool": name, "args": args})


FINAL_JSON = json.dumps({"final": True})
