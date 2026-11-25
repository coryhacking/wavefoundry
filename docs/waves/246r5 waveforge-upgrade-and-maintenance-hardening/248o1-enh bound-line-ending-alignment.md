# Bound line-ending alignment work

Change ID: `248o1-enh bound-line-ending-alignment`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-11-24
Wave: 246r5 waveforge-upgrade-and-maintenance-hardening

## Rationale

Framework writers use sequence alignment to retain individual line endings. Repeated lines can make exact alignment disproportionately expensive; no field slowdown has been measured.

## Product Intent

Operators can update large repetitive files with bounded alignment work while ordinary edits preserve their current endings (AC-1 and AC-2).

## Requirements

1. Return the original text for a logical no-op and use a linear path for uniform endings. Bound exact alignment on changed mixed-ending inputs using a documented work budget. Above the budget use the original majority ending, preserving body content, lone carriage returns and the requested final termination.

## Scope

Update the writer contract in docs/contributing/build-and-verification.md and the module contract to describe the bounded mixed-ending fallback. Fully generated files and writer APIs retain their current behavior.

## Acceptance Criteria

- [x] AC-1: Tests cover mixed no-op, uniform LF and CRLF, majority ties, lone carriage returns and addition or removal of a final newline. Below the budget untouched aligned lines retain their own endings.
- [x] AC-2: Exercise both sides of the budget and a large repetitive mixed input. Prove the large input bypasses exact alignment and produces the expected bytes; report representative elapsed times separately from the deterministic assertion.

## Tasks

- [x] Return the original text for a logical no-op and use a linear path for uniform endings. Bound exact alignment on changed mixed-ending inputs using a documented work budget. Above the budget use the original majority ending, preserving body content, lone carriage returns and the requested final termination.
- [x] Exercise AC-1 and AC-2 and record evidence in the Progress Log.

## Agent Execution Graph

The implementer delivers the change and its checks. The reviewers verify the evidence independently.

## Serialization Points

- `.wavefoundry/framework/scripts/line_endings.py`
- `.wavefoundry/framework/scripts/tests/test_line_endings.py`

## Affected Architecture Docs

No architecture boundary changes. Keep the existing contract documentation consistent with this change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Verifies the primary outcome. |
| AC-2 | required | Verifies the compatibility boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-24 | Planned from Waveforge’s v1.51.0 feedback. | Item A2. |
| 2026-11-24 | Readback: Preserve logical no-ops and uniform endings without alignment. Use exact alignment for changed mixed files through one million old-line/new-line pairs. A 10,000-line mixed file with one edit now takes the original majority ending throughout. | AC-1 and AC-2 cover the shared merge helper, its tests and the contributor contract. Generated writers retain their separate LF path. |
| 2026-11-24 | AC-1 and AC-2 passed. The helper suite checks original bytes on no-ops, uniform files, mixed alignment at the budget and majority bytes above it. Tests replace SequenceMatcher with a failing stub on the bypass paths. | All 45 line-ending tests passed, including the 18 helper tests and the writer census. The helper also matched the prior implementation on 5,000 seeded below-budget inputs. Local median of seven single merges with one changed repeated line: 71.23 ms at 1,000 mixed lines (exact), 0.366 ms at 10,000 mixed lines (fallback). Timings are observations only. |

| 2026-11-24 | Delivery handoff | Implementation and targeted checks are complete. The wave coordinator owns full validation and delivery review. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-24 | Use the existing framework path. | Planner default within the operator-selected scope. | Always normalizing mixed files would change untouched lines on ordinary edits. Per-caller limits would miss other writers. |

## Risks

Update the writer contract in docs/contributing/build-and-verification.md and the module contract to describe the bounded mixed-ending fallback. Fully generated files and writer APIs retain their current behavior.

## Session Handoff

Prepare the admitted spec before implementation.
