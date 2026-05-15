# Persona Docs and Wave-Doc Detector: Remove Scope Requirement and Fix Path-Based Detection

Change ID: `12mcr-bug persona-scope-section-wave-anchor-antipattern`
Change Status: `complete`
Previous Change Status: `planned`
Owner: Engineering
Status: active
Last verified: 2026-05-14
Wave: `12mc3 agent-detail-panel-blank-section-mismatch`

## Rationale

Two related bugs in the same file are fixed together.

**Bug 1 — Persona Scope antipattern:** Persona docs generated across projects contain a `## Scope` section that anchors the persona to a `wave-id`. This is a misapplication of the plan template's Scope concept — persona docs define a user or operator role, not a change scope. The anchor records when the persona was *synthesized*, not what the persona *is*, and drifts immediately as waves progress. Docs-lint actively enforces this antipattern: `PERSONA_REQUIRED_SECTIONS = ("## Scope",)` in `constants.py`, and `wave_validators.py` fails any Scope section that omits a `wave-id` anchor. The seed (120) does not define a Scope section, so the section is added by analogy with plan docs.

**Bug 2 — Wave-doc detector uses content heuristic:** `check_wave_docs` scans `docs/waves/**/*.md` but uses a string-presence check on the wave-id keyword to decide whether to apply wave-record checks (Title, Objective, Wave Summary, Journal Watchpoints). Since the function only scans `docs/waves/`, this heuristic is redundant and wrong — it misidentifies any change doc whose prose discusses wave-id concepts. The correct detection is structural: `wave.md` is the wave record; every other `.md` in the wave directory is a change doc. These should be checked differently.

## Requirements

1. `PERSONA_REQUIRED_SECTIONS` in `wave_lint_lib/constants.py` must no longer include `"## Scope"`. Persona docs do not require a Scope section.
2. The wave-id anchor check in `check_persona_docs` (`wave_validators.py` lines 719–721) must be removed. No persona doc field should be required to reference a wave-id.
3. Seed-120 must explicitly state that persona docs do not include a `## Scope` section; evidence supporting a persona's existence should be embedded inline in the **Who** and **Goals** sections where it is contextually useful, not collected into a standalone Scope block.
4. Seed-120 must state that wave-id references do not belong in persona doc content — they are synthesis metadata and are not part of the persona's definition.
5. Seed-005 must note that the persona doc section structure (`Who`, `Goals`, `Workflows`, `Failure modes`, `Invocation signals`, `Operating identity`, `Salience triggers`, `Associated journal`) is fixed and distinct from plan/change docs; `## Scope` is a plan concept and must not appear in persona docs.
6. `check_wave_docs` in `wave_validators.py` must replace the wave-id string-presence heuristic with path-based detection. Implementation: split the existing loop body into two branches keyed on `path.name == "wave.md"`. The `wave.md` branch applies all current wave-record checks: `WAVE_REQUIRED_SECTIONS`, `Title:` metadata, `## Objective`, `## Journal Watchpoints` bullet check, `wave-id` uniqueness, and the `## Changes` / Change ID declarations. The non-`wave.md` branch applies only: Change ID header present, Change ID not already seen in `seen_item_ids` (duplicate tracking). The non-`wave.md` branch must NOT apply `WAVE_REQUIRED_SECTIONS`, `Title:`, `## Objective`, or `## Journal Watchpoints` checks — those are wave-record-only.

## Scope

**Problem statement:** Two bugs in `wave_validators.py`: (1) docs-lint requires `## Scope` with a wave-id anchor in every persona doc, encoding an antipattern as a lint rule; (2) `check_wave_docs` uses a content heuristic to identify wave records instead of the structurally unambiguous `wave.md` filename, causing change docs that discuss wave-id concepts to be misclassified and incorrectly linted.

**In scope:**

- Remove `"## Scope"` from `PERSONA_REQUIRED_SECTIONS` in `constants.py`.
- Remove the wave-id anchor check from `check_persona_docs` in `wave_validators.py`.
- Replace the wave-id string-presence heuristic in `check_wave_docs` with `path.name == "wave.md"` for wave-record checks; apply only change-doc checks to other `.md` files in the wave directory.
- Update seed-120 to prohibit `## Scope` and wave-id references in persona doc content; specify where evidence belongs (inline in Who/Goals).
- Update seed-005 to name the fixed persona section structure and note that Scope is a plan concept.
- Update tests in `test_docs_lint.py` to cover the corrected behaviour.

**Out of scope:**

- Retrofitting existing persona docs in installed projects to remove their Scope sections (advisory, not enforced).
- Changes to persona doc sections other than removing Scope.
- The wave-id cross-reference validator for other doc types — only the persona-specific check and the wave-record detector are modified.

## Acceptance Criteria

