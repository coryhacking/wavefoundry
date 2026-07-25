# Repaired defect fusion-empty-relevance-union-surfaces-unrelated-records

Owner: Engineering
Status: active
Last verified: 2026-07-24

Memory ID: `1theb-mem repaired-defect-fusion-empty-relevance-union-surfaces-unrela`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-24
Updated: 2026-07-24
Source exploration cost: 426910
Source event: `finding:1tbt5:fusion-empty-relevance-union-surfaces-unrelated-records`
Validation: promote
Validated by: agent
Action delta: Before changing the memory-eval candidate ranking (_policy_order in run_memory_eval.py), remember the query path must restrict to the positive-match union: an empty lexical+semantic union means zero candidates, never all surfaced records; the shipped-baseline containment path opts out via prefiltered=True.
Validation rationale: Verified against the terminal ledger chain and the current tree: the empty-relevance-union defect was real (an empty order admitted every record), the fix restricts the query path and adds test_empty_relevance_union_yields_zero_candidates, and the targets (run_memory_eval.py, test_memory_eval.py) are the actual repaired surfaces. Correctly targeted, evidence-backed, no harness-token misattribution.
Evidence verified: true
Current target verified: true
Canonical overlap: none
## Summary

Real defect fixed in wave 1tbt5: Repair verified complete: the query path admits zero candidates on an empty union, the baseline path is unrestricted via prefiltered=True, and the hermetic metrics and fingerprint reproduce unchanged. The blocking code-reviewer lane is cle…

## Evidence

- `fusion-empty-relevance-union-surfaces-unrelated-records`
- `ev-fusion-empty-relevance-union-surfaces-unrelated--3`
- `1tbt5`

## Targets

- `test_memory_eval.py`
- `.wavefoundry/framework/scripts/tests/eval/run_memory_eval.py`
