# Project Context Memory

Owner: Engineering
Status: active
Last verified: 2026-09-02

Durable reusable workflow guidance discovered during waves and promoted from journals.

## Auto-Memory Categories

The auto-memory system recognizes four file types: `user`, `feedback`, `project`, `reference`. Two content categories that are particularly easy to miss and worth capturing explicitly:

**Architectural decisions** (`project` type) — why an approach was chosen, not just what was done. Capture when the reasoning is non-obvious and not recoverable from git history or the change doc alone. Lead with the decision, then **Why:** and **How to apply:** lines.

**Validated approaches** (`feedback` type) — positive confirmations that a non-obvious choice worked well. The memory system skews toward corrections if only failures are saved; confirmations of working patterns carry equal weight. Record from both failure and success.

**Wave close is the primary capture moment.** The close-wave retrospective step ("what was non-obvious in this wave that a future session should know?") is the intended trigger for surfacing both categories.

## Self-Hosting Path Resolution

Wavefoundry is both the framework source repository and a target repository consuming rendered framework surfaces. The framework content lives at `.wavefoundry/framework/`. Seeds reference `.wavefoundry/framework/scripts/<script>.py` and `.wavefoundry/framework/seeds/` directly.

**Agents** should prefer MCP **`wf_validate_docs`** and **`wf_garden_docs`** over shelling to the `wf` dispatcher. The canonical cross-OS **CLI** dispatcher (`wf docs-lint`, `wf docs-gardener`) routes through `wf_cli.py` to `.wavefoundry/framework/scripts/` for hooks, CI, and hosts without MCP — intentional for self-hosting mode. `build_pack.py` is self-locating: it derives the framework root from its own file location, so packaging reads from `.wavefoundry/framework/` and produces a zip with `framework/` entries for operators.

## MCP audit landing (`wf_audit`)

Use MCP **`wf_audit`** as the default read-only **combined** check after uncertainty or a mutating tool: it returns **`data.wave`**, **`data.validation`** (same information as **`wf_validate_docs`** / docs-lint), **`data.index`** (a bounded metadata readiness snapshot, wave 1t59p: `metadata_ready` with `freshness: "unknown"` — it never cold-loads native storage or hashes the working tree; call **`index_health`** when verified freshness matters), and **`data.ready`** (`true` only when a wave is present **active or planned**, lint passes, and **`metadata_ready`** is true). It does **not** write docs or trigger reindexes. When a sub-check fails, follow **`next_tools`** (`wf_validate_docs`, `index_build`, or `wf_current_wave`) instead of guessing. When **`ready`** is **`true`**, **`next_tools`** is still **`["wf_current_wave"]`** — a default navigation hint, not a recovery step. Individual tools remain available for targeted debugging.

## Framework VERSION Semantics

`.wavefoundry/framework/VERSION` is stamped by `build_pack.py` immediately before writing the distribution archive. The VERSION value is `<date><letter>` (e.g. `2026-04-28a`). Do not manually edit VERSION; it is managed by the build script.

## Seed Protection During Framework Edits

When editing canonical seed prompts under `.wavefoundry/framework/seeds/`, set `.wavefoundry/guard-overrides.json` `seed_edit_allowed.enabled` to `true` before editing. After the edit, set it back to `false` or remove the file. The pre-edit hook enforces this.

## Lifecycle ID Epoch

The lifecycle ID epoch for Wavefoundry is `2022-04-28T00:00:00Z` (UTC midnight, 4 years before the first packaging date `2026-04-28`). This was chosen because the repository had no git commits at init time. The epoch produces IDs with exactly one leading zero (`0xxxx`), visually distinct from the `00000` baseline wave prefix. See `docs/workflow-config.json` `lifecycle_id_policy` for the full contract.

## MCP Tool Naming Namespaces (wave 1t3gt)

The first-party MCP tool surface uses subsystem prefixes: `wf_` (framework/server operations and the wave lifecycle, verb-first names like `wf_close_wave` / `wf_open_gate` / `wf_start_dashboard`), `memory_` (agent memory records), `index_` (semantic/graph index), plus the pre-existing `docs_` / `code_` / `seed_`. The `wave_` prefix is retired with no aliases. `wave_review` and `wave_implement` still exist as workflow-config KEYS (they are config schema, not tool names) and must never be renamed in configs, fixtures, or migration tables. `MCP_TOOL_PREFIXES` in `server_impl.py` is the enforced invariant.

## Context Efficiency Stage Model (wave 1t3gt)

