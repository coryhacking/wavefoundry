# Leiden Bootstrap Dependencies

Change ID: `12xwz-maint leiden-bootstrap-dependencies`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

The graph clustering implementation now prefers Leiden when `igraph` and `leidenalg` are present. `setup_wavefoundry.py` delegates to `setup_index.py` for environment bootstrap, and `setup_index.py` is the installer of record for framework dependencies. If Leiden is only listed in `pyproject.toml`, bootstrap can still leave the shared tool venv without the clustering backend and the graph pipeline falls back to the local compatibility path.

This change keeps the bootstrap surface aligned with the graph clustering contract: if the repo declares Leiden as a supported clustering backend, the canonical setup path should install it automatically.

## Requirements

1. Add `igraph` and `leidenalg` to the bootstrap dependency check in `setup_index.py`.
2. Preserve the existing install flow and venv bootstrap behavior.
3. Add tests that ensure the bootstrap dependency list includes the Leiden packages.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`

**Out of scope:**

- graph clustering logic itself
- dashboard visualization changes
- any change to the canonical graph artifact schema

## Acceptance Criteria

- [x] AC-1: `setup_index.py` installs `igraph` and `leidenalg` when they are missing from the tool venv.
- [x] AC-2: The bootstrap path still uses the existing venv install flow and does not change any unrelated dependency handling.
- [x] AC-3: Tests cover the presence of the Leiden packages in the required dependency list.

## Tasks

- [x] Add `igraph` and `leidenalg` to the bootstrap dependency map.
- [x] Add or update tests for the required dependency list.
- [x] Verify the setup script still reports a clean satisfied-deps path when the packages are present.

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-27 | Added as a bootstrap follow-up so Leiden is installed by the canonical setup path instead of relying on pyproject-only metadata. | `setup_index.py`, `setup_wavefoundry.py` |

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The tool venv must receive the clustering backend automatically |
| AC-2 | required | Bootstrap behavior should remain consistent with the existing setup flow |
| AC-3 | required | Dependency coverage needs test enforcement so the setup path does not drift |
