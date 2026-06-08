# Deferred ACs And Tasks Read As Outstanding While Open, Completed Once Closed

Change ID: `1p45a-enh deferred-items-count-as-completed`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-06-08
Wave: 1p458 dashboard-progress-rendering-fixes

## Rationale

Wave `1p31b` (1p32k) introduced `[~]` "intentionally-deferred" ACs and tasks and made the dashboard **exclude** them from progress denominators, surfacing them as a separate "· N deferred" tally (e.g. `ACS 3048/3177 · 8 deferred`). The operator's pain is the trailing tally on **finalized** work: once a wave is closed, a deferral is a settled decision — it should read as resolved, not as an outstanding badge.

The original plan for this change folded `[~]` into the completed total **unconditionally** (open and closed alike). The Prepare-wave red-team flagged that this masks in-flight de-scoping: a change that deferred most of its ACs while the wave is still active would render a green "done" bar with no signal that scope was dropped. The operator's resolution is to **gate the fold on wave closure**:

- **Closed wave:** a `[~]` deferred AC/task counts as **completed** (numerator + denominator), consistent with the existing closed-wave treatment where every in-scope item reads done. Contributes to 100%; no "· N deferred" suffix.
- **Open / active wave:** a `[~]` deferred AC/task counts in the **denominator** but as **not-done** (outstanding). An open change with unresolved deferrals reads **below** 100% until the wave is closed, keeping de-scoping visible. No "· N deferred" suffix.

The per-item `~` marker in the detail dialog is retained in both states so reviewers can still see *which* items were deferred. This deliberately reverses the **denominator** part of `1p31b` (deferred now sit in the denominator) and reverses its closed-wave exclusion (deferred now fold into done at close), while preserving the `[~]` parse and marker.

The change rides the open-vs-closed branch the dashboard already has:

- Backend `dashboard_lib.py`: `_parse_tasks` (`:461-488`) computes `in_scope_total = len(tasks) - deferred` (`:481`) — the deferred subtraction is removed so the denominator includes deferred; per-change `completed` stays `[x]`-only. `_parse_ac_items` (`:494-532`) sets `"done": done and not is_deferred` (`:528`) — kept (deferred read not-done, correct for the open numerator). The progress-snapshot builder (`:620-654`) filters `in_scope = [item for item in items if not item.get("deferred")]` (`:628`) and branches `closed → ac_done += len(in_scope)` else `ac_done += sum(done)` (`:631-634`); the deferred filter is removed (denominator includes deferred) so the closed branch folds deferred into done and the open branch leaves them outstanding. Task counting branches the same way at `:615-619`. `_completed_ac_counts` (`:535-544`) keeps skipping deferred (it is the open/per-change "actually-done" count). `_deferred_ac_counts` (`:547-555`) and the `tasks_deferred` / `ac_deferred_counts` dataclass fields (`:694`, `:698`) survive only if a consumer still needs them after the suffix is removed.
- Frontend `dashboard.js`: `ProgressCard` (`:482-530`) filters `visibleAcItems(c).filter(a => !a.deferred)` for both `acTotal` (`:513`) and the closed/open `acDone` branch (`:514-517`), and sums `tasks_total`/`tasks_completed` with a closed/open branch (`:508-511`); the `!a.deferred` denominator filter is removed and the closed branch counts all in-scope incl deferred. `ProgressRow` (`:449-480`) drops the `deferred` arg and the `· N deferred` suffix (`:471-478`). `waveStats` (`:158-178`) and `acProgressStats` (`:184-201`) are **status-agnostic** today and must be reconciled with the open/closed treatment (or confirmed unused) so per-wave cards / mini-graphs do not drift from the ACS/TASKS bars.

## Requirements

