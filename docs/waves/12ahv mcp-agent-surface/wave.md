# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-01

wave-id: `12ahv mcp-agent-surface`
Title: Mcp Agent Surface

## Changes

Change ID: `1297t-feat mcp-change-creation-coverage`
Change Status: `complete`

Change ID: `1298v-feat mcp-resource-template-surface`
Change Status: `complete`

Change ID: `12991-feat mcp-code-navigation-tools`
Change Status: `complete`

Change ID: `12aj7-enh mcp-layer-polish`
Change Status: `complete`

Completed At: 2026-05-01

## Wave Summary

Expand the Wavefoundry MCP agent surface across four fronts: complete the change-creation tool set (six missing `wave_new_*` kinds), route validation/gardening instructions through MCP-first, and add lifecycle DX fixes (mode discoverability, complete wave.md template, broken-link detection, journal-format hints); add read-only MCP resource and resource-template registrations for stable context discovery; add exact code-navigation tools (`code_keyword_search`, `code_read`, `code_list_files`) as milestone 1 of structured code navigation; and deliver six MCP layer polish improvements (wave status drift detection, `wave_change_create` deprecation, bulk change reads, session handoff tools, search mode transparency, AC priority warnings).

## Journal Watchpoints

- All ten `wave_new_*` kinds covered and tested before docs/seed updates begin (1297t).
- Seed edits for 1297t and 12aj7 performed inside a single `seed_edit_allowed` guarded window; guard restored before lint.
- 1298v resource URIs settled before implementation to avoid naming churn.
- 12991 includes both exact navigation (milestone 1) and symbol navigation (milestone 2, limited language scope + explicit unsupported responses); symbol tools must not overclaim coverage.
- 12aj7 `wave_change_create` deprecation does not remove the tool — removal is a follow-on.

## Review Signoff

Review date: 2026-05-01


| Lane               | Status | Notes                                                                                                                                                                                                                                                  |
| ------------------ | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| architecture       | ✅ pass | All changes scope to additive server.py tools/resources, AGENTS.md, and architecture doc updates. No structural reshaping of the MCP server or wave lifecycle. Domain boundary in domain-map.md to be evaluated at implementation.                     |
| code               | ✅ pass | Four change docs each identify specific helpers to reuse (indexer file-walk, existing server helpers, `get_change`, `get_prompt`, `current_wave`). No new external dependencies introduced. Tests required for all new helpers and tool registrations. |
| qa                 | ✅ pass | AC priority tables populated for all four changes. Required ACs cover root safety, ignore behavior, tool registration, existing-tool non-regression, and missing-resource behavior. All changes specify test coverage expectations.                    |
| docs-contract      | ✅ pass | Each change doc specifies AGENTS.md and architecture doc updates as explicit tasks. Architecture docs affected: `current-state.md`, `data-and-control-flow.md`, `domain-map.md`.                                                                       |
| performance        | ✅ pass | New tools are all read-only lightweight file operations (grep, directory walk, ranged read). MCP resources/templates are read-only. No background indexing or blocking I/O added.                                                                      |
| factor-12          | ✅ pass | MCP tools remain stateless per-call. Resources/templates are read-only and carry no session state. Symbol navigation backend choice (1299) must not introduce process-level state.                                                                     |
| factor-13          | ✅ pass | Response envelope (`status`, `data`, `diagnostics`, `next_tools`, `usage`) maintained across all new tools. Error paths must return `isError: True` responses, not raw exceptions.                                                                     |
| framework-operator | ✅ pass | Seed edits for 1297t and 12aj7 require `seed_edit_allowed.enabled: true` guard; watchpoint recorded. Stage gate (Prepare wave passed) confirmed before any framework edits begin.                                                                      |
| wave-coordinator   | ✅ pass | Implement order: 1297t → 1298v → 12991 → 12aj7. 1297t unblocks MCP-first routing used by later changes. 12aj7 `wave_change_create` deprecation must not remove the tool. Symbol tools must not overclaim language coverage.                            |


**Overall: PASS** — Wave 12ahv is ready for implementation. Begin with 1297t.

## Review Signoff Evidence

- 2026-05-01: All 4 changes confirmed complete. 539 tests pass. docs-lint clean. `seed_edit_allowed` guard verified restored to `false`. All AC priority tables populated. Architecture docs (domain-map.md, embedding-model.md, search-architecture.md, testing-architecture.md, data-and-control-flow.md, current-state.md) updated. AGENTS.md updated. Signed off: Engineering operator.

## Dependencies

- No external wave dependencies.