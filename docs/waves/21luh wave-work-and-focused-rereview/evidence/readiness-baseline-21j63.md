# Readiness baseline: 21j63

Owner: Engineering
Status: active
Last verified: 2026-10-25

## Scope and method

Captured at planning time for wave 21luh from the closed 21j63 ledger via `wf_review_event(event='list', wave_id='21j63', verbose=true)`: 125 records, no truncation. Count `review_policy_receipt` separately from `executable_evidence` with `claim_kind=approval` and `approval_phase=readiness`. Do not filter the generic `phase` field: these approvals carry `phase=delivery` while their explicit `approval_phase` is readiness.

Source: `docs/waves/21j63 intent-fit-review/events.jsonl`. SHA-256 at capture: `559f083c9c193d892026088ad11babb8584428d6140148ae21fc24217efa4472`. This baseline retains identifiers/counts, not raw transcripts or duplicated full evidence. Read-only SQLite observation used `.wavefoundry/logs/context-efficiency.sqlite` with `mode=ro`.

## Exact ledger counts

- 12 published receipts: one initial and 11 superseding transitions.
- 34 readiness approval records across 9 receipt groups; 3 receipts received none.
- 4 distinct signoff lanes. Defining repeat submission as every readiness approval after that lane's first gives 30 repeated approvals. This is not 30 complete reviews, and not proof that all 30 were avoidable.
- Reviewer rounds cannot be equated with receipt transitions: some have no approval and some contexts cover several lanes. Context identifiers below preserve the grouping without manufacturing human/agent sessions or elapsed time.

| Receipt | Supersedes | Readiness approvals | Contexts |
| --- | --- | ---: | --- |
| `review-policy-d62e9305fbe36969defc` | none | 0 | none |
| `review-policy-e6ed682f4bb62ecfc104` | `review-policy-d62e9305fbe36969defc` | 3 | `21j63-readiness-docs-contract`, `21j63-readiness-code-reviewer`, `21j63-readiness-council` |
| `review-policy-60be91fc30f22b74f013` | `review-policy-e6ed682f4bb62ecfc104` | 0 | none |
| `review-policy-ef8a675f814b686dd6fe` | `review-policy-60be91fc30f22b74f013` | 3 | `docs-contract-21kk5-readiness-fv1`, `qa-21kk5-readiness-fv1`, `code-21kk5-readiness-fv1` |
| `review-policy-0e601d2a38fb888a72fe` | `review-policy-ef8a675f814b686dd6fe` | 4 | `docs-contract-21kk5-readiness-fv2`, `qa-21kk5-readiness-fv2`, `code-21kk5-readiness-fv2`, `council-21kk5-readiness-fv2` |
| `review-policy-5aca9cb13c9706c5e229` | `review-policy-0e601d2a38fb888a72fe` | 4 | `docs-contract-21kk5-readiness-fv3`, `qa-21kk5-readiness-fv3`, `code-21kk5-readiness-fv3`, `council-21kk5-readiness-fv3` |
| `review-policy-ca400848997119c715da` | `review-policy-5aca9cb13c9706c5e229` | 4 | `docs-contract-21kk5-readiness-fv4`, `code-21kk5-readiness-fv4`, `qa-21kk5-readiness-fv4`, `council-21kk5-readiness-fv4` |
| `review-policy-0e8d767e244f5fc35493` | `review-policy-ca400848997119c715da` | 4 | `docs-contract-21kk5-readiness-fv5`, `qa-21kk5-reverify-ac1`, `code-21kk5-reverify-currency-readiness`, `council-21j63-readiness-final` |
| `review-policy-e2c1610d15f1601ae89f` | `review-policy-0e8d767e244f5fc35493` | 4 | `docs-contract-21kk5-readiness-fv6`, `code-21kk5-readiness-fv6`, `qa-21kk5-readiness-fv6`, `council-21j63-readiness-fv6` |
| `review-policy-9b90e2a62b20bef9c05f` | `review-policy-e2c1610d15f1601ae89f` | 4 | `21j63-ir1-focused-readiness-20261025` |
| `review-policy-53ead68b1b5120cd4823` | `review-policy-9b90e2a62b20bef9c05f` | 0 | none |
| `review-policy-29221440c61a25e8f33b` | `review-policy-53ead68b1b5120cd4823` | 4 | `21j63-roster-guidance-readiness-20261025` |

