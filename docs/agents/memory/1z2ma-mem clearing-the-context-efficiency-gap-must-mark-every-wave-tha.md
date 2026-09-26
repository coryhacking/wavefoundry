# Clearing the context-efficiency gap must mark every wave that lived through it

Owner: Engineering
Status: active
Last verified: 2026-09-25

Memory ID: `1z2ma-mem clearing-the-context-efficiency-gap-must-mark-every-wave-tha`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-09-25
Updated: 2026-09-25
Source exploration cost: 48347
Source event: `decision-log:1z1vu-bug context-efficiency-gap-permanent-and-unexplained:f212d52261e56f66`
Validation: promote
Validated by: agent
Action delta: When changing the gap barrier or its clear, keep fail-closed per wave: any path that lifts the store-wide gap must mark unsealed and not-closed waves (including ones with no wave_state row) accounting_gap in the same transaction, and never treat a leftover .clearing file as a live gap.
Validation rationale: The generated candidate recorded only the CLI-versus-MCP-tool choice, which the code shows plainly. The non-obvious lesson came from readiness: a naive clear let waves open across the gap publish undercounts as healthy (F4), and marking only existing rows missed waves refused a row during the gap (B1); delivery found a stale set-aside file marked healthy waves (N1). Verified against clear_accounting_gap and _commit_event_once in the current tree.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

The context-efficiency accounting gap is store-wide (sentinel file plus meta.accounting_gap), and while it holds, _commit_event refuses events before _touch_wave, so a wave whose first telemetry fell in the gap has no wave_state row. clear_accounting_gap therefore upserts rows for every not-closed wave folder and marks every unsealed row measurement_status='accounting_gap' in the same transaction that removes the barrier; a set-aside .clearing file counts as a gap only while the meta flag is set. Busy/locked writes retry whole attempts within BUSY_RETRY_BUDGET_SECONDS before poisoning.

## Evidence

- `1z1vu-bug context-efficiency-gap-permanent-and-unexplained`
- `1z2m4`

## Targets

- `.wavefoundry/framework/scripts/context_efficiency.py`
