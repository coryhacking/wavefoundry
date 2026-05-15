# Seeds: Agent Doc Best Practices — Canonical Headings, Structure, and Dashboard Contract

Change ID: `12mc3-bug agent-bootstrap-seed-missing-canonical-heading-names`
Change Status: `complete`
Previous Change Status: `planned`
Owner: Engineering
Status: active
Last verified: 2026-05-14
Wave: `12mc3 agent-detail-panel-blank-section-mismatch`

## Rationale

The agent bootstrap seed (seed-050) describes agent doc content requirements in prose but never names the exact H2 heading strings that constitute the canonical structure. This causes cross-project heading drift — different projects generate agent docs with different section names, making it impossible to build reliable tooling against the docs. The dashboard's full-doc markdown render (companion change) removes the parser fragility, but canonical headings still matter for readability, consistency, and future tooling. Additionally, seed-050 and related seeds lack explicit best-practice guidance on: doc length and focus, what distinguishes a good agent identity section from boilerplate, and how the dashboard renders agent docs (so authors know what users will see).

## Requirements

1. Seed-050 must explicitly list the canonical H2 heading strings for agent docs in a reference block, with role-type applicability (reviewer vs. builder vs. coordinator vs. specialist).
2. Seed-050 must note that the dashboard renders the full agent doc — authors should write identity and responsibilities sections as if a human reader will see them directly in the UI.
3. Seed-050 must include best-practice guidance: agent docs should be focused and scannable; Operating Identity should be 2–5 sentences max; avoid duplicating content already in `AGENTS.md` or `020-run-contract`; Execution Contract should use only the role-relevant subset of run-contract rules.
4. Seed-050 must state the preferred section order for canonical role docs: `## Operating Identity` → `## Responsibilities` → `## Salience Triggers` → `## Default Stance` → `## Review Dimensions` / `## Evidence Requirements` (reviewer roles) → `## Output Shape` → `## Do Not` → `## Assumption Tracking` → `## Memory Responsibilities` → `## Execution Contract`.
5. Seed-006 (agent journal system overview) must name the canonical journal section headings explicitly (`## Operating Identity`, `## Salience Triggers`, `## Distillation`, `## Active Signals`, `## Promotion Evidence`, `## Retirement And Supersession`, `## Governance`) so journal authors use consistent headings across projects. Note: seed-130 uses `## Retirement and Supersession` (lowercase "and") — the canonical form must be chosen and the discrepancy between seed-006 and seed-130 resolved to a single casing in this change.
6. Seed-050 canonical heading guidance applies to generic agent roles. Specialist agent seeds (211–214) are generic framework seeds distributed to all projects and evaluated for applicability like any other seed; each project customizes them for its own domain. Seed-050 may reference them as examples of specialist role seeds but must use domain-neutral language — it must not reference Wavefoundry-internal file names (chunker.py, server.py, etc.) in its guidance. Note: the current content of seeds 212–214 references Wavefoundry-internal files; correcting that content is a separate issue outside this wave's scope.

## Scope

**Problem statement:** Seeds describe agent doc content requirements in prose but omit the exact heading strings and best-practice authoring guidance, leading to cross-project inconsistency.

**In scope:**

- Add a canonical heading reference block to seed-050 with role-type applicability and preferred section order.
- Add dashboard-render awareness note to seed-050.
- Add authoring best-practice guidance (focus, length, non-duplication) to seed-050.
- Add canonical journal section heading names to seed-006.

**Out of scope:**

- Retrofitting existing agent docs in installed projects.
- Changing seeds other than seed-050 and seed-006.
- Enforcing heading names via docs-lint (separate wave if desired).

## Acceptance Criteria

