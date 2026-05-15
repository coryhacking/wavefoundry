# Dashboard: Agent Detail Panel Always Blank Due to Hardcoded Section Allowlist

Change ID: `12mc3-bug agent-detail-panel-blank-hardcoded-section-allowlist`
Change Status: `planned`
Owner: Engineering
Status: active
Last verified: 2026-05-14
Wave: `12mc3 agent-detail-panel-blank-section-mismatch`

## Rationale

The agent detail panel in the dashboard shows blank content for all agents in projects that do not use the exact H2 section headings in `_DETAIL_SECTIONS`. The allowlist (`dashboard_lib.py` line 684) contains eight headings (`Operating Identity`, `Who`, `Goals`, `Responsibilities`, `Default Stance`, `Focus Areas`, `Scope`, `Failure Modes`) — a mix of Wavefoundry-canonical and generic names. Projects seeded with the standard agent bootstrap produce docs using sections like `Execution Contract`, `Salience Triggers`, `Memory Responsibilities`, `Review Dimensions`, `Output Shape`, `Do Not`, `Assumption Tracking` — none of which are in the allowlist. When no section matches, `details` is an empty list and the panel is blank. This is the same class of hardcoded-name mismatch as the `Item Status` / `Change Status` bug (wave 12m9w).

Two distinct failure modes:

1. **Section name mismatch** — agent docs use sections described by seed-050 (`Execution Contract`, `Salience Triggers`, etc.) that are absent from `_DETAIL_SECTIONS`.
2. **No H2 sections** — agent docs with flat prose (no H2 sections at all) produce empty `details` regardless of the allowlist.

## Requirements

1. `_DETAIL_SECTIONS` must include all section names seed-050 describes as canonical: `Execution Contract`, `Salience Triggers`, `Memory Responsibilities`, `Review Dimensions`, `Evidence Requirements`, `Output Shape`, `Do Not`, `Assumption Tracking`.
2. When an agent doc has no matching sections (empty `details`), the parser must fall back to the first non-empty paragraph of the document body (up to ~500 characters, ending at a sentence boundary) so flat-prose agent docs show something meaningful rather than a blank panel.
3. The fallback must strip metadata header lines (`Owner:`, `Status:`, `Last verified:`, `Role:`) before extracting body text.
4. Existing agents that already match current allowlist sections must be unaffected.

## Scope

**Problem statement:** `_DETAIL_SECTIONS` in `dashboard_lib.py` is a hardcoded allowlist that does not cover the full set of section names the agent bootstrap seed produces.

**In scope:**

- Extend `_DETAIL_SECTIONS` with all section names described by seed-050 as canonical.
- Add a fallback body-text render for agents with no matching sections.
- Update `collect_agents` in `dashboard_lib.py` to apply the fallback.

**Out of scope:**

- Changing H2 section names in existing agent docs.
- Modifying the dashboard JS detail panel UI (it already renders whatever `details` contains).

## Acceptance Criteria

- AC-1: An agent doc using only `## Execution Contract` and `## Salience Triggers` produces non-empty `details` in the snapshot.
- AC-2: An agent doc with no H2 sections (flat prose) produces a `details` entry with `heading: "Overview"` and body drawn from the document text.
- AC-3: An agent doc using `## Operating Identity` (current allowlist) is unaffected.
- AC-4: The fallback body is capped at ~500 characters and ends at a sentence or paragraph boundary; metadata header lines are stripped before extraction.

## Tasks

- [ ] Extend `_DETAIL_SECTIONS` in `dashboard_lib.py` to add: `Execution Contract`, `Salience Triggers`, `Memory Responsibilities`, `Review Dimensions`, `Evidence Requirements`, `Output Shape`, `Do Not`, `Assumption Tracking`.
- [ ] In `collect_agents`, after the section loop: if `details` is empty, extract the first non-empty paragraph from the document body (after stripping metadata lines) and append `{"heading": "Overview", "body": <truncated>}`.
- [ ] Add tests covering: named-section match, flat-prose fallback, existing-section no-regression.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|------------|-------|------------|-------|
| parser-fix | implementer | — | dashboard_lib.py + tests only |

## Serialization Points

- N/A

## Affected Architecture Docs

N/A — confined to dashboard agent collection parsing; no boundary or flow changes.

## AC Priority

| AC   | Priority  | Rationale |
|------|-----------|-----------|
| AC-1 | required  | Named-section agents must surface details |
| AC-2 | required  | Flat-prose agents must not be blank |
| AC-3 | required  | Must not regress existing working projects |
| AC-4 | important | Fallback quality — readable excerpt, not a truncated mid-word blob |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Root cause confirmed; two failure modes identified | Cross-project diagnosis of aceiss/javaagent agent docs vs dashboard_lib.py:684 |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | Extend allowlist + add fallback rather than dynamic H2 discovery | Allowlist keeps rendering predictable; fallback handles structural edge cases | Dynamic discovery (render any H2) — would surface noise sections like session-handoff `## Current Session` |

## Risks

| Risk | Mitigation |
|------|------------|
| Fallback extracts metadata header lines | Strip `Owner:`, `Status:`, `Last verified:`, `Role:` lines before body extraction |
| Allowlist extension causes unexpected sections to appear for projects that incidentally use those headings | All added headings are meaningful agent-identity sections; cosmetically safe |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
