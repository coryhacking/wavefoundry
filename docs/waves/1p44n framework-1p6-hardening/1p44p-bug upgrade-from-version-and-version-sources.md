# Fix from_version Resolution and Consolidate Version Sources in Upgrade

Change ID: `1p44p-bug upgrade-from-version-and-version-sources`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-08
Wave: 1p44n framework-1p6-hardening

## Rationale

The upgrade flow's downgrade guard is silently dead. `_read_installed_revision` (`upgrade_wavefoundry.py:284-290`) reads `.wavefoundry/framework/MANIFEST` and runs `json.loads()` on it, returning `None` on `JSONDecodeError`. But MANIFEST is a newline-delimited path list, not JSON: `build_pack.py:227-228` writes it with `'\n'.join(rel_paths) + '\n'`, and `prune_framework.py:41-46` consumes it via `.splitlines()`. So `json.loads` always raises, and `_read_installed_revision` always returns `None`.

Both callers (`upgrade_wavefoundry.py:836` and `:972`) assign that `None` to `from_version`, and the downgrade guard at `:986` is gated on `if from_version and to_version ...`, so it never executes. The upgrade summary also prints `Version: (none)` because `from_version` is never populated.

This is compounded by version-source divergence: there are four uncoordinated readers — `_read_pack_version` (`:276-281`, from `framework/VERSION`), `_read_installed_revision` (`:284-290`, broken), `_read_zip_version` (`:293-304`, from the zip's VERSION), and the upgrade lock's stored `from`/`to` (`upgrade_lib.py:58-59`) re-read by cleanup/rebuild phases (`:1446-1447`, `:1467-1468`). Nothing makes one of these the source of truth.

Correction confirmed against the source: pruning correctness is unaffected by this bug. Pruning keys off `OLD_MANIFEST_TMP` saved at `:1506` and passed as `--old-manifest` (`:1114-1115`), independent of `from_version`. This change must not alter pruning behavior.

The fix: read the installed revision from `docs/prompts/prompt-surface-manifest.json` (`framework_revision` key, which is genuinely JSON with that key), fall back to `framework/VERSION`, and stop `json.loads`-ing the path-list MANIFEST. Consolidate the version reads behind a single resolver; once the upgrade lock is written, later phases read the version from the lock. This re-enables the downgrade guard and fixes the `Version: (none)` summary.

## Requirements

1. `_read_installed_revision` MUST stop calling `json.loads()` on `.wavefoundry/framework/MANIFEST` (a newline-delimited path list). The MANIFEST file MUST NOT be parsed as JSON anywhere in the version-resolution path.
2. The installed framework revision MUST be read from `docs/prompts/prompt-surface-manifest.json` using the `framework_revision` key (a JSON file that actually contains that key).
3. When `prompt-surface-manifest.json` is absent or lacks a usable `framework_revision`, resolution MUST fall back to `.wavefoundry/framework/VERSION`, returning `None` only when neither source yields a value.
4. On a normal upgrade of an already-installed project, `from_version` MUST be a real revision string (not `None`) at both assignment sites (`upgrade_wavefoundry.py:836` and `:972`).
5. The downgrade guard at `upgrade_wavefoundry.py:986` MUST execute its comparison on a genuine downgrade (installed revision newer than the pack/zip target) instead of being skipped because `from_version` is falsy.
6. A single version-resolver helper MUST be the source of truth for installed-revision resolution; the four divergent readers MUST route through it (or document why a reader legitimately reads a different artifact, e.g. the zip's embedded VERSION).
7. Once the upgrade lock is written (`upgrade_lib.py:58-59`), later phases (cleanup/rebuild at `:1446-1447`, `:1467-1468`) MUST read the from/to versions from the lock rather than independently re-resolving them.
8. Pruning behavior MUST remain byte-for-byte unchanged: it continues to key off `OLD_MANIFEST_TMP` (`:1506`) passed via `--old-manifest` (`:1114-1115`), independent of `from_version`.
9. The upgrade summary MUST print the resolved `from_version` instead of `Version: (none)` when a revision is resolvable.

## Scope

**Problem statement:** `_read_installed_revision` parses the newline-delimited MANIFEST path-list as JSON, so it always returns `None`; this propagates to `from_version`, silently disabling the downgrade guard and producing a `Version: (none)` summary. The same flow has four uncoordinated version sources with no single source of truth.

**In scope:**

- Rewriting `_read_installed_revision` to read `framework_revision` from `docs/prompts/prompt-surface-manifest.json`, with fallback to `framework/VERSION`.
- Introducing a single version-resolver helper and routing the installed-revision readers through it.
- Making later upgrade phases read from/to versions from the upgrade lock once written.
- Re-enabling the downgrade guard at `:986` and fixing the `Version: (none)` summary line.
- Tests for the manifest read, the fallback, and downgrade-guard activation.

**Out of scope:**

- Any change to pruning logic or the `OLD_MANIFEST_TMP` / `--old-manifest` mechanism (`:1114-1115`, `:1506`).
- Changing the on-disk format of `.wavefoundry/framework/MANIFEST` (it stays a newline-delimited path list).
- Changing the zip's embedded VERSION read (`_read_zip_version`), beyond routing it through the shared resolver if applicable.
- Broader refactors to `upgrade_wavefoundry.py` unrelated to version resolution.

## Acceptance Criteria

- [ ] AC-1: `_read_installed_revision` contains no `json.loads()` call against `.wavefoundry/framework/MANIFEST`; the only JSON parsed for revision resolution is `docs/prompts/prompt-surface-manifest.json`.
- [ ] AC-2: On a normal upgrade against a project that has a valid `prompt-surface-manifest.json`, the resolver returns the `framework_revision` value (a real revision string, not `None`), and `from_version` is non-`None` at both `:836` and `:972`.
- [ ] AC-3: When `prompt-surface-manifest.json` is missing or has no usable `framework_revision`, the resolver falls back to `framework/VERSION`; when both are absent, it returns `None`.
- [ ] AC-4: On a genuine downgrade (installed revision newer than target), the downgrade guard at `:986` executes its comparison branch (verifiable via a test that asserts the guard's effect — warning/abort — fires).
- [ ] AC-5: A single version-resolver helper is the sole entry point for installed-revision resolution; all installed-revision readers route through it (grep confirms no other code path re-parses the manifest/VERSION for installed revision).
- [ ] AC-6: After the upgrade lock is written, cleanup/rebuild phases (`:1446-1447`, `:1467-1468`) read from/to versions from the lock (`upgrade_lib.py:58-59`), not by re-resolving.
- [ ] AC-7: Pruning is unchanged — a test (or assertion) confirms pruning still keys off `OLD_MANIFEST_TMP` via `--old-manifest` and produces identical results regardless of `from_version`.
- [ ] AC-8: The upgrade summary prints the resolved `from_version` (no `Version: (none)`) when a revision is resolvable.
- [ ] AC-9 (regression/test): Unit tests cover (a) the manifest read returning `framework_revision`, (b) the fallback to `framework/VERSION`, and (c) downgrade-guard activation on a newer-installed-than-target scenario; all pass in `run_tests.py`.

## Tasks

- [ ] Read `upgrade_wavefoundry.py:276-304` and `:836`/`:972`/`:986` plus `upgrade_lib.py:58-59` and the cleanup/rebuild reads at `:1446-1447`/`:1467-1468` to confirm current control flow.
- [ ] Rewrite `_read_installed_revision` to load `docs/prompts/prompt-surface-manifest.json` and return its `framework_revision`, falling back to `framework/VERSION`; remove the MANIFEST `json.loads` path.
- [ ] Introduce a single version-resolver helper as the source of truth and route the installed-revision callers (`:836`, `:972`) through it.
- [ ] Verify the downgrade guard at `:986` now receives a real `from_version` and fires on a downgrade; fix the summary line so it prints the resolved version.
- [ ] Make cleanup/rebuild phases read from/to versions from the written lock instead of re-resolving.
- [ ] Confirm pruning still keys off `OLD_MANIFEST_TMP` / `--old-manifest` and is untouched.
- [ ] Add/extend tests for the manifest read, the VERSION fallback, and downgrade-guard activation.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and fix failures.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| resolver-rewrite | Engineering | — | Rewrite `_read_installed_revision`; add single resolver helper; route `:836`/`:972` callers |
| guard-and-summary | Engineering | resolver-rewrite | Re-enable downgrade guard at `:986`; fix `Version: (none)` summary |
| lock-read-phases | Engineering | resolver-rewrite | Cleanup/rebuild phases read from/to from the lock (`upgrade_lib.py:58-59`) |
| tests | Engineering | resolver-rewrite, guard-and-summary | Manifest-read, fallback, and downgrade-guard activation tests; pruning-unchanged assertion |


## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` — shared with waves 1p44o, 1p44q, 1p44r, and 1p454. Coordinate edits to avoid conflicting changes in the same file; sequence merges and re-run tests after each.

## Affected Architecture Docs

N/A — this change is confined to version resolution inside `upgrade_wavefoundry.py` (with a read of an existing JSON artifact and the existing upgrade lock). It introduces no new module boundary, data-flow, or verification surface; pruning and the MANIFEST format are explicitly unchanged.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Removing the wrong `json.loads` on the path-list MANIFEST is the root-cause fix. |
| AC-2 | required | `from_version` being a real revision is the core observable behavior the bug breaks. |
| AC-3 | required | Fallback prevents the resolver from regressing to `None` when the manifest is absent. |
| AC-4 | required | Re-enabling the downgrade guard is the primary safety outcome of this change. |
| AC-5 | important | Single source of truth prevents the divergence from re-emerging; structural but not strictly behavioral. |
| AC-6 | important | Reading from the lock removes redundant re-resolution and keeps phases consistent. |
| AC-7 | required | Guarantees the explicit invariant that pruning correctness is unaffected. |
| AC-8 | important | User-visible summary correctness; lower risk than the guard but expected by operators. |
| AC-9 | required | Regression coverage so the silent-`None` failure cannot return undetected. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | Read installed revision from `framework_revision` in `docs/prompts/prompt-surface-manifest.json`, falling back to `framework/VERSION`. | That file is genuinely JSON and contains the `framework_revision` key, so it is the correct source for a revision. | Re-parse `.wavefoundry/framework/MANIFEST` differently — rejected: MANIFEST is a newline-delimited path list by design (`build_pack.py:227-228`, `prune_framework.py:41-46`), not a revision carrier. |
| 2026-06-08 | Consolidate to one version-resolver helper and have later phases read from/to from the written lock. | Four uncoordinated sources (`:276-281`, `:284-290`, `:293-304`, `upgrade_lib.py:58-59`) caused the divergence; a single source of truth and lock-backed reads prevent recurrence. | Leave readers independent — rejected: keeps the divergence risk that this bug exemplifies. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Routing readers through one resolver inadvertently changes the zip-VERSION read path. | Keep `_read_zip_version` distinct (it reads a different artifact); only consolidate the installed-revision readers; cover with tests. |
| Reworking phase reads accidentally alters pruning, which keys off `OLD_MANIFEST_TMP`. | Treat pruning as out of scope; add AC-7 assertion that pruning still uses `--old-manifest` and is independent of `from_version`. |
| Projects without `prompt-surface-manifest.json` lose revision resolution. | Explicit fallback to `framework/VERSION`, with `None` only when both are absent (AC-3). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
