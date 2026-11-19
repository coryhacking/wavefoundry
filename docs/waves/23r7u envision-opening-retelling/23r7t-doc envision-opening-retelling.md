# Check whether a reader can retell the vision

Change ID: `23r7t-doc envision-opening-retelling`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-18
Wave: 23r7u envision-opening-retelling

## Rationale

The existing reviewer can explain the opening at length. A colleague needs to hear the intended beneficiary and distinctive outcome in a short account.

## Product Intent

The author obtains a fresh reader’s short account of what becomes possible for whom, and uses it to identify a lost distinctive benefit. AC-1 verifies delivery of this question. Actual comprehension depends on a future run.

## Requirements

1. Ask for a one- or two-sentence explanation to a colleague before showing the roadmap or brief.
2. Compare the retained answer with the intended distinctive benefit and repair a consequential mismatch within the existing review pass.

## Scope

Edit the canonical Envision review companion and its local copy. Use the existing reviewer and single vision paragraph.

## Acceptance Criteria

- [x] AC-1: Both companions carry the same colleague question and repair instruction, with the opening-only answer retained before roadmap disclosure. A generic retelling that loses the distinctive benefit goes to the author for the existing repair pass.

## Tasks

- [x] Update and compare both companions and validate documentation.

## Affected Architecture Docs

N/A. The review sequence and participants already exist.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Delivers the agreed reader check |

## Progress Log

- 2026-11-18 — Readback: AC-1 gives a fresh reviewer the opening first. Both review companions retain the answer before sharing the roadmap. The reviewer flags a lost distinctive benefit and the author repairs the opening within the existing pass.

- 2026-11-18 — Compared the complete companion bodies, checked opening-only input and answer retention before disclosure, and rejected two in-memory controls that removed retention or assigned repair to the reviewer. Field comprehension awaits the first local run.

## Decision Log

Use the existing opening reconstruction so every run can test the wording without another review.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
