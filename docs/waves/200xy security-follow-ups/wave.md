# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-07
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `200xy security-follow-ups`
Title: Security Follow Ups

## Objective

Close the follow-ups left by the five sequential waves 1zxnz to 1zyb4: every remaining docs-lint and single-id change-lookup reader of wave and plan documents applies the member-doc read rule, the vendored-script check stops echoing unvalidated table and server text, four upgrade and render edge paths gain a fix or evidence, the prompt-name and council-key changes are carried through to fresh installs and this repository's own config and generated text, and framework processes cache bytecode under `.wavefoundry/cache/` instead of recompiling or writing beside their sources.

## Changes

Change ID: `200v1-bug lint-and-vendored-check-echo-hardening`
Change Status: `implemented`

Change ID: `200v2-maint upgrade-and-render-edge-test-gaps`
Change Status: `implemented`

Change ID: `200xx-enh prompt-name-and-council-key-follow-through`
Change Status: `implemented`

Change ID: `1zyv1-enh project-local-bytecode-cache`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer, software-engineer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-07

## Wave Summary

Wave `200xy` (Security Follow Ups) delivered 4 changes: Lint and Vendored-Check Echo Hardening, Upgrade and Render Edge Test Gaps, Prompt-Name and Council-Key Follow-Through, and Project-local Python bytecode cache. Notable adjustments during implementation: Lint and Vendored-Check Echo Hardening: Implemented. Docs-lint: `helpers` record reader (identity-keyed cache, per-run refusal registry cleared by `read_text_cache_clear`, non-following `iter_markdown_docs`), `wave_validators.lint_wave_dirs` and non-following `_wave_folder_docs`, `check_plan_filenames`, orphan-ledger and scaffolding passes; the wave-owned-doc message is folded into the registry; `cli` emits the registry once in the full and `--changed` runs (the changed-set filter's drops join it). Secrets: non-following file set for record documents, record reads through the rule with the 5 MiB guard on `lstat` ahead of the read, refusals and dropped documents surfaced through `_record_scan_skip` and kept out of the scan cache (`_SCANNER_SKIPS_UNPUBLISHED`). Server: `_resolve_change_doc_matches` runs `_refuse_runtime_lock_target` then `_read_member_doc_bytes` (universal newlines kept, so a readable document is unchanged), a hard-linked lock refusal keeps `refused: True`, `_resolve_unique_change_doc` deleted; `_close_change_scoped_lint` also takes the registry. Vendored: field check for `package`, `source`, `url` (C0, C1, `Cf`), `Cf` in `_row_path_problem`, class-only redirect and download messages. Docs: cross-cutting-concerns bullet and the `wf_get_change` spec entry.; Lint and Vendored-Check Echo Hardening: Mutation probes in scratch (each restored after): lock check after the member read (lock and census tests fail); lookup through `read_text` (wf_get_change, get_change, resource_change subtests, FIFO and lock tests fail; `wf_add_change` refuses through its own probe either way); no `refused` on the hard-link lock refusal (fails); enumeration `lstat` to `stat` (EnumerationRuleTests fails); record reader bypassing the rule (fails); registry not emitted in the full run, in the `--changed` run, or not de-duplicated (each fails); cache keyed on a following `stat` (fails); cause class from `str(exc)` (fails; this probe found a real defect, now fixed: `MemberDocRefused` carries its cause in `strerror`); secrets file-set drop not surfaced, file set following, refusal cached as clean, size guard after the read (each fails); field check without C1/`Cf`, `Cf` path check removed, either registry message echoing the package, either redirect message echoing the target, `FetchError` with exception text (each fails).; Lint and Vendored-Check Echo Hardening: Full suite in a scratch copy (with the parallel 200v2 work in flight): first run 2 files red, both caused by this change (`test_vocabulary_census`: two edited docstrings dropped their allowlisted record-name literal, so the two stale allowlist entries were removed; `test_lifecycle_gates_structure`: three non-mock patches in the new test file gained `inert-by-design` notes). Rerun: 11636 tests across 168 files, OK. `wf_validate_docs` passed.

**Changes delivered:**

- **Lint and Vendored-Check Echo Hardening** (`200v1-bug lint-and-vendored-check-echo-hardening`) — 13 ACs completed. Key decisions: Route record-document reads through `_read_member_doc_bytes` via one lint helper, and make discovery non-following under the record roots only.; Refuse control and format characters in README fields at parse time.
- **Upgrade and Render Edge Test Gaps** (`200v2-maint upgrade-and-render-edge-test-gaps`) — 6 ACs completed. Key decisions: Load `history_paths` from the incoming framework for the preview.; Make the unlink message path-free while adding its test.
- **Prompt-Name and Council-Key Follow-Through** (`200xx-enh prompt-name-and-council-key-follow-through`) — 9 ACs completed. Key decisions: Skip profile-path writes while the manifest record is unreadable, rather than record at manifest creation.; Suggest the key's current shortcut for a default alias.
- **Project-local Python bytecode cache** (`1zyv1-enh project-local-bytecode-cache`) — 17 ACs completed. Key decisions: Operator decision: allow Python bytecode caching for the framework test runner and for running projects (MCP server, hooks, `wf` CLI, setup and index subprocesses). The cache lives inside the project's `.wavefoundry/` folder, is flushed on upgrade and is otherwise allowed. Source trees stay free of `__pycache__` by using `PYTHONPYCACHEPREFIX` / `sys.pycache_prefix`.; Location `.wavefoundry/cache/pycache/`
## Watchpoints

- Watchpoint: wave 1zyb4 closed and was committed in `404e4950`, which is this wave's base; every change's facts were re-verified against it.
- Watchpoint: shared files inside this wave: `render_agent_surfaces.py` (200v2, 200xx), `reconcile_scan.py` (200xx, 1zyv1), `server_impl.py` (200v1, and the 1zyv1 module-head guard), every module head converted by 1zyv1 (against all three others), and `render_platform_surfaces.py` plus the hook re-render (1zyv1) after the 200xx prompt updates. Serialization order: 200v1, 200v2, 200xx, then 1zyv1 last, with one final render.
- Watchpoint: one owner per shared root file: 1zyv1 writes the wave's CHANGELOG bullets under the existing `## [1.29.0]` heading (kept uncommitted as this repository's unreleased section) from the texts 200v1 and 200xx record in their Progress Logs, and makes the AGENTS.md edit.
- Public repository: describe defect classes only, no reproduction steps or sample values.
- Watchpoint: 200xx Requirement 4 (reconciled region strings) ships in this release (operator decision 2026-10-07), together with the council-key rename, so target waves are marked for re-Prepare once; the CHANGELOG discloses it.
- Follow-up: 200v2 AC-6 needs a Linux host and WSL2; without access it is marked `[~]` and stays a named follow-up.
- Follow-up: retiring the old council keys as tool input and Codex apply_patch gating stay out of this wave.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | completed | code-reviewer, docs-contract-reviewer |
| DEL-2 | do_now | no | pending | — |
| DEL-3 | do_now | no | pending | — |
| DEL-4 | do_now | no | pending | — |
| DEL-5 | do_now | no | pending | — |

