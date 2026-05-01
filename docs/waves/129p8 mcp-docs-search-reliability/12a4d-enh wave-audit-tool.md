# Wave Audit Tool

Change ID: `12a4d-enh wave-audit-tool`
Change Status: `complete`
Owner: implementer
Status: complete
Last verified: 2026-04-30
Wave: 129p8 mcp-docs-search-reliability

## Rationale

Agents recovering from uncertainty or arriving after a mutation have no single
read-only landing point that combines wave state, docs validation, and index
health into one call. They currently need to chain `wave_current` + `wave_validate`
+ `wave_index_health` manually. A dedicated `wave_audit` tool closes this gap:
one call, structured result, clear `next_tools` guidance — the preferred audit
landing point cited by diagnostics and the MCP spec.

## Requirements

1. `wave_audit` must accept an optional `wave_id: str = ""` parameter; when
   omitted it operates on the active wave (same discovery as `wave_current`).
2. `wave_audit` must aggregate three sub-results in its `data` payload:
   `wave` (current wave state), `validation` (docs-lint pass/fail + diagnostics),
   and `index` (semantic index health summary).
3. `wave_audit` must be read-only and safe to call at any time; it must not
   trigger writes, reindexes, or background refreshes.
4. `wave_audit` must return a top-level `ready` boolean that is `true` only when
   all three sub-checks pass: wave is **active or planned** (same discovery as
   `wave_current`), docs validation passes, and `semantic_ready` is `true`.
5. `wave_audit` must populate `next_tools` with specific recovery tools when any
   sub-check fails (e.g. `wave_validate` when lint fails, `wave_index_build`
   when index is non-ready).
6. `wave_audit` must be annotated as `readOnlyHint: true`, `destructiveHint: false`,
   `idempotentHint: true`, `openWorldHint: false`.
7. `wave_audit` must be added to the `wave_help` core-tools list and the
   `inspect_wave` workflow chain.
8. Tests must cover: healthy state (all pass), lint-fail path, index-absent path,
   no-active-wave path.

## Scope

**Problem statement:** There is no single MCP tool that gives an agent a complete
"am I in a good state to proceed?" answer. Agents have to issue three separate
calls and mentally merge the results, making recovery flows more brittle.

**In scope:**

- `wave_audit_response` function in `server.py`
- `wave_audit` tool registration with annotations and full docstring
- `wave_help` catalogue update (add `wave_audit` to `core_tools` and
  `inspect_wave` workflow)
- Tests in `test_server_tools.py`
- `docs/specs/mcp-tool-surface.md` spec entry

**Out of scope:**

- Surfacing `code_search` index health (code embeddings are optional; omit from
  audit to keep the signal clean)
- Writing or repairing anything (wave_audit is strictly read-only)
- Replacing `wave_current`, `wave_validate`, or `wave_index_health` — they remain
  individually callable

## Acceptance Criteria

- AC-1: `wave_audit()` returns `status: "ok"` with a `data` payload containing
  `wave`, `validation`, and `index` sub-objects plus a top-level `ready` boolean.
- AC-2: `ready` is `true` only when a wave is present (**active or planned** per
  `current_wave` semantics), validation passes (zero failures), and
  `semantic_ready` is `true`.
- AC-3: When docs-lint fails, `next_tools` includes `wave_validate`.
- AC-4: When index is non-ready, `next_tools` includes `wave_index_build`.
- AC-5: When no active wave is found, `data.wave` reflects the absent state
  and `ready` is `false`; tool does not raise an unhandled exception.
- AC-6: `wave_audit` appears in `wave_help` `core_tools` list.
- AC-7: `wave_audit` appears in the `inspect_wave` workflow chain.
- AC-8: `wave_audit` tool has `readOnlyHint: true` annotation.
- AC-9: Tests pass for all four paths (healthy, lint-fail, index-absent,
  no-active-wave); docs-lint clean.

**Contract note (healthy path):** When `ready` is `true`, the server still returns
`next_tools: ["wave_current"]` because the recovery list would otherwise be empty —
this is a **default navigation hint**, not a recovery action. Documented in
`docs/specs/mcp-tool-surface.md` § Audit.

## Tasks

- Implement `wave_audit_response(root, wave_id="", cache=None)` in `server.py`
- Register `wave_audit` tool with annotations, docstring, and `wave_id` param
- Update `_help_catalog` `core_tools` list and `inspect_wave` workflow
- Update `wave_index_health` recovery diagnostics to reference `wave_audit` as
  an alternative landing point
- Add tests in `test_server_tools.py` covering AC-1 through AC-5
- Update `docs/specs/mcp-tool-surface.md` with `wave_audit` entry
- Run tests + docs-lint

## Agent Execution Graph

| Workstream   | Owner       | Depends On | Notes                             |
|--------------|-------------|------------|-----------------------------------|
| server-impl  | implementer | —          | response function + tool reg      |
| catalog      | implementer | —          | wave_help + inspect_wave update   |
| tests        | implementer | server-impl| test_server_tools.py              |
| spec         | implementer | server-impl| mcp-tool-surface.md               |
| verification | implementer | all above  | tests + docs-lint                 |

## Serialization Points

- All changes land in `server.py` and `test_server_tools.py`; implement in a
  single sequential pass.

## Affected Architecture Docs

N/A — MCP surface addition confined to `server.py`; spec update to
`docs/specs/mcp-tool-surface.md` is handled as a task above.

## AC Priority

| AC   | Priority      | Rationale                                              |
|------|---------------|--------------------------------------------------------|
| AC-1 | required      | Core response shape                                    |
| AC-2 | required      | `ready` flag is the primary value of the tool          |
| AC-3 | required      | Recovery guidance on lint failure                      |
| AC-4 | required      | Recovery guidance on index failure                     |
| AC-5 | required      | Must not crash on no-wave state                        |
| AC-6 | important     | Discoverability via wave_help                          |
| AC-7 | important     | Workflow chain completeness                            |
| AC-8 | important     | MCP annotation contract compliance                     |
| AC-9 | required      | Verification gate                                      |

## Progress Log

| Date       | Update                          | Evidence |
|------------|---------------------------------|----------|
| 2026-04-30 | Created                         |          |
| 2026-04-30 | All 9 ACs implemented and verified | 309 tests pass; docs-lint clean |

## Decision Log

| Date       | Decision                              | Reason                            | Alternatives                     |
|------------|---------------------------------------|-----------------------------------|----------------------------------|
| 2026-04-30 | Exclude code index from audit scope   | Code embeddings are optional;     | Include with degraded-ok signal  |
|            |                                       | absence is normal, not a failure  |                                  |

## Risks

| Risk                                                   | Mitigation                                         |
|--------------------------------------------------------|----------------------------------------------------|
| wave_audit re-executes lint + health on every call     | Both are fast read-only checks; acceptable cost    |
| Aggregated payload is larger than individual tools     | Sub-objects are already returned by existing tools |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
