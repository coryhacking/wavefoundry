# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-05

wave-id: `1p3iv indexer-drift-skips-empty-files`
Title: Indexer Drift Skips Empty Files

## Objective

Two threads, one wave. **(a)** Fix the self-repair thrash where files that legitimately produce zero chunks (empty files, all-whitespace, marker-region-dominated content) are flagged as drifted on every incremental index update; the prior 1p399/1p3b9 self-repairing-indexer landing assumed "zero Lance rows = broken state" and didn't account for files that have no chunks to emit. **(b)** Roll the deferred review-surface and naming follow-ups from `1p3dk` Candidate Changes and `1p3ix` scope notes into this wave — cross-weave the new code-correctness review patterns into reality-checker and red-team, ship the canonical-names manifest infrastructure that converts every rename from "ambiguous-by-default" to "ambiguous-only-during-bounded-transition", and complete the convergence half of the config-key rename on top of that infrastructure. Ships in 1.5.0 before the public release.

## Changes

Change ID: `1p3iw-bug drift-skips-zero-chunk-files`
Change Status: `implemented`

Change ID: `1p3ix-enh code-reviewer-state-and-assumption-correctness`
Change Status: `implemented`

Change ID: `1p3j4-enh reality-checker-cross-weave`
Change Status: `implemented`

Change ID: `1p3j5-enh red-team-cross-weave`
Change Status: `implemented`

Change ID: `1p3j6-enh canonical-names-manifest`
Change Status: `implemented`

Change ID: `1p3j7-enh config-key-rename-convergence`
Change Status: `implemented`

Change ID: `1p3jc-enh chunker-module-chunks-for-symbolless-code-files`
Change Status: `implemented`

Completed At: 2026-06-05

## Wave Summary

Wave `1p3iv` (Indexer Drift Skips Empty Files) delivered 7 changes: Drift detection skips files with chunks_emitted=0, Code-reviewer seed gains state-and-assumption + failure-path correctness checklists, Reality-checker routes to State And Assumption Correctness patterns, Red-team routes to Failure Path And Boundary Correctness patterns, Canonical-names manifest as single source for framework renames, Config-key rename converges via bounded removal window, and Chunker emits module-summary chunk for code files with no extractable symbols. Notable adjustments during implementation: Config-key rename converges via bounded removal window: Post-prepare-council fixes landed: drop-case log fidelity (`_rewrite_legacy_config_keys` returns 4-tuples with action discriminator + dropped value; stderr line distinguishes rename from drop) + dry-run report-file parity (`_write_convergence_preview_report` + `_write_convergence_report` write dedicated log files mirroring the 1.5.0 migration shape). 5 new tests added; 2688 total pass. Addresses prepare-council advisory findings.

**Changes delivered:**

- **Drift detection skips files with chunks_emitted=0** (`1p3iw-bug drift-skips-zero-chunk-files`) — 9 ACs completed. Key decisions: --------; Record `chunks_emitted: int` per file_meta entry rather than `non_empty: bool`.
- **Code-reviewer seed gains state-and-assumption + failure-path correctness checklists** (`1p3ix-enh code-reviewer-state-and-assumption-correctness`) — --------; Two new sections (State And Assumption + Failure Path And Boundary) rather than one combined section.
- **Reality-checker routes to State And Assumption Correctness patterns** (`1p3j4-enh reality-checker-cross-weave`) — 4 ACs completed. Key decisions: --------; Cross-reference with applies-when hints, not full pattern duplication.
- **Red-team routes to Failure Path And Boundary Correctness patterns** (`1p3j5-enh red-team-cross-weave`) — 4 ACs completed. Key decisions: --------; Section placed between `## Modes` and `### council-seat` (the last mode), not as a sub-section of any single mode.
- **Canonical-names manifest as single source for framework renames** (`1p3j6-enh canonical-names-manifest`) — 8 ACs completed. Key decisions: --------; Manifest is canonical; constants.py derives from it at import time (preserving the public names `RETIRED_ROLE_NAMES` and `WORKFLOW_REQUIRED_KEYS`).
- **Config-key rename converges via bounded removal window** (`1p3j7-enh config-key-rename-convergence`) — 11 ACs completed. Key decisions: --------; `removed_in: "2.0.0"` for both config-key renames.
- **Chunker emits module-summary chunk for code files with no extractable symbols** (`1p3jc-enh chunker-module-chunks-for-symbolless-code-files`) — 10 ACs completed
## Candidate Changes

