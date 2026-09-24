# Deployed

Fill in after first successful Render deploy. Required by spec submission item 2.

- App URL: _(TBD — set after push triggers Render hook)_
- Health URL: _(TBD)_`/health` — must return `{"app":"ok","mcp_tools":5,...}`
- Chat URL: _(TBD)_`/` (static chat) and `POST /chat`
- MCP URL (same service): _(TBD)_`/mcp`
- Render config: `render.yaml` present (single web service, free plan, uvicorn start). CI deploy gate fires on `main` after tests pass via `RENDER_DEPLOY_HOOK_URL` secret.

## Free-tier notes (expected)

- Cold start: service spins down after inactivity. First request rebuilds/loads the vector index and pays OpenRouter first-token latency. Record cold vs warm p50/p95 separately in evaluation.
- Ephemeral disk: SQLite index/checkpointer files may vanish on redeploy; app rebuilds index from `policy_docs/` at boot if missing. No action needed by grader.
- Env vars set on Render: `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `MCP_TRANSPORT=in-process`. Data paths default into the service disk (`policy_docs/`, `data/rag.db`, `data/threads.db`, `mock_data/`); override via `POLICY_DIR`, `RAG_DB`, `THREADS_DB`, `MOCK_DIR` only if needed.
- If the platform is down, document the outage here with date + screenshot; demo video must still show local run of both tasks.

## Measured boot profile (dev machine, hash-fallback provider)

- Index build from `policy_docs/` (20 docs, 277 chunks): 0.1s wall, 22MB peak RSS.
- Render free tier offers ~512MB: two orders of magnitude headroom. No torch, no PDF-loader stack in the boot path, so the OOM-crash-loop scenario does not apply; with MiniLM installed add ~90MB transient and re-measure here.
- Ephemeral-disk rebuild keeps this profile on every cold start; the committed-DB alternative was rejected (stale-index risk + provider-dependent vectors).
