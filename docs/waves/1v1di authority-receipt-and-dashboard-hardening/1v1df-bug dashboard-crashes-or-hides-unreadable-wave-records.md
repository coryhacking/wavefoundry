# The Dashboard Crashes On Or Hides Unreadable Wave Records

Change ID: `1v1df-bug dashboard-crashes-or-hides-unreadable-wave-records`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-11
Wave: 1v1di authority-receipt-and-dashboard-hardening

## Rationale

`collect_waves` in `dashboard_lib.py` re-reads every wave record raw: `Path(wave["path"]).read_text()` guarded by `except OSError: continue`. Executed during wave `1uzwh`'s delivery review (recorded in the `wave-council-delivery` ledger synthesis carry-forward list, "dashboard collect_waves raw reads", and re-executed by this wave's readiness council): a decode-broken `wave.md` raises `UnicodeDecodeError` out of the dashboard snapshot (the crash class `1v0lw` closed for every MCP tool), and a permission-broken one silently vanishes from the dashboard. The dashboard is a diagnostic surface: it misbehaves on exactly the input an operator would open it to investigate.

`1uzwh` also concretized a second defect here: the enumeration contract now emits **repo-relative** `path` values for degraded entries (leak-safe for envelopes), while readable entries keep absolute paths. `collect_waves` treats `path` as a filesystem path, so a degraded entry resolves against the process CWD: at the repo root it reopens the broken file (crash on decode), anywhere else it raises `FileNotFoundError` and the wave silently vanishes.

Readiness-council correction (2026-08-11): the changes collector's `Path(wave["path"])` join inherits the CWD-dependent PATTERN but not an observable defect today, because a degraded enumeration entry carries `changes: []` and the join body never executes for it (executed probe). The reachable crash in that collector is one function away: `parse_change_doc` wraps only `OSError`, so a decode-broken CHANGE DOC crashes the snapshot by the identical mechanism. Both are in scope; the change-doc site is the one with a red-first reproduction.

## Requirements

