# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-23

wave-id: `12tms python-env-and-semver-implementation`
Title: Python Env and Semver Implementation

## Objective

Implement the two rollout-readiness contracts decided in wave `12t9b`: adopt a shared user-level tool venv at `~/.wavefoundry/venv` (removing the `--break-system-packages` hack), and migrate all version identifiers from `YYYY-MM-DDx` date strings to `MAJOR.MINOR.PATCH` semver starting at `1.0.0`.

## Changes

Change ID: `12tm5-enh python-tool-venv-bootstrap`
Change Status: `implemented`

Change ID: `12tm5-enh migrate-versioning-to-semver`
Change Status: `implemented`

Change ID: `12tp1-enh venv-python-launchers`
Change Status: `implemented`

## Coordinator

- `wave-coordinator`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| implementer | implement | both changes |
| wave-coordinator | coordinate | full wave lifecycle routing and readiness gate |
| qa-reviewer | review | both changes — AC coverage, test fidelity, migration correctness |
| release-reviewer | review | `12tm5-enh migrate-versioning-to-semver` — semver artifact naming, upgrade ordering, packaging contract |
| architecture-reviewer | review | both changes — runtime environment boundary and version contract coherence |

Completed At: 2026-05-23

## Wave Summary

Wave `12tms` (Python Env and Semver Implementation) delivered 3 changes: Python Tool Venv Bootstrap, Migrate Versioning To Semver, and Venv Python Launchers. Notable adjustments during implementation: Python Tool Venv Bootstrap: Implemented. `_bootstrap_venv()` + `_missing_in_venv()` added; `_install_deps()` rewritten to venv Python; `--break-system-packages` removed; `pyproject.toml` created; docs updated; `test_setup_index.py` rewritten. 1580 tests pass.; Migrate Versioning To Semver: Revised starting version to v0.9.0 bridge → v1.0.0 clean semver. Added the bridge artifact requirement: `0.9.0` remains semver internally but must keep the old date-style zip naming so legacy pre-semver upgrade flows can adopt it directly. Added red-team risks: packaging bootstrap ordering, date-string detection scope, dist-dir malformed filenames.; Migrate Versioning To Semver: Implemented. `check_version.py` rewritten with `_to_version()` + semver `compare_versions()`; `build_pack.py` redesigned for `--version` flag, dist dir, semver internals, and bridge artifact naming; `upgrade_wavefoundry.py` `_find_latest_release_zip()` + UpgradeContext docstring; `packaging` added to `pyproject.toml`; `test_check_version.py` created; `test_build_pack.py` + `test_upgrade_wavefoundry.py` updated; docs updated.

**Changes delivered:**

- **Python Tool Venv Bootstrap** (`12tm5-enh python-tool-venv-bootstrap`) — 7 ACs completed. Key decisions: --------; Use `~/.wavefoundry/venv` as the default shared tool environment.
- **Migrate Versioning To Semver** (`12tm5-enh migrate-versioning-to-semver`) — 10 ACs completed. Key decisions: --------; Start at `1.0.0`. Operator-confirmed 2026-05-22.
- **Venv Python Launchers** (`12tp1-enh venv-python-launchers`) — 13 ACs completed
## Journal Watchpoints

- **Watchpoint:** `pyproject.toml` must be created by `12tm5-enh python-tool-venv-bootstrap` before `12tm5-enh migrate-versioning-to-semver` adds `packaging` as a dependency — land both in the same wave; do not implement semver change first.
- **Watchpoint:** `_to_version()` in `check_version.py` must exist before `build_pack.py` and `upgrade_wavefoundry.py` are updated — both depend on it.
- **Watchpoint:** Do not stamp `VERSION` to `1.0.0` until `build_pack.py` semver support is complete — the packager will reject a semver string before that change lands.
- **Watchpoint:** `upgrade_wavefoundry.py` must handle `~/.wavefoundry/dist/` being absent gracefully (fall back to project directory); `build_pack.py` creates the directory on first use.
- **Watchpoint:** Update both `test_build_pack.py` and `test_upgrade_wavefoundry.py` — date-string test cases must be removed or updated; semver and dist-dir cases must be added.
- **Watchpoint:** v0.9.0 is the bridge release. It must stamp semver internally (`0.9.0+<build>`) while keeping the old date-style zip artifact name so legacy pre-semver zip-adoption flows can land it directly before the new semver-aware upgrader takes over.
- **Watchpoint:** `upgrade_wavefoundry.py` may be run with system Python before the venv is bootstrapped. Use a lazy import for `packaging` with a clear error message directing operators to run `setup_wavefoundry.py` first.

