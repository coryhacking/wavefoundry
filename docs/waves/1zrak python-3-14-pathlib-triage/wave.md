# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-04
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zrak python-3-14-pathlib-triage`
Title: Python 3 14 Pathlib Triage

## Objective

On Python 3.14, `pathlib` predicates return `False` instead of raising `OSError`, so framework guards that relied on the error to refuse an undetermined path may now pass it. When this wave closes, every affected call site is classified and every guard defect is fixed with a stat-based check that behaves the same on 3.11 through 3.14, before the Waveforge handoff.

## Changes

Change ID: `1zraj-bug python-3-14-pathlib-oserror-triage`
Change Status: `implemented`

Change ID: `1zu4y-bug python-3-14-discovery-lint-removal-fail-open`
Change Status: `implemented`

## Participants

- Coordinator: wave-council
- Write-owning roles: implementer
- Requested review lanes: security-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, release-reviewer, security-reviewer

Completed At: 2026-10-04

## Wave Summary

Wave `1zrak` (Python 3 14 Pathlib Triage) delivered two changes: Triage Framework Guards That Rely On Pathlib Predicates Raising, Which Python 3.14 Stopped Doing and Refuse Uninspectable Wave Roots, Lint Inputs And Removal Sources Instead Of Reading Them As Absent On Python 3.14. Notable adjustments during implementation: Triage Framework Guards That Rely On Pathlib Predicates Raising, Which Python 3.14 Stopped Doing: Scratch-copy and focused verification for the test-run task: the coordinator ran the full suite in a scratch copy on 3.14 (11,035 tests OK), and the touched test files ran focused on 3.14.8 and 3.13.16 after the delivery repairs. Two focused runs tripped the repository-change guard because another session added `docs/plans/1zu4y-bug python-3-14-discovery-lint-removal-fail-open.md`; they were rerun on a quiet tree.; Triage Framework Guards That Rely On Pathlib Predicates Raising, Which Python 3.14 Stopped Doing: Repaired after readiness review (F1 to F7, F9): one errno rule after `_authority_member_lstat`; AC-3 and Requirement 5 restated (stricter than 3.13 by design); census refreshed; AC-1 grouped table; sink-first AC-2 method; AC-6 follow-up recording; root skip and patched-`os.lstat` pins; AC-9 and `upgrade_wavefoundry.py` added.; Refuse Uninspectable Wave Roots, Lint Inputs And Removal Sources Instead Of Reading Them As Absent On Python 3.14: Amended per the coordinator's relay of the operator's no-follow-up direction: below-root discovery failures moved into scope (Requirement 4, code `record_folder_unreadable`, AC-14, AC-15), caller effects re-checked, legitimate-tree exclusions derived from `_list_subdirs` (nested: dot and symlink skip before stat; flat: `guarded=False` keeps both), `_has_wave_md` and the `MAX_DEPTH`/record-file descent rule in `walk_wave_candidates`.

**Changes delivered:**

- **Triage Framework Guards That Rely On Pathlib Predicates Raising, Which Python 3.14 Stopped Doing** (`1zraj-bug python-3-14-pathlib-oserror-triage`) — 9 ACs completed. Key decisions: Operator agreement on the three needs-decision sites: fix them in this release as `1zu4y-bug python-3-14-discovery-lint-removal-fail-open`, admitted to wave 1zrak, instead of deferring them.; Coordinator-approved delivery repairs (non-blocking review items): an uninspectable upgrade lock gets its own path-free refusal and is never treated as stale or rewritten (DEL-R1); `materialize_lifecycle_policy`'s parse and type refusals become path-free (DEL-R2); AC-9's recovery reads "then re-run the upgrade"; the Triage B5 reason and the `_prepare_council_verdict_locations` group are corrected; the reverts that only mode-0 pins kill are disclosed.
- **Refuse Uninspectable Wave Roots, Lint Inputs And Removal Sources Instead Of Reading Them As Absent On Python 3.14** (`1zu4y-bug python-3-14-discovery-lint-removal-fail-open`) — 18 ACs completed. Key decisions: Delivery repair DEL-U4 (coordinator-approved): `docs/architecture/decisions` is a prefix-source root of the mint, like the plans root, and refuses as `record_root_unreadable` with the restore-access recovery; Requirement 13 and AC-16 amended.; Delivery repair D2 (accepted by delivery review): in the flat layout an entry's own failed `lstat` refuses as `record_root_unreadable` naming the waves or archive root, the interpretation of Requirement 4(c).
## Watchpoints

- Framework edits need `framework_edit_allowed`, opened before the first edit and closed after.
- Pins must run on both 3.14 (`~/.wavefoundry/venv`) and 3.13 (`~/.wavefoundry/venv-py313-bak`, read-only); full suites only in scratch copies.
- Include `test_server_package` in every focused run (wave 1zqe4 lesson).
- AC-6 follow-ups need operator agreement; the operator chose to fix them in this wave as `1zu4y`.
- `1zu4y` edits `indexer.py`, `memory_backfill.py`, `review_policy_upgrade.py` and `CHANGELOG.md` after `1zraj`'s edits there have settled.
- `1zu4y` adds a `RecordLayoutInvalid` subclass; pin that an older upgrade runner's `_reload_in_place` still catches it.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-R1 | do_now | no | completed | — |
| DEL-R2 | maybe_later | no | completed | — |
| DEL-U1 | do_now | no | completed | — |
| DEL-U2 | do_now | no | completed | — |
| DEL-U3 | do_now | no | completed | — |
| DEL-U4 | do_now | no | completed | — |

*Machine review state — 6 findings; current: do_now 5, maybe_later 1, dont_do_later 0, not_issue 0*
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
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 75 | 0 |
| implement | 102 | 1,401,539 |
| review | 46 | 579,993 |
| **Total** | **223** | **1,981,532** |

<!-- wave:context-efficiency-state {"generation":225,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":102,"content_source_credit":1516929,"derived_artifact_credit":1147,"direct_net":1401539,"estimated_tokens_saved":1401539,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4484,"response_debit":118059,"source_credit_count":56,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6006},"plan":{"calls":75,"content_source_credit":149534,"derived_artifact_credit":1554,"direct_net":-10036,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5280,"response_debit":159653,"source_credit_count":17,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":46,"content_source_credit":724539,"derived_artifact_credit":4601,"direct_net":579993,"estimated_tokens_saved":579993,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":15605,"response_debit":135858,"source_credit_count":78,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":223,"content_source_credit":2391002,"derived_artifact_credit":7302,"direct_net":1971496,"estimated_tokens_saved":1981532,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25369,"response_debit":413570,"source_credit_count":151,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12131},"wave_id":"1zrak python-3-14-pathlib-triage"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 5 | 0 | 4 | 1,805,332 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":1805332,"surfaced_events":5} -->
<!-- wave:exploration-avoided end -->