*Machine review state — 5 findings; current: do_now 5, maybe_later 0, dont_do_later 0, not_issue 0*
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

- No external wave dependencies are declared; landing after wave 1zyb4 is a sequencing watchpoint (see Watchpoints).
- Intra-wave sequencing: the changes share files (see Watchpoints) and land in the order 200v1, 200v2, 200xx, 1zyv1; 1zyv1 runs last because it converts every module head, re-renders the hooks once and owns the final CHANGELOG and AGENTS.md pass.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 29 | 17,585 |
| implement | 51 | 26,980 |
| review | 84 | 2,253,939 |
| **Total** | **164** | **2,298,504** |

<!-- wave:context-efficiency-state {"generation":172,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":51,"content_source_credit":44727,"derived_artifact_credit":6949,"direct_net":26980,"estimated_tokens_saved":26980,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2936,"response_debit":23354,"source_credit_count":12,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1594},"plan":{"calls":29,"content_source_credit":47896,"derived_artifact_credit":2187,"direct_net":17585,"estimated_tokens_saved":17585,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2963,"response_debit":36039,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6504},"review":{"calls":84,"content_source_credit":2455046,"derived_artifact_credit":2760,"direct_net":2253939,"estimated_tokens_saved":2253939,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12201,"response_debit":194050,"source_credit_count":122,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2384}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":164,"content_source_credit":2547669,"derived_artifact_credit":11896,"direct_net":2298504,"estimated_tokens_saved":2298504,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":18100,"response_debit":253443,"source_credit_count":154,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10482},"wave_id":"200xy security-follow-ups"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 20 | 0 | 12 | 8,677,473 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":12,"estimated_exploration_avoided":8677473,"surfaced_events":20} -->
<!-- wave:exploration-avoided end -->
