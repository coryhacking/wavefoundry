# Agent Category Metadata and Dashboard Grouping

Change ID: `12rps-enh agent-category-metadata-dashboard-grouping`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-20
Wave: `12rnv agent-prompt-harness`

## Rationale

`Role:` is the agent identity field, but it is not a good dashboard grouping key. The dashboard needs an explicit grouping field so the presentation layer does not have to infer behavior from filenames or host-specific storage.

This change introduces `Category:` as the dashboard grouping metadata for dashboard-visible agent docs. The linter will validate that `Category:` is one of the supported dashboard groups, and the dashboard will use that field to place entries into the right section.

This change also needs to propagate into the framework seed prompts and generated host entry surfaces so the category contract is broadly implemented instead of only living in the local docs.

The intended categories are:

- `build`
- `review`
- `coordinate`
- `specialist`
- `factor`
- `operate`
- `journal`

## Requirements

1. Keep `Role:` as the identity field for agent docs.
2. Add `Category:` as the dashboard grouping field for dashboard-visible agent docs.
3. Validate that `Category:` is one of the supported values.
4. Use `Category:` to place agent docs into the correct dashboard group.
5. Preserve the separate `Factor` group.
6. Propagate the category contract into the relevant framework seeds and rendered prompt surfaces.
7. Generate the appropriate thin pointers and native wrappers for supported coding agents and hosts, including Codex, Cursor, Claude Code, Junie, GitHub Copilot, Warp, Windsurf, and Air.
8. Preserve current journal behavior unless a separate change says otherwise.

## Scope

**Problem statement:** The dashboard currently infers grouping from file shape and naming conventions. That makes grouping implicit, spreads taxonomy rules across multiple code paths, and makes it harder to validate dashboard-visible agent docs consistently.

**In scope:**

- `Category:` metadata for dashboard-visible agent docs
- category validation in docs lint
- dashboard grouping based on `Category:`
- framework seed updates so the category contract is part of the canonical prompt surface
- generated host pointers and wrappers for supported coding agents and hosts
- factor agents grouped under `factor`
- tests that prove category-based grouping works

**Out of scope:**

- changing `Role:` identity semantics
- changing journal behavior
- changing support docs that are not dashboard-visible agent entries
- changing the factor taxonomy location unless a separate change covers that move
- changing the set of supported hosts

## Acceptance Criteria

- AC-1: Dashboard-visible agent docs declare `Category:`.
- AC-2: `Category:` is validated against the allowed dashboard groups.
- AC-3: The dashboard uses `Category:` to render agent group headings.
- AC-4: The `Factor` group is rendered from `Category: factor`.
- AC-5: `Role:` remains the identity field and is not repurposed as a group label.
- AC-6: The relevant framework seeds and generated prompt surfaces carry the category contract.
- AC-7: Supported coding-agent and host surfaces receive the appropriate thin pointers and wrappers.
- AC-8: Journals and personas continue to follow the current behavior and are not forced into a new category contract.

## Tasks

- [x] Add `Category:` metadata to the dashboard-visible agent docs.
- [x] Update the docs linter to validate `Category:` values.
- [x] Update the dashboard collector and renderer to group by `Category:`.
- [x] Update the framework seeds and prompt-rendering surfaces so the category contract is broadly implemented.
- [x] Generate or update thin pointers and native wrappers for supported hosts, including Codex, Cursor, Claude Code, Junie, GitHub Copilot, Warp, Windsurf, and Air.
- [x] Update factor docs so they declare `Category: factor`.
- [x] Add tests covering explicit category grouping and invalid category rejection.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|-----------|-------|------------|-------|
| category-metadata | implementer | — | Category metadata, validation, and dashboard grouping |

## Serialization Points

- Decide the allowed category values before editing docs or dashboard grouping logic.

## Affected Architecture Docs

Likely `docs/agents/README.md` and `docs/agents/platform-mapping.md`; possibly dashboard architecture notes if grouping behavior becomes part of the documented contract.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | The new contract must be explicit in docs |
| AC-2 | required | Validation is the enforcement mechanism |
| AC-3 | required | The dashboard grouping must be driven by metadata |
| AC-4 | required | Factor agents need a stable top-level group |
| AC-5 | required | `Role:` and grouping should remain separate concepts |
| AC-6 | required | The seed and render surfaces must carry the contract forward |
| AC-7 | required | Host-specific pointers and wrappers are part of the rollout |
| AC-8 | required | Current journal and persona behavior stays intact |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-20 | Change created from category-grouping review. | user request |
| 2026-05-20 | Change admitted into wave `12rnv agent-prompt-harness`. | user request |
| 2026-05-20 | Implemented `Category:` grouping across the dashboard-visible agent docs, seeds, lint, and dashboard renderer. | dashboard tests + docs-lint |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-20 | Introduce `Category:` as the dashboard grouping field instead of overloading `Role:`. | Preserves identity semantics and makes grouping explicit and lintable. | Use `Role:` for grouping — rejected because it conflates identity with presentation. |

## Risks

| Risk | Mitigation |
|------|------------|
| Category values drift or become inconsistent | Validate against a small allowed set and add tests |
| Dashboard and docs disagree on grouping | Make the dashboard consume the same metadata the linter enforces |
| Journal behavior regresses | Keep journals out of the new category contract unless a separate change opts them in |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
