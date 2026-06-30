# Stage gate anti-drift guard — the two named gate sections are a fixed cross-doc contract

Change ID: `1p8t5-enh stage-gate-anti-drift-guard`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-29
Wave: `1p8t7 stage-gate-anti-drift-guard` (requires `seed_edit_allowed` at implementation)

## Rationale

Implements the decision in `1p8t4-adr stage-gate-canonical-structure`. `seed-050` prescribes the agent-entry gate as two named sections (`## Stage Gate (repository code)`, `## Implementation guard (product code)`), while the upgrade seeds (`150`/`160`) tell repos to "preserve repo-grown behavior / reconcile in place." That collision is **active, not theoretical**: a low-experience consumer (teton, few waves) drifted to consolidating the two gates into one table — following the upgrade license — leaving its by-name references soft-resolving. The headings are a **cross-document contract** (referenced by name across host entry docs and lifecycle prompts), so consolidation accrues addressability debt that hardens as the framework trends toward determinism. This change closes the license-gap that invited the drift: the gate's two named sections are carved out of the consolidate-in-place license. Seed wording only — no validator, no anchors, no second template, no lifecycle behavior change.

## Requirements

1. **`seed-050` tasks 17/19** — add a clause to each gate prescription: the two named gate sections are a **fixed cross-document contract** (referenced by name across host entry docs and lifecycle prompts) and are **exempt from the "preserve repo-grown / consolidate in place" license** — do NOT consolidate or rename them. Include the one-line *why*: so those by-name references stay resolvable. They remain the canonical render target for new installs.
2. **`seed-160` reconciliation step** (the AGENTS.md section reconciliation, near the "ensure `Implementation guard (product code)` exists / preserve repo-grown" language) — state that on upgrade the gate is **re-established as the two named sections** (preserving the documented per-surface preconditions); a repo that consolidated the gate is guided back to the canonical two-section form. Make explicit that this surface is the carve-out from the general preserve-repo-grown rule.
3. **Standing-decision note** — record (in the `seed-050` gate area and/or the `seed-009` framework-maintenance contract, wherever standing decisions live) that the framework will **not** add a validator asserting the literal gate heading strings: the carve-out is enforced by guidance, not a brittle heading-string check.
4. **No new machinery** — no validator, no anchor/marker convention, no second/consolidated template, no lifecycle behavior change.

## Scope

**Problem statement:** the `seed-050`-vs-`150`/`160` contradiction is active (it drifted a consumer); resolve it toward fix-canonical and prevent recurrence.

**In scope:**

- `seed-050` (tasks 17/19) wording — the fixed-contract carve-out clause + the *why*.
- `seed-160` reconciliation-step wording — re-establish/keep the two named sections; explicit carve-out from preserve-repo-grown.
- The standing-decision note (no literal-heading validator).
- Link `1p8t4-adr` from the touched seed(s).

**Out of scope:**

- Blessing a consolidated-table template; an anchor/marker convention; a validate-by-policy or literal-heading validator (all declined in `1p8t4-adr`).
- The "wave-admitted surfaces" third-gate-dimension question (separate, independently-evaluated enhancement — do not couple).
- Any change to gate *semantics* (the preconditions themselves are unchanged — only the structure-is-fixed rule is added).

## Acceptance Criteria

- [x] AC-1: `seed-050` tasks 17/19 state the two named gate sections are a fixed cross-document contract, exempt from the consolidate-in-place license (do not consolidate/rename), with the by-name-references rationale.
- [x] AC-2: the `seed-160` reconciliation step re-establishes/keeps the two named sections on upgrade (preserving the documented preconditions) and explicitly carves the gate out of the general preserve-repo-grown rule. (Added in both the drift-detection backfill list and the every-upgrade reconcile list, mirroring how the Implementation guard already appears in both.)
- [x] AC-3: a standing-decision note records that no literal-heading gate validator will be added (guidance-enforced carve-out). (Recorded in `seed-009` Overwrite-vs-preserve rules, with a co-located restatement in `seed-050` task 17.)
- [x] AC-4: no validator / anchor / second template / lifecycle change is introduced; the two-section form remains the canonical render target; the framework suite + docs-lint stay green. (Diff is additive prose across 3 markdown seeds — no `.py`; suite 3683 green; docs-lint ok.)
- [x] AC-5: `1p8t4-adr stage-gate-canonical-structure` is linked from the touched seed(s). (All three touched seeds reference the ADR by path.)

