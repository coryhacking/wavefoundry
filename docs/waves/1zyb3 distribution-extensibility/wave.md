# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-06
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1zyb3 distribution-extensibility`
Title: Distribution Extensibility

## Objective

Give distributions safe ownership of declared skills, declared extension points for the journal migration, per-profile goldens that cover extension tools, and gating for patch-style edit tools in the Copilot hooks.

## Changes

Change ID: `1zxnu-enh declared-skill-ownership-and-profile-goldens`
Change Status: `implemented`

Change ID: `1zxnv-enh journal-migration-extension-points`
Change Status: `implemented`

Change ID: `1zxny-enh gate-patch-tool-edits-in-hooks`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-10-07

## Wave Summary

Wave `1zyb3` (Distribution Extensibility) delivered 3 changes: Declared Skill Ownership, Orphan Removal and Prompt Templates; Declared-Profile Golden Covers Modules, Hidden Tools, Replacements and Skills, Journal Migration Extension Points: Declared Pristine Templates and a Pre-Migration Hook, and Gate Copilot apply_patch Edits by the File Headers in the Patch Text. Notable adjustments during implementation: Declared Skill Ownership, Orphan Removal and Prompt Templates; Declared-Profile Golden Covers Modules, Hidden Tools, Replacements and Skills: Deviation for review: Requirement 8's parenthetical lists four added names, but Requirement 6's hidden tool needs a plain unpinned alias and the only existing plain alias targets `wf_help`, which many tests reference; hiding `wf_gpu_doctor` adds a fifth name, `wf_alias_gpu_doctor`, so the added-names assertion has five. The Decision Log row for the name choice (Requirement 6) is left to the coordinator because Decision Log edits rotate the review receipt.; Declared Skill Ownership, Orphan Removal and Prompt Templates; Declared-Profile Golden Covers Modules, Hidden Tools, Replacements and Skills: Mutation probes (scratch copy, each restored): marker matched anywhere, legacy adoption removed, refusal removed, all three link checks off with `os.stat`, extra-entry check off, case-sensitive name compare, `wf-` skip removed, template overwrite of an existing doc, preflight template destination dropped (with and without render containment), fixture module schema changed, undeclared `module_files` allowed: every probe fails at least one named test. A single link layer off is not detected, because the three link checks overlap (defense in depth).; Journal Migration Extension Points: Declared Pristine Templates and a Pre-Migration Hook: Implemented. `mcp_tool_extensions`: `EXTENSION_JOURNAL_TEMPLATES`, `EXTENSION_JOURNAL_PRE_MIGRATION_HOOK`, `journal_declaration_problems(templates, hook, helper_modules)` (reads the module constants when an argument is None). `upgrade_extensions`: `JournalDeclarationError`, `_load_journal_declaration` (by-path load under a private name; missing file or constants read as empty; import failure names the class only), `_load_journal_hook` (exact listed `.py`, resolved parent check, signature bind), `_compile_journal_template` (escaped literals, named group then backreference per placeholder), `migrate_journals(..., templates=)` (default loads the declaration without the hook), `_run_journal_pre_migration_hook`, and the gate wiring in `pre_docs_gate`; `_migrate_journals` docstring names `pre_docs_gate`. `record_layout_support`: both keys frozen, `journal_declaration_problems()` in `_VALIDATE_DRIVER`. Docs: spec rows and paragraph, layering row, seed 210 sentence, CHANGELOG Added bullet.

**Changes delivered:**

- **Declared Skill Ownership, Orphan Removal and Prompt Templates; Declared-Profile Golden Covers Modules, Hidden Tools, Replacements and Skills** (`1zxnu-enh declared-skill-ownership-and-profile-goldens`) — 12 ACs completed. Key decisions: Refusing an unmarked overwrite skips that one skill on that host and reports it; the rest of the render proceeds.; The marker is a fixed HTML-comment body line, `<!-- wavefoundry:declared-skill -->`, first after the frontmatter; only declared skills carry it (coordinator decision).
- **Journal Migration Extension Points: Declared Pristine Templates and a Pre-Migration Hook** (`1zxnv-enh journal-migration-extension-points`) — 9 ACs completed. Key decisions: The two declarations live in `mcp_tool_extensions.py`, and the hook is `"module:function"` in a declared helper module (coordinator decision).; An invalid declaration refuses the upgrade at `pre_docs_gate` with its problems; a hook that raises skips the migration with a path-free warning and the upgrade continues (coordinator decision).
- **Gate Copilot apply_patch Edits by the File Headers in the Patch Text** (`1zxny-enh gate-patch-tool-edits-in-hooks`) — 8 ACs completed. Key decisions: Fail closed when an `apply_patch` payload yields no header path.; Read `input`, then `patch`, then a raw string argument.
## Watchpoints

- Watchpoint: fourth of five sequential waves; lands after 1zyb2 (C) and rebases on its `test_upgrade_wavefoundry.py` edits; 1zyb4 (E) follows and derives skill names on top of 1zxnu.
- Follow-up: Codex apply_patch stays ungated (no hook host).
- Follow-up (delivery re-verification, low): add a test that an orphan `SKILL.md` unlink failure raises, and assert the exception class in the rmdir NOTICE test; `{{date}}` matches non-ASCII digits.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | completed | — |
| DEL-2 | do_now | no | pending | — |
| DEL-3 | do_now | no | pending | — |
| DEL-4 | do_now | no | pending | — |

*Machine review state — 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0*
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
| plan | 24 | 17,211 |
| implement | 15 | 69,854 |
| review | 14 | 145,158 |
| **Total** | **53** | **232,223** |

<!-- wave:context-efficiency-state {"generation":53,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":15,"content_source_credit":94425,"derived_artifact_credit":2548,"direct_net":69854,"estimated_tokens_saved":69854,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":3176,"response_debit":24141,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":198},"plan":{"calls":24,"content_source_credit":38514,"derived_artifact_credit":1555,"direct_net":17211,"estimated_tokens_saved":17211,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2061,"response_debit":30007,"source_credit_count":14,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9210},"review":{"calls":14,"content_source_credit":181347,"derived_artifact_credit":1270,"direct_net":145158,"estimated_tokens_saved":145158,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4846,"response_debit":34997,"source_credit_count":24,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2384}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":53,"content_source_credit":314286,"derived_artifact_credit":5373,"direct_net":232223,"estimated_tokens_saved":232223,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":10083,"response_debit":89145,"source_credit_count":62,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11792},"wave_id":"1zyb3 distribution-extensibility"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
