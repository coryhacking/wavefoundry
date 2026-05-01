# MCP-First Routing for Change Creation, Validation, and Gardening

Change ID: `1297t-feat mcp-change-creation-coverage`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-04-29
Wave: TBD

## Environment note (Wavefoundry self-host)

Post-edit hooks and local verification use **`.wavefoundry/bin/docs-lint`** and **`.wavefoundry/bin/docs-gardener`**. This repository does **not** ship repo-root `./docs-lint` / `./docs-gardener` shims. Where this plan names “wrapper” CLI fallback after MCP, use **`.wavefoundry/bin/...`** here; target repositories may still carry legacy root shims until upgraded.

## Rationale

Three related gaps motivate this change. All three are about replacing direct script invocations in agent instructions with the MCP tools that already (or will, after this change) provide structured equivalents.

**1. The MCP change-creation surface is incomplete.** `lifecycle_id.py` accepts ten change kinds (`bug`, `feat`, `enh`, `change`, `doc`, `debt`, `ref`, `task`, `maint`, `ops`) but the MCP server only exposes four (`wave_new_feature`, `wave_new_bug`, `wave_new_enhancement`, `wave_new_refactor`). An agent asked to scaffold a `doc`, `debt`, `task`, `maint`, `ops`, or generic `change` plan today must drop down to a shell subprocess of `lifecycle_id.py`, which is exactly the workflow the foundation feature was meant to retire.

**2. The seed and prompt instructions still route through `lifecycle_id.py`.** `docs/prompts/plan-feature.md`, `docs/plans/plan-template.md`, and `.wavefoundry/framework/seeds/170-plan-feature.prompt.md` instruct agents to run `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>` directly. The MCP `wave_new_`* tools should be the canonical agent path for change creation in any repository where the server is registered; the script invocation is correct for operators on the CLI but should not be the default agent route.

**3. Validation and gardening instructions still route through shell entrypoints (historically `./docs-lint` / `./docs-gardener`; now `.wavefoundry/bin/docs-lint` / `.wavefoundry/bin/docs-gardener` in this repo) instead of MCP first.** The MCP server already exposes `wave_validate` (wraps `docs_lint.py`) and `wave_garden` (wraps `docs_gardener.py`) as structured tools, but instruction sites across `docs/prompts/`, `docs/prompts/agents/`, `AGENTS.md`, `CLAUDE.md`, and `docs/contributing/build-and-verification.md` may still tell agents to invoke the CLI launchers directly. Output parsing, exit-code handling, and error surfacing all become per-agent responsibilities under the script path; the MCP tools return structured pass/fail with extracted errors. Symmetric reasoning to the change-creation case: the **bin** launchers remain for hooks, CI, and operator CLI, but the agent default should be MCP.

**Wave creation is deliberately excluded from this change.** The lifecycle mutation tools (`wave_create`, `wave_add_change`, etc.) were explicitly deferred from the foundation feature (see [12926-feat wavefoundry-mcp-index](../waves/1293d mcp-server-foundation/12926-feat wavefoundry-mcp-index.md), Requirement 14) and have not been planned. Until that follow-on lands, `lifecycle_id.py --kind wave` remains the canonical path for wave-folder ID generation and seed/prompt references to it must remain intact. Full retirement of script invocation depends on that follow-on. The post-edit hook in `.claude/hooks/post-edit.py` and the Cursor `.cursor/hooks/after-file-edit.py` continue to invoke **`.wavefoundry/bin/docs-lint`** directly (not MCP) because hooks are not MCP clients; only **agent-facing instructions** are rerouted.

## Requirements

