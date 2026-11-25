# QA review: wave 24buu readiness

Owner: Engineering
Status: active
Last verified: 2026-11-24

- Lane: qa-reviewer, readiness, fresh context, independent (implemented nothing).
- Read: `docs/agents/qa-reviewer.md`, seed 209 readiness finding bar, `wave.md`, specs 24but, 24ax3, 24bn7, 24bn8, 24bn9, the red-team primer and the upgrade rehearsal.
- Retrieval: MCP `code_definition` and `code_read` first. Gapfill: long line ranges in 7000-line files, the 1.51.0 bytes (`git show 03672b89:...`) and the release-zip listing went through shell `sed`, `grep` and `python3 -I`, because those reads are cheaper there; every claim below was read in the tree.
- Executed (read-only, `python3 -B`, `PYTHONPYCACHEPREFIX` in the session scratchpad): the plan-template comparison (F4 replay), `index_state_store.file_commit_times` on an absent and a corrupt store, a stdlib-name collision check over the framework scripts, and a member listing of `~/.wavefoundry/dist/wavefoundry-1.51.0.q5hc.zip`. No repository file was edited.

## Verdict

**Not approved.** Four demonstrated AC defects (QA-1 to QA-4) and three untested intent parts (QA-5 to QA-7). Each is cheap to repair in the spec text.

## Findings

### QA-1. `churn_available` cannot detect the real failure modes; AC-7 passes with the defect present (24but)

- Anchors: 24but Requirement 1 and AC-7; `index_state_store.file_commit_times` (line 1395); `index_state_store.open_read_only` (line 993); `wf_server/memory_handlers._memory_ranked` (lines 312 to 318).
- Requirement 1 sets `churn_available` false "when the commit-time read that `_memory_ranked` uses fails". That read never signals failure: `file_commit_times` returns `{}` when the store is absent, unreadable or on the wrong schema (`open_read_only` returns `None`) and on any SQL error (`except _SQL_ERRORS: return {}`). The `except Exception` in `_memory_ranked` sees only other errors.
- Executed: `file_commit_times(<absent dir>, ['a.py'])` returned `{}`; with a garbage `state.sqlite` it returned `{}`; neither raised.
- Consequence: the natural implementation (flag set in the `except` branch) reports `churn_available: true, target_churn: 0` for a target with no index or a corrupt or schema-mismatched store, which is exactly the "reads as clean" case F9 named. AC-7 says "with the commit-time read made to fail"; it passes only when the test monkeypatches the function to raise, so it passes while the motivating case still fails.
- Repair: define availability as the store opening (for example `open_read_only(index_dir) is not None`, or a `file_commit_times` variant that returns availability), and make AC-7 use two fixtures, an absent store and a corrupt store, with today's `{}` path as the known bad. A store that opens and has no rows for the targets stays `churn_available: true`.

### QA-2. AC-1's expected object omits `churn_available`, so it cannot pass as written (24but)

- Anchors: 24but AC-1 ("returns `revalidation` equal to `{"active_records": 4, ...}`" with four keys) and Requirement 1 (five fields, including `churn_available`).
- A dict equality against four keys fails on any object that satisfies Requirement 1. Repair: add `"churn_available": true` to the AC-1 expected object.

### QA-3. 24bn7 AC-1's fixture and run boundary are unspecified; two natural choices pass with the fix absent, and the passing run starts a full upgrade (24bn7)

- Anchors: 24bn7 Requirement 2 and AC-1; `upgrade_bundle.run` (line 294), `upgrade_bundle._incoming_runner` (lines 237 to 286).
- `retain` (the failing import) runs on only some branches:
  1. Protocol 2 (the rehearsal target, which went through `_incoming_runner`, per the rehearsal traceback): `retain` runs before `_materializer`. Reproduces the bug.
  2. Protocol 1 (no `UPGRADE-PROTOCOL.json`, the audience the Rationale names): `retain` runs only when `envelope.inspect` finds an embedded model declaration. The lean release zip has none (the 1.51.0 zip has no descriptor member). A protocol-1 fixture with a lean zip never imports `contained_files`, so AC-1 passes with the fix absent.
  3. `--dry-run`: `_incoming_runner` skips `retain` entirely. Also passes with the fix absent.
