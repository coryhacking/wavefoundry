# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-30
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zf1y reload-restart-guidance`
Title: Reload Restart Guidance

## Objective

Make the upgrade guidance tell the truth about the in-process reload (tool layer only; `loaded_code_stale` means restart) and stop the staleness check flagging the implementation module after a reload re-executes it. Found on three 1.28.0 test builds.

## Changes

Change ID: `1zf1x-bug reload-leaves-modules-stale`
Change Status: `complete`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, docs-contract-reviewer

Completed At: 2026-09-30

## Wave Summary

Wave `1zf1y` (Reload Restart Guidance) delivered one change: Upgrade Guidance Treats an In-Process Reload as Complete When Modules Stay Stale. Notable adjustments during implementation: Upgrade Guidance Treats an In-Process Reload as Complete When Modules Stay Stale: Reverification of DEL-1ZF1Y-BYTECODE-IDENTITY (independent, Opus, scratch): RESOLVED. The full-implementation reproduction runs the old bytecode and records the new hash with the repair reverted, and runs the new source with a matching hash with it in place; unchecked-hash pycs are covered by the deletion, checked-hash pycs revalidate, a pycache prefix set before import is covered, and an undeletable cache records nothing. Hardening taken for its two residual gaps (another non-`-B` process rewriting a stale pyc between unlink and reload; the pycache prefix changing after import): after the reload, `_bytecode_cache_absent` requires the reloaded module's own `__spec__.cached` to be absent (nothing writes it under `-B`) or nothing is recorded; test added, its mutant fails; Upgrade Guidance Treats an In-Process Reload as Complete When Modules Stay Stale: Post-approval review (DEL-1ZF1Y-BYTECODE-IDENTITY): a timestamp `.pyc` stays valid when replacement source has the same size and whole-second mtime, and `-B` does not stop Python reading it, so the reload could execute old bytecode while the before/after source digests matched, marking unexecuted source current. Repaired: `_discard_reloaded_bytecode` removes the implementation module's `__spec__.cached` before the reload so the reload compiles the source it reads, and the entry is recorded only when no bytecode cache remains (unlink failure or a lingering cache records nothing). Windows, macOS, Linux and WSL2 identical (a cache file delete). Tests: a real module with a same-size, same-mtime rewrite shows the stale `.pyc` really is executed on this interpreter; discarding makes the reload run the current source; a cache that cannot be removed is reported; a reload whose executed bytes are unknown records nothing and stays stale. Mutants: gate removed, no unlink, discard after the digest; all caught; Upgrade Guidance Treats an In-Process Reload as Complete When Modules Stay Stale: Delivery review (independent, Opus): all lanes and seats APPROVE, no build-changing defect; 6 mutants all killed; patching `capture_loaded_identity` confirmed a faithful oracle (`assess_setup` calls the same function and compares with `!=`). Advisories taken: A1, digest `wf_server/server_impl.py` before and after the reload and record only on a match (`_reloaded_source_digests`), so a file rewritten while the reload read it is never marked current (test added; the no-match-check mutant fails it); A2, the guidance sentence now says modules the server already imported keep their launch version so the process can run a mix of old and new code (the tool-path `_load_script` copies do refresh lazily), in both files and the CHANGELOG; A3, a test pins the cleanup next step. Full suite 10178 OK before these.

**Changes delivered:**

- **Upgrade Guidance Treats an In-Process Reload as Complete When Modules Stay Stale** (`1zf1x-bug reload-leaves-modules-stale`) — 4 ACs completed. Key decisions: Re-record the reloaded entries after a reload instead of dropping them from `SOURCE_FILES`; Keep the in-process reload and correct the guidance
## Watchpoints

- Watchpoint: seed 160 and the prompt twin are edited by hand under `seed_edit_allowed`.
- Watchpoint: the reload must stay never-fail; re-recording is best-effort.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1ZF1Y-BYTECODE-IDENTITY | do_now | no | completed | — |

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
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Focused independent follow-up — 2026-09-30: REQUEST CHANGES** (`DEL-1ZF1Y-BYTECODE-IDENTITY`, code-reviewer). Matching source hashes around `importlib.reload` do not establish which bytes Python executed: inherited timestamp-based bytecode remains acceptable when replacement source has the same size and integer mtime, including under `-B`. A temporary copy of the full current implementation module executed its old marker while the source held the new marker; public `perform_mcp_reload` returned `ok` and recorded the new source digest. The coordinator independently replayed this result. A smaller loader fixture also reached real `assess_setup`: omitting the new refresh preserved `loaded_code_stale`, current code suppressed it while executing old bytecode, and bypassing the old bytecode loaded the new marker. Repair must establish executed-source provenance before recording it current, with a regression test using actual source and bytecode. No live server, repository code, or home cache was changed.
- Follow-up verification: QA independently ran all seven `ReloadedSourceIdentityTests` without skips and killed omit-refresh and refresh-indexer controls; the code lane killed omit-refresh and omit-before/after-match controls. The tests simulate changed digests and do not cover bytecode provenance. The coordinator verified four identical guidance sentences and both catalog restart conditions; docs validation is green and the close preview proves the current 10,180-test receipt. The Wave Summary still says two re-executed files although the implementation refreshes one (editorial advisory). Reviewed Git blobs: `server.py` `e35cbe30d19d743ed13fb377b360610a512e9ac7`, `test_server_tools.py` `96c8dcebb21dafd9a09be771c8c755573fc65ad7`, `upgrade_handlers.py` `34de2ef27c84ea60839023d34a99894afa181ab8`; fingerprints did not move. Existing reviewer contexts were reused, with no implementation participation; this is an independent follow-up, not a fresh-context approval. No full-suite rerun or native Windows execution. Existing reviewer capability was sufficient for bounded code/QA probes; model and effort overrides were not used.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: re-recording only the implementation module's copy would be overwritten by the runner on the next reload and leave runner-side assessments stale; resolved by updating the runner global in place before the handler is built; strongest-alternative: always require a host restart after an upgrade, rejected because `loaded_code_stale` already says precisely when one is needed)
- Prepare council seat evidence (2026-09-30): red-team blocked on the identity-object gap, now in Requirement 2; docs-contract-reviewer approved (three seed locations and the twin equivalents identified; seed line 43 phrasing reused).

- **Delivery-phase Wave Council [delivery-council] — 2026-09-30: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: a file rewritten between the reload's read and the fresh hash would be marked current and under-report staleness; closed by requiring the same digest before and after the reload; strongest-alternative: also mark the lazily re-executed `_load_script` copies current, rejected because their imports and the public imports stay old, so it could under-report; disagreements: none)
- Delivery council seat evidence (2026-09-30): red-team approved with advisories A1 and A2, both taken; docs-contract-reviewer approved (new sentence identical in seed and twin, no remaining reload-is-enough text).

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 16 | 6,147 |
| implement | 6 | 0 |
| review | 76 | 808,495 |
| **Total** | **98** | **814,642** |

<!-- wave:context-efficiency-state {"generation":102,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":6,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-320,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":50,"response_debit":270,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":16,"content_source_credit":14549,"derived_artifact_credit":2205,"direct_net":6147,"estimated_tokens_saved":6147,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1475,"response_debit":18345,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9213},"review":{"calls":76,"content_source_credit":1017390,"derived_artifact_credit":2160,"direct_net":808495,"estimated_tokens_saved":808495,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10707,"response_debit":202664,"source_credit_count":45,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":98,"content_source_credit":1031939,"derived_artifact_credit":4365,"direct_net":814322,"estimated_tokens_saved":814642,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12232,"response_debit":221279,"source_credit_count":55,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11529},"wave_id":"1zf1y reload-restart-guidance"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 5 | 0 | 4 | 4,336,975 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":4336975,"surfaced_events":5} -->
<!-- wave:exploration-avoided end -->
