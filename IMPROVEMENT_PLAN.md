# TaigaAI Improvement Plan

## Roadmap to an All-in-One AI Companion

---

## Phase 0: Security Foundation (Day-One Hardening)

### 0.1 Secret & Credential Redaction
- [ ] Structural regex matching first (before entropy fallback) — avoids false positives on base64 blobs
- [ ] Detect: AWS keys (`AKIA*`), GCP service accounts, GitHub tokens, JWTs, database connection strings, private keys (PEM headers)
- [ ] **Length-preserving masks** — replace characters with mask symbols matching original length
  - `AKIAIOSFODNN7EXAMPLE` → `[REDACTED_AWS_KEY_____________]` (18 chars → 18 chars)
  - Preserves column/row offsets for AST parsing, linter integration, and editor line mappings
- [ ] Redaction at pipeline entry point (before Ollama, before cache, before context-builder)
- [ ] Prevent credential leakage into: Ollama system logs, SQLite cache, session history
- [ ] High-entropy string detection as catch-all (applied only after structural rules pass)
- [ ] Configurable redaction patterns (`.taiga/config.json` `redact_patterns` key)
- [ ] `taiga config redact --test "string"` — dry-run redaction preview

### 0.2 SQLite Concurrency Strategy
- [ ] Enable WAL (Write-Ahead Logging) mode on all connections
- [ ] Set `synchronous=NORMAL` for balanced durability/speed
- [ ] Busy timeout (e.g., 5000ms) to handle concurrent reads during writes
- [ ] Single connection factory with thread-safe access for chat+cache+metrics

### 0.3 Context Auto-Truncation Algorithm
- [ ] Hybrid buffer strategy (not blind truncation, not summary-only):
  - **Always preserve:** System prompt + last 4 raw turns (exact strings, no compression)
  - **Structural summary:** Hardcoded project-environment block (tech stack, DB, ports, framework) — never model-generated, never compressed
  - **Compress intermediate turns only when** total token count exceeds 70% of configured budget
  - **Intermediate compression:** Use a cheap rule-based summary (extract decisions, constrains, key values), not model-generated summaries — avoids hallucination compounding over 5+ turns
- [ ] Token estimation via character ratio (~4 chars = 1 token, configurable per model)
- [ ] Configurable budget per model in `config.json`
- [ ] `taiga chat /budget` — show current token usage and window state

**Warning:** Never ask the model to summarize its own previous turns and feed that back as context. Minor semantic drift compounds exponentially over sessions, causing the model to forget initial constraints (e.g., "must use Python 3.9", "no external dependencies"). Rule-based compression is safer.

---

## Phase 1: Foundation (Low Effort, High Impact)

### 1.1 OpenAI-Compatible API Server (`taiga serve`)
- [ ] `taiga serve` — local HTTP server at `localhost:11435`
- [ ] `/v1/chat/completions` endpoint
- [ ] `/v1/models` endpoint — lists available Ollama models
- [ ] SSE streaming: translate Ollama NDJSON → OpenAI `data: {"choices":[{"delta":...}]}\n\n`
- [ ] `data: [DONE]` stream termination
- [ ] API key passthrough (optional `Authorization: Bearer` header, checked against config)

**Purpose:** Instantly make TaigaAI a security proxy that any OpenAI-compatible client (Continue.dev, Aider, Cursor, Cline, Cody) can target. TaigaAI sits as a firewall between the client and Ollama, enforcing path whitelisting, file size limits, and secret redaction on every request.

### 1.2 Persistent Chat & Multi-Turn Sessions
- [ ] `taiga chat` — interactive REPL with session history
- [ ] Session persistence via SQLite (with WAL mode)
- [ ] Context window management with sliding-window early-turn summaries
- [ ] `taiga --continue` — resume last session
- [ ] `/clear`, `/save`, `/load <session>` chat commands
- [ ] Tool-use interleaving: `/file foo.py`, `/diff`, `/explain` within chat

### 1.3 Project-Level Configuration
- [ ] `.taiga/config.json` — per-project overrides (model prefs, excluded paths, redact patterns, token budget)
- [ ] `.taigaignore` — glob patterns to exclude from context
- [ ] `.taigacontext` — explicit files/globs to always include
- [ ] `taiga init` — scaffold a project config

### 1.4 Smart Context Assembly (Phase 4.1, moved up)
- [ ] Auto-detect language/framework from project files
- [ ] Include relevant build/config files (Cargo.toml, package.json, pyproject.toml, etc.)
- [ ] Token budgeting — fit max relevant context within model limits (Qwen 9B: ~262K)
- [ ] File dependency ranking: include most-relevant imports first
- [ ] Git-aware: include recently changed files, diff context
- [ ] **Strategy:** Rely on Qwen's native 262K context window + AST dependency map, not vector embeddings, for small-to-medium codebases. Chunked embeddings introduce retrieval noise and lose structural code integrity.

