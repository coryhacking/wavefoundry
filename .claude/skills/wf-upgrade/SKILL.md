---
name: wf-upgrade
description: Operator checklist for intentionally editing the Wave Framework or repo-local wave surfaces (Upgrade Wavefoundry). Framework maintenance only, never product code changes.
disable-model-invocation: true
---

# Upgrade Wavefoundry

**Backwards-compatible operator phrases:** *Upgrade wave framework*, *Upgrade wave context* — same checklist.

Use this checklist when intentionally editing the wave framework or repo-local wave surfaces.

## Gate sequence

1. Read `AGENTS.md` and `docs/prompts/upgrade-wavefoundry.prompt.md`.
2. Produce a file-level patch plan and wait for operator approval before broad framework-maintenance edits.
3. After the operator approves the file-level plan, open the framework edit gate before editing these protected surfaces: `wf_open_gate(gate="framework_edit_allowed")` (CLI fallback: `wf gate open framework_edit_allowed`).
   - `.wavefoundry/framework/`
   - `docs/prompts/`
   - `AGENTS.md`
   - tracked hook config files
4. Before editing any `.wavefoundry/framework/seeds/*.prompt.md` file, also open the seed gate: `wf_open_gate(gate="seed_edit_allowed")` (CLI fallback: `wf gate open seed_edit_allowed`).
5. When the maintenance pass is complete, close both gates: `wf_close_gate(gate="seed_edit_allowed")` and `wf_close_gate(gate="framework_edit_allowed")` (CLI fallback: `wf gate close seed_edit_allowed` and `wf gate close framework_edit_allowed`).

## Verification sequence

1. Run framework tests when the test suite is present (development installs only — not included in distribution packs): `python3 -B .wavefoundry/framework/scripts/run_tests.py` (skip if `run_tests.py` does not exist)
2. `wf render-surfaces` (hooks, MCP, bin launchers, and `render_agent_surfaces.py` when `docs/agents/guru.md` exists)
3. Backfill `AGENTS.md` auto-Guru tier-1 sections per `seed-050` when missing; ensure `docs/agents/guru.md` exists; re-run step 2 if tier-1 was just added
4. `./.wavefoundry/bin/wf docs-gardener` — native Windows: `.\.wavefoundry\bin\wf.cmd docs-gardener` (or MCP `wf_garden_docs`)
5. `./.wavefoundry/bin/wf docs-lint` — native Windows: `.\.wavefoundry\bin\wf.cmd docs-lint` (or MCP `wf_validate_docs`)

## Guardrails

- Keep inventory and drift-detection lanes read-only unless explicit write ownership was granted.
- Update existing canonical docs in place instead of creating parallel files when a topical home already exists.
- Preserve memory records, personas, wave archives, and historical records unless the upgrade explicitly retires a live replacement surface.
