# interrupted-lifecycle-states-need-a-named-recovery-route

Owner: Engineering
Status: active
Last verified: 2026-07-22

Memory ID: `1td27-mem interrupted-lifecycle-states-need-a-named-recovery-route`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-07-22
Updated: 2026-07-22
Source event: `finding:1t8la:pending-archive-docs-gate-has-no-recovery`
Validation: promote
Validated by: agent
Action delta: When a fenced multi-step lifecycle can be interrupted, give its intermediate on-disk state a lint/gate diagnostic that names the exact retry command instead of a bare schema error.
Validation rationale: The generated summary only echoed the lane-clearance prose; the durable lesson is the recovery-route principle. Verified against the repaired check_memory_docs branch: the pending-archive state (retired-status body under memory/archive after the rename window) now yields a diagnostic naming the memory_reconcile retry, pinned by regression, while completed-archive validation stays strict.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1t8la's archive transaction left a valid interrupted state (retired-status body under memory/archive after the rename window) that failed the docs gate with a bare schema error, stranding upgrades with no route out. Repair: the gate detects the pending-archive combination and names the exact memory_reconcile(memory_id=..., status='archived', archive_reason=...) retry. When designing interruption-tolerant multi-step lifecycles, every reachable intermediate state needs either automatic convergence or a gate diagnostic naming the recovery command; a schema error without a route is a stranded operator.

## Evidence

- `pending-archive-docs-gate-has-no-recovery`
- `ev-pending-archive-docs-gate-has-no-recovery-6`
- `1t8la`

## Targets

- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/memory_records.py`
