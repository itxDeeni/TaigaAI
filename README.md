# TaigaAI Workstation Engine

Welcome to the **TaigaAI Workstation Engine**. TaigaAI is a zero-autonomy, read-only developer copilot designed to work natively with your local Ollama models on **Linux, macOS, and Windows**.

By prioritizing native Python execution, **canonical path sandboxing**, **secret redaction**, and strict structured prompt contracts, the system guarantees high-value coding assistance, interactive chat, git workflows, and security auditing without exposing your filesystem or shell.

---

## 💻 Multiplatform Installation

### 🍎 Linux & macOS Setup
1. Clone the repository to your chosen directory.
2. Run the dynamic shell installer:
   ```bash
   ./install.sh
   ```
   *This automatically registers safe, dynamic symbolic links inside `~/.local/bin/` so all tools are accessible globally in your shell.*

### 🔌 Windows Setup
1. Clone the repository to your chosen directory.
2. Open PowerShell as a standard user and execute the setup script:
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process
   .\install.ps1
   ```
   *This self-diagnoses Windows Python & Git pathways and permanently adds the workstation's batch wrappers directly to your User Environment Path so you can type any `taiga-*` command inside any PowerShell or Command Prompt terminal instantly.*

---

## 🔒 Safety and Sandbox Security Model

1. **Canonical Path Resolution**: Every input file argument is verified using Python's `Path(file_path).resolve()`. This resolves symlinks, relative traversal operators (`../../`), and double-dots to their target absolute directories.
2. **Directory Whitelist**: Files can only be read if their resolved path lies inside the configured whitelist (e.g. `~/Documents/Code`, `~/projects`, `~/dev`). Supports `~` home directory shortcuts for absolute portability across different user accounts.
3. **Memory DoS Boundaries**: Imposes an explicit **5MB size threshold** on all read operations, preventing memory exhaustion attacks from massive log files or data dumps.
4. **Secret & Credential Redaction**: 19 regex-based patterns (AWS keys, GitHub tokens, JWT, PEM keys, database URLs, etc.) are detected and **length-preserving masked** at pipeline entry — before cache, before Ollama — so credentials never leak into system logs or SQLite. Masks preserve original string length to avoid breaking AST offsets.
5. **Prompt Injection Escaping**: Escapes nested standard XML container tags and CDATA closures within ingested code, git diffs, and piped inputs to block prompt injection or prompt layout escaping.
6. **Auto-Eviction Query Cache**: SQLite cache is dynamically capped to the **200 most recent queries** via transaction `rowid` ordering, ensuring the local cache database never consumes excessive disk space.
7. **Interactive Model Puller**: Intercepts Ollama 404 model-not-found errors and offers interactive, stream-download progress bars directly in the terminal, completely avoiding silent network queries or headless downloads.
8. **Dynamic Config Discovery**: Looks for configuration defaults in local workspaces, standard Linux/macOS paths (`~/.config/taiga-ai/config.json`), or Windows APPDATA, keeping settings intact across workspace moves.
9. **Command Execution Isolation**: AI outputs are strictly treated as text. There is zero `eval` or automated command execution. Suggested shell commands must be inspected and executed manually by you.
10. **No Auto-Commit Policy**: The Git assistant analyzes changes and generates commit messages, but never commits or pushes to remote repositories automatically.

*For an extensive architecture map, security posture analysis, and details on active security controls, check out the dedicated [SECURITY.md](SECURITY.md) policy guide.*

---

## 🚀 Daily Coding & Development Workflows

### 1. General Queries and Context Piping (`taiga`)
The core `taiga` CLI router switches between models seamlessly:
- **Coder Mode** (`-c`, `--coder`): Maps to your preferred coding model for synthesis.
- **Thinker Mode** (`-t`, `--thinker`): Maps to your preferred general-purpose reasoning model for explanation.

*(Note: Models map dynamically based on your workspace `config.json` configuration.)*

**Examples:**
```bash
# Direct inline instruction
taiga -c -p "Write an idempotent python retry decorator"

# Piping files as context (automatically sandboxed)
taiga -c -p "Refactor these database queries to use transaction blocks" db.py

# Piping stdout from another command
cat schema.sql | taiga -c -p "Convert this PostgreSQL schema into a clean Go struct"
```

---

### 2. Git Assistant (`taiga-git`)
`taiga-git` analyzes changes in your repository and prints conventional commits or Pull Request documentation.

**Examples:**
```bash
# Stage your changes
git add -A

