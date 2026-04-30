# MCP Guided Tool Contracts

Change ID: `12993-feat mcp-guided-tool-contracts`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-04-30
Wave: `1293d mcp-server-foundation`

## Rationale

The initial Wavefoundry MCP server exposes useful capabilities, but its current tool
surface still expects agents to infer workflow from tool names and prose descriptions.
That is fragile as the surface grows. External MCP implementation experience confirms
that reliable agents need a small guided core, structured discovery, stable identifiers,
safe retry behavior, and response breadcrumbs that make the next call obvious.

This change improves the MCP contract so Wavefoundry can scale past a basic tool list
without making agents guess.

## Requirements

1. The MCP server exposes a structured discovery tool, tentatively `wave_help(goal="")`,
  that returns supported workflows, recommended tool chains, fallbacks, and an exact
   next-call hint.
2. Tool responses use a consistent machine-readable envelope with `status`, `data`,
  `diagnostics`, `next_tools`, and `usage` fields where practical.
3. Search, inspection, creation, validation, gardening, and surface-sync tools include
  forward breadcrumbs so the next likely tool call is explicit.
4. Mutating tools support a non-writing dry-run mode before or alongside write mode.
5. Change creation is consolidated behind a core tool that accepts a `kind` enum and
  `mode` enum while preserving existing `wave_new_*` wrappers for compatibility.
6. Search results and read-oriented tools return stable result identifiers or anchors
  that later tools can accept as inputs, instead of requiring agents to describe prior
   results in natural language.
7. Tool descriptions and, where supported by the MCP SDK, tool annotations distinguish
  read-only, mutating, and potentially destructive operations.
8. Unknown or unsupported discovery goals return the supported catalogue rather than a
  dead-end error.
9. The server enforces configured allowed roots before exposing generic file reads or
  project navigation tools.
10. Search results and repository file content are labeled as untrusted project content
  unless they come from trusted framework metadata or explicitly trusted docs.
11. The server defines five to ten documented core verbs in MCP server instructions or
  the closest supported local equivalent, and classifies extra tools as compatibility,
    fallback, diagnostic, or expert tools.
12. Tool names keep consistent prefixes by surface (`wave_*`, `docs_*`, `code_*`,
  `seed_*`) and route normal workflows through the documented core verbs.
13. The server provides a map/anchors tool, or equivalent anchor-bearing read/search
  output, so follow-up calls can refer to stable addresses rather than line offsets or
    natural-language descriptions.
14. Diagnostic fields use stable names across tools and explicitly cite recovery tools.
15. Mutation tools use consistent argument names, mode semantics, envelope fields, and
  retry/idempotency behavior.
16. Tool schemas reject unknown arguments where the Python MCP runtime permits it; where
  the runtime cannot enforce strictness, server-side validation returns a diagnostic
    error with the supported schema.
17. The MCP surface includes an audit landing tool or clearly designates existing audit
  tools so agents have a reliable recovery target after mutation or uncertainty.
18. Frequently repeated recovery-loop data is cached per server process when safe,
  especially discovery catalogues, wave summaries, prompt resolution metadata, and
    index metadata.
19. Repeat calls to mutating tools are safe or explicitly diagnosed with the existing
  artifact/path and the recommended next recovery tool.
20. The implementation is covered by tests that assert the response envelope shape,
  discovery output, dry-run behavior, compatibility wrappers, and root-safety checks.

## Scope

**Problem statement:** The current MCP server is useful but too dependent on agent
initiative. As the tool surface grows, models can pick less appropriate tools, stop
after one call, retry unsafe mutations, or lose references between calls.

**In scope:**

- Add `wave_help(goal="")` or equivalent structured discovery entry point
- Define the five to ten core verbs in server instructions or a local equivalent
- Add a shared response envelope helper for MCP tools
- Add `next_tools` and `usage` breadcrumbs to all first-party tool responses
- Add dry-run support to change creation and framework operation tools where practical
- Add consolidated `wave_change_create(kind, slug, mode)` while retaining wrappers
- Add stable IDs/anchors to search results and future read/navigation outputs, plus a
map/anchors helper if follow-up addressing needs a separate tool
- Add tool metadata/annotations if supported by the Python MCP runtime in use
- Add allowed-root validation ahead of generic file-read/navigation tools
- Add untrusted-content labeling for indexed project content
- Add strict schema validation where runtime support exists, with explicit diagnostics
where it does not
- Add or designate an audit landing tool for recovery after uncertain or mutating calls
- Add safe per-process caching for repeated discovery, audit, prompt, and wave-summary
lookups
- Update tests and architecture docs for the revised MCP contract
- Update agent-facing docs and seeds so instructions prefer the guided core tools