- AC-1: Seed-050 contains a reference block listing the exact H2 heading strings for canonical role docs, with role-type applicability.
- AC-2: Seed-050 states the preferred section order.
- AC-3: Seed-050 includes authoring best-practice guidance (doc focus, identity length, non-duplication with AGENTS.md/020).
- AC-4: Seed-050 notes that the dashboard renders the full agent doc and authors should write for human readability.
- AC-5: Seed-006 explicitly names the canonical journal H2 heading strings.
- AC-6: The `## Retirement And Supersession` / `## Retirement and Supersession` capitalization discrepancy between seed-006 and seed-130 is resolved to a single canonical form.
- AC-7: Seed-050 guidance for specialist roles uses domain-neutral language — no Wavefoundry-internal file names appear in the seed text.

## Tasks

- [ ] Add canonical heading reference block + section order + authoring best practices + specialist exclusion note to seed-050 (`seed_edit_allowed` gate required). Insert after the existing "Agent Doc Structure" or equivalent section — before any run-contract or tooling guidance.
- [ ] Add canonical journal heading names to seed-006; resolve `Retirement And/and Supersession` capitalization in both seed-006 and seed-130 to a single canonical form (`seed_edit_allowed` gate required).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|------------|-------|------------|-------|
| seed-update | implementer | 12mc6-enh | seed_edit_allowed gate required; dashboard render change must land first so seeds can reference the new rendering path |

## Serialization Points

- `seed_edit_allowed` gate must be open before editing seeds (seed-050, seed-006, seed-130); close immediately after. Note: seed-130 is edited as part of the capitalization fix (AC-6) alongside seed-006.

## Affected Architecture Docs

N/A — seed documentation update only; no boundary or flow changes.

## AC Priority

| AC   | Priority  | Rationale |
|------|-----------|-----------|
| AC-1 | required  | Canonical headings prevent cross-project drift |
| AC-2 | required  | Section order makes docs consistent and scannable |
| AC-3 | important | Best-practice guidance prevents bloated/duplicated agent docs |
| AC-4 | important | Dashboard-render awareness connects authoring to the UI |
| AC-5 | required  | Journal canonical headings are referenced by seed-130 and the journal bootstrap |
| AC-6 | required  | Capitalization inconsistency would leave conflicting guidance in two seeds |
| AC-7 | required  | Seed-050 must not embed Wavefoundry-internal file names in guidance that is meant to apply to all projects |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Gap identified: seed-050 and seed-006 describe content but not heading contracts or best practices | Cross-project diagnosis of aceiss/javaagent agent docs |
| 2026-05-14 | Red team + wave council review complete; findings incorporated: dependency on 12mc6-enh, seed-130 capitalization conflict (AC-6), specialist seed exclusion (AC-7/Req-6), insertion point specified in task | Red team + wave council parallel review |
| 2026-05-14 | Correction: seeds 211–214 are generic framework seeds evaluated per-project like any other seed. The issue is that their current *content* references Wavefoundry-internal files (chunker.py/server.py) — fixing that is out of scope here. Req-6/AC-7 reframed: seed-050 specialist guidance must use domain-neutral language. | Cross-project review |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | Scope to seed-050 and seed-006 only | These are the two seeds directly responsible for agent doc authoring; other seeds reference agent docs but don't author them | Broader seed sweep — higher risk, lower return |
| 2026-05-14 | Include dashboard-render awareness in seed-050 | Authors who know the dialog renders their full doc will write better identity sections | Omit — leaves authoring disconnected from the UI contract |

## Risks

| Risk | Mitigation |
|------|------------|
| Over-prescribing section order makes thin agent docs feel forced | Note that only role-relevant sections are required; thin/generic roles can omit sections that don't apply |
| Canonical headings conflict with existing project conventions | Seed guidance is advisory for new docs; existing docs are not required to retrofit |
| Choosing wrong capitalization for `Retirement And/and Supersession` creates downstream lint mismatches | Audit seed-006, seed-130, and installed journal files; choose the form that requires fewest downstream fixes; document the chosen form explicitly |
| Seed-050 specialist guidance inadvertently uses Wavefoundry-internal file names | Use abstract role descriptions (e.g. "performance reviewer", "security reviewer") without referencing specific internal files; note that each project customizes specialist seeds for its own domain |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
