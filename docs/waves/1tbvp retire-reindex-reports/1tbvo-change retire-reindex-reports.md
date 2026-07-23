# Retire the Daily Reindex Report Artifact

Change ID: `1tbvo-change retire-reindex-reports`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-22
Wave: `1tbvp retire-reindex-reports`

## Rationale

The docs gardener writes `docs/reports/reindex-<date>.md` on every day it stamps `Last verified:` on changed docs — one file per active working day, 30 accumulated in this repository. An investigation (2026-07-22, operator-directed) found no consumer anywhere in the framework, and three subsystems carry explicit code to IGNORE them: drift detection exempts `docs/reports/` because dated reindex reports "dominated the false-positive tail" (`index_state_store.py` `DRIFT_EXEMPT_PREFIXES`), link and metadata validators skip the prefix, and `reconcile_scan` excludes it. The reports' content (which docs were stamped on which day) is fully recoverable from git history, and the gardener already prints the stamped paths to stdout and returns them in its envelope. The one measured effect of the artifact on the system was negative. Operator decision: stop writing them entirely (option 2 over a rolling single report or bounded retention) and delete the backlog.

## Requirements

1. **The gardener stops writing reindex reports.** `gardener_run` no longer creates or refreshes `docs/reports/reindex-<date>.md`; the dead `render_report` helper is removed. Stdout still reports the outcome (stamped-path summary on a stamping run; the existing "ok (nothing to report)" on an empty run), and the returned updated-paths list is unchanged in meaning (it no longer includes a report path). `ensure_manifest`, `docs/reports/` as a staging directory for other report types, and all existing lint/drift/scan exemptions for the prefix are untouched.
2. **Tests pin the retirement:** gardener tests assert a stamping run creates NO report file (replacing the report-creation assertions); the empty-run tests keep their existing no-report behavior.
3. **Seeds stop teaching the artifact:** seed 140 (reindex-ongoing) drops its "Refresh `docs/reports/reindex-<YYYY-MM-DD>.md`" step; seed 190's report-archival step drops the reindex-report example and the gardener-regeneration caveat sentence (the gardener no longer regenerates reports); general report archival for other report types stays.
4. **This repository's 30 dated reindex reports are deleted** (git history preserves their content; the archival-into-wave-folders alternative was rejected as busywork for artifacts nothing reads). Other files under `docs/reports/` are untouched.

## Scope

**Problem statement:** a write-only daily artifact accumulates indefinitely with no consumer, no retention mechanism, and a history of causing drift-detection noise.

**In scope:**

- `docs_gardener.py` report-writing path and `render_report`
- `test_docs_gardener.py` report assertions
- Seeds 140 and 190 wording
- Deletion of the 30 local `reindex-*.md` files

**Out of scope:**

- `docs/reports/` as a directory and its lint/drift/scan exemptions (other report types still stage there)
- The gardener's stamping, manifest, and session-handoff behavior
- Retention automation for other report types (nothing else auto-generates dailies)

## Acceptance Criteria

- [x] AC-1: a stamping gardener run against a fixture repo stamps docs and writes NO file under `docs/reports/`; the empty-run behavior is unchanged; `render_report` no longer exists.
- [x] AC-2: no shipped seed instructs creating or refreshing a reindex report; seed 190's general report archival for other report types remains.
- [x] AC-3: zero `docs/reports/reindex-*.md` files remain in this repository; all other reports remain; docs gate passes and the full framework suite is green.

## Tasks

- [x] Remove the report-writing path + `render_report`; update gardener tests.
- [x] Update seeds 140 and 190.
- [x] Delete the 30 local reports; docs gate; full suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| gardener | implementer | — | Code + tests |
| surfaces | implementer | — | Seeds 140/190 |
| local-cleanup | implementer | gardener | Delete backlog after the producer stops |

## Serialization Points

- Delete the backlog after the producer change lands, so no new report reappears mid-wave.

## Affected Architecture Docs

