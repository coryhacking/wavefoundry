# Repaired defect run-garden-stdout-contract-break

Owner: Engineering
Status: superseded
Last verified: 2026-07-22

Memory ID: `1tazk-mem repaired-defect-run-garden-stdout-contract-break`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-22
Updated: 2026-07-22
Source exploration cost: 66598
Source event: `finding:1tbvp:run-garden-stdout-contract-break`
Validation: rewrite
Validated by: agent
Action delta: Before changing any subprocess's stdout wording, census who parses that output; prose-grep contracts (like the retired 'wrote' grep) must be replaced with an exact-prefix machine line tested against the real producer.
Validation rationale: The drafted candidate again extracted its target from the verification command (run_tests.py) instead of the contract surfaces (docs_gardener.py stdout and server_impl.py run_garden). The durable lesson is real and two-sided: changing gardener stdout silently broke run_garden's 'wrote' grep and with it the wf_garden_docs index-refresh trigger, and the suite missed it because RunGardenTests fed a hand-written fixture instead of canonical producer output.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1tax0-mem stdout-is-a-contract-when-something-parses-it`
## Summary

Real defect fixed in wave 1tbvp: Repair verified terminal: live MCP reproduction of the operator's failing case now passes, with executed suite evidence and drift-proof test coverage on both sides of the contract.

## Evidence

- `run-garden-stdout-contract-break`
- `ev-run-garden-stdout-contract-break-3`
- `1tbvp`

## Targets

- `run_tests.py`