## Review Evidence

- wave-council-readiness: approved 2026-05-22 — Two implementation changes admitted with complete AC sets, checkbox tasks, and binding decisions from `12t9b`. Serialization through `pyproject.toml` creation is the only cross-change dependency; documented as a watchpoint and serialization point. Required reviewer lanes: qa-reviewer for both changes; release-reviewer for semver artifact naming, upgrade ordering, and packaging contract; architecture-reviewer for runtime environment boundary and version contract coherence. Red-team blocking findings resolved: packaging bootstrap-ordering risk (lazy import + error); partial venv failure (detect absent binary, recreate). Advisory findings resolved: date-string regex + ValueError; dist-dir skip of non-matching files. Legacy upgrade path resolved by treating `0.9.0` as a bridge release that keeps the old date-style artifact name while installing the new semver-aware upgrader. Wave is ready for implementation.
- wave-council-delivery: approved 2026-05-23 — synthesized after fixed-seat review (qa-reviewer, architecture-reviewer, security-reviewer, reality-checker, red-team) plus rotating domain seat release-reviewer. All specialist lanes pass. Two non-blocking advisories: (1) `update_manifest_revision()` design change (operator-directed during close session) not reflected in 12tm5-semver progress log — recorded here instead; (2) in-session improvements (home-dir zip search, hook absolute paths, manifest revision fix, test isolation) not individually wave-doc'd in progress log. Neither advisory blocks closure. 1614 tests pass; docs-lint clean.
- operator-signoff: approved — operator confirmed closure 2026-05-23

## Review Checkpoints

- **Pre-implementation review — 2026-05-22: PASS** — Highest risk: `packaging` import before venv bootstrapped; mitigated by lazy import with clear `ModuleNotFoundError`. Partial venv failure mitigated by absent-binary detection and recreate. All five identified risks covered in change doc mitigations. Proceed to implementation.

- **Prepare-phase Wave Council [prepare-council] — 2026-05-22: PASS** (red-team fixed seat; architecture-reviewer rotating seat; qa-reviewer, release-reviewer additional)
  - Both change docs have complete, testable AC sets with checkbox tasks and populated AC priority tables. Decisions are binding from `12t9b`; no open planning questions.
  - Release-reviewer: semver artifact naming, dist-dir workflow, mixed-version migration path, and `packaging` dependency serialization are all correctly scoped and documented.
  - Architecture-reviewer: minimal blast radius — venv change wires existing dead code; semver change centralizes migration logic in `_to_version()`. Cross-change dependency limited to `pyproject.toml` creation; serialization is explicit.
  - Red-team (fixed): two blocking findings addressed before implementation. (1) `packaging` bootstrap-ordering risk — `upgrade_wavefoundry.py` may run with system Python before the venv exists; mitigated with lazy import + clear error. (2) Partial venv creation failure leaves broken state; mitigated by detecting absent venv Python binary and recreating. Advisory findings: date-string detection underspecified (resolved: explicit regex + `ValueError` on unknown formats); dist-dir non-matching filenames (resolved: skip silently, covered by AC-5 and AC-7). Legacy upgrade path risk (old upgrade scripts cannot compare semver against date strings) is resolved by the `0.9.0` bridge artifact using the old date-style zip naming while carrying the new semver-aware upgrader inside the pack.
  - No blocking contradictions between the two changes. Proceed to implementation.

