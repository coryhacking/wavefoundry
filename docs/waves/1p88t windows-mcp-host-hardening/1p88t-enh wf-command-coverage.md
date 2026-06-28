# WF command coverage

Change ID: `1p88t-enh wf-command-coverage`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-27
Wave: `1p88t windows-mcp-host-hardening`

## Rationale

Agents still encounter guidance that tells them to run framework scripts directly with raw Python, for example `python3 .wavefoundry/framework/scripts/gen_codebase_map.py`. Native-Windows testing already showed agents can guess the wrong invocation shape when instructions expose raw script paths. Wavefoundry should make `wf` the operator/agent CLI surface for every framework action an agent may be asked to run, leaving raw Python script execution as a development-only fallback.

## Requirements

1. Inventory every agent/operator-facing direct framework-script invocation in AGENTS, docs, prompts, seeds, and distributed reference material. Classify each invocation as covered by an existing `wf` command, requiring a new `wf` command, or allowed development-only/internal guidance.
2. Add `wf` subcommands for the currently known agent-facing framework scripts that are recommended directly from installed/distributed Wavefoundry surfaces:
   - `wf codebase-map` -> `gen_codebase_map.py`
   - `wf render-surfaces` -> `render_platform_surfaces.py`
   - `wf secrets-scan` -> `run_secrets_scan.py`
   - **`prune_framework.py` is intentionally NOT a `wf` subcommand** (operator decision, post-review): it is a manual upgrade-cleanup fallback run directly as `python3 .wavefoundry/framework/scripts/prune_framework.py --old-manifest <path>` because it requires the pre-upgrade MANIFEST that only the operator running the upgrade holds, and its `main() -> None` made the dispatcher's `int()` coercion crash. The dispatcher now also coerces a `None` return to exit 0 defensively.
3. Add any additional `wf` subcommands required by the inventory before rewriting guidance; known candidates include lifecycle ID generation and dashboard fallback commands if those references are agent/operator-facing rather than development-only.
4. Each subcommand forwards arguments verbatim, self-activates through the existing `wf_cli.py` bootstrap, and works through POSIX `.wavefoundry/bin/wf` and native-Windows `.wavefoundry\bin\wf.cmd`.
5. Replace operator/agent-facing docs, prompts, and seeds that instruct direct `python3 .wavefoundry/framework/scripts/*.py` invocation with the corresponding `wf` subcommand.
6. Keep explicit development-only direct Python examples only where the framework test/development context genuinely requires them; label those as development-only and not distribution-pack instructions.
7. Keep Wavefoundry source-host-only scripts such as `run_tests.py` and `build_pack.py` out of the distributed command surface and verify they are not included in framework zip packages.
8. Tests cover the new dispatch table entries and ensure generated docs do not reference missing `wf` subcommands.

## Scope

**Problem statement:** raw Python script references in agent-facing guidance are fragile across Windows/POSIX and invite incorrect invocation guesses.

**In scope:**

- `wf_cli.py` subcommands and help text.
- Renderer/bin shim tests where needed.
- Prompt/seed/docs cleanup for direct script references.
- A checked-in inventory or test fixture that records every direct script reference and its classification.
- Changelog note.

**Out of scope:**

- MCP server launch path; MCP should continue to call `server.py` directly.
- Removing all shebangs or making scripts non-runnable for developers.
- Creating host-native GUI launchers.
- Adding `wf` subcommands for Wavefoundry source-host-only scripts such as `run_tests.py` or `build_pack.py`.

## Acceptance Criteria

