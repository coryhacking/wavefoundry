# Extension Tool Aliases, Hidden Names and Replacements

Change ID: `1z8oy-enh extension-tool-aliases`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-28
Wave: 1z8oz extension-tool-aliases

## Rationale

A downstream fork with its own record vocabulary (RFC section 4.3) wants the MCP tools named in that vocabulary. It also wants some names to mean something different: in the fork, `wf_close_wave` closes one work item, while Wavefoundry's container close is served under another name. Tools keep their canonical Wavefoundry names internally.

The extension declaration in `mcp_tool_extensions.py` (waves `1yv9l`, `1yyoj`) already lets a fork add tools and override core tools with compatible schemas. It has no way to:

- serve a tool under a second name;
- stop advertising a name;
- reuse a core name with an incompatible handler while keeping the core behaviour reachable.

A plain second registration is not enough. The wrappers `_wrap_lifecycle_mutation_lock`, `_wrap_upgrade_publication_guard`, `_wrap_first_party_tool_costs` and `_wrap_setup_notice` each loop over the served table. They rebind `tool.fn` with a closure that captures the table key, and look up the lock set, the guard set, `_COST_EXEMPT_TOOLS` and the extractor maps by that key. An alias registered as its own entry would therefore run without the lifecycle lock or the publication guard.

In FastMCP 1.28.1, `Tool` is a pydantic model and `Tool.run` calls `self.fn`. A scratch probe showed that `model_copy(update={"name": alias})` of a wrapped `Tool` shares the wrapped `fn`, lists under the alias, and runs the closure keyed on the canonical name.

## Requirements

1. **Declaration.** The fork-edited declaration in `mcp_tool_extensions.py` gains three constants, all empty as shipped:
   - `EXTENSION_TOOL_ALIASES`: `{alias: canonical_name}`.
   - `EXTENSION_HIDDEN_TOOLS`: canonical names that are not advertised.
   - `EXTENSION_REPLACEMENTS`: `{module: {core_name: {"alias_for_core": name, "tier": optional "read" or "write"}}}`. This covers a core name that the module reuses with an incompatible handler.

   `declared()` returns true when any of the three is non-empty, as it already does for modules, prefixes, tiers and overrides.
2. **Validation, split by where the facts live.**
   - **In `declaration_problems`** (stdlib only, called by the roster), refuse the following:
     - an alias that collides with `TOOL_TIERS`, `EXTENSION_TOOL_TIERS`, `roster.RUNNER_TOOLS`, another alias or an `alias_for_core`;
     - an alias without a prefix in `CORE_TOOL_PREFIXES + EXTENSION_TOOL_PREFIXES`;
     - an alias whose target is not a served name (a core name or an `EXTENSION_TOOL_TIERS` key, in both the roster and the server callers), is a runner tool, is another alias, or is a replaced core name;
     - a hidden name with no alias, a hidden name that is a runner tool, or a hidden name that is a replaced core name;
     - a replacement whose module is not in `EXTENSION_MODULES`, whose core name is not served, is a runner tool or is also in `EXTENSION_OVERRIDES`, or whose `alias_for_core` fails the alias rules.

     The runner check uses `roster.RUNNER_TOOLS`, not the table. On first startup `wf_reload_mcp` is not yet in the table, and FastMCP's `add_tool` silently returns an existing entry with the same name.
   - **In `_install_extension_tools`**, following the existing reserved-name check there: refuse an alias or `alias_for_core` that collides with `_reserved_tool_name_collections()`, which includes the retired names in `render_platform_surfaces._RENAMED_MCP_TOOLS`.
