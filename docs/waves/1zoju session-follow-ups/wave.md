# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-03
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zoju session-follow-ups`
Title: Session Follow Ups

## Objective

Close five follow-ups left by waves `1zls7`, `1zls8` and `1zlu1`. When this wave closes, unhandled tool exceptions reach clients without absolute paths, and status drift between a wave record and its change documents is flagged and blocks close. A fenced `Depends On:` example no longer activates or gates a change, the dashboard counts done changes by the framework's one done set, and a stale helper reference after reload is reported.

## Changes

Change ID: `1zogm-bug fenced-depends-on-is-not-a-dependency`
Change Status: `implemented`

Change ID: `1zodx-enh wave-record-change-doc-status-drift-check`
Change Status: `implemented`

Change ID: `1zodw-bug unhandled-tool-exception-text-is-path-free`
Change Status: `implemented`

Change ID: `1zojt-enh stale-helper-reference-advisory`
Change Status: `implemented`

Change ID: `1zody-bug dashboard-done-statuses-from-lint-constants`
Change Status: `implemented`

## Participants

- Coordinator: Engineering (coordinating agent)
- Write-owning roles: implementer
- Requested review lanes: security-reviewer, architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer

Completed At: 2026-10-03

## Wave Summary

Wave `1zoju` (Session Follow Ups) delivered 5 changes: A Fenced Depends On Line Is Not A Dependency, Wave Record And Change Doc Status Drift Check, Unhandled Tool Exception Text Is Path-Free, Stale Helper Reference Advisory, and Dashboard Done Statuses From The Lint Constants. Notable adjustments during implementation: Wave Record And Change Doc Status Drift Check: Implemented: `member_status_drift` and `change_doc_header_status` in `wave_validators` (exact path, header-only, CRLF read as LF), a docs-lint WARNING for waves not closed or completed (also from an in-scope change document on incremental lint, reported once per run), the blocking `change_status_drift` close gate before close's writes and skipped for closed or completed waves, and `_detect_wave_status_drift` rebuilt on the detector; spec and CHANGELOG updated. Golden `lifecycle-gate-golden.json` regenerated: each of the 6 close captures gains one `change_status_drift` (the fixtures' change documents carry no header status); the extraction-golden comparison declares that addition. Close-success fixtures in `test_server_tools_lifecycle` and `test_phase_gates` now give their change documents a matching header status; Wave Record And Change Doc Status Drift Check: Readiness amendments F3 to F5: close gate skips already-closed waves; the gate is placed before close's own writes, and AC-4 stubs `run_garden`; drift figure corrected to 5; incremental lint warns via the in-scope change document; Unhandled Tool Exception Text Is Path-Free: Delivery repair F3 to F5: AC-4 reworded to name the upgrade-publication guard and state that the cost wrapper swallows its own recording errors by design (Decision Log row added; still `[x]`); the spec note now says a plain alias shares the canonical's rendered callable, so `data.tool` names the canonical tool, while a mapped alias names itself; spec and CHANGELOG say a crash is now a normal result whose JSON envelope carries `isError: true`, so the protocol-level `isError` reads false, as for every other error envelope. Follow-up: `wf_reload_mcp`, the only coroutine tool, is not rendered; it needs an async render variant.

**Changes delivered:**

- **A Fenced Depends On Line Is Not A Dependency** (`1zogm-bug fenced-depends-on-is-not-a-dependency`) — 7 ACs completed. Key decisions: Readiness amendment F11: the implement-wave parser takes fence flags over the whole wave text and ends `## Changes` only at an unfenced heading; Skip fenced `Depends On:` lines in every reader, but keep reading fenced status lines
- **Wave Record And Change Doc Status Drift Check** (`1zodx-enh wave-record-change-doc-status-drift-check`) — 8 ACs completed. Key decisions: Recheck N2: AC-7 and Requirement 3 now describe the real re-close contract (`ok`, `transitioned_to_closed: false`, handoff converges) and cite no test; Readiness amendment F3: the close gate applies only to waves not already `closed` or `completed`
- **Unhandled Tool Exception Text Is Path-Free** (`1zodw-bug unhandled-tool-exception-text-is-path-free`) — 9 ACs completed. Key decisions: Delivery repair F3: AC-4 names the upgrade-publication guard as the inner wrapper whose exception the test renders; Render centrally as a registration-time wrapper pass
- **Stale Helper Reference Advisory** (`1zojt-enh stale-helper-reference-advisory`) — 7 ACs completed. Key decisions: Recheck N6: each eviction replaces the retained list, which is cleared in a `finally` around the scan and in `register_mcp_surface`'s `except BaseException` block; Recheck N7, amended by delivery repair F2: (b) requires the new module to still bind the name (`n in vars(new)`), and skips every old binding whose name is a dunder (`__doc__`, `__file__`, `__spec__` and the rest of the import machinery) or whose value's exact type is `NoneType`, `bool`, `int`, `float`, `complex`, `str`, `bytes`, `tuple`, `frozenset`, `range`, `ellipsis` or `NotImplementedType`
- **Dashboard Done Statuses From The Lint Constants** (`1zody-bug dashboard-done-statuses-from-lint-constants`) — 6 ACs completed. Key decisions: Python imports `DONE_CHANGE_STATUSES`; JavaScript receives it in the snapshot; Use the done set, not the terminal set
## Watchpoints

