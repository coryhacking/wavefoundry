# The Framework Test Suite Runs With a Distribution's Tool Declarations

Change ID: `1zim4-debt suite-under-distribution-declarations`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zim5 profile-portable-test-suite

## Rationale

From the downstream "Tool-name seams" note against `v1.28.0`: with one alias declared in `mcp_tool_extensions`, the suite gains 34 stable failures there. Measured upstream at readiness (2026-09-30, scratch copy, `EXTENSION_TOOL_ALIASES = {"wf_alias_help": "wf_help"}`, 8 files sampled): 22 failures and errors in 6 files; 7 are MCP-surface test doubles breaking in `_install_served_names` at `table[canonical].model_copy` (6 in `test_sqlite_serving`, 1 in `test_graph_snapshot_readers`); others are stock-surface pins (`test_tool_surface_golden`, `test_mcp_tool_registry`) and declaration-machinery tests in `test_extension_tool_modules` that stack their own declaration on the ambient one. A distribution's declarations then mask real regressions in its own suite run.

## Requirements

1. **One base-declaration helper.** Tests whose subject is the shipped declaration, and tests that exercise the declaration machinery with their own declaration, run against a known base (the empty declaration plus the test's own) through one shared helper that patches the module constants and resets anything the server computed from them at import, so the ambient declaration does not leak in.
2. **Test doubles behave like FastMCP.** MCP-surface doubles build on a real `FastMCP` instance or a shared double exposing `_tool_manager._tools` of `Tool` objects, so declaration machinery runs against them as against the server.
3. **A declared-alias run.** `1zim1`'s run mode can apply a sample declaration (one alias now; a parameter-mapped alias once `1zim0` lands) under the default profile, so the suite proves it holds with declarations present.
4. **Platforms.** Windows, macOS, Linux and WSL2 behave the same.
5. **Transition.** Test infrastructure only; no CHANGELOG entry.

## Scope

**Problem statement:** a distribution's own tool declarations break unrelated tests in the framework suite, masking real regressions.

**In scope:**

- The base-declaration helper; the MCP-surface doubles; the sample-declaration option of the run mode.

**Out of scope:**

- Production changes to extension serving (`1zim0`).

## Acceptance Criteria

- [x] AC-1: with a sample alias declared, the suite passes under the default profile: stock-surface and declaration-machinery tests use the shared helper, and no test double fails in `_install_served_names`.
- [x] AC-2: removing the helper from a stock-surface test makes it fail under the sample declaration (the helper is load-bearing).
- [x] AC-3: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Base-declaration helper and its adoption.
- [x] FastMCP-backed doubles.
- [x] Sample-declaration option.
- [x] Tests.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Declarations portability | implementer | 1zim1 runner mode | |
| Review | code-reviewer, qa-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/`, `.wavefoundry/framework/scripts/run_tests.py`
- In tests: the stock-surface and declaration-machinery tests and MCP-surface doubles; in the runner: the sample-declaration option.

## Affected Architecture Docs

`docs/architecture/testing-architecture.md` (Doubles Policy entry for the FastMCP-backed double).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Distribution suites stay meaningful |
| AC-2 | required | Pins are real |
| AC-3 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Implemented. Helper `tests/declaration_support.py`: `base_declaration` / `apply_base_declaration` / `base_declaration_source` set every `EXTENSION_*` constant on every loaded copy of `mcp_tool_extensions` (including a copy another module holds after a server reload) to the frozen empty `SHIPPED_DECLARATION` plus the test's own, clear `_EXTENSION_PROVENANCE` and `_EXTENSION_REPLACED_CORE` on every loaded `server_impl`, and restore both; `declaration_profile_match` mirrors `declared_profile_match`. Double `RecordingFastMCP`: a real `FastMCP` that also records raw tool functions and resource functions; it replaces nine hand-written recorders in `test_sqlite_serving`, `test_graph_snapshot_readers`, `test_index_source_guard`, `test_setup_readiness_integration`, `test_server_tools_lifecycle` and `test_server_context_efficiency`. Helper adopted by `test_tool_surface_golden` (`_BootedSurface`, so `test_mcp_tool_registry`'s booted tests too), `RosterWarningTests`, `test_agents_available_tools_census_matches_registration`, `test_write_tier_permissions_delta_survives_bounding_with_counts`, `test_review_ergonomics_preserves_review_event_schema_and_tool_roster`, `DeclarationValidationTests` and every `test_extension_tool_modules` scratch driver. Asset `tests/fixtures/profiles/declared.json` (plain alias `wf_alias_help`; `wf_alias_read_raw` on `code_read` renaming `file` to `path` and pinning `with_line_numbers`); `apply_profile` now edits `mcp_tool_extensions` too (tuples kept, invalid declarations refused, declaration module imported only when edited), and the marker and `declared_profile_match` ignore declarations. Deviations: `test_declaration_module_ships_empty` now requires the shipped empty declaration or a profile asset's (as the record snapshot guard does); the tool-name collection census skips the declaration constants, which name tools by design. Whole-suite `--profile declared`: 45 failures and errors in 12 of 147 files before (5 of them this change's own first draft in `test_profile_support`), 0 in 148 files after, 34 skips both times. AC-2: the helper removed from `_BootedSurface` fails 3 golden tests, from `RosterWarningTests` 2; 8 more scratch mutations of the helper, double and `apply_profile` each fail the new tests. No production defect found. Test infrastructure only; behaves the same on Windows, macOS, Linux and WSL2 | `test_declaration_support` (9), `test_profile_support` (46); run output in the session scratchpad |
| 2026-09-30 | Readiness round 1: red-team approved; lanes approved with an upstream measurement (22 failures in 6 of 8 sampled files; 7 doubles) showing declaration-machinery tests also need the helper; folded into Requirement 1; the run is under the default profile; dependency on `1zim1` declared | Prepare council and lane review |
| 2026-09-30 | Planned from the downstream note's test-suite section | Downstream report |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Separate from `1zim1` | Different mechanism (declarations, not record profile); shares the runner mode | Fold into `1zim1` |

## Risks

| Risk | Mitigation |
| --- | --- |
| A double that must stay minimal for speed | A shared FastMCP-backed double keeps it cheap |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