1. **Closed-wave fold:** for a closed wave's ACS/TASKS bars, a `[~]` deferred AC/task counts as completed in **both** the numerator and the denominator — consistent with the closed-wave rule that all in-scope items read done — so a closed wave with deferrals reads 100%.
2. **Open-wave outstanding:** for an open/active wave's ACS/TASKS bars, a `[~]` deferred AC/task counts in the **denominator** but **not** in the completed numerator, so the bar reads below 100% until the wave is closed (e.g. a change with 8 `[x]` and 2 `[~]` reads `8/10` while open and `10/10` once closed).
3. **No deferred suffix:** the "· N deferred" suffix rendered by `ProgressRow` (`dashboard.js:476`) is removed in both states — the deferred count is never surfaced as a separate tally on the bars.
4. **Cross-surface consistency:** the open/closed treatment is applied identically across the backend per-change counts (`dashboard_lib.py`) and every frontend surface (`ProgressCard` ACS/TASKS bars, the wave card, and mini-graphs) so all agree — no double counting, no off-by-deferred drift, including for aggregate bars that combine closed and open waves.
5. **`not-this-scope` unchanged:** `not-this-scope` ACs continue to be excluded entirely; an AC that is **both** `[~]` and `not-this-scope` stays excluded (it is not folded into completed in either state). Only in-scope `[~]` items are affected.
6. **Marker retained:** the `[~]` checkbox parse and the per-item `~` glyph / `--deferred` styling in the AC/Tasks detail dialogs (`dashboard.js:963-988`, `:1007+`) are retained — deferred items remain visually identifiable even though they read as done once closed.

## Scope

**Problem statement:** `[~]` deferred ACs/tasks are excluded from progress denominators and shown as a separate "· N deferred" tally (`dashboard_lib.py:481`/`:628`, `dashboard.js:513`/`:476`). The operator wants them counted as completed **once the wave is closed**, and shown as outstanding (in the denominator, not done) while the wave is open — with no separate tally in either state.

**In scope:**

- Backend `dashboard_lib.py`: remove the deferred subtraction/filter from the **denominator** in `_parse_tasks` (`:481`) and the progress-snapshot builder (`:628-630`); keep the closed-vs-open numerator branch (`:615-619`, `:631-634`) so closed folds deferred into done and open leaves them outstanding. Keep `_completed_ac_counts` skipping deferred (open/per-change "done").
- Frontend `dashboard.js`: include deferred in the `ProgressCard` denominator (`:513`) and the closed-branch numerator (`:514-517`); keep the open-branch numerator counting only `done`; drop the `deferred` arg and `· N deferred` suffix in `ProgressRow` (`:471-478`).
- Reconcile the status-agnostic `waveStats` (`:158-178`) / `acProgressStats` (`:184-201`) with the open/closed treatment, or confirm and document that they are unused for the affected surfaces.
- Retain `[~]` parsing and the per-item `~` glyph / `--deferred` styling in the detail dialogs.
- Remove the now-dead `.progress-row-deferred` CSS rule in `dashboard.css` once the suffix is gone; keep the detail-dialog `--deferred` / `status-deferred` styles.
- Update or remove tests that assert the old deferred-exclusion/unconditional semantics; add tests for the closed-fold, open-outstanding, no-suffix, and `[~]`×`not-this-scope` behaviors.

**Out of scope:**

- Removing the `[~]` mark or its detail-dialog glyph (kept for visibility).
- Changing `not-this-scope` AC handling.
- Any change to how `[~]` is authored/linted in change docs, or to the close-gate that requires `[x]`/`[~]` at close.
- The recent-changes id-wrap fix (sibling `1p459`).

## Acceptance Criteria

- [x] AC-1: For a **closed** wave, `[~]` deferred ACs/tasks count as completed in both numerator and denominator — a closed wave with deferrals reads 100% on its ACS/TASKS bars (e.g. 8 `[x]` + 2 `[~]` reads `10/10`), with no "· N deferred" suffix.
- [x] AC-2: For an **open/active** wave, `[~]` deferred ACs/tasks count in the denominator but not as done, so the bar reads below 100% while deferrals are unresolved (the same 8 `[x]` + 2 `[~]` change reads `8/10` while open) and resolves to 100% when the wave is closed.
- [x] AC-3: The "· N deferred" suffix is no longer rendered by `ProgressRow` in either state.
- [x] AC-4: Backend `dashboard_lib.py` and the frontend `dashboard.js` apply the same open/closed treatment; the wave card, mini-graphs, and ACS/TASKS bars agree (no double counting, no off-by-deferred drift), including aggregate bars combining closed and open waves. `waveStats` / `acProgressStats` are reconciled with the open/closed treatment or shown unused for these surfaces.
- [x] AC-5: `not-this-scope` ACs remain fully excluded (unchanged); an AC that is both `[~]` and `not-this-scope` stays excluded in both states (a dedicated test covers this combination). Only in-scope `[~]` items are affected.
- [x] AC-6: The AC/Tasks detail dialogs still render `[~]` items with the `~` marker and `--deferred` styling (visibility retained) even though they read as completed once closed.
- [x] AC-7: The dashboard counting tests asserting the previous semantics are migrated in `test_dashboard_server.py` — the `acTotal … !a.deferred` source-string assertion (`:351-352`), the `ProgressRow` `deferred` signature/props assertions (`:705-710`), the task in-scope-total assertion (`:744-758`), and `test_deferred_acs_excluded_from_progress_denominator` (`:761-785`, rename + re-assert as open-outstanding / closed-fold). **Do not** modify the `[~]` parse / docs-lint / close-gate tests in `test_docs_lint.py`, `test_server_tools.py`, or `test_install_log_lib.py` (preserved contract). New tests cover AC-1..AC-5; `python3 .wavefoundry/framework/scripts/run_tests.py` is green.