- [x] AC-1: a direct-script invocation inventory exists before docs cleanup and classifies every agent/operator-facing `python3 .wavefoundry/framework/scripts/*.py` reference as covered by `wf`, newly requiring `wf`, or allowed development-only/internal guidance.
- [x] AC-2: `wf codebase-map`, `wf render-surfaces`, `wf secrets-scan`, and any additional installed/distributed subcommands required by the inventory dispatch to the intended scripts and forward args. (`prune_framework.py` was removed from the `wf` surface post-review per operator decision — it stays a manual `python3` upgrade-cleanup step; the dispatcher now coerces a `None`-returning `main()` to exit 0 so a future None-returning target cannot crash it. Covered by `test_wf_cli.py` `test_each_subcommand_routes_to_its_module`, `test_prune_framework_is_not_a_subcommand`, `test_none_returning_main_coerces_to_exit_zero`.)
- [x] AC-3: `.wavefoundry/bin/wf --help` and `.wavefoundry\bin\wf.cmd --help` list the new subcommands through the shared dispatcher.
- [x] AC-4: agent/operator-facing docs/prompts/seeds prefer `wf` subcommands over direct `python3 .wavefoundry/framework/scripts/*.py` calls for covered actions. Post-review sweep converted the remaining operator-facing breaches (`docs/RELIABILITY.md`, `docs/PLANS.md`, `CONTRIBUTING.md`, `docs/architecture/graph-index-system.md` "Also available as a CLI").
- [x] AC-5: direct Python references that remain are either shebangs, tests, development-only instructions, design/architecture narration, or internal code comments; a real scan enforces this boundary — `test_wf_cli.py` `NoRawCoveredScriptInvocationInOperatorDocsTests` fails on any runnable `python3 .wavefoundry/framework/scripts/<covered>.py` in operator-facing docs (covered set auto-derived from the dispatch table; `docs/architecture/**`, plans/waves/reports, and CHANGELOG excluded with documented rationale).
- [x] AC-6: `run_tests.py` and `build_pack.py` are documented/classified as Wavefoundry source-host-only and are excluded from framework zip packages; tests or packaging assertions verify that exclusion.
- [x] AC-7: full framework suite and docs-lint pass.

## Tasks

- [x] Inventory direct framework-script invocations and classify each one before command/doc edits.
- [x] Extend `wf_cli.py` dispatch table and help text for the known commands and any inventory-discovered gaps.
- [x] Add/adjust `test_wf_cli.py` coverage.
- [x] Sweep AGENTS, docs/prompts, seeds, and references for direct script instructions; replace with `wf` where covered.
- [x] Update package exclusion rules so source-host-only `build_pack.py` is not shipped; keep/assert the existing `run_tests.py` exclusion.
- [x] Add a shipped-guidance scan for stale raw script invocations.
- [x] Run full suite and docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Inventory | docs-contract-reviewer | — | Classify direct script references and identify required command coverage. |
| CLI | implementer | Inventory | Add subcommands first. |
| Docs sweep | docs-contract-reviewer | CLI | Replace only with commands that exist. |
| Tests | qa-reviewer | CLI, Docs sweep | Dispatcher and guidance scans. |

## Serialization Points

- Docs cleanup must wait for the inventory and new `wf` subcommands so instructions never point at missing commands.

## Direct-call Inventory Scope

Only include scripts that instructions expect an operator or agent to run directly from a terminal when MCP is unavailable, during Wavefoundry source maintenance, or during distribution packaging. Do not include scripts that are only implementation modules, MCP subprocess targets, generated-hook internals, or descriptive references.

### Include In `wf` Coverage

| Script | Direct-use context | Planned `wf` surface |
| --- | --- | --- |
| `setup_wavefoundry.py` | Initial setup, repair, full rebuild instructions | Existing `wf setup` |
| `docs_lint.py` | No-MCP docs validation fallback | Existing `wf docs-lint` |
| `docs_gardener.py` | No-MCP metadata gardening fallback | Existing `wf docs-gardener` |
| `setup_index.py` | No-MCP index update/rebuild fallback | Existing `wf update-indexes`; decide whether docs need a clearer alias such as `wf index` before rewriting |
| `lifecycle_id.py` | No-MCP wave/change/document ID fallback | Existing `wf lifecycle-id` |
| `upgrade_wavefoundry.py` | No-MCP upgrade fallback | Existing `wf upgrade` |
| `dashboard_server.py` | Local dashboard start/open fallback | Existing `wf dashboard`; verify it covers documented root/open/no-open forms before rewriting |
| `render_platform_surfaces.py` | Regenerate host configs/hooks/bin shims and auto-Guru surfaces | New `wf render-surfaces` |
| `run_secrets_scan.py` | Full secrets baseline CLI fallback when MCP unavailable | New `wf secrets-scan` |

