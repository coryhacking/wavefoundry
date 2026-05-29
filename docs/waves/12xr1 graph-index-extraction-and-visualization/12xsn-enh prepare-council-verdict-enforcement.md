# Prepare Council Verdict Enforcement

Change ID: `12xsn-enh prepare-council-verdict-enforcement`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: TBD

## Rationale

Wave prepare currently depends on a human-maintained marker in `## Review Checkpoints` to prove that the prepare-phase Wave Council review happened. That is too weak for critical waves. The current gate checks for the substring `prepare-council`, which means a wave can be made admissible with a plausible-looking line even if the actual adversarial review was never run.

The goal of this enhancement is to make the prepare-phase council verdict a structured, machine-validated artifact instead of a hand-authored convention. The operator should still see the same prepare flow, but the system should enforce that a real council review happened and that the result contains enough structure to be useful later.

## Requirements

1. `wave_review(phase="prepare")` must surface a structured council verdict packet for the prepare phase so the operator can record it without guessing the required shape.
2. `wave_prepare(mode="create")` must refuse to finalize prepare unless the structured verdict is present and valid.
3. The verdict must capture the core council evidence needed for later auditing: date, seats, red-team strongest challenge, strongest alternative, and final verdict.
4. The verdict must live in a dedicated `## Review Checkpoints` block with a stable machine-readable marker, not as a free-form substring.
5. The prepare gate must fail if the verdict is missing, incomplete, or malformed.
6. The prepare gate must remain compatible with the existing `wave-council-readiness` signoff in `## Review Evidence`.
7. The canonical contract must live in the framework seeds under `.wavefoundry/framework/seeds/`; the rendered `docs/prompts/` copies are outputs, not the source of truth.
8. Add tests for the prepare-review write path, the prepare gate, and malformed or missing verdict cases.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/seeds/001-feature-wave-framework-overview.md`
- `.wavefoundry/framework/seeds/007-review-system-overview.md`
- `.wavefoundry/framework/seeds/230-council-review.prompt.md`
- `.wavefoundry/framework/scripts/tests/`
- `docs/prompts/prepare-wave.prompt.md` (rendered output)
- `docs/prompts/review-wave.prompt.md` (rendered output)
- `docs/prompts/council-review.prompt.md` (rendered output, if wording alignment is required)
- wave record / checkpoint formatting

**Out of scope:**

- changes to the actual council seat roster
- changes to the single-active-wave rule
- changes to implementation-phase delivery review semantics
- changes to non-wave docs or product code behavior

## Proposed Contract

The prepare-phase review becomes a two-step machine contract:

1. `wave_review(wave_id=..., phase="prepare")` runs the red-team primer and fixed seats, then surfaces a structured verdict packet and template for `## Review Checkpoints`.
2. `wave_prepare(mode="create")` validates that the structured verdict exists and matches the expected shape before it marks the wave active.

Suggested verdict shape:

```md
- **Prepare-phase Wave Council [prepare-council] — 2026-05-27: PASS** (red-team fixed seat; code-reviewer rotating seat)
  - Red-team strongest challenge: ...
  - Strongest alternative considered: ...
  - Council verdict: ...
  - Blocking findings: none
```

The exact wording can vary, but the structure must be stable enough for validation.

## Acceptance Criteria

- [x] AC-1: `wave_review(phase="prepare")` surfaces the prepare council verdict packet in a structured format that can be recorded into `## Review Checkpoints` without ambiguity.
- [x] AC-2: `wave_prepare(mode="create")` fails when the structured prepare council verdict is missing.
- [x] AC-3: `wave_prepare(mode="create")` fails when the structured prepare council verdict is malformed or incomplete.
- [x] AC-4: `wave_prepare(mode="create")` succeeds only when the structured prepare council verdict and `wave-council-readiness` signoff are both present.
- [x] AC-5: The prepare council verdict includes the red-team challenge, strongest alternative, and final verdict text.
- [x] AC-6: Tests cover happy path, missing verdict, malformed verdict, and prepare/readiness reconciliation.

## Tasks

- [x] Update `wave_review(phase="prepare")` to emit a structured prepare council verdict packet and template.
- [x] Update `wave_prepare(mode="create")` to validate the verdict structure instead of scanning for a substring.
- [x] Update framework seeds and rendered prompts to describe the new required verdict shape.
- [x] Add tests for prepare review write behavior and prepare gate enforcement.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| prepare council verdict | implementer | review pipeline | Produce structured verdict data from the review pass |
| prepare gate enforcement | implementer | prepare council verdict | Block prepare create-mode until verdict is valid |
| tests | qa-reviewer | both implementation workstreams | Verify missing/malformed verdicts fail cleanly |

## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/prompts/prepare-wave.prompt.md`
- `docs/prompts/review-wave.prompt.md`
- `docs/prompts/council-review.prompt.md`

## Affected Architecture Docs

`docs/contributing/review-and-evals.md` should explain that prepare-phase council readiness is now structurally enforced, not just string-matched. The canonical wording belongs in framework seeds; project prompt surfaces are rendered copies.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The core write path must exist and produce the structured prepare verdict |
| AC-2 | required | The gate must reject missing council evidence |
| AC-3 | required | The gate must reject incomplete or malformed evidence |
| AC-4 | required | Readiness and council review both remain mandatory |
| AC-5 | required | The verdict must include the red-team challenge, strongest alternative, and final verdict text |
| AC-6 | required | Prevents regressions in the enforcement path and keeps the gate behavior covered by tests |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-27 | Drafted from the missed prepare-council enforcement gap identified during wave-1 review. Canonical contract lives in framework seeds, with `docs/prompts/` as generated surfaces. | `server_impl.py` prepare gate and review flow; framework seed surfaces |
| 2026-05-27 | Implemented structured prepare-council gate enforcement, updated the canonical seed/prompt contract, and added targeted tests for happy path, missing verdict, and malformed verdict cases. | `server_impl.py`, `graph_indexer.py`, `test_server_tools.py`, `test_graph_indexer.py`, `test_docs_lint.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-27 | Require a structured council verdict rather than a substring marker. | Substring checks are too easy to spoof and do not capture enough review evidence. | Leave the existing `prepare-council` substring check in place — rejected |
| 2026-05-27 | Keep `wave-council-readiness` as a separate signoff. | Readiness signoff and council verdict serve different purposes and should not be collapsed. | Replace the signoff with the verdict block — rejected |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Verdict schema becomes too rigid for future council needs | Keep the required fields small and stable; validate structure, not exact prose |
| Review tooling and prepare gate drift apart | Add tests for both write and validation paths and keep the verdict shape centralized |
| Existing docs/prompts become inconsistent with enforcement | Update the prepare/review/council prompts in the same wave |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
