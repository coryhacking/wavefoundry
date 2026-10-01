# A Tool Replacement Can Relist a Write Tool as Read or Replace the Edit Gates

Change ID: `1zhme-bug replacement-tier-downgrade`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-09-30
Wave: 1zicq install-and-permission-hardening

## Rationale

A downstream validation of v1.28.0 (request 4), verified: an extension's `EXTENSION_REPLACEMENTS` entry may declare a `tier`, and `mcp_tool_roster.all_tool_tiers` applies it with `if "tier" in spec: tiers[core_name] = spec["tier"]`, validating only that the value is `read` or `write`. A replacement of a core write-tier tool can therefore declare `read`, and the name lands in the read-tier allow rules that `render_platform_surfaces.render_claude_permissions` grants without the operator's write-tier setting. Replacements may also target the edit-gate tools `wf_open_gate` and `wf_close_gate` (core write tools); only the runner tool `wf_reload_mcp` is refused. The shipped declarations are empty, so no installation is affected today.

## Requirements

1. **No tier downgrade.** A replacement that declares a tier lower than the core tool's tier (write to read) is a declaration problem, raised through `ExtensionDeclarationError` like every other invalid declaration. `declaration_problems` and `validate_declaration` gain an optional `core_tiers` mapping (the extension module cannot import the roster, which imports it); both callers pass it: `mcp_tool_roster.all_tool_tiers` and the server's extension load in `wf_server/server_impl.py` (`_install_extension_tools`). `all_tool_tiers` therefore never lowers a core tier, and the server refuses the same declaration the roster does. Declaring the same tier, or raising read to write, stays allowed.
2. **Edit gates cannot be taken over by declaration.** A new constant in `mcp_tool_extensions` names the edit-gate tools `wf_open_gate` and `wf_close_gate`; a declaration that overrides (`EXTENSION_OVERRIDES`), replaces (`EXTENSION_REPLACEMENTS`) or hides one is refused, as runner tools already are. Aliases of them stay allowed (an alias serves the core handler). `RUNNER_TOOLS` is not reused: it also means "registered by the runner, not core".
3. **Threat model stated.** Extension modules are trusted distribution code running in the server process; these checks catch a mistaken or careless declaration and keep the permission roster honest. They are not a sandbox against code that patches handlers directly. The contract docs say so.
4. **Docs.** `docs/specs/mcp-tool-surface.md` (the replacement `tier` field and the replacement-target rules) and `docs/architecture/threat-model.md` (declared tiers and refused targets) describe the downgrade refusal and the protected gate tools; the contract comments in `mcp_tool_extensions` and the `all_tool_tiers` docstring match.
5. **Platforms.** Windows, macOS, Linux and WSL2 behave the same (declaration validation).
6. **Transition.** Applies when the release is loaded; no shipped declaration changes. CHANGELOG under `### Fixed` in `## [Unreleased]`.

## Scope

**Problem statement:** an extension replacement can lower a write tool's permission tier into hosts' default allow lists, or replace the edit-gate tools.

**In scope:**

- `mcp_tool_extensions` declaration validation; `mcp_tool_roster.all_tool_tiers`; the server's extension load call; contract docs; tests; CHANGELOG.

**Out of scope:**

- Tier handling for aliases and hidden names (they already take the core tier).
- Handler patching by extension code at runtime (trusted code; see Requirement 3).
- Name-list edit gating in hooks (validation request 5, an observation).

## Acceptance Criteria

- [x] AC-1: a replacement declaring `tier: read` for a core write tool is a declaration problem through both `all_tool_tiers` and the server's extension load, and the core write tier stands; same-tier and read-to-write declarations still apply.
- [x] AC-2: an override, a replacement, or a hidden name targeting `wf_open_gate` or `wf_close_gate` is refused; an alias of either is still accepted.
- [x] AC-3: the tool-surface spec, the threat model and the in-code contract comments describe the downgrade refusal, the protected gate tools and the trusted-code boundary.
- [x] AC-4: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Tier-downgrade validation and the roster guard.
- [x] Protected gate-tool constant checked for overrides, replacements and hidden names.
- [x] `core_tiers` passed from the server's extension load.
- [x] Contract docs and comments.
- [x] Tests; CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Declaration guards | implementer | readiness | |
| Review | code-reviewer, qa-reviewer, security-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`, `.wavefoundry/framework/scripts/mcp_tool_roster.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `docs/specs/mcp-tool-surface.md`, `docs/architecture/threat-model.md`
- In `server_impl.py`, only `_install_extension_tools` changes.

## Affected Architecture Docs

`docs/architecture/threat-model.md` (extension declarations); the contract lives in `docs/specs/mcp-tool-surface.md`.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Permission-roster integrity |
| AC-2 | required | Edit gates guard framework edits |
| AC-3 | required | The contract docs must stay true |
| AC-4 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-30 | Implemented. `EDIT_GATE_TOOLS` in `mcp_tool_extensions` refused for overrides, replacements and hidden names; `declaration_problems`/`validate_declaration` take optional `core_tiers` and refuse a write-to-read replacement; `all_tool_tiers` passes `TOOL_TIERS` and `_install_extension_tools` passes `roster.TOOL_TIERS`. Tests: four new refusal fixtures through the real server (`replace_downgrade`, `override_gate`, `replace_gate`, `hidden_gate`), three declaration tests including the roster raising and an alias of a gate tool accepted; `EDIT_GATE_TOOLS` classified non-behavior in the census. Mutation: dropping `core_tiers` from the server load fails `replace_downgrade`. Docs: tool-surface spec, threat model, testing-architecture refusal row (architecture-reviewer note), comments, CHANGELOG. `test_extension_tool_modules.py` 60, `test_server_package.py` 31, `test_render_platform_surfaces.py` 116 OK | Focused runs; mutation |
| 2026-09-30 | Readiness round 1: code-reviewer and red-team blocked because `EXTENSION_OVERRIDES` can also replace the gate handlers; docs-contract-reviewer blocked because the tool-surface spec and threat model would go stale. Repaired: protected constant across overrides, replacements and hidden names; `core_tiers` threaded to the server load; contract docs in scope; trusted-code boundary stated | Prepare council and lane review |
| 2026-09-30 | Planned from the v1.28.0 downstream validation (request 4), verified: `all_tool_tiers` applies a replacement tier unconditionally; replacement targets refuse only `RUNNER_TOOLS` (`wf_reload_mcp`); `wf_open_gate`/`wf_close_gate` are core write tools; no existing test covers a write-to-read downgrade | Code reads |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Refuse the declaration rather than silently keep the core tier | A distribution author learns at load time; nothing is half-applied | Keep the core tier and warn |

## Risks

| Risk | Mitigation |
| --- | --- |
| A distribution relies on downgrading | None ship; the refusal names the rule |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
