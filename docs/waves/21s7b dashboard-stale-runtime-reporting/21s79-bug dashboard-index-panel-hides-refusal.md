# Dashboard Index panel reports a refused read as "not built"

Change ID: `21s79-bug dashboard-index-panel-hides-refusal`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-26
Wave: 21s7b dashboard-stale-runtime-reporting

## Rationale

On 2026-10-26 the dashboard's Index dialog showed Semantic "not built", Graph "not built" and "updated 1w ago" while `index_health` reported a ready index (42,252 doc and 15,017 code vectors, graph of 74,566 nodes built that day). The dashboard process had been running since the previous day; a newer indexer had since written the index, so the index-compatibility guard refused the old process's reads with `index_runtime_stale`. The live `/api/health` payload carried that diagnostic on the graph section, and the dashboard discarded it. Restarting the dashboard fixed the display.

Two code paths turn a refusal into "not built" (both verified by execution, see Decision Log):

- `_read_store_build_meta` (`.wavefoundry/framework/scripts/dashboard_lib.py`) re-executes `index_state_store` on every call. Under a stale capture that import raises `IndexCompatibilityError` from `index_compatibility.register_loaded_source()`, the bare `except Exception` returns `{}`, and `_index_stats` reports `present: False`. The header age then falls back to `built_at` from `index-build-stats.json`, which was nine days old.
- `read_graph_payload` returns `present: False` with `diagnostic.code == "index_runtime_stale"`, but `GraphIndexSection` and `IndexSection` in `.wavefoundry/framework/dashboard/dashboard.js` branch only on `present`.

"Not built" sends the operator toward a rebuild, which the guard's own message says not to do ("preserve the newer index instead of rebuilding it").

## Product Intent

An operator looking at the dashboard's Index dialog can tell a missing index apart from an index the dashboard cannot read, and sees the recovery action the framework already names (restart the dashboard) instead of an instruction-shaped "not built". Missing indexes still read "not built". The compatibility guard keeps refusing stale reads; only the reporting changes. AC-1 together with AC-2 tests the intent.

## Requirements

1. When the dashboard's store build-meta read fails, the health payload's `index.project` carries a typed `diagnostic` (code, message, recovery usage) instead of an indistinguishable empty result. A compatibility refusal keeps its own code (`index_runtime_stale`, `index_version_newer`, `index_compatibility_unproven`); any other read failure uses a distinct generic code. A store that is simply absent yields no diagnostic.
2. The Index dialog's Semantic and Graph sections render the diagnostic (a short human label plus the recovery action) whenever one is present, and render "not built" only when the section is absent with no diagnostic. Only `index_runtime_stale` is labelled as restart-required; `index_version_newer` and `index_compatibility_unproven` show their own message without promising that a restart fixes them (installed sources older than the index, for example after a branch switch, are not fixed by a restart).
3. When the store read is refused, the dialog header does not present the `index-build-stats.json` `built_at` as the index's update time.
4. The compatibility guard's behavior is unchanged: the dashboard does not bypass or weaken `index_compatibility` to make the read succeed.

## Scope

**Problem statement:** the dashboard reports a refused or failed index read as an absent index, hiding the recovery action.

**In scope:**

- `dashboard_lib.py`: typed diagnostic from the build-meta read; health payload shape; header age suppression on refusal.
- `dashboard.js` (and `dashboard.css` if a style is needed): render diagnostics in `IndexSection` and `GraphIndexSection`.
- Tests in `test_dashboard_server.py`.

**Out of scope:**

- Detecting staleness outside the Index dialog (change `21s7a-enh dashboard-stale-runtime-banner`).
- The dashboard's high CPU and watcher stalls observed on the stale process (cause unverified; see Risks).
- Any change to `index_compatibility`, the MCP server, or `index_health`.
- Other dashboard reads that swallow the refusal without misreporting an absent index: `dashboard_server._index_is_stale` (its `stale` field is not rendered) and the graph focus-neighborhood error text (already shows the exception).

**Platform behavior:** pure in-process Python and browser rendering; identical on Windows, macOS, Linux and WSL2. No path, process or filesystem semantics change.

## Acceptance Criteria

- [x] AC-1: With the dashboard modules loaded and the runtime capture then made stale (the technique used in the Decision Log probe), `collect_health` returns `index.project.diagnostic.code == "index_runtime_stale"` alongside the existing graph diagnostic; with no index store present it returns no diagnostic. Fails before the fix, where `index.project` carries no diagnostic.
- [x] AC-2: The Index dialog shows the restart-required diagnostic for both Semantic and Graph when the payload carries one, and "not built" only when there is no diagnostic. Required evidence is a rendered check of a dashboard whose loaded capture is made stale after startup; a dashboard.js source-contract test is supplementary and does not satisfy this AC alone. Fixture mechanics are designed during implementation and must not touch the repository's index or the operator's running dashboard.
- [x] AC-3: Under a refused store read, the dialog header shows no "updated" age derived from `index-build-stats.json`.
- [x] AC-4: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Return a typed result from `_read_store_build_meta` (summary or diagnostic) and carry the diagnostic into `_index_stats` / `collect_health`.
- [x] Map compatibility codes to recovery text per Requirement 2; generic failures get their own code.
- [x] Suppress the stats-file age when the store read is refused.
- [x] Render diagnostics in `IndexSection` and `GraphIndexSection`.
- [x] Tests: stale-capture health payload, absent-store control, dashboard.js contract.
- [x] Rendered check against a dashboard with a stale capture (required evidence for AC-2).

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| payload | implementer | none | dashboard_lib diagnostic and tests |
| render | implementer | payload | dashboard.js sections and contract test |