1. The MCP server exposes a `wave_new_`* tool for every change kind currently supported by `lifecycle_id.py`: `change`, `doc`, `debt`, `task`, `maintenance`, `operations`. (Kinds `bug`, `feat`, `enh`, `ref` already have tools.) Tool names use the human-readable form (`wave_new_documentation`, `wave_new_tech_debt`, `wave_new_task`, `wave_new_maintenance`, `wave_new_operations`, `wave_new_change`) so they read clearly to agents and operators in tool listings.
2. Each new tool wraps the same logic as the existing four: generate ID via `lifecycle_id.py`, scaffold `docs/plans/<change-id>.md` from `plan-template.md`, return the change ID and file path. Behavior is identical to the existing tools except for the kind argument.
3. The tools are registered via the same `_register_tools()` path in `server.py` so all 10 are listed together in tool discovery and a single test asserts the registration count.
4. Tests in `test_server_tools.py` cover the new tools at parity with existing coverage: each tool generates a valid ID, writes the file, returns the correct path, and uses the template.
5. `AGENTS.md` "MCP Server" section lists all 10 `wave_new_`* tools.
6. `docs/prompts/plan-feature.md` and `docs/prompts/agents/plan-feature.md` are updated to instruct agents to call the MCP `wave_new_<kind>` tool first, with the script invocation listed as a CLI fallback only.
7. `docs/plans/plan-template.md` updates the "generate with..." comment to reference the MCP tool first; the CLI command remains as a parenthetical fallback.
8. `.wavefoundry/framework/seeds/170-plan-feature.prompt.md` and `.wavefoundry/framework/seeds/040-docs-structure-bootstrap.prompt.md` are updated identically. Editing seeds requires `seed_edit_allowed.enabled: true` in `.wavefoundry/guard-overrides.json` for the duration of the edit and reset afterward.
9. The MCP foundation change doc ([12926-feat](../waves/1293d mcp-server-foundation/12926-feat wavefoundry-mcp-index.md)) Requirement 13 currently names only four creation tools; this change does not edit that closed-wave artifact, but the new tools satisfy the broader intent.
10. `lifecycle_id.py` itself is not edited. The script remains the canonical ID source called by the MCP tools and the only available path for wave-folder ID generation until lifecycle mutation tools land.
11. Agent-facing instruction sites that still tell agents to run the docs gate via shell first are updated to instruct calling MCP `wave_validate` and `wave_garden` first, with **`.wavefoundry/bin/docs-lint`** / **`.wavefoundry/bin/docs-gardener`** (or legacy repo-root shims, when present in a target repo) listed as labeled CLI fallbacks. The full inventory: `docs/prompts/implement-wave.md`, `docs/prompts/close-wave.md`, `docs/prompts/upgrade-wavefoundry.md`, `docs/prompts/implement-feature.md`, `docs/prompts/agents/upgrade-wave-context.md`, `docs/prompts/agents/implement-wave.md`, `docs/prompts/agents/close-wave.md`, `docs/prompts/agents/implement-feature.md`, `docs/contributing/build-and-verification.md`, and `AGENTS.md` "What Wavefoundry Owns" / MCP Server sections.
12. `CLAUDE.md` "Docs Gate" section describes that the post-edit hook runs **`.wavefoundry/bin/docs-lint`** (not MCP); this is purely descriptive of what happens automatically and is not an agent instruction.
13. The seed `.wavefoundry/framework/seeds/030-inventory-and-map.prompt.md` and any other seed under `.wavefoundry/framework/seeds/` that names `docs_lint.py` or `docs_gardener.py` as an agent step is updated to instruct MCP-first routing; descriptive references (i.e., naming the script as a project artifact rather than a step to execute) are left intact. Seed edits are gated by `seed_edit_allowed.enabled: true` in `.wavefoundry/guard-overrides.json`.
14. The **Python** implementations `docs_lint.py` and `docs_gardener.py` under `.wavefoundry/framework/scripts/` remain the backends MCP tools delegate to. **`.wavefoundry/bin/`** launchers remain the canonical non-MCP CLI entrypoints in this repository (repo-root `./docs-lint` / `./docs-gardener` shims are optional in other targets and are not required here). This change is about routing in agent-facing instructions and seed text, not removing the backends.

## Scope

**Problem statement:** Agents must shell out to scripts for three workflows that already (or after this change, will) have MCP equivalents: change-doc creation (six of ten kinds missing tools), docs validation (CLI via `.wavefoundry/bin/docs-lint` or legacy `./docs-lint`), and docs gardening (CLI via `.wavefoundry/bin/docs-gardener` or legacy `./docs-gardener`). Instructions across prompts, seeds, and agent docs still route through scripts, undermining the structured-tool-call benefit the MCP foundation feature established for the four creation kinds it did cover.

**In scope:**

