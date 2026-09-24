# Extension Tool Modules

Change ID: `1yuc4-feat extension-tool-modules`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-09-23
Wave: 1yv9l extension-tool-modules

## Rationale

A downstream distribution (a fork that ships its own framework pack) needs to add its own MCP tools. Enterprise security review requires those tools to be served by the single Wavefoundry MCP server entry point, so operators validate and approve one server rather than several. Today the only way to add a tool is to edit `register_mcp_surface` in `server_impl.py`, which turns every upstream release into a merge conflict for the fork.

Brief: goal is a generic, fork-extensible tool set under the one server entry point. Audience is a downstream distribution that edits one stdlib-only module at merge time. Wavefoundry needs no knowledge of any fork's tools. Constraints: no auto-discovery and no code loaded from target repositories (the approved distribution is exactly what runs); stock Wavefoundry behavior and public tool surface unchanged; follows the fork-editable constant precedent of `record_paths` (wave `1y0gz`). Success: a fixture extension module is served, permissioned, wrapped, reloadable and visible in provenance, while an empty declaration leaves the stock surface byte-identical.

## Requirements

1. Add a stdlib-only module, `mcp_tool_extensions.py`, that a downstream distribution edits at merge time. It declares the extension module names to register, the tool-name prefixes new extension tools may use, a permission tier (`read` or `write`) for every new extension tool, and the set of existing tool names each module overrides. Shipped values are empty. It imports nothing from the server and carries the pure validation helpers for the declaration, so the permission renderer, upgrade and the server apply the same checks without starting the server.
2. Staged registration: `register_mcp_surface` imports each declared module by public name and calls its `register(mcp, get_handler)` against a staging tool surface (a FastMCP instance whose `add_tool` records every attempt, so `@mcp.tool()` decorators work) rather than the served tool table. The staging surface and the core table are argument-model normalized before comparison, so every Requirement 4 check runs on the schemas the server would publish. Only after every declared module has staged and every check passes are overridden core tools removed and the staged tools installed into the served table, before the prefix contract, served-table normalization and the `MIDDLEWARE` chain run, so new and overriding extension tools pass through the same contract and wrappers as core tools. Modules are loaded only from the declaration; nothing is discovered from the filesystem or a target repository. Declared names are single-file flat modules.
3. Overrides: an extension may replace an existing tool only when the declaration names that tool as an override for that module. Override targets are tools registered by core `register_mcp_surface`; runner tools (`mcp_tool_roster.RUNNER_TOOLS`) can never be overridden. Installation removes the existing tool and installs the staged replacement, because FastMCP's `add_tool` otherwise keeps the existing tool and only logs a warning. An override keeps the public name, so seeds, prompts, allowlists and server guidance that name the tool reach the replacement. An override keeps the core permission tier and must be structurally call-compatible on the normalized published input schema: it rejects undeclared arguments the way core tools do (its handler takes `**kwargs`, so normalization closes its schema), accepts every parameter of the tool it replaces, and requires no parameter the replaced tool left optional. Returning the typed unknown-argument diagnostic (by calling `_ensure_no_extra_args`, reachable by public name on `server_impl`) is a documented obligation on the extension, not a registration check, because observing it would require calling extension code during registration. Replacing the MCP tool does not change the server's internal callers of core response functions.
4. Registration fails closed with a diagnostic naming the module and the cause when a declared module name collides with an existing framework script module, fails to import, has no source file, or whose resolved file's resolved parent is not the resolved framework scripts directory; lacks `register`, or raises during registration; attempts to register a name that is already registered by core or already staged by another module, unless it is a declared override of a core tool (judged from the recorded attempts, since FastMCP silently ignores a duplicate); declares an override of a runner tool, of a name core does not register, or does not register a declared override; declares the same override in two modules; registers a new tool without a declared extension prefix or tier, or whose name matches any core prefix; leaves a declared tier unregistered; or breaks override structural call-compatibility. An extension prefix is invalid when it and any core prefix in `MCP_TOOL_PREFIXES` are equal or either begins with the other.
5. Failure leaves no unwrapped surface. Any failure between core registration and the completed `MIDDLEWARE` chain (the extension checks above and the existing prefix contract) removes every tool other than the runner tools from the served table before the error propagates; the runner-tool set comes from `mcp_tool_roster.RUNNER_TOOLS`, and if the roster cannot load, every tool is removed. At startup the server refuses to run; on `wf_reload_mcp` the existing `register_surface_failed` warning is returned while only the runner tools are served, so no core tool is ever served without its lock, guard or cost wrappers.
6. Permission tiers: the roster's rule-producing functions (`tools_for_tiers`, `allow_rules`) include declared tiers for new extension tools, so the rendered host allowlist and the upgrade allowlist reconciliation cover them through the existing tier opt-in. Before merging, the roster runs the declaration's validation helpers and raises, rendering no rules, when a tier entry names a core tool or runner tool, lacks a declared extension prefix, or when a declared prefix overlaps a core prefix. Overrides reuse the core tier, so the allowlist does not change for them. Core `TOOL_TIERS` stays core-only so the existing core parity checks are unchanged. The runtime registry parity check accounts for extension tools as rostered.
7. Wrappers and contract checks: the middleware chain applies by tool name, so an override of a core tool receives exactly the wrappers the replaced tool had (cost recording, the lifecycle mutation lock for lifecycle tools, the upgrade publication guard for registered publishers). The prefix contract (`first_party_tool_names_violating_prefix`) and the cost wrapper's prefix filter both accept declared extension prefixes, so new extension tools start and are costed like first-party tools. New write-tier extension tools fail fast while Upgrade owns project state through `publication_control.publication_checkpoint_reason`; the guard's registry lookup returns no reason for unknown names, so they need that direct checkpoint path rather than only joining the guarded name set. Trust-boundary statements, documented rather than enforced: new extension tools must not write wave lifecycle records directly; distribution-shipped extension code runs with the server's authority, so an extension that rebinds core tools or wrapper names in place (the `MIDDLEWARE` entries bind late) is outside what staging can detect.
8. Reload: `mcp_tool_extensions` is a literal entry on the reload purge list, and the purge reads the fresh declaration before purging the modules it names, so an edited declaration or declared extension module is fresh after reload and overrides are re-applied. Undeclared helper modules an extension imports are not purged; the spec says so.
9. Provenance: `wf_server_info_response` reports the declaration module's path and hash, the declared prefixes, and for each loaded extension module its repository-relative path, a hash of the bytes imported, the new tools it registered with their tiers, and the core tools it overrides, so an operator can confirm what code serves each tool. With no declarations the field is present and reports empty declarations. The `wf_server_info` handler body inside `register_mcp_surface` is not changed.
10. Documentation: record the extension contract in `docs/specs/mcp-tool-surface.md` (the one edited module, `register(mcp, get_handler)` where `get_handler()` returns the server's handler object, what the staging surface supports, the flat-module and location rule, prefix, tier and override rules, structural call-compatibility and the unknown-argument obligation, failure behavior, the internal-caller and undeclared-helper reload limits, the trust-boundary statements and the new `wf_server_info` field), and correct the spec's Naming Contract prefix table to `MCP_TOOL_PREFIXES`, naming that constant as the source of the prefix rule. Add a section to ADR `1ye5y` recording this hook, its exception to the module-top public-name import rule (declared modules are imported during registration), the first import dependency between flat siblings (`mcp_tool_roster` reading `mcp_tool_extensions`) against the ADR's revisit trigger, the package question declined for this hook with the module-count trigger retained, and tool aliases/namespace transforms declined because declared overrides keep canonical names.

## Scope

**Problem statement:** a fork cannot add MCP tools to the single approved server without editing core registration.

**In scope:**

- The new declaration module, registration hook, explicit overrides, fail-closed validation, roster tier merge, wrapper coverage, reload purge, provenance reporting, tests and the documentation in Requirement 10.

**Out of scope:**

- Any specific fork's tools; tool aliases, renames or namespace transforms; overrides that change a tool's tier or break call-compatibility; redirecting the server's internal callers of core response functions; a `server/` package; config-driven, repository-supplied or auto-discovered extension code; out-of-process or proxied tool sources; extension resources or prompts; lifecycle mutation lock coverage for new (non-override) extension tools; changes to core tool names, schemas or tiers.

## Acceptance Criteria

- [x] AC-1: With the shipped empty declaration, the committed tool-surface golden fixture, the core roster parity checks, the rendered allowlist and the stock `wf_server_info` fields other than the new empty extension field are unchanged.
- [x] AC-2: A fixture extension module declared through the public declaration is served by the real registration path: its tools are callable through the MCP tool table, carry the middleware marker for the applicable wrappers in declared order, appear in the runtime registry without parity defects, and their declared tiers appear in the rendered allowlist rules.
- [x] AC-3: Each fail-closed case in Requirement 4 stops registration with a diagnostic naming the module and cause, demonstrated with a fixture per case, and an invalid tier declaration makes the real allowlist renderer raise without rendering rules. For startup and for `wf_reload_mcp`, a failing case leaves no served tool other than the reload survivors, and no core tool is served without its applicable wrappers.
- [x] AC-4: A write-tier fixture extension tool fails fast while an upgrade publication checkpoint is active, and a read-tier fixture tool is costed like a first-party tool.
- [x] AC-5: After a fixture extension module's source is edited in a scratch copy of the scripts tree (the existing subprocess reload pattern in `tests/test_handler_modules.py`), `wf_reload_mcp` serves the edited behavior, an undeclared module placed in the scripts directory is not loaded, and `wf_server_info` reports the module path, its updated hash, its new tools and its overrides.
- [x] AC-6: The spec and the ADR `1ye5y` section describe the shipped contract and both declined decisions, and the documents this change authors or edits validate.
- [x] AC-7: A declared fixture override of a core read tool and of a core lifecycle tool is served under the core name through the MCP tool table instead of the core handler, rejects an undeclared argument with the typed unknown-argument diagnostic, keeps the core tier and allowlist rule, and carries the same middleware markers the replaced tool had (including the lifecycle lock for the lifecycle tool); an undeclared same-name registration is refused rather than silently ignored.

## Tasks

- [x] Add `mcp_tool_extensions.py` with empty declarations and its pure validation helpers.
- [x] Wire declared modules into `register_mcp_surface` ahead of the prefix contract and `MIDDLEWARE`, with explicit override removal, call-compatibility checks and fail-closed validation.
- [x] Merge extension tiers into the roster rule functions and the registry parity check; extend the prefix, cost and upgrade-guard coverage to declared extension tools.
- [x] Add declared modules to the reload purge and report provenance from `wf_server_info`.
- [x] Add fixture-based tests through the real registration, renderer and reload paths, with negative controls per fail-closed case.
- [x] Update `docs/specs/mcp-tool-surface.md`, ADR `1ye5y` and affected architecture docs; add an Unreleased changelog bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Declaration and registration hook | implementer | readiness | Single write owner for server_impl.py and the roster |
| Tests and fixtures | implementer | hook | Real registration, renderer and reload paths |
| Documentation | implementer | hook | Spec, ADR section, changelog |
| Independent verification | code, qa, security, architecture reviewers | implementation | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/mcp_tool_roster.py`
- `.wavefoundry/framework/scripts/mcp_tool_registry.py`
- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/publication_control.py`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/decisions/1ye5y-adr flat-sibling-tool-registry.md`
- `docs/architecture/layering-rules.md`
- `docs/architecture/current-state.md`
- `docs/architecture/threat-model.md`
- `docs/architecture/testing-architecture.md`
- `docs/contributing/build-and-verification.md`

## Affected Architecture Docs

- `docs/architecture/decisions/1ye5y-adr flat-sibling-tool-registry.md`: extension section per Requirement 10.
- `docs/architecture/layering-rules.md`: the handler-sibling row says registration remains in the composition root; add the declared extension exception.
- `docs/architecture/current-state.md`: registration flow gains staged extension install.
- `docs/architecture/threat-model.md`: trust-boundary row for distribution-shipped extension modules (trusted as distribution code; anything that can write the scripts directory already holds server authority).
- `docs/architecture/testing-architecture.md`: fixture extension coverage.
- `docs/contributing/build-and-verification.md`: runtime parity wording includes declared extension tiers.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Stock distribution must not change |
| AC-2 | required | Core capability |
| AC-3 | required | Enterprise approval relies on fail-closed loading |
| AC-4 | required | Extension tools must not bypass upgrade safety or telemetry |
| AC-5 | required | Reload and provenance are part of the operating contract |
| AC-6 | required | Forks implement against the documented contract |
| AC-7 | required | Overrides are the primary extension path for existing tool names |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-23 | Planned from operator direction after the Waveforge RFC review: single server entry point for enterprise security, generic extensibility, forks extend themselves | Operator request; RFC section 9 open item 2 |
| 2026-09-23 | Bounded readiness repair of red-team RT-READY-1 to 4 and primer questions: staged registration, surface emptied on pre-middleware failure (including reload), recorded-attempt duplicate detection, two-way prefix rule, scripts-directory location check, normalized call-compatibility, declaration on purge list, write-tier checkpoint path | Red-team primer; `server._refresh_mcp_tool_surface`, `publication_control.publication_block_reason`, FastMCP `ToolManager.add_tool` verified |
| 2026-09-23 | Operator-approved second bounded repair after focused verification: structural call-compatibility with the unknown-argument diagnostic as extension obligation (CODE/DOCS-READY-1), runner tools never overridable (ARCH-READY-1), roster merge validates tiers and fails closed (SEC-READY-1), spec prefix table corrected to `MCP_TOOL_PREFIXES` (DOCS-READY-2); agreed notes folded in: resolved-directory location check, sibling-name collision, cross-module new-name collision, richer provenance, ADR exceptions, affected docs, AC-5 scratch-tree oracle | Focused readiness lanes; operator decision in session |
| 2026-09-23 | Implemented: `mcp_tool_extensions.py` (declarations + pure validation), staged loader/install/strip in `server_impl.py`, roster `all_tool_tiers`, registry tier merge, extension prefixes in the prefix contract and cost filter, direct checkpoint guard for write-tier extension tools, `extensions` provenance in `wf_server_info_response`; spec, ADR, architecture docs and changelog. Carried notes resolved: core prefixes now live in `mcp_tool_extensions.CORE_TOOL_PREFIXES` (server aliases it); module collision set is reserved names, stdlib names and modules the server already imported; roster-cannot-load fallback and allowlist/upgrade stop documented. Full suite 9,566 tests OK; 16 new tests; six mutants each killed. Gapfill: code reads for implementation used shell sed/grep over known anchors already verified by readiness lanes, faster than MCP round trips for bulk region reads | `test_extension_tool_modules.py`; `evidence/mutants.py`; test-cache inputs_hash 2b58386a |
| 2026-09-24 | Delivery repair cycle 1: refuse async handlers, unrecorded staging registrations, staging tampering, resources and prompts; drive lifecycle lock, upgrade guard and unknown-argument checks through FastMCP call_tool; relative provenance path and build_server startup refusal asserted; spec Failure list completed | `delivery-review.md` Repair cycle 1; `evidence/repair1-fingerprint.txt`; nine mutants killed |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-23 | Fork-edited stdlib-only declaration module, loaded only from that declaration | Matches the `record_paths` precedent; the approved distribution is exactly what runs; renderer can read tiers without the server | Workflow-config or repository-discovered modules: a new trust boundary that loads target-supplied code. Python entry-point plugins: requires pip-installed packaging Wavefoundry does not use. Separate MCP server per fork: rejected by operator, multiplies servers to approve. Proxied `tool_sources` command: rebuilds an MCP server inside ours. |
| 2026-09-23 | Fail closed at startup for any declared-module defect | A declared module is part of the approved distribution; silently skipping it hides a broken deployment | Skip with warning: server looks healthy while approved tools are missing |
| 2026-09-23 | Keep lifecycle mutation lock core-only | The lock set is tied to lifecycle record ownership; new extension tools may not write those records, while overrides inherit the lock by name | Let new extension tools opt into the lock: widens an ownership contract without a consumer |
| 2026-09-23 | Stage extension registration, then install; empty the surface on any pre-middleware failure | Readiness primer RT-READY-1/2: FastMCP silently ignores duplicate names, and a reload failure after core registration served core tools without wrappers | Register directly into the served table and diff names: cannot see ignored duplicates. Rollback-on-exception: must restore exact prior state on the reload path, harder to prove |
| 2026-09-23 | Allow overriding existing tools, only when explicitly declared | Operator direction: existing `wf_`/`code_` names keep working and reach the fork's implementation. FastMCP silently keeps the first registration, so an implicit override would silently fail | Implicit override by re-registration: silently serves the core tool. Last-writer-wins without declaration: an accidental name reuse replaces a core tool unnoticed |
| 2026-09-23 | Overrides keep the core tier and must be call-compatible | Allowlists, prompts and server recovery guidance name the tool and its parameters; an incompatible replacement breaks them silently | Allow any schema or tier: hosts' approvals and agent guidance no longer describe what runs |

## Risks

| Risk | Mitigation |
| --- | --- |
| Extension module breaks reload freshness | Purge through the existing mechanism and test an edited module after reload |
| Core release later adds a tool that collides with an extension name | Extension prefixes may not overlap core prefixes; collision is a startup failure, never a silent shadow |
| Extension tiers drift from registered tools | Registration fails when declared tiers and registered tools differ |
| Hook reorders the core wrapper chain | Golden fixture and existing middleware-order tests guard core; AC-1 |
| Operators assume an override changes behavior the server reaches internally | Spec states overrides replace the public tool only; provenance lists every override |
| Override drops a guarantee the core tool enforced (validation, containment) | Overrides inherit the core wrappers by name; the replacement's own guarantees are the fork's responsibility and the spec says so |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
