# Contributing to TaigaAI

Thanks for contributing. TaigaAI is a local-first, security-hardened AI copilot. Keep these principles in mind when proposing changes.

## Philosophy

- **Zero autonomy.** No code generation, no auto-commit, no command execution. AI output is text only.
- **Local safety.** Everything runs on the user's machine. No telemetry, no cloud APIs, no silent network calls.
- **Security first.** New features must pass through the sandbox layer. Never bypass `validate_path()` or skip `redact_text()`.

## Getting Started

```bash
git clone https://github.com/itxDeeni/TaigaAI
cd TaigaAI
cp config.json.example config.json  # edit to match your Ollama setup
python3 tests/test_engine.py        # 21 tests must pass
```

Dependencies: Python 3.10+, [Ollama](https://ollama.com/), `prompt_toolkit`, `aiohttp`.

```bash
pip install prompt_toolkit aiohttp
```

## Development Workflow

1. **Fork and branch** off `staging`.
2. **Write code** matching existing patterns (zero-dependency preference, ANSI color constants, stderr for UI, stdout for output).
3. **Add tests** in `tests/test_engine.py`. Mock external services.
4. **Run tests** before committing:
   ```bash
   python3 tests/test_engine.py
   ```
5. **Use conventional commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `perf:`, `chore:`.
6. **Open a PR** against `staging`.

## Code Conventions

- Python standard library over external packages unless there's a clear justification.
- All file I/O goes through `core/security.py` `validate_path()`.
- All model-facing text goes through `core/redaction.py` `redact_text()`.
- UI messages use `COLOR_*` ANSI constants, printed to `sys.stderr`.
- Tool output goes to `sys.stdout` (pipeable).
- No docstrings required — code should be self-documenting.
- SQLite connections use `_conn()` with WAL mode from `core/cache.py`.

## Security Rules

- **Never** log or print raw user prompts or AI responses that may contain secrets.
- **Never** commit `config.json` or `.taiga/.chat_history`.
- **Never** add network calls without user opt-in (interactive model puller is the only exception).
- **Always** redact before cache, before Ollama, before any persistence.
- **Always** validate paths before reading files.

## Adding a New Tool

1. Create `bin/taiga-<tool>` entry point (executable, shebang, project root in sys.path).
2. Core logic in `core/<module>.py`.
3. Add to `bin/taiga-manage` tools list and uninstall list.
4. Add to `README.md` workflow section.
5. Add tests.

## Questions

Open an issue or start a discussion. PRs welcome.
