# Agent Body — Plan Feature

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Context

You are running **Plan feature** on Wavefoundry. Author a consolidated change document following `docs/plans/plan-template.md`.

## Change ID Generation

Use MCP first when the Wavefoundry server is available. The `wave_new_*` tools generate the lifecycle ID and scaffold `docs/plans/<change-id>.md` in one call:

| Kind | MCP tool |
|------|----------|
| `feat` | `wave_new_feature` |
| `bug` | `wave_new_bug` |
| `enh` | `wave_new_enhancement` |
| `ref` | `wave_new_refactor` |
| `change` | `wave_new_change` |
| `doc` | `wave_new_documentation` |
| `debt` | `wave_new_tech_debt` |
| `task` | `wave_new_task` |
| `maint` | `wave_new_maintenance` |
| `ops` | `wave_new_operations` |

If MCP is unavailable, use the CLI fallback:

```bash
python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>
```

Epoch: `2022-04-28T00:00:00Z` → IDs look like `0xxxx-<kind> <slug>`.

## Affected Architecture Docs

Required when the change crosses module boundaries, integration contracts, primary data/control paths, or test/release seams. Reference specific child docs under `docs/architecture/`. If not applicable, write `N/A` with a one-line rationale.

## Framework / Prompt-Surface Plans

When the change touches `docs/prompts/`, `AGENTS.md`, seed prompts, or hook configs:
- Name intended file edits
- Identify protected surfaces
- Define read-only vs write-owning lanes

## Stage Gate Reminder

Repository code must not be edited until:
1. This change doc exists
2. The change is admitted via **Create wave** / **Add change to wave**
3. **Prepare wave** has passed cleanly