- **Delivery review [wave-council-delivery] — 2026-05-23: PASS** (release-reviewer rotating seat; qa-reviewer, architecture-reviewer, security-reviewer, reality-checker, red-team fixed seats)
  - QA (fixed): All required-priority ACs evidenced in code and tests. `_bootstrap_venv()` / `_missing_in_venv()` / `_tool_venv_python()` present; no `--break-system-packages`. `pyproject.toml` exists with `packaging>=24`. `_to_version()` with explicit `YYYY-MM-DDx` regex; `compare_versions()` via `packaging.version.Version`; `ValueError` on unknown formats. `manifest.framework_revision` stamped at `1.0.0+2v2n`. 1614 tests pass; docs-lint clean.
  - Release (rotating): Semver zip naming (`wavefoundry-MAJOR.MINOR.PATCH.<build>.zip`) confirmed correct. Version ordering verified: `compare_versions("1.10.0", "1.9.0")` → `"upgrade"`. Dist-dir discovery and home-dir search functional. Bridge artifact design correct — `0.9.0` uses old date-style zip name while carrying new semver-aware upgrader. Advisory: `update_manifest_revision()` design change (replacing `check_manifest_revision()` check with a write during packaging) was directed by operator during this session but is not reflected in the 12tm5-semver progress log; record here instead.
  - Architecture (fixed): Bootstrap exception boundary explicit — lazy `packaging` import in `upgrade_wavefoundry.py` with clear `ModuleNotFoundError`. Venv path overridable via `WAVEFOUNDRY_TOOL_VENV`. Single centralized `_to_version()` in `check_version.py`. Minimal blast radius: venv change wires existing dead code; semver change replaces one comparison function.
  - Security (fixed): No new trust boundaries. `WAVEFOUNDRY_TOOL_VENV` used as a path only, not evaluated. `packaging` is a well-maintained PyPA library; no shell-execution of zip content.
  - Reality-checker (fixed): No false confidence. All ACs checked have direct code or test evidence. Advisory: in-session improvements landed outside wave doc scope — home-dir zip search, hook absolute paths, manifest revision fix, and test isolation (`update_manifest=False`) are shipped but not in the progress log; advisory recorded in wave-council-delivery evidence line.
  - Red-team (fixed): No bypass paths found. Manifest stamped inside `build_zip()` before zip assembly — cannot produce a zip with a stale revision. Home-dir search uses the same semver ordering as other locations; no injection or ordering attack surface. Lazy import failure path tested. Wave closes with no blocking security findings.

## Dependencies

- Wave `12t9b public-rollout-readiness-decisions` (closed) — source of all binding decisions implemented here.

## Serialization Points

- `python-tool-venv-bootstrap` creates `pyproject.toml`; `migrate-versioning-to-semver` adds `packaging` to it — implement together, `pyproject.toml` first.
- `_to_version()` helper in `check_version.py` must land before `build_pack.py` and `upgrade_wavefoundry.py` updates.
- `build_pack.py` semver support must be complete before `VERSION` is stamped to `1.0.0`.

## Execution Plan

1. Implement `12tm5-enh python-tool-venv-bootstrap`:
   - `_bootstrap_venv()` + `_tool_venv_python()` default update + `_install_deps()` rewrite
   - Add `pyproject.toml`
   - Update docs and tests
2. Implement `12tm5-enh migrate-versioning-to-semver`:
   - `_to_version()` + `compare_versions()` rewrite in `check_version.py`
   - `build_pack.py` semver input + artifact naming + `~/.wavefoundry/dist/` default
   - `upgrade_wavefoundry.py` dist-dir discovery + hook rewrites
   - Add `packaging` to `pyproject.toml`
   - Update tests and docs
