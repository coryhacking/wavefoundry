# Allow nonconflicting wf-prefixed extension skills

Change ID: `22oay-bug extension-skill-name-collisions`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-11-05
Wave: 22ob1 distribution-integration-followups

## Rationale

The operator reports Waveforge used wfs- names because wf- was rejected even when no complete skill name collided. Source confirms skill_declaration_problems rejects every wf- prefix. Declared-skill orphan discovery also skips every wf- folder, so removing validation alone would leave newly permitted extension orphans outside normal cleanup. MCP extension guidance already allows a shared core prefix and recommends a distribution-specific prefix to reduce future name collisions; skill guidance should follow that policy. No exact rejected field names were supplied; test names must be labelled synthetic.

## Product Intent

A downstream fork can add a nonconflicting wf- skill without a forced alternate prefix, while core skills, extension skills and handwritten local files remain distinct and protected. AC-1 through AC-3 exercise naming, rendering and cleanup. The downstream project will rename its own wfs-* declarations and references to wf-*; this framework change enables that work and does not perform it.

## Requirements

1. Replace blanket prefix reservation with complete-name collision checks against the effective core registry and explicitly retired managed names. Include configured core-name overrides and doc-gated core skills even when their backing prompt is absent. Respect existing syntax and case-insensitive destination collision rules.
2. Reuse authoritative core-name information without introducing a renderer/declaration import cycle. Preserve the declaration module's stdlib-only boundary. Keep skill validation outside fatal MCP tool declaration validation.
3. Diagnose the actual conflicting full name before any render writes or removals. A later upgrade introducing a colliding core name must refuse safely rather than overwrite a distribution skill.
4. Treat extension ownership through the existing declared-skill marker and verified paths, irrespective of prefix. Re-render and removal of a declared wf- skill must follow the same ownership checks as other extension skills. Do not infer ownership or delete a handwritten skill from its prefix alone.
5. Preserve contained, link-safe preflight across active Codex, Claude and agent skill hosts, thin-pointer bodies, eligibility rules, manual-only policy and core retirement behavior. Existing wfs- declarations remain valid until the downstream project changes them; no automatic rename, alias or migration system is added.
6. Align skill namespace guidance with MCP tools: a distribution-specific prefix is recommended to reduce future collisions, but sharing wf- is allowed. Explain full-name conflicts, intentionally reserved retired names and safe refusal if a later core release introduces a collision. This does not add MCP-style override or alias mechanisms to skills.

## Scope

In scope: mcp_tool_extensions.py skill validation, render_agent_surfaces.py naming/preflight/orphan handling, declared-extension-skill tests and published extension guidance. Out of scope: changing MCP tool namespaces, shortening core names, performing the downstream project's wfs-* to wf-* rename, unrestricted overriding of core skills or regenerating unrelated local surfaces during planning.

## Acceptance Criteria

- [x] AC-1: A synthetic valid noncolliding wf- declaration validates and renders on every active skill host. Core/retired/configured-name collisions are diagnosed before mutation, including a doc-gated core entry and an upgrade-introduced conflict.
- [x] AC-2: Re-rendering and removing that extension follow marker-based ownership and contained cleanup; unmarked local files, linked paths and unrelated custom wf- skills remain protected.
- [x] AC-3: Existing wfs- declarations, standard core skills, retirement cleanup and eligibility/manual-only rules retain behavior. Documentation explicitly allows downstream wf- skills, recommends rather than requires a distribution prefix, and explains real-name collisions and downstream ownership of any rename.

## Tasks

- [x] Exercise the rejected-prefix case and identify effective/retired name owners.
- [x] Implement exact collision checks and prefix-independent declared cleanup.
- [x] Test both renderer entry points, all active host shapes and refusal with no writes; update the extension contract.

## Agent Execution Graph

One coordinated stream owns validation and rendering. Review cleanup and naming together; neither half is sufficient alone.

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_declared_extension_skills.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/current-state.md`
- `docs/architecture/layering-rules.md`

CHANGELOG.md records the compatibility change. Reviewers read; the readied implementation owns source edits.

## Affected Architecture Docs

Update current-state.md and layering-rules.md for the source of collision information, maintaining the one-way declaration/renderer dependency.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Solves the reported namespace restriction. |
| AC-2 | required | Prevents prefix-based ownership mistakes. |
| AC-3 | required | Preserves existing installations. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-05 | Reserve conflicting complete names, with verified ownership for cleanup. | A shared prefix is not a destination collision; marker-based ownership already distinguishes declared skills. | Keeping wfs- mandatory preserves the restriction; deleting the prefix check alone leaves cleanup inconsistent. |
| 2026-11-05 | Match MCP's prefix guidance; leave downstream renames to the downstream project. | The operator clarified that framework support for new wf- skills is the required change. | A new namespace/alias system or framework-driven bulk rename adds unnecessary scope. |

## Risks

Configured names and retired aliases can conflict even when a default registry name does not. Test the effective names and preserve refusal before writes; do not promise unrestricted wf- naming.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-05 | Implemented contextual effective/retired full-name collision checks and marker-owned cleanup for wf-prefixed extensions. All-host render/rerender/remove and no-write collision controls pass; named collision/orphan mutants detected. Downstream owns renames; no alias/override system. | delivery-evidence.json; named production tests and guard mutants; full canonical qualification and independent delivery review pending. |
| 2026-11-05 | Readback: allow new nonconflicting downstream wf-prefixed declarations, reject actual effective/retired names before mutation and clean marked extensions independently of prefix. AC-1–3; implementer owns declaration/renderer and declared-skill tests. Downstream owns renames; no alias or namespace system, no prefix-based ownership. | Current receipt review-policy-9f3ca64efa19fe8cfee4; Implement wave activation succeeded. |
| 2026-11-05 | Planned from operator feedback and current validation/renderer reads; field names and an end-to-end reproduction remain unavailable. | mcp_tool_extensions.py skill_declaration_problems; render_agent_surfaces.py declared_skill_problems and _declared_skill_orphans. |
| 2026-11-05 | Clarified shared-prefix support and optional prefix advice; downstream owns its wfs-* to wf-* rename. Still planning only. | Operator direction; MCP prefix guidance in mcp_tool_extensions.py and docs/specs/mcp-tool-surface.md. |
| 2026-11-05 | Final delivery passed: canonical suite 12,369 tests / 217 files / 12 reported skips; full docs validation and independent required lanes plus Council approve. Four supporting test-fixture repairs were independently verified in cycle 1; no product repair or scope change was needed. | delivery-evidence.json and typed events.jsonl; current receipt 92ad0645. Wave remains open for operator signoff. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