**Out of scope:**

- Full wave lifecycle mutation tools (`wave_create`, `wave_add_change`, prepare/review/close)
- Remote MCP deployment or authentication
- Replacing semantic search models or index file format
- IDE-specific UI affordances beyond generated MCP registration files
- Removing existing compatibility tools in this wave

## Acceptance Criteria

- AC-1: `wave_help()` returns a structured catalogue of supported workflows and
core tools without requiring external documentation.
- AC-2: `wave_help(goal="plan_feature")` returns a recommended chain that starts
with change creation and includes exact next-call usage strings.
- AC-3: Each MCP tool returns or can be adapted to a standard envelope containing
`status`, `data`, `diagnostics`, `next_tools`, and `usage`.
- AC-4: `wave_change_create(kind="feat", slug="example", mode="dry_run")` reports
the planned ID/path without writing a file.
- AC-5: `wave_change_create(kind="feat", slug="example", mode="create")` writes
the plan once, reports the path and ID, and handles repeat calls predictably.
- AC-6: Existing `wave_new_feature`, `wave_new_bug`, and related wrappers continue
to work and delegate to the consolidated creation path.
- AC-7: Search results include stable result IDs or anchors suitable for follow-up
reads or references.
- AC-8: Read-only and mutating tools are distinguishable through descriptions and
annotations where the MCP runtime supports them.
- AC-9: Generic file navigation/read tools reject paths outside configured allowed
roots before reading content.
- AC-10: Indexed project content returned by MCP is labeled as untrusted content;
trusted framework metadata remains distinguishable.
- AC-11: Tests cover discovery, response envelopes, dry-run mode, wrapper
compatibility, stable anchors, and allowed-root rejection.
- AC-12: Architecture docs describe the guided MCP contract and response envelope.
- AC-13: The server instruction surface or local equivalent names five to ten core
verbs and classifies non-core tools as compatibility, fallback, diagnostic, or expert.
- AC-14: Tool names conform to the documented prefix scheme by surface, and tests
fail if new first-party tools violate it.
- AC-15: A map/anchors path exists so a result from search/inspect can be used as a
stable follow-up address without natural-language restatement.
- AC-16: Diagnostic fields have stable names and cite recovery tools in failed or
partial-success responses.
- AC-17: Mutating tools share the same mode enum semantics and mutation envelope
fields.
- AC-18: Unknown arguments are rejected strictly or diagnosed consistently with the
supported schema.
- AC-19: An audit landing tool is available and referenced by mutating and recovery
responses.
- AC-20: Repeated recovery-loop calls use safe cache paths where appropriate and can
be invalidated when underlying files change.
- AC-21: Repeat calls to mutating tools are safe or return a predictable diagnostic
that includes the existing artifact and next recovery tool.

## Tasks

- Define the guided MCP response envelope and helper functions in `server.py`.
- Implement `wave_help(goal="")` with workflow catalogue and goal-specific chains.
- Define the core-verb set and expose it via MCP server instructions or `wave_help`
when direct server instructions are not supported by the runtime.
- Add prefix-scheme checks for first-party MCP tools. *(landed 2026-04-29)*
- Add `next_tools`, `usage`, and diagnostics to search, wave inspection, change
creation, validation, gardening, and surface-sync responses.
- Standardize named diagnostic fields and recovery-tool references.
- Implement consolidated `wave_change_create(kind, slug, mode)` and migrate
`wave_new_`* wrappers onto it.
- Add dry-run behavior for mutating tools and document retry/idempotency semantics.
- Add stable search result IDs/anchors and preserve enough metadata for follow-up
reads.
- Add a map/anchors helper if stable addressing cannot be covered cleanly by search
and read responses alone. *(landed 2026-04-29: `wave_map`)*
- Add allowed-root validation utilities before adding broad file navigation tools. *(landed 2026-04-29: `resolve_path_under_root`)*
- Add untrusted-content labels to project search/read results.
- Add strict argument validation or server-side unknown-argument diagnostics. *(landed 2026-04-29: `docs_search` kind, non-empty slug, `apply`→`create`; 2026-04-29: `**kwargs` rejection on all MCP tool handlers when extras are forwarded)*
- Add or designate an audit landing tool and cite it from mutation/recovery outputs.
- Add safe per-process caching for discovery catalogues, wave summaries, prompt
resolution, and index metadata. *(landed 2026-04-29: `wave_help` LRU snapshot, `McpRepoCache` for wave/plan lists and prompt text keyed by `docs/prompts/*.md` mtimes, index `_loaded` reset on mutation)*
- Add or update MCP tool contract tests.
- Update architecture docs and agent-facing prompt/seed guidance.
- Run `python3 .wavefoundry/framework/scripts/run_tests.py`.
- Run `python3 .wavefoundry/framework/scripts/docs_lint.py`.