3. Run full test suite; verify semver round-trip and mixed-version upgrade path.

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-22 | Wave created. Both changes carry binding decisions from `12t9b`; implementation begins when wave is prepared and active. | `docs/plans/12tm5-enh python-tool-venv-bootstrap.md`, `docs/plans/12tm5-enh migrate-versioning-to-semver.md` |
| 2026-05-22 | Red-team review completed. Two blocking findings resolved (packaging bootstrap ordering, partial venv failure). Starting version revised to v0.9.0 bridge → v1.0.0 clean semver. Change docs updated with new ACs, risks, and decisions. | Red-team prepare-council findings; operator confirmation of v0.9.0 bridge approach. |
| 2026-05-22 | Implementation complete. `12tm5-enh python-tool-venv-bootstrap`: `setup_index.py` rewritten with `_bootstrap_venv()` / `_missing_in_venv()`, `--break-system-packages` removed, `pyproject.toml` created, tests rewritten. `12tm5-enh migrate-versioning-to-semver`: `check_version.py` rewritten with `_to_version()` and semver `compare_versions()`, `build_pack.py` redesigned for semver, `upgrade_wavefoundry.py` gets `_find_latest_release_zip()`, `test_check_version.py` created. 1601 tests pass. | All AC checkboxes complete in both change docs at that implementation point. |
| 2026-05-23 | Bridge-packaging correction completed. `0.9.0` remains semver internally but now packages with the old date-style zip naming so legacy pre-semver upgrade flows can adopt it directly. The helper-based `migrate_legacy_revision.py` bridge path was removed from the active operator contract, and the packaging/upgrade docs plus canonical seeds were reconciled to the corrected bridge design. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_build_pack.py'`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_upgrade_wavefoundry.py'`; `python3 .wavefoundry/framework/scripts/docs_lint.py` |
| 2026-05-23 | `12tp1-enh venv-python-launchers` implemented. `render_platform_surfaces.py` updated with `_venv_python_path()` and venv-aware templates for all bin launchers and MCP JSON configs. `upgrade-wavefoundry` launcher now generated by `render_bin_launchers()`. All surfaces regenerated. `install-wavefoundry.prompt.md` MCP copy-ready entries updated. 1601 tests pass. | Initial launcher/runtime AC set complete at implementation time; later follow-ons extended the same change. |
| 2026-05-23 | Final Python-runtime hardening completed inside `12tp1-enh venv-python-launchers`. `server_impl.py` and `upgrade_wavefoundry.py` now resolve the shared tool venv explicitly for operator-facing runtime subprocesses instead of relying on inherited `sys.executable`, while preserving the intentional fresh-machine bootstrap exception. Additional regression coverage landed for MCP helper subprocesses and upgrade-phase runtime selection. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_server_tools.py'`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_upgrade_wavefoundry.py'`; `python3 .wavefoundry/framework/scripts/docs_lint.py` |
| 2026-05-23 | Policy-A bootstrap follow-on completed inside `12tp1-enh venv-python-launchers`. `setup_wavefoundry.py` is now the canonical operator bootstrap command, `.wavefoundry/bin/setup-wavefoundry` is generated as its wrapper, remaining operator-facing recovery text was shifted to prefer it, and the native Windows `upgrade-wavefoundry.bat` wrapper was removed to stay aligned with the WSL2-only operator stance. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_setup_wavefoundry.py'`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_render_platform_surfaces.py'`; `python3 .wavefoundry/framework/scripts/docs_lint.py` |
| 2026-05-23 | Canonical seed reconciliation completed for the shipped semver + Python-runtime contract. The framework seeds now describe semver packaging (`wavefoundry-MAJOR.MINOR.PATCH.<build>.zip`, `VERSION`/`framework_revision` stamping, `~/.wavefoundry/dist/` default), semver-based upgrade adoption/version guard, and `setup_wavefoundry.py` as the canonical bootstrap command with `setup_index.py` retained only as the compatibility path behind it. Self-hosted packaging/upgrade prompts were refreshed to match. | `python3 .wavefoundry/framework/scripts/docs_lint.py`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_docs_lint.py'` |