- After `_materializer`, `run` executes `next_argv`: the incoming `upgrade_wavefoundry.py --root <fixture> --pack ... --yes` without `--dry-run`. "Reaches the bridge's next step" therefore starts a real upgrade of the fixture with the inherited environment (home, dependency provisioning and index phases). Requirement 2 does not say how the test bounds it.
- Repair: name the fixture as protocol 2 (the rehearsal shape) and, separately, the combined `.with-models` zip on protocol 1; require the test to show the unfixed zip fails with `No module named 'contained_files'` on the same fixture; and bound the child (for example a fixture whose incoming runner exits at once, or assert on the spawned argv with the spawn replaced, plus `HOME` and `WAVEFOUNDRY_*` home paths redirected to the temp root).

### QA-4. Outside-layer reads have no seam that crosses the render child, so AC-1 and AC-6 read real user and system state and depend on the host (24ax3)

- Anchors: 24ax3 Requirement 5 (enterprise file "at its documented path for the platform", no override), AC-1 ("running the Phase 1 permissions render child"), AC-4 ("No test reads the real home or system paths"), AC-6 (end-to-end); `upgrade_wavefoundry.phase_surface_rendering` spawns `render_platform_surfaces.py` as a subprocess; existing tests (`tests/test_spec_tool_permissions.py`, `tests/test_upgrade_wavefoundry.py`) isolate only in process with `patch.object`, and `run_tests.py` sets no `HOME`.
- An in-process patch of the enterprise path or `Path.home()` does not reach the child. AC-1 and AC-6 then read the developer's real `~/.claude/settings.json`, `~/.codex/config.toml` and the real managed-settings file. On a workstation with a personal deny or ask on an old name, or an enterprise-managed laptop, AC-1 and AC-6 fail; elsewhere they pass. Requirement 4 also moves the outside layers into `assess`, which every existing `spec_permission_holds` test reaches.
- Repair: Requirement 5 names an override for each outside location that a child inherits (environment variables for the enterprise path, plus `HOME`, `USERPROFILE`, `CLAUDE_CONFIG_DIR` and `CODEX_HOME`), and the test plan sets them to temp paths for every test that reaches `assess`, the child or the end-to-end harness, not only AC-4.

### QA-5. Untested intent: no write outside the checkout through a symlink (24ax3)

- Anchors: 24ax3 Boundaries ("upgrade writes only host settings inside the checkout"), Requirement 8 (a symlinked or outside-resolving file is not written).
- No AC covers a `.claude/settings.local.json` or `.codex/config.toml` symlink that points outside the checkout. AC-3 covers only a malformed file. Classification: `required_ac` (the Boundary is the intent). Repair: add an AC with a symlinked settings file whose target is byte-identical afterwards and whose routes stay held.

### QA-6. Untested intent: two of the four continuation boundaries, and a fake child could satisfy AC-1 (24bn9)

- Anchors: 24bn9 Boundaries and Requirement 3 (storage-migration pause, restart-required receipt, failed index publication, retained upgrade checkpoint); AC-3 tests only the failed index publication and the storage-migration continuation.
- The restart-required receipt and the retained upgrade checkpoint have no test, and auto-cleanup there removes the lock that recovery owns. Classification: `required_ac`. Repair: extend AC-3 to all four states.
- Also: AC-1's "lock removed" must come from the real `--cleanup` child (or the real `phase_cleanup`), not a patched child runner that deletes the lock; otherwise AC-1 is vacuous. State this in the AC.

### QA-7. Untested intent: an unknown-baseline copy is never overwritten (24bn8)

- Anchors: 24bn8 Boundaries ("never overwrites a locally edited copy, an unknown-baseline copy, or a copy that changed after the comparison"); AC-2 and AC-4 cover the first and third.
- Classification: `important_ac` (the write path is gated on `upstream_changed_local_matches_previous`, so the risk is low). Repair: add a `baseline_unknown` case (previous template missing) to AC-2 or AC-4.

## Primer engagement

