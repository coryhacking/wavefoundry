# Agent Body — Upgrade Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-07-31

## Context

You are running **Upgrade Wavefoundry** (seed-160) on the Wavefoundry repository. Self-hosting mode: `.wavefoundry/framework/` is the canonical framework directory.

## Upgrade Contract

1. Inventory/drift-detection subagents run **read-only**.
2. Produce a concise file-level upgrade plan before broad edits to `docs/prompts/`, `AGENTS.md`, or hook configs.
3. Update existing canonical docs in place; do not create parallel files when a topical home already exists.
4. After reconciliation: verify the docs gate — **with MCP**, run **`wf_garden_docs`** (if needed) then **`wf_validate_docs`**; **without MCP**, run `wf docs-gardener && wf docs-lint`. Fix all failures.
5. The docs gate runs an incremental secrets scan in **record-only** mode (wave 1p5pz): secret findings are written to `docs/scan-findings.json` and surfaced as a non-fatal `[secrets]` notice, but they do **not** fail the docs gate or halt the upgrade. The Phase-4 index build's full-tree baseline also records untouched-file findings. Secrets are enforced **only at `wf_close_wave`** (`pending`/`suspected-secret` hard-block; `confirmed-secret` non-blocking + reminded) — classify findings via the security reviewer, seed-213, before your next wave close. (A refused retired-sidecar cleanup retains `failed_phase=review_sidecar_cleanup`: stop the dashboard and every attached host, then re-run the full upgrade. Ordinary lint errors retain a recoverable `failed_phase=docs_gate` lock; resume via `wf upgrade --resume-after-gate` / `wf_upgrade(phase="resume_after_gate")`, which reruns only the docs gate and then establishes or refreshes the historical-memory checkpoint. If it returns memory action-required, continue through `resume_after_memory`. Resume-after-memory, update/rebuild-index, and cleanup all refuse until the matching recovery passes. That path is for docs recovery, not secrets. A cutover-active 1.15 events-only upgrade run (one that removed a retired sidecar or the stale root lock, or upgraded from a version predating 1.15, unknown treated fail-safe as pre-1.15) additionally requires a full restart of every attached MCP/agent host before lifecycle mutation resumes; on such a run the upgrade suppresses its automatic in-process reload (guaranteed only from newly loaded code onward: a pre-1.15 host crossing the boundary may still fire its old unconditional reload, which does not substitute for the full restart) and `wf_reload_mcp` alone is not sufficient. Non-cutover runs keep the normal reload flow.)

## Protected Surfaces

Require `framework_edit_allowed` guard approval for broad changes to:
- `docs/prompts/`
- `AGENTS.md`
- Hook configs (`.claude/settings.json`, `.cursor/hooks.json`, `.github/hooks/hooks.json`)

## Git Commits

Operator-owned. Hand off diff + suggested message; do not run `git commit`.

## Version Guard

After unpacking a new zip: verify `docs/prompts/prompt-surface-manifest.json` `framework_revision` matches the new `.wavefoundry/framework/VERSION`. Update manifest if needed.
