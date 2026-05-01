# Migrate Existing Wave Project To Wavefoundry Prompt

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Purpose

Explicit migration prompt for existing target repositories that already contain the legacy vendored Wave Framework layout:

```text
agent-workflows/wave-context-framework/
```

The migration moves the target repository toward the Wavefoundry target layout while preserving project-local operating context.

## Invocation Modes

This prompt may be invoked in either mode:

- **Native Wavefoundry mode:** an agent in the Wavefoundry source repository reads `framework/seeds/250-migrate-existing-wave-project.prompt.md` before migrating a target repository.
- **Post-unpack handoff mode:** an old-layout target repository first runs `Migrate to Wavefoundry` from `agent-workflows/wave-context-framework/240-migrate-to-wavefoundry.prompt.md`; that bridge stages a `wavefoundry-*.zip` under `.wavefoundry/framework/`, then reads this file from `.wavefoundry/framework/seeds/250-migrate-existing-wave-project.prompt.md`.

In post-unpack handoff mode, this staged file is the canonical migration instruction for the package that was just unpacked. Follow this file for compatibility checks, activation, validation, and reporting while still obeying the target repository's local `AGENTS.md` safety rules.

## Trigger Phrases

- `Migrate to Wavefoundry`
- `Upgrade to Wavefoundry`
- `Migrate wave framework to Wavefoundry`
- Natural language asking to move a project from `agent-workflows/wave-context-framework` to the Wavefoundry layout

## Target Layout

For target repositories, the preferred Wavefoundry-managed layout is:

```text
.wavefoundry/
  config.json
  framework/
    VERSION
    seeds/
    scripts/
  index.sqlite        # optional, when local indexing is enabled

docs/
  prompts/
  agents/
  waves/
  plans/

AGENTS.md
```

Do not install the canonical framework at top-level `framework/` inside arbitrary target repositories. That path belongs to the Wavefoundry source repository and may collide with product code in other projects.

## Migration Rules

- This is an explicit migration, not a silent side effect of package upgrade.
- Preserve local `docs/`, `AGENTS.md`, waves, plans, journals, personas, specs, architecture docs, reports, and project-specific customizations.
- Treat `agent-workflows/wave-context-framework/` as the old vendored framework source.
- Treat `.wavefoundry/framework/` as the new vendored framework source/cache for target repositories.
- Treat rendered local prompt and agent surfaces under `docs/` as target-owned outputs.
- Do not delete the old `agent-workflows/wave-context-framework/` tree until validation passes and the operator has reviewed the result.
- Never overwrite project-local customizations without reporting a diff or conflict.
- In post-unpack handoff mode, assume `.wavefoundry/framework/` already contains the staged Wavefoundry package. Do not unpack the package again unless the operator asks or the staged tree is incomplete.
- Do not activate `.wavefoundry/framework/` by rewriting manifests, wrappers, or hooks until the compatibility gate below passes.

## Preflight

1. Confirm the target repository root.
2. Check whether `agent-workflows/wave-context-framework/` exists.
3. Check whether `.wavefoundry/framework/` already exists.
4. Read:
   - `AGENTS.md`
   - `docs/prompts/prompt-surface-manifest.json`, when present
   - `docs/workflow-config.json`, when present
   - optional legacy repo-root `docs-lint` / `docs-gardener` scripts, **`.wavefoundry/bin/docs-lint`** / **`.wavefoundry/bin/docs-gardener`**, and `package-wave-framework`, when present
5. Inventory local generated and project-owned surfaces:
   - `docs/prompts/`
   - `docs/agents/`
   - `docs/agents/session-handoff.md`
   - `docs/agents/journals/`
   - `docs/waves/`
   - `docs/plans/`
6. Run the target repository's current docs gate when available before changing migration-sensitive files — **prefer MCP `wave_garden` then `wave_validate`** when the Wavefoundry server is attached; otherwise **`.wavefoundry/bin/docs-lint`** (and **`.wavefoundry/bin/docs-gardener`** when metadata refresh is part of the repo's documented gate).
7. Record whether this is native Wavefoundry mode or post-unpack handoff mode.

## Migration Steps

1. Create `.wavefoundry/` if it does not exist.
2. Create or update `.wavefoundry/config.json` with:

```json
{
  "framework": {
    "source": ".wavefoundry/framework",
    "layout": "wavefoundry-target",
    "self_hosting": false
  },
  "index": {
    "enabled": false,
    "path": ".wavefoundry/index.sqlite"
  }
}
```

3. Ensure the new canonical framework source is staged at `.wavefoundry/framework/`.
   - In native Wavefoundry mode, copy or stage the selected Wavefoundry framework package there.
   - In post-unpack handoff mode, verify the bridge already staged it there.