- Watchpoint: serialize edits to `wf_server/server_impl.py` (1zogm, 1zodx, 1zodw, 1zojt) and to `wave_validators.check_wave_docs` (1zogm, 1zodx); no two of these changes edit either at the same time.
- Land 1zogm before 1zodx: both touch the consumers of the wave-record parser (`_parse_change_records`, the close paths, `check_wave_docs`).
- Land 1zodw last: it changes how every served-tool exception surfaces, which the other changes' tests observe.
- No retrieval receipt pair is owed: none of these changes alters ranking, indexing or retrieval.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1ZOJU-FENCED-SECTION-AND-STALE-FP | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| wave-council-delivery | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-10-03: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: 1zojt's stale-helper scan first read function and class metadata from vars(), where those descriptors do not live, so it could never report anything, and then retained evicted modules across a window a failed install could leave open; resolved by a namespace identity comparison with release on every install path; strongest-alternative: hold retained old modules in a WeakValueDictionary so a failed install needs no release code, not adopted because explicit release on both paths plus a weakref AC is simpler to test)
- Prepare council seat evidence (2026-10-03): one independent reviewer ran both seats and the code, qa, architecture and docs-contract lanes against the tree over three rounds; round one approved with F1 to F11 (1zodw outermost render pass, 1zodx re-close scope, 1zojt metadata reads as the medium items); round two blocked on N1 (1zojt metadata descriptors) and N2 (1zodx AC-7 cited an edit-gate test); round three approved every seat with N6 (release on a failed install) and N7 (dropped names) applied as specified.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 116 | 66,235 |
| implement | 72 | 29,279 |
| review | 64 | 1,439,207 |
| **Total** | **252** | **1,534,721** |

<!-- wave:context-efficiency-state {"generation":195,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":72,"content_source_credit":49604,"derived_artifact_credit":1501,"direct_net":29279,"estimated_tokens_saved":29279,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3856,"response_debit":24206,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6236},"plan":{"calls":116,"content_source_credit":108631,"derived_artifact_credit":7888,"direct_net":66235,"estimated_tokens_saved":66235,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5854,"response_debit":53643,"source_credit_count":32,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9213},"review":{"calls":64,"content_source_credit":1655464,"derived_artifact_credit":2963,"direct_net":1439207,"estimated_tokens_saved":1439207,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6663,"response_debit":214873,"source_credit_count":51,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":252,"content_source_credit":1813699,"derived_artifact_credit":12352,"direct_net":1534721,"estimated_tokens_saved":1534721,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16373,"response_debit":292722,"source_credit_count":95,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":17765},"wave_id":"1zoju session-follow-ups"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