### 1.5 Developer Tools
| Subcommand | Purpose |
|------------|---------|
| `taiga-explain` | Explain code paths, algorithms, architecture |
| `taiga-doc` | Generate/update documentation from code |
| `taiga-refactor` | Suggest refactors with before/after diffs |
| `taiga-test` | Generate unit tests for functions/files |
| `taiga-deps` | Analyze/visualize dependency graphs |

---

## Phase 2: Ecosystem Bridge (Medium Effort, Strategic)

### 2.1 MCP (Model Context Protocol) Integration
- [ ] **MCP Client**: Connect to external MCP servers for tool use
  - Filesystem server for safe, filtered file access
  - Database/PostgreSQL for querying schemas
  - Web search / Brave / Exa for fetching docs
- [ ] **MCP Server**: Expose TaigaAI as an MCP server
  - Ollama model queries with security sandbox
  - Caching layer
  - Output validation
- [ ] Tool-use loop: model requests tool → TaigaAI executes → feeds result back

### 2.2 Editor Integration
- [ ] VS Code extension — send selection to taiga (via local proxy), render response inline
- [ ] Vim/Neovim plugin
- [ ] Helix editor support
- [ ] `taiga --watch` — file watcher mode for live feedback
- [ ] **Leverage:** Since `taiga serve` exposes OpenAI API, many editors already work. Write thin shims, not full integrations.

---

## Phase 3: Intelligence Layer (Medium Effort)

### 3.1 Project Map & Dependency Graph
- [ ] Auto-build file dependency graph from imports
- [ ] Language-aware AST parsing (Python, TypeScript, Rust, Go)
- [ ] Include in context: project structure overview
- [ ] Visual output: `taiga-deps --visual` (Mermaid/DOT)
- [ ] **No vector DB**: Use the dependency graph to grab raw source files and feed them into Qwen's 262K context window. This preserves code structure integrity better than chunked embeddings for small-to-medium codebases.

### 3.2 Optional RAG for Large Codebases (Deferred)
- [ ] Only activate when project exceeds context window budget
- [ ] Local embeddings via Ollama (`nomic-embed-text`, `mxbai-embed-large`)
- [ ] Hybrid search: file path + content similarity
- [ ] `taiga @search "how is auth middleware implemented?"`

### 3.3 Multi-Model Router
- [ ] Query classification — detect intent (code, review, security, explain, chat)
- [ ] Auto-dispatch to best configured model
- [ ] Model chaining pipelines:
  - `taiga review-chained file.ts` → thinker summarize → coder review → security audit
- [ ] Parallel query: same prompt → multiple models → diff/merge outputs
- [ ] Response scoring: pick best answer (confidence, consensus)

---

## Phase 4: Developer Experience

### 4.1 Smart Context Assembly
- [ ] Auto-detect language/framework from project files
- [ ] Include relevant build/config files (Cargo.toml, package.json, etc.)
- [ ] Token budgeting — fit max relevant context within model limits
- [ ] File dependency ranking: include most-relevant imports first
- [ ] Git-aware: include recently changed files, diff context

### 4.2 Git Workflow Deepening
- [ ] `taiga-git review-pr` — review PR diff with inline comments
- [ ] `taiga-git changelog` — generate changelog from commits
- [ ] `taiga-git release` — draft release notes from changelog
- [ ] Git hook integration — auto-review on pre-commit, suggest message on commit-msg

### 4.3 Prompt Library & Templates
- [ ] Built-in prompt templates (code review, explain, refactor, etc.)
- [ ] User-defined custom templates stored in config
- [ ] Template variables: `{file}`, `{lang}`, `{selection}`
- [ ] `taiga --template onboarding` — full codebase onboarding report

---

## Phase 5: Observability & Polish

### 5.1 Metrics & Stats
- [ ] Token counting (approximate via character ratio or Ollama eval_count)
- [ ] Response latency tracking per model
- [ ] `taiga stats` — dashboard: queries, tokens, cache hits, model usage
- [ ] Cache analytics: hit rate, total queries saved

### 5.2 Cache Improvements
- [ ] TTL-based expiration (optional, not just LRU count)
- [ ] Cache warming: pre-cache common queries
- [ ] Configurable cache size limit
- [ ] Cache export/import for sharing across machines

### 5.3 Configuration UX
- [ ] JSON schema for config validation
- [ ] `taiga config` — get/set config values from CLI
- [ ] `taiga config validate` — check config for issues
- [ ] Profile switching: `taiga --profile work`, `--profile personal`

---

## Phase 6: Enhanced Security & Multi-User

### 6.1 Enhanced Security Sandbox
- [ ] Per-project path whitelists (not just global)
- [ ] Read-only chroot-style sandbox via Linux namespaces (optional)
- [ ] Audit log: every file accessed, every query made
- [ ] **Credential redaction already at Phase 0** — this phase extends to structural sandboxing

### 6.2 Multi-User / Shared Config
- [ ] System-wide config vs user config vs project config
- [ ] Config inheritance chain: project > user > system > default
- [ ] Shared model cache across users (optional)
- [ ] Role-based model access (admin sets which users can use which models)

---

## Summary Matrix

