# build_pack.py Pre-flight Checks

Change ID: `12r7a-maint build-pack-preflights`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-19
Wave: `12r09 automated-upgrade`

## Rationale

Packaging a Wavefoundry distribution zip is a multi-step manual process. Two of those steps — running the docs gate and verifying that `prompt-surface-manifest.json` records the correct `framework_revision` — were performed by the operator before running `build_pack.py`, with no automated enforcement. Folding them into the script makes packaging self-verifying: a stale manifest or broken docs will abort the build before a zip is stamped, rather than shipping a bad artifact.

## Requirements

1. `check_manifest_revision(repo_root, expected_version)` reads `docs/prompts/prompt-surface-manifest.json`, compares its `framework_revision` field to the expected next version, and exits 1 with a clear diagnostic on mismatch or missing file.
2. `check_docs_gate(repo_root)` runs `docs-gardener` then `docs-lint` from `.wavefoundry/bin/`. It exits 1 immediately if either command is not found or returns non-zero, naming the failing command in the error.
3. `main()` in `build_pack.py` runs the docs gate first, then peeks at `next_suffix` to compute `expected_version`, then runs the manifest check — both before `build_zip` is called.
4. `--skip-docs-gate` bypasses the docs gate check. `--skip-manifest-check` bypasses the manifest check. Both flags are documented in `--help`.
5. The `next_suffix` call used for the manifest pre-flight is a read-only peek; `build_zip` makes its own independent call. The two calls return the same value because no zip is written between them.

## Scope

**In scope:**

- `scripts/build_pack.py` — `check_manifest_revision`, `check_docs_gate`, `--skip-docs-gate`, `--skip-manifest-check` flags, wiring in `main()`
- `scripts/tests/test_build_pack.py` — `ManifestRevisionTests` (5 tests), `DocsGateTests` (6 tests)

**Out of scope:**

- Test-suite gate (checking all tests pass before packaging) — intentionally left as a manual operator step; it involves running the full suite and takes ~2 minutes, better surfaced in the packaging runbook than baked into the script
- Rotating or compressing old zips before building the next one
- Manifest validation beyond `framework_revision` (other fields are operator-managed)

## Acceptance Criteria

- AC-1: `build_pack.py` exits 1 with a diagnostic when `prompt-surface-manifest.json` records a version that doesn't match the next stamp.
- AC-2: `build_pack.py` exits 1 with a diagnostic when `framework_revision` is absent from the manifest.
- AC-3: `build_pack.py` exits 1 when `docs-gardener` or `docs-lint` is not found or fails.
- AC-4: `--skip-manifest-check` and `--skip-docs-gate` bypass their respective checks.
- AC-5: All existing `BuildPackTests` continue to pass (no regression).

## Tasks

- Add `check_manifest_revision(repo_root, expected_version)` to `build_pack.py`
- Add `check_docs_gate(repo_root)` to `build_pack.py`
- Wire both pre-flights into `main()` with skip flags
- Write `ManifestRevisionTests` and `DocsGateTests`
- Update `docs/prompts/prompt-surface-manifest.json` `framework_revision` to `2026-05-19b`

## Affected Architecture Docs

N/A — packaging-tool change; no MCP surface, schema, or architecture boundary impact.

## AC Priority

| AC   | Priority  | Rationale                                         |
| ---- | --------- | ------------------------------------------------- |
| AC-1 | required  | Core deliverable — stale manifest must be caught  |
| AC-2 | required  | Missing field is equally invalid                  |
| AC-3 | required  | Broken docs must block packaging                  |
| AC-4 | required  | Escape hatch needed for tests and special cases   |
| AC-5 | required  | No regression                                     |

## Progress Log

| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-05-19 | Implemented. `check_manifest_revision` and `check_docs_gate` added; wired into `main()` with `--skip-manifest-check` and `--skip-docs-gate`. 11 new unit tests. `framework_revision` in manifest updated to `2026-05-19b`. 1439 tests pass. | `python3 .wavefoundry/framework/scripts/run_tests.py` — 1439 OK |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-19 | Docs gate uses `.wavefoundry/bin/` bin scripts directly, no Python fallback | Bin scripts are the canonical interface; adding a Python fallback discovery path adds complexity for an edge case that shouldn't occur in a properly set-up repo | Discover Python equivalents as fallback |
| 2026-05-19 | `next_suffix` called twice (peek + inside `build_zip`) | Simpler than threading the suffix through `build_zip` as a parameter; idempotent because no zip is written between calls | Pass computed suffix into `build_zip` |
| 2026-05-19 | Test-suite gate left as manual step | ~2 min run time; better as a runbook item than a blocking `build_pack` step | Add `--run-tests` flag |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
