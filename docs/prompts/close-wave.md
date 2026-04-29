# Close Wave

Owner: Engineering
Status: active
Last verified: 2026-04-28

Shortcut: **`Close wave`**

## Purpose

Finalize and archive the wave. Closure requires full reconciliation — not just a status flip.

## Closure Requirements (all must be met)

1. All changes marked `complete` or `deferred` with explicit rationale
2. All required review lanes from readiness reconciled in `## Review checkpoints` (or deferred with rationale)
3. **Docs-contract review:** recorded as performed with findings, or `Docs-contract review: not applicable` with rationale — required whenever any `docs/specs/*.md` changed during the wave
4. Chronology reconciled: `Status: completed`, `Completed at:` date, all change statuses finalized
5. Journal distillation: important implementation/review lessons added to relevant role or persona journals (absence of new journal entries is acceptable if nothing warranted one)
6. Durable memory promoted to `docs/references/project-context-memory.md` (and other canonical docs when applicable)
7. `docs/agents/session-handoff.md` cleared or refreshed to post-closure state

**Closure is blocked until all seven items are explicitly recorded in the wave record.**

## What Goes in Wave Summary

`## Wave Summary` is populated at closure. Include:
- What was delivered
- What was deferred (with rationale)
- Key decisions made during the wave
- Lessons promoted to journals or canonical docs

## Wavefoundry-Specific Closure Checks

- If framework scripts changed: confirm `python3 .wavefoundry/framework/scripts/run_tests.py` passes
- If `docs/prompts/` or manifest changed: confirm `./docs-lint` passes
- If seed prompts changed: confirm guard-overrides reset to `false`
