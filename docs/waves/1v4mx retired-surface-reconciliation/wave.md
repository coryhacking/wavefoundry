# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-12
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1v4mx retired-surface-reconciliation`
Title: Retired Surface Reconciliation

## Objective

Stop shipping instructions that point at retired surfaces. The upgrade currently instructs a retired journal step on every run, and nothing reconciles the instructions left behind by the journal retirement or the `.md` to `.prompt.md` rename, so a repository that runs every prescribed migration still references surfaces that no longer exist.

## Changes

Change ID: `1v4mv-bug retired-surface-references-survive-migration`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (upgrade output, scan surfaces), qa (report-only and clean-repo assertions)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, release-reviewer

Completed At: 2026-08-12

## Wave Summary

Wave `1v4mx` (Retired Surface Reconciliation) delivered one change: Retired-Surface References Survive Migration. Notable adjustments during implementation: Retired-Surface References Survive Migration: **Readiness council, code-grounded: the plan's mechanism claim is FALSE and the scope is corrected below.** `reconcile_scan.py` is not a generic retired-surface list. It carries TWO pattern families, and every pattern in both is hardcoded to a specific textual shape: `_LITERAL_PATTERN`, `_DYNAMIC_PATTERN` and `_VAR_BINDIR_PATTERN` all match the `.wavefoundry/bin/<name>` form, and `_TOOL_MCP_PATTERN` / `_TOOL_BARE_PATTERN` match `mcp__wavefoundry__<tool>` and bare tool tokens. Neither family can express a prose instruction (`Stop and journal when:`) or a path-extension rename (`docs/prompts/X.md` to `X.prompt.md`). Adding a name to `_RETIRED_SURFACE_REPLACEMENTS` would only make the scan look for `.wavefoundry/bin/journal`, which is meaningless. Items 2 and 3 therefore require NEW pattern families inside the existing scan, not a list extension. The Decision Log row rejecting "a new dedicated journal-reference scanner" as duplicative stands on its conclusion (stay inside one scan, one report-only contract, one findings shape) but not on its stated reason, and is corrected.; Retired-Surface References Survive Migration: AC-2/AC-3 delivered as a THIRD pattern family in `reconcile_scan.py`, per the corrected scope. Journal shapes are matched by anchored patterns over the retired system's own vocabulary rather than the bare word "journal", because prose legitimately narrates history. The prompt-extension surface is RESOLUTION-based, not textual: a reference is stale only when its `.prompt.md` twin exists on disk, so a genuinely-`.md` prompt doc is never flagged. Same scan, same report-only contract, same findings shape; no second scanner.; Retired-Surface References Survive Migration: **False positive found by running the new scan against this repository, then fixed.** `Distill journals` is not only a retired instruction: it is the documented legacy alias of the LIVE **Migrate journals** command (seed-210). The first pattern flagged `AGENTS.md`'s shortcut table, which would have told operators to delete a working command's alias. Added a line-scoped exemption that names the live command, so it cannot silence a bare instruction that merely sits near one. This is why the scan was run against a real corpus before the tests were written rather than after.

**Changes delivered:**

- **Retired-Surface References Survive Migration** (`1v4mv-bug retired-surface-references-survive-migration`) — 8 ACs completed. Key decisions: Extend the existing retired-surface reconciliation scan rather than add migration-time rewriting.; Reconcile this repository's own 32 stale journal references inside this wave rather than excluding `docs/agents/**` from the new pattern.
## Watchpoints

- **Release intent (operator, 2026-08-12):** the retired journal step shipped in 1.16.1; the fix rides in 1.16.2 whenever that is cut. No dedicated hotfix.
- **Watchpoint:** the existing scan is REPORT-ONLY and must stay so. Auto-rewriting operator-authored instructions is out of scope; a wrong rewrite is harder to notice than a stale reference.
- **Watchpoint:** do not build a second scanner. A parallel implementation of an existing rule is exactly how the two marker families in wave `1v4mw` drifted apart.
- **Follow-up (do not expand this wave):** if the census finds further retired surfaces with lagging references, file them separately.
- Counts for the journal and prompt-extension gaps (~90 sites across 43 files; 41 references across 27 files) are DOWNSTREAM observations. Reproduced at readiness cycle 2: the journal gap DOES hold here at 32 live files, the prompt-extension gap does NOT at zero references. The ACs assert shapes rather than counts for that reason; quote the local numbers, not the downstream ones.
- **Watchpoint:** the journal pattern cannot land green until this repository's own 32 stale references are reconciled, because the shipped guard asserts an empty editable channel for this repo and routes through the same helper. If that guard is made to pass by excluding `docs/agents/**` rather than by fixing the files, the wave has defeated its own purpose.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

*Machine review state — 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-12: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the two larger items rest on counts observed in a DOWNSTREAM repository (~90 sites across 43 files; 41 references across 27 files) that are not reproduced here, so the wave could be sized against numbers that do not hold locally; the plan already answers this by asserting SHAPES rather than counts in AC-2 through AC-4 and by recording the distinction in the Progress Log, and the reporter independently verified the strings are absent from current seeds and from the renderer, which makes them install-time legacy rather than anything this repository still emits; strongest-alternative: rewrite stale references automatically during migration, rejected because the existing scan is deliberately report-only and a wrong rewrite of operator-authored instructions is harder to notice than the stale reference it replaced)

Seat evidence:

- **red-team** — verified code-grounded. The editing-pass output does hardcode the retired journal step, with an adjacent comment stating the label needed fixing, so this is a known-and-unfixed defect rather than a new discovery. The reconciliation scan exists, is documented "report-only — the scan never mutates any file", and already returns three categorized lists, so extending its surface list is the established shape and no new machinery is warranted. Confirmed the plan forbids a second scanner, which matters because the sibling wave exists precisely because one rule got two implementations.
- **docs-contract-reviewer** — one finding, already the change's premise rather than new: the upgrade's shipped output contradicts two seeds simultaneously. seed-120 says persona journals must not be generated because the system is retired, and seed-160 says journals are retired and never a closure requirement, while the upgrade instructs journal reconciliation on every run. A shipped instruction that contradicts the seeds it points at is a documentation-contract defect in its own right, independent of the reference-lag items.

- **Prepare-phase Wave Council [prepare-council] — 2026-08-12: PASS with scope corrected** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the plan's load-bearing mechanism claim is FALSE and this cycle supersedes the previous cycle's red-team conclusion on exactly that point; `reconcile_scan.py` carries two pattern families whose every pattern is bound to the `.wavefoundry/bin/<name>` or `mcp__wavefoundry__<tool>` literal shape, so neither can express a prose instruction or a path-extension rename and adding a name to the shared map would only search for `.wavefoundry/bin/journal`; items 2 and 3 need NEW pattern families, which is materially more work than "extend the list", and the plan is corrected rather than approved as written; strongest-alternative: exclude `docs/agents/**` so the new pattern does not fire on this repository's own 32 stale files, rejected because the staleness lives exactly where the exclusion would go, which would ship a detector aimed away from the only instance we can observe)

Seat evidence (cycle 2, code-grounded against the tree):

- **red-team** — **supersedes this seat's cycle-1 conclusion.** Cycle 1 verified that the scan exists, is report-only, and returns three categorized lists, then concluded "extending its surface list is the established shape and no new machinery is warranted". That last step was never checked against the patterns themselves and is wrong: `RETIRED_SURFACES` is derived from `_RETIRED_SURFACE_REPLACEMENTS` and consumed only by `_LITERAL_PATTERN`, `_DYNAMIC_PATTERN` and `_VAR_BINDIR_PATTERN`, all three anchored to `.wavefoundry[\\/]bin[\\/]`. The architectural conclusion (one scan, one contract, one findings shape, no second scanner) survives; the mechanism claim does not. Three further results: item 1 confirmed live at the editing-pass log line; item 2 REPRODUCES here at 32 live files, with the string confirmed absent from seeds, renderers and install templates, so the legacy-content diagnosis holds at its source; item 3 does NOT reproduce here at zero references, so AC-3 requires a fixture and the plan's cited `wave-coordinator.md:15` is a downstream line that must not be chased locally.
- **docs-contract-reviewer** — one new finding, now recorded as AC-7: the shipped guard `test_no_live_file_references_a_retired_wrapper` asserts an EMPTY editable channel for this repository and routes through the shipped helper by design, so the journal pattern cannot land green while our own 32 files remain stale. The plan did not disclose this. It is a documentation-contract issue as much as a test one, since the framework would otherwise ship a staleness detector while carrying the staleness it detects. Operator was shown the size difference and chose the full scope on 2026-08-12; AC-7 and AC-8 added, Scope and Decision Log corrected.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 15 | 6,609 |
| implement | 7 | 0 |
| review | 7 | 34,217 |
| **Total** | **29** | **40,826** |

<!-- wave:context-efficiency-state {"generation":29,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":7,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-687,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":111,"response_debit":642,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":66},"plan":{"calls":15,"content_source_credit":24009,"derived_artifact_credit":1300,"direct_net":6609,"estimated_tokens_saved":6609,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4020,"response_debit":20376,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5696},"review":{"calls":7,"content_source_credit":48287,"derived_artifact_credit":1056,"direct_net":34217,"estimated_tokens_saved":34217,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2767,"response_debit":13705,"source_credit_count":10,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":29,"content_source_credit":72296,"derived_artifact_credit":2356,"direct_net":40139,"estimated_tokens_saved":40826,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6898,"response_debit":34723,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7108},"wave_id":"1v4mx retired-surface-reconciliation"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
