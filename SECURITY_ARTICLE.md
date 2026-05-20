# Solving the Local AI Sandbox Issue: How TaigaAI Keeps Your Workstation Safe

As developers, we’re increasingly integrating AI copilots directly into our terminal workflows. Running local LLMs via Ollama is fantastic for privacy and offline capability, but it introduces a glaring security dilemma: **the local sandbox issue.**

When you pipe local files, logs, or directories into an AI CLI, you are exposing your filesystem. A malicious prompt injection within a third-party codebase, or an overly aggressive autonomous agent, can easily result in path traversal (`../../`), arbitrary file reads, or even disastrous automated shell executions.

We need local AI assistance, but we need it strictly sandboxed. This is the exact problem [TaigaAI](https://github.com/itxDeeni/TaigaAI) solves.

---

## What is TaigaAI?

TaigaAI is a zero-autonomy, read-only developer copilot built specifically to interface natively with local Ollama models. Instead of giving the AI a long leash to roam your system and execute code, TaigaAI operates on a strict, hardened perimeter.

Here is a technical breakdown of how TaigaAI solves the local sandboxing issue at the architecture level:

---

## The Core Security Safeguards

### 1. Canonical Path Resolution & Whitelisting
Many AI CLI tools blindly open whatever file path you pass them. TaigaAI intercepts every file argument and forces it through Python’s `Path(file_path).resolve()`.

* **The Fix:** This resolves all symlinks and neutralizes relative traversal operators (`../../`).
* **The Whitelist:** Even after resolution, the file is blocked unless its absolute path lands inside a pre-configured whitelist (e.g., `~/projects/` or `~/Documents/Code`). Requests outside approved workspace boundaries are rejected immediately.

### 2. Protection Against Memory DoS
What happens when you accidentally pipe a 10GB database dump or a runaway application log into your local model? Your machine locks up, or your context window blows out, crashing the local server.

* **The Fix:** TaigaAI imposes an explicit, hardcoded **5MB size threshold** on all read operations. It acts as a circuit breaker, preventing memory exhaustion attacks and saving your RAM from massive data dumps.

### 3. Prompt Injection Escaping
If you use an AI to review untrusted code or audit HTTP logs (`taiga-sec`), you run the risk of the payload containing a prompt injection intended to hijack the AI's output format or bypass safety constraints.

* **The Fix:** Before any local file or piped `stdin` hits your Ollama model, TaigaAI neutralizes prompt-control delimiters. This ensures the model treats the ingested code strictly as data, preventing layout escaping or instruction overriding.

### 4. Absolute "Zero-Eval" Isolation
The most dangerous trend in AI tooling is the "auto-execute" feature. TaigaAI is fundamentally read-only.

* **The Fix:** AI outputs are treated strictly as text. There is zero `eval()` and zero automated shell execution. If `taiga` suggests a shell command, or `taiga-git` generates a commit message, it outputs it to your terminal. *You* remain the final execution layer.

---

## Practical Application: The CLI Toolset

With the security perimeter established, TaigaAI exposes this read-only architecture through a suite of specialized CLI tools designed for daily development workflows:

* **`taiga`**: The core router for direct inline instructions or securely piping context (e.g., `cat schema.sql | taiga -c -p "Convert this PostgreSQL schema into a Go struct"`).
* **`taiga-git`**: Analyzes staged changes to generate conventional commit messages or Pull Request summaries, adhering strictly to the "no auto-commit" policy.
* **`taiga-review` & `taiga-sec`**: Targeted static analysis tools that evaluate source files, HTTP proxy logs, or configs for logic flaws, secret leaks, and code quality issues, returning findings via a rigid output contract.

To maintain high performance without hammering your local system on repetitive tasks, the engine utilizes a local SQLite query cache. If you repeat an identical file review or commit generation, it returns the cached output instantly (under 1ms).

---

## Getting Started: Multiplatform Installation

Setting up a secure perimeter shouldn't require a weekend of configuring containers. TaigaAI installs directly to your host environment and supports Linux, macOS, and Windows.

### For Linux & macOS:
```bash
git clone https://github.com/itxDeeni/TaigaAI.git
cd TaigaAI
./install.sh
```
*This registers safe symlinks inside `~/.local/bin/` so the tools are accessible globally.*

### For Windows (PowerShell):
```powershell
git clone https://github.com/itxDeeni/TaigaAI.git
cd TaigaAI
Set-ExecutionPolicy Bypass -Scope Process
.\install.ps1
```
*This script self-diagnoses Windows Python & Git pathways and adds the batch wrappers to your User Environment Path.*

During installation, an interactive setup script will scan your local Ollama models, recommend optimal routing, and help you configure the strict directory whitelists (`config.json`) required for the sandboxing engine to run safely.

---

## The Takeaway

We shouldn't have to choose between the productivity of AI copilots and the security of our host operating systems. By implementing canonical sandboxing, memory caps, and zero-autonomy execution, TaigaAI proves that you can have a deeply integrated terminal assistant without giving up the keys to your filesystem.

---

### 🔗 Get Involved & Star the Repo!
* **GitHub Repository:** [itxDeeni/TaigaAI](https://github.com/itxDeeni/TaigaAI)
