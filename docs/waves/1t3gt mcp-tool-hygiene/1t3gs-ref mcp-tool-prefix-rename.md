# MCP Tool Prefix Rename: wave_ → wf_ / memory_ / index_

Change ID: `1t3gs-ref mcp-tool-prefix-rename`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

Every non-framework MCP tool on this server currently starts with `wave_`, regardless of
whether it actually operates on a wave record (`wave_close`, `wave_create_wave`) or is a general
server/framework operation that happens to share the namespace (`wave_help`, `wave_gpu_doctor`,
`wave_dashboard_start`, `wave_index_build`, `wave_memory_add`, …). That collapses two different
concepts — "the Wave Framework product" and "a wave lifecycle record" — into one prefix, making
the tool surface harder to scan and reason about.

This change splits the namespace by what a tool actually operates on:

- `wf_` — the general product/server namespace (help, diagnostics, dashboard, index maintenance,
  docs validation, gates, upgrade, change-doc scaffolding, and the wave-lifecycle tools
  themselves, since a wave record IS a `wf_`-namespace concept, not a separate product).
- `memory_` and `index_` — dedicated subsystem namespaces, matching the existing `docs_`/`code_`/
  `seed_` precedent, for the two subsystems large and cohesive enough to warrant their own
  namespace (7 memory tools, 4 index tools).

Within `wf_`, tool names follow natural verb-first ordering (`wf_reopen_wave`, not
`wave_reopen`/`wf_wave_reopen`), with a disambiguating object noun added only where the bare verb
would be ambiguous (`wf_close_wave` vs. `wf_close_gate`), and omitted where the existing object is
already unambiguous (`wf_remove_change`, not `wf_remove_change_wave`). This also fixes several
tools that were already noun_verb order before this change (`wave_dashboard_start` →
`wf_start_dashboard`, `wave_gate_open` → `wf_open_gate`, `wave_mcp_reload` → `wf_reload_mcp`,
`wave_install_audit` → `wf_audit_install`).

## Requirements

1. `MCP_TOOL_PREFIXES` (`server_impl.py:213`) must become
   `("wf_", "memory_", "index_", "docs_", "code_", "seed_")` — `"wave_"` is dropped entirely
   since no tool uses it after this change.
2. All 47 tools listed in the rename table below must be renamed exactly as specified — MCP
   tool registration/function name, and every internal cross-reference to that name inside
   `server_impl.py`/`server.py` (`next_tools`, `usage`, `recovery_tools` hints, diagnostic/error
   message text, `_RELOAD_SURVIVOR_TOOLS`).
3. The 14 wave-lifecycle tools are included in this rename (all move to `wf_`, per the naming
   rule above); none remain `wave_`-prefixed. See table.
4. No tool's parameters, semantics, or response shape changes — this is a pure rename.
5. No backward-compatible alias/shim for old tool names — a clean rename, not a dual-naming
   transition period.
6. All tests asserting specific tool names (prefix-violation tests, tool-existence/tool-list
   tests, etc.) must be updated to the new names.
7. `AGENTS.md`'s "Available tools" list, `docs/specs/mcp-tool-surface.md`, seed prompts, and
   `docs/prompts/*.prompt.md` referencing specific tool names must reflect the new names.
8. Subagent tool allowlists (`.claude/agents/*.md` frontmatter `tools:` lists) and any other
   rendered platform surface enumerating individual `mcp__wavefoundry__wave_*` tool names must
   be updated to the new `mcp__wavefoundry__{wf_,memory_,index_}*` names.
9. Historical content — closed wave records under `docs/waves/`, journal entries under
   `docs/agents/journals/`, and Decision Log prose narrating past tool usage — must NOT be
   rewritten. Per this repo's Cleanup and Destructive Operations policy, those are point-in-time
   records, not live documentation.
10. A case-insensitive, repo-wide sweep for the old `wave_`-prefixed tool-name strings (excluding
    `docs/waves/` archives and `docs/agents/journals/`) must return zero hits after the change.

### Full rename table (61 live tools, 47 renamed)

