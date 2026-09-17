# Identity Delivery Review

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Scope and verdict

Independent code-reviewer, qa-reviewer and docs-contract-reviewer lanes found no actionable identity-delivery defects. Receipt selects those three lanes; no delivery council required. Each lane had a five-minute budget and used targeted tests per in-memory mutant, with no source edits. All reviewed source fingerprints stayed unchanged. No native Windows/Linux execution claimed. Unrelated memory implementation changes were excluded.

## Executed evidence

| Lane | Checks | Observation |
| --- | --- | --- |
| code-reviewer | Resolver + public integration + operator ledger tests; prepared receipt fixture and existing ledger regressions | 23 tests pass, zero skips after using the working Git binary on PATH |
| qa-reviewer | Public integration + prepared receipt fixture; resolver + operator ledger tests; 140 existing ledgers; independently recomputed framework receipt | 8 + 13 focused tests pass, zero skips; all ledgers valid and byte-preserved; current green receipt matches |
| docs-contract-reviewer | Seven public integration tests, real registered schema, spec bullet and seed row read against implementation | All seven pass; optional identity agrees with documented degradation, replay and role-authority boundaries |

## Mutation table

| Lane | In-memory mutation | Detection |
| --- | --- | --- |
| code-reviewer | Disable ambiguity guard | Ambiguous-email fixture fails |
| code-reviewer | Change Git timeout 10 to 11 | Bounded subprocess fixture fails |
| code-reviewer | Remove blank-handle guard | Invalid-map fixture fails |
| code-reviewer | Bypass nested operator validation | 28 invalid-shape subcases fail |
| code-reviewer / qa-reviewer | Drop public operator forwarding | Three event contexts lose identity and rendered attribution fails |
| docs-contract-reviewer | Omit mapped identity or invent unknown explicit identity | Direct public preview comparisons detect both false contract claims |
| docs-contract-reviewer | Add email to nested operator | Unknown-field validation rejects it |

No disk source mutants persisted. Full suite was run by the coordinator: 9147 tests, 17 skips, result ok. Each reviewer independently executed its stated focused checks; none claims an independent full-suite run. Fresh registration/reload exercised in fixtures; attached host reconnect remains a user-facing schema refresh concern.

## Frozen source identity

Framework receipt inputs_hash: `416da29caabc905cd8ecfa498133132b45467858290977f72fecceb2ae4a529a`.

Key git hash-object values (identical start/end):

- operator_identity.py: `e53b1d0277d9b455687eabe436163cb1bab144f9`
- review_evidence.py: `6a339648945706dff87f064ef55ad1ec13371a2a`
- server_impl.py: `21c208cfaacc501f5a568a3c0484e7370172c0d7`
- tests/test_review_operator_integration.py: `245cd8f9f93fa5a33ea76f4da89fedbc6189b903`
- seed209: `40bba674ebb2b8cc5c0056a73907c6b4b2ae050c`
- docs/specs/mcp-tool-surface.md: `41bb702e8e4c5ab3c3d62280c60d7057bad7ddff`
- docs/contributors.json: `175476f0f5afe9f70d6b9b227b57a55b92047510`

## Accounting correction

The operator requested correction before closure. One planning-stage source credit attributed 113050624 estimated tokens to binary `.wavefoundry/index/index.sqlite`. The exact row was changed to zero in one SQLite transaction; its key remains for deduplication. Original row, before/after totals, authorization and reason are preserved in [the correction record](context-accounting-correction.json). A fresh standard projection regenerated the wave table. No call debits or other source credits were changed.

At the correction instant the total changed from 116227832 to 3177208; intervening investigation/review calls explain the difference from the earlier 115714942 displayed snapshot. The remaining number is an estimate against whole-file reads, not measured model-token or monetary savings. Broader binary exclusion, measurement wording and auditable correction behavior belong to the separately requested estimator change, not this identity implementation.

## Retrospective

Contributor attribution can remain optional while review evidence remains strict: resolve once on new operations, pass metadata outside semantic identity, and preserve the stored bundle on replay. This is already canonical in seed209, the public tool spec and the admitted decision log; no duplicate durable memory is necessary. The accounting discovery is captured in the separate planned defect rather than generalized into a savings claim.
