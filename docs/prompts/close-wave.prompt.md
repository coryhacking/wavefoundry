# Close Wave

Owner: Engineering
Status: active
Last verified: 2026-05-19

Shortcut: **`Close wave`**

## Purpose

Finalize and archive the wave. Closure requires full reconciliation — not just a status flip.

## Closure Requirements (all must be met)

1. All changes marked `complete` or `deferred` with explicit rationale
2. All required review lanes from readiness reconciled in `## Review checkpoints` (or deferred with rationale)
3. When `wave_council_policy.enabled` is true, both `wave-council-readiness` and `wave-council-delivery` are present in `## Review Evidence`
4. **Docs-contract review:** recorded as performed with findings, or `Docs-contract review: not applicable` with rationale — required whenever any `docs/specs/*.md` changed during the wave
5. Chronology reconciled: `Status: completed`, `Completed at:` date, all change statuses finalized
6. Journal distillation: important implementation/review lessons added to relevant role or persona journals (absence of new journal entries is acceptable if nothing warranted one)
7. Durable memory promoted to `docs/references/project-context-memory.md` (and other canonical docs when applicable)
8. **Retrospective step completed:** ask "what was non-obvious in this wave that a future session should know?" — surface memory candidates for architectural decisions (why an approach was chosen), validated approaches that should carry forward (positive confirmations, not only corrections), and workflow discoveries; promote findings to auto-memory or `docs/references/project-context-memory.md`
9. `docs/agents/session-handoff.md` updated to idle format: last-closed wave ID and one-line summary of what shipped, plus an **Open questions / Deferred decisions** section for any intent not captured in a change doc

**Closure is blocked until all nine items are explicitly recorded in the wave record.**

## What Goes in Wave Summary

`## Wave Summary` is populated at closure. Include:
- What was delivered
- What was deferred (with rationale)
- Key decisions made during the wave
- Lessons promoted to journals or canonical docs

## Wavefoundry-Specific Closure Checks

- If framework scripts changed: confirm `python3 .wavefoundry/framework/scripts/run_tests.py` passes
- If `docs/prompts/` or manifest changed: confirm docs gate passes (**`wave_validate`** over MCP, or **`.wavefoundry/bin/docs-lint`** if MCP is unavailable)
- If seed prompts changed: confirm guard-overrides reset to `false`
- If Wave Council is enabled: confirm `council-moderator` recorded both council signoffs in `## Review Evidence`
