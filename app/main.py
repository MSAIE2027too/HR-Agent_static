"""Single-service FastAPI: static chat UI + /chat + /health (+ /mcp mount point)."""
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import vector_store
from mcp.server import DB_PATH, POLICY_DIR, mcp_list_tools

app = FastAPI(title="HR Policy Agentic AI")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    if vector_store.doc_count(DB_PATH) == 0:
        vector_store.build_index(POLICY_DIR, DB_PATH)
    yield


app.router.lifespan_context = _lifespan


@app.get("/health")
def health() -> dict:
    tools = mcp_list_tools()
    return {"app": "ok", "mcp_tools": len(tools),
            "policy_docs": vector_store.doc_count(DB_PATH)}


@app.post("/mcp")
def mcp_bridge(body: dict) -> dict:
    from fastapi import HTTPException

    from mcp.server import mcp_call_tool, mcp_list_tools

    if body.get("action") == "list_tools":
        return {"tools": mcp_list_tools()}
    if body.get("action") == "call_tool":
        return mcp_call_tool(body.get("tool", ""), body.get("args", {}))
    raise HTTPException(status_code=400,
                        detail="action must be list_tools or call_tool")


@app.post("/chat")
def chat(body: dict) -> dict:
    from fastapi import HTTPException

    from .agent import run

    message = (body.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    import uuid as _uuid

    sid = (body.get("session_id") or "").strip() or f"anon-{_uuid.uuid4().hex[:8]}"
    out = run(message, session_id=sid)
    return {"answer": out["answer"], "citations": out["citations"],
            "snippets": out["snippets"],
            "tool_trace": out["tool_trace"], "escalation": out["escalation"],
            "needs_confirmation": out.get("needs_confirmation", False)}


_STATIC = Path(__file__).resolve().parent / "static"
if _STATIC.exists():
    app.mount("/", StaticFiles(directory=_STATIC, html=True), name="static")