To be scaffolded as separate change docs and admitted via `wave_add_change` as the operator works each one. Listed in dependency order — items further down build on items above:

1. ~~**Cross-weave State And Assumption Correctness patterns into `seed-216` (reality-checker).**~~ Admitted and implemented as `1p3j4-enh reality-checker-cross-weave`.

2. ~~**Cross-weave Failure Path And Boundary Correctness patterns into `seed-225` (red-team).**~~ Admitted and implemented as `1p3j5-enh red-team-cross-weave`.

3. ~~**Canonical-names manifest infrastructure.**~~ Admitted and implemented as `1p3j6-enh canonical-names-manifest`.

4. ~~**Convergence half of the config-key rename.**~~ Admitted and implemented as `1p3j7-enh config-key-rename-convergence`.

## Journal Watchpoints

- This wave is a follow-up to `1p3b9` (`1p399 self-repairing indexer drift detection`) — the prior landing assumed all zero-Lance-rows cases were broken state; `1p3iw` adds the missing "legitimately empty" case as a distinct state in `file_meta`.
- The placeholder wave `1p3j1 post-1-5-0-review-surface-followups` was created mid-session as a parking spot for the cross-weaving items, then the operator directed all of its candidates be rolled into this wave. The `1p3j1` directory and its journal were removed; do not re-create them.
- Candidates 1–2 (cross-weaving) are independent and can be admitted in either order. Candidates 3–4 are dependency-ordered (manifest before convergence); the convergence half should not be admitted before the manifest lands.
- Follow-up after all candidates land: repackage `1.5.0` and confirm (a) the indexer drift diagnostic doesn't fire on known-empty files in dogfood (b) the canonical-names manifest is in the pack and used by docs-lint / renderers / upgrade migrator.
- Coordinate gate state: edits cross `framework_edit_allowed` for `indexer.py` + `wave_lint_lib/*` + `upgrade_*.py` and the test files; `seed_edit_allowed` for seed-216 / seed-225 / canonical-names-manifest seed prose. Open/close at change boundary; do not leave open across operator handoff.
- No `WALKER_VERSION` / `CHUNKER_VERSION` / `GRAPH_BUILDER_VERSION` bump required for the indexer-drift fix (additive `file_meta` field). The canonical-names manifest and convergence-half may need version bumps depending on how the migration flow is structured — evaluate at change-doc admission.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-05: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: wave implemented before prepare — operator-driven in-session compression collapsed plan + implement + review into one session, so this readiness review ran retroactively against completed work; two minor advisory findings recorded for follow-on (1p3j7 drop-case log fidelity; 1p3j7 dry-run report-file parity); both low-severity, not release-blockers; strongest-alternative: split into two waves (1p3iv for the bug fix + a separate 1p3j1 placeholder for the follow-ups) — declined per operator direction to work them together and ship under one 1.5.0 packaging cycle; architecture-reviewer and security-reviewer stances assessed implicitly via wave scope checks: no boundary crossing, no trust changes, no auth-or-data-path code; qa-reviewer stance covered by the 2683-test gate (+43 new across the wave). Reality-check verified: load-bearing assumptions per change either confirmed via direct test or noted as field-observable (1p3j4/1p3j5 cross-weave routing effectiveness requires re-evaluation after next council session that uses one of those stances).)
- **Implementation review [code-reviewer/qa-reviewer] — 2026-06-05: BLOCKED**. Findings: (1) `1p3jc` AC-1/AC-2 and Requirement 3 specify a symbolless module chunk with `kind="code"`, `section="<file_stem>"`, and `id="<path>::__module__"`, but the implementation emits `kind="code-summary"`, `section="summary"`, and `id="<path>#summary"` via `_chunk_code_summary`; the tests assert the implementation shape instead of the admitted AC shape. Reconcile by either changing implementation/tests to the admitted contract or explicitly narrowing the change doc ACs. (2) `1p3jc` AC-5 says marker-region-dominated files with no other content emit zero chunks, but a direct chunker check on `<!-- waveframework:foo begin --> ... <!-- end -->` produced chunks for both markdown and Python paths; no AC-5 regression test was found. Add marker-region stripping/skip behavior or mark the AC intentionally not met with rationale before delivery approval.
- **Implementation review fixes [code-reviewer/qa-reviewer] — 2026-06-05: RESOLVED**. `1p3jc` now emits the symbolless fallback as a real module `code` chunk with `id="<path>::__module__"` and `section="<file_stem>"`; tests assert the admitted AC shape for Python and TypeScript and module-searchability for Go/Rust cases. Marker-region-only files now return zero chunks before dispatch; chunker and indexer-facing regressions cover markdown/Python marker-only content and `_chunks_for_file` zero-output behavior. Verification: `python3 .wavefoundry/framework/scripts/run_tests.py` — 2702 tests across 27 files, OK.

