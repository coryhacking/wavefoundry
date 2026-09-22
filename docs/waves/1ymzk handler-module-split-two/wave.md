# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-21
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1ymzk handler-module-split-two`
Title: Handler Module Split Two

## Objective

When this wave closes, the techdocs and memory handler families live in `techdocs_handlers.py` and `memory_handlers.py` with byte-identical registration in `server_impl.py`, `memory_cli.py` reaches the moved names through `memory_handlers` instead of the monolith (`memory_eval.py` keeps its single handle by decision), and the public tool surface is unchanged against the golden fixture. Now, because the `1y0h2` recipe is proven and idle, memory is the largest family still inlined, and the modularity kickoff scheduled these two slices last.

## Changes

Change ID: `1ymzi-ref techdocs-handler-module`
Change Status: `complete`

Change ID: `1ymzj-ref memory-handler-module`
Change Status: `complete`

## Participants

- Coordinator: wave-coordinator
- Write-owning roles: implementer (the two new modules, the composition root, the inverted memory CLI, tests), technical-writer (the `current-state.md` handler-module line, the `domain-map.md` Handler ownership paragraph, the new `layering-rules.md` boundary row, the two standing-baseline references, CHANGELOG)
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer

Completed At: 2026-09-21

## Wave Summary

Wave `1ymzk` (Handler Module Split Two) delivered two changes: Techdocs Handler Module and Memory Handler Module. Notable adjustments during implementation: Techdocs Handler Module: Readiness round (red-team and architecture seats, code and QA lanes, all fresh). Corrections folded in: a source-text allowlist test in `test_render_agent_surfaces.py` and an advisory-site census in `test_server_tools_lifecycle.py` both fail on a third module and are now named edits; the two `TECHDOCS_AUDIT_*` constants and the `McpRepoCache` annotation were missing from the inventory; `_diagnostic` is imported directly from its owner; the existing tests are the transport-free coverage, so only the `FAMILIES` entry and a dry-run assertion are added; the wave owes a before-and-after retrieval receipt pair because `server_impl.py` is a production retrieval module; `domain-map.md` and a `layering-rules.md` row join the affected docs.; Memory Handler Module: Repair cycle 1: typed repair_start recorded for CODE-DEL-1 and QA-DEL-1 before test-only edits. Migrated exact record-layout message exemption; expanded lock-order source owners and exact qualified-call recognition while retaining >=8 coverage and proving nested violation detection. Six focused tests passed in 0.712s; product unchanged, repaired test hashes frozen. Gapfill: exact compiler-AST census and mechanical test-path migration used native source reads because the checks depend on complete source syntax rather than semantic ranking.; Memory Handler Module: Implement: independently approved inventory published before source edits; all 29 domain functions and 14 objects moved, five lifecycle/crediting compositions retained. Added direct CLI owner, four explicit patch migrations, cache non-vacuity and corrected same-interpreter premise; identity, staying, reload and bounded closure tests added. The inventory deliverable is recorded in the tree; Git commit remains operator-owned.

**Changes delivered:**

- **Techdocs Handler Module** (`1ymzi-ref techdocs-handler-module`) — 5 ACs completed. Key decisions: Follow the `1y0h2` recipe, not the kickoff's `TOOLS` list.; Techdocs first, memory second, in one wave.
- **Memory Handler Module** (`1ymzj-ref memory-handler-module`) — 6 ACs completed. Key decisions: Follow the `1y0h2` recipe with a rebinding block that re-exports every reached name and object.; Move criterion is domain ownership; two close-gate compositions and three crediting extractors stay.
## Watchpoints

- Watchpoint: techdocs moves first and its review completes before the memory inventory is committed, so the recipe is rehearsed on the small family.
- Watchpoint: the wave owes a before-and-after standing-evaluation receipt pair because `server_impl.py` is a production retrieval module; the before-receipt is recorded before the techdocs move's first edit, or the deviation is recorded explicitly.
- Watchpoint: the memory inventory is a committed, reviewed deliverable before any memory definition moves; the move criterion is domain ownership, five memory-named definitions stay in `server_impl.py` (two close-gate compositions, three crediting extractors), fourteen module-level objects move and are re-exported, and the classification table governs.
- Watchpoint: every new module must enter the reload purge list by plain module-body import; the import-derived purge census only sees that form.
- Watchpoint: `PRODUCTION_RETRIEVAL_MODULES` membership for `memory_handlers.py` is derived from measured-tool reachability, not assumed; the known route to check is `code_read_response` reaching `_memory_advisories_for_path`.
- Watchpoint: `server_impl.py` is a fragile file with a memory playbook; the memory-mint re-entry seam and the upgrade runner's reach into `_memory_backfill_batch_locked` are verified before and after the move.
- Follow-up: context-efficiency projection and persistence are the next family, planned separately because they interleave with the middleware chain and the index interlock.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| CODE-DEL-1 | do_now | no | completed | code-reviewer, qa-reviewer |
| QA-DEL-1 | do_now | no | completed | code-reviewer, qa-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- docs-contract-reviewer readiness seat: approved after correcting the wave objective, enumerating technical-writer edits, naming standing-baseline receipt files and replacing both-siblings wording. All findings were folded into the plans; no blockers remain. Historical seat evidence and focused verification are recorded in [readiness-review.md](readiness-review.md).

- **Prepare-phase Wave Council [prepare-council] — 2026-09-21: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the memory plan left fourteen module-level objects unclassified while closures, a staying definition and about twenty test sites reach them, and the techdocs plan missed a source-text allowlist test; strongest-alternative: move the close-gate compositions too and have lifecycle import the handler module, rejected because they are lifecycle-gate logic and the domain-ownership criterion replaces the false direction argument; . The red-team and architecture seats blocked on plan text, one bounded repair pass resolved every finding, and two focused verifiers approved; the docs-contract-reviewer seat ran last on the repaired plans and approved with nonblocking wording findings only. Per-seat evidence and the repair summary are in `readiness-review.md`)

## Dependencies

- No external wave dependencies.
- Intra-wave order: `1ymzi` techdocs move and its review complete before the `1ymzj` memory inventory is committed; both edit `server_impl.py` and `test_handler_modules.py` under one implementer.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 61 | 427,398 |
| implement | 82 | 2,242,694 |
| review | 72 | 887,824 |
| **Total** | **215** | **3,557,916** |

<!-- wave:context-efficiency-state {"generation":200,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":82,"content_source_credit":2435904,"derived_artifact_credit":5733,"direct_net":2242694,"estimated_tokens_saved":2242694,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2716,"response_debit":200033,"source_credit_count":41,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3806},"plan":{"calls":61,"content_source_credit":534111,"derived_artifact_credit":5203,"direct_net":427398,"estimated_tokens_saved":427398,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5596,"response_debit":126542,"source_credit_count":50,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":20222},"review":{"calls":72,"content_source_credit":1031793,"derived_artifact_credit":4618,"direct_net":887824,"estimated_tokens_saved":887824,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19409,"response_debit":131494,"source_credit_count":88,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2316}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":215,"content_source_credit":4001808,"derived_artifact_credit":15554,"direct_net":3557916,"estimated_tokens_saved":3557916,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":27721,"response_debit":458069,"source_credit_count":179,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":26344},"wave_id":"1ymzk handler-module-split-two"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 5 | 0 | 4 | 3,425,282 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":4,"estimated_exploration_avoided":3425282,"surfaced_events":5} -->
<!-- wave:exploration-avoided end -->
## Closure reconciliation

- Both admitted changes are complete; every AC and task is checked, with no intentionally deferred ACs. TechDocs and memory handlers moved; registration remains unchanged; memory_cli uses the new owner while memory_eval retains its handle.
- Required delivery lanes are reconciled by the fresh contexts in independent-delivery-review.md. Readiness authority is current; delivery Council is not required by the receipt. No unresolved tree-moved finding remains.
- Docs-contract review was performed by the independent architecture/docs lane; no specs changed. Closure tool owns final status and completion-date reconciliation.
- Memory capture rerun at closure: zero new candidates, zero remaining; three previously rejected canonical duplicates retained. Retrospective: structural tests must follow moved owners; corpus composition must be checked before attributing evaluation changes; retained reviewer contexts must not be marked fresh. Existing policy plus the independent review and corrected delivery report preserve these lessons; no duplicate memory promoted.
- Cleanup: retained all fourteen wave files. Inventories, staged reviews, corrected evidence and the authoritative ledger contain unique history or live citations; no verified disposable scratch artifacts found. Ledger-cited paths remain stable.
- Nonblocking follow-ups preserved: recurring policy-ineligible corpus reaping, invalid receipt retention-index omissions, and misplaced Progress Log rows in the change docs. No code or change-doc scope edits during close.
- Session handoff will be set idle after successful close; changes remain uncommitted. Operator condition: close if the reviewed evidence and current gates are satisfactory, as requested in this turn.