3. **Aliases inherit every protection by construction.** After `apply_middleware` has wrapped the served table, each alias is installed as `model_copy(update={"name": alias})` of the canonical name's wrapped `Tool`. It keeps the same schema and annotations, and takes the canonical tier. The lock, the publication guard, the cost wrapper, the setup notice and the extractors therefore run keyed on the canonical name. Busy responses, cost records and context-efficiency attribution carry the canonical name, which is the internal identity.
4. **Hidden names.** A hidden canonical name is removed from the served table after its aliases are installed. It is then neither advertised nor callable over MCP. Nothing outside tests calls a tool by name through FastMCP, and internal code that calls the `*_response` functions directly is unaffected.
5. **Replacements.**
   1. In `_install_extension_tools`, before the core `Tool` is removed, capture it (already argument-normalized) for each replacement.
   2. The replacing handler must keep `additionalProperties: false`, which preserves the `unknown_arguments` envelope. The parameter-shape clauses of `_override_compatibility_problem` do not apply to it.
   3. The replacing handler is served under the core name and wrapped by the main middleware pass. The lock, publication guard and cost wrapper apply to it by name. When the replacement declares a tier, that tier replaces the core name's tier in the roster.
   4. **Every decision that differs between the replacing handler and the core behaviour is made when the wrapper is built, never by name at call time.** Both passes key on `core_name`, so a name-keyed check at call time would give both the same answer. `_install_extension_tools` records a module-level set of replaced names, which is cleared in the fail-closed `except`. Only the main pass reads it, through keyword arguments on the wrappers (for example `_wrap_first_party_tool_costs(mcp, get_handler, *, extractor_free=...)`). The per-pass differences are:
      - **Extractors:** off for the replacing handler, because the argument-parsing extractors (`_ARTIFACT_EXTRACTORS`, `_COST_FOCUS_EXTRACTORS`, `_STATE_SOURCE_EXTRACTORS`) parse the core schema. The replacing handler records only its cost debit.
      - **Hint rewrite:** skipped for the replacing handler, whose own hints name the fork's tool.
      - **Guard for a declared `"write"` replacement:** when `core_name` is not already in `publication_control.registered_publication_tool_names()`, the replacing handler is guarded with `publication_checkpoint_reason`. The choice between the checkpoint check and the block check is made at wrap time. A core name that is already registered keeps its existing guard, which includes the `memory_recovery` exemption for `memory_backfill` and `memory_validate`.
   5. After the main pass, still inside the fail-closed block, a scratch surface whose table holds only `{core_name: captured}` is wrapped. The scratch pass uses a chain with the same labels, the stock name-keyed sets, extractors on, and the hint rewrite applied. The resulting wrapped `Tool` is installed as `model_copy(update={"name": alias_for_core})`. The core behaviour under `alias_for_core` therefore has exactly the stock lock, guard, cost wrapper, setup notice and extractors keyed on the core name, plus the rewrite. Its own hints (for example the lock-busy `recovery_tools`) therefore name `alias_for_core`.
   6. `wf_server_info` lists each replacement: core name, module, `alias_for_core` and tier.
6. **Response hints use the served names.** The rewrite map is:
   - `{canonical: first-declared alias}` for names that are not replaced;
   - `{core_name: alias_for_core}` for replaced names.

   When the map is non-empty, a rewrite wrapper is appended at apply time. It is not added to the static `MIDDLEWARE` tuple, which a test pins, and it runs before the alias copies are made so they inherit it.
   - It rewrites `next_tools`, `usage`, `diagnostics[].recovery_tools` and `diagnostics[].recovery_usage`: exact match for list items, token-bounded inside strings. It returns a copy and does not mutate the result.
   - It is sync-only, and it skips runner tools and coroutine tools. It is not applied to replacing-handler entries (Requirement 5.4).
   - It does not reach names inside `data` (the `wf_help` catalog, `next_step`), `diagnostics[].message` prose, docstrings, tool descriptions, FastMCP argument-validation errors, or runner-tool responses. This is a documented limit: canonical names in prose always mean the core behaviour.
   - `wf_server_info` `extensions` publishes the full map (canonical name to served name, replacements included), so an agent can translate prose deterministically.
   - With no declaration, nothing is appended and core responses are byte-identical.
7. **Roster and permissions.** `mcp_tool_roster.all_tool_tiers()` returns core plus extension tools plus aliases (at their canonical tier) plus `alias_for_core` names, minus hidden names, with replacement tiers applied. `allow_rules()` and `build_registry` follow it. The tests on a booted server, `RealSurfaceRegistryTests` and `RosterRuntimeParityTests`, compare against `all_tool_tiers()` instead of `roster.TOOL_TIERS`. `RosterRegistrationParityTests` stays on `roster.TOOL_TIERS` as the core-source parity gate: it is a census of the `@mcp.tool` decorators in the source (an AST scan), and cannot see declarations. `test_agents_available_tools_census_matches_registration` is unchanged, because it already compares a repository's own `AGENTS.md` with live registration, which is correct for a fork.
8. **Reload and fail-closed startup.** Alias, hide and replacement installation runs inside the existing fail-closed block of `register_mcp_surface`. Any failure strips to runner tools and re-raises, so a partial install never serves a hidden name or an unguarded alias. Reload (`server.perform_mcp_reload` through `_refresh_mcp_tool_surface`) already removes every served name except `wf_reload_mcp`, then re-runs `register_mcp_surface`; `server.py` needs no change.
9. **Provenance.** `wf_server_info` `extensions` reports aliases, hidden names, replacements and the rewrite map. For the stock surface these are empty.
10. **Documentation.**
    - `docs/specs/mcp-tool-surface.md` extension section: the new constants, the inheritance rule, the replacement rule, the rewrite map and its limit.
    - `docs/architecture/threat-model.md`: aliases and `alias_for_core` keep the lock and publication guard. A replacement inherits its core name's tier, lock and guard unless it declares a tier. A replacement is trusted-distribution code.
    - `docs/architecture/current-state.md` and `docs/architecture/layering-rules.md`: the install order. Extension tools are installed before the prefix contract and `MIDDLEWARE`; the rewrite, aliases, core-behaviour aliases and hiding run after.
    - `docs/contributing/build-and-verification.md`: roster parity against `all_tool_tiers()`; the rewrite wrapper is appended only when declared.
    - CHANGELOG: an Added line.