- **Strongest challenge (F1).** Resolved in design: an outside deny or ask now holds the route (Requirement 5), and the receipt has a distinct upgrade body (Requirement 7). The tests for that safeguard are not yet isolated (QA-4).
- **Q1, receipt authority.** Resolved by the distinct body and the outside-layer hold.
- **Q2, separated holds.** Resolved by Requirement 4, Requirement 2.3 and AC-5.
- **Q3, which process runs each change.** Resolved for 24ax3 and 24bn8. Verified: the 1.51.0 `phase_surface_rendering` (`git show 03672b89`, lines 2242 to 2270) launches `SCRIPTS_DIR/render_platform_surfaces.py --include-permissions`, and that file is the freshly extracted one. 24bn9 states its hop, and the watchpoint rehearses both hops.
- **Q4, CLI versus MCP.** Resolved by `--no-auto-cleanup` (AC-2). The sentinel half ("one terminal result", Requirement 4) has no AC; see the notes.
- **Q5, plan-template cause.** Resolved. Executed: the 1.51.0 template with only the date substituted still differs from its incoming-code materialization at exactly `Change ID:` and `Change Status:`. AC-3 uses the 1.51.0 bytes, and the upstream template differs in other lines too, so label normalization cannot collapse AC-3 into `already_current`.
- **Q6, upgrade policy block.** Resolved. AC-4 asserts on the block rendered by the replay; `tests/test_review_policy.py` line 682 holds the pin to update.
- **Q7, writes after the docs gate.** Resolved by moving both writers into the Phase 1 child and re-rendering owned regions (24bn8 Requirement 3).
- **Efficacy replays.** 24ax3, 24bn7 (F3, F11), 24bn8 (F4, F6, F12) and 24bn9 (F5, F8) are resolved in design. 24but F7 is resolved; F9 is only partly resolved (QA-1).

## AC-by-AC

| Spec | AC | Can pass | Fails without fix | Oracle | Note |
| --- | --- | --- | --- | --- | --- |
| 24but | AC-1 | No as written (QA-2) | Yes | Hand-computed counts | Use the `_seed` churn harness class near `tests/test_memory_records.py` line 6711 |
| 24but | AC-2 | Yes | Weak | Same producer (`_memory_ranked`) on both sides | A consistency guard; AC-1 is the independent oracle |
| 24but | AC-3, AC-4 | Yes | Yes | Text pins; AC-4 on `reconcile_upgrade_policy_surface` output | Fine |
| 24but | AC-5 | Yes | n/a (measurement) | Live counts | Read-only on records |
| 24but | AC-7 | Yes, vacuously (QA-1) | No for real failures | Monkeypatch only | Repair per QA-1 |
| 24ax3 | AC-1 to AC-7 | Yes | Yes (today holds all five) | `assess`, file bytes, receipts | Host-dependent until QA-4 |
| 24bn7 | AC-1 | Yes | Depends on fixture (QA-3) | Subprocess result | AC-3 is feasible through `build_upgrade_bundle(bundle_source=...)` from a temp copy |
| 24bn7 | AC-2 | Yes | n/a | Existing member pins | Fine |
| 24bn8 | AC-1 to AC-5 | Yes | Yes | Fresh-install render equality, the 1.51.0 bytes | AC-5 holds: same pack means `incoming_matches` and no finding |
| 24bn9 | AC-1 to AC-5 | Yes | Yes | Lock state, argv, exit code | See QA-6 |

Priority tables: justified as written. Each required AC carries a Product Intent part or a safety boundary.

Existing test files named in Tasks all exist: `test_memory_records.py`, `test_review_policy.py`, `test_spec_tool_permissions.py`, `test_upgrade_wavefoundry.py`, `test_upgrade_protocol.py`, `test_lifecycle_baseline_drift.py` and `fixtures/register-surface-handler-digests.json`. The upgrade handler tests are spread over `test_server_tools.py`, `test_upgrade_reload_runner.py` and others; 24bn9 Tasks should name one.

## Implementation notes (non-blocking)

