# Upgrade Wave Framework

Owner: Engineering
Status: active
Last verified: 2026-04-28

Shortcut: **`Upgrade wave framework`** | Legacy: **`Upgrade wave context`**

## Purpose

Upgrade the Wave Framework operating surface in a target repository. Reconciles the rendered local docs, prompt surface, platform hook/config surfaces, and `AGENTS.md` with the current canonical framework source.

## Upgrade Steps

**Step 0 (optional zip adoption):** If a `wavefoundry-framework-<date><letter>.zip` is at the repository root, the upgrade seed unpacks the lexicographically greatest zip, stages it under `.wavefoundry/framework/`, runs `render_platform_surfaces.py`, and continues full reconciliation. Archives with other names or outside the root are ignored.

**Full reconciliation:**
1. Inventory current state (seed-030 in targeted mode)
2. Drift-detect against canonical framework (read-only subagents for inventory)
3. Produce a file-level upgrade plan before broad edits
4. Reconcile prompt surface, platform surfaces, `AGENTS.md`, manifests
5. Run `./docs-gardener && ./docs-lint` to verify

## Verification Checklist

See `docs/contributing/build-and-verification.md` **Wave framework pack upgrade verification** for the ordered operator commands.

1. Framework tests: `python3 .wavefoundry/framework/scripts/run_tests.py`
2. Docs gate: `./docs-gardener && ./docs-lint`
3. Review diff of pack changes, hooks, `docs/prompts/`, manifests
4. Commit (operator-owned)

## Protected Surfaces

Inventory/drift-detection subagents run read-only. Broad edits to `docs/prompts/`, `AGENTS.md`, or hook configs require `framework_edit_allowed` guard approval and a concise file-level plan before execution.

## Git Commits

**Operator-owned.** Agent hands off diff + suggested message. Operator commits.

## Aliases

- **Upgrade wave context** — legacy; identical behavior
