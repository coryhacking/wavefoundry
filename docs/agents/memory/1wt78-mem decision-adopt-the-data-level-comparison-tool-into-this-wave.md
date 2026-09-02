# Decision: ADOPT the data-level comparison tool into this wave (Requir…

Owner: Engineering
Status: rejected
Last verified: 2026-09-01

Memory ID: `1wt78-mem decision-adopt-the-data-level-comparison-tool-into-this-wave`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-01
Updated: 2026-09-01
Source exploration cost: 125943
Source event: `decision-log:1wtpl-bug retrieval-eval-store-identity-binding:9436403ff5fcc524`
Validation: reject
Validated by: agent
Action delta: No durable action: the adoption is complete, the tool's role as disclosure rather than a signed receipt is stated in docs/contributing/review-and-evals.md and in the tool's own docstring, and the commit obligation that carries it is recorded in the wave record and the handoff.
Validation rationale: Evidence followed: the 1wtpl Decision Log row and Requirement 4. Current target verified: benchmarks/compare_retrieval_receipts.py exists (untracked, named in the commit obligation) with the updated docstring. The decision was wave-local scope accounting; everything a future agent needs is on canonical surfaces, so a memory record would duplicate them.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1wur7): ADOPT the data-level comparison tool into this wave (Requirement 4). `benchmarks/compare_retrieval_receipts.py` stays where wave `1wpif` wrote it and is declared by this wave, so the requirement's subject is present in the repository rather than dependent on a paused wave's commit. Its docstring is updated: the blocker it was written for is repaired here, so it now documents the residual case (a comparison across two `evaluator_identity` values, which the compatibility rule binds unconditionally and by design).. Rationale: `1wpif` is paused and its close is blocked on a foreign wave's uncommitted change document, so sequencing behind its commit would hand this requirement's satisfiability to a third party. The tool is small, self-contained, imports nothing from `retrieval_eval`, and labels its output `computed`; nothing about adopting it changes `1wpif`'s own record..

## Evidence

- `1wtpl-bug retrieval-eval-store-identity-binding`
- `1wur7`

## Targets

- `benchmarks/compare_retrieval_receipts.py`
