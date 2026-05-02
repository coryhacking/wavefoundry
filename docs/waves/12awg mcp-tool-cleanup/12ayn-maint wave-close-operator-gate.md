# Wave Close Operator Gate

Change ID: `12ayn-maint wave-close-operator-gate`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-01
Wave: `12awg mcp-tool-cleanup`

## Rationale

During the review of wave `12awg`, `wave_close(mode="create")` was called automatically after a dead-code removal task without explicit operator instruction. No hard rule existed requiring operator approval before writing the closed status — unlike `git commit`, which already had a clear operator-owned policy in AGENTS.md and the run-contract seed. This gap allowed an agent to chain a destructive finalization step onto an unrelated cleanup task.

## Requirements

1. Add a `## Wave Close (Operator-Owned)` section to `AGENTS.md` mirroring the existing `## Git Commits (Operator-Owned)` pattern.
2. Clarify that adjacent tasks ("remove dead code", "run review", "implement wave") do not constitute close approval.
3. Add the same rule to `020-run-contract.prompt.md` alongside the `git commit` rule in Operating Rules.
4. Add a hard guardrail to `190-finalize-feature.prompt.md` Guardrails section with bold emphasis.
5. Explicitly exempt `wave_close(mode="dry_run")` in all three locations — dry-run is always safe.

## Scope

**In scope:**

- `AGENTS.md` policy section addition
- `020-run-contract.prompt.md` Operating Rules addition
- `190-finalize-feature.prompt.md` Guardrails addition

**Out of scope:**

- Any server.py changes — this is a policy/guidance change only
- Changes to how `wave_close` validates or executes — behavior is unchanged

## Acceptance Criteria

| # | Criteria | Priority |
|---|----------|----------|
| AC-1 | `AGENTS.md` has `## Wave Close (Operator-Owned)` section prohibiting `wave_close(mode="create"\|"apply")` without explicit operator instruction | required |
| AC-2 | Rule clarifies adjacent tasks do not constitute close approval | required |
| AC-3 | `020-run-contract.prompt.md` includes the rule alongside the `git commit` rule | required |
| AC-4 | `190-finalize-feature.prompt.md` Guardrails section includes the hard gate rule | required |
| AC-5 | `wave_close(mode="dry_run")` explicitly exempted in all three locations | required |
| AC-6 | `wave_validate` clean after edits | required |

## Progress Log

| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-05-01 | Change doc authored and implemented in the same session as the triggering incident. | `wave_validate` clean; all three files updated. |
