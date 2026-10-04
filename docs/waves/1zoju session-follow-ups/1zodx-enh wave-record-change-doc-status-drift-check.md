# Wave Record And Change Doc Status Drift Check

Change ID: `1zodx-enh wave-record-change-doc-status-drift-check`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-03
Wave: 1zoju session-follow-ups

## Rationale

Red-team finding R8 from wave `1zls7` (recorded in `1zlu0`'s Decision Log as a follow-up): a change's `Change Status` in the wave record can disagree with the `Change Status` in its own change document, and only some paths notice.

What exists today (census predicate: every framework script, tests excluded, that emits the `change_status_drift` code or compares a wave-record member status against a change document's status line):

- `wf_close_change_response` (wave `1zlu1`) refuses with `change_status_drift` when the closing change's two statuses differ; it reads the change document's status from its leading metadata only (`_close_change_doc_status`, CRLF normalised) at the exact path `_wave_change_doc_path` returns.
- `wf_current_wave_response` emits an advisory `change_status_drift` through `_detect_wave_status_drift`, for the active wave only. That helper finds the change document by substring match on file stems (`cid.lower() in p.stem.lower()` over an `rglob`) and reads the FIRST `Change Status` line anywhere in the document, including one inside a fenced example or a Progress Log row.
- docs-lint (`check_wave_docs`) validates each status line's syntax and transitions per file, but never compares the two files.
- `wf_close_wave_response` reads only the wave record's member statuses (`_close_open_work_records`), so a wave closes while a change document still says `planned` or `active`. That is how the archive acquired its drift: measured on 2026-10-03 over every `docs/waves/*/wave.md` with this plan's own predicate (Requirement 1: exact path, header-only status, a missing document is not drift), 5 of 1,039 member records disagree with their change document, all in closed waves (`12wsj` twice, `1p61u`, `1rvjs`, `1t3gt`); 3 further records in `12pn3` have no change document at the exact path, which Requirement 1 does not count as drift. No open wave has any.

The cheapest point to stop new drift is close, where it becomes permanent, plus an early, non-blocking signal while work is in flight. One shared detector keeps the three readers from disagreeing about what "drift" means.

## Requirements

1. One detector in `wave_lint_lib/wave_validators.py`, `member_status_drift(wave_text, wave_dir)`, returns `(change_id, wave_status, doc_status)` for each change record from `_parse_change_records(wave_text, ...)` whose change document exists at `wave_dir / f"{change_id}.md"` (the `_wave_change_doc_path` rule) and whose header status differs. The header status is read as `_close_change_doc_status` reads it: CRLF normalised to LF, the text before the first `## ` heading, the first `CHANGE_STATUS_PATTERN` match, `None` when absent. A missing or unreadable change document is not drift (other lint rules and gates own those); a document whose header has no readable status is drift with `doc_status = None`.
2. docs-lint reports each drift as a WARNING (not a failure) for every wave record whose `Status` is not `closed` or `completed`, naming the change id, both values and both repository-relative paths. Closed and completed waves are never reported, so the 5 historical records stay untouched. On the incremental path (`check_wave_docs(only=...)`), which skips `wave.md` unless it is in `only`, the same warning is also emitted when an in-scope CHANGE document is processed: the check reads the `wave.md` beside it, finds that change's member record, and compares that one record. That is one extra file read per in-scope change document. A drift reported through both paths in one run is reported once.
3. `wf_close_wave` (dry run and create) refuses with a blocking `change_status_drift` diagnostic listing every drifted change, with `recovery_tools=["wf_get_change", "wf_current_wave"]`, before close's own writes (summary, status, handoff). Only when the wave's `Status` is not already `closed` or `completed` does the gate apply, matching Requirement 2. So the convergent re-close of an already-closed wave (the `_already_closed` branch, wave `1seax`, which returns `ok` with `transitioned_to_closed: false` and re-converges the handoff) is unaffected, including for the archived waves that carry drift. Create-mode close runs `run_garden` first, and that may stamp `Last verified` before the gate fires. The gate does not change that existing ordering; it guarantees only that close's own writes do not happen.
4. `_detect_wave_status_drift` (`wf_current_wave`) is reimplemented on the detector, keeping its advisory code, its active-wave-only scope and its envelope shape; the substring lookup and whole-document read go away.
5. `wf_close_change` keeps its own single-change gate unchanged (it already reads the same header the same way).
6. Platform behaviour: the detector reads bytes decoded as UTF-8 and normalises CRLF before matching, so a CRLF-saved change document (common on Windows checkouts with `core.autocrlf=true`) reads the same as an LF one; file lookup is by exact name under the wave folder. Identical on Windows, macOS, Linux and WSL2.

## Scope

**Problem statement:** wave-record and change-document statuses drift silently, and close archives the drift.

**In scope:**

- The detector and the lint warning in `wave_lint_lib/wave_validators.py`.
- The close gate in `wf_close_wave_response` and the `_detect_wave_status_drift` rewrite in `wf_server/server_impl.py`.
- Tests in `tests/test_docs_lint.py`, `tests/test_server_tools_lifecycle.py` (the existing `WaveStatusDriftDetectionTests` keep passing), and the close-gate golden fixture if close's diagnostic set is pinned there.
- `docs/specs/mcp-tool-surface.md` (close gate) and a CHANGELOG bullet.

**Out of scope:**

- Rewriting the 8 drifted records in closed waves (closed history is not rewritten).
- Auto-syncing one file from the other: which side is right is a judgment call.
- A separate Prepare or Review check: Prepare and Review already run docs-lint, so the warning reaches both.

## Acceptance Criteria

- [x] AC-1: Detector unit tests: equal statuses yield nothing; differing statuses yield one tuple; a CRLF change document with an equal status yields nothing; a fenced or Progress Log `Change Status` line after the header is ignored; a missing change document yields nothing; a header with no status line yields `doc_status = None`.
- [x] AC-2: docs-lint on a fixture with an active wave whose wave record says `active` and whose change document says `planned` reports one warning naming both values and paths, and no failure; the same fixture with the wave `closed` reports nothing.
- [x] AC-3: Running docs-lint on this repository produces no new warning from this rule (measured: zero drift in non-closed waves on 2026-10-03).
- [x] AC-4: Reproducer, failing first: `wf_close_wave` dry run on a wave whose member says `complete` and whose change document says `active` returns `change_status_drift` and blocks; on `create`, with `run_garden` stubbed as `test_lifecycle_golden` stubs it, the wave record's `Status` line and every change document's status lines are unchanged after the call, and no summary or handoff is written. Before the change the same wave closes.
- [x] AC-5: `wf_current_wave` still reports `change_status_drift` as an advisory for the active wave, and now finds a change whose id is a prefix of another change's stem only at its exact path (a test with ids `1abcd-bug x` and `1abcd-bug x-two`).
- [x] AC-6: The change's own test files and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-7: Create-mode `wf_close_wave` on a fixture wave that is already `closed` and whose member status and change-document status disagree, with `run_garden` stubbed, returns `ok` with `data.transitioned_to_closed is False` and no `change_status_drift` diagnostic, and the handoff converges (it is written as the `_already_closed` branch writes it). The test fails if the gate is applied regardless of wave status (checked by temporarily removing the status scope).
- [x] AC-8: Incremental lint (`check_wave_docs(only={change_doc})`) on the AC-2 fixture, scoped to the drifted change document only, reports the same warning once.

## Tasks

- [x] Write the AC-4 close reproducer and confirm it closes on the current tree.
- [x] Add `member_status_drift` and its unit tests (AC-1).
- [x] Add the lint warning, including the in-scope change-document path for incremental lint (AC-2, AC-3, AC-8).
- [x] Add the close gate, skipped for already-closed waves (AC-4, AC-7).
- [x] Reimplement `_detect_wave_status_drift` on the detector (AC-5).
- [x] Update the spec and CHANGELOG; run the full suite in a scratch copy and docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| detector | implementer | none | AC-1 |
| lint-warning | implementer | detector | AC-2, AC-3 |
| close-gate | implementer | detector | AC-4, failing first |
| current-wave | implementer | detector | AC-5 |

## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`, `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `docs/specs/mcp-tool-surface.md`
- The CHANGELOG at the repository root is edited too.

## Affected Architecture Docs

N/A: one detector shared by an existing lint pass, an existing close gate and an existing advisory; no component boundary or flow changes.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The shared definition of drift |
| AC-2 | required | The in-flight signal |
| AC-3 | important | Shows the warning is quiet on the current corpus |
| AC-4 | required | The permanent-drift fix, failing first |
| AC-5 | important | Removes the second, looser reading |
| AC-6 | required | Suite and lint gate |
| AC-7 | required | The 1seax convergent re-close must survive the new gate |
| AC-8 | important | The in-flight signal reaches the incremental post-edit lint |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-03 | Delivery repair (optional item): `wf_current_wave`'s drift advisory now names each change with its wave-record status and its change-document status in neutral words and ends "Reconcile the wave record and the change document."; a missing header status reads "no header status", never `None` | Tests: `WaveStatusDriftDetectionTests.test_missing_header_status_is_named_not_none` (new) and the updated needle in `test_prefix_id_is_found_only_at_its_exact_path`; both failed first on the pre-repair tree. Mutation R8 (print `None`) killed. Full suite `--no-cache` in a fresh scratch copy, plus `--profile second` and `--profile declared`: 10,930 tests across 157 files OK (34 skipped); second 10,927 OK; declared 10,930 OK. The first repaired run failed only `test_label_reader_census` (its allowlist entry for the old `wf_current_wave` message became stale and was removed) |
| 2026-10-03 | Implemented: `member_status_drift` and `change_doc_header_status` in `wave_validators` (exact path, header-only, CRLF read as LF), a docs-lint WARNING for waves not closed or completed (also from an in-scope change document on incremental lint, reported once per run), the blocking `change_status_drift` close gate before close's writes and skipped for closed or completed waves, and `_detect_wave_status_drift` rebuilt on the detector; spec and CHANGELOG updated. Golden `lifecycle-gate-golden.json` regenerated: each of the 6 close captures gains one `change_status_drift` (the fixtures' change documents carry no header status); the extraction-golden comparison declares that addition. Close-success fixtures in `test_server_tools_lifecycle` and `test_phase_gates` now give their change documents a matching header status | Tests: `test_docs_lint.MemberStatusDriftDetectorTests` (AC-1), `MemberStatusDriftLintTests` (AC-2, AC-8), `test_server_tools_lifecycle.CloseWaveStatusDriftTests` (AC-4, AC-7), `WaveStatusDriftDetectionTests.test_prefix_id_is_found_only_at_its_exact_path` (AC-5). AC-3: docs-lint on this repository prints no warning. Failing-first on HEAD: the AC-4 wave closed (`dry_run` and `ok`), AC-1, AC-2, AC-5 and AC-8 failed; AC-7 passed as a preservation check. Mutations M8 to M16 all killed (M8 after strengthening the header-only test with a header that has no status). full suite `run_tests.py --no-cache` in a scratch copy: 10,925 tests, 157 files, OK; `--profile second` and `--profile declared` OK (second 10,922 tests, declared 10,925; the final run, after every code change; 34 tests skipped in the full run). Gapfill: retrieval used grep and sed over the scripts tree instead of the MCP code tools, because the edits needed exact multi-line anchors in a 25,000-line module and the attached MCP server runs the pre-change code |
| 2026-10-03 | Readiness amendments F3 to F5: close gate skips already-closed waves; the gate is placed before close's own writes, and AC-4 stubs `run_garden`; drift figure corrected to 5; incremental lint warns via the in-scope change document | Re-derived with the exact-path, header-only predicate: 5 drifted, 3 missing (`12pn3`) |
| 2026-10-03 | Planned from `1zls7` red-team R8 | Corpus probe: 8 of 1,039 member records drift, all in closed waves (an id-prefix lookup; superseded by the row above) |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-03 | Recheck N2: AC-7 and Requirement 3 now describe the real re-close contract (`ok`, `transitioned_to_closed: false`, handoff converges) and cite no test | The cited `test_close_already_closed_gate_returns_advisory` exercises the edit-gate tool (`wf_close_wave_gate_response`, `gate_already_closed`), not wave close, and wave close returns no advisory on re-close | Keep the citation (rejected: wrong tool) |
| 2026-10-03 | Readiness amendment F3: the close gate applies only to waves not already `closed` or `completed` | The convergent re-close of a closed wave (`1seax`) must keep working, and archived drift is history that Requirement 2 already exempts | Gate every close (rejected: would block re-closing the 5 archived waves with drift) |
| 2026-10-03 | Readiness amendment F5: on incremental lint, emit the warning from the in-scope change document | The post-edit hook scopes lint to the edited file, which is usually the change document, so a `wave.md`-only check would stay silent mid-flight; the extra cost is one read of the sibling `wave.md` | Rely on full lint, Prepare, Review and close as the boundary (rejected: the signal would arrive late) |
| 2026-10-03 | Lint WARNING, close BLOCKS | Statuses legitimately disagree between the two edits of a status change, and the post-edit hook runs lint after each file; a failure there would fire on correct work. Close is where drift becomes permanent | Lint failure (rejected: noisy mid-edit); close advisory only (rejected: that is today's leak) |
| 2026-10-03 | One detector in `wave_lint_lib`, header-only status read | Lint cannot import the server; the server already imports lint. The header read matches `wf_close_change`, so all readers agree | Keep `_detect_wave_status_drift` as is (rejected: its substring lookup and whole-document read disagree with close_change) |
| 2026-10-03 | No separate Prepare or Review gate | Both already run docs-lint, so the warning appears there with no new code | A Prepare gate (rejected: blocks readiness on a recordkeeping lag that close will catch) |
| 2026-10-03 | Do not auto-sync | Which side is correct needs a human or agent judgment | Copy the wave-record status into the document at close (rejected: could archive a wrong status silently) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The close gate blocks a wave an operator wants closed | The diagnostic names each change and both values; fixing is a one-line edit. No current open wave would be blocked (AC-3 measurement) |
| Closed-wave history trips the warning | Closed and completed waves are skipped (AC-2) |
| CRLF documents misread on Windows | CRLF normalised before matching (AC-1) |
| Platform behaviour | Pure text comparison with exact-path lookup; identical on Windows, macOS, Linux and WSL2 (Requirement 6) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