**Wave-lifecycle tools → `wf_`, disambiguating noun added where the bare verb was ambiguous (14):**

| Old | New |
| --- | --- |
| `wave_current` | `wf_current_wave` |
| `wave_list_waves` | `wf_list_waves` |
| `wave_get_change` | `wf_get_change` |
| `wave_create_wave` | `wf_create_wave` |
| `wave_add_change` | `wf_add_change` |
| `wave_remove_change` | `wf_remove_change` |
| `wave_prepare` | `wf_prepare_wave` |
| `wave_pause` | `wf_pause_wave` |
| `wave_review` | `wf_review_wave` |
| `wave_record_review_evidence` | `wf_review_evidence` |
| `wave_context_efficiency_attach_evaluation` | `wf_context_efficiency_eval` |
| `wave_implement` | `wf_implement_wave` |
| `wave_reopen` | `wf_reopen_wave` |
| `wave_close` | `wf_close_wave` |

**Memory subsystem → `memory_` (7):**

| Old | New |
| --- | --- |
| `wave_memory_add` | `memory_add` |
| `wave_memory_propose` | `memory_propose` |
| `wave_memory_backfill` | `memory_backfill` |
| `wave_memory_validate` | `memory_validate` |
| `wave_memory_search` | `memory_search` |
| `wave_memory_brief` | `memory_brief` |
| `wave_memory_reconcile` | `memory_reconcile` |

**Index subsystem → `index_` (4):**

| Old | New |
| --- | --- |
| `wave_index_health` | `index_health` |
| `wave_index_build` | `index_build` |
| `wave_index_optimize` | `index_optimize` |
| `wave_index_build_status` | `index_build_status` |

**General framework/server tools → `wf_`, verb-first order (36):**

| Old | New |
| --- | --- |
| `wave_help` | `wf_help` |
| `wave_server_info` | `wf_server_info` |
| `wave_gpu_doctor` | `wf_gpu_doctor` |
| `wave_mcp_reload` | `wf_reload_mcp` |
| `wave_dashboard_start` | `wf_start_dashboard` |
| `wave_dashboard_open` | `wf_open_dashboard` |
| `wave_dashboard_stop` | `wf_stop_dashboard` |
| `wave_dashboard_restart` | `wf_restart_dashboard` |
| `wave_upgrade` | `wf_upgrade` |
| `wave_upgrade_status` | `wf_upgrade_status` |
| `wave_validate` | `wf_validate_docs` |
| `wave_garden` | `wf_garden_docs` |
| `wave_sync_surfaces` | `wf_sync_surfaces` |
| `wave_gate_open` | `wf_open_gate` |
| `wave_gate_close` | `wf_close_gate` |
| `wave_gate_status` | `wf_gate_status` |
| `wave_map` | `wf_map` |
| `wave_get_prompt` | `wf_get_prompt` |
| `wave_get_handoff` | `wf_get_handoff` |
| `wave_set_handoff` | `wf_set_handoff` |
| `wave_audit` | `wf_audit` |
| `wave_list_plans` | `wf_list_plans` |
| `wave_graph_report` | `wf_graph_report` |
| `wave_install_audit` | `wf_audit_install` |
| `wave_run_sensors` | `wf_run_sensors` |
| `wave_scan_secrets` | `wf_scan_secrets` |
| `wave_new_feature` | `wf_new_feature` |
| `wave_new_bug` | `wf_new_bug` |
| `wave_new_enhancement` | `wf_new_enhancement` |
| `wave_new_refactor` | `wf_new_refactor` |
| `wave_new_change` | `wf_new_change` |
| `wave_new_documentation` | `wf_new_documentation` |
| `wave_new_tech_debt` | `wf_new_tech_debt` |
| `wave_new_task` | `wf_new_task` |
| `wave_new_maintenance` | `wf_new_maintenance` |
| `wave_new_operations` | `wf_new_operations` |

## Scope