- AC-1: A persona doc without a `## Scope` section passes docs-lint.
- AC-2: A persona doc with a `## Scope` section that omits a wave-id anchor passes docs-lint (no false failure).
- AC-3: Seed-120 explicitly states that persona docs do not include a Scope section and that wave-id references belong in synthesis metadata, not persona content.
- AC-4: Seed-005 lists the fixed persona section structure and notes that Scope is a plan concept.
- AC-5: Tests for `check_persona_docs` no longer assert that Scope or wave-id are required.
- AC-6: A change doc inside `docs/waves/*/` whose prose contains the text `wave-id` does not trigger wave-record lint checks (Title, Objective, Wave Summary, Journal Watchpoints).
- AC-7: `wave.md` files continue to receive full wave-record lint checks.

## Tasks

- [ ] Remove `"## Scope"` from `PERSONA_REQUIRED_SECTIONS` in `wave_lint_lib/constants.py` (`framework_edit_allowed` gate required).
- [ ] Remove `scope_text` / wave-id anchor check (lines 719–721) from `check_persona_docs` in `wave_validators.py` (`framework_edit_allowed` gate required).
- [ ] Replace content heuristic in `check_wave_docs` (`wave_validators.py` line 464) with `path.name == "wave.md"` for wave-record checks; apply change-doc checks only to other `.md` files (`framework_edit_allowed` gate required).
- [ ] Update `test_docs_lint.py`: remove Scope/wave-id required assertions for persona docs; add test asserting change docs with `wave-id` prose are not flagged as bad wave records (`framework_edit_allowed` gate required).
- [ ] Update seed-120 to prohibit Scope section and wave-id in persona doc content; specify evidence placement (`seed_edit_allowed` gate required).
- [ ] Update seed-005 to name fixed persona section structure; note Scope is a plan concept (`seed_edit_allowed` gate required).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|------------|-------|------------|-------|
| lint-fix | implementer | — | constants.py + wave_validators.py: remove Scope requirement, wave-id check, and fix wave-doc detector |
| test-update | implementer | lint-fix | test_docs_lint.py: remove Scope/wave-id assertions; add change-doc false-positive regression test |
| seed-update | implementer | lint-fix | seed-120 + seed-005: prohibit Scope, name correct structure; seed_edit_allowed gate |

## Serialization Points

- `framework_edit_allowed` gate required for `constants.py`, `wave_validators.py`, `test_docs_lint.py`.
- `seed_edit_allowed` gate required for `seed-120` and `seed-005`; open before editing, close immediately after.

## Affected Architecture Docs

N/A — confined to lint rules and seed guidance; no boundary or flow changes.

## AC Priority

| AC   | Priority  | Rationale |
|------|-----------|-----------|
| AC-1 | required  | Core fix — persona docs without Scope must pass lint |
| AC-2 | required  | Existing persona docs with Scope but no wave-id must not regress |
| AC-3 | required  | Seed-120 must actively prohibit the antipattern, not just omit it |
| AC-4 | important | Seed-005 structural note prevents the analogy confusion that caused this |
| AC-5 | required  | Tests must not re-encode the antipattern as an assertion |
| AC-6 | required  | Root cause of the wave-doc false positive that surfaced during this change's own admission |
| AC-7 | required  | Must not regress wave-record validation for legitimate wave.md files |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Bug confirmed: PERSONA_REQUIRED_SECTIONS includes "## Scope"; wave_validators.py lines 719–721 require a wave-id anchor in Scope; seed-120 does not define Scope section | Code inspection + cross-project persona doc review |
| 2026-05-14 | Second bug confirmed: check_wave_docs uses a wave-id string-presence heuristic instead of path-based detection (wave.md filename); false positive surfaced when this change doc was admitted and its own prose triggered the detector | Docs-lint failure during wave_add_change |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | Remove Scope from persona docs entirely rather than redefine it | Persona docs define a user role; no boundary/scope concept applies | Redefine Scope as "persona boundary" — adds a section with no clear value over Who/Goals |
| 2026-05-14 | Evidence belongs inline in Who/Goals, not in a separate section | Keeps persona docs focused on the persona definition; synthesis metadata doesn't belong in the doc | Separate Evidence section — still not a standard plan concept; adds noise |

## Risks

| Risk | Mitigation |
|------|------------|
| Removing Scope lint check causes existing persona docs with Scope to silently carry dead content | Acceptable — removing a section is advisory; lint will no longer flag its absence, not its presence |
| Seed-120 update doesn't reach projects that already have the Scope pattern | Seed guidance is forward-looking; existing docs are not required to retrofit |
| Path-based detector misses wave records stored outside `docs/waves/` | Not a real risk — `check_wave_docs` already anchors its scan to `docs/waves/`; no wave records exist elsewhere by convention |
| Change docs with a legitimate `wave.md`-like name could be misdetected | Only `wave.md` (exact filename) triggers wave-record checks; any other name is treated as a change doc |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
