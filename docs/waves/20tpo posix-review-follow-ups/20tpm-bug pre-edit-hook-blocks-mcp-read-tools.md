# Pre-edit hook gates read-only MCP tools that carry a path argument

Change ID: `20tpm-bug pre-edit-hook-blocks-mcp-read-tools`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-15
Wave: `20tpo posix-review-follow-ups`

## Rationale

The rendered Claude pre-edit hook (`claude_pre_edit_source` in `render_platform_surfaces.py`, registered on `PreToolUse` with no matcher) classifies tools by name. Edit tools are gated; `Read` and `Bash` pass; every other tool is "unfamiliar" and, by design, is not guessed about. But for an unfamiliar tool the hook still extracts any explicit path field it recognises (`tool_input.path` among them) and runs `gate_file_path` on it. The wavefoundry MCP read tools (`code_read`, `code_outline`, `code_definition` and the rest) pass their target as `path`, so a read of a framework file is blocked with "Broad framework-maintenance edits require guard-overrides" whenever no framework gate is open.

The effect is that the project's own agent guidance, which says to prefer the MCP code tools over shell reads, cannot be followed on framework files outside an open wave. Both review passes this month fell back to shell reads for that reason. The fail-closed stance for genuinely unknown tools is right; the defect is that known read-only tools are in the unknown set.

## Requirements

1. Reuse the existing stdlib-only `mcp_tool_roster.py` permission classification (`TIER_READ`) to derive exact canonical Wavefoundry tool names eligible for non-edit treatment. This is an observational permission contract: telemetry/accounting side effects are allowed. It is not a promise of no writes and does not use MCP `readOnlyHint`.
2. This first version exempts only canonical core read-tier names under the exact `mcp__wavefoundry__` namespace. Aliases, extensions, foreign namespaces and overridden core handlers remain gated; do not claim coverage for every read tool. Inspect the existing validated extension declaration to remove overridden core names from the exemption.
3. Missing, malformed or stale classification/declaration data grants no exemption. Unknown tools keep the current explicit-path check and compatibility warning. Never infer permission from a `code_` prefix or handler implementation.
4. Rendering uses the stdlib roster/declaration contracts, never imports or starts the MCP server or loads models. Regenerate the hook through the canonical renderer; no hand patch.
5. Prove the set excludes every write-tier tool and every overridden core name. Exercise the generated hook entry point with both admitted reads and refused counterparts.

## Scope

**Problem statement:** known observational core MCP calls are treated as unfamiliar edits.

**In scope:** `claude_pre_edit_source` in `.wavefoundry/framework/scripts/render_platform_surfaces.py`, the existing stdlib roster and validated extension declarations, generated hook and focused tests.

**Out of scope:** new permission registries, changing telemetry, server startup, prefix exemptions, exemptions for aliases/extensions, or relaxing unknown-tool checks.

## Acceptance Criteria

- [x] AC-1: Generated hook payloads for exact canonical core read-tier tools, including `mcp__wavefoundry__code_read`, pass with framework paths while edit guards remain closed; permission classification allows existing telemetry.
- [x] AC-2: Foreign/similarly prefixed tools, unknown names, aliases, extensions and overridden core read names remain gated; malformed/missing/stale contract data grants no exemption.
- [x] AC-3: Deriving the exemption from the existing validated roster excludes all write-tier tools; a deliberate writer misclassification is detected by the contract regression control.
- [x] AC-4: Canonical rendering regenerates `.claude/hooks/pre-edit.py` without importing the server or models; no hand edit is necessary.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Use the existing stdlib roster and validated override declarations to define the conservative core-name exemption.
- [x] Add generated-hook positive/negative controls, including stale/malformed contract data and overridden names.
- [x] Regenerate surfaces and verify no server/model import side effects.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Renderer and registry | Implementer | Readiness | Single write owner; `framework_edit_allowed` gate for the renderer |
| Delivery review | QA, security | Renderer and registry | Security: no write tool may enter the exempt set |

## Serialization Points

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/mcp_tool_roster.py` and extension declaration contract, only if needed to consume existing classification safely
- `.wavefoundry/framework/scripts/tests/`

The generated hook is updated through the renderer.

## Affected Architecture Docs

`docs/agents/platform-mapping.md` if it describes the pre-edit hook's tool classification; otherwise N/A.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The defect |
| AC-2 | required | Fail-closed stance must hold |
| AC-3 | required | No write tool exempted |
| AC-4 | required | Rendered surface, not hand-patched |
| AC-5 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned after both review passes hit the block | Hook output "COMPATIBILITY: unfamiliar tool mcp__wavefoundry__code_read ... BLOCKED" on a read with no gate open |

| 2026-10-15 | Readback: derive exact canonical core read-tier names from existing validated roster, excluding overrides/replacements/extensions/aliases. Embed source-contract hashes so stale/missing/malformed data grants no exemption; generated hook performs bounded nonblocking source checks without importing server/models. Unknown tools retain path gating. Before code_read is blocked like an edit; after a current qualified core read passes. | Current-source MCP reads and admitted ACs; material code waits for current readiness binding |

| 2026-10-15 | Implemented exact validated core read permissions and source-contract freshness checks, excluding overrides/replacements/aliases/extensions. Source identity bindings detect stale loaded permission modules without importing server/models. Four generated-hook tests pass; three mutants detect a writer misclassified as read, removed override exclusion and removed stale-contract check. Canonical wf_sync_surfaces regenerated only the Claude pre-edit hook. | test_core_read_hook; registered renderer output; cold-import trap |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Reuse observational read permission, not a new no-write registry | TPO-RD3: existing read tools intentionally emit telemetry; `TIER_READ` already models their permission | Handler-side-effect inference rejected |
| 2026-10-15 | Exempt only exact canonical core reads with no override | Small conservative first version; unknown/aliased/extension tools keep existing protection | Broad prefix or unvalidated extension inheritance rejected |

## Risks

| Risk | Mitigation |
| --- | --- |
| A core name is overridden by a writer | Remove overrides from exemption; invalid declaration grants no exemption |
| Generated classification becomes stale | Fail closed against current contract identity and regenerate; test stale input |
| Read telemetry is mistaken for edit authority | Document observational permission explicitly; no claim of pure handlers |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
