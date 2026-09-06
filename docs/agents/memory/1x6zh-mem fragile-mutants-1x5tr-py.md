# Fragile: mutants_1x5tr.py

Owner: Engineering
Status: rejected
Last verified: 2026-09-05

Memory ID: `1x6zh-mem fragile-mutants-1x5tr-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-05
Updated: 2026-09-05
Source exploration cost: 1286966
Source event: `repeated-repairs:1x5tr:mutants_1x5tr.py`
Validation: reject
Validated by: agent
Action delta: No durable action: mutants_1x5tr.py is a reviewer's scratch probe script under the session scratchpad, not a repository file; the two findings named repaired secrets_validators.py and its test module.
Validation rationale: The drafter keyed on the artifact_or_test_id text of CODE-DEL-1 and QA-DEL-1, which cite the scratch mutant script; the target does not exist in the tree and the real repaired files are covered by the RED-DEL-9 rewrite.
Evidence verified: true
Current target verified: true
Canonical overlap: none
## Summary

mutants_1x5tr.py required 2 separate repairs during wave 1x5tr; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `CODE-DEL-1`
- `QA-DEL-1`
- `1x5tr`

## Targets

- `mutants_1x5tr.py`
