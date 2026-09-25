# Extension Tools May Use Core Prefixes

Change ID: `1yxl8-enh extension-tools-allow-core-prefixes`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-09-25

## Rationale

Waveforge feedback (modularity RFC section 10.1): a downstream distribution that shares Wavefoundry's naming convention cannot add new tools named `wf_*` because `mcp_tool_extensions` refuses any extension prefix that equals, starts with, or is a prefix of a core prefix, and refuses tier entries whose names use a core prefix. The operator decided not to prevent this: forks that are blocked will work around the rule and cause more issues. Name collisions stay detectable without the prefix rule, because registration already refuses any undeclared tool whose name matches an existing tool, and provenance (`ToolSpec.source_module`, `wf_server_info.extensions`) does not depend on the name.

Brief: remove the prefix-overlap and core-prefixed-name refusals; keep every name-collision, override, tier and fail-closed check; document a distribution-specific prefix as the recommendation and state that a later core release adding the same name makes the server refuse to start until the fork renames the tool or declares an override. No opt-in flag and no upgrade preflight collision check (operator decision).

## Requirements

1. `mcp_tool_extensions.declaration_problems` no longer refuses an extension prefix because it equals, starts with, or is a prefix of an entry in `CORE_TOOL_PREFIXES`, and no longer refuses a tier entry because its name uses a core prefix. `_prefixes_overlap` is removed if unused. Every other declaration check is unchanged, including refusing a tier for an existing core or runner tool.
2. Registration (`server_impl._install_extension_tools`) continues to refuse any attempted name that core already registers unless it is a declared override, and continues to require that every new tool start with a declared extension prefix and have a declared tier. A fork that wants `wf_` names declares `wf_` (or a longer `wf_` prefix) in `EXTENSION_TOOL_PREFIXES`.
3. The prefix contract, cost wrapper and allowlist rules continue to cover extension tools named with core prefixes (they already accept core prefixes).
4. Name-keyed core behavior. Rule: a name is reserved when any module-level collection in the served framework scripts is keyed or populated by MCP tool name and changes how the server wraps, accounts, dispatches or upgrade-reconciles a tool by that name. Registration refuses a new extension tool (not a declared override) whose name is reserved, naming the collection. Applying the rule today gives: `_LIFECYCLE_MUTATION_LOCK_TOOLS`, `_COST_EXEMPT_TOOLS`, `_ARTIFACT_EXTRACTORS`, `_COST_FOCUS_EXTRACTORS` (server_impl), `_STATE_SOURCE_EXTRACTORS` (context_efficiency_handlers), `publication_control.registered_publication_tool_names()`, and the retired-name keys of `render_platform_surfaces._RENAMED_MCP_TOOLS` (a fork tool with a retired name would otherwise be rewritten by upgrade reconciliation). A census test derives candidate collections from the rule (module-level collections whose members or keys intersect registered or retired tool names) and fails when one is neither in the reserved list nor recorded as not changing behavior for a name it does not own (for example sets reached only through core handlers passing their own literal name). The check runs at registration only; the allowlist renderer may render a rule for a name the server then refuses, which fails closed.
5. The spec's Distribution Extension Tools section, the `EXTENSION_TOOL_PREFIXES` comment and the extension tests reflect the new rule: overlapping prefixes are allowed; a distribution-specific prefix is recommended; a core release that later adds the same name causes a startup refusal naming the tool, and a tier entry naming the now-existing tool also makes `allow_rules` raise (stopping allowlist rendering and upgrade reconciliation); resolution is renaming the fork tool, or declaring an override when the fork tool is call-compatible with the new core tool (and removing its tier entry). `wf_help` uses a fixed catalog: it describes the `wf_` prefix as lifecycle and framework operations and does not list extension tools.

## Scope

In scope: `mcp_tool_extensions.py` validation, the extension tests, the spec section, the `mcp_tool_extensions` docstring and comments, and an Unreleased changelog bullet.

Out of scope: an opt-in flag, an upgrade preflight collision check, tool aliases or renames, changes to core tool names, tiers or the prefix contract, and RFC follow-ups 10.2 and 10.3.

## Acceptance Criteria

