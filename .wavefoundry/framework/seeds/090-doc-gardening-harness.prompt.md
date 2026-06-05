# 090 - Doc Gardening Harness

Intent:

- Define the behavior of the gardener and lint scripts that seed repositories use to keep docs, prompts, and generated artifacts synchronized.

Tasks:

1. Create or update the root wrappers in the target project's repository.
2. Explain how the canonical scripts should be used from the shared pack.
3. Ensure gardener output can refresh metadata, write reports, and surface drift candidates.
4. Ensure linting can validate key docs metadata and key prompt-surface files.
5. Document the split: **agents** with Wavefoundry MCP should prefer **`wave_garden`** / **`wave_validate`** / **`wave_audit`**; **hooks and CI** invoke **`.wavefoundry/bin/docs-gardener`** and **`.wavefoundry/bin/docs-lint`** because they cannot call MCP.

Required semantics:

- metadata refresh behavior
- report generation behavior
- validation scope
- failure signaling expectations
- MCP vs bin entrypoints (per `seed-050` / `seed-080`)

Guardrails:

- Keep the scripts generic and portable.
- Prefer safe updates and explicit reporting over hidden mutation.

Operator reference:

- Operators reviewing what `docs-lint` deliberately does NOT flag (e.g., transient cache directories like `__pycache__`, `.pytest_cache`, `.mypy_cache`) should consult **`.wavefoundry/framework/docs/lint-exclusions.md`**. The doc ships in the framework pack (vendored on every install / upgrade per wave `1p3b9` / `1p3b5`) and enumerates each excluded pattern with its generated-by tool and rationale. Single source of truth for security audit; the constant lives at `wave_lint_lib/core_validators.py:LINT_EXCLUDED_TRANSIENT_DIRS`.
