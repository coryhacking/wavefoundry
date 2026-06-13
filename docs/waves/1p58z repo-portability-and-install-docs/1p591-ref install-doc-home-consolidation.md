# [Change Title]

Change ID: `1p591-ref install-doc-home-consolidation`
Change Status: `planned`
Owner: [role or person]
Status: planned
Last verified: 2026-06-13
Wave: [wave-id or TBD]

## Rationale

Install-related content is scattered across four framework subtrees with no single discoverable home: `.wavefoundry/framework/install/` (the `install-log.template.md` and `install-wavefoundry.template.md` templates), `.wavefoundry/framework/release/install-block.md`, `.wavefoundry/framework/docs/references/install-log-format.md` (the format spec), and `.wavefoundry/framework/seeds/01x-install-wavefoundry*.prompt.md` (the install prompts). On top of the sprawl, `install-log-format.md` is duplicated framework↔project (`docs/references/install-log-format.md`) — exactly the framework/project split the `1p4ww` fold removed for the index. A contributor cannot find "where install lives," and the duplicate can drift.

## Requirements

1. Define one canonical home for each install-asset type (templates, release block, format spec, prompts); the change doc records an old→new inventory.
2. Remove the framework↔project `install-log-format.md` duplication — single source of truth, the other a pointer or removed.
3. Update every consumer reference so nothing breaks: scripts (`build_pack.py` reads `release/install-block.md`; setup reads the install templates), seed ordering, and doc cross-links.
4. Behavior-neutral: the install, release, and setup flows produce identical output before and after the move.

## Scope

**Problem statement:** install docs are spread across four framework subtrees and duplicated framework↔project, with no clear home — hard to find and prone to drift.

**In scope:**

- The framework install assets (`framework/install/`, `framework/release/install-block.md`, `framework/docs/references/install-log-format.md`, `framework/seeds/01x-install-*`).
- The project `docs/references/install-log-format.md` duplicate.
- Consumer path references in scripts/seeds/docs + their tests.

**Out of scope:**

- Changing install/release/setup behavior or rewriting the install-prompt content.
- The path-portability change (that is `1p590`).

## Acceptance Criteria

- [ ] AC-1: each install asset has exactly one canonical location; the doc contains an old→new mapping inventory.
- [ ] AC-2: no duplicate `install-log-format.md` (framework vs project) — one source of truth; any remaining reference is a pointer.
- [ ] AC-3: all script/seed/doc references updated; a grep for the old paths returns no stragglers.
- [ ] AC-4: install + release + setup flows verified behavior-identical (relevant tests green: `build_pack`, `setup_index`/setup, `upgrade`).
- [ ] AC-5: docs-lint clean with no broken doc links.

## Tasks

- [ ] Inventory all install assets and their consumers (exact paths) — produce the old→new mapping.
- [ ] Choose the canonical home (prepare/design); consider an ADR (mirrors the `1p4xx` fold ADR).
- [ ] Move assets + update all references in one coordinated pass; add pointers where external links exist.
- [ ] Run `build_pack`/setup/upgrade tests + docs-lint; grep for old-path stragglers.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| [workstream-1] | [role] | —            |       |
| [workstream-2] | [role] | workstream-1 |       |


## Serialization Points

- [Shared file or integration gate that requires coordination before parallel work proceeds]

## Affected Architecture Docs

A new ADR under `docs/architecture/decisions/` is likely warranted to record the chosen install-doc home and the framework↔project dedup rule (mirrors the `1p4xx` fold ADR). Update the install-docs index / `docs/references` cross-links. No change to layering, data-flow, or testing-architecture docs (behavior-neutral relocation).

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required / important / nice-to-have / not-this-scope |           |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
|      |            |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
