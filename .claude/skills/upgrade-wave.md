# Claude skill: Upgrade wave framework

**Backwards-compatible operator phrase:** *Upgrade wave context* — same checklist.

Use this checklist when intentionally editing the wave framework or repo-local wave surfaces.

## Gate sequence

1. Read `AGENTS.md` and `docs/prompts/upgrade-wavefoundry.md`.
2. Produce a file-level patch plan and wait for operator approval before broad framework-maintenance edits.
3. Create or update `.wavefoundry/guard-overrides.json` before editing:
   - `.wavefoundry/framework/`
   - `docs/prompts/`
   - `AGENTS.md`
   - tracked hook config files
4. Set `framework_edit_allowed.enabled: true` after the operator approves the file-level plan.
5. Set `seed_edit_allowed.enabled: true` before editing any `.wavefoundry/framework/seeds/*.prompt.md` file.
6. Delete the override file or set both flags back to `false` when the maintenance pass is complete.

## Verification sequence

1. `python3 -B .wavefoundry/framework/scripts/run_tests.py`
2. `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py`
3. **Docs gate:** Prefer MCP **`wave_garden`** (if needed) then **`wave_validate`**. **CLI fallback:** `.wavefoundry/bin/docs-gardener` then `.wavefoundry/bin/docs-lint`

## Guardrails

- Keep inventory and drift-detection lanes read-only unless explicit write ownership was granted.
- Update existing canonical docs in place instead of creating parallel files when a topical home already exists.
- Preserve journals, personas, wave archives, and historical records unless the upgrade explicitly retires a live replacement surface.