N/A — removes a write-only generated artifact; no boundary, flow, or verification impact (drift/lint exemptions for the prefix are retained unchanged).

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The retirement itself; ships to all target repos. |
| AC-2 | required | Stale seed instructions would resurrect the artifact. |
| AC-3 | required | The operator-directed local cleanup + standard gates. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-22 | Drafted from the operator decision (option 2 of the three presented). Investigation evidence: producer at `docs_gardener.py:282`; zero consumers by census; three explicit ignore/exempt sites (`DRIFT_EXEMPT_PREFIXES`, link/metadata validator skips, `reconcile_scan` exclusion); 30 dated files of 34 total in `docs/reports/`; only seed 140 teaches the artifact, seed 190 mentions it as an archival example. | Session investigation (code_keyword censuses, code_read of `gardener_run`) |
| 2026-07-22 | Implemented: report-writing path and `render_report` removed from `gardener_run` (stamping run now prints `stamped N doc(s)`; empty-run output unchanged); new `test_stamping_run_writes_no_reindex_report` pins no-report + `render_report` absence; seeds 140/190 updated; pre-deletion census zero references; 30 dated reports deleted, 4 other reports remain; docs gate clean. | `test_docs_gardener` 9 OK; census output; `wf_validate_docs` ok |
| 2026-07-22 | Operator mid-implementation directive: remove tests that are no longer relevant. Removed `test_empty_run_leaves_existing_report_untouched` (tested the retired empty-run-vs-existing-report interaction) and simplified the empty-run test to `test_empty_run_prints_nothing_to_report` (its no-report assertion is subsumed by the stronger stamping-run test). Kept the reindex-named FIXTURES in `test_doc_drift`/`test_docs_lint`: they exercise the retained `docs/reports/` prefix exemptions, which stay live for other report types. Gardener+drift+lint modules: 927 tests OK. | Module run output |
| 2026-07-22 | Gapfill: implement-stage MCP retrieval is near zero by design — the exploration (producer/consumer/exemption censuses, `gardener_run` read) ran at plan stage via code_keyword/code_read; implementation was mechanical removal at already-located sites plus a docs-only deletion. | Plan-stage retrieval telemetry |
| 2026-07-22 | Full suite green post-implementation and post-pruning: 6,138 tests across 59 files OK in a single run. AC-1 through AC-3 met. | Suite output |
| 2026-07-22 | Second operator review P2 (`run-garden-parses-bounded-output`): run_garden parsed the contract lines from the BOUNDED output (200k first-chars cap), so a 6,000-record run reported 2,273 with a corrupted final path. Repair: parse the COMPLETE result.stdout for contract records; the bound now applies only to the human-facing `output` field; over-cap regression (6,000-record >200k fixture) pins all records and full paths surviving with `output_truncated` true. | `events.jsonl` cycle-2 chain; `test_over_cap_output_parses_all_records_from_complete_stdout` |
| 2026-07-22 | Operator review P1 (`run-garden-stdout-contract-break`): the stdout change broke `run_garden()`'s implicit 'wrote'-grep contract, so `wf_garden_docs` returned files_updated 0 on stamping runs and never triggered the background docs-index refresh; the suite missed it because `RunGardenTests` fed a hand-written 'Wrote docs/foo.md' fixture (the recorded fixture-echo defect class). Repair: stable `docs-gardener: updated <path>` per-path output contract (documented on both sides), exact-prefix parsing in `run_garden`, canonical-producer integration tests running the real gardener subprocess (stamping + empty), a negative test proving prose/legacy lines never count, and `GardenDocsIndexRefreshTriggerTests` pinning refresh-on-stamping / no-refresh-on-empty. Live post-reload MCP probe: backdated a tracked doc's stamp, real `wf_garden_docs(mode='run')` returned files_updated 1 with the doc listed and restored the stamp; empty run returned 0. | `events.jsonl` cycle-1 chain; live probe envelopes; module runs 8+8 OK |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-22 | Stop writing reindex reports entirely; delete the backlog. | No consumer exists; content duplicates git history; the artifact's one measured system effect was drift false-positive noise (patched by exemption); stdout + envelope already carry the same information. | Rolling single `reindex-latest.md` (keeps a receipt file nothing needs); N-day retention (automates upkeep of an unread artifact); archiving dailies into wave folders per seed 190 (busywork for unread artifacts; rejected by operator). |
| 2026-07-22 | Keep `docs/reports/` and all its exemptions. | Other report types (audits, validation plans, migration notes, downstream tests) legitimately stage there; the exemptions are keyed to the prefix, not to reindex reports specifically. | Removing the directory or narrowing exemptions (out of scope, would touch unrelated report flows). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A doc or test references a dated reindex report by name. | Repository-wide census before deletion; docs gate link integrity after; test fixtures that use reindex-named files to test skip-prefix behavior are self-contained temp-dir fixtures and unaffected. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
