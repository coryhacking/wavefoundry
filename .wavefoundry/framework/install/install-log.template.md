# Wavefoundry Install Log

Owner: operator
Status: in-progress
Schema version: 1.2
Last verified: {{generated_at}}

This file is the **install state machine** for this project. Each row is a slug pointing at the canonical source for the step's full instructions — execute the source, verify the artifact exists, mark `[x]`, advance.

This is your project's **live log instance**, copied from `.wavefoundry/framework/install/install-log.template.md` on first install. The template is overwritten on framework upgrades; this file is NOT — your install progress is preserved.

## Row format

Each row is one of four kinds, distinguished by the parenthesized source:

- **Seed-driven:** `(seed-NNN)` — execute the named seed prompt; details live in `.wavefoundry/framework/seeds/NNN-*.prompt.md`
- **Script-driven:** `(script-name.py)` — run the named framework script
- **Verification:** `(verify)` — call the named tool/check; expected return shape follows `expects:`
- **Instruction:** `(instruction)` — operator/agent action with no on-disk artifact (e.g., restart the agent)

Mark a row `[~]` (not applicable) when the step genuinely doesn't fit this project. `wf_audit_install` treats `[~]` as terminal.

For full schema (row format, trustworthy-invariant rule, parser semantics), see `docs/references/install-log-format.md` (created during Phase 2 step 2.4).

---

## Phase 1 — Harness (no MCP required)

After Phase 1 completes, you must restart your AI agent so the MCP server becomes available.

- [ ] 1.1 — Bootstrap harness: lifecycle-ID policy auto-provision + venv + framework deps + semantic indexes + `wf` dispatcher shim + host configs + MCP dry-run smoke test (setup_wavefoundry.py) — artifact: the committed `.mcp.json` names `command: "python"` + `args: [".wavefoundry/framework/scripts/server.py"]` AND `python3 .wavefoundry/framework/scripts/server.py --dry-run` exits 0
- [ ] 1.2 — Verify lifecycle-ID policy provisioned by setup (verify) — expects: `docs/workflow-config.json` carries `lifecycle_id_policy.scheme_version` `"v2"`; if absent run `wf upgrade --materialize-lifecycle-policy` (never hand-edit epoch/offset/scheme_version)
- [ ] 1.3 — STOP: instruct operator to restart agent for MCP availability (instruction)

## Phase 2 — Project discovery (MCP required)

After every step, call `wf_audit_install` — it runs docs-lint, validates checked-row artifacts, and returns the next unchecked row.

- [ ] 2.1 — Audit Phase 1 outputs (verify) — expects: `wf_audit_install(phase=1)` returns `{status: "next_step"}`
- [ ] 2.2 — Capture legacy baseline wave if applicable (seed-110 / conditional) — artifact: `docs/waves/00000 wave-zero-plans-and-specs/wave.md` (or mark `[~]` if no legacy corpora detected)
- [ ] 2.3 — Bootstrap evidence base (seed-030) — artifact: `docs/repo-profile.json`
- [ ] 2.4 — Create canonical docs structure and topical artifact homes (seed-040) — artifact: `docs/README.md`
- [ ] 2.5 — Generate per-role agent docs INCLUDING the three councils as specialists (seed-050) — artifact: `docs/agents/specialists/wave-council.md`
- [ ] 2.6 — Map architecture, boundaries, and integration contracts (seed-060) — artifact: `docs/ARCHITECTURE.md`
- [ ] 2.7 — Establish quality, reliability, security, performance posture (seed-070) — artifact: `docs/QUALITY_SCORE.md`
- [ ] 2.8 — Wire docs gate mechanics (seed-080 + seed-090) — artifact: `docs/contributing/build-and-verification.md`
- [ ] 2.9 — Generate repo-local prompt surface (seed-100) — artifact: `docs/prompts/prompt-surface-manifest.json`
- [ ] 2.10 — Bootstrap wave artifacts and journals tree (seed-110) — artifact: `docs/waves/README.md`
- [ ] 2.11 — Synthesize project-specific personas (seed-120) — artifact: `docs/agents/personas/README.md`
- [ ] 2.12 — Bootstrap per-role journals (seed-130) — artifact: `docs/agents/journals/`
- [ ] 2.13 — Register drift and reindex expectations (seed-140) — artifact: drift entries in `docs/workflow-config.json`
- [ ] 2.14 — Final install completeness gate (verify) — expects: `wf_audit_install()` returns `{status: "complete"}`
- [ ] 2.15 — Deliver structured operator summary handoff (instruction) — covers: what was seeded, workflow, commands, agents/personas, docs/gates, configuration, first-time-operator rules (see seed-012 § Operator summary handoff)