# Generate a compliant Conventional Commit message (feat/fix/chore)
taiga-git commit

# Instantly commit using the AI generated message
git commit -m "$(taiga-git)"

# Generate a complete Pull Request summary of branch changes against 'main'
taiga-git summarize
```

---

### 3. Automated Code Reviewer (`taiga-review`)
`taiga-review` performs deep static analyses on source files or piped files, outputting structured findings using a rigid schema contract.

**Examples:**
```bash
# Review a single source file
taiga-review auth.py

# Pipe a specific function using grep/sed
sed -n '12,50p' handler.go | taiga-review
```

**Output Contract:**
```text
[AI-TOOL: taiga-review]
Severity: [Low/Medium/High]
Issue: <Concise description of the bug or code quality flaw>
Evidence: <Specific function, line number or code snippet>
Fix: <Step-by-step description of the recommended replacement or refactoring>
```

---

### 4. Security Auditor (`taiga-sec`)
`taiga-sec` is your security reasoning assistant, analyzing logs, request/response dumps, JWT tokens, or configuration files in read-only mode to find logical authorization flaws (like IDOR), secrets leaks, and authentication issues.

**Examples:**
```bash
# Audit an HTTP proxy log payload (e.g. mitmproxy, Burp, curl dump) for IDOR
taiga-sec http_requests.json

# Check local configuration for exposed secrets
taiga-sec config.prod.json

# Analyze JWT tokens or OAuth payloads streamed from stdin
echo "eyJhbGciOi..." | taiga-sec
```

**Output Contract:**
```text
[AI-TOOL: taiga-sec]
Severity: [Medium/High/Critical]
Vulnerability: <IDOR / Broken Auth / Credentials Leak / PII Leak>
Location: <Endpoint URI, file name, line number, or JSON key>
Evidence: <Log or payload snippet exposing the risk>
Remediation: <Specific secure design advice and fix implementation description>
```

---

### 5. Interactive Chat REPL (`taiga-chat`)

Multi-turn chat session with persistence, history, and project-aware context.

```bash
# Launch interactive chat
taiga-chat

# Load a specific model
taiga-chat --model qwen3.5:9b

# Resume a saved session
taiga-chat --load <session_id>
```

**Session commands within the REPL:**
| Command | Description |
|---------|-------------|
| `/exit`, `/quit` | Save session and exit |
| `/clear` | Clear current conversation |
| `/save [name]` | Save session to SQLite |
| `/load [id]` | List or load a session |
| `/sessions` | List all saved sessions |
| `/delete [id]` | Delete a session |
| `/model [name]` | Show or switch model |
| `/help` | Show all commands |

*Multi-line input via `Alt+Enter`. Arrow keys for history search.*

---

### 6. OpenAI-Compatible Proxy Server (`taiga-serve`)

Exposes TaigaAI as a secure OpenAI API proxy at `http://localhost:11435`, enforcing secret redaction and security policies on every request before forwarding to Ollama.

```bash
# Start the proxy server
taiga-serve

# Custom bind
taiga-serve --host 127.0.0.1 --port 11435
```

**Use with any OpenAI-compatible client** (Continue.dev, Aider, Cursor, Cline):

```json
{
  "models": [{
    "title": "Taiga Secure Qwen",
    "provider": "openai",
    "model": "qwen3.5:9b",
    "apiBase": "http://localhost:11435/v1"
  }]
}
```

**Supported endpoints:**
- `POST /v1/chat/completions` — streaming (SSE) and non-streaming
- `GET /v1/models` — list available local models

---

### 7. Project-Level Configuration

Per-project overrides live in `.taiga/config.json` at project root:

```json
{
  "model": "qwen3.5:9b",
  "system_prompt": "You are a project-specific assistant..."
}
```

Additional project files:
- **`.taigaignore`** — glob patterns excluded from context (`node_modules/`, `*.pyc`)
- **`.taigacontext`** — explicit files always included in context

---

## ⚡ Local Cache & Modeling Performance

The engine includes **Local Query Caching** (backed by SQLite). 
- If you repeat an identical file review or commit message generation, the tool detects it via a SHA-256 hash of the prompt and model and returns the output **instantly (under 1ms)**.
- If a model connection fails or is missing, it will automatically attempt a **model fallback chain** (e.g., trying Qwen -> Llama) to ensure the CLI never hard-crashes.

