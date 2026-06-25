# Project Context Memory

Owner: Engineering
Status: active
Last verified: 2026-06-25

Durable reusable workflow guidance discovered during waves and promoted from journals.

## Auto-Memory Categories

The auto-memory system recognizes four file types: `user`, `feedback`, `project`, `reference`. Two content categories that are particularly easy to miss and worth capturing explicitly:

**Architectural decisions** (`project` type) — why an approach was chosen, not just what was done. Capture when the reasoning is non-obvious and not recoverable from git history or the change doc alone. Lead with the decision, then **Why:** and **How to apply:** lines.

**Validated approaches** (`feedback` type) — positive confirmations that a non-obvious choice worked well. The memory system skews toward corrections if only failures are saved; confirmations of working patterns carry equal weight. Record from both failure and success.

**Wave close is the primary capture moment.** The close-wave retrospective step ("what was non-obvious in this wave that a future session should know?") is the intended trigger for surfacing both categories.

## Self-Hosting Path Resolution

Wavefoundry is both the framework source repository and a target repository consuming rendered framework surfaces. The framework content lives at `.wavefoundry/framework/`. Seeds reference `.wavefoundry/framework/scripts/<script>.py` and `.wavefoundry/framework/seeds/` directly.

**Agents** should prefer MCP **`wave_validate`** and **`wave_garden`** over shelling to the `wf` dispatcher. The canonical cross-OS **CLI** dispatcher (`wf docs-lint`, `wf docs-gardener`) routes through `wf_cli.py` to `.wavefoundry/framework/scripts/` for hooks, CI, and hosts without MCP — intentional for self-hosting mode. `build_pack.py` is self-locating: it derives the framework root from its own file location, so packaging reads from `.wavefoundry/framework/` and produces a zip with `framework/` entries for operators.

## MCP audit landing (`wave_audit`)

Use MCP **`wave_audit`** as the default read-only **combined** check after uncertainty or a mutating tool: it returns **`data.wave`**, **`data.validation`** (same information as **`wave_validate`** / docs-lint), **`data.index`** (semantic readiness summary), and **`data.ready`** (`true` only when a wave is present **active or planned**, lint passes, and **`semantic_ready`** is true). It does **not** write docs or trigger reindexes. When a sub-check fails, follow **`next_tools`** (`wave_validate`, `wave_index_build`, or `wave_current`) instead of guessing. When **`ready`** is **`true`**, **`next_tools`** is still **`["wave_current"]`** — a default navigation hint, not a recovery step. Individual tools remain available for targeted debugging.

## Framework VERSION Semantics

`.wavefoundry/framework/VERSION` is stamped by `build_pack.py` immediately before writing the distribution archive. The VERSION value is `<date><letter>` (e.g. `2026-04-28a`). Do not manually edit VERSION; it is managed by the build script.

## Seed Protection During Framework Edits

When editing canonical seed prompts under `.wavefoundry/framework/seeds/`, set `.wavefoundry/guard-overrides.json` `seed_edit_allowed.enabled` to `true` before editing. After the edit, set it back to `false` or remove the file. The pre-edit hook enforces this.

## Lifecycle ID Epoch

The lifecycle ID epoch for Wavefoundry is `2022-04-28T00:00:00Z` (UTC midnight, 4 years before the first packaging date `2026-04-28`). This was chosen because the repository had no git commits at init time. The epoch produces IDs with exactly one leading zero (`0xxxx`), visually distinct from the `00000` baseline wave prefix. See `docs/workflow-config.json` `lifecycle_id_policy` for the full contract.