Stage accounting writes exactly three values: `plan` (create/prepare and adopted pre-wave exploration), `implement`, and `review` (review/close). The vocabulary is enforced in `context_efficiency.set_focus`; there is no legacy mapping (pre-rename history was cleaned once, by hand). The wave.md checkpoint publishes at mutating lifecycle boundaries; close seals and compacts.

## Fresh-Install Gate Coherence (wave 1viyu)

Three rules that came out of the 2026-08-17 fresh-install field report and its delivery review. (1) Anything the docs gate requires on a fresh install ships as data under `.wavefoundry/framework/install/` and is applied by code at setup Step 0 (absent-only), never as a seed prose step; the seven `workflow-config.json` sections were lost exactly that way in the 1p35d install split. (2) Every `docs/**` file the renderer materializes (lifecycle prompt baselines, scaffolds, pointer-form carriers) must satisfy `check_metadata` on first lint, so it carries `Owner` / `Status` / `Last verified: {{generated_at}}` and every baseline family stamps the date on write; a fixture that claims a "Phase-1-complete" tree must be built by the real producers (Step 0 provisioners plus `render_agent_surfaces`) and judged by the real validator, or it cannot see this class. (3) Install-log rows are never renumbered (retire by removal, insert by decimal extension); seed-012 mirrors the template's numbered rows and `test_install_log_lib.FreshInstallContractParityTests` holds the parity. Typed memory records `1vnka`, `1vn0v`, `1vn8p`, `1vlnj`, `1vkk1` carry the detail.


## Canonical Suite Scheduling and True Counts (wave 1tmtx)

Three durable facts from the 2026-08-27 test-suite-performance wave. (1) The canonical runner's alphabetical file order is the MEASURED schedule winner: a counterbalanced A-T-T-A comparison against timing-guided longest-first, on a byte-identical digest-bound manifest and unchanged source, measured alphabetical faster (means 130.5 s vs 136.8 s) because starting all heavy files together saturates the host; do not re-propose longest-first without a new measurement through `run_tests.py --schedule-control`. (2) Suite totals printed before this wave carried +5 contamination (the per-file count parse took the FIRST "Ran N tests" match, which a mock main() print satisfied); post-wave totals anchor to unittest's own final summary, so historical counts do not line up with current ones (true pre-wave base 7,494). (3) The `test_server_tools*` shard family (core/infra retains the original basename; retrieval; lifecycle) shares fixtures through non-discovered `server_tools_support.py`; new MCP tool tests go in the shard matching their domain, and the split is regenerable from the pre-split source by the wave's archived `shard_split.py` with preservation proven by `verify_shards.py`.


## Retrieval-Receipt Attribution and Production Identity (wave 1wybs)

Three durable facts from the 2026-09-02 review-churn-follow-ups wave, all found by delivery review rather than by planning.

(1) **Any edit to a `retrieval_eval.PRODUCTION_RETRIEVAL_MODULES` member owes a before/after receipt pair**, because production identity is whole-module: `_production_identity` hashes each module's whole bytes, so a lint-parse or install-audit edit to `server_impl.py`, which cannot reach a retrieval tool, still moves the digest and makes the wave the one that "changes production retrieval bytes" under the standing-gate policy. Check the module list before assuming a wave owes no receipt.

(2) **A `cross_generation` comparison attributes corpus drift to the change.** `_quality_comparison` is zero-tolerance (`cur + 1e-12 < base`) over holdout aggregate and per-class metrics, so documents added or changed between the two generations move holdout metrics with no retrieval edit at all; this wave's after-receipt returned `fail` on five `code_ask` regressions of at most 0.055 nDCG@10 across 37 generations. The proof pattern that settles it: reverse-patch the wave's own diff onto a scratch copy of the production modules and re-hash with `_production_identity`; equality with the before-receipt's digest bounds the wave's whole production change byte-exactly, and a call-site census plus an AST reachability closure from `code_ask`, `code_search`, `docs_search`, and `code_lexical` then shows whether any changed symbol is reachable. A drift-free same-generation pair is not available today: `run_evaluation`'s `production_scripts_dir` is identity-only (it hashes that directory but runs the imported modules), so the evaluator cannot measure pre-change bytes on the current generation.

(3) **`wf_prepare_wave(mode='ready')` gardens the canonical copy of a shipped/canonical doc pair but not its shipped twin**, which breaks `test_shipped_templates_are_byte_identical_to_canonical` on the next full suite (here `docs/references/install-log-format.md` was re-stamped and `.wavefoundry/framework/install/install-log-format.md` was not). After any gardening pass, re-sync every shipped/canonical pair before the last suite run, and keep the full suite genuinely last because any edit under `.wavefoundry/framework/` invalidates the close-time test receipt.
