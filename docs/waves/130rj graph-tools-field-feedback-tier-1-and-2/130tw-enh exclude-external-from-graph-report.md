# `exclude_external` Parameter on `wave_graph_report` — Filter External Library Calls from Architectural Rankings

Change ID: `130tw-enh exclude-external-from-graph-report`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 130rj graph-tools-field-feedback-tier-1-and-2

## Rationale

Aceiss field report on `1.1.0+30tt`: `wave_graph_report(exclude_generated=true)` still shows `external::getClass` (count 127), `external::get` (count 117) as top fan_in entries. The first project-internal entry appears at rank 6. The `exclude_generated` filter does exactly what its name suggests — removes generated-tagged project nodes — but the operator's real intent on "show me architectural hotspots in my codebase" is also harmed by stdlib externals dominating the rankings.

The right fix is NOT to overload `exclude_generated` (the flag does what it says; the name matters). Instead, add a separate `exclude_external: bool = False` parameter that filters `external::*` nodes from `fan_in`, `fan_out`, `chokepoints`, and `betweenness` sections.

Default remains `False` for backward compatibility — operators who use fan_in as a stdlib-dependency-density signal still get that view. Setting `exclude_external=True` answers "what's important in MY code."

## Requirements

1. `wave_graph_report_response` accepts `exclude_external: bool = False`. When True, filters out any node whose `node_id` starts with `external::` from `fan_in`, `fan_out`, `chokepoints`, and `betweenness` sections.
2. MCP wrapper exposes the parameter with a docstring explaining the use-case.
3. Response echoes the flag (`"exclude_external": true`) so callers can confirm it took effect.
4. Filter operates independently of `exclude_generated` — both can be True simultaneously (and typically should be, for "architectural orientation in my code").
5. Communities section is NOT affected — external nodes aren't members of project communities.
6. Tests cover: (a) default off preserves externals, (b) flag on removes externals from fan_in, (c) combined `exclude_generated=True, exclude_external=True` returns project-internal-only rankings, (d) flag echoes in response.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py`: `exclude_external` parameter on `wave_graph_report_response` + filter logic + MCP wrapper signature update.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`: 4 regression tests.

**Out of scope:**

- Default-on behavior change. Backward compat preserved.
- Same filter on `code_graph_community`. That tool returns community members; externals aren't community members. No need.
- Same filter on per-symbol navigation tools (`code_callhierarchy`, `code_impact`). They already have `include_external` per wave 130ol's external-suppression default; the report tool is the missing parity surface.

## Acceptance Criteria

- [x] AC-1: `wave_graph_report_response` accepts `exclude_external: bool = False`. When True, every entry in `fan_in`, `fan_out`, `chokepoints`, `betweenness` whose `node_id` starts with `external::` is filtered out before truncation.
- [x] AC-2: MCP wrapper exposes `exclude_external` with a docstring; introspection confirms the parameter is in the FastMCP tool schema.
- [x] AC-3: Response carries `exclude_external: true/false` echoing the flag.
- [x] AC-4: `exclude_generated=True, exclude_external=True` combined returns only project-internal, non-generated rankings.
- [x] AC-5: `exclude_external=True` does not affect the `communities` section (community members are project-internal by definition).
- [x] AC-6: 4 regression tests cover the behavior; all existing tests continue to pass.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add `exclude_external` parameter to `wave_graph_report_response`
- [x] Apply filter to fan_in/fan_out/chokepoints/betweenness sections
- [x] Update MCP wrapper signature + docstring
- [x] Add 4 regression tests
- [x] Update MCP wrapper-layer parameter-exposure test (`TestMcpWrapperParameterExposure`) to assert `exclude_external` is present
- [x] Run framework tests
- [ ] Close gate (held open across remaining 130tw changes)
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The headline filter |
| AC-2 | required | MCP wrapper exposure — lesson from wave 130ol |
| AC-3 | required | Observable echo for caller confirmation |
| AC-4 | required | Combined-flag behavior verified |
| AC-5 | required | No collateral damage to communities |
| AC-6 | required | Regression coverage |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Separate `exclude_external` flag rather than overloading `exclude_generated` | The flags answer different questions. `exclude_generated`: "remove machine-generated noise." `exclude_external`: "show me MY code." Combining them loses the ability to ask either question alone | Overload `exclude_generated` (rejected — name no longer matches behavior; confusing for operators) |
| 2026-06-01 | Default `False` | Backward compat. Existing operators using fan_in as a dependency-density signal still get it | Default True (rejected — changes the default behavior; existing snapshot tests and external consumers break) |
| 2026-06-01 | Filter excludes `external::*` prefix only; doesn't filter "external" file= entries | Node IDs are the authoritative signal. File field is set from source_file on the node, not always populated for external nodes | Filter on `file == "external"` (rejected — node_id is the canonical signal) |

## Risks

| Risk | Mitigation |
|---|---|
| Operators using fan_in for dependency-density analysis miss the externals when `exclude_external=True` | Flag is opt-in; the legacy use case continues to work with the default |
| Communities section behavior unclear | AC-5 explicitly asserts no effect; doc string makes this explicit |

## Related Work

- Aceiss field report: "fan_in still shows external:: entries with exclude_generated=true. The filter should probably exclude externals from ranking sections too."
- Companion to `130rj-enh graph-tool-shape-consistency` (Change 2) and `130rj-enh generated-code-classifier-and-filters` (Change 5) — same fan_in/fan_out/chokepoints/betweenness sections, additional filter dimension.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
