# MCP Resource Template Surface

Change ID: `1298v-feat mcp-resource-template-surface`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-04-29
Wave: `12ahv mcp-agent-surface`

## Rationale

Wavefoundry's MCP server currently exposes useful callable tools, but its MCP resource and resource-template registries are empty. That is fine for actions, but it leaves stable read-only context such as Start Here docs, prompt references, active wave state, handoff state, seed prompts, and change docs available only through tool calls or direct filesystem reads. Adding a small resource/template surface would make common context discoverable as MCP context without treating every read as an action.

## Requirements

1. Add read-only MCP resources for high-value static or current-session context:
  - project overview
  - prompt index
  - architecture current-state summary
  - current wave
  - current session handoff
2. Add MCP resource templates for parameterized reads:
  - change by ID or prefix
  - wave by ID or prefix
  - prompt by shortcut/slug
  - seed by slug/name
  - architecture doc by slug
3. Resource and template reads must not mutate repository state.
4. Resource/template implementations must reuse existing server helpers where practical.
5. Missing resources must return clear not-found responses rather than raw tracebacks.
6. Tests must cover resource registration, successful reads, and missing-resource behavior.

## Scope

**Problem statement:** MCP clients can call Wavefoundry tools, but cannot discover or attach Wavefoundry context through MCP's resource/template mechanisms. This makes read-only context less visible and keeps agents dependent on tool calls or direct file reads for stable documentation.

**In scope:**

- Read-only MCP resources and resource templates in `.wavefoundry/framework/scripts/server.py`
- Tests in `test_server_tools.py` or a dedicated server-resource test file
- AGENTS.md and architecture docs updates documenting the resource/template surface
- No-op behavior when optional docs do not exist in a target repo

**Out of scope:**

- Any mutation tools
- Lifecycle state transitions such as create/admit/prepare/close wave
- Replacing existing tools such as `docs_search`, `wave_get_change`, or `seed_get`
- Remote resource access or network-backed resources

## Acceptance Criteria

- MCP resource registry exposes stable Start Here resources for project overview, prompt index, current architecture state, current wave, and session handoff.
- MCP resource templates expose change, wave, prompt, seed, and architecture-doc reads by identifier.
- Registered resources/templates work against an explicit target root and preserve allowed-root behavior already expected of the server.
- Missing files or unknown identifiers return clear not-found messages.
- Existing MCP tools continue to register and pass their current tests.
- Tests cover resource/template registration and representative reads.
- AGENTS.md documents when to use resources/templates versus tools.
- Architecture docs describe the read-only MCP resource path.

## Tasks

- Inspect FastMCP resource/template APIs and current `server.py` registration style.
- Define URI names for stable resources and templates.
- Implement resource handlers for Start Here docs and current state.
- Implement resource templates for change, wave, prompt, seed, and architecture docs.
- Add tests for registration and read behavior.
- Update AGENTS.md MCP Server section.
- Update architecture docs that describe MCP topology and data/control flow.
- Run framework tests and docs lint.

## Agent Execution Graph


| Workstream       | Owner       | Depends On       | Notes                                             |
| ---------------- | ----------- | ---------------- | ------------------------------------------------- |
| server-resources | implementer | —                | Add read-only MCP resource/template registrations |
| tests            | implementer | server-resources | Cover registration and missing-resource behavior  |
| docs             | implementer | server-resources | Document usage and topology                       |


## Serialization Points

- `server.py` resource registration should land before test/docs details are finalized.
- URI naming should be reviewed before implementation to avoid compatibility churn.

## Affected Architecture Docs

- `docs/architecture/current-state.md`
- `docs/architecture/data-and-control-flow.md`
- Possibly `docs/architecture/domain-map.md` if the MCP resource surface becomes a separately named interface boundary.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority  | Rationale                                                      |
| ---- | --------- | -------------------------------------------------------------- |
| AC-1 | required  | Resource registration is the feature's main deliverable        |
| AC-2 | required  | Templates are the part that removes repeated direct file reads |
| AC-3 | required  | Target-root behavior is part of the MCP safety model           |
| AC-4 | required  | MCP clients need predictable failures                          |
| AC-5 | required  | Existing tool surface must not regress                         |
| AC-6 | required  | Resource/template support needs direct test coverage           |
| AC-7 | important | Agents need guidance on when to use resources versus tools     |
| AC-8 | important | Architecture docs should reflect the new read path             |


## Progress Log


| Date       | Update                                          | Evidence                                                 |
| ---------- | ----------------------------------------------- | -------------------------------------------------------- |
| 2026-04-29 | Planned MCP resource/template follow-up feature | `docs/plans/1298v-feat mcp-resource-template-surface.md` |
| 2026-05-01 | Implementation complete. 5 stable resources (`wavefoundry://overview`, `wavefoundry://prompts`, `wavefoundry://architecture/current-state`, `wavefoundry://wave/current`, `wavefoundry://session-handoff`) and 5 resource templates (`change/{id}`, `wave/{id}`, `prompt/{slug}`, `seed/{slug}`, `architecture/{slug}`) registered in server.py. 17 new resource/template tests added. AGENTS.md updated with resources-vs-tools guidance. Architecture docs (current-state.md, data-and-control-flow.md) updated with Path 6b read path and MCP topology diagram. 344 tests pass. docs-lint clean. | `python3 .wavefoundry/framework/scripts/run_tests.py` → 344 OK; `.wavefoundry/bin/docs-lint` → ok |


## Decision Log


| Date       | Decision                                    | Reason                                                                                         | Alternatives                                                                      |
| ---------- | ------------------------------------------- | ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| 2026-04-29 | Scope is read-only resources/templates only | Keeps this separate from lifecycle mutation and avoids expanding MCP write surface prematurely | Add resource support while also adding lifecycle mutations; rejected as too broad |


## Risks


| Risk                                      | Mitigation                                                                                                          |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| URI naming churn breaks client habits     | Choose simple, stable names and document them before implementation                                                 |
| Resource handlers duplicate tool logic    | Reuse existing helper functions such as `get_change`, `get_prompt`, `current_wave`, and seed lookup where practical |
| Clients vary in resource/template support | Keep existing tools as the primary compatibility path; resources improve context discovery but do not replace tools |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.