- Six new MCP tools (`wave_new_change`, `wave_new_documentation`, `wave_new_tech_debt`, `wave_new_task`, `wave_new_maintenance`, `wave_new_operations`)
- Tests at parity with existing `wave_new_`* coverage
- Documentation updates: `AGENTS.md`, `docs/prompts/plan-feature.md`, `docs/prompts/agents/plan-feature.md`, `docs/plans/plan-template.md`
- Routing of validation/gardening instructions through MCP across the prompt sites listed in Requirement 11
- Seed updates: `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`, `.wavefoundry/framework/seeds/040-docs-structure-bootstrap.prompt.md`, plus any seed under `.wavefoundry/framework/seeds/` that names `docs_lint.py`/`docs_gardener.py` as an agent step (per Requirement 13)

**Out of scope:**

- Any wave lifecycle mutation tooling (`wave_create`, `wave_add_change`, `wave_remove_change`, `wave_prepare`, `wave_pause`, `wave_review`, `wave_close`) — deferred per the foundation feature
- Removing `lifecycle_id.py` references from seeds/prompts that pertain to wave-folder ID generation (`--kind wave`) — depends on lifecycle mutation tools follow-on
- Removing `lifecycle_id.py` itself — it remains the canonical generator called internally by MCP
- Renaming existing tools (`wave_new_feature` etc. stay as-is for backwards compatibility)
- Changing `lifecycle_id.py`'s kind taxonomy
- Modifying the post-edit hook in `.claude/hooks/post-edit.py` or `.cursor/hooks/after-file-edit.py` to call MCP instead of **`.wavefoundry/bin/docs-lint`** directly — hooks are not MCP clients and the cost of making them so (process startup latency, transport boilerplate) outweighs the benefit
- Modifying `wave_validate` or `wave_garden` tool implementations themselves — only their adoption in instruction sites is in scope
- Sync surfaces tool routing: `wave_sync_surfaces` exists but no agent-facing instructions currently tell agents to run `render_platform_surfaces.py`; reviewing or expanding that surface is deferred

## Acceptance Criteria

