# Decision: OPERATOR DECISION on Requirement 5: close verifies the exis…

Owner: Engineering
Status: archived
Last verified: 2026-11-10

Memory ID: `1wv6w-mem decision-operator-decision-on-requirement-5-close-verifies-t`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-01
Updated: 2026-11-25
Source exploration cost: 125943
Source event: `decision-log:1wuui-enh acceptance-criteria-locality-and-gate-scope:877a58d9a7b533e5`
Validation: promote
Validated by: agent
Action delta: When a plan asserts that no artifact exists for a requirement, check the tree before designing a replacement: the framework test receipt already existed and was hash-bound, and the operator's challenge to the contrary claim is what produced the close gate this wave shipped.
Validation rationale: Evidence followed: the 1wuui Decision Log row recording the operator decision on Requirement 5 and the alternatives it rejected (running the suite at close, a new receipt format, lane review alone), and the delivered _framework_test_receipt_status in server_impl.py which reuses run_tests.py's own _hash_inputs. Current targets verified: build_pack.py and indexer.py still carry the exclusion-list references the row cites, and the gate is documented in AGENTS.md, seed 190, and the close prompt. The decision itself is canonical now; the memory supplements it with the operator challenge and the rejected alternatives, which no canonical surface records.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Checked at: 2026-11-25T16:09:21Z
Check note: Item 7 review: target gone or duplicate. The decision has shipped and is canonical. AGENTS.md 'Framework test receipt at close' and docs/contributing/build-and-verification.md:631 'Close gate: the framework test receipt' state that close verifies the existing test-cache.json receipt (ok result plus a current inputs_hash) and runs no suite. tests/test_server_tools_lifecycle.py:3505 test_close_resp.
Check flags: target_churn, target_not_canonical
Archived: 2026-11-25
Archive reason: Retired in the 244cm item 7 review, gone or carried by The decision has shipped and is canonical. AGENTS.md 'Framework test receipt at close' and docs/contributing/build-and-verification.md:631 'Close gate: the framework test receipt' state that close verifies the existing test-cache.json receipt (.
Archive path: `docs/agents/memory/archive/1wv6w-mem decision-operator-decision-on-requirement-5-close-verifies-t.md`

## Summary

Decision (wave 1wur7): OPERATOR DECISION on Requirement 5: close verifies the existing `test-cache.json` receipt (green plus current `inputs_hash`) rather than running the suite, inventing a receipt format, or relying on lane review alone.. Rationale: The receipt already exists and is already hash-bound: `run_tests.py` writes `inputs_hash` over every file under `.wavefoundry/framework/` except packaging artifacts and the cache itself, so it self-invalidates on any framework change, which is exactly the staleness binding a close-time check needs. Nothing outside `run_tests.py` reads it today (the only other references are `build_pack.py` and `indexer.py` exclusion lists), so the requirement is a read, not a build. This keeps the whole-suite requirement machine-visible as it leaves the ACs, at no wall-clock cost. An earlier draft of this analysis asserted no receipt existed; the operator challenged it and the challenge was correct..

## Evidence

- `1wuui-enh acceptance-criteria-locality-and-gate-scope`
- `1wur7`

## Targets

- `build_pack.py`
- `indexer.py`