## Review Evidence

- wave-council-readiness: approved 2026-06-05 — standard tier (3 stances: reality-checker, red-team, docs-contract). All six changes implemented and verified: 2683 tests pass, docs-lint clean. Strongest challenge: wave was implemented before prepare (operator-driven in-session compression of the lifecycle), so the readiness review ran retroactively. Two minor advisory findings recorded: (a) `1p3j7` convergence migration's drop-case stderr line uses identical wording to the rename-case, losing the dropped-legacy-value from the log (operators recovering "wait, I had different values" would need git history); (b) `1p3j7` dry-run path prints planned actions to stderr without writing a preview report file, asymmetric with the existing `upgrade-migration-1.5.0.preview.log` pattern — documented as out-of-scope in the change doc but the CHANGELOG bullet doesn't note the asymmetry. Both findings are low-severity, addressable in follow-on if signal demands, not release-blockers. One assumption gap noted: `1p3j4`/`1p3j5` cross-weave routing effectiveness is field-observable only — re-evaluate after next council session that uses one of those stances. Strongest alternative declined: split into two waves (consumed `1p3j1` placeholder instead per operator direction).
- post-prepare-council fixes: addressed 2026-06-05 — both advisory findings (a) and (b) from the prepare-council review landed in-session per the fix-now-not-later policy. **(a)** `_rewrite_legacy_config_keys` now returns `(legacy, canonical, action, dropped_value)` 4-tuples where `action` is `"rename"` or `"drop"`; the convergence migration's stderr line distinguishes the two cases and the dropped value is captured for log recovery. **(b)** Dry-run writes `.wavefoundry/logs/upgrade-convergence-migration.preview.log` (parity with the 1.5.0 migration's `.preview.log`); real-run writes `.wavefoundry/logs/upgrade-convergence-migration.log` with full per-record detail including dropped values rendered as JSON for the drop case. 5 new tests; 2688 total pass. CHANGELOG `1p3j7` bullet updated to describe the new log surfaces. Field-observation assumption gap for `1p3j4`/`1p3j5` remains open for next session per its nature.
- implementation-review: blocked 2026-06-05 — `1p3jc` AC reconciliation failed for module-summary chunk shape and marker-region-dominated zero-chunk behavior. Delivery approval not recorded.
- implementation-review-fixes: resolved 2026-06-05 — `1p3jc` module fallback shape and marker-region-only zero-chunk behavior fixed; `test_chunker.py` and `test_indexer.py` regressions added; full framework suite passes (2702 tests).
- wave-council-delivery: approved 2026-06-05 — standard tier; delivery evidence reconciled after implementation-review fixes. Seat synthesis: code-reviewer/qa-reviewer blockers for `1p3jc` were resolved by changing the implementation to the admitted module chunk contract and adding marker-region-only zero-chunk coverage; architecture/security impact remains low because the fixes stay inside chunker/indexer semantics and do not cross trust boundaries; docs-contract review passes because the change doc and wave record now carry the corrected evidence trail. Verification evidence: `python3 .wavefoundry/framework/scripts/run_tests.py` passed (2702 tests across 27 files), `wave_validate` passed (`docs-lint: ok`). Residual risk: semantic framework index remains stale until refreshed, but close correctness is supported by source review, tests, and docs lint.
- operator-signoff: approved 2026-06-05 — operator explicitly requested "close wave".

## Dependencies

- No external wave dependencies.
