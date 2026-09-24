# AI Tooling & Methodology Disclosure

This document discloses how generative AI and agentic engineering tools were utilized throughout the development, verification, and evaluation of the **Autonomous Enterprise HR Policy & Workflow Agent**, in strict accordance with **Quantic MSAIE Capstone Submission Mandate Item 2**.

---

## 1. AI Engineering Tools & Runtime Models

| Tool / Model | Context of Use | Role & Integration Surface |
|---|---|---|
| **Google Antigravity & OpenCode** | Local Agentic Pair Programming | Architecture review, test-driven development (TDD) harness construction, heuristic UI refactoring, and documentation drafting. |
| **OpenRouter (`openrouter/free`)** | Runtime Reasoning Engine | Powers live agentic planning, policy query reformulation, and MCP tool selection at inference time. |
| **`all-MiniLM-L6-v2`** | Local Semantic Embeddings | Zero-cost, 384-dimensional dense vector embeddings executing locally via CPU (Hugging Face / sentence-transformers). |
| **LangGraph (StateGraph)** | Orchestration Framework | Deterministic state machine managing nodes (`filter_input`, `planner`, `finalize`), conditional edges, and SQLite thread persistence. |
| **Model Context Protocol (MCP)** | Tool Interoperability Standard | In-process and HTTP streamable protocol defining and exposing all 5 domain tools. |

---

## 2. What Worked Well

1. **Test-Driven Scaffolding & Contract Definition**:
   - Automated generation of exhaustive test matrices (`pytest`) covering unit safety filters, MCP tool discovery, and LangGraph multi-turn state transitions before wiring backend execution.
   - Rapid generation of JSON Schema definitions matching the Model Context Protocol specification for the 5 HR tools (`search_policy_documents`, `get_policy_section`, `lookup_employee_profile`, `check_pto_balance`, `create_mock_hr_ticket`).
2. **Architectural Trade-Off Analysis**:
   - Evaluating latency and failure surfaces between multi-tier architectures (Streamlit + FastAPI) versus single-tier monolithic designs (FastAPI + static HTML).
   - Profiling deterministic functional guardrails vs. LLM-node guardrails: collapsing security filters into compiled regex functions saved ~2.5s per turn and eliminated token consumption for malicious/out-of-scope queries.
3. **Dual-Persona UI/UX Refactoring**:
   - Implementing Nielsen Norman usability heuristics (Heuristic #8: Aesthetic & Minimalist Design, Heuristic #5: Error Prevention) by segregating developer telemetry into an Evaluator Inspector Drawer while keeping the employee-facing concierge interface pristine.

---

## 3. What Did Not Work & Human Engineering Corrections

1. **Model Output Syntax Quirks on Open Source Weights**:
   - *Issue*: Open models on OpenRouter (e.g. Gemma, Qwen, Llama variants) intermittently wrap JSON in markdown fences (` ```json `) or emit custom model tokens (such as `<|tool_call_start|>[tool_name(args)]<|tool_call_end|>`).
   - *Correction*: Engineered a custom sanitization pipeline (`clean_llm_json()` in `app/llm.py`) using regular expressions to normalize non-standard tool tokens into compliant JSON before passing them to the JSON parser.
2. **Redundant Planning Loops & Latency Bloat**:
   - *Issue*: LLM planners tended to repeat vector searches when policy evidence was already present in state, causing delays that threatened the capstone's latency goals.
   - *Correction*: Refined `PLANNER_SYSTEM` rules to mandate immediate `{"final": true}` emissions once sufficient evidence is gathered, and placed the `MAX_LOOPS` cap check at the top of the planning node to prevent redundant model roundtrips.
3. **HTTP Client Timeout Under Cloud Queuing**:
   - *Issue*: Default 30-second read timeouts triggered premature exceptions during peak free-tier OpenRouter queuing.
   - *Correction*: Increased HTTP read timeout to 60.0s with explicit `httpx.Timeout(60.0, connect=10.0)` configuration, paired with a deterministic one-turn self-correction loop.

---

## 4. Academic Integrity & Responsibility Statement

* **Human Oversight**: Every line of code, prompt instruction, and configuration was reviewed, executed, and verified against unit tests (`pytest`) and live integration benchmarks.
* **Deterministic Verification**: No generative AI claims are accepted without empirical validation. 100% of unit, wiring, and discovery tests pass deterministically on local infrastructure.
* **Zero PII & Data Privacy**: No proprietary, private, or real employee data was transmitted to external AI endpoints. The policy corpus and employee records are completely synthetic (`mock_data/`).

---

## 5. Heterogeneous Retrieval & Processing Pipeline

The ingestion and retrieval pipeline implements a multi-format document parser supporting **Markdown (.md), Plain Text (.txt), HTML (.html), and PDF (.pdf)** via `app/ingest.py`. 
* **Ingest Flow**: Source File Loader -> Strip/Clean -> Heading-Aware Chunker (~800 characters / 150 overlap) -> `all-MiniLM-L6-v2` Local Embedder -> SQLite Vector Store.
* **Retrieval Flow**: Natural Language Query -> Cosine Similarity Scan (Top-k=4) -> Injected Evidence Chunks with Document ID & Section Headings (`[doc_id:section]`) -> Final Grounded Response.
