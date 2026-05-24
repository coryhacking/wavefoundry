# Post-Prepare Wave Council Review

Change ID: `12sp5-enh pre-implementation-gate-lint-check`
Change Status: `implemented`
Owner: software-engineer
Status: implemented
Last verified: 2026-05-21
Wave: 12sq2 enterprise-role-seeds-and-lint

## Rationale

Wave `12sg7` introduced the pre-implementation review gate (12sg4) as a protocol-only step — agents were instructed to record a verdict before implementing, but nothing enforced it or produced the review automatically. This change makes the prepare-phase review structural and automated: `wave_prepare` runs a Wave Council review of the admitted change docs as its final step, records the verdict, and `wave_validate` enforces that the verdict exists before implementation can proceed. Issues raised by the council must be resolved before implementation starts — this is a blocking gate, not advisory.

## Requirements

1. `wave_prepare` must trigger a Wave Council prepare-phase review as its final step, after all other prepare checks pass.
2. The council must have red-team as a fixed seat. An optional domain-specific rotating seat is selected based on wave content (e.g. `docs-contract-reviewer` for seed/prompt-heavy waves, `security-reviewer` for waves touching auth or trust boundaries, `architecture-reviewer` for waves with significant structural changes). The rotating seat selection heuristic must be documented and implemented explicitly — not left to implementer discretion.
3. The council review assesses the admitted change docs for: scope clarity, AC testability, implementation risk, serialization gaps, and any misuse or bypass vectors (red-team focus).
4. Issues identified by the council must be recorded and must block implementation until resolved. A clean pass records a verdict that allows implementation to proceed.
5. The verdict must be recorded in `## Review Checkpoints` in wave.md with a `prepare-council` marker.
6. `wave_validate` must emit an error when a wave at `implement_wave` or later has no recorded prepare-phase council verdict.
7. The lint check must be tolerant of waves that predate this feature — treat absence of the verdict as a warning (not a hard error) for waves created before this change was introduced.
8. The validator must have at least one passing and one failing test in the framework test suite.

## Scope

**Problem statement:** The prepare-phase review is protocol-only and manual — no automated council review runs at prepare time, and nothing enforces that a verdict was recorded before implementation begins.

**In scope:**

- Wave Council prepare-phase review triggered as the final step of `wave_prepare`
- Fixed council seat: `red-team`
- Optional rotating seat: selected from wave content analysis (change types, affected file categories, stated risks); heuristic documented explicitly in implementation
- Verdict recording in `## Review Checkpoints` with `prepare-council` marker
- Blocking behavior: issues must be resolved before implementation proceeds
- `wave_validate` lint check enforcing verdict presence at `implement_wave` or later
- Unit tests for the lint check (passing and failing cases)

**Out of scope:**

- Retroactively failing existing closed waves that lack the verdict
- Changes to the delivery-phase Wave Council review (wave_review)
- `wave_review` phase parameter and prepare-phase lane review gate — handled in `12sqb`
- Full structural doc quality scoring — council reviews scope, risk, and change readiness, not doc formatting
- Configurable council seat policy (rotating seat selection is heuristic-based for now)

## Acceptance Criteria

- [x] AC-1: `wave_prepare` runs a Wave Council prepare-phase review as its final step and records the verdict in `## Review Checkpoints`
- [x] AC-2: Red-team is always a council seat; a domain-appropriate rotating seat is selected via documented heuristic and identified in the verdict
- [x] AC-3: A council finding that identifies issues blocks implementation — `wave_validate` emits an error until the issue is resolved and a clean verdict recorded
- [x] AC-4: A clean council pass records a verdict that allows `wave_validate` to pass
- [x] AC-5: `wave_validate` emits an error when a wave at `implement_wave` or later has no prepare-phase council verdict
- [x] AC-6: Waves predating this feature do not hard-fail lint (warning only)
- [x] AC-7: At least one passing and one failing test cover the lint validator

## Tasks

