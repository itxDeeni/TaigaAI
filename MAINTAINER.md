# TaigaAI Maintainer Guide

Principles and conventions for maintaining this project.

## Git & Branching

```
main       ← tagged releases only
staging    ← integration branch, PR target
feat/*     ← feature branches, squash-merge into staging
fix/*      ← bug branches, squash-merge into staging
docs/*     ← documentation changes
```

- **`main` is sacred.** Only merged from `staging` after review + tests pass. No direct pushes.
- **`staging` is your integration branch.** All feature branches fork off `staging` and PR back into it.
- **Feature branches are ephemeral.** Delete after merge. Name them `feat/chat-sessions`, `fix/wal-lock`, `docs/readme-tools`.
- **Conventional commits always.** `feat:`, `fix:`, `docs:`, `refactor:`, `perf:`, `chore:`. Enables automated changelogs.
- **Never force push to `main` or `staging`.** If something goes wrong, branch and fix forward.
- **Squash-merge PRs** to keep history clean (`git merge --squash` or GitHub squash button).

## Security (Non-Negotiable)

- **Personally review every PR** touching `core/security.py`, `core/redaction.py`, or `core/cache.py` — these are the trust boundary.
- **No PR merges without `python3 tests/test_engine.py` passing.** CI must enforce this.
- **Audit new dependencies.** Zero-dependency core is a feature, not an accident. Every external package is new attack surface.
- **`config.json` is in `.gitignore`.** No PR should ever commit local paths.
- **Never log or print raw user prompts or AI responses that may contain secrets.**
- **Redact before cache, before Ollama, before any persistence — every time.**

## OSS Maintenance

- **Respond fast, code slow.** 24-hour reply on issues builds trust. Merging unreviewed code breaks it.
- **Say no.** "This adds an external dependency" or "this bypasses the sandbox" are valid rejections. The project's philosophy is its moat.
- **Document before merging.** PRs without README updates or tests are incomplete.
- **Release with changelogs.** Tagged releases (`v0.2.0`) with a brief description give users confidence to upgrade.
- **Keep the issue tracker clean.** Stale bugs get a "can you still reproduce this?" after 30 days. Close if no response.
- **Use GitHub's CODEOWNERS** to auto-request your review on security-critical paths.

## Code Review Checklist

- [ ] Follows existing patterns (zero-dependency preference, ANSI colors on stderr, output on stdout)
- [ ] All file I/O goes through `core/security.py` `validate_path()`
- [ ] All model-facing text goes through `core/redaction.py` `redact_text()`
- [ ] Tests added and passing
- [ ] README updated if adding a new tool or changing behavior
- [ ] No secrets, local paths, or debug prints committed
- [ ] Conventional commit message

## Versioning (Semver)

- **Major:** Breaking changes to the security model (e.g., removing a sandbox feature).
- **Minor:** New tools, new features (chat, serve, redaction).
- **Patch:** Bug fixes, docs, internal refactors.

Current: pre-`v1.0`. Tag `v0.1.0` for the first release.

## Recommended CI Pipeline

```yaml
# .github/workflows/ci.yml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install prompt_toolkit aiohttp
      - run: python3 tests/test_engine.py
```
