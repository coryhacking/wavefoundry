# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-01
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zimf extension-seams`
Title: Extension Seams

## Objective

Distribution extension modules get a stable public helper surface, a declared way for their own tools to take the lifecycle mutation lock and earn derived-artifact credit, and declared extra change kinds validated like the vocabulary profile, so a downstream distribution's team-workflow tools stop depending on private names and no longer store their own kinds as `change`.

## Changes

Change ID: `1zimn-enh extension-public-helpers`
Change Status: `implemented`

Change ID: `1zimo-enh extension-lifecycle-tools-and-artifact-credit`
Change Status: `implemented`
Depends On: `1zimn-enh extension-public-helpers`

Change ID: `1zimp-enh declared-extra-change-kinds`
Change Status: `implemented`
Depends On: `1zimn-enh extension-public-helpers`, `1zimo-enh extension-lifecycle-tools-and-artifact-credit`

## Participants

- Coordinator: <wave coordinator>
- Write-owning roles: <roles selected during Prepare wave>
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-01

## Wave Summary

Wave `1zimf` (Extension Seams) delivered 3 changes: Public Helpers for Extension Handlers, Lifecycle Lock and Artifact Credit for Extension Tools, and Declared Extra Change Kinds. Notable adjustments during implementation: Public Helpers for Extension Handlers: Implemented. `server_impl` gains the marked public-helper block: `EXTENSION_PUBLIC_HELPERS` and `ensure_no_extra_args`, `make_response`, `make_diagnostic`, each a `def` calling its private counterpart by module-global lookup at call time (change `1zimp` adds `change_doc_response` and the pin now names four). The two loader refusals name `server_impl.ensure_no_extra_args`; every extension fixture module in the driver uses the public names. Spec **Registration** names the supported surface and states that a lock-needing tool declares `EXTENSION_LIFECYCLE_TOOLS` instead of taking the lock; **Overrides** names the public helper; CHANGELOG `### Added`. Tests failed first (missing attributes, old message), then passed. AC-1, AC-3: `PublicHelperContractTests`; AC-2: `PublicHelperLateBindingTests` and the reload half of `PublicHelperServingTests`; AC-4: `PublicHelperServingTests`; AC-5: `ExtensionRefusalTests.test_refusals_name_the_public_helper` and the census suites. Verification: full suite (`run_tests.py --no-cache`) in a scratch copy, 10,567 tests in 153 files OK (34 skipped); `--profile second` 10,564 OK and `--profile declared` 10,567 OK; 16 mutations of the new guards, all killed.; Lifecycle Lock and Artifact Credit for Extension Tools: Reverification repair. The duplicate-credit test drops the symlink name when the account cannot create symlinks (Windows without Developer Mode) instead of writing an empty stand-in file, which resolved to its own path and added a second zero-token artifact. The spec credit contract and the CHANGELOG bullet now say each resolved file is credited once per response, core extractors included.; Lifecycle Lock and Artifact Credit for Extension Tools: Implemented. `mcp_tool_extensions` gains `EXTENSION_LIFECYCLE_TOOLS` and `EXTENSION_ARTIFACT_PATH_FIELDS` (counted by `declared()`) and `_lock_and_credit_problems` in `declaration_problems`; `server_impl` records the installed declarations in `_EXTENSION_LIFECYCLE_TOOLS` and `_EXTENSION_ARTIFACT_PATH_FIELDS` (cleared at install start and on any registration failure), refuses a declaration no module registered, passes them through `_lock_pass_kwargs` (`extension_tools`) and `_cost_pass_kwargs` (`artifact_extractors`, used only for names absent from `_ARTIFACT_EXTRACTORS`), and reports `lifecycle_tools` and `artifact_path_fields` in provenance. Name-keyed set audit (Requirement 7): `_LIFECYCLE_MUTATION_LOCK_TOOLS` extended by the pass set, not edited; `_COST_EXEMPT_TOOLS` reserved, so a declared tool is never exempt; `_ARTIFACT_EXTRACTORS` extended by the pass map, not edited; `_COST_FOCUS_EXTRACTORS` and `_STATE_SOURCE_EXTRACTORS` unchanged (no extension entry); publication writer registry unchanged (write-tier extension tools already consult the checkpoint); `extractor_free` applies only to replacements; setup-notice skip set (runner tools and `index_health`) unchanged; roster tiers unchanged (declared tools are already `write`); `_CONTEXT_RETRIEVAL_TOOLS`, `_INDEXED_CONTEXT_TOOLS`, `_REFERENCE_ONLY_GRAPH_TOOLS`, `_LIFECYCLE_CONTEXT_STAGES`, `_TRACKING_CONTEXT_TOOLS`, `mcp_tool_roster.TOOL_TIERS` and `RUNNER_TOOLS`, `render_platform_surfaces._RENAMED_MCP_TOOLS`, the `wf_prepare_wave` `readiness_receipts` special case and `_EXTENSION_REPLACED_CORE` are keyed on core names and unchanged (a declared tool records only its cost-wrapper debit and credit). Lock-file check (wave `1zimc` Requirement 9): a declared tool's call passes only the setup, rewrite, guard, lock and cost wrappers; the lock re-entry consults the hold registry before opening the file, and the credit uses `stat` only, so no declared path opens the lifecycle lock file in-process (pinned: re-entry and a served locked call open no lock file, and crediting the lock file's own path keeps the hold). Tests failed first, then passed: AC-1 `LockAndCreditDeclarationTests`; AC-2, AC-6 `ExtensionRefusalTests` (`lifecycle_unregistered`, `artifact_unregistered`, `lifecycle_reserved_name`, `lifecycle_invalid_declaration`); AC-3 to AC-7 `ExtensionLifecycleToolTests` with a real second-process lock holder; AC-8 `LockAndCreditDeclarationTests.test_shipped_declaration_lists_both_constants_and_a_non_empty_value_fails` and the declaration census. Verification: full suite (`run_tests.py --no-cache`) in a scratch copy, 10,567 tests in 153 files OK (34 skipped); `--profile second` 10,564 OK and `--profile declared` 10,567 OK; 16 mutations of the new guards, all killed.