- [x] Read `wave_prepare` implementation in `server_impl.py` to understand the prepare write sequence and insertion point for the council review step
- [x] Design and document rotating seat selection heuristic: map wave change categories to domain seats
- [x] Implement council review trigger as the final step of `wave_prepare`; produce a structured verdict (pass/issues) and record it in `## Review Checkpoints` with `prepare-council` marker
- [x] Implement `wave_validate` lint check for prepare-phase council verdict presence
- [x] Wire lint check into the lint runner
- [x] Write passing and failing test cases for the lint check
- [x] Run full test suite; confirm no regressions

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Read wave_prepare + design council integration | software-engineer | — | |
| Rotating seat selection heuristic (documented) | software-engineer | Design | |
| Council review trigger in wave_prepare | software-engineer | Heuristic | Needs `framework_edit_allowed` gate |
| Verdict recording in Review Checkpoints | software-engineer | Council trigger | |
| Lint check in wave_validate | software-engineer | Verdict format | Needs `framework_edit_allowed` gate |
| Tests | software-engineer | Lint check | |
| Full test suite pass | qa-reviewer | Tests | |

## Serialization Points

- `framework_edit_allowed` gate: single open/close around all `server_impl.py` and `wave_validators.py` edits
- Verdict format (`prepare-council` marker) must be agreed before implementing the council trigger and the lint check — both depend on the same marker; share with `12sqb` implementer before that change begins

## Affected Architecture Docs

N/A — change is confined to `wave_prepare` in `server_impl.py`, `wave_validators.py`, and their tests. No boundary, flow, or architectural impact beyond the prepare write path.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core deliverable — automated council review at prepare time |
| AC-2 | required | Red-team fixed seat is the key governance requirement; heuristic must be explicit |
| AC-3 | required | Blocking behavior is essential — advisory-only is not sufficient |
| AC-4 | required | Clean pass must unblock implementation |
| AC-5 | required | Lint enforcement closes the gate |
| AC-6 | important | Backwards compatibility with pre-existing waves |
| AC-7 | required | Test coverage gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-21 | Change created | Red-team advisory from 12sg7 wave-council-delivery |
| 2026-05-21 | Scope expanded from lint-only to full automated Wave Council review at prepare time | Operator requirement: automated blocking review, red-team fixed seat, issues must be resolved before implementation |
| 2026-05-21 | Renamed from pre-implementation to prepare-phase | Naming is more precise — review happens after prepare, not just before implementation |
| 2026-05-21 | Added rotating seat heuristic documentation requirement | Council advisory: heuristic must be explicit, not left to implementer discretion |
| 2026-05-21 | `check_prepare_council_verdict` added to `wave_validators.py` + `cli.py` | Warns for `active`, errors for `implementing` waves lacking verdict; `_extract_sections` used in validator |
| 2026-05-21 | `_prepare_council_verdict_present`, `_select_prepare_council_rotating_seat`, `_build_prepare_council_brief` added to `server_impl.py` | Inline heading parser used (re module); `wave_prepare(mode="create")` blocks without verdict |
| 2026-05-21 | Tests written: 4 lint tests in `test_docs_lint.py`, 5 gate tests in `test_server_tools.py` | 1554 tests pass, 0 failures |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-05-21 | Warn rather than hard-error for waves predating this feature | Backwards compatibility — existing waves have no verdict | Hard-fail all waves missing the entry |
| 2026-05-21 | Red-team is a fixed seat; rotating seat is heuristic-selected from wave content | Red-team challenge is always relevant; domain seat adds targeted expertise without requiring operator configuration | Fully configurable seat list; or fixed seats only |
| 2026-05-21 | Blocking gate — issues must be resolved before implementation | Advisory-only review would be ignored under time pressure; blocking is the only meaningful enforcement | Advisory with warning |
| 2026-05-21 | Verdict recorded in `## Review Checkpoints` with `prepare-council` marker | Consistent with existing prepare-phase checkpoint pattern in wave.md | Separate section |
| 2026-05-21 | Named "prepare-phase" not "pre-implementation" | More precise — names when the review occurs, not what it precedes; pairs symmetrically with post-implementation | Pre-implementation |

## Risks

| Risk | Mitigation |
| --- | --- |
| Rotating seat selection heuristic misclassifies wave content | Heuristic is documented and recorded in verdict so operator can assess accuracy |
| Council review adds latency to wave_prepare for complex waves | Acceptable — prepare is a deliberate stage gate, not a hot path |
| Verdict marker too strict — valid verdicts fail lint | Design marker pattern to match reasonable variants; test against real wave records |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
