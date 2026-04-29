# Claude Code — Wavefoundry

Thin pointer. Read `AGENTS.md` first for the full agent operating surface.

## Startup Order

1. Read `AGENTS.md` — shortcuts, stage gate, git commits policy, framework script hygiene
2. Read `docs/prompts/index.md` — public command catalog
3. Read `docs/references/project-overview.md` — project orientation
4. Read `docs/agents/session-handoff.md` — current session state if work is in progress

## Key Guardrails

- Before editing framework seeds: set `.wavefoundry/guard-overrides.json` `seed_edit_allowed.enabled: true`; restore after editing
- Before broad framework-maintenance edits: set `framework_edit_allowed.enabled: true`; restore after
- Never run `git commit` unless the operator explicitly requests it in the current session
- Stage gate applies before any code edit: change doc → wave admission → Prepare wave

## Docs Gate

After any edit to files under `docs/`, the post-edit hook runs `./docs-lint` automatically. Fix failures before continuing.

## Framework Tests

```bash
python3 .wavefoundry/framework/scripts/run_tests.py
```

## Self-Hosting Note

`.wavefoundry/framework/` is the canonical framework directory. Seeds at `.wavefoundry/framework/seeds/`, scripts at `.wavefoundry/framework/scripts/`.