## Scope

**Problem statement:** a fork cannot serve Wavefoundry tools under its own vocabulary without losing name-keyed protections, and cannot reuse a core name while keeping the core behaviour reachable.

**In scope:**

- The declaration constants and their validation, alias installation, hidden names, replacements, the hint rewrite, roster and permission handling, provenance, the tests and the docs above.

**Out of scope:**

- Generating tool names from vocabulary tier names (the RFC rejects this too).
- Rewriting names in prose, `data` payloads, docstrings and tool descriptions.
- Aliases for resources, prompts or runner tools.
- Rendered prompt surfaces and AGENTS.md naming the fork's aliases. Forks own their rendered surfaces.
- The optional parent tier (RFC section 5), which is on hold.

## Acceptance Criteria

- [ ] AC-1: each invalid declaration named in Requirement 2 is refused, with a message naming the entry, and startup strips to runner tools. The cases include:
  - an alias named `wf_reload_mcp` on first startup;
  - an alias whose target is a replaced core name;
  - hiding a replaced core name;
  - an aliases-only declaration with no module, which is validated and served rather than ignored.
- [ ] AC-2: a plain alias carries the canonical protections:
  - an alias of `wf_close_wave` returns the lock-busy response while the lifecycle lock is held;
  - an alias of a write-tier tool is blocked by the publication guard during an upgrade checkpoint;
  - an alias of a cost-exempt tool records no cost;
  - `table[alias].fn is table[canonical].fn`.

  Each test calls through the alias name over the served table.
- [ ] AC-3: a hidden canonical name is absent from `list_tools` and not callable over MCP, while its alias works.
- [ ] AC-4: a replacement with an incompatible schema behaves as follows:
  - It is served under the core name, with the lifecycle lock applied.
  - It records only a cost debit, with no extractor credit.
  - Its own `next_tools` are not rewritten.
  - The core behaviour answers under `alias_for_core` with the lock and guard (the AC-2 checks), and with extractor credit on an extractor-bearing tool (`wf_review_event`).
  - The replacing handler's `__wf_middleware__` markers equal that core name's stock markers. The markers of the core behaviour under `alias_for_core` equal the stock markers plus `rewrite`.
  - Its lock-busy response names `alias_for_core` in `recovery_tools` and `next_tools`.
  - A replacement declaring `"write"` on a read-tier core name is guarded and allowlisted at write tier. The core behaviour under `alias_for_core` stays unguarded.
  - A declared `"write"` replacement of `memory_validate` leaves the core behaviour's `memory_recovery` exemption intact.
  - `wf_server_info` lists the replacement.
- [ ] AC-5: rewriting uses the served names:
  - With an alias declared, `next_tools`, `usage`, `recovery_tools` and `recovery_usage` in a real handler response name the alias.
  - A core response naming a replaced core name is rewritten to `alias_for_core`.
  - A name that contains the canonical name as a substring (`wf_close_wave_x`) is not rewritten.
  - With the shipped empty declaration, the surface golden (`tests/test_tool_surface_golden.py`), `HandlerDigestTests` and the `MIDDLEWARE` order pin are unchanged, and every response except `wf_server_info` is byte-identical.
  - `StockSurfaceTests` asserts that the new `wf_server_info` fields are empty.
- [ ] AC-6: after `wf_reload_mcp`, aliases, hidden names and replacements are rebuilt from the declaration, and a declaration made invalid before reload fails closed.
- [ ] AC-7: the rendered permission allowlist includes each alias and `alias_for_core` at its tier and omits hidden names. Parity is tested at two levels:
  - `RosterRegistrationParityTests` passes unchanged, as the core-source gate.
  - `RealSurfaceRegistryTests` and `RosterRuntimeParityTests` pass both for the shipped empty declaration and for fixture declarations: one with an alias, a hidden name and a replacement, and one that is aliases-only. The fixture cases run on a booted server or through the `ExtensionServingTests` path.

  `DeclarationValidationTests` saves and restores all seven declaration constants.
- [ ] AC-8: the change's own suites pass, and the documents it edits validate.

## Tasks

