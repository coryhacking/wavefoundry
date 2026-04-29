# 090 - Doc Gardening Harness

Intent:

- Define the behavior of the gardener and lint scripts that seed repositories use to keep docs, prompts, and generated artifacts synchronized.

Tasks:

1. Create or update the root wrappers in the target project's repository.
2. Explain how the canonical scripts should be used from the shared pack.
3. Ensure gardener output can refresh metadata, write reports, and surface drift candidates.
4. Ensure linting can validate key docs metadata and key prompt-surface files.

Required semantics:

- metadata refresh behavior
- report generation behavior
- validation scope
- failure signaling expectations

Guardrails:

- Keep the scripts generic and portable.
- Prefer safe updates and explicit reporting over hidden mutation.
