# 080 - Mechanical Enforcement

Intent:

- Define the docs gate, wrappers, and automation expectations needed to keep the Wave Framework layer healthy over time.

Tasks:

1. Ensure target repositories get **`.wavefoundry/bin/docs-lint`** and **`.wavefoundry/bin/docs-gardener`** launchers (via install / `render_platform_surfaces`) that invoke the canonical scripts under `.wavefoundry/framework/scripts/`. **Agent-facing instructions** should prefer MCP **`wave_validate`**, **`wave_garden`**, and **`wave_audit`** over shelling out to those launchers when the Wavefoundry MCP server is available.
2. Ensure hooks and CI entrypoints resolve **`.wavefoundry/bin/docs-lint`** / **`.wavefoundry/bin/docs-gardener`** from the repository root (see `050` hook contracts).
3. Define the minimum docs gate and where it should run.
4. Ensure generated files are trackable in git and not accidentally hidden by broad ignore rules.
5. Keep generated prompts, persona wrappers, and key framework files versioned when they are part of the checked-in project contract in the repository.
6. Ensure generated artifact indexes and prompt manifests stay synchronized with the generated outputs.
7. Ensure validation covers wave artifacts, journals, persona docs, prompt-surface docs, and wrapper references.

Required semantics:

- wrapper contract
- docs gate command
- tracking expectations for generated framework files
- minimal CI hook guidance
- generated-artifact registration expectations
- validation scope for wave-context-specific artifacts

Root wrapper contract:

- `.wavefoundry/bin/docs-lint` should forward to `.wavefoundry/framework/scripts/docs_lint.py`
- `.wavefoundry/bin/docs-gardener` should forward to `.wavefoundry/framework/scripts/docs_gardener.py`
- wrappers should pass `PROJECT_ROOT` as the repository root
- wrappers should use project-root-relative execution so seeded repos remain portable

Minimum docs gate:

- **Agents (MCP attached):** **`wave_garden`** when metadata needs refresh, then **`wave_validate`** (or **`wave_audit`** for a combined readout); follow each tool’s parameter contract.
- **Operators / CI / hooks / no MCP:** **`.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`** (pass `--date <YYYY-MM-DD>` only when overriding today's date; use `--paths <doc>` or `--all-docs` to target specific files instead of git-changed docs)

Validation targets to cover:

- required prompt docs
- required readiness prompt and supporting agent prompt body when the seeded surface exposes wave operator commands
- prompt-surface manifest presence and basic integrity
- generated waves root
- generated journals root
- required metadata in docs
- `factor_review_policy` anchors when factor-review agents are applicable
- `persona_review_policy` anchors when user/operator personas exist
- wave-execution anchors for readiness-before-implementation and rerun-before-closure when the project uses non-trivial waves
- wrapper path consistency
- stale legacy framework references when a repo has already migrated

Guardrails:

- Do not assume every project uses the same CI platform.
- Keep the enforcement contract portable.
- Prefer deterministic checks over vague guidance so upgrades can repair drift consistently.
