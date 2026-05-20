# Factor Agents Live in the Shared Agent Taxonomy

Change ID: `12rpn-enh factor-agents-shared-taxonomy`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-20
Wave: `12rnv agent-prompt-harness`

## Rationale

Factor agents are currently modeled as a separate dashboard surface that lives only in `.claude/agents/`, which makes them look like a host-specific implementation detail instead of part of the shared agent taxonomy. That is the wrong source-of-truth boundary.

This change makes factor agents first-class shared agent docs at the root of `docs/agents/` as `factor-*.md`, while keeping `.claude/agents/` as a pointer/wrapper surface for native host integration.

This change must also propagate through the framework seed prompts and platform-surface generation so the canonical factor docs are broadly implemented rather than only moved in the local repo.

The goal is to make the taxonomy consistent:

- canonical agent content lives with the other agent docs
- host-specific agent entrypoints can still point at the canonical docs
- the dashboard should continue to render a distinct `Factor` group, but it should source those entries from the shared agent surface

## Requirements

1. Define a canonical home for factor agents under `docs/agents/` so they live alongside the rest of the shared agent taxonomy.
2. Preserve the `factor-` filename prefix for all factor agent docs.
3. Keep `.claude/agents/` as a pointer or wrapper surface that references the canonical factor docs rather than owning the content.
4. Preserve the dashboard’s separate `Factor` group.
5. Update the agent taxonomy docs and seed prompts so the factor location and pointer relationship are explicit.
6. Generate or refresh the appropriate thin pointers and native wrappers for supported hosts, including Codex, Cursor, Claude Code, Junie, GitHub Copilot, Warp, Windsurf, and Air.
7. Update validation and dashboard discovery so factor agents are still surfaced correctly after the move.

## Scope

**Problem statement:** Factor agents are currently stored only in a host-native directory, which obscures the shared canonical taxonomy and makes the dashboard/grouping logic look like it depends on platform-specific storage.

**In scope:**

- relocating canonical factor content into `docs/agents/`
- keeping canonical factor docs at the `docs/agents/` root as `factor-*.md`
- keeping `.claude/agents/` as a pointer surface
- propagating the canonical factor contract through framework seeds and platform-surface generation
- generating or refreshing host pointers and native wrappers for supported hosts
- dashboard collection changes for factor discovery
- docs updates describing the new canonical location
- tests proving the dashboard still shows a dedicated `Factor` group

**Out of scope:**

- changing the meaning of factor-review policy
- folding factors into specialists
- changing journal behavior
- changing the dashboard group label unless needed for consistency
- changing the supported host set

## Acceptance Criteria

- AC-1: Factor agents have a canonical home under `docs/agents/`.
- AC-2: All factor agent filenames continue to use the `factor-` prefix.
- AC-3: Canonical factor docs live at the root of `docs/agents/` as `factor-*.md`.
- AC-4: `.claude/agents/` remains available as a pointer/wrapper surface to the canonical factor docs.
- AC-5: The dashboard still renders a separate `Factor` group.
- AC-6: Factor agents do not get merged into the specialist group.
- AC-7: The docs surface explains the canonical factor location and the pointer relationship clearly.
- AC-8: The relevant framework seeds and platform-surface generation carry the factor contract forward.
- AC-9: Supported host entry surfaces receive the correct thin pointers and native wrappers.
- AC-10: Validation and dashboard discovery continue to work after the move.

## Tasks

- [x] Move canonical factor docs to the root of `docs/agents/` as `factor-*.md`.
- [x] Update the factor agent docs, seed prompts, and any native wrappers so `.claude/agents/` points back to the canonical docs.
- [x] Update the framework seeds and rendering pipeline so the factor contract is part of the canonical generated surface.
- [x] Generate or update thin pointers and native wrappers for supported hosts, including Codex, Cursor, Claude Code, Junie, GitHub Copilot, Warp, Windsurf, and Air.
- [x] Update dashboard collection so factors are discovered from the canonical shared agent surface.
- [x] Update `docs/agents/README.md` and `docs/agents/platform-mapping.md` to document the new layout.
- [x] Add or update tests for factor discovery, grouping, and pointer-surface behavior.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|-----------|-------|------------|-------|
| factor-canonical-layout | implementer | — | Move factor content into shared agent taxonomy and keep pointer wrappers |

## Serialization Points

- Decide the canonical factor directory before changing dashboard discovery or wrappers.

## Affected Architecture Docs

Likely `docs/agents/README.md` and `docs/agents/platform-mapping.md`; possibly dashboard architecture notes if the collection path changes materially.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Canonical layout is the core of the change |
| AC-2 | required | The prefix is part of the factor taxonomy and should remain stable |
| AC-3 | required | Canonical docs must live at the root of the shared agent taxonomy |
| AC-4 | required | Pointer surfaces preserve host-native access without duplicating truth |
| AC-5 | required | The separate dashboard group must remain visible |
| AC-6 | required | Factor must stay distinct from specialists |
| AC-7 | required | The factor contract must flow through seeds and platform generation |
| AC-8 | required | Host-specific wrappers are part of the supported agent surface |
| AC-9 | required | Operators need to understand where the source of truth lives |
| AC-10 | required | The change must be operationally safe |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-20 | Change created from factor taxonomy review. | user request |
| 2026-05-20 | Change admitted into wave `12rnv agent-prompt-harness`. | user request |
| 2026-05-20 | Implemented canonical factor docs under `docs/agents/`, kept `.claude/agents/` as wrappers, and updated the dashboard/docs surfaces to use the shared taxonomy. | dashboard tests + docs-lint |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-20 | Move canonical factor docs into the shared agent taxonomy and keep `.claude/agents/` as a pointer surface. | Keeps factor agents aligned with the rest of the agent docs and avoids making the host-native directory the source of truth. | Leave canonical docs only in `.claude/agents/` — rejected because it makes the taxonomy host-specific. |

## Risks

| Risk | Mitigation |
|------|------------|
| Duplicate factor content drifts between canonical docs and wrappers | Make the canonical docs the only editable source and keep wrappers generated or clearly pointed |
| Dashboard discovery breaks during the move | Add tests before switching the collection path |
| Factor docs become confused with specialists | Keep the separate `Factor` group and document the boundary explicitly |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
