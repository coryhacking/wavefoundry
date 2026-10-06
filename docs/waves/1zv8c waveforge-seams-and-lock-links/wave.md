# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-05
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zv8c waveforge-seams-and-lock-links`
Title: Waveforge Seams And Lock Links

## Objective

Close the last concrete Waveforge requests before 1.29.0: a declared seam for a distribution's own skills (R3), an offline check of the vendored dashboard scripts against their pinned hashes, and a lock-holder check so a markdown link to a runtime lock cannot release it (the wave 1zv87 residual).

## Changes

Change ID: `1zv89-enh declared-extension-skills`
Change Status: `implemented`

Change ID: `1zv8a-enh offline-vendored-script-check`
Change Status: `implemented`

Change ID: `1zv8b-bug docs-link-releases-runtime-lock`
Change Status: `implemented`

## Participants

- Coordinator: main session
- Write-owning roles: implementer (one per change, sequential on shared files)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-10-05

## Wave Summary

Wave `1zv8c` (Waveforge Seams And Lock Links) delivered 3 changes: A Distribution Cannot Declare Its Own Skills, Vendored Dashboard Scripts Have No Offline Hash Check, and A Docs Link To A Runtime Lock Can Release The Lock. Notable adjustments during implementation: A Distribution Cannot Declare Its Own Skills: Implemented: `EXTENSION_SKILLS` (plain literal) and `skill_declaration_problems` in `mcp_tool_extensions` (stdlib-only; also refuses a `prompt_doc` with a backtick, control character, or empty or `.` segment, and YAML numbers including base-60 and `.inf`/`.nan`); renderer `declared_skill_problems` (adds the retired-path check) and `declared_skills`, validated in `_skill_output_destinations` so `preflight_agent_surface_paths` refuses before any write, re-checked in `render_skills`; `_thin_pointer_body(label=...)` keeps framework skills byte-identical; `wf_server_info` lists `skills` and `skill_problems`; test support `SHIPPED_DECLARATION`, profile `_VALIDATE_DRIVER` and the refusal-driver reset updated; spec, `layering-rules.md` row, `current-state.md` sentence and CHANGELOG Added bullet; Vendored Dashboard Scripts Have No Offline Hash Check: Implemented: `offline_problems`, `unlisted_scripts` and `verify_offline` with `--offline` (exit 0/1/2); `OfflineCheckTests` (10) including a no-request proof; `build_pack._check_vendored_scripts` at the top of `build_zip` (skipped when the tree has no vendor folder, as in mini-framework test fixtures); README documents the flag. Mutation probes killed: check call removed, hash comparison disabled, a real vendored byte changed, a stray `.js` added; A Docs Link To A Runtime Lock Can Release The Lock: Scan scope and bound: record roots from `unvalidated_record_roots` plus the archive root (recursive; an out-of-repository directory link is refused), `docs/` (recursive; an out-of-repository directory link is skipped), and the repository root's own entries (not recursive). Only link entries are resolved; in-repository directory links are followed with a visited set; a followed link never enters `.git` or `.wavefoundry/index`; `_LINK_SCAN_ENTRY_LIMIT = 50_000` listed entries refuses with `link_scan_limit` (this repository lists 3,170). Measured cost on this repository, macOS warm: scan median 17.2-17.3 ms (min 16.1, max 19.4); full acquire, scan and release median 17.7 ms, max 23.3 ms; within the 50 ms budget.

**Changes delivered:**

- **A Distribution Cannot Declare Its Own Skills** (`1zv89-enh declared-extension-skills`) — 4 ACs completed. Key decisions: Renderer-only declaration, outside `declared()`; Declared skills reuse the thin-pointer body and must not use the `wf-` prefix
- **Vendored Dashboard Scripts Have No Offline Hash Check** (`1zv8a-enh offline-vendored-script-check`) — 4 ACs completed. Key decisions: Reuse the README file table as the pinned source
- **A Docs Link To A Runtime Lock Can Release The Lock** (`1zv8b-bug docs-link-releases-runtime-lock`) — 4 ACs completed. Key decisions: Check at lock acquisition, not in each markdown reader; Detect hard links by the lock file's own link count
## Watchpoints

- Watchpoint: `wf_server/server_impl.py` is touched by 1zv89 (`wf_server_info` listing) and 1zv8b (refusal mapping, shared predicate); implement them sequentially or in disjoint regions.
- Watchpoint: 1zv89 and 1zv8b both edit `docs/architecture/layering-rules.md` and `docs/architecture/current-state.md`; edit them one after the other.
- All three changes add a bullet under `## [1.29.0]` in `CHANGELOG.md` (Added, Added, Security); one owner edits it last.
- The `framework_script_census_problems` census from wave 1zv88 requires `EXTENSION_SKILLS` to be a plain literal on disk.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | completed | — |
| DEL-2 | do_now | no | completed | — |
| DEL-3 | do_now | no | completed | code-reviewer |
| DEL-4 | do_now | no | completed | code-reviewer |
| DEL-5 | do_now | no | completed | docs-contract-reviewer |
| DEL-6 | do_now | no | completed | qa-reviewer |
| DEL-7 | do_now | no | completed | — |
| DEL-8 | do_now | no | completed | code-reviewer |

*Machine review state — 8 findings; current: do_now 8, maybe_later 0, dont_do_later 0, not_issue 0*
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
| release-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
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
| plan | 30 | 59,929 |
| implement | 12 | 0 |
| review | 36 | 551,108 |
| **Total** | **78** | **611,037** |

<!-- wave:context-efficiency-state {"generation":73,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":12,"content_source_credit":612,"derived_artifact_credit":1490,"direct_net":-548,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":689,"response_debit":1961,"source_credit_count":3,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":30,"content_source_credit":85795,"derived_artifact_credit":6312,"direct_net":59929,"estimated_tokens_saved":59929,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3513,"response_debit":32474,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3809},"review":{"calls":36,"content_source_credit":693039,"derived_artifact_credit":1548,"direct_net":551108,"estimated_tokens_saved":551108,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14804,"response_debit":130991,"source_credit_count":66,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":78,"content_source_credit":779446,"derived_artifact_credit":9350,"direct_net":610489,"estimated_tokens_saved":611037,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19006,"response_debit":165426,"source_credit_count":93,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6125},"wave_id":"1zv8c waveforge-seams-and-lock-links"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
