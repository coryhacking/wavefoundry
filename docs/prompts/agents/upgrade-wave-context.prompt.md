# Agent Body — Upgrade Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-06-15

## Context

You are running **Upgrade Wavefoundry** (seed-160) on the Wavefoundry repository. Self-hosting mode: `.wavefoundry/framework/` is the canonical framework directory.

## Upgrade Contract

1. Inventory/drift-detection subagents run **read-only**.
2. Produce a concise file-level upgrade plan before broad edits to `docs/prompts/`, `AGENTS.md`, or hook configs.
3. Update existing canonical docs in place; do not create parallel files when a topical home already exists.
4. After reconciliation: verify the docs gate — **with MCP**, run **`wave_garden`** (if needed) then **`wave_validate`**; **without MCP**, run `.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`. Fix all failures.
5. The docs gate runs an incremental secrets scan in **record-only** mode (wave 1p5pz): secret findings are written to `docs/scan-findings.json` and surfaced as a non-fatal `[secrets]` notice, but they do **not** fail the docs gate or halt the upgrade. The Phase-4 index build's full-tree baseline also records untouched-file findings. Secrets are enforced **only at `wave_close`** (`pending`/`suspected-secret` hard-block; `confirmed-secret` non-blocking + reminded) — classify findings via seed-213 before your next wave close. (Ordinary lint errors still fail the docs gate with a recoverable `failed_phase=docs_gate` lock; resume via `.wavefoundry/bin/upgrade-wavefoundry --resume-after-gate` / `wave_upgrade(phase="resume_after_gate")` — that path is for lint errors, not secrets.)

## Protected Surfaces

Require `framework_edit_allowed` guard approval for broad changes to:
- `docs/prompts/`
- `AGENTS.md`
- Hook configs (`.claude/settings.json`, `.cursor/hooks.json`, `.github/hooks/hooks.json`)

## Git Commits

Operator-owned. Hand off diff + suggested message; do not run `git commit`.

## Version Guard

After unpacking a new zip: verify `docs/prompts/prompt-surface-manifest.json` `framework_revision` matches the new `.wavefoundry/framework/VERSION`. Update manifest if needed.
