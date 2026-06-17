# reality-checker: precise scope-guard (silent creep yes, approved scope no)

Change ID: `1p60k-enh reality-checker-scope-guard-precision`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-16
Wave: `1p5x8 large-codebase-map`
Last verified: 2026-06-16

## Rationale

Operator feedback: the reality-checker keeps surfacing **process/scope-governance** commentary ("scope sprawl", "the wave grew beyond its title", "this change is off-theme") in delivery reviews. That is noise — scope is the operator's call, and the changes in question were operator-directed. Source: `216-reality-checker.prompt.md` `implementation-challenge` mode ("no silent scope expansion") is leaking onto operator-approved scope changes.

**The guardrail must be preserved.** The original intent — catch *unasked / unapproved* scope creeping in — is valuable and must NOT be weakened. The fix is precision, not removal: flag implementation that **isn't traceable to an admitted change doc / ACs** (genuine silent creep); never flag scope the operator approved (admitted changes, a wave accumulating approved changes). The reviewer's job is implementation substance, not wave governance.

## Requirements

1. **Preserve the guardrail (load-bearing).** The seed must still explicitly instruct the reality-checker to flag **silent scope expansion** — implementation that exceeds its admitted change doc / ACs, or behavior added with no admitting change. State this affirmatively ("still DO flag …") so the change can't be misread as "stop checking scope."
2. **Operationalize the distinction.** Untraceable-to-an-admitted-change → flag (silent creep). Operator-directed / admitted → not a finding. The test is traceability to a change doc / operator instruction.
3. **Remove the noise.** Add a `Do Not` instructing the reality-checker not to comment on wave scope/process/governance (operator-directed changes, "growing beyond its title", "off-theme") — and to focus on implementation substance (assumptions, evidence, failure modes, correctness).
4. Generic + seed-first (applies to every project's reality-checker).

## Acceptance Criteria

- [x] AC-1: `216-reality-checker.prompt.md` `implementation-challenge` mode flags only scope **not traceable to an admitted change doc / ACs** (silent creep), explicitly NOT operator-directed/approved scope; the affirmative "still DO flag silent scope expansion (impl beyond its change doc/ACs)" guardrail is stated so it isn't read as "stop checking scope."
- [x] AC-2: A `Do Not` bullet removes wave scope/process/governance commentary and refocuses on implementation substance. Generic, no project-specific content; docs-lint clean.

## Tasks

- [x] Refine the `implementation-challenge` mode line (silent/untraceable creep only; affirmative guardrail).
- [x] Add the `Do Not` bullet (no process/governance commentary; implementation substance).
- [x] docs-lint + render parity (seed-first).

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The guardrail (catch unapproved creep) must survive while the noise goes. |
| AC-2 | required | Removing the process-commentary noise is the operator ask. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | Operator: reality-checker keeps flagging operator-directed scope changes as "sprawl" — noise. Keep the silent-creep guardrail; remove the approved-scope commentary. | `216-reality-checker.prompt.md:15` |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
