# Declarative Tool Registry And Explicit Wrapper Chain

Change ID: `1y0be-ref tool-registry-and-wrapper-chain`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-17
Wave: `1y0h1 tool-registry-dispatch`

## Rationale

**Brief.** Goal: give the MCP server an enumerable runtime registry of tool specifications and one explicit, ordered middleware chain, without moving a single handler body or changing the public surface. Audience: framework maintainers. Approach: a flat sibling module holding `ToolSpec` and a post-registration pass that builds the registry by introspecting FastMCP's own tool table and cross-referencing `mcp_tool_roster.TOOL_TIERS`, leaving all existing `@mcp.tool` sites untouched; the three post-registration wrappers become one applied chain. Constraints: golden tool surface identical; hot-reload safe; the roster check stays warning-only at runtime. Success: the registry lists every tool with its tier, the chain order is inspectable and tested, and `server_impl.py` behaves identically.

Verification established the shape of today's code. `register_mcp_surface` spans lines 31007 to 35275 of `server_impl.py` (31058 to roughly 35329 as of 2026-09-17, after one insertion block earlier in the file) and holds the implementation-owned decorated handlers as closures that call `_ensure_no_extra_args` and delegate to module-level `*_response` functions. The implementation-owned set excludes runner survivors; derive it from actual registration and the roster, not textual decorator occurrences. The wrappers `_wrap_first_party_tool_costs`, `_wrap_lifecycle_mutation_lock`, and `_wrap_upgrade_publication_guard` are applied in that order at lines 35266 to 35268 (35320 to 35322 as of 2026-09-17), so cost is innermost and the guard is outermost, and a test already proves the guard never waits on the lock — this order and the test are untouched by all four commits. The roster parity check at lines 35240 to 35261 (35286 to 35315 as of 2026-09-17) is warning-only by a recorded decision that drift must never deny the whole server; `mcp_tool_roster.py` itself is untouched. Hot reload clears `_script_cache` and purges a named list of sibling modules before re-importing `server_impl`, so a new module is reload-safe when it is on that list. The RFC and kickoff propose a `server/` package; this change keeps flat sibling modules to preserve that reload model and the pack's tree-walk packaging.

Re-verified 2026-09-17, one new finding: `1y3og setup-local-reconciliation` added `setup_readiness.py`, statically imported at the top of both `server.py` and `server_impl.py`, and `runtime_advisory.py` (from the later `1y6hg` wave), statically imported only in `server.py`. Neither is in the module purge list, neither is loaded via `_load_script`, and a plain top-level `import` does not re-execute an already-cached module on `importlib.reload(server_impl)` — so both are stale across `wf_reload_mcp` today, the same gap already open for `repo_root`, `subprocess_util`, and `venv_bootstrap`. Upstream worked around the symptom rather than the gap: `_record_runner_identity` (`server.py:111`) now explicitly re-stamps three `setup_readiness`-owned identity attributes onto the freshly-reloaded `server_impl` module after every reload, rather than making `setup_readiness.py` itself reload-safe. This does not change this change's design — `mcp_tool_registry.py` is stateless by Requirement 4 below, so it belongs on the purge list outright, no re-stamp trick needed — but it widens the case for the deferred reload-staleness follow-up in the wave watchpoints from three modules to five.

## Requirements

1. A new module `.wavefoundry/framework/scripts/mcp_tool_registry.py` defines `ToolSpec` (name, permission tier, annotations, the registered callable, and the source module name) and a `ToolRegistry` with `register(spec)`, `tools()` sorted by name, and `get(name)`.
2. A function `build_registry(mcp) -> ToolRegistry` runs once at the end of `register_mcp_surface`, after the existing decorator-based registration, and derives one `ToolSpec` per implementation-owned entry in FastMCP's tool table (the same `mcp._tool_manager._tools` attribute the golden-snapshot test in `1xzsl-enh tool-surface-golden-snapshot` reads), taking the tier from `mcp_tool_roster.TOOL_TIERS` and the annotations and callable from the table entry. A registered tool with no roster tier, or a roster tier (outside `RUNNER_TOOLS`) with no registered tool, is recorded as a parity defect on the registry rather than raising. None of the existing `@mcp.tool` sites change: no edit to handler bodies, names, parameters, docstrings, decorators, or annotations. Runner boundary: initial `build_server` registers survivors after the implementation surface, while reload retains survivor entries. `build_registry` must explicitly exclude `RUNNER_TOOLS` on both paths rather than assume they are absent from the FastMCP table. Parity tests cover both an initial table without survivors and a reload table containing them. A tool registered directly in `server.py` must be declared in `RUNNER_TOOLS`; full-runner parity in `1xzsl` detects an undeclared extra tool. Reject no server startup solely because of a parity defect.
3. The three post-registration wrappers become a single ordered tuple `MIDDLEWARE` applied by one `apply_middleware(mcp, registry)` call, composing cost innermost, lifecycle lock middle, upgrade-publication guard outermost. Each applied wrapper records its name on the callable in an inspectable `__wf_middleware__` tuple. `_ensure_no_extra_args` remains the first statement of each handler and is not part of the chain.
4. The registry is rebuilt on every `register_mcp_surface` call and holds no handler instance: each spec's callable resolves `get_handler()` per invocation exactly as today. `mcp_tool_registry` is added to the module purge list at the top of `server_impl.py`, and the reload test asserts the registry is fresh after `wf_reload_mcp`.
5. The runtime roster check stays warning-only, but it now compares the registry against `mcp_tool_roster.TOOL_TIERS` instead of the decorated set, and the test suite gains a registry-based parity test beside the existing AST census. The AST census is retained in this wave and in `1y0bf`: decorated closures remain in the composition root even when response functions move.
6. The golden tool-surface fixture from `1xzsl-enh tool-surface-golden-snapshot` is unchanged, and the wrapper-order test from that change passes against the new chain without modification.
7. No alias, namespace transform, or public-name mapping is introduced. No tool is added, renamed, or removed. `wf_help` and `wf_server_info` responses are unchanged.
8. The change touches `register_mcp_surface` and the wrapper application only; no `*_response` function moves.

