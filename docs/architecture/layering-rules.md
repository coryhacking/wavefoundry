# Layering Rules

Owner: Engineering
Status: active
Last verified: 2026-04-30

## Allowed Dependencies

| Layer | May Import / Read | May Not Import / Read |
|-------|-----------------|----------------------|
| `.wavefoundry/framework/seeds/` | Nothing (text files only) | Any runtime code |
| `.wavefoundry/framework/scripts/` | Python stdlib; `.wavefoundry/framework/scripts/wave_lint_lib/` | `src/wavefoundry/` (future MCP) |
| `src/wavefoundry/` (future) | Python stdlib; third-party libs; `.wavefoundry/framework/seeds/` for seed resolution | `.wavefoundry/framework/scripts/` (use as library only if explicitly extracted) |
| `docs/` | N/A (markdown only; consumed by scripts, not importing scripts) | — |

## Boundary Invariants

| Edge | Invariant | Verified / Inferred |
|------|-----------|----------------------|
| MCP server → target repo | Must never write outside configured allowed roots without mutation tool approval | Inferred from AGENTS.md and seed-050 safety rules |
| `build_pack.py` → VERSION | Must stamp VERSION before writing zip; VERSION must match zip basename date+letter | Verified from build_pack.py behavior described in seeds |
| `docs_lint.py` → manifest | Must fail (exit non-zero) when `framework_revision` in manifest does not match `.wavefoundry/framework/VERSION` | Verified from seed-010 lint gate requirement |
| `render_platform_surfaces.py` → `.github/` | Must not create or modify `.github/workflows/` — only `.github/hooks/` | Verified from seed-050 scope boundary |

## Violation Detection

- Dependency violations: currently informal (no import linter); enforce through code review using this doc.
- Boundary invariants: enforced through MCP **`wave_validate`** (agents) or **`.wavefoundry/bin/docs-lint`** (hooks/CI), plus seed protection hook and framework plan gate hook.