## Agent Execution Graph


| Workstream                     | Owner                 | Depends On                            | Notes                                          |
| ------------------------------ | --------------------- | ------------------------------------- | ---------------------------------------------- |
| Contract design                | architecture-reviewer | —                                     | Envelope, discovery, annotations, trust labels |
| Core verb and discovery design | factor-13-api-first   | Contract design                       | Core verbs, prefixes, browseable catalogue     |
| Server implementation          | implementer           | Contract design                       | `server.py` tools and helpers                  |
| Test coverage                  | code-reviewer         | Server implementation                 | Contract and compatibility tests               |
| Docs and seeds                 | implementer           | Contract design                       | Agent guidance must prefer guided tools        |
| Acceptance review              | framework-operator    | Server implementation, Docs and seeds | Validate actual agent ergonomics               |


## Serialization Points

- `.wavefoundry/framework/scripts/server.py` response shape is a shared contract; finish
envelope design before broad tool edits.
- The core verb list and prefix taxonomy must be decided before changing prompt/seed
guidance.
- Prompt and seed edits must wait until tool names and response fields are stable.
- Compatibility wrapper behavior must be reviewed before changing agent-facing docs.

## Affected Architecture Docs

- `docs/architecture/current-state.md`
- `docs/architecture/data-and-control-flow.md`
- `docs/architecture/cross-cutting-concerns.md`
- Potentially `docs/architecture/decisions/*` if the response envelope becomes a
durable MCP contract decision

## AC Priority

(Populated at Prepare wave.)


| AC    | Priority  | Rationale                                                      |
| ----- | --------- | -------------------------------------------------------------- |
| AC-1  | required  | Discovery is the entry point for guided tool use.              |
| AC-2  | required  | Goal-specific chains remove ambiguity from common workflows.   |
| AC-3  | required  | Standard envelopes are the foundation for reliable chaining.   |
| AC-4  | required  | Dry-run mode is required before safe mutation guidance.        |
| AC-5  | required  | Create mode must remain useful and retry-safe.                 |
| AC-6  | required  | Existing tool users must not break.                            |
| AC-7  | important | Stable anchors improve chaining and future read tools.         |
| AC-8  | important | Tool metadata improves safety on clients that support it.      |
| AC-9  | required  | Generic navigation tools require root safety.                  |
| AC-10 | required  | Project content must not become hidden instructions.           |
| AC-11 | required  | Contract behavior needs regression coverage.                   |
| AC-12 | important | Architecture docs need to reflect the new MCP contract.        |
| AC-13 | required  | Agents need an explicit recommended core path.                 |
| AC-14 | required  | Prefix consistency is part of the chaining contract.           |
| AC-15 | required  | Stable anchors prevent lossy follow-up calls.                  |
| AC-16 | required  | Diagnostics need predictable recovery paths.                   |
| AC-17 | required  | Mutation semantics must be consistent across tools.            |
| AC-18 | required  | Unknown arguments should not be silently ignored.              |
| AC-19 | required  | Agents need a reliable audit/recovery landing point.           |
| AC-20 | important | Recovery loops will repeat calls; cache avoids avoidable cost. |
| AC-21 | required  | Retry-safe mutation behavior is central to agent reliability.  |


## Progress Log


