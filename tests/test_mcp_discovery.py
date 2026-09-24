"""CI gate test (rubric 8): agent must discover + call MCP-exposed tools.

This test must hit the MCP layer (list_tools / call_tool), never direct imports
of tool functions. Fails until mcp/server.py exposes exactly the 5 tools.
"""
from mcp.server import mcp_list_tools, mcp_call_tool

REQUIRED_TOOLS = {
    "search_policy_documents",
    "get_policy_section",
    "lookup_employee_profile",
    "check_pto_balance",
    "create_mock_hr_ticket",
}


def test_list_tools_has_5():
    tools = mcp_list_tools()
    names = {t["name"] for t in tools}
    assert REQUIRED_TOOLS <= names, f"missing tools: {REQUIRED_TOOLS - names}"


def test_call_lookup_employee_via_mcp():
    out = mcp_call_tool("lookup_employee_profile", {"employee_id": "E001"})
    assert out["ok"] is True
    assert out["result"]["id"] == "E001"


def test_write_requires_confirmation():
    out = mcp_call_tool(
        "create_mock_hr_ticket",
        {"employee_id": "E002", "summary": "PTO request"},
    )
    assert out["ok"] is False
    assert out["error"] == "needs_confirmation"
