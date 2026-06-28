# Agent Body — Plan Feature

Owner: Engineering
Status: active
Last verified: 2026-06-27

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
wf lifecycle-id --kind <kind> --slug <slug>
```

Epoch: `2022-04-28T00:00:00Z` → IDs look like `0xxxx-<kind> <slug>`.

## Affected Architecture Docs

Required when the change crosses module boundaries, integration contracts, primary data/control paths, or test/release seams. Reference specific child docs under `docs/architecture/`. If not applicable, write `N/A` with a one-line rationale.

## Framework / Prompt-Surface Plans

When the change touches `docs/prompts/`, `AGENTS.md`, seed prompts, or hook configs:
- Name intended file edits
- Identify protected surfaces
- Define read-only vs write-owning lanes

## Guru Orientation

Before drafting the change doc, run an orientation pass to ground the plan in indexed evidence:

```
code_search(topic, kind="code-summary", limit=5) # which modules are relevant?
code_ask("how does X currently work?") # existing behavior; inspect partition_applied/final_rank when present
code_dependencies(path) # what does the target file depend on?
```

Use the results to populate `## Rationale` and `## Affected architecture docs` with specific citations. A plan grounded in indexed evidence is easier to scope accurately and harder to challenge.

If MCP is not available, use `grep -r "keyword" .` scoped to likely directories. Cite results as `path:line_number` and note that results are from a keyword scan.

## Stage Gate Reminder

Repository code must not be edited until:
1. This change doc exists
2. The change is admitted via **Create wave** / **Add change to wave**
3. **Prepare wave** has passed cleanly