- [x] AC-1: A declared module registering a new tool named with a core prefix (for example `wf_fork_tool`, with `wf_` declared as an extension prefix and a tier) is served through `build_server` and `call_tool`, appears in the registry and rendered allowlist with its declared tier, and is wrapped like other extension tools.
- [x] AC-2: A declared module registering a name core already registers without declaring it as an override is still refused at registration with a diagnostic naming the tool; the existing collision, tier, override and fail-closed refusal fixtures still pass.
- [x] AC-3: The spec and changelog describe the shipped rule and recommendation, and the documents this change authors or edits validate.
- [x] AC-4: A new extension tool whose name is reserved under Requirement 4 (exercised with a retired `_RENAMED_MCP_TOOLS` key and with a fixture name added to a reserved collection in a scratch copy) is refused with a diagnostic naming the collection; a declared override of a registered core tool in those collections still registers; the census test fails when a behavior-changing name-keyed collection is added without classification.

## Tasks

- [x] Remove the prefix-overlap and core-prefixed-tier refusals from `declaration_problems`; update the module's docstring and comments.
- [x] Add a new positive fixture module registering a `wf_`-named tool for AC-1; update or drop the existing overlap fixtures (`prefix_shorter_than_core`, `prefix_longer_than_core`, `core_prefix_tier`), whose refusal cause changes; confirm the same-name refusal still holds (AC-2).
- [x] Add the reserved-name refusal (Requirement 4) with refusal fixtures, an override positive control and the census test (AC-4).
- [x] Update the spec section and add an Unreleased changelog bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Validation and tests | implementer | readiness | Single write owner |
| Documentation | implementer | validation | Spec and changelog |
| Verification | code, qa, security, docs-contract reviewers | implementation | Read-only |

## Serialization Points

- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/context_efficiency_handlers.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

N/A: no module boundary, ownership or trust-boundary change. The trust boundary (declared distribution code only) is unchanged; ADR `1ye5y`'s extension section does not state the prefix rule.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The requested capability |
| AC-2 | required | Collisions must stay detected once the prefix guard is gone |
| AC-3 | required | Forks implement against the documented contract |
| AC-4 | required | Replaces the protection the prefix rule gave for name-keyed core behavior |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-25 | Planned from Waveforge RFC section 10.1 and operator decision to allow core prefixes without an opt-in or preflight check | Operator request |
| 2026-09-25 | Readiness primer (no blockers): added Requirement 5 / AC-4 refusing new tools named in core name-keyed sets, a new positive fixture instead of converting overlap fixtures, server_impl in serialization points, spec notes on wf_help grouping | readiness-review.md |
| 2026-09-25 | Operator-approved second bounded repair after focused round (DOCS-READY-1..3 and code/QA notes): reserved-name rule with census, complete collection list including extractor maps and retired-name keys, corrected wf_help wording, allowlist and override-resolution notes | readiness-review.md |
| 2026-09-25 | Implemented: overlap and core-prefixed-tier refusals removed from declaration_problems; `_reserved_tool_name_collections` refuses new tools named in the seven reserved collections; new fixtures core_prefix_new_tool (served, tiered, wrapped, allowlisted), reserved_retired_name, reserved_collection_name; census test with 7 reserved and 18 non-behavior collections (the census found WORKFLOW_REQUIRED_KEYS in wave_lint_lib, classified non-behavior); spec, changelog; 23 extension tests OK; mutants in evidence/mutants.py killed. Gapfill: code reads by shell over anchors verified in readiness | test_extension_tool_modules.py; evidence/mutants.py |
| 2026-09-25 | Delivery repair DEL-CENSUS-COVERAGE (red-team and docs-contract): census widened to assignments derived from a classified collection (8 derived collections classified), membership invariant keeps reserved collections to served core or retired names, spec, testing-architecture and docstring narrowed to the actual predicate, ADR 1yb8v warning-scope clause, `InertRecordLayoutConfigTests` made standalone; mutants: derived collection and reserved-gains-unserved-name killed, unserved-only collection a documented survivor | test_extension_tool_modules.py; evidence/mutants.py |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-25 | Allow extension prefixes that overlap core prefixes; keep same-name refusal; recommend distribution-specific prefixes | Operator: preventing it only drives workarounds; collisions remain detected by name at registration | Opt-in flag: adds configuration for no extra safety. Upgrade preflight collision check: declined by operator; the startup refusal already names the collision. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A later core release adds a tool with the same name as a fork tool | Startup refusal names the tool; spec documents the resolution (rename or declare an override) |
| A fork declares a core prefix without intending to | Tools still need declared tiers and cannot shadow existing names; provenance lists every extension tool |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
