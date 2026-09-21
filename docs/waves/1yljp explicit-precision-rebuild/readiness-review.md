# Explicit Precision Rebuild Readiness Review

Owner: Engineering
Status: active
Last verified: 2026-09-21

## Verdict

APPROVE against review-policy-adf153e47a9cb452c4d1. Two independent contexts: 1yljp-independent-readiness-20260921 covers red-team Council seat and code/QA lanes; 1yljp-architecture-docs-readiness-20260921 covers architecture lane and docs-contract Council seat. These are two contexts, not five separate reviews. Inherited model was selected for bounded state/compatibility judgment; observed runtime identity unknown.

## Evidence

The red-team/code/QA reviewer built a real temporary docs index through public build_index with deterministic embeddings. Same-class second update performed zero embedding batches; changing the predictor full to INT8 while full=False instead succeeded, embedded a batch and changed docs/code provenance. This is the known-bad control and uses no fabricated starting metadata, models, network or live corpus.

The architecture/docs reviewer independently ran PrecisionClassVersionTests.test_precision_class_change_forces_reembed and test_same_precision_class_no_reembed (2 tests, no skips, 1.558 seconds). The first confirms implicit INT8-to-full conversion expands docs to all and re-embeds; the adjacent same-class test is a no-op. This older test seeds metadata; delivery must use producer-built fixture state.

Both traced writer comparison, provider selection, actual embedding factory, final provenance stamping and query precision selection. A guard must inspect untouched siblings, distinguish explicit full from internal escalation, and recognize explicit full/int8 tokens without treating missing legacy provenance as known full.

## Bounded repair

One pass folded two clarifications from architecture/docs: setup_index.main's unconditional failed-epoch claim is false for a preflight refusal and must become truthful; chunking-and-indexing-pipeline.md has two automatic-conversion claims requiring updates. Both reviewers rechecked the repaired plan and approved. No unresolved findings.

The constructive alternative was preserving full precision on CPU. It requires coordinated factory/cache/identity changes and was rejected for this bounded repair. Silently mixing or relabeling vectors remains invalid. Existing schema settlement is not bypassed; this is preservation of a schema-current published snapshot, not a promise of no SQLite coordination files.

## Limits

Readiness only. Deterministic precision/provider seams represent hardware changes; no Windows machine, native GPU failure, live corpus rebuild or full suite was run. Delivery must prove both directions, scoped sibling and graph escalation, explicit-full and fresh CPU controls, refusal propagation, and guard-removal detection.
