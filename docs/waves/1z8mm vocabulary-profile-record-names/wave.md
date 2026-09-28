# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-27
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1z8mm vocabulary-profile-record-names`
Title: Vocabulary Profile Record Names

## Objective

<Describe the wave's load-bearing goal in 1–3 sentences — what changes in the project state when this wave closes, and why now. This text is displayed in the dashboard wave card.>

## Changes

Change ID: `1z826-feat vocabulary-profile-record-names`
Change Status: `complete`

Change ID: `1z8qi-feat vocabulary-profile-record-writers`
Change Status: `complete`
Depends On: `1z826-feat vocabulary-profile-record-names`

Change ID: `1z8qj-bug events-path-ignores-record-roots`
Change Status: `complete`

Change ID: `1z8qk-debt remove-dead-by-path-fallbacks`
Change Status: `complete`

Change ID: `1z8ql-enh discovery-ignores-fileless-folders`
Change Status: `complete`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

## Wave Summary

Wave `1z8mm` (Vocabulary Profile Record Names) delivered 5 changes: Vocabulary Profile for Record Names: Profile and Readers, Vocabulary Profile for Record Names: Writers and End-to-End Proof, Review Ledger Path Check Ignores Configured Record Roots, Remove Dead By-Path Import Fallbacks, and Discovery Diagnostic Ignores Folders Without Files. Notable adjustments during implementation: Vocabulary Profile for Record Names: Writers and End-to-End Proof: Implemented. Writers routed in `server_impl` (scaffold title, id line, member heading, summary heading and the scaffold's Dependencies prose; the change block and its missing-section path; the back-reference rewrite; `new_change`; the summary rewrite and the close-time `Completed At:` anchor). The legacy back-reference placeholders stay fixed text as `_LEGACY_BACKREF_PLACEHOLDERS` (census `retired_name`). The shipped template is localized at render (see Decision Log). The Stop hook imports the profile at runtime; this repository's hooks were re-rendered and only `.claude/hooks/session-capture.py` changed. The census pending-writer class is removed; Review Ledger Path Check Ignores Configured Record Roots: Implemented: the waves root and depth come from `record_paths.unvalidated_record_roots`, which never raises, so the first draft's fallback to a literal default root was removed (the record-layout census flagged it); Discovery Diagnostic Ignores Folders Without Files: Implemented: `record_paths._holds_a_file` (non-dot regular file, unlistable counts as none) filters candidates after the any-record check, which must come first because `_has_wave_md` follows a symlinked record that `_holds_a_file` skips. Delivery review: all lanes approved; D1 (the unlistable-folder test was vacuous on Python 3.13, where `Path.iterdir` also uses `os.scandir`) repaired by failing only the leaf's listing, with a control; D3 limit (a symlink-only renamed record stays silent) added to the docstring.

**Changes delivered:**

- **Vocabulary Profile for Record Names: Profile and Readers** (`1z826-feat vocabulary-profile-record-names`) — 6 ACs completed. Key decisions: Profile is a fork-edited module, not a `workflow-config.json` block (RFC open question 1; confirmed by the operator on 2026-09-27: "code module the way it works today"); Export fragments, not whole patterns
- **Vocabulary Profile for Record Names: Writers and End-to-End Proof** (`1z8qi-feat vocabulary-profile-record-writers`) — 4 ACs completed. Key decisions: Localize the shipped template's labels at render instead of adding placeholders to it (Requirement 2 revised during implementation); The generated close summary prose ("Wave ... delivered one change") stays as written
- **Review Ledger Path Check Ignores Configured Record Roots** (`1z8qj-bug events-path-ignores-record-roots`) — 4 ACs completed. Key decisions: Position-only, root from `record_paths`
- **Remove Dead By-Path Import Fallbacks** (`1z8qk-debt remove-dead-by-path-fallbacks`) — 2 ACs completed. Key decisions: Remove rather than repair
- **Discovery Diagnostic Ignores Folders Without Files** (`1z8ql-enh discovery-ignores-fileless-folders`) — 3 ACs completed. Key decisions: Ignore any candidate without a direct file, not only those with subfolders
## Watchpoints

- <Add watchpoint, follow-up, or blocking notes here — coordination constraints, sequencing, or guard requirements.>

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
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
| plan | 48 | 2,643,138 |
| implement | 44 | 637,657 |
| review | 33 | 169,552 |
| **Total** | **125** | **3,450,347** |

<!-- wave:context-efficiency-state {"generation":127,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":44,"content_source_credit":663674,"derived_artifact_credit":1403,"direct_net":637657,"estimated_tokens_saved":637657,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2861,"response_debit":26017,"source_credit_count":19,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1458},"plan":{"calls":48,"content_source_credit":2758224,"derived_artifact_credit":3569,"direct_net":2643138,"estimated_tokens_saved":2643138,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2841,"response_debit":122325,"source_credit_count":92,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6511},"review":{"calls":33,"content_source_credit":203440,"derived_artifact_credit":7098,"direct_net":169552,"estimated_tokens_saved":169552,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5003,"response_debit":38299,"source_credit_count":30,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":125,"content_source_credit":3625338,"derived_artifact_credit":12070,"direct_net":3450347,"estimated_tokens_saved":3450347,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10705,"response_debit":186641,"source_credit_count":141,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10285},"wave_id":"1z8mm vocabulary-profile-record-names"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 3 | 0 | 2 | 1,558,108 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":2,"estimated_exploration_avoided":1558108,"surfaced_events":3} -->
<!-- wave:exploration-avoided end -->
