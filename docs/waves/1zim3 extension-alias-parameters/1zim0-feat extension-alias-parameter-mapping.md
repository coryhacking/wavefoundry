# Extension Aliases Can Rename and Pin Parameters, and Overrides Can Delegate to the Core Handler

Change ID: `1zim0-feat extension-alias-parameter-mapping`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-30
Wave: 1zim3 extension-alias-parameters

## Rationale

From a downstream distribution's note against `v1.28.0` ("Tool-name seams", requests 1 to 3; request 4, replacement tiers, shipped in wave 1zicq). With a vocabulary profile that renames the tiers (container "Set", item "Wave"), tool *parameter* names still carry the default vocabulary: `wf_add_change(wave_id, change_id)` means *set id, wave id*. A plain `EXTENSION_TOOL_ALIASES` entry cannot serve `wf_add_wave(set_id, wave_id)`, because an alias is a `model_copy` of the wrapped canonical `Tool` (`_install_served_names`) with the canonical schema. The other routes lose guarantees: a new extension tool that calls a core `*_response` function skips the name-keyed lifecycle lock, publication guard and cost accounting; an override removes the core handler and must copy upstream internals to delegate; and hints come back with canonical tool and parameter names.

The chosen seam keeps everything keyed on the canonical name: a parameter-mapped alias is served by a translating function that renames (and pins) arguments and then calls the canonical tool's wrapped callable, so the lock, guard, cost accounting and tier apply exactly as for the canonical name.

## Requirements

1. **Declaration.** A new constant `EXTENSION_TOOL_PARAMETERS: {alias: {"rename": {alias_param: canonical_param}, "fixed": {canonical_param: value}}}` applies to names declared in `EXTENSION_TOOL_ALIASES`. `rename` must be a bijection between the alias's parameters and the canonical parameters that are not fixed; `fixed` names canonical parameters with JSON-serialisable values the canonical schema accepts. Validation (in `mcp_tool_extensions.declaration_problems`, plus the server for checks that need the live schema) refuses: an entry for a name that is not an alias; a rename that is not a bijection or collides with another alias parameter; a fixed name that is not a canonical parameter, is also renamed, or whose value the canonical schema rejects; and a mapping on an alias of a runner or edit-gate tool. A refused declaration serves nothing beyond runner tools, as today.
2. **Served schema and call.** The alias's input schema is the canonical schema with the properties renamed and the fixed ones removed; types, descriptions, defaults and the required list carry over under the new names. A call is validated against the alias schema, translated (renames reversed, fixed values added) and passed to the canonical tool's wrapped callable, so the canonical name's lifecycle lock, publication guard, cost accounting, extractors and tier apply. An unknown argument is refused as for any tool. The alias takes the canonical tool's tier and annotations.
3. **Hints.** The served-name rewrite (`_rewrite_served_names`) maps a canonical tool name in `next_tools` and `recovery_tools` to its alias as today. In `usage` and `recovery_usage`, a call written as `canonical(arg=..., ...)` is rewritten to the alias with its parameters renamed only when every argument is representable (each fixed parameter is absent or equals the pinned value; fixed ones are then dropped); otherwise the canonical form is kept. `data` and prose keep canonical names, as today.
4. **Override delegation.** For each name a module declares in `EXTENSION_OVERRIDES`, the staging surface offers `core_handler(name)` during `register`, returning the core tool's handler *before* middleware (the override's own registration is wrapped by name, so delegating through it takes the lock and guard once, not twice). Asking for a name the module did not declare as an override raises.
5. **Docs and provenance.** `docs/specs/mcp-tool-surface.md` documents the constant, the schema rule, the hint rule and `core_handler`; `wf_server_info` extension provenance lists parameter mappings. `docs/architecture/threat-model.md` notes that a mapped alias keeps the canonical name's controls.
6. **Platforms.** Windows, macOS, Linux and WSL2 behave the same (in-process schema and call translation).
7. **Transition.** Additive; an empty declaration changes nothing. CHANGELOG under `### Added` in `## [Unreleased]`.

## Scope

**Problem statement:** a distribution with a renamed vocabulary cannot serve a tool whose parameter names match its vocabulary while keeping the canonical tool's lock, guard, accounting and tier, and an override cannot delegate to the core handler without copying internals.

