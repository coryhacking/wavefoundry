# Agent Body — Upgrade Wave Framework

Owner: Engineering
Status: active
Last verified: 2026-04-30

## Context

You are running **Upgrade wave framework** (seed-160) on the Wavefoundry repository. Self-hosting mode: `.wavefoundry/framework/` is the canonical framework directory.

## Upgrade Contract

1. Inventory/drift-detection subagents run **read-only**.
2. Produce a concise file-level upgrade plan before broad edits to `docs/prompts/`, `AGENTS.md`, or hook configs.
3. Update existing canonical docs in place; do not create parallel files when a topical home already exists.
4. After reconciliation: verify the docs gate — **with MCP**, run **`wave_garden`** (if needed) then **`wave_validate`**; **without MCP**, run `.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`. Fix all failures.

## Protected Surfaces

Require `framework_edit_allowed` guard approval for broad changes to:
- `docs/prompts/`
- `AGENTS.md`
- Hook configs (`.claude/settings.json`, `.cursor/hooks.json`, `.github/hooks/hooks.json`)

## Git Commits

Operator-owned. Hand off diff + suggested message; do not run `git commit`.

## Version Guard

After unpacking a new zip: verify `docs/prompts/prompt-surface-manifest.json` `framework_revision` matches the new `.wavefoundry/framework/VERSION`. Update manifest if needed.