### Exclude From `wf` Coverage

| Script/reference | Reason |
| --- | --- |
| `server.py` | MCP host launch target, not an operator CLI; generated configs must keep calling it directly. |
| `prune_framework.py` | **Reclassified post-review (operator decision):** manual upgrade-cleanup fallback run directly (`python3 .wavefoundry/framework/scripts/prune_framework.py --old-manifest <path>`). It needs the pre-upgrade MANIFEST that only the operator running the upgrade holds, and routing it through `wf` added no value while its `main() -> None` crashed the dispatcher's `int()` coercion. Allowlisted in the AC-5 scan. |
| `render_agent_surfaces.py` | Implementation detail of `render_platform_surfaces.py`; use `wf render-surfaces` for direct regeneration. |
| `indexer.py` | Background/index implementation detail; use MCP index tools or `wf update-indexes`/`wf setup`. |
| `dashboard_lib.py` | Library module only. |
| `install_log_lib.py` | Parser/library module only. |
| `run_tests.py` | Wavefoundry source-host verification only; should not be a distributed `wf` command and should not ship in target-repo packages. |
| `build_pack.py` | Wavefoundry source-host packaging/release only; should not be a distributed `wf` command and should not ship inside the package it creates. |
| `build_pack.py` mentions that only describe package internals | Keep or rewrite as source-maintainer docs, but do not turn descriptive implementation references into distributed commands. |
| Historical `docs/waves/**`, `docs/reports/**`, and test fixtures | Evidence/history only; do not drive the shipped command surface. |
| MCP tool-surface recovery strings that should prefer MCP tools | Update recovery guidance where appropriate, but do not create standalone commands for MCP-only internals. |

## Affected Architecture Docs

`N/A` for architecture boundaries. Update operator guidance and prompt surfaces only.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prevents partial command coverage and stale direct-script guidance. |
| AC-2 | required | Adds the command surface. |
| AC-3 | important | Discoverability on both OS families. |
| AC-4 | required | Prevents the observed agent invocation mistakes. |
| AC-5 | important | Keeps the surface from regressing. |
| AC-6 | required | Keeps source-host-only scripts out of the distributed package and command surface. |
| AC-7 | required | Regression safety. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-27 | Planned from native-Windows install feedback and direct script reference scan. | Installed direct-call examples include `gen_codebase_map.py`, `lifecycle_id.py`, dashboard fallback, render surfaces, secrets scan, and prune cleanup. `run_tests.py` and `build_pack.py` are source-host-only exclusions. |
| 2026-06-27 | Implemented distributed `wf` command coverage and docs sweep. | Added `wf codebase-map`, `wf render-surfaces`, `wf secrets-scan`, `wf prune-framework`; kept `run_tests.py`/`build_pack.py` source-host-only; full suite 3510 tests OK; docs-lint OK. |
| 2026-06-27 | Post-review fixes. | `wf prune-framework` crashed on every call (`int(None)` on its `main() -> None`) and was reclassified to a manual `python3 prune_framework.py` step (operator decision); dispatcher hardened to coerce `None`→0. Built the real AC-5 scan (`NoRawCoveredScriptInvocationInOperatorDocsTests`, covered set auto-derived from the dispatch table) and converted the remaining operator-facing raw-script breaches (`RELIABILITY.md`, `PLANS.md`, `CONTRIBUTING.md`, `graph-index-system.md`). Full suite 3521 tests OK. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-27 | Make `wf` the operator/agent CLI surface for covered scripts. | Cross-OS dispatch belongs in one place; agents should not infer Python/script invocation forms. | Keep raw script docs (rejected); route MCP through `wf` (rejected). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| `wf` grows into an unstructured kitchen sink. | Limit to agent/operator-facing scripts; keep development-only scripts direct. |
| Docs sweep removes useful developer examples. | Preserve clearly marked development-only direct Python instructions where appropriate. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
