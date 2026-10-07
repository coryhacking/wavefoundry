# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zxo0 path-and-id-containment`
Title: Path And Id Containment

## Objective

Validate change ids read from wave records against one allow-list and contain every member-doc read inside the repository, and harden the journal migration, vendored-script check and extension provenance paths, so a crafted record or README cannot read or reveal files outside the repository.

## Changes

Change ID: `1zxns-bug change-id-and-path-containment`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-07

## Wave Summary

Wave `1zxo0` (Path And Id Containment) delivered one change: Change-Id Allow-List and Path Containment for Record, Journal, Vendor and Provenance Paths. Notable adjustments during implementation: Change-Id Allow-List and Path Containment for Record, Journal, Vendor and Provenance Paths: Composition with wave A (1zxnz): wave A's `_read_repo_text_checked` lives in `server_impl` and `lifecycle_gate_support` cannot import the server, so `_read_member_doc_bytes` applies the same runtime-lock rule itself. A `.md` member doc can never match the lock name test, and the helper refuses a regular file whose `(st_dev, st_ino)` is that of a `*.lock` under `.wavefoundry/` (checked only when `st_nlink > 1`, using `stat` alone, the identity half of `_is_runtime_lock_path`). No lock file is opened. `_resolve_change_doc_matches` (single-id lookup, out of scope) keeps wave A's checked read unchanged.; Change-Id Allow-List and Path Containment for Record, Journal, Vendor and Provenance Paths: Fixture ids moved to canonical ids where tests drive lifecycle tools (`test_server_tools_lifecycle.py`, `test_dashboard_server.py`, `test_memory_records.py`, `test_record_layout_lifecycle.py`, `test_record_discovery_fail_closed.py`); lint-negative ids kept. Message expectations updated in `test_change_kinds.py`, `test_docs_lint.py`, `test_change_doc_checklist.py`; census allowlists updated in `test_label_reader_census.py`, `test_record_layout_census.py`; the bulk `wf_get_change` advisory site added to the sanctioned advisory set. Handler-digest fixture and tool-surface goldens unchanged (no `@mcp.tool` wrapper edited).; Change-Id Allow-List and Path Containment for Record, Journal, Vendor and Provenance Paths: Mutation probes (scratch, each restored): allow-list always true, unfiltered extraction, path-helper assertion removed, repository containment removed, cap removed, `lstat` regular check removed, close-gate `change id` branch removed, positional status pairing, plain bulk read, unconfined dashboard read, plain `wf_add_change` probe read, `wf_remove_change` shape check removed, absolute provenance fallback, lint message echoing the value, open-records message echoing the value: 15 of 15 caught. ws-2 and ws-3 probes are listed in their rows' reports (6 and 8, all caught).

**Changes delivered:**

- **Change-Id Allow-List and Path Containment for Record, Journal, Vendor and Provenance Paths** (`1zxns-bug change-id-and-path-containment`) — 16 ACs completed. Key decisions: Allow-list on the kind *shape*, not the live `CHANGE_KINDS` list.; A bad member line is filtered at extraction, blocks phase gates, is advisory in bulk `wf_get_change`, and is otherwise omitted; recovery is a hand edit of the record line.
## Watchpoints

- Watchpoint: sequencing and shared files below; follow-up items go to later waves, not this one.
- Second of five sequential waves; lands after 1zxnz and before 1zyb2 (which moves the vendored check into a shipped module).
- Public repository: describe defect classes only, no reproduction steps.
- Follow-up (delivery re-verification): docs-lint passes other than the wave-owned-doc loop (scaffolding integrity, migration edges, the shared lint text reader) still follow a linked member doc and block on a non-regular one; a regular-file guard in the shared lint reader is the likely single fix. Also: the vendored check's malformed-row and package/source messages echo README text, and the control-character check does not cover Unicode format characters.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | maybe_later | no | pending | — |
| DEL-2 | do_now | no | pending | — |
| DEL-3 | do_now | no | pending | — |
| DEL-4 | maybe_later | no | pending | — |
| DEL-5 | maybe_later | no | pending | — |

*Machine review state — 5 findings; current: do_now 2, maybe_later 3, dont_do_later 0, not_issue 0*
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
| plan | 13 | 12,159 |
| implement | 8 | 3,553 |
| review | 16 | 58,755 |
| **Total** | **37** | **74,467** |

<!-- wave:context-efficiency-state {"generation":37,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":8,"content_source_credit":6278,"derived_artifact_credit":0,"direct_net":3553,"estimated_tokens_saved":3553,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":25,"response_debit":2700,"source_credit_count":5,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":13,"content_source_credit":31586,"derived_artifact_credit":1566,"direct_net":12159,"estimated_tokens_saved":12159,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1970,"response_debit":22831,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3808},"review":{"calls":16,"content_source_credit":93615,"derived_artifact_credit":1271,"direct_net":58755,"estimated_tokens_saved":58755,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5605,"response_debit":32910,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2384}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":37,"content_source_credit":131479,"derived_artifact_credit":2837,"direct_net":74467,"estimated_tokens_saved":74467,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7600,"response_debit":58441,"source_credit_count":41,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6192},"wave_id":"1zxo0 path-and-id-containment"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