## Tasks

- [x] Edit `seed-050` tasks 17/19 — add the fixed-contract carve-out clause + the *why* (under `seed_edit_allowed`).
- [x] Edit `seed-160` reconciliation step — re-establish/keep two named sections; carve-out note.
- [x] Add the standing-decision note (seed-050 gate area and/or `seed-009`).
- [x] Verify no validator/anchor/template/lifecycle change crept in.
- [x] Run the framework suite + docs-lint; confirm green.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| seed-050 carve-out + standing-decision note | implementer | — | `seed_edit_allowed` |
| seed-160 reconciliation wording | implementer | — | `seed_edit_allowed`; coordinate idiom with seed-050 |
| verify no machinery added + suite/docs-lint | qa-reviewer | both | guidance-only assertion |

## Serialization Points

- `seed-050` and `seed-160` are both seed edits — open `seed_edit_allowed` for the implementation pass and keep the two edits idiomatically consistent (same "fixed contract / carved out of preserve-in-place" phrasing).

## Affected Architecture Docs

`docs/architecture/decisions/1p8t4-adr stage-gate-canonical-structure.md` (the decision this implements; already authored). No other architecture-doc impact — guidance wording only.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The core anti-drift carve-out (prevents the next teton). |
| AC-2 | required | Resolves the active upgrade-reconciliation contradiction. |
| AC-3 | required | Forecloses the heading-string-validator foot-gun. |
| AC-4 | required | Keeps the change wording-only (no machinery, no regression). |
| AC-5 | important | Traceability to the ADR. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-29 | Drafted from `1p8t4-adr`. Parked in `docs/plans/` to ride the next seed-touching wave (seed edits need `seed_edit_allowed` + admission). | `1p8t4-adr stage-gate-canonical-structure`; verified prior: `wave_lint_lib` has 0 gate checks, `waveframework:` markers are render-regions not addressing anchors, wavefoundry (530 changes) never consolidated. |
| 2026-06-29 | Admitted into wave `1p8t7`, prepared (readiness + prepare-council PASS), implemented under `seed_edit_allowed`. Edited `seed-050` tasks 17/19 (fixed-contract carve-out + standing-decision restatement), `seed-160` (both backfill lists — re-establish two named sections, preserve preconditions verbatim), `seed-009` (standing decision: no heading-string validator). All 5 ACs `[x]`. | seeds 050/160/009 diff (+6/−2, markdown-only); framework suite 3683 green (125.3s); `wave_validate` docs-lint ok. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-29 | Resolve the contradiction toward fix-canonical (carve the gate out of the consolidate license), not bless-consolidation. | The teton drift shows blessing consolidation would worsen the natural drift; the canonical two-section form is frictionless in wavefoundry's 530-change corpus. | Bless consolidation / anchors / validate-by-policy (all declined in `1p8t4-adr`). |
| 2026-06-29 | Guidance-enforced, not a validator. | The gate is policy agents read; a literal-heading validator is the foot-gun this very decision forecloses. | Add a heading/anchor validator (rejected). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The carve-out over-reaches and reads as "AGENTS.md is not customizable." | Scope the carve-out explicitly to the two gate sections; the general preserve-repo-grown rule stays intact for every other surface. |
| The seed-160 "re-establish two sections" reads as a destructive rewrite of a consumer's gate. | Phrase as preserve-the-preconditions-restructure-to-two-sections; the documented per-surface preconditions are kept, only the structure is normalized. |
| Drafted now but seeds change before implementation. | It's a small wording change against stable seed anchors (tasks 17/19, the 160 reconciliation step); re-confirm the anchor lines at implementation. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