## Scope

**Problem statement:** There is no enumerable list of tools at runtime, so parity is checked by parsing source, and cross-cutting behavior is applied by three ad hoc passes whose order is documented only in a comment.

**In scope:**

- The registry module, the introspection-based `build_registry` pass, the middleware tuple and application, purge-list entry, and tests.

**Out of scope:**

- Moving handler bodies or `*_response` functions (`1y0h2 handler-module-split`).
- A `server/` package or any change to how sibling modules are loaded and packaged.
- Aliases, deprecations, or a public-name projection.
- Any edit to the existing `@mcp.tool` registration sites, including a decorator-factory conversion (rejected; see Decision Log).
- Fixing the reload staleness of `repo_root`, `subprocess_util`, and `venv_bootstrap`, which are outside the purge list today; recorded as a wave watchpoint.

## Acceptance Criteria

- [ ] AC-1: The golden tool-surface fixture is unchanged, and a test compares an AST-derived digest of every actual `@mcp.tool` handler definition in `register_mcp_surface` (decorator, signature, docstring, body) against a digest captured before this change, with identical name sets and every corresponding digest equal.
- [ ] AC-2: `registry.tools()` returns specs whose names exactly equal `set(TOOL_TIERS) - RUNNER_TOOLS` and whose tiers equal the corresponding `TOOL_TIERS` values, and a test that registers one extra tool on a stub `mcp` (absent from the roster) and removes one roster entry sees both defects reported by the registry parity test.
- [ ] AC-3: The wrapper-order test from `1xzsl` passes unchanged, and a new test reads `__wf_middleware__` on a lifecycle tool and finds the tuple in the order cost, lock, guard.
- [ ] AC-4: After `wf_reload_mcp` the registry reflects a tool description edit made on disk, and no spec holds a reference to the pre-reload module.
- [ ] AC-5: The existing guard-is-outermost test, roster census test, and the whole `WaveMcpReloadTests` class pass unchanged.
- [ ] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Write `mcp_tool_registry.py` with `ToolSpec`, `ToolRegistry`, `build_registry`, `MIDDLEWARE`, and `apply_middleware`, plus unit tests against a stub `mcp` with a hand-built tool table.
- [ ] Call `build_registry` at the end of `register_mcp_surface` before the middleware pass, and run the golden test to confirm the surface is unchanged.
- [ ] Replace the three wrapper calls with `apply_middleware` and add the `__wf_middleware__` marker.
- [ ] Point the runtime roster warning at the registry and add the registry-based parity test.
- [ ] Add the purge-list entry and extend the reload test for registry freshness.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.

## Agent Execution Graph


| Workstream     | Owner       | Depends On   | Notes |
| -------------- | ----------- | ------------ | ----- |
| registry       | implementer | `1y0do` golden | module and unit tests |
| build          | implementer | registry     | `build_registry` call site in `register_mcp_surface` |
| middleware     | implementer | registry     | chain and marker, parallel with build |
| guards         | qa          | build, middleware | parity, reload, golden |


## Serialization Points

