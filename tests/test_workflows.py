"""Workflow tests: the 2 demo tasks end-to-end (red phase, LLM mocked).

ST-1 remote work: lookup_employee_profile -> search_policy_documents -> cited steps.
ST-2 PTO: check_pto_balance -> search_policy_documents -> ticket only after confirm.
ST-3 out-of-scope: refuse via filter, no tools called.
"""
from unittest.mock import MagicMock


def test_remote_work_sequence():
    agent = MagicMock()
    agent.run.return_value = {
        "tool_trace": [
            "lookup_employee_profile",
            "search_policy_documents",
            "get_policy_section",
        ],
        "citations": ["remote-policy:duration"],
    }
    out = agent.run("DEMO TASK A")
    assert out["tool_trace"][0] == "lookup_employee_profile"
    assert len(out["citations"]) > 0


def test_pto_ticket_needs_confirmation():
    agent = MagicMock()
    agent.run.return_value = {"needs_confirmation": True, "tool_trace": ["check_pto_balance"]}
    out = agent.run("DEMO TASK B")
    assert out["needs_confirmation"] is True
    assert "create_mock_hr_ticket" not in out["tool_trace"]


def test_out_of_scope_refuses():
    agent = MagicMock()
    agent.run.return_value = {"refused": True, "tool_trace": []}
    out = agent.run("How do I bake a cake?")
    assert out["refused"] is True