## Available telemetry and limits

At capture: generation 434, sealed=true, compacted_generation=434; raw telemetry_event rows for this wave: 0. The close-time compactor retains cumulative published totals and removes raw per-call events. Thus per-round tool usage, elapsed reviewer effort and model tokens cannot be recovered from this store. Do not infer them from context-avoidance estimates or divide aggregate totals by approval counts.

| Stage | Recorded calls | Request debit proxy | Response debit proxy |
| --- | ---: | ---: | ---: |
| plan | 68 | 3008 | 125074 |
| implement | 91 | 2845 | 78922 |
| review | 277 | 56450 | 599474 |
| total | 436 | 62303 | 803470 |

These are stage aggregates covering more than re-readiness. Debits are the existing UTF-8/4 accounting estimates, not billed model tokens, wall-clock reviewer time or measured savings. No per-round effort baseline is claimed. The existing `context_efficiency.compact_published_wave` behavior and read-only store observation agree on that limitation.

## Prospective comparison

Observe the first three later waves that actually require renewed readiness after this feature ships. Record each changed contract's scope/size, receipt transitions, approvals by lane, independently identified material changes and whether the brief omitted any, whether the assessment changed a decision, additional retrieval calls when attributable, and measured effort only when available. Preserve compact observations before normal close-time telemetry compaction; do not retain transcripts or change store retention. Note shared reviewer contexts, missing data and workload differences. The expected improvement is less reconstruction effort with equally complete review, not fewer mandatory approvals. Use the bounded matched reconstruction exercise for a controlled completeness/content comparison; later waves provide observational evidence, not causal proof.

## Reproduction

Repeat the read-only typed ledger listing; group receipt and approval records with the predicates above. For telemetry, read `wave_state` generation/sealed/compacted_generation/published_json and count `telemetry_event` rows with wave_id `21j63 intent-fit-review` using a read-only SQLite connection. Missing local telemetry on another host means unavailable, not zero effort. Existing 21j63 wave records retain the aggregate checkpoint.

## Bounded reconstruction exercise (21luh)

The registered `ReceiptSnapshotPublicIntegrationTests` fixture defines its oracle independently of attribution helpers: R1 Scope=alpha / Constraints=loose; R2 Scope=beta / Constraints=loose; R3 Scope=beta / Constraints=strict plus routine checkbox and Progress Log tracking. Code last approved R1; Council last approved R2. Both the structured brief and the captured full-plan reference route returned Scope+Constraints for code and Constraints only for Council. Tracking was absent from substantive differences. A latest-pair-only mutant failed the code-lane assertion; Prepare-only snapshot and live-reread substitution mutants also failed their public tests.

Executed with `env -u PYTHONPYCACHEPREFIX PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests /Users/coryhacking/.wavefoundry/venv/bin/python3 -B -m unittest test_server_tools_lifecycle.ReceiptSnapshotPublicIntegrationTests`: six tests passed, zero skips (2.186 seconds). The local interpreter path is an observation of this run, not a portable requirement.

| Scripted route | Calls/content observed |
| --- | --- |
| Structured review | One registered review call; brief 4,152 UTF-8 bytes, complete review response 13,025 bytes |
| Full-plan reference | Three captured plan reads (670/669/724 characters; response bytes 1,087/1,086/1,142), plus one ledger read (16,225 response bytes) |

These are synthetic reconstruction proxies, not billed tokens, reviewer effort or causal savings. R1/R2 full-plan reads were captured at approval time; later retention/re-reading is unknown. The structured route still offers full plans and evidence. No actual reviewer decision, later-wave outcome, native Windows qualification or transport subprocess was measured. The first-three-later-waves observation procedure above remains necessary. The reproducible tests and this bounded result are durable; routine runner captures remain disposable.
