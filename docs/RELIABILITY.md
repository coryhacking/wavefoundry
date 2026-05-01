# Reliability

Owner: Engineering
Status: active
Last verified: 2026-04-30

## Reliability Posture

Wavefoundry is local developer tooling. No uptime SLA; failures are immediately visible to the operator. Primary reliability concern is **correctness** (producing valid framework distributions and lint results) rather than availability.

## Known Reliability Risks

| Risk | Affected Domain | Mitigation |
|------|----------------|-----------|
| `.wavefoundry/framework/` missing or corrupted | All scripts via `.wavefoundry/` | `ls .wavefoundry/framework/` check; restore from git if needed |
| `docs_lint.py` false positive | Docs gate | Framework script tests cover common cases; fixture tests validate lint behavior |
| VERSION stamp mismatch | build_pack.py / distribution | Always use `build_pack.py`; never manually edit VERSION |
| `render_platform_surfaces.py` partial write | Hook entrypoints | Script is idempotent; re-run if interrupted |
| No automated test runs | Framework scripts | Run `python3 .wavefoundry/framework/scripts/run_tests.py` before any framework script change |

## Recovery Behaviors

- **Framework dir missing:** `git checkout HEAD -- .wavefoundry/framework` to restore from git
- **Docs gate failing:** With MCP, run **`wave_validate`** (or **`wave_audit`** for combined diagnostics). **CLI fallback:** `.wavefoundry/bin/docs-lint` for raw output when MCP is unavailable
- **Hook entrypoints missing:** re-run `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py`
- **Partial zip archive:** re-run `python3 .wavefoundry/framework/scripts/build_pack.py`; the script is idempotent and will produce a new letter-suffixed archive

## Reliability Hotspots (from domain-map)

| Hotspot | Risk | Notes |
|---------|------|-------|
| `.wavefoundry/framework/VERSION` | Written by `build_pack.py`; read by `docs_lint.py` | These must stay in sync; `build_pack.py` ensures this atomically |
| `prompt-surface-manifest.json` `framework_revision` | Drift from actual VERSION causes lint failure | Update manifest whenever running init/upgrade |
| Future MCP code index | Index may become stale if target repo changes | Re-index trigger TBD in server design |
