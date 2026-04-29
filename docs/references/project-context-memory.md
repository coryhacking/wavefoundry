# Project Context Memory

Owner: Engineering
Status: active
Last verified: 2026-04-28

Durable reusable workflow guidance discovered during waves and promoted from journals.

## Self-Hosting Path Resolution

Wavefoundry is both the framework source repository and a target repository consuming rendered framework surfaces. The canonical script path for self-hosting is `framework/scripts/` directly; `.wavefoundry/framework` is a symlink to `../framework`. When seeds reference `.wavefoundry/framework/scripts/<script>.py`, those paths resolve correctly through the symlink.

Root wrappers (`./docs-lint`, `./docs-gardener`) point to `.wavefoundry/framework/scripts/` via the symlink — this is intentional and correct for self-hosting mode.

## Framework VERSION Semantics

`framework/VERSION` is stamped by `build_pack.py` immediately before writing the distribution archive. The VERSION value is `<date><letter>` (e.g. `2026-04-28a`). Do not manually edit VERSION; it is managed by the build script.

## Seed Protection During Framework Edits

When editing canonical seed prompts under `framework/seeds/`, set `.wavefoundry/guard-overrides.json` `seed_edit_allowed.enabled` to `true` before editing. After the edit, set it back to `false` or remove the file. The pre-edit hook enforces this.

## Lifecycle ID Epoch

The lifecycle ID epoch for Wavefoundry is `2022-04-28T00:00:00Z` (UTC midnight, 4 years before the first packaging date `2026-04-28`). This was chosen because the repository had no git commits at init time. The epoch produces IDs with exactly one leading zero (`0xxxx`), visually distinct from the `00000` baseline wave prefix. See `docs/workflow-config.json` `lifecycle_id_policy` for the full contract.