**Problem statement:** The `wave_` prefix conflates "the Wavefoundry product/server surface"
with "a wave lifecycle record," and several tool names read backwards (noun before verb). This
splits the namespace by subsystem and applies consistent verb-first naming throughout.

**In scope:**

- `MCP_TOOL_PREFIXES` update in `server_impl.py`
- All 47 tool renames (registration + internal cross-references) across `server_impl.py` and
  `server.py`, including `_RELOAD_SURVIVOR_TOOLS`
- Tests asserting tool names
- `AGENTS.md`, `docs/specs/mcp-tool-surface.md`, seed prompts, `docs/prompts/*.prompt.md`
- Subagent tool allowlists (`.claude/agents/*.md`) and other rendered platform surfaces that
  enumerate individual tool names

**Out of scope:**

- The sibling root-discovery unification tech debt flagged in `1t1b3-bug
  memory-cli-root-default-cwd-not-repo` — unrelated subsystem, tracked separately
- Any backward-compatible alias/shim for old tool names
- Any behavior, parameter, or response-shape change to any tool — pure rename
- Rewriting historical content under `docs/waves/` archives or `docs/agents/journals/`

## Acceptance Criteria

- [x] AC-1: `MCP_TOOL_PREFIXES == ("wf_", "memory_", "index_", "docs_", "code_", "seed_")` and
      `first_party_tool_names_violating_prefix()` passes for the full live tool set.
- [x] AC-2: All 47 renamed tools exist under their new name; none of the old `wave_`-prefixed
      names for these 47 remain registered as MCP tools.
- [x] AC-3: The 14 wave-lifecycle tools appear correctly under their new names (full table above).
- [x] AC-4: Full framework test suite passes
      (`python3 .wavefoundry/framework/scripts/run_tests.py`).
- [x] AC-5: Case-insensitive repo-wide grep for old tool-name strings returns zero hits,
      excluding only historical archives (`docs/waves/`, `docs/agents/journals/`, closed-wave
      Decision Log prose). The sweep explicitly includes `docs/workflow-config.json` (notes
      field), rendered hook bodies (`.claude/hooks/pre-edit.py`, `post-edit.py`), and
      `docs/agents/memory/README.md`, all verified at prepare time to carry old-name
      references. (`.claude/agents/*.md` allowlists were verified clean at prepare time; the
      repo-wide sweep still covers them.)
- [x] AC-6: `wf_reload_mcp()` confirms the server's live tool list matches the new names without
      a full process restart.
- [x] AC-7: `AGENTS.md` and `docs/specs/mcp-tool-surface.md` pass docs-lint (`wave_validate`).

## Tasks

- [x] Update `MCP_TOOL_PREFIXES` in `server_impl.py:213`
- [x] Rename all 14 wave-lifecycle tool functions/registrations
- [x] Rename all 7 `memory_*` tool functions/registrations
- [x] Rename all 4 `index_*` tool functions/registrations
- [x] Rename all 36 remaining general `wf_*` tool functions/registrations, including
      `wave_mcp_reload` → `wf_reload_mcp` and `_RELOAD_SURVIVOR_TOOLS` in `server.py`
- [x] Sweep `server_impl.py`/`server.py` for internal string references to old names
      (`next_tools`, `usage`, `recovery_tools`, diagnostic/error text) and update
- [x] Update all affected tests (`test_server_tools.py`, `test_build_pack.py`,
      `test_memory_backfill.py`, and any others found during the sweep)
- [x] Update `AGENTS.md` tool list and `docs/specs/mcp-tool-surface.md`
- [x] Update seed prompts and `docs/prompts/*.prompt.md` referencing specific tool names
- [x] Update subagent tool allowlists under `.claude/agents/*.md` and any other rendered
      platform surfaces enumerating tool names
- [x] Run case-insensitive grep sweep confirming no live-surface references to old names remain
- [x] Run full framework test suite
- [x] Reload the MCP server, verify the new tool set live, and note in session handoff that
      existing agent sessions need to reconnect to pick up the new names

## Agent Execution Graph


