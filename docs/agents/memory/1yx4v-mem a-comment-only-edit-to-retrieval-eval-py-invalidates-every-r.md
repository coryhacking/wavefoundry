# A comment-only edit to retrieval_eval.py invalidates every receipt as a baseline

Owner: Engineering
Status: active
Last verified: 2026-09-25

Memory ID: `1yx4v-mem a-comment-only-edit-to-retrieval-eval-py-invalidates-every-r`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-09-25
Updated: 2026-09-25
Source exploration cost: 200863
Source event: `finding:1yxyw:DOCS-DEL-1`
Validation: promote
Validated by: agent
Action delta: Never edit retrieval_eval.py (not even a comment) between a baseline receipt and its after receipt; put evaluator comment edits in the evaluator step, and when a pointer must name the reference receipt, name one whose evaluator_identity.source_sha256 equals the shipped file.
Validation rationale: DOCS-DEL-1 (1yxyw delivery): retrieval_eval._evaluator_identity hashes raw source bytes, so a post-baseline comment-only edit (AST-identical) made the documented reference receipt e2c unusable as --baseline (invalid_baseline) and had already invalidated one E2 attempt. Repaired by recording e3 on the shipped bytes; reverified by the docs-contract lane. Generated summary had no actionable content, so rewritten.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

The evaluator identity is the sha256 of retrieval_eval.py's raw bytes, not its AST. In wave 1yxyw a comment-only edit after the E1 baseline invalidated an after-receipt attempt (invalid_baseline) and then made the documented reference receipt unusable for the shipped evaluator (DOCS-DEL-1), costing an extra receipt run and a review repair. Finish every evaluator edit, comments included, before recording the baseline; a reference receipt must carry the shipped file's sha256.

## Evidence

- `DOCS-DEL-1`
- `ev-docs-del-1-3`
- `1yxyw`

## Targets

- `.wavefoundry/framework/scripts/retrieval_eval.py`