## Tasks

- [x] `dashboard_lib.py` `_parse_tasks` (`:464-488`): set `total = len(tasks)` (include deferred in the denominator); keep `completed` as `[x]`-only and `deferred` for the marker. The closed/open numerator branch in the snapshot builder then folds vs. leaves-outstanding.
- [x] `dashboard_lib.py` progress-snapshot builder (`:620-654`): drop the `in_scope` deferred filter (`:628`) so the AC denominator includes deferred; keep `closed → ac_done += len(in_scope)` / `open → ac_done += sum(done)` (`:631-634`) and the task branch (`:615-619`) so closed folds deferred into done and open leaves them outstanding. Keep `_parse_ac_items` `"done": done and not is_deferred` (`:528`) and `_completed_ac_counts` skipping deferred (`:535-544`). Guard the `[~]`×`not-this-scope` edge (AC-5).
- [x] `dashboard.js` `ProgressCard` (`:500-518`): remove the `!a.deferred` denominator filter (`:513`); keep the closed-branch numerator counting all in-scope (now incl deferred) and the open-branch counting only `done`; apply the same to tasks (`:508-511`).
- [x] `dashboard.js` `ProgressRow` (`:449-480`): remove the `deferred` arg and the `· N deferred` suffix (`:471-478`).
- [x] `dashboard.js` `waveStats` (`:158-178`) / `acProgressStats` (`:184-201`): reconcile with the open/closed treatment (make status-aware for the closed fold) or confirm + document they are unused for the wave card / mini-graphs.
- [x] `dashboard.css`: remove the now-dead `.progress-row-deferred` rule once the suffix is gone; keep the detail-dialog `--deferred` / `status-deferred` styles (still used).
- [x] Keep `[~]` parse + detail-dialog `~` marker (`dashboard.js:963-988`) intact; remove dead aggregate-deferred plumbing (`ac_deferred_counts` / `tasks_deferred` / snapshot `deferred`) only if no consumer remains.
- [x] Migrate/replace the `test_dashboard_server.py` counting tests and add new open-outstanding / closed-fold / no-suffix / `[~]`×`not-this-scope` coverage; leave the `[~]` parse/lint/close-gate tests untouched.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py`; run `.wavefoundry/bin/docs-lint` on this plan.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| backend-counts | Engineering | — | `dashboard_lib.py`: deferred in denominator; closed folds into done, open leaves outstanding. |
| frontend-stats-and-bar | Engineering | backend-counts | `dashboard.js`: mirror the open/closed treatment; drop `· N deferred` suffix; reconcile `waveStats`/`acProgressStats`. |
| tests | Engineering | frontend-stats-and-bar | Migrate old-semantics tests; add open-outstanding + closed-fold + no-suffix + not-this-scope coverage. |


## Serialization Points

- `.wavefoundry/framework/scripts/dashboard_lib.py` — single owner here; coordinate with any other in-flight dashboard work.
- `.wavefoundry/framework/dashboard/dashboard.js` — shared with sibling `1p459` (recent-changes id wrap). The two touch different functions (`Activity` vs progress stats/`ProgressRow`); sequence and re-verify after both land.
- `.wavefoundry/framework/dashboard/dashboard.css` — `1p459` adds a scoped `.wave-change-id` rule; this change removes `.progress-row-deferred`. Coordinate so neither clobbers the other.

## Affected Architecture Docs

N/A — a confined progress-accounting/rendering change in the dashboard layer (`dashboard_lib.py` + `dashboard.js`); it adjusts a counting policy from wave `1p31b` but introduces no new module boundary, data flow, or verification surface.

## AC Priority

_Confirmed at Prepare wave 1p458 (2026-06-08), re-confirmed after the status-conditional refinement — required/important classifications interrogated by the readiness council and stand as below._


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | Closed-wave fold — resolves the operator's trailing-tally pain on finalized work. |
| AC-2 | required   | Open-wave outstanding — the red-team fix; keeps in-flight de-scoping visible. |
| AC-3 | required   | Remove the "· N deferred" label per the operator's intent. |
| AC-4 | required   | Backend/frontend and all surfaces must agree to avoid mismatched totals. |
| AC-5 | required   | Must not accidentally fold `not-this-scope` (incl `[~]`×not-this-scope) into completed. |
| AC-6 | important  | Retain deferred visibility in detail while counting as complete once closed. |
| AC-7 | required   | Migrate old-semantics tests + cover the new open/closed behavior. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-08 | Status-conditional fold implemented on the existing open/closed branch: deferred `[~]` items now sit in the denominator (`_parse_tasks` total, snapshot builder, `ProgressCard`/`acProgressStats`/`waveStats`), count as outstanding while open and fold into done once the wave is closed; `· N deferred` suffix + `.progress-row-deferred` CSS removed; `[~]` parse + detail `~` marker retained. | `run_tests.py` green (2782); new open-outstanding (`8/10`) + not-this-scope + closed-fold + no-suffix tests pass; `test_docs_lint`/`test_server_tools` `[~]` contract untouched. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | Gate the fold on wave closure: `[~]` deferred ACs/tasks count as **completed** only once the wave is **closed**; while the wave is **open** they sit in the denominator as **outstanding** (not done), so the bar reads below 100% until close. Drop the "· N deferred" suffix in both states. | Resolves the operator's trailing-tally pain on finalized work while addressing the Prepare-council red-team challenge — an unconditional fold lets an open change that deferred most of its work read "done", masking in-flight de-scoping. Rides the existing open-vs-closed counting branch. | (a) Unconditional fold (original plan — rejected: masks open de-scoping); (b) keep exclusion + retain the "· N deferred" tally for open waves (rejected: keeps the tally the operator wants gone, weak de-scoping signal); (c) exclude deferred entirely while open with no tally (rejected: deferred invisible while open, does not address the concern). |
| 2026-06-08 | Keep the `[~]` parse and the per-item `~` marker / `--deferred` styling in the AC/Tasks detail dialogs. | Reviewers still benefit from seeing *which* items were deferred even though they read as done once closed; only the bar accounting changes. | Remove `[~]`/`~` entirely (loses the deferred-vs-done distinction in detail). |
| 2026-06-08 | Implement consistently across `dashboard_lib.py` and `dashboard.js`, applying the same open/closed treatment everywhere (including the status-agnostic `waveStats`/`acProgressStats`). | Avoids the wave card / mini-graphs / ACS-TASKS bars disagreeing on totals, especially for aggregate bars combining closed and open waves. | Frontend-only fold (risks backend-derived surfaces diverging). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Open bar now drops for deferrals, surprising users who expect a fully-met-with-deferrals change to read complete. | Intentional (de-scoping visibility); resolves to 100% at close; documented in the Decision Log and the AC-2 worked example (`8/10` open → `10/10` closed). |
| The open/closed branch is applied asymmetrically across backend + frontend or aggregate (closed+open) bars, causing drift. | AC-4 cross-layer/aggregate test; `waveStats`/`acProgressStats` explicitly reconciled or shown unused. |
| `not-this-scope` (or `[~]`×`not-this-scope`) accidentally folded into completed while reworking the filters. | AC-5 explicit test that both stay excluded in open and closed states. |
| Dead aggregate-deferred plumbing (`ac_deferred_counts` / `tasks_deferred` / snapshot `deferred`) left inert or removed unsafely after the suffix is gone. | The per-item `deferred` flag drives the detail marker; remove the aggregate fields only with a passing test guard, otherwise leave inert and note it. |
| Edit collides with sibling `1p459` in `dashboard.js`/`dashboard.css`. | Serialization point; different functions/selectors — sequence and re-verify. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