| Workstream        | Owner       | Depends On     | Notes |
| ------------------ | ----------- | -------------- | ----- |
| code-rename         | Engineering | —              | Single coordinated pass over server_impl.py/server.py + tests — one shared file, no parallel split |
| docs-and-surfaces   | Engineering | code-rename    | AGENTS.md, mcp-tool-surface.md, seeds, prompt docs, subagent allowlists — follows the finalized names, not run concurrently against a moving target |


## Serialization Points

- `server_impl.py` and `server.py` are single shared files carrying most of the 47 renames plus
  dozens of internal cross-references — this must land as one coordinated pass, not split across
  parallel editors, to avoid merge conflicts and partial renames.
- Docs/seed/allowlist updates should follow the finalized code rename, not run concurrently
  against it.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` (the canonical tool reference) requires a full update — tracked
under Tasks. `N/A` for the `docs/architecture/*.md` hub docs and `docs/ARCHITECTURE.md` — this is
a pure rename with no structural, boundary, or data-flow change.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The prefix invariant is the enforced startup guard; wrong prefixes fail server boot |
| AC-2 | required  | Partial renames would leave a split-brain tool surface — old and new names coexisting is worse than either state |
| AC-3 | required  | The lifecycle table is the operator-approved naming decision; deviation is silent scope drift |
| AC-4 | required  | Suite-green is the delivery gate for all framework script changes |
| AC-5 | required  | The grep sweep is the only mechanism that catches missed references in prose hints, seeds, and rendered surfaces — without it AC-2 is unverifiable at scale |
| AC-6 | important | Live-reload verification proves the rename works end-to-end, but a full server restart achieves the same confidence if reload misbehaves |
| AC-7 | required  | Docs-lint clean is the standing docs gate |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-20 | Council readiness fix: AC-5 sweep scope aligned to Requirement 10 (repo-wide minus historical archives); named surfaces corrected after code-grounded verification found `workflow-config.json`, rendered hooks, and the memory README carry old-name references while `.claude/agents` allowlists do not. | Prepare-council finding (architecture-reviewer, moderate): directory-allowlist AC-5 contradicted the repo-wide Requirement 10 and would miss real references. | Keep the allowlist AC (rejected: unverifiable completeness); add a shim/alias period (rejected at council: alias machinery cost exceeds benefit for a local-only tool surface). |
| 2026-07-20 | Implementer must re-derive the live `@mcp.tool` registration list and diff it against this doc's rename table before editing. | A stale session listing already produced one phantom tool (`wave_setup_resume_after_memory`); the table is a snapshot, the registration set is the authority. | Trust the table as written (rejected: known-stale-source incident this same planning session). |
| 2026-07-20 | AC-6 verification: fresh-process `tools/list` probe confirms 83 tools, zero `wave_`-prefixed (50 `wf_`, 7 `memory_`, 4 `index_`, plus docs/code/seed), all renamed tools present. Known one-time caveat: in-session hot reload cannot rename the reload-survivor tool itself — the old process's in-memory `wave_mcp_reload` trips the new prefix guard, so THIS rename requires one host reconnect (already a wave watchpoint). Future reloads are unaffected (`wf_reload_mcp` is the survivor from now on). | Renaming the tool that performs hot reload is inherently a process-restart boundary; verified via MCP stdio client against a fresh `server.py` rather than the degraded live session. | Exempt the survivor from the prefix guard (rejected: permanent hole in the invariant for a one-time transition). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A less-common rendered platform surface (Codex `config.toml`, Windsurf, Antigravity, etc.) enumerates individual tool names and gets missed | Repo-wide case-insensitive grep sweep (AC-5) before closing, not limited to the primary files |
| Other live agent sessions using old tool names error out until they reconnect | Expected, existing MCP hot-reload behavior (new/renamed tools require reconnect, as just observed in this session); documented in session handoff and confirmed via AC-6 |
| Large mechanical rename is error-prone (typos, partial renames, missed cross-references) | Single coordinated pass (see Serialization Points) plus automated grep verification (AC-5) and full test suite (AC-4) rather than manual per-file editing without a final sweep |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