**Changes delivered:**

- **Public Helpers for Extension Handlers** (`1zimn-enh extension-public-helpers`) — 7 ACs completed. Key decisions: Public helpers live on `server_impl` as late-bound wrappers; Names `make_response` and `make_diagnostic`, not `response` and `diagnostic`
- **Lifecycle Lock and Artifact Credit for Extension Tools** (`1zimo-enh extension-lifecycle-tools-and-artifact-credit`) — 10 ACs completed. Key decisions: A declared lifecycle tool gets no supported way to compose core lifecycle operations in this change (readiness strongest challenge); Two declarations, one for the lock and one for the artifact field
- **Declared Extra Change Kinds** (`1zimp-enh declared-extra-change-kinds`) — 8 ACs completed. Key decisions: Declare extra kinds in `vocabulary_profile.py`, with the core kinds moved there as the single source; Token rule `^[a-z][a-z0-9]{1,15}$`, no core kind, no duplicate, not `wave`, `mem`, `sec` or `adr`
## Watchpoints

- Blocking: wave `1zimc` (`1zimg-bug lifecycle-lock-holds-survive-reentry-and-probe`) must close before `1zimo` is implemented; extension lifecycle tools use the same lock wrapper and its hold registry.
- Watchpoint: all three changes edit `wf_server/server_impl.py` and `docs/specs/mcp-tool-surface.md`; implement in order 1zimn, 1zimo, 1zimp.
- Watchpoint: audit every name-keyed set a declared extension tool passes through (lock, cost exemption, artifact, focus and state extractors, publication registry, `extractor_free`, setup-notice skips, roster tiers); no declaration may lower `write` to `read` or touch `EDIT_GATE_TOOLS`.
- Watchpoint: run the whole suite under the default run, `--profile second` and `--profile declared` before delivery review; the seed 170 edit needs the `seed_edit_allowed` gate.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1ZIMF-DELIVERY-HARDENING | do_now | no | completed | — |

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
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| security-reviewer | pending | no current executed approval | record approval evidence for security-reviewer |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-10-01: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: a declared lifecycle tool runs under the lock but has no public way to call core lifecycle operations, since core_handler is limited to same-name overrides and calling a served locked tool is refused as re-entry, so such tools still reach private response functions; recorded as a follow-up decision; strongest-alternative: let a module declaring EXTENSION_LIFECYCLE_TOOLS call core_handler for any core lifecycle-locked tool, deferred to its own change)
- Prepare council seat evidence (2026-10-01): one independent Opus reviewer ran both seats and the code, qa, architecture, docs-contract and security lanes against the code: no import cycle from moving kinds into vocabulary_profile; reload re-imports vocabulary_profile and mcp_tool_extensions; core_handler cannot re-enter the lock; read-tier, core and edit-gate tools cannot be declared. It blocked on 1zimp: the tuple-versus-list comparison under --profile second and the editable-constant snapshot pin, and a census test that would scan seeds. Its edits 1-11 were applied verbatim.

## Dependencies

- External: wave `1zimc lifecycle-lock-hold-registry` (`1zimg-bug lifecycle-lock-holds-survive-reentry-and-probe`), implemented first; `1zimo` builds on its lock hold registry and re-entry behaviour.
- Intra-wave: declared by the `Depends On:` lines under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 69 | 3,812,049 |
| implement | 35 | 767,372 |
| review | 44 | 1,006,701 |
| **Total** | **148** | **5,586,122** |

<!-- wave:context-efficiency-state {"generation":154,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":35,"content_source_credit":871675,"derived_artifact_credit":0,"direct_net":767372,"estimated_tokens_saved":767372,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1688,"response_debit":102615,"source_credit_count":15,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":69,"content_source_credit":3906128,"derived_artifact_credit":13357,"direct_net":3812049,"estimated_tokens_saved":3812049,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3985,"response_debit":112664,"source_credit_count":140,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9213},"review":{"calls":44,"content_source_credit":1093559,"derived_artifact_credit":2783,"direct_net":1006701,"estimated_tokens_saved":1006701,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6701,"response_debit":85256,"source_credit_count":42,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":148,"content_source_credit":5871362,"derived_artifact_credit":16140,"direct_net":5586122,"estimated_tokens_saved":5586122,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":12374,"response_debit":300535,"source_credit_count":197,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11529},"wave_id":"1zimf extension-seams"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 9 | 0 | 7 | 3,483,127 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":7,"estimated_exploration_avoided":3483127,"surfaced_events":9} -->
<!-- wave:exploration-avoided end -->