- [ ] Declaration constants, `declared()`, and validation in `declaration_problems` and `_install_extension_tools`.
- [ ] Alias installation after `apply_middleware` inside the fail-closed block; hidden-name removal.
- [ ] Replacements: capture before removal; keep `additionalProperties: false`; per-pass `extractors` flag in the cost wrapper; scratch-surface wrap of the captured core `Tool`; declared tier and guard membership.
- [ ] Hint-rewrite wrapper, appended only when the map is non-empty.
- [ ] `all_tool_tiers()`, `allow_rules()`, `build_registry`; parity tests switched to `all_tool_tiers()`.
- [ ] `wf_server_info` provenance and `StockSurfaceTests`.
- [ ] Tests for AC-1 to AC-7 using scratch extension module fixtures.
- [ ] Spec, threat model, current-state, build-and-verification, CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Declaration and install | implementer | readiness | Validation first |
| Replacements, hints, roster, provenance | implementer | Declaration and install | |
| Review | combined reviewer | both | Code, QA, architecture, docs, security |

## Serialization Points

- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`, `.wavefoundry/framework/scripts/mcp_tool_roster.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/wf_server/mcp_tool_registry.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/specs/mcp-tool-surface.md`, `docs/architecture/threat-model.md`, `docs/architecture/current-state.md`, `docs/architecture/layering-rules.md`, `docs/contributing/build-and-verification.md`
- `CHANGELOG.md`

## Affected Architecture Docs

- `docs/architecture/threat-model.md`: the protections kept by aliases and replacements, and the trusted-distribution risk of replacements.
- `docs/architecture/current-state.md`: the install order.

The spec `docs/specs/mcp-tool-surface.md` owns the declaration contract.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Fail-closed declaration |
| AC-2 | required | Protections are the safety property |
| AC-3 | required | Hide behaviour |
| AC-4 | required | Replacement keeps the core behaviour reachable and protected |
| AC-5 | important | Agent steering; core unchanged |
| AC-6 | required | Reload parity |
| AC-7 | required | Permission and roster correctness |
| AC-8 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-28 | Planned from the downstream RFC section 4.3. Code facts verified: every wrapper keys on the served table key, overrides already exist, hints are literals at about 333 `next_tools` sites | investigation of `mcp_tool_extensions.py`, `server_impl.register_mcp_surface`, FastMCP 1.28.1 `ToolManager` |
| 2026-09-28 | Readiness review folded in: capture and separately wrap the core `Tool` for replacements; per-pass extractor flag; replacement-aware rewrite map; `declared()` covers the new constants; checks split by location; `wf_reload_mcp` alias case; optional replacement tier; parity tests on `all_tool_tiers()`; docs census | readiness review B1 to B4, N1 to N10; scratch probe of `model_copy` on a wrapped `Tool` |
| 2026-09-28 | Confirmation round folded in: rewrite skip and writer-guard membership decided per pass (a declared-write replacement no longer changes the core behaviour's guard or drops the memory-recovery exemption); core-source parity test kept on `TOOL_TIERS`; marker expectations; extension-tool alias targets; `layering-rules.md` | confirmation review B5, B6, N-a to N-f; scratch probe of `apply_middleware` on a stub surface |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-28 | Declare aliases in the extension declaration, not the vocabulary profile | Overrides, prefixes and tiers already live there with validation, provenance and reload; the operator chose this | The vocabulary profile, as the RFC proposes |
| 2026-09-28 | Aliases are `model_copy` renames of the wrapped canonical `Tool` | Every protection applies by construction; a probe confirmed the copy shares the wrapped closure | Resolve alias to canonical inside every wrapper and extractor |
| 2026-09-28 | Wrap the captured core `Tool` in a separate scratch pass | Overrides are swapped in before `apply_middleware`, so the core `Tool` is unwrapped when removed; a separate pass keys every wrapper on the core name with extractors on | Serve the unwrapped capture (no lock or guard) |
| 2026-09-28 | Keep replacements in this change (operator decision: "keep together") | The RFC's motivating case is a replaced name; the fixes above make the path safe | Split replacements into a follow-up change, as the red-team seat suggested |
| 2026-09-28 | Decide every difference between the two passes at wrap time, from a main-pass-only set | Both passes key on the core name, so any call-time check by name leaks between the replacing handler and the core behaviour | Serve the core behaviour under its alias with every set resolving the alias to the core name |
| 2026-09-28 | Rewrite only the four structured hint fields, and publish the map | The rewrite is exact there; prose stays canonical and the published map lets an agent translate it | Rewrite prose as well |

## Risks

| Risk | Mitigation |
| --- | --- |
| The core behaviour under `alias_for_core` is served without protections | Scratch-pass wrap; AC-4 marker equality with a stock surface |
| A replacement handler trips extractors that parse the core schema | Per-pass extractor flag; AC-4 |
| A core hint for a replaced name steers agents to the fork's same-named tool | Replacement-aware rewrite map; AC-5 |
| A mutating replacement of a read-tier core name runs at read tier without the guard | Optional declared tier with guard membership; threat-model note; AC-4 |
| An aliases-only declaration is silently ignored | `declared()` covers the new constants; AC-1, AC-7 |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
