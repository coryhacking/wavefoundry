# Contributing to Wavefoundry

Thanks for your interest in Wavefoundry. This document describes how to file
issues, propose changes, and submit pull requests.

If you only have a few minutes, skim the **TL;DR**, the **License of
contributions**, and the **Wave workflow** section.

---

## TL;DR

- Open an issue first for anything non-trivial — it saves rework.
- Wavefoundry is self-hosted: the project develops itself using the Wave
  Framework it ships. Significant changes go through a **wave**.
- All contributions are licensed under Apache-2.0 — same as the project. No CLA.
- Be respectful. See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
- Report security issues privately. See [`SECURITY.md`](SECURITY.md).

---

## Ways to contribute

| Type | Where to start |
|---|---|
| Bug report | [Open an issue](https://github.com/coryhacking/wavefoundry/issues/new/choose) using the bug template |
| Feature idea | Open an issue using the feature template *before* writing code |
| Documentation fix | Small fixes can go straight to a PR; larger restructurings should start with an issue |
| Seed prompt change | Open an issue first — seeds are guarded by a stage gate (see below) |
| Security report | Do **not** open a public issue. See [`SECURITY.md`](SECURITY.md) |

---

## License of contributions

By contributing to this repository you agree that your contributions are
licensed under the [Apache License, Version 2.0](LICENSE), the same license
that covers the rest of the project. You retain copyright on what you wrote;
Apache-2.0 §5 grants the project the rights it needs without a separate CLA.

If your employer has IP rights over your work, get their sign-off before
submitting. Apache-2.0's inbound-equals-outbound rule does not override
employment agreements.

---

## Development setup

**Requirements**

- Python ≥ 3.11
- macOS or Linux native (Windows via WSL2)
- An MCP-aware agent host if you want to exercise the full tool surface
  (Claude Code, Cursor, Codex, Junie, Copilot, Windsurf — see the install
  table in [`docs/prompts/install-wavefoundry.prompt.md`](docs/prompts/install-wavefoundry.prompt.md))

**Clone and bootstrap**

```bash
git clone https://github.com/coryhacking/wavefoundry.git
cd wavefoundry
python3 .wavefoundry/framework/scripts/setup_wavefoundry.py
```

`setup_wavefoundry.py` creates a shared tool venv at `~/.wavefoundry/venv`
(override with `$WAVEFOUNDRY_TOOL_VENV`), installs dependencies, and builds
the local semantic index. It does not modify your system or project Python.

**Run the framework test suite**

```bash
python3 .wavefoundry/framework/scripts/run_tests.py
```

Tests must pass before any PR is reviewed.

**Documentation gate**

After editing anything under `docs/`, run:

```bash
.wavefoundry/bin/docs-lint
```

If an MCP server is attached, `wave_validate` and `wave_garden` are the
preferred checks. The `docs-lint` hook runs automatically on save and must
exit clean before the change is mergeable.

---

## Wave workflow

Wavefoundry develops itself using the Wave Framework. The expectation is:

1. **Plan feature** — for any non-trivial change, an agent (or you, by hand)
   authors a change document under `docs/plans/<id>.md`.
2. **Create wave** and **Add change** — the change is admitted to a wave.
3. **Prepare wave** — readiness check runs before any code edit. The stage
   gate is enforced; do not edit repository code before this step passes.
4. **Implement** — make the change.
5. **Review wave** — required reviewer lanes (security, performance,
   architecture, operator) run via `wave_review`.
6. **Close wave** — operator signoff plus all declared lanes recorded.
   Produces a permanent record in `docs/waves/`.

For trivial fixes (typo, single-line doc edit, dead-link repair), you can
skip the wave and submit a PR directly. When in doubt, open an issue and
ask.

See [`AGENTS.md`](AGENTS.md) for the full operator surface and
[`docs/contributing/`](docs/contributing/) for the lifecycle documents in
detail.

---

## Seed prompts and framework edits

Two areas are protected by stage gates because they affect every downstream
install:

| Area | Gate name | How to open |
|---|---|---|
| `.wavefoundry/framework/seeds/` | `seed_edit_allowed` | `.wavefoundry/bin/wave-gate open seed_edit_allowed` |
| Broad framework scripts | `framework_edit_allowed` | `.wavefoundry/bin/wave-gate open framework_edit_allowed` |

Close the gate immediately after the edit:

```bash
.wavefoundry/bin/wave-gate close seed_edit_allowed
```

If you don't have wave tooling installed yet, raise an issue and a
maintainer will route the change.

---

## Pull request expectations

- One logical change per PR. If you find a second thing to fix, file a
  follow-up issue.
- Reference the issue number in the PR description (`Closes #123` if it
  resolves it).
- Tests must pass. Docs gate must pass. The PR template asks you to confirm
  both.
- Keep commit messages descriptive. No AI-attribution trailers
  (`Co-Authored-By: Claude` etc.) — this project's commit style is
  human-authored, even when an agent helped.
- Squash on merge is the default. Keep history readable from `main`.

---

## Reporting bugs

Use the bug-report issue template. Include:

- Wavefoundry version (`cat .wavefoundry/framework/VERSION`)
- Python version and OS
- The agent host you're using (Claude Code, Cursor, …) if relevant
- Minimal reproduction steps
- Expected vs. actual behavior
- Log output (`~/.wavefoundry/logs/` and `.wavefoundry/logs/`)

---

## Questions

For usage questions and design discussion, open a
[GitHub Discussion](https://github.com/coryhacking/wavefoundry/discussions)
rather than an issue.

For anything security-sensitive, see [`SECURITY.md`](SECURITY.md).
