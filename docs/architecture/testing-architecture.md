# Testing Architecture

Owner: Engineering
Status: active
Last verified: 2026-04-30

## Test Tiers

| Tier | Scope | Location | Runner |
|------|-------|----------|--------|
| Framework script unit tests | `docs_lint.py`, `build_pack.py` behavior | `.wavefoundry/framework/scripts/tests/` | `python3 .wavefoundry/framework/scripts/run_tests.py` |
| Fixture-based integration | Docs-lint against fixture repos | `.wavefoundry/framework/scripts/tests/fixtures/` | Same runner |
| Manual docs gate | MCP **`wave_validate`** succeeds, **or** `.wavefoundry/bin/docs-lint` passes | MCP / repo root | `wave_validate` / `.wavefoundry/bin/docs-lint` |
| Manual gardener | MCP **`wave_garden`**, **or** `.wavefoundry/bin/docs-gardener` | MCP / repo root | `wave_garden` / `.wavefoundry/bin/docs-gardener` |

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
2. Docs gate: **agents** — MCP **`wave_validate`** succeeds (use **`wave_garden`** first when metadata needs refresh); **CI / no MCP** — `.wavefoundry/bin/docs-lint` passes on the Wavefoundry repo itself

## Framework Script Hygiene

Run tests without writing bytecode: `python3 -B .wavefoundry/framework/scripts/run_tests.py`. If caches were written, clean them:

```bash
find .wavefoundry/framework/scripts -type d -name '__pycache__' -prune -exec rm -rf {} \;
```

## Minimum Verification Bar for Cross-Module Changes

Any change touching `.wavefoundry/framework/scripts/wave_lint_lib/` or `docs_lint.py`:
- All existing fixture tests must pass
- Docs gate: **`wave_validate`** (MCP) or **`.wavefoundry/bin/docs-lint`** (CLI) on the Wavefoundry repo

Any change to `docs/prompts/prompt-surface-manifest.json` or `.wavefoundry/framework/VERSION`:
- **`wave_validate`** or **`.wavefoundry/bin/docs-lint`** must pass (manifest `framework_revision` validation)
