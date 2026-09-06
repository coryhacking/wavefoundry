# Repaired defect QA-DEL-6

Owner: Engineering
Status: rejected
Last verified: 2026-09-05

Memory ID: `1x6r0-mem repaired-defect-qa-del-6`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-05
Updated: 2026-09-05
Source exploration cost: 1322693
Source event: `finding:1x5tr:QA-DEL-6`
Validation: reject
Validated by: agent
Action delta: No durable action: QA-DEL-6 was a missing test pin for the ledger dedupe, closed by one test; the target the drafter picked is a reviewer's scratch mutant script, not a repository file.
Validation rationale: The candidate keys on the artifact text of the finding (mutants4_1x5tr.py under the session scratchpad); the durable lesson about the scanner cache producers is already active as 1x5tw-mem and the test-oracle rule (delete the guard before claiming it lands) is standing project practice.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Real defect fixed in wave 1x5tr: Gap closed with a test that discriminates the mutant on both paths.

## Evidence

- `QA-DEL-6`
- `ev-qa-del-6-3`
- `1x5tr`

## Targets

- `mutants4_1x5tr.py`