**In scope:**

- `mcp_tool_extensions` (constant and validation), `wf_server/server_impl.py` (`_install_served_names`, the staging surface, `_rewrite_served_names`, provenance), `mcp_tool_roster` only if tiers need the new names; tests; spec, threat model, CHANGELOG.

**Out of scope:**

- Renaming parameter names inside response `data` or prose.
- A public accessor that calls a served canonical tool by name from a new extension tool (the mapped alias covers the requested ground without it).
- Lifecycle-lock opt-in for arbitrary new extension tools.
- Test-suite portability under a distribution's declarations (planned in `1zim1`).

## Acceptance Criteria

- [ ] AC-1: a declared mapping serves the alias with the renamed schema (fixed parameters removed, types, defaults and required list carried over), and a call through FastMCP `call_tool` reaches the canonical behaviour with translated arguments; each refusal case in Requirement 1 refuses at server start and serves only runner tools.
- [ ] AC-2: a mapped alias of a lifecycle-locked, publication-guarded tool takes the lock (observed held inside the canonical body) and the guard (fails fast during an upgrade checkpoint), records cost under the canonical name, and has the canonical tier in the allow rules.
- [ ] AC-3: hints: a canonical `usage` call with representable arguments is rewritten to the alias with renamed parameters; one whose fixed argument differs keeps the canonical form; list hints map names as today.
- [ ] AC-4: an override that calls `core_handler(name)` returns the core result with the lock taken once (no deadlock, no double cost record); asking for an undeclared name raises at registration.
- [ ] AC-5: the spec, threat model, provenance and CHANGELOG describe the mapping and delegation.
- [ ] AC-6: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [ ] Constant and declaration validation.
- [ ] Translating alias tool and schema.
- [ ] Hint rewrite for mapped calls.
- [ ] Staging `core_handler`.
- [ ] Provenance; docs; CHANGELOG.
- [ ] Tests through FastMCP `call_tool`, refusal fixtures, census classification of the new constant.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Alias mapping | implementer | readiness | |
| Override delegation | implementer | alias mapping | same files |
| Review | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `docs/specs/mcp-tool-surface.md`, `docs/architecture/threat-model.md`

## Affected Architecture Docs

`docs/architecture/threat-model.md` (extension declarations row).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The core capability |
| AC-2 | required | Controls follow the canonical name |
| AC-3 | important | Hints stay usable |
| AC-4 | required | Delegation without copying internals |
| AC-5 | required | Contract docs |
| AC-6 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-30 | Planned from the downstream "Tool-name seams" note, verified: `_install_served_names` serves an alias as `table[canonical].model_copy(update={"name": alias})`, sharing the wrapped callable and schema; `_rewrite_served_names` rewrites tool names only in hint fields; replacements capture the core tool into `_EXTENSION_REPLACED_CORE` and serve it under `alias_for_core`, overrides capture nothing; FastMCP validates arguments through the tool's own `fn_metadata`, so a renamed schema needs its own argument model. Request 4 shipped in 1zicq (1zhme) | Code reads |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Parameter-mapped aliases rather than a public call-by-name accessor | Every control stays keyed on the canonical name with no new opt-in surface | Accessor plus lifecycle-lock opt-in (the note's alternative) |
| 2026-09-30 | `core_handler` returns the pre-middleware handler | The override's own wrapper already applies the name-keyed controls; a wrapped handler would lock twice | Return the wrapped handler |
| 2026-09-30 | Fixed arguments are part of the same constant | One translation path; the note suggested folding them in | Separate constant |

## Risks

| Risk | Mitigation |
| --- | --- |
| FastMCP's argument model for a generated signature diverges from the canonical model (defaults, `Annotated` metadata) | Build the alias model from the canonical tool's `fn_metadata` and compare schemas in tests; a readiness spike proves the approach on `wf_add_change` and `wf_review_wave` |
| Hint rewrite misreads a call in prose | Rewrite only `usage` and `recovery_usage`, and only exact `name(args)` calls |
| Double application of name-keyed wrappers | Tests observe one lock acquisition and one cost record |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