1. **An unreadable wave record renders as a visible degraded row.** The dashboard lists the wave with its id, status, and a `read_error` (path-free, the enumeration contract's own field), for both causes, instead of crashing or omitting it. The degrade mirrors `wf_list_waves`' per-entry contract: the broken wave is the one entry an operator most needs to see.
2. **Path handling is root-anchored, never CWD-dependent.** `wave["path"]` joins against the collector's `root` when relative; absolute paths pass through. The census enumerates every `Path(wave["path"])` consumer in `dashboard_lib.py` (the waves collector, the changes collector, and any others) and each gets the same treatment.
3. **Every raw filesystem touch on the render path fails closed per entry**, not only `read_text` sites: the census covers the wave-record read, the change-doc read in `parse_change_doc` (which wraps only `OSError` today, so a decode-broken change doc crashes the snapshot), and the non-read touches on the degraded path (`relative_to(root)` raises `ValueError` on an already-relative path; `stat()` raises on a file deleted between enumeration and render). A failure produces the degraded row, not a `continue` and not a raise. Where the enumeration entry already carries `read_error` from the seam, the dashboard trusts it instead of re-deriving.
4. **No change for readable waves.** The rendered snapshot for a healthy corpus is unchanged, verified by an executed before/after comparison over the real corpus.

## Scope

**Problem statement:** the operator-facing diagnostic surface crashes on decode-broken wave records, hides permission-broken ones, and resolves degraded entries' repo-relative paths against the process CWD.

**In scope:** the wave-record read and path handling in `collect_waves` and the sibling changes collector in `dashboard_lib.py`; degraded-row rendering; red-first tests in `test_dashboard_server.py` (which today has no unreadable-wave coverage, per the `1uzwh` seat report).

**Out of scope:** the enumeration contract itself (`1v0lw`, shipped); dashboard rendering fidelity beyond the degraded row (parked plan `1p30y` owns broader rendering work); the MCP tool surfaces.

## Acceptance Criteria

- [x] AC-1: A decode-broken wave record no longer crashes the snapshot, reproduced **red-first**: today `collect_waves` raises `UnicodeDecodeError` at repo-root CWD. Post-fix the snapshot contains the degraded row.
- [x] AC-2: A permission-broken wave record appears as a degraded row, reproduced **red-first**: today it is silently omitted.
- [x] AC-3: The snapshot is CWD-independent: the same corpus yields the same snapshot from the repo root and from a foreign working directory. The red-first vehicle is the DECODE fixture (a permission-only corpus is byte-identical from both CWDs today, so it cannot go red; the readiness council executed both).
- [x] AC-7: A decode-broken admitted change doc no longer crashes the snapshot, reproduced **red-first** at `parse_change_doc`'s `OSError`-only wrap; the change renders with a degraded indication.
- [x] AC-4: The degraded row carries no absolute filesystem path, asserted with a reach guard.
- [x] AC-5: A healthy corpus renders an unchanged snapshot (executed before/after comparison over the real corpus), and the existing dashboard suite passes.
- [x] AC-6: The full framework suite and docs-lint pass.

## Tasks

- [x] Red-first tests: wave-record decode crash, permission vanish, CWD dependence (decode vehicle), the change-doc decode crash at `parse_change_doc` (AC-7), leak guard.
- [x] Root-anchored path handling at every `wave["path"]` consumer (census recorded); fail-closed touches per Requirement 3.
- [x] Degraded-row rendering; healthy-corpus comparison; full suite; docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-tests | implementer | — | Both causes plus the CWD matrix |
| collectors | implementer | red-tests | Waves and changes collectors, same treatment |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Affected Architecture Docs

`N/A` with rationale: the dashboard remains a read-only consumer of the enumeration contract; this change makes it honor that contract's degrade semantics without moving any boundary. `docs/references/dashboard-adapter-model.md` gains a sentence only if the degraded row needs adapter-level documentation, disclosed here if so.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The crash class, on the diagnostic surface. |
| AC-2 | required | A hidden broken wave is the misdirection twin of the crash. |
| AC-3 | required | The CWD dependence is new exposure concretized by the seam's repo-relative paths. |
| AC-4 | required | The leak class must not recur on a new rendering path. |
| AC-5 | required | Invisible for normal input. |
| AC-6 | required | Standard gate. |
| AC-7 | required | The same crash class one function away; shipping without it over-claims the fix. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-11 | Planned from wave `1uzwh`'s carried-forward findings (delivery-council synthesis carry-forward list, executed both CWD variants by that seat). Premises executed before authoring: `collect_waves` reads raw with `except OSError: continue` (source read); the decode crash and permission vanish observed by the seat; degraded enumeration entries now carry repo-relative paths while readable entries stay absolute | 1uzwh ledger synthesis plus source reads, 2026-08-11 |
| 2026-08-11 | Readiness council (red-team and docs-contract seats): the sibling-collector claim was FALSIFIED by execution (a degraded entry carries `changes: []`, so the changes collector's join never runs on a real read; it inherits the pattern, not the defect), and the council found the actually reachable crash one function away: `parse_change_doc` wraps only `OSError`, so a decode-broken change doc crashes the snapshot by the identical mechanism. Rationale corrected; Requirement 3 widened to every raw filesystem touch on the render path (including `relative_to` and `stat` on the degraded path); AC-7 added for the change-doc crash; AC-3's red vehicle pinned to the decode fixture (a permission-only corpus is CWD-identical today, both variants executed) | seat reports, executed probes P5-P9, 2026-08-11 |
| 2026-08-11 | Red-first executed against the unmodified tree (implementer, in-session): AC-1 decode-broken `wave.md` raised `UnicodeDecodeError` out of `collect_waves` (reached through `collect_dashboard_snapshot`) at repo-root CWD; AC-2 permission-broken `wave.md` silently vanished (`[] is not true`); AC-3 red carried by the decode vehicle (repo-root run crashed while the foreign-CWD run dropped the wave); AC-7 decode-broken change doc raised `UnicodeDecodeError` out of `collect_changes` at `parse_change_doc`, and the permission-cause pin failed with `read_error` absent (the silent misparse: file stem as change_id, status unknown, no marker); the vanished-in-window and seam-trust reds failed with the wave dropped (`[] != ['12v ghost-wave']`, `0 != 1`); AC-4 leak guards were unreachable pre-fix (crash before the row exists). Eight red tests red for the predicted mechanisms; one AC-5 support pin (`read_error` key absent on healthy output) green by design | red run of `tests.test_dashboard_server.UnreadableWaveRecordTests`, 2026-08-11 |
| 2026-08-11 | Fix landed in `dashboard_lib.py` only. Census: `collect_changes` and `collect_waves` are the only two `Path(wave["path"])` consumers in the file; both now root-anchor via `_root_anchored` (absolute passes through, relative joins the collector's root, never the CWD). `plan["path"]` was already root-anchored (`root / plan["path"]`), and downstream `path` consumers anchor too (`dashboard_server.py` `/api/doc` does `root / doc_path`; `dashboard.js` passes `change.path` opaquely). `collect_waves` trusts a seam-carried `read_error` without re-reading, catches `(OSError, UnicodeError)` locally with the strerror-or-type-name idiom (`server._read_error_detail`), and renders a degraded row that reuses `review_evidence_status` (`integrity: "invalid"`, `diagnostics: [read_error]`) so the cause reaches the existing frontend tooltip with no `dashboard.js` change; substituted-empty text is never routed through `_review_evidence_dashboard_state` (which would mislabel the row `legacy`). `relative_to` and `stat()` fail closed per entry (`_repo_rel_or_name`, `_stat_mtime_iso`). `parse_change_doc` returns an `_unreadable_change_record` with `read_error` bound for both causes; `_change_payload` strips the `read_error` key from healthy records so healthy corpora render unchanged | source diff in `.wavefoundry/framework/scripts/dashboard_lib.py`; all nine tests green, 2026-08-11 |
| 2026-08-11 | Verification: `tests.test_dashboard_server` 198 tests OK twice (one pre-existing env-gated browser skip). AC-5 executed as a paired same-corpus comparison: byte-copied pre-edit `dashboard_lib.py` vs the working tree, both run over the real repo corpus (215 waves, 808 wave changes, 8 staged plans), canonical sorted-key JSON byte-identical at 7,495,338 bytes, with a two-baseline-runs stability control. A naive before/after taken minutes apart differed only by sibling-implementer Progress Log rows and the wave.md mtime (corpus drift, not this change) | `capture_snapshot.py` plus `snapshot_paired_before/after.json` in session scratch, 2026-08-11 |
| 2026-08-11 | AC gate evidence (coordinator, shared across the wave's three docs): full framework suite via `run_tests.py` reports 7129 tests across 62 files, OK, rc=0 captured unpiped; `wf_validate_docs` passed with zero warnings after the readiness seat-evidence rows were recorded. Independently re-executed by the delivery docs-contract seat: same 7129/62 OK rc=0 and "docs-lint: ok" | run_tests.py 2026-08-11 rc=0; wf_validate_docs 2026-08-11; docs-contract seat rerun 2026-08-11 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-11 | Degrade per entry in the dashboard, mirroring `wf_list_waves` | The dashboard is the recovery surface; the broken wave is the entry the operator came to see, and the enumeration contract already defines the degrade vocabulary | Skip unreadable waves with a banner count (rejected: hides which wave is broken); reuse the seam by importing server_impl into dashboard_lib (kept open for implementation: the entry may already carry `read_error`, making a local guarded read unnecessary) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The dashboard template renders the degraded row poorly or not at all | AC-1/AC-2 assert on the rendered snapshot payload, not on collector internals |
| Root-anchoring breaks a consumer that relied on CWD resolution | The census (Requirement 2) enumerates every `wave["path"]` consumer; AC-5 pins the healthy-corpus snapshot |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
