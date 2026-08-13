# Reconciliation Findings Have No Historical-Record Disposition

Change ID: `1v7a1-bug reconciliation-findings-have-no-historical-record-disposition`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-12
Wave: 1v79z reconciliation-self-healing-and-dispositions

## Rationale

The reconciliation scan reports every match with the same suggestion, because a regex cannot tell a
live reference from a historical record. Both a config key pointing at a deleted directory and a
sentence recording that the directory was deleted receive "the journal system is retired; capture
durable lessons as typed memory records". The first is correct. The second instructs the operator to
rewrite a record the framework's own policy protects. That rule ships in the SEEDS, not only in this
repository's `AGENTS.md`: seed-160 and seed-220 both state that during cleanup you "remove only live
working docs and deprecated files that have explicit replacements; do not remove historical
references from changelogs, closed-wave records, release notes, or archived documentation — retiring
a file removes the file, not the historical record of it". `AGENTS.md` **Cleanup and Destructive
Operations** carries the same rule in its own words. Because the rule is seeded, every target
repository inherits it, so the conflict between the scan's suggestion and the framework's own policy
reaches every consumer rather than being a local quirk.

Reported from a downstream repository on 1.16.2 with a concrete instance: a handoff line reading
"All 17 files under `docs/agents/journals/` … were pristine scaffolds" is a factual record of what
the retirement did. The operator's only options today are to rewrite a true statement or to accept
the same finding on every upgrade forever. Neither is right, and a channel that reports the same
unresolvable item indefinitely is a channel operators learn to skip — the failure `1v4mv` AC-8
guarded against for archives but could not cover for records living in non-excluded files.

Wholesale exclusion is not the answer. `1v4mv` already excludes the archive directories
(`docs/waves`, `docs/reports`, `docs/agents/memory`); the remaining cases are historical statements
inside files that also carry live instructions, so file-level exclusion would silence real findings
in the same file.

**The framework already solved this shape once.** The secrets scanner writes findings to
`docs/scan-findings.json` with per-finding status (`pending` → `confirmed-secret` /
`false-positive`), classified once by a reviewer, persisted, and consulted by the close gate. That
is precisely "mark it resolved once" for a sibling scanner, and it is the model to follow rather
than invent.

## Requirements

1. A reconciliation finding can be marked as a historical record, once, and stops being reported on
   subsequent runs.
2. The marking is per finding, not per file, so a live instruction in the same file still reports.
3. A marked record is durable across upgrades, since the recurrence it fixes is an upgrade-time one.
4. A marking that no longer corresponds to a real finding does not silently persist as a blanket
   suppression: if the underlying text changes, the disposition does not carry over to the new text.
5. The mechanism follows the existing `docs/scan-findings.json` disposition model rather than
   introducing a second, differently-shaped one.

## Scope

**Problem statement:** the reconciliation channel has exactly one disposition — unresolved — so a
finding that is correct-as-written can only be silenced by rewriting a protected record.

**In scope:**

- A per-finding historical-record disposition for reconciliation findings, following the
  `scan-findings.json` model.
- Suppressing marked findings from the reported channel while keeping them inspectable.

**Out of scope:**

- Widening the journal patterns to further morphological variants (`journal distillation`,
  `journals distilled`, `distilling journal lessons`). That work is deliberately sequenced AFTER
  this change: broader patterns without a disposition produce more unresolvable findings, which is
  the defect this change exists to fix. File it separately once this lands.
- The secrets gate, its statuses, or `scan-findings.json` itself. This follows its model; it does
  not modify it.
- Auto-classifying findings. The framework does not get to decide what is historical; that judgment
  is the operator's, which is the entire point of a report-only channel.
- Changing which findings the scan produces.

## Acceptance Criteria

- [x] AC-1: A finding marked as a historical record is not reported on the next scan, asserted end to end through the reported channel rather than the marking store.
- [x] AC-2: Marking is per finding: a second, unmarked finding in the SAME file still reports, asserted with one historical line and one live instruction in one file.
- [x] AC-3: The disposition survives a simulated upgrade cycle, asserted by re-running the scan against the persisted marking rather than an in-process value.
- [x] AC-4: A disposition does not carry over when the underlying text changes, asserted by marking a finding then altering the matched line so a new finding reports.
- [x] AC-5: An unmarked repository behaves exactly as today, asserted so the mechanism adds nothing to repositories that never use it.
- [x] AC-6: The marking store's shape and vocabulary follow `docs/scan-findings.json`, asserted against that file's structure so the two do not diverge into different idioms.