- `.wavefoundry/framework/scripts/mcp_tool_registry.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

`docs/architecture/current-state.md` and `docs/architecture/layering-rules.md` describe the registry as the runtime source of tool specifications and the middleware tuple as the only place cross-cutting behavior is applied. A decision record under `docs/architecture/decisions/` records flat sibling modules over a `server/` package, with the reload and packaging reasoning, and defers aliases.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The refactor is defined by an unchanged public surface |
| AC-2 | required  | Enumerability is the deliverable |
| AC-3 | required  | Order becomes an inspectable invariant |
| AC-4 | required  | Reload safety was the constraint that shaped the server split originally |
| AC-5 | required  | Existing guards must survive untouched |
| AC-6 | required  | Standard change-local verification |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-14 | Change planned and admitted to `1y0h1 tool-registry-dispatch` | this document |
| 2026-09-16 | Operator resolved the open registry-design decision in favor of FastMCP introspection; requirements, ACs, tasks, and risks rewritten accordingly; readiness to be re-recorded | Decision Log entry dated 2026-09-16 |
| 2026-09-16 | Prepare council re-run on the rewritten doc. Repairs applied: AC-1 restated as an AST-digest test instead of a diff-review instruction (both seats); Requirement 2 gains the `RUNNER_TOOLS` timing invariant (red-team). Refuted with an anchor: the red-team claim that no module purge list exists; the `sys.modules` eviction set at the top of `server_impl.py` (the block naming `review_evidence`, `review_policy`, `lifecycle_lock`, `publication_control`, `context_efficiency`, `public_contract`, `gardener_metadata`) is the list Requirement 4 refers to. Cross-document follow-up recorded in the wave watchpoints for `1y0h2` | council seat outputs 2026-09-16; `server_impl.py` module-eviction block |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-14 | Flat sibling module, not a `server/` package | Hot reload purges named sibling modules and `_load_script` caches flat files; `build_pack.py` tree-walks the scripts directory; both work unchanged with a flat module | RFC `server/` package: cleaner namespace, but reload and packaging semantics for a package are unproven here and would need their own change |
| 2026-09-14 | Roster check stays warning-only at runtime | Recorded decision in the code: drift must never deny the whole server; enforcement belongs in tests, which now compare the registry | Kickoff's fail-fast at startup: stricter, and reverses a deliberate availability choice |
| 2026-09-14 | No aliases or namespace transform | Every seed, prompt, and host allowlist references canonical names; an alias layer would fragment the agent-facing contract for no current consumer | RFC `aliases` and `namespace_transform`: general capability, speculative today |
| 2026-09-17 | Flat sibling modules stay unreviewed as a permanent choice; no stated revisit trigger | Archetype Council (Marcus Aurelius, 2026-09-17): this decision is sound today but names no condition under which it should be revisited, even though `server_impl.py` keeps growing independently of this plan | Revisit trigger recorded as guidance, not a requirement: if flat MCP-surface-adjacent sibling modules under `.wavefoundry/framework/scripts/` exceed roughly 15-20, or two of them develop a real import dependency on each other, reopen the `server/` package question rather than adding a 21st flat module by default |
| 2026-09-16 | DECIDED by the operator: build the registry by introspecting FastMCP's own `_tool_manager._tools` after existing decorator-based registration; the 90-site decorator-factory conversion is rejected. Requirement 2, Scope, AC-1, AC-2, Tasks, the execution graph, and Risks were rewritten to match on the same date | Operator decision recorded 2026-09-16 on the reviewers' finding below. The only benefit the conversion offered, an explicit per-site hook for future aliases, is a capability this change already defers; the introspection pass reaches the same enumerability with no handler-site diff and no per-site tier or annotation transcription. Original reviewer reasoning: Red-team review (2026-09-17, `improvement-review` + `simplicity`/`first-principles` stances) and Archetype Council (Feynman, independently, same session) both converged on the same finding: FastMCP already builds an enumerable tool table (the golden-snapshot test in `1xzsl` already reads `mcp._tool_manager._tools` directly), and `mcp_tool_roster.TOOL_TIERS` already carries tier data — so a post-registration pass that reads both and cross-references them satisfies Requirement 1 with zero edits to the 90 sites, zero risk of a copy-paste tier/annotation error, and no batch-and-verify task list. Requirement 3 (the explicit middleware chain) is untouched by this question either way — it only replaces the 3 wrapper calls at the end of `register_mcp_surface`. Reviewers left the decision to the operator on 2026-09-17; the operator took it on 2026-09-16 | Rejected: keep the 90-site decorator-factory conversion as originally designed: gives every site an explicit registration point future aliasing could hang off of, at the cost of a larger mechanical diff and the residual risk a golden-fixture-only safety net doesn't fully eliminate (e.g., an `_ensure_no_extra_args` ordering mistake at one of 90 sites is only caught by inherited test coverage, not a requirement this change adds) |
| 2026-09-17 | Confirmed value against Waveforge's real fork, not just theory | `register_mcp_surface`, `_ensure_no_extra_args`, `_load_script`, and `_read_workflow_config` are name-identical (verified by AST function-name extraction, `docs/reports/waveforge-fork-audit.md`) across Wavefoundry's and Waveforge's independently-diverged `server_impl.py` files. This wave's improvements to those specific functions reach Waveforge automatically on their next merge, with zero rework on either side — the three `_wrap_*` wrappers and the individual `wf_*_response` lifecycle handlers are not shared, so this wave's benefit is concentrated exactly where the registry/middleware work lives | — |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| `build_registry` depends on the private FastMCP attribute `_tool_manager._tools`, which a dependency bump could reshape | The golden-snapshot test and the existing reload tests already read the same attribute, so a shape change fails visibly in the suite rather than silently; the read is confined to one function in `mcp_tool_registry.py` |
| Something caches a spec callable across reload | The registry is rebuilt on each registration pass and the reload test checks module identity |
| A roster tier is wrong for a registered tool and nothing at the registration site says otherwise | The registry parity test compares the introspected set against the roster in both directions; tiers have exactly one source (`mcp_tool_roster`), so there is no second copy to drift |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