| Phase | Items | Effort | Impact |
|-------|-------|--------|--------|
| 0. Security Foundation | Secret redaction, SQLite WAL, context truncation | Low | Critical |
| 1. Foundation | `taiga serve`, chat REPL, project config, smart context, dev tools | Low-Medium | High |
| 2. Ecosystem Bridge | MCP client/server, editor shims | Medium | Strategic |
| 3. Intelligence | Project map, optional RAG, multi-model router | Medium | High |
| 4. Developer UX | Git deepening, prompt templates | Low-Medium | Medium |
| 5. Observability | Metrics, cache improvements, config UX | Low | Medium |
| 6. Advanced | Enhanced sandbox, multi-user | Medium-High | Medium |

---

## Refined Sprint Sequencing

| Sprint | Items | Justification |
|--------|-------|---------------|
| **Sprint 1: Core Engine** | `taiga chat` (REPL) + Secret Redaction + SQLite WAL + Context Truncation | Establish interactive loops while blocking credential leakage at pipeline entry. |
| **Sprint 2: The Proxy** | `taiga serve` (OpenAI API compatibility) | Gain instant compatibility with existing editor extensions without writing custom UI plugins. |
| **Sprint 3: Workspace UX** | Project config (`.taigaignore`) + Smart Context Assembly | Control exactly what hits the model's 262K context window based on native workspace bounds, leveraging Qwen's massive native context instead of vector search. |
| **Sprint 4: Ecosystem** | MCP integration + dev tools (explain, test, doc, deps) | Bridge to broader tool ecosystem and deliver high-demand developer utilities. |
| **Sprint 5: Intelligence** | Project map + multi-model router + optional RAG | Semantic understanding of codebase structure for advanced queries. |
| **Sprint 6: Polish** | Git deepening, prompt templates, metrics, editor plugins | Round out the experience and provide observability. |

---

## Ollama-to-OpenAI SSE Stream Translation

### Mapping Reference

```
Ollama (raw NDJSON)                  OpenAI (SSE)
─────────────────────               ─────────────
{"response":"def"}                   data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"def"}}]}

{"response":" hello("}               data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":" hello("}]}

{"response":".","done":true,...}     data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"."}]}
                                     data: [DONE]
```

### Key Translation Points

1. **Stream framing:** Ollama sends bare NDJSON lines. OpenAI wraps with `data: ` prefix, `\n\n` termination, and prepends `\n\n` before first chunk.
2. **Event type:** `response` field → `delta.content`. No `role` in delta for streaming (role only in non-streaming).
3. **Termination:** Ollama sends `{"done":true}` after final content chunk. Extract `total_duration`, `eval_count`, `prompt_eval_count` for usage stats.

### Critical Edge Case: Final Token Drop

Ollama's `done: true` chunk occasionally carries the **last token** (e.g., trailing punctuation) *alongside* the termination flag. Checking `done` before yielding `response` drops the final character.

**Correct order:**
```python
data = json.loads(line)
content = data.get("response", "")
if content:
    yield sse_chunk(content)      # Yield content FIRST
if data.get("done"):
    yield "data: [DONE]\n\n"      # Then terminate
    break
```

### Latency-Optimized Async Streaming

Per-chunk `json.loads()` + `json.dumps()` in a synchronous loop introduces micro-stuttering under GPU-native token rates. Use async iteration with an f-string envelope to bypass `json.dumps` overhead on static structure:

```python
import time, json

async def ollama_to_openai_sse_stream(async_lines, model: str, request_id: str):
    async for line in async_lines:
        if not line.strip():
            continue
        data = json.loads(line)

        content = data.get("response", "")

        # Yield content BEFORE checking done (final-token edge case)
        if content:
            timestamp = int(time.time())
            escaped = json.dumps(content)
            yield (
                f'data: {{"id":"{request_id}","object":"chat.completion.chunk",'
                f'"created":{timestamp},"model":"{model}",'
                f'"choices":[{{"index":0,"delta":{{"content":{escaped}}}}}]}}\n\n'
            )

        if data.get("done"):
            # Optionally yield usage stats chunk before DONE
            yield "data: [DONE]\n\n"
            break
```

**Why f-strings:** The outer envelope (id, object, model, choices array structure) is static JSON. Only `content` changes per chunk. Using `json.dumps()` only on the content string and wrapping it in an f-string envelope saves ~40% CPU on the serialization path versus a full `json.dumps(chunk_dict)` per token.

### Chunk ID & Model

- Generate UUID per request: `f"chatcmpl-{uuid.uuid4().hex}"`
- Pass through Ollama model tag as `model` in response
- Non-streaming endpoint maps to the same format, just single chunk with `finish_reason: "stop"`

### Tool Call Chasm

Ollama's native tool calling uses a different event schema (`tool_calls` delta). When MCP/tool-use is added later (Phase 2.1), the translator needs a second path:
```python
if data.get("tool_calls"):
    delta = {"tool_calls": [{"index": 0, "function": {"arguments": data["tool_calls"]}}]}
```
This is deferred until tool-use is implemented.


