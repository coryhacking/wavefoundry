# Decision: OPERATOR DECISION on Requirement 5: close verifies the exis…

Owner: Engineering
Status: active
Last verified: 2026-09-01

Memory ID: `1wv6w-mem decision-operator-decision-on-requirement-5-close-verifies-t`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-01
Updated: 2026-09-01
Source exploration cost: 125943
Source event: `decision-log:1wuui-enh acceptance-criteria-locality-and-gate-scope:877a58d9a7b533e5`
Validation: promote
Validated by: agent
Action delta: When a plan asserts that no artifact exists for a requirement, check the tree before designing a replacement: the framework test receipt already existed and was hash-bound, and the operator's challenge to the contrary claim is what produced the close gate this wave shipped.
Validation rationale: Evidence followed: the 1wuui Decision Log row recording the operator decision on Requirement 5 and the alternatives it rejected (running the suite at close, a new receipt format, lane review alone), and the delivered _framework_test_receipt_status in server_impl.py which reuses run_tests.py's own _hash_inputs. Current targets verified: build_pack.py and indexer.py still carry the exclusion-list references the row cites, and the gate is documented in AGENTS.md, seed 190, and the close prompt. The decision itself is canonical now; the memory supplements it with the operator challenge and the rejected alternatives, which no canonical surface records.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
## Summary

Decision (wave 1wur7): OPERATOR DECISION on Requirement 5: close verifies the existing `test-cache.json` receipt (green plus current `inputs_hash`) rather than running the suite, inventing a receipt format, or relying on lane review alone.. Rationale: The receipt already exists and is already hash-bound: `run_tests.py` writes `inputs_hash` over every file under `.wavefoundry/framework/` except packaging artifacts and the cache itself, so it self-invalidates on any framework change, which is exactly the staleness binding a close-time check needs. Nothing outside `run_tests.py` reads it today (the only other references are `build_pack.py` and `indexer.py` exclusion lists), so the requirement is a read, not a build. This keeps the whole-suite requirement machine-visible as it leaves the ACs, at no wall-clock cost. An earlier draft of this analysis asserted no receipt existed; the operator challenged it and the challenge was correct..

## Evidence

- `1wuui-enh acceptance-criteria-locality-and-gate-scope`
- `1wur7`

## Targets

- `build_pack.py`
- `indexer.py`