4. Run the compatibility gate below before activation.
5. If the compatibility gate passes, update `docs/prompts/prompt-surface-manifest.json` when present:
   - `seed_framework_source` should point to `.wavefoundry/framework`
   - `framework_revision` should match `.wavefoundry/framework/VERSION`
   - generated artifact paths should remain project-local, usually under `docs/`
6. If the compatibility gate passes, update `docs/workflow-config.json` when present so any framework source pointer uses `.wavefoundry/framework`.
7. If the compatibility gate passes, ensure docs gate launchers when present:
   - **`.wavefoundry/bin/docs-lint`** should invoke `.wavefoundry/framework/scripts/docs_lint.py`
   - **`.wavefoundry/bin/docs-gardener`** should invoke `.wavefoundry/framework/scripts/docs_gardener.py`
   - Retire or repoint legacy **repo-root** `docs-lint` / `docs-gardener` files if they still target old layout paths
   - `package-wave-framework` should normally be removed or replaced with target-appropriate guidance, because packaging canonical framework source belongs in Wavefoundry, not ordinary target repositories
8. If the compatibility gate passes, update platform hook/config surfaces that reference old framework script paths.
9. If the compatibility gate passes, re-render generated surfaces using the migrated renderer path.
10. Leave `agent-workflows/wave-context-framework/` in place as a temporary migration backup unless the operator explicitly approves removal after validation.

## Compatibility Gate

Before changing existing wrappers, manifests, workflow config, or platform hooks from `agent-workflows/wave-context-framework/` to `.wavefoundry/framework/`, verify that the staged Wavefoundry package supports target repositories using `.wavefoundry/framework/`.

Minimum checks:

- `.wavefoundry/framework/VERSION` exists.
- `.wavefoundry/framework/seeds/` exists.
- `.wavefoundry/framework/scripts/` exists.
- A target-compatible validation entrypoint exists or is documented.
- A target-compatible renderer exists or is documented.
- The validation and rendering paths do not assume they are running inside the Wavefoundry source repository's top-level `framework/` layout.
- The package documents how generated local surfaces under `docs/` are refreshed from `.wavefoundry/framework/`.

If any check fails, stop after staging `.wavefoundry/framework/`. Leave `agent-workflows/wave-context-framework/` active, do not rewrite manifests/wrappers/hooks, and report exactly what target-compatible Wavefoundry tooling is missing.

If all checks pass, continue with activation steps 5-9 above.

## Post-Upgrade Checklist

After staging, and again after activation if activation occurs:

1. Run framework script tests from the migrated target when they are vendored:

```bash
python3 -B .wavefoundry/framework/scripts/run_tests.py
```

2. Run project docs validation (**agents with MCP:** **`wave_garden`** then **`wave_validate`**; **CLI / CI:**):

```bash
.wavefoundry/bin/docs-gardener
.wavefoundry/bin/docs-lint
```

3. Search for stale old-layout references that are not historical records:

```bash
rg -n "agent-workflows/wave-context-framework|wave-context-framework-|package-wave-framework" AGENTS.md docs .wavefoundry
```

4. Confirm `docs/prompts/prompt-surface-manifest.json` and `docs/workflow-config.json` point at `.wavefoundry/framework`.
5. Confirm **`.wavefoundry/bin/`** launchers (and any legacy repo-root wrappers) and platform hooks invoke `.wavefoundry/framework/scripts/...` when activation occurred. If activation was deferred, confirm they still point at the old active layout.
6. Confirm active wave, plan, handoff, journal, and persona files still exist and were not regenerated destructively.
7. Record a migration note in `docs/reports/` or the active wave record. The note should include invocation mode, selected package or source path, staged revision, compatibility-gate result, activation decision, validation result, and old-layout removal decision.
8. Ask the operator before deleting `agent-workflows/wave-context-framework/`.

## Removal Of Old Layout

Only remove `agent-workflows/wave-context-framework/` after all are true:

- migrated validation passes
- stale live references have been reconciled
- project-local customizations are preserved or intentionally resolved
- the operator has approved removal

Historical references in closed waves, changelogs, release notes, and migration records may keep the old path. Do not rewrite history just to remove old-layout strings.

## Completion Criteria

- Target repository has `.wavefoundry/framework/`.
- Target repository keeps readable local operating surfaces under `docs/`.
- Manifest and workflow config point at `.wavefoundry/framework` if activation occurred.
- If activation was deferred, the old layout remains active and the missing Wavefoundry compatibility requirements are documented.
- Validation passes or failures are documented with next steps.
- Old layout is either retained as a reviewed backup or removed after explicit operator approval.
