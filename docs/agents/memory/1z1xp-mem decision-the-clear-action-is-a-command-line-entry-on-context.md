# Decision: The clear action is a command-line entry on `context_effici…

Owner: Engineering
Status: superseded
Last verified: 2026-09-25

Memory ID: `1z1xp-mem decision-the-clear-action-is-a-command-line-entry-on-context`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-25
Updated: 2026-09-25
Source exploration cost: 48347
Source event: `decision-log:1z1vu-bug context-efficiency-gap-permanent-and-unexplained:f212d52261e56f66`
Validation: rewrite
Validated by: agent
Action delta: When changing the gap barrier or its clear, keep fail-closed per wave: any path that lifts the store-wide gap must mark unsealed and not-closed waves (including ones with no wave_state row) accounting_gap in the same transaction, and never treat a leftover .clearing file as a live gap.
Validation rationale: The generated candidate recorded only the CLI-versus-MCP-tool choice, which the code shows plainly. The non-obvious lesson came from readiness: a naive clear let waves open across the gap publish undercounts as healthy (F4), and marking only existing rows missed waves refused a row during the gap (B1); delivery found a stale set-aside file marked healthy waves (N1). Verified against clear_accounting_gap and _commit_event_once in the current tree.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1z2ma-mem clearing-the-context-efficiency-gap-must-mark-every-wave-tha`

## Summary

Decision (wave 1z2m4): The clear action is a command-line entry on `context_efficiency.py`, not an MCP tool or `wf` subcommand. Rationale: Smallest surface; the MCP tool roster and the `wf` dispatcher are pinned elsewhere; it runs without MCP.

## Evidence

- `1z1vu-bug context-efficiency-gap-permanent-and-unexplained`
- `1z2m4`

## Targets

- `context_efficiency.py`
