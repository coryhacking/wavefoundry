# Repaired defect fusion-empty-relevance-union-surfaces-unrelated-records

Owner: Engineering
Status: archived
Last verified: 2026-11-10

Memory ID: `1theb-mem repaired-defect-fusion-empty-relevance-union-surfaces-unrela`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-24
Updated: 2026-11-25
Source exploration cost: 426910
Source event: `finding:1tbt5:fusion-empty-relevance-union-surfaces-unrelated-records`
Validation: promote
Validated by: agent
Action delta: Before changing the memory-eval candidate ranking (_policy_order in run_memory_eval.py), remember the query path must restrict to the positive-match union: an empty lexical+semantic union means zero candidates, never all surfaced records; the shipped-baseline containment path opts out via prefiltered=True.
Validation rationale: Verified against the terminal ledger chain and the current tree: the empty-relevance-union defect was real (an empty order admitted every record), the fix restricts the query path and adds test_empty_relevance_union_yields_zero_candidates, and the targets (run_memory_eval.py, test_memory_eval.py) are the actual repaired surfaces. Correctly targeted, evidence-backed, no harness-token misattribution.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Checked at: 2026-11-25T16:09:20Z
Check note: Item 7 review: encoded elsewhere. tests/eval/run_memory_eval.py no longer exists (logic is in .wavefoundry/framework/scripts/memory_eval.py:650-672, _policy_order with prefiltered); the summary is a truncated reviewer note. The whole repair is pinned by tests/test_memory_eval.py::MemoryEvalTests::test_empty_relevance_union_yields_zero_candidates, which asserts an empty relevance union admits zero.
Check flags: target_unresolved, target_not_canonical
Archived: 2026-11-25
Archive reason: Retired in the 244cm item 7 review, encoded in tests/eval/run_memory_eval.py no longer exists (logic is in .wavefoundry/framework/scripts/memory_eval.py:650-672, _policy_order with prefiltered); the summary is a truncated reviewer note. The whole repair is pinned by tests/test_memory_eval.py::Memor.
Archive path: `docs/agents/memory/archive/1theb-mem repaired-defect-fusion-empty-relevance-union-surfaces-unrela.md`

## Summary

Real defect fixed in wave 1tbt5: Repair verified complete: the query path admits zero candidates on an empty union, the baseline path is unrestricted via prefiltered=True, and the hermetic metrics and fingerprint reproduce unchanged. The blocking code-reviewer lane is cle…

## Evidence

- `fusion-empty-relevance-union-surfaces-unrelated-records`
- `ev-fusion-empty-relevance-union-surfaces-unrelated--3`
- `1tbt5`

## Targets

- `test_memory_eval.py`
- `.wavefoundry/framework/scripts/tests/eval/run_memory_eval.py`
