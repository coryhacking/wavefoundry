# Fragile: retrieval_eval.py

Owner: Engineering
Status: rejected
Last verified: 2026-09-02

Memory ID: `1wwa9-mem fragile-retrieval-eval-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-02
Updated: 2026-09-02
Source exploration cost: 2790236
Source event: `repeated-repairs:1wpif:retrieval_eval.py`
Validation: reject
Validated by: agent
Action delta: No durable action: neither cited finding repaired this file, so there is nothing for a future agent to do differently.
Validation rationale: Followed both cited findings in the ledger. The first was refuted rather than repaired, and its own repair record states that no production change was made in this wave. The second was a wave-record accuracy defect whose repair edited the wave record. Neither touched the evaluator module; it appears only as a place evidence was read. The file exists, so the target is current, but the fragility claim rests on citation counting rather than on repairs, and the remedy it proposes, re-running the full suite, is already the standing rule for every framework file.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

retrieval_eval.py required 2 separate repairs during wave 1wpif; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `PERF-DEL-6`
- `EVID-DEL-2`
- `1wpif`

## Targets

- `retrieval_eval.py`