## Serialization Points

- `.wavefoundry/framework/scripts/dashboard_lib.py`, `.wavefoundry/framework/dashboard/dashboard.js`, `.wavefoundry/framework/dashboard/dashboard.css`, `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Affected Architecture Docs

N/A: confined to the dashboard's read and render path; no module boundary, data flow, or verification seam changes. The health payload gains an optional field consumed only by `dashboard.js`.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The payload must carry the cause for anything to render it. |
| AC-2 | required | The operator-visible defect. |
| AC-3 | important | The nine-day age was misleading but secondary. |
| AC-4 | required | Change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-26 | Planned from a live incident; dashboard restarted to clear it. | Live `/api/health` showed `graph.project.diagnostic.code == "index_runtime_stale"` and `index.project.present == false`; after `wf_restart_dashboard` both read present. |
| 2026-10-26 | Readiness note: the Risks row "Only the three compatibility codes map to restart guidance" predates the readiness repair; Requirement 2 governs (only `index_runtime_stale` is restart-required). Left unedited to keep the readiness receipt. | Council-readiness synthesis residual note 1. |
| 2026-10-26 | Delivered. `_read_store_build_meta` returns `(summary, diagnostic)`; an absent store (no `index.sqlite`) is checked before the re-exec so it never yields a diagnostic, even under a stale capture (pins the qa-reviewer readiness note). `collect_health` attaches `index.project.diagnostic` and blanks `built_at` on refusal. `MissingIndexSection` renders both Index dialog sections: restart label only for `index_runtime_stale`, `index_health()` for the other compatibility codes, the payload's recovery for anything else. Diagnostic text is rendered as children and a `title` attribute only. | `test_dashboard_server.DashboardStaleRuntimeReportingTests` (10 tests, OK). Known-bad: the same tests against HEAD's `dashboard_lib.py`, `dashboard_server.py` and `dashboard.js` in a scratch copy fail 8 of 10 (the two controls pass by design). Rendered: `.wavefoundry/work/21s7b/evidence/current-index.png` (control), `stale-index.png` (both sections restart-required, no updated age), `restarted-index.png`. |
| 2026-10-26 | Follow-up (not this scope): two other surfaces still read a refusal as absent: the Graph view's "Graph index has not been built yet." and the main Index metric card's "Missing". The global notice from `21s7a` now explains both while the runtime is stale. | Seen in `stale-graph.png` and `stale-main.png`. |
| 2026-10-26 | Delivery review follow-ups (one future change, not this scope): (I1) for `index_version_newer` and `index_compatibility_unproven` no notice shows, so the Index metric card ("Missing") and Graph view ("not built yet") still contradict the dialog; (M1) a `graph_publication_in_flight` diagnostic now reads "The index could not be read" and should read as in progress; (M2) the `title` tooltip for non-stale compatibility codes carries the exception's restart text, contradicting the visible `index_health()` action; the semantic path maps migration failures to `index_health()` where the graph path names `wf_upgrade_status()`; the compatibility code set is defined in three places; the JS render path is checked only by source-string tests plus screenshots. | Red-team, code-reviewer and qa-reviewer delivery reports, cycle 0. |
| 2026-10-26 | Gapfill: shell was used for executed probes only (scratch-copy known-bad runs, a scratch dashboard on port 43991 and headless Chrome screenshots); code reads went through `code_read`/`code_keyword`. | n/a |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-26 | Carry a typed diagnostic from the server payload into both Index sections. | Reuses the diagnostic shape `graph_snapshot` already produces; one rendering rule covers both sections. Efficacy: replaying the incident, both sections would have shown restart-required instead of "not built". It is advisory; the operator acts because the text names a one-step action. It cannot misfire on a missing index because absent-store reads produce no diagnostic. | (B) Render only the graph diagnostic already present: the semantic section stays opaque because its exception is swallowed. (C) Let dashboard reads bypass the runtime guard: defeats the guard, which exists to stop old code misreading a newer store. |
| 2026-10-26 | Readiness repair (red-team F3, F4, F6): restart label only for `index_runtime_stale`; rendered check is required AC-2 evidence; two other swallowing reads recorded as out of scope. | `graph_snapshot._read_failure` gives restart guidance for all three compatibility codes, which is wrong when installed sources are older than the index. The other two reads do not produce the misleading "not built" this change fixes. New review surface: per-code labels. | Reuse `_read_failure` text unchanged (wrong for `index_version_newer`). |
| 2026-10-26 | Mechanism verified by execution, not inference. | Fresh-process probe: after preloading `dashboard_lib`, `index_state_store`, `graph_snapshot` and replacing `index_compatibility._SOURCE_HASHES`, `read_build_summary` still succeeded (module already imported), `_read_store_build_meta` returned `{}` (re-import raised `index_runtime_stale`), `lexical_statistics` returned `ready`, and `read_graph_payload` returned `present: False` with `index_runtime_stale`. That matches the incident screenshot exactly. | n/a |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The stale process also ran at about 73% CPU with repeated 30s watcher stalls; this change does not address that, and the link to staleness is unverified. | Out of scope; re-observe after `21s7a` lands and plan separately if it recurs on a current process. |
| A generic read failure could be relabelled restart-required. | Only the three compatibility codes map to restart guidance; others keep a distinct code and message. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