## Tasks

- [x] Reproduce first: a historical record and a live instruction in one file must both report before the change, and only the live one after.
- [x] Read the `scan-findings.json` model and mirror its store shape, status vocabulary, and read path.
- [x] Implement the per-finding disposition and its suppression at the reported-channel boundary.
- [x] Decide and document what invalidates a disposition when the underlying text changes.
- [x] Confirm the downstream-reported case resolves: a handoff line recording the retirement can be marked once and stops recurring.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| reproduce | implementer | — | One file, one historical record, one live instruction. |
| store | implementer | reproduce | Mirror `scan-findings.json`; do not invent a second idiom. |
| suppression | implementer | store | Suppress at the reported-channel boundary, keep findings inspectable. |
| invalidation | implementer | store | What breaks a disposition when the text moves. AC-4 is the hard part. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/reconcile_scan.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_wf_cli.py`

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` if the disposition surfaces through a tool response. Otherwise
`N/A`: this adds a disposition to an existing report-only channel and decides no new boundary. The
`scan-findings.json` precedent means the model itself is already recorded.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect: no disposition exists. |
| AC-2 | required | File-level suppression would silence real findings, which is worse than the recurrence it fixes. |
| AC-3 | required | The recurrence is upgrade-time, so an in-process marking fixes nothing. |
| AC-4 | required | A disposition that outlives its finding is a blanket suppression wearing a per-finding label, and would hide a genuinely new stale reference on a line that once held a historical one. |
| AC-5 | required | Repositories that never mark anything must be unaffected. |
| AC-6 | important | Two differently-shaped disposition stores is how one rule becomes two implementations, the same divergence wave `1v4mw` was filed to repair. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-12 | Filed from downstream 1.16.2 field feedback with a concrete unresolvable instance (a handoff line recording the journal retirement). Verified the precedent before planning: the secrets scanner persists findings to `docs/scan-findings.json` with per-finding statuses classified once and read by the close gate, which is the disposition model this change should follow rather than invent. Confirmed the gap is real: `1v4mv` handles historical records by EXCLUDING whole archive directories, which cannot cover a historical statement inside a file that also carries live instructions. | `server_impl` secrets-gate reader and status vocabulary; `reconcile_scan.EXCLUDED_DIRS`; field report. |
| 2026-08-12 | Implemented following the `scan-findings.json` model: a `docs/reconcile-dispositions.json` store of `{key, status}` entries, `HISTORICAL_RECORD` status, read at the reported-channel boundary in `scan_repo_channels`. `scan_repo` deliberately stays unfiltered so an audit can still see what was dispositioned away rather than it vanishing. The store fails OPEN on a malformed or unreadable file: silently hiding stale references is the failure this channel exists to prevent, so a corrupt store must not suppress anything. | `DISPOSITIONS_REL`, `disposition_key`, `load_dispositions`, `is_dispositioned`; `HistoricalRecordDispositionTests` 8/8. |
| 2026-08-12 | AC-4 resolved by keying on the MATCHED TEXT and deliberately NOT on the line number. Excluding the line means editing prose elsewhere in the file does not resurrect a settled judgment; including the matched text means a disposition cannot outlive the text it was made about. Both halves are asserted, because either alone would be wrong: a key with the line number would churn on every unrelated edit, and a key without the matched text would be a blanket file suppression wearing a per-finding label. | `test_disposition_does_not_survive_a_text_change` and `test_line_movement_does_not_resurrect_a_disposition`. |
| 2026-08-12 | **Design defect caught by the AC-1 fixture, not by inspection: the disposition store scanned ITSELF.** The store records each settled finding's matched text verbatim, so writing a disposition for `docs/agents/journals/` created a NEW finding quoting it in the store file. Dispositioning a finding produced a finding. Fixed by adding `reconcile-dispositions.json` to `EXCLUDED_BASENAMES` beside `CHANGELOG.md` and `prompt-surface-manifest.json`, its machine-managed siblings. | `test_dispositioned_finding_stops_reporting` failed with a `docs/reconcile-dispositions.json` finding before the exclusion, then passed. |
| 2026-08-12 | Implementation slip worth recording: a ` ` separator from the design draft was written into `disposition_key` as a LITERAL null byte, which made `reconcile_scan.py` unparseable and errored all 18 tests in the file at import. Repaired to a source-level `\x1f` escape. Cheap to fix, but a reminder that a separator chosen in prose must be written as an escape sequence in source, not pasted as the character. | `SyntaxError: source code string cannot contain null bytes`; byte offset located and replaced. |
| 2026-08-12 | **Gapfill:** implement-stage instrumented retrieval shows 0 `code_*` / `docs_search` calls against 5 changed non-docs files, and the harness fallback was the right instrument here. Both seams were located during READINESS, not implementation: the council had already read `ensure_manifest`, `default_manifest_payload`, `EXCLUDED_BASENAMES`, the `scan-findings.json` reader, and the per-key consumer census through MCP retrieval, and recorded the exact anchors in the plans. Implementation was then edits at known symbols plus executed probes (test runs, reproduction scripts, a byte-level null-byte repair), which are shell work by the posture's own terms. The one genuinely new question that arose mid-implementation, whether `gardener_run` gates reconciliation, was answered by reading the enclosing function directly at a known call site rather than by search. Recorded rather than left as an unexplained advisory. | `wf_review_wave` `retrieval_posture_gap` advisory; readiness-cycle retrieval recorded in both plans' Progress Logs. |
| 2026-08-12 | **Readiness council corrected a citation in this plan.** The first draft attributed "retiring a file removes the file, not the historical record of it" to `AGENTS.md` **Cleanup and Destructive Operations**. That exact sentence is NOT in `AGENTS.md`; it is in seed-160 and seed-220, while `AGENTS.md` states the equivalent rule in its own wording. The correction strengthens the rationale rather than weakening it: because the rule is SEEDED, every target repository inherits it, so the conflict between the scan's suggestion and the framework's own policy is shipped to every consumer rather than being local to this repo. | `seeds/160-upgrade-wavefoundry.prompt.md` and `seeds/220-legacy-framework-migration.prompt.md` carry the quoted sentence; `AGENTS.md` **Historical reference preservation** carries the paraphrase. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-12 | Follow the `scan-findings.json` disposition model rather than designing a new one. | The framework already solved "a scanner produced a finding a human must judge once, and the judgment must persist" for secrets. A second store with different shape and vocabulary is how one rule becomes two implementations, which is exactly the divergence wave `1v4mw` existed to repair. | A new bespoke store (rejected: duplicates a solved problem). An inline suppression comment in the source file (rejected as the primary mechanism: it mutates the operator's protected record to silence a report about that record, which is self-defeating; may still be worth it as a secondary affordance). |
| 2026-08-12 | Sequence this change BEFORE widening the journal patterns. | Broader patterns produce more historical-record matches. Widening first would multiply exactly the unresolvable findings this change exists to make resolvable, and would arrive as noise in every downstream repo at once. | Widen first and disposition later (rejected: ships the noise before the remedy). Do both together (rejected: the widening is judgment-heavy and would delay a fix that stands on its own). |
| 2026-08-12 | The framework does not auto-classify a finding as historical. | The channel is report-only precisely so this judgment stays with the operator. A heuristic that guessed wrong would either hide a live stale reference or keep instructing a rewrite of a protected record, and neither failure is visible to the operator. | Heuristic classification by surrounding context (rejected: silent failure in both directions). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A disposition keyed too loosely becomes a blanket file suppression, hiding genuinely new stale references. | AC-2 and AC-4 assert both halves directly: a sibling finding in the same file still reports, and altering the matched text produces a new finding. |
| The store could drift from `scan-findings.json` into a second idiom over time. | AC-6 asserts the shape against that file rather than describing the intent in prose. |
| Marking could be mistaken for fixing, leaving real staleness dispositioned away. | The disposition names the record as historical, not resolved; keep marked findings inspectable rather than deleted, so an audit can review what was marked and by whom. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