---

## ⚙️ Model Customization & Configuration

The workstation is completely model-agnostic. You can bind any local Ollama model to any assistant tool by updating your local `config.json` file. 

To initialize the configuration, you can choose either of these seamless methods:

#### Method A: The Interactive Setup Assistant (Recommended)
Simply run the installer script:
```bash
./install.sh
```
This launches a premium, interactive wizard that scans your local Ollama models, recommends optimal roles, auto-discovers/whitelists your current workspace, and generates a valid `config.json` for you.

#### Method B: Manual Configuration
1. Copy the provided template configuration:
   ```bash
   cp config.json.example config.json
   ```
2. Open `config.json` and customize the model tags or whitelisted sandbox folders.

Example configuration output:
```json
{
  "allowed_paths": [
    "~/Documents/Code",
    "~/projects"
  ],
  "models": {
    "coder": "deepseek-coder:6.7b",
    "thinker": "mistral:7b",
    "security": "codellama:7b"
  },
  "ollama_url": "http://localhost:11434"
}
```
*Simply ensure your custom models are downloaded locally (`ollama pull deepseek-coder:6.7b`) and they will be routed automatically.*

---

## 🎨 VS Code Integration (Fully Local Autocomplete)

You can completely replace GitHub Copilot or tab-completion with local models running through the TaigaAI secure proxy.

### Via TaigaAI Proxy (Recommended — Enforces Security Policies)

Run the proxy in the background, then point any OpenAI-compatible extension at it:

```bash
taiga-serve &
```

Configure your editor to use `http://localhost:11435/v1` as the API base.

### Option A: Continue.dev Extension
`Continue` is a premier open-source AI assistant plugin for VS Code.

1. Install the **Continue** extension from the VS Code Marketplace.
2. Open `~/.continue/config.json` (or press `Ctrl+Shift+P` -> "Continue: Open config.json").
3. Use the TaigaAI proxy endpoint to enforce security policies:

```json
{
  "models": [
    {
      "title": "Taiga Secure",
      "provider": "openai",
      "model": "qwen3.5:9b",
      "apiBase": "http://localhost:11435/v1"
    }
  ]
}
```

### Option B: Llama Coder Extension (Frictionless Tab Autocomplete)
If you only want fast, single-line inline code completions:
1. Install **Llama Coder** from the VS Code Extensions tab.
2. Open VS Code Settings (`Ctrl+,`) and configure:
   - `Llama Coder: Model` ➔ `qwen3.5:9b`
   - `Llama Coder: Endpoint` ➔ `http://localhost:11434`

---

## 🧪 Testing & Post-Installation Verification

To ensure that your installation is fully functional and that all sandboxing rules are actively running on your workstation, we provide both a programmatic unit test suite and a manual verification checklist.

### 1. Running the Automated Test Suite
From the root of the repository, run the comprehensive, mock-isolated unit test suite to assert the correctness of path resolution, size limits, caching, regex validation, XML escaping, and secret redaction:
```bash
python3 tests/test_engine.py
```
*21 tests covering 7 modules.*

### 2. Manual Verification Checklist
* **Symlink Resolution**: Run `which taiga` to confirm that the shell correctly locates the symlink at `~/.local/bin/taiga`.
* **CWD Sandbox Check**: `cd /tmp` and execute `taiga -h`. It must fail instantly with `Security Violation: Command must be executed within whitelisted directories!`.
* **End-to-End Pipeline Test**: Run `taiga-review test_code.py` from within a whitelisted workspace directory. It will query your local Ollama server, apply schema validation, and subsequent executions will trigger instant cache hits under 1ms.

---

## 🔒 Security Audit & Policy

For in-depth documentation covering architecture, threat vector assessment, and active security controls, refer to the [SECURITY.md](SECURITY.md) policy guide.

---

## 🗺️ Roadmap

See [IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md) for the full engineering roadmap covering:

- **Phase 0:** WAL mode, secret redaction, hybrid context truncation ✓
- **Phase 1:** Chat REPL, proxy server, project-level config ✓
- **Phase 2:** MCP client/server, editor integrations
- **Phase 3:** Project maps, multi-model routing, optional RAG
- **Phase 4:** Git deepening, prompt templates
- **Phase 5:** Observability dashboard, cache analytics
- **Phase 6:** Multi-user support, namespace sandboxing