| Date       | Update                                                                                                                                                                                                                                                                        | Evidence                                                                                                     |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| 2026-04-30 | Planned change from MCP best-practices review and admitted to current wave.                                                                                                                                                                                                   | `docs/waves/1293d mcp-server-foundation/12993-feat mcp-guided-tool-contracts.md`                             |
| 2026-04-30 | Expanded plan against the MCP design checklist: core verbs, prefixes, anchors, diagnostics, audit, caching, and retry safety.                                                                                                                                                 | Requirements 11-20 and AC-13 through AC-21                                                                   |
| 2026-04-30 | Created formal MCP tool surface spec prerequisite.                                                                                                                                                                                                                            | `docs/specs/mcp-tool-surface.md`                                                                             |
| 2026-04-30 | Thought: execute the MCP contract foundation slice first: structured envelopes, discovery, consolidated change creation, and wrapper delegation.                                                                                                                              | Implement wave kickoff after clean Prepare pass                                                              |
| 2026-04-30 | Observe: foundational MCP contract slice landed in `server.py` and focused server tests passed.                                                                                                                                                                               | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_server_tools.py'`          |
| 2026-04-30 | Reflect: the baseline MCP index feature is now marked complete, allowing the guided-contract change to move into active implementation. Remaining work is a follow-on slice for prefix enforcement, allowed-root validation, stricter argument handling, and cache semantics. | `python3 .wavefoundry/framework/scripts/run_tests.py`; `python3 .wavefoundry/framework/scripts/docs_lint.py` |
| 2026-04-29 | Observe: second contract slice — tool prefix enforcement at `build_server` registration, `resolve_path_under_root`, strict `docs_search` kind + slug/mode normalization (`apply`→`create`), `McpRepoCache` for wave/plan lists with mtime fingerprints, mutation invalidation (including `WaveIndex` reload), and `wave_help` catalogue LRU snapshot. | `python3 .wavefoundry/framework/scripts/run_tests.py`                                                                                              |
| 2026-04-29 | Observe: third slice — `wave_map` anchor resolver, prompt-resolution cache on `McpRepoCache`, `_registered_mcp_tool_names` for FastMCP `_tool_manager`, and `**kwargs` guards on every MCP tool for unknown-argument diagnostics. | `python3 .wavefoundry/framework/scripts/run_tests.py`                                                                                              |


## Decision Log


| Date       | Decision                                                                                                                                 | Reason                                                                                                      | Alternatives                                                    |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| 2026-04-30 | Keep existing `wave_new_*` tools as compatibility wrappers while adding a consolidated core creation tool.                               | Reduces tool-choice ambiguity without breaking current instructions or clients.                             | Remove wrappers immediately; leave all creation tools separate. |
| 2026-04-30 | Treat project search/read content as untrusted unless explicitly labeled trusted.                                                        | Indexed repo content can contain prompt-like text and should not silently become instruction context.       | Trust all indexed docs equally.                                 |
| 2026-04-30 | Make `wave_help` the local equivalent of `get_instructions()` if the Python MCP runtime does not expose first-class server instructions. | The checklist requires an explicit recommended path; runtime support should not block the product behavior. | Rely only on tool descriptions or AGENTS.md.                    |


## Risks


| Risk                                                                                  | Mitigation                                                                                                                        |
| ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Envelope migration breaks clients expecting string responses.                         | Preserve compatibility wrappers or return JSON-compatible strings only after client behavior is verified.                         |
| Tool surface grows while trying to simplify it.                                       | Make `wave_help` and consolidated core verbs the documented path; classify wrappers as compatibility tools.                       |
| Dry-run semantics are inconsistent across tools.                                      | Define mode enum behavior centrally and test each mutating tool.                                                                  |
| Trust labeling is ignored by agents.                                                  | Put trust labels in structured fields and human-readable excerpts.                                                                |
| Runtime cannot reject unknown arguments before tool dispatch.                         | Add server-side schema validation and return structured diagnostics with supported fields.                                        |
| Cached recovery data becomes stale after edits.                                       | Include file mtimes/hashes in cache keys or invalidate caches after mutation tools run.                                           |
| Formal MCP tool surface spec can drift from implementation during contract migration. | Keep `docs/specs/mcp-tool-surface.md` aligned during delivery and include docs-contract-reviewer sign-off before readiness/merge. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.