1. 24bn8 and 24ax3: vendor the 1.51.0 bytes as test fixtures. Do not call `git show` at test time, because the packaged framework has no git history.
2. 24bn8: build the lock's findings through the canonical producer (`lifecycle_baseline_report` with the incoming renderer), not by hand-writing a finding with a digest.
3. 24bn9: Requirement 4's "one terminal result" with two printed summaries has no AC. Add one, or assert the last sentinel in AC-1.
4. 24bn9 (architecture): a 1.51.0 MCP server still running against a 1.52.0 install would call the 1.52.0 primary without `--no-auto-cleanup`. The required host restart makes this unlikely; worth a sentence in the Risks table.
5. 24ax3: on Windows `Path.home()` reads `USERPROFILE`, not `HOME`; the test isolation must set both.
6. 24ax3: Requirement 5's outside `allow` recommendation and the malformed outside-file notice have no AC. Optional.
7. 24bn7: append the zip's scripts path to `sys.path`; do not prepend it. Executed check: no framework script name collides with `sys.stdlib_module_names` today.
8. 24but AC-1: name the fixture's commit history for B through the existing `_seed` / `apply_freshness` producer so churn comes from the store, not from `commit_times_override`.

## Focused verification

- Context `24buu-readiness-qa-reviewer-2`: fresh and independent. I did not write or touch the repair.
- Inputs: `.wavefoundry/work/24buu/readiness/repair-1.md`, the cycle 1 rows in each Progress Log, and the current Requirements and ACs of all five specs.
- Probe: `python3 -B <scratchpad>/qa2/check.py`. It parses the current spec text and reruns the QA-1 store reproduction. A second probe, `qa2/knownbad.py`, runs the same assertions on the pre-repair text.

| Finding | Repair | Result | Known bad |
| --- | --- | --- | --- |
| QA-1 | 24but Requirement 1 adds an availability signal. AC-7 uses absent, corrupt and wrong-schema stores with no monkeypatching. | Resolved | Rerun: `file_commit_times` returned `{}` without raising on all three stores, so AC-7 fails on today's code. |
| QA-2 | AC-1 expects `churn_available: true` | Resolved | The key-set check fails on the old four-key object. |
| QA-3 | 24bn7 uses a protocol-2 fixture, a non-dry run, a stubbed next step and both zips | Resolved | The check fails on the old Requirement 2. |
| QA-4 | 24ax3 resolves paths through one function that honors five environment variables. AC-4 and AC-10 apply that isolation. | Resolved | The check fails on the old AC-4. |
| QA-5 | 24ax3 AC-9 covers a symlinked file and a file that resolves outside the checkout | Resolved | There was no AC-9 before the repair. |
| QA-6 | 24bn9 AC-7 covers the restart-required receipt and the retained checkpoint. AC-8 requires the real child and one terminal result. | Resolved | The check fails on the old AC-3. |
| QA-7 | 24bn8 AC-7 covers `baseline_unknown` and unchanged-upstream copies | Resolved | There was no AC-7 before the repair. |

Delta check, focused. No new demonstrated defect.

- 24ax3:
  - AC-4 cases 1 to 6 each name a known bad. They match Requirement 5.1 to 5.3.
  - AC-10 drives the verbatim 1.51.0 argv. `setup_wavefoundry._run_render_platform_surfaces` exists at line 93 and passes `--include-permissions`.
  - AC-11 and AC-12 can be tested. Each fails on today's code: readiness has no spec-tool reason today, and the Codex table copy does not exist.
- 24bn7 AC-1 to AC-3 can be tested and have real known bads.
- 24bn8 AC-7 and AC-8 can be tested. AC-8 fails if replacement ignores the lock.
- 24bn9 AC-7 to AC-10 can be tested.

Implementation notes (non-blocking):

1. 24ax3: apply the AC-4 environment isolation suite-wide. AC-1 and AC-6 do not restate it, and the existing `spec_permission_holds` tests reach `assess`, which now reads the outside layers.
2. 24bn7: the stub next step under `python3 -I` cannot be patched in. Build the test's feature zip with a stub `upgrade_wavefoundry.py` whose bytes match the selection hashes.
3. 24bn9 AC-9: "to completion" should not run a real index build in a test. Bound the run as 24bn7 does, or patch the index phase in process, and assert the recovery report text.
