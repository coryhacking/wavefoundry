# Junie Guidelines — Wavefoundry

Thin pointer. Read `AGENTS.md` first.

## Startup Order

1. `AGENTS.md` — shortcuts, stage gate, git commits policy
2. `docs/prompts/index.md` — public command surface

## Key Rules

- Stage gate before any code edit: change doc → wave admission → Prepare wave
- Never commit without explicit operator instruction
- Do not edit `.wavefoundry/framework/seeds/*.prompt.md` without `seed_edit_allowed` in `.wavefoundry/guard-overrides.json` and an admitted change doc per `AGENTS.md`
