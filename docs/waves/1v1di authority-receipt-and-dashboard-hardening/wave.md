# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-11
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1v1di authority-receipt-and-dashboard-hardening`
Title: Authority Receipt And Dashboard Hardening

## Objective

Retire the residue the last two waves exposed at the review system's trust surfaces: the authority facade silently reclassifies a permission-unreadable declared wave as legacy prose with empty text (and crashes on the decode cause), the dashboard crashes on or hides exactly the broken records an operator opens it to investigate (wave records today, and the same crash class at its change-doc read), and the last two citation-rule carriers ship unpinned. Every premise was executed against the tree before planning and re-executed by the readiness council.

## Changes

Change ID: `1v1de-bug review-authority-downgrades-on-unreadable-wave-record`
Change Status: `implemented`

Change ID: `1v1df-bug dashboard-crashes-or-hides-unreadable-wave-records`
Change Status: `implemented`


Change ID: `1v1dh-debt implementer-and-author-citation-variants-unpinned`
Change Status: `implemented`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-08-11

## Wave Summary

Wave `1v1di authority-receipt-and-dashboard-hardening` (Authority Receipt And Dashboard Hardening) delivered 3 changes: Review Authority Silently Downgrades On An Unreadable Wave Record, The Dashboard Crashes On Or Hides Unreadable Wave Records, and The Implementer And Author Citation Variants Have No Pins. Notable adjustments during implementation: Review Authority Silently Downgrades On An Unreadable Wave Record: Readiness council (red-team and docs-contract seats): both facade premises re-executed independently (both causes probed; the decode escape and empty-text downgrade confirmed; the leak confirmed with the note that the decode message carries neither path nor filename). Council correction folded pre-receipt: the consumer census re-scoped from call sites to OBJECT FLOW, because the one consumer where a wrong result shape is fail-OPEN is not a call site: the close carve-out predicate in `_required_wave_council_signoffs` would drop the readiness key from the close roster if the unreadable result presented with empty `ledger_errors`. Requirement 2 and AC-4 now name the predicate and the safe shape; Review Authority Silently Downgrades On An Unreadable Wave Record: AC-5 corpus comparison executed THROUGH the facade per wave (not the 1v0lz ledger-only derive-states, which is vacuous for the facade): for every `docs/waves/*/wave.md` the script resolves `resolve_review_authority(root, wave_dir)` with the facade doing its own record read, and derives typed flag, `ledger_errors`, record count, `evidence_present`, `any_signoff_evidence`, `operator_signoff_present`, `max_severity`, and per-key `signoff_current`/`signoff_recorded` for both approval phases plus the prose prepare section across five canonical keys. Before side: byte-copy of the pre-edit working-tree scripts (taken before the first edit, since HEAD predates the uncommitted 1uzwi/1uzwh deliveries; the copy isolates exactly this change). Result: 215 waves (75 typed, 140 legacy), 6880 derived state fields, zero diffs, output byte-identical. File-scope verification: `tests.test_review_evidence` 156 tests OK, `tests.test_dashboard_server` 189 tests OK (1 environment skip), `tests.test_server_tools` 1680 tests OK in a single module run (338.9s); the wave-level suite row below carries the full-suite tally; The Dashboard Crashes On Or Hides Unreadable Wave Records: Readiness council (red-team and docs-contract seats): the sibling-collector claim was FALSIFIED by execution (a degraded entry carries `changes: []`, so the changes collector's join never runs on a real read; it inherits the pattern, not the defect), and the council found the actually reachable crash one function away: `parse_change_doc` wraps only `OSError`, so a decode-broken change doc crashes the snapshot by the identical mechanism. Rationale corrected; Requirement 3 widened to every raw filesystem touch on the render path (including `relative_to` and `stat` on the degraded path); AC-7 added for the change-doc crash; AC-3's red vehicle pinned to the decode fixture (a permission-only corpus is CWD-identical today, both variants executed).

**Changes delivered:**

- **Review Authority Silently Downgrades On An Unreadable Wave Record** (`1v1de-bug review-authority-downgrades-on-unreadable-wave-record`) — 6 ACs completed. Key decisions: Reuse the existing `authority_errors` fail-closed shape rather than a new result type
- **The Dashboard Crashes On Or Hides Unreadable Wave Records** (`1v1df-bug dashboard-crashes-or-hides-unreadable-wave-records`) — 7 ACs completed. Key decisions: Degrade per entry in the dashboard, mirroring `wf_list_waves`
- **The Implementer And Author Citation Variants Have No Pins** (`1v1dh-debt implementer-and-author-citation-variants-unpinned`) — 4 ACs completed. Key decisions: Pin head sentences exactly plus load-bearing clauses, rather than the full multi-paragraph seed-170 prose byte-exact
## Watchpoints

- Watchpoint (readiness-council removal): `1v1dg failed-prepare-supersedes-the-current-receipt` was admitted, WITHHELD by both council seats, removed, and withdrawn. Both seats independently established that wave `1usqm`'s `1upba` already executed and falsified this exact design space (its Requirement 6 froze the publication path as a hard boundary; candidates B and C are its executed-and-rejected alternatives verbatim; the observed churn loop cannot reproduce on the post-`1upba` tree because the refuse-on-pending-mint contract errors the dead re-record with attribution; `1v1dg` AC-1 could not go green without reversing two pinned `1upba` tests, one of them mutant-proven). The field feedback is resolved-by-`1upba`; the only unfalsified residual (binding approvals to the deterministic pending receipt id as an EXPLICIT renegotiation of `1upba`'s refusal contract, amending its AC-1/AC-6/AC-10 by name) is recorded as a future design seed, not planned work. Follow-up for planners: search closed-wave records, not only `docs/plans/`, for a defect's prior art.
- Watchpoint (no intra-wave write collisions remain): the three admitted changes touch disjoint code files (`review_evidence.py`/`server_impl.py` for `1v1de`; `dashboard_lib.py` for `1v1df`; `test_docs_lint.py` only for `1v1dh`).
- Watchpoint (follow-up, out of this wave's scope): the `1v1de` implementer's census found the same `{exc}` path-leak idiom repaired in `_review_authority_path_error` also present at `upgrade_wavefoundry.py` (`retired sidecar path is not safely resolvable: {exc}`, line 1937 today). Not touched here (outside the change's ownership and this wave's diagnostic scope); a future leak-idiom census change should sweep `upgrade_wavefoundry.py` alongside any other `f"...{exc}"` renderers of caught `OSError`s. The delivery red-team seat added a second member to that sweep list: `project_state_publication_lock` in `review_evidence.py` renders `{exc}` of `RuntimeLockBusy`/`RuntimeLockError` (OSError subclasses whose messages embed the absolute lock path), surfacing through the `ProjectPublicationUnavailable` handlers; lock acquisition, not a record read, so out of `1v1de` scope but in the same idiom class.
- Watchpoint (delivery-council residue, deferred to the parked rendering plan `1p30y`): change-level `read_error` has zero `dashboard.js` consumers today, so an unreadable change doc is UI-indistinguishable from a healthy doc lacking a status header; the cause is UI-visible only on wave rows. AC-7 holds at the snapshot-payload layer its tests assert on, per the change doc's Risks framing.
- Watchpoint (implementation outcome, 2026-08-11): all three changes implemented with every red demonstrated as specified; `server_impl.py` byte-identical through `1v1de` (facade-only fix, matching the census expectation); `1v1df` AC-5 re-executed as a paired same-corpus comparison after sibling-implementer doc churn contaminated the naive before/after; `1v1dh` pins red via scratch-tree seed mutations (failures, not skips).

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-11: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: both seats WITHHELD round one over 1v1dg, whose premise, two of three candidate mechanisms, and required AC-1 were contradicted by the executed record and pinned tests of wave 1usqm's 1upba (closed two days before planning); the moderator removed and withdrew the change, recorded the falsification chain and the single unfalsified residual in Watchpoints, corrected the stale session memory that seeded the plan, and folded the seats' repairs on the three surviving changes (object-flow census with the close carve-out predicate in 1v1de; the falsified sibling claim corrected and the reachable parse_change_doc crash added as required AC-7 in 1v1df; the attribution swap fixed in 1v1dh), after which both seats reverified to final APPROVE; strongest-alternative: for the residual post-1upba operator cost, pending-receipt-id binding as an explicit renegotiation of 1upba's refusal contract amending its AC-1/AC-6/AC-10 by name, recorded as a future design seed rather than planned work)

- **Readiness seat evidence [docs-contract-reviewer] — 2026-08-11:** round one WITHHELD: `1v1dg`'s premise, candidates B and C, and required AC-1 contradicted by wave `1usqm`/`1upba`'s executed record and pinned tests (independently re-derived from the closed wave record). On the surviving changes: `1v1df`'s sibling-behavior claim corrected against the executed dashboard census and the reachable `parse_change_doc` crash promoted to required AC-7; `1v1dh`'s lane-attribution swap (`1uzwh` vs `1uzwi`) corrected. Reverified after repairs: APPROVE.
- **Readiness seat evidence [red-team] — 2026-08-11:** round one WITHHELD over `1v1dg` on the same falsification chain (reached via the refuse-on-pending-mint contract's attribution error, executed on the post-`1upba` tree). On `1v1de`: demanded the object-flow consumer census with the close carve-out predicate named and the AC-5 comparison derived through the facade rather than the `1v0lz` ledger-only script; both folded into the change doc. Reverified after repairs: APPROVE.
- **Delivery-phase Wave Council [delivery-council] — 2026-08-11: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the docs-contract seat WITHHELD round one over checkbox honesty, the full-suite ACs in all three docs marked done with no named executed suite evidence anywhere in the record plus a dangling "recorded below" evidence pointer in 1v1de's AC-5 row; the coordinator repaired both with a shared suite-evidence Progress Log row in each doc (7129 tests across 62 files, rc=0 unpiped, docs-lint clean) and the concrete 1680-test module tally, after which the seat reverified against the tree to final APPROVE; strongest-alternative: the red-team seat demonstrated that additive negation slips past any substring pin, including the Decision Log's rejected full-paragraph byte pins, and judged the clause-pin trade-off correctly priced against the family's observed drift class)
- **Delivery seat evidence [red-team] — 2026-08-11:** all five attacks HELD, executed against live modules with scratch fixtures: the facade census re-derived at exactly six production call sites, all passing seam-read text; probe demonstrated the old silent-legacy shape satisfies the close carve-out predicate (dropping the readiness key) while the new typed-with-errors shape does not, so the fix is strictly less permissive at the one site where lenience was possible; the path-freedom sweep found the changed paths clean and identified the `project_state_publication_lock` lock-path renderers as a same-idiom carry-forward (recorded in Watchpoints); dashboard degraded rows carry the full healthy key set and the `WaveEvidence` tooltip renders diagnostics as an attribute with no HTML sink; the seed pins fail on head-sentence drift (executed red on a scratch copy) and tolerate only additive negation, inherent to any substring pin. APPROVE.
- **Delivery seat evidence [docs-contract-reviewer] — 2026-08-11:** round one verified every executable claim true (four test classes, both full modules, the full framework suite at 7129/62 rc=0, both censuses re-derived exactly, every cited anchor resolving, events-ledger corroboration of the readiness arc) and WITHHELD on two documentary findings: F1 (moderate) suite ACs without named executed suite evidence, F2 (minor) a dangling evidence pointer. Both repaired as specified; post-repair reverification confirmed the shared suite row terminates each Progress Log, the AC-5 row's forward reference resolves, and docs-lint returns clean with zero warnings. Final APPROVE.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 193 | 3,557,537 |
| implement | 198 | 3,964,238 |
| review | 79 | 1,787,340 |
| **Total** | **470** | **9,309,115** |

<!-- wave:context-efficiency-state {"generation":389,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":198,"content_source_credit":4492792,"derived_artifact_credit":262,"direct_net":3964238,"estimated_tokens_saved":3964238,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8061,"response_debit":524106,"source_credit_count":102,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3351},"plan":{"calls":193,"content_source_credit":3905938,"derived_artifact_credit":4403,"direct_net":3557537,"estimated_tokens_saved":3557537,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8246,"response_debit":350254,"source_credit_count":94,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":79,"content_source_credit":2015339,"derived_artifact_credit":1060,"direct_net":1787340,"estimated_tokens_saved":1787340,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5675,"response_debit":224730,"source_credit_count":55,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":470,"content_source_credit":10414069,"derived_artifact_credit":5725,"direct_net":9309115,"estimated_tokens_saved":9309115,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":21982,"response_debit":1099090,"source_credit_count":251,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10393},"wave_id":"1v1di authority-receipt-and-dashboard-hardening"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 19 | 0 | 9 | 9,941,341 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":9,"estimated_exploration_avoided":9941341,"surfaced_events":19} -->
<!-- wave:exploration-avoided end -->
