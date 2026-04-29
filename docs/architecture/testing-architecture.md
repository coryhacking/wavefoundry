# Testing Architecture

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Test Tiers

| Tier | Scope | Location | Runner |
|------|-------|----------|--------|
| Framework script unit tests | `docs_lint.py`, `build_pack.py` behavior | `.wavefoundry/framework/scripts/tests/` | `python3 .wavefoundry/framework/scripts/run_tests.py` |
| Fixture-based integration | Docs-lint against fixture repos | `.wavefoundry/framework/scripts/tests/fixtures/` | Same runner |
| Manual docs gate | `./docs-lint` passes on current repo | Repo root | `./docs-lint` |
| Manual gardener | `./docs-gardener` refreshes metadata | Repo root | `./docs-gardener` |

## Test File Locations

| Test File | What It Tests |
|-----------|--------------|
| `.wavefoundry/framework/scripts/tests/test_docs_gardener.py` | docs_gardener behavior |
| `.wavefoundry/framework/scripts/tests/test_build_pack.py` | build_pack.py behavior |
| `.wavefoundry/framework/scripts/tests/fixtures/docs_lint/base/` | Fixture target repo for docs_lint tests |

## Doubles Policy

- No mocking of file I/O; tests use fixture directories as real file trees.
- Tests do not connect to external services; all operations are local file reads/writes.

## CI / CD

No automated CI pipeline currently. All tests run manually.

Minimum verification bar for any framework script change:
1. `python3 .wavefoundry/framework/scripts/run_tests.py` passes (no bytecode: use `-B` flag or the run_tests.py wrapper)
2. `./docs-lint` passes on the Wavefoundry repo itself

## Framework Script Hygiene

Run tests without writing bytecode: `python3 -B .wavefoundry/framework/scripts/run_tests.py`. If caches were written, clean them:

```bash
find .wavefoundry/framework/scripts -type d -name '__pycache__' -prune -exec rm -rf {} \;
```

## Minimum Verification Bar for Cross-Module Changes

Any change touching `.wavefoundry/framework/scripts/wave_lint_lib/` or `docs_lint.py`:
- All existing fixture tests must pass
- `./docs-lint` must pass on the Wavefoundry repo

Any change to `docs/prompts/prompt-surface-manifest.json` or `.wavefoundry/framework/VERSION`:
- `./docs-lint` must pass (it validates the manifest `framework_revision`)