- AC-1: Six new MCP tools registered (`wave_new_change`, `wave_new_documentation`, `wave_new_tech_debt`, `wave_new_task`, `wave_new_maintenance`, `wave_new_operations`); the `test_all_tools_registered` test count reflects 10 `wave_new_`* tools (plus the 9 existing non-creation tools).
- AC-2: For each new tool: a test asserts (a) the generated change ID has the correct kind suffix, (b) the file is written to `docs/plans/<change-id>.md`, (c) the template content is used, (d) forward-slash paths are returned, mirroring the existing `NewChangeTests` cases.
- AC-3: `python3 .wavefoundry/framework/scripts/run_tests.py` passes with new tests included.
- AC-4: `AGENTS.md` "MCP Server" section lists all 10 `wave_new_`* tools.
- AC-5: `docs/prompts/plan-feature.md`, `docs/prompts/agents/plan-feature.md`, and `docs/plans/plan-template.md` instruct the MCP-first path with script as fallback.
- AC-6: Seed files `170-plan-feature.prompt.md` and `040-docs-structure-bootstrap.prompt.md` route the change-ID step through MCP tools first.
- AC-7: MCP **`wave_validate`** succeeds when MCP is used for the gate; **`.wavefoundry/bin/docs-lint`** passes when verifying via CLI (no MCP).
- AC-8: After the seed edits, `.wavefoundry/guard-overrides.json` is restored to `seed_edit_allowed.enabled: false`.
- AC-9: Server can be cold-loaded via the existing test harness without errors after the new tool registrations.
- AC-10: The eight non-`feat` `lifecycle_id.py` kinds remain reachable via MCP after this change (4 pre-existing + 6 new = 10 covered, matching the script's full taxonomy).
- AC-11: Every prompt and agent prompt listed in Requirement 11 instructs MCP `wave_validate` first when the agent needs to run docs validation, with **`.wavefoundry/bin/docs-lint`** (or legacy `./docs-lint` when present) shown as a labeled CLI fallback.
- AC-12: Every prompt and agent prompt listed in Requirement 11 instructs MCP `wave_garden` first when the agent needs to run docs gardening, with **`.wavefoundry/bin/docs-gardener`** (or legacy `./docs-gardener` when present) shown as a labeled CLI fallback.
- AC-13: `docs/contributing/build-and-verification.md` retains the **`.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`** shell snippets as authoritative *operator/CI* guidance, alongside an MCP-first agent guidance section that names the tools.
- AC-14: A grep over `docs/prompts/`, `docs/prompts/agents/`, and `AGENTS.md` shows no stale instruction that tells agents to use **only** repo-root `./docs-lint` or `./docs-gardener` as the primary path where `bin/` is the contract (fallback labeling is OK). Descriptive mentions ("the docs-lint validator checks…") are not affected.
- AC-15: Hook-driven invocations of **`.wavefoundry/bin/docs-lint`** (post-edit hook in `.claude/hooks/`, `.cursor/hooks/`) remain subprocess-based and verified still passing via `python3 .wavefoundry/framework/scripts/run_tests.py`.

## Tasks

- Read existing `wave_new_feature/_bug/_enhancement/_refactor` registration in `server.py` to mirror the pattern.
- Add six new tool registrations in `_register_tools()` with identical scaffolding logic.
- Add six new test cases under `NewChangeTests` in `test_server_tools.py` (one per kind).
- Update `test_all_tools_registered` count.
- Run `python3 .wavefoundry/framework/scripts/run_tests.py` and confirm all tests pass.
- Update `AGENTS.md` "MCP Server" available tools list.
- Update `docs/prompts/plan-feature.md` and `docs/prompts/agents/plan-feature.md` step ordering: MCP first, script second.
- Update `docs/plans/plan-template.md` `Change ID:` annotation.
- Set `.wavefoundry/guard-overrides.json` `seed_edit_allowed.enabled: true`.
- Update `.wavefoundry/framework/seeds/170-plan-feature.prompt.md` to mention MCP `wave_new_<kind>` tools as primary and script as fallback for the change-ID step. Preserve `--kind wave` script invocation language for wave-folder ID generation.
- Update `.wavefoundry/framework/seeds/040-docs-structure-bootstrap.prompt.md` similarly.
- Inventory all instruction sites that still prefer shell over MCP for the docs gate (including `.wavefoundry/bin/docs-lint` / legacy `./docs-lint`) via grep and confirm against the Requirement 11 list before editing.
- Update each prompt and agent prompt in the Requirement 11 inventory to MCP-first routing with labeled CLI fallback. Order: top-level prompts before `agents/` mirrors so wording can be reused.
- Update `AGENTS.md` "MCP Server" tools list (already touched for change-creation tools) to also note that `wave_validate`/`wave_garden` are the agent-default for docs validation/gardening.
- Update `docs/contributing/build-and-verification.md` to add an MCP-first section while preserving the **`.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`** shell snippets as operator/CI guidance.
- Update any seed under `.wavefoundry/framework/seeds/` (besides those already named) that names `docs_lint.py`/`docs_gardener.py` as an agent step (typically `030-inventory-and-map.prompt.md`, possibly others — confirmed via grep). Use the same MCP-first / fallback pattern. Performed inside the same `seed_edit_allowed` window as the change-creation seed updates.
- Restore `.wavefoundry/guard-overrides.json` `seed_edit_allowed.enabled: false`.
- Run MCP **`wave_validate`** (preferred) or **`.wavefoundry/bin/docs-lint`** (CLI only) and confirm pass.
- Run grep verification per AC-14 and record output.
- Update this change doc Progress Log with task completion timestamps and evidence.

## Agent Execution Graph


| Workstream    | Owner       | Depends On   | Notes                                                  |
| ------------- | ----------- | ------------ | ------------------------------------------------------ |
| server-tools  | Engineering | —            | Add 6 tool registrations to `server.py`                |
| server-tests  | Engineering | server-tools | Mirror existing `NewChangeTests` for the six new kinds |
| docs-update   | Engineering | server-tools | Can land in parallel with tests                        |
| seed-update   | Engineering | server-tools | Requires `seed_edit_allowed` guard toggle              |
| guard-restore | Engineering | seed-update  | Reset guard to disabled state before commit            |


## Serialization Points

- `server.py` `_register_tools()` is a single-author surface during this change; cannot be edited concurrently with other server work.
- `.wavefoundry/guard-overrides.json` toggle is single-author for the entire seed edit window.
- `docs/prompts/plan-feature.md` and the seed `170-plan-feature.prompt.md` carry parallel content; both must be updated in lockstep so seed and rendered surface stay aligned.

## Affected Architecture Docs

N/A — this change adds tools to an existing module along an established pattern, does not introduce new module boundaries, does not change data/control flow paths beyond what Path 6 already documents in `docs/architecture/data-and-control-flow.md` (which describes "Creation tools" generically, not a per-kind list).

## AC Priority

(Populated at Prepare wave.)


| AC    | Priority                                             | Rationale |
| ----- | ---------------------------------------------------- | --------- |
| AC-1  | required / important / nice-to-have / not-this-scope |           |
| AC-2  | required / important / nice-to-have / not-this-scope |           |
| AC-3  | required / important / nice-to-have / not-this-scope |           |
| AC-4  | required / important / nice-to-have / not-this-scope |           |
| AC-5  | required / important / nice-to-have / not-this-scope |           |
| AC-6  | required / important / nice-to-have / not-this-scope |           |
| AC-7  | required / important / nice-to-have / not-this-scope |           |
| AC-8  | required / important / nice-to-have / not-this-scope |           |
| AC-9  | required / important / nice-to-have / not-this-scope |           |
| AC-10 | required / important / nice-to-have / not-this-scope |           |


## Progress Log


| Date       | Update         | Evidence                 |
| ---------- | -------------- | ------------------------ |
| 2026-04-29 | Plan authored. | This conversation thread |


## Decision Log


| Date       | Decision                                                                                                                                                                                            | Reason                                                                                                                                                                               | Alternatives                                                                                                              |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| 2026-04-29 | Tool naming uses human-readable forms (`wave_new_documentation`, `wave_new_tech_debt`, `wave_new_maintenance`, `wave_new_operations`) instead of script kind tokens (`doc`, `debt`, `maint`, `ops`) | Existing `wave_new_feature`/`wave_new_enhancement` already use the long form; consistency matters more than terseness for tool discovery in MCP listings.                            | Use script tokens (`wave_new_doc`, `wave_new_debt`); rejected because it breaks naming consistency with the existing four |
| 2026-04-29 | Wave-creation MCP tooling deliberately excluded                                                                                                                                                     | Was already deferred from the foundation feature; mixing the two would inflate scope and conflict with the planned lifecycle mutation feature.                                       | Bundle wave creation into this change (rejected: explicit scope discipline)                                               |
| 2026-04-29 | `lifecycle_id.py` kept and unchanged                                                                                                                                                                | It is the canonical generator wrapped by every `wave_new_`* tool and is also still the only path for wave-folder ID generation. Removing or relocating it would break wave creation. | Inline lifecycle ID computation into `server.py` (rejected: duplicates logic, breaks CLI use case)                        |
| 2026-04-29 | Seed edits gated by `seed_edit_allowed.enabled: true` per `CLAUDE.md` and `AGENTS.md` cleanup rules                                                                                                 | Standard guardrail for any framework seed change.                                                                                                                                    | Skip the guard (rejected: the guard exists for a reason)                                                                  |


## Risks


| Risk                                                                                                                                              | Mitigation                                                                                                                                                       |
| ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tool names diverge from `lifecycle_id.py` kind tokens (`wave_new_documentation` vs kind `doc`), creating mental-mapping cost.                     | Tool docstring includes the kind token explicitly; tests assert correct kind is passed to the underlying script; `AGENTS.md` documents the mapping.              |
| Seed edits during the guard-enabled window are easy to forget to revert, leaving the repository with `seed_edit_allowed.enabled: true` committed. | Add the guard-restore step as the final task before docs-lint; verify in the change doc Progress Log evidence.                                                   |
| Updating prompts to "MCP first" creates divergent guidance if MCP server is unavailable in some agent environment.                                | Prompts retain the script command as a clearly-labeled fallback ("If the Wavefoundry MCP server is not registered, run …"); the script remains shipped.          |
| Seed and rendered prompt surface drift if one is updated and the other isn't.                                                                     | The plan explicitly lists both for synchronized update; `docs-lint` runs after the change to surface mismatches via the existing prompt-surface manifest checks. |
| Tests for the six new tools become brittle if they hardcode template content rather than the template path.                                       | Mirror the existing `test_uses_template_if_exists` pattern which checks for template-derived content rather than literal strings.                                |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.