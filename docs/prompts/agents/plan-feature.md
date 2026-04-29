# Agent Body — Plan Feature

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Context

You are running **Plan feature** on Wavefoundry. Author a consolidated change document following `docs/plans/plan-template.md`.

## Change ID Generation

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
