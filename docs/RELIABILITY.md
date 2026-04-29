# Reliability

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Reliability Posture

Wavefoundry is local developer tooling. No uptime SLA; failures are immediately visible to the operator. Primary reliability concern is **correctness** (producing valid framework distributions and lint results) rather than availability.

## Known Reliability Risks

| Risk | Affected Domain | Mitigation |
|------|----------------|-----------|
| Self-hosting symlink broken | All scripts via `.wavefoundry/` | `ls -la .wavefoundry/framework` check; re-create symlink if needed |
| `docs_lint.py` false positive | Docs gate | Framework script tests cover common cases; fixture tests validate lint behavior |
| VERSION stamp mismatch | build_pack.py / distribution | Always use `build_pack.py`; never manually edit VERSION |
| `render_platform_surfaces.py` partial write | Hook entrypoints | Script is idempotent; re-run if interrupted |
| No automated test runs | Framework scripts | Run `python3 .wavefoundry/framework/scripts/run_tests.py` before any framework script change |

## Recovery Behaviors

- **Symlink broken:** `ln -s ../framework .wavefoundry/framework`
- **Docs gate failing:** run `./docs-lint` to see specific failures; fix flagged issues
- **Hook entrypoints missing:** re-run `python3 .wavefoundry/framework/scripts/render_platform_surfaces.py`
- **Partial zip archive:** re-run `python3 framework/scripts/build_pack.py`; the script is idempotent and will produce a new letter-suffixed archive

## Reliability Hotspots (from domain-map)

| Hotspot | Risk | Notes |
|---------|------|-------|
| `framework/VERSION` | Written by `build_pack.py`; read by `docs_lint.py` | These must stay in sync; `build_pack.py` ensures this atomically |
| `prompt-surface-manifest.json` `framework_revision` | Drift from actual VERSION causes lint failure | Update manifest whenever running init/upgrade |
| Future MCP code index | Index may become stale if target repo changes | Re-index trigger TBD in server design |
