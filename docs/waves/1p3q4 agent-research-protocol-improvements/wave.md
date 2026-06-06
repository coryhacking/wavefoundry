# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-06

wave-id: `1p3q4 agent-research-protocol-improvements`
Title: Agent Research Protocol Improvements

## Objective

Apply multi-angle research discipline — null-result surfacing, hypothesis falsification, and independence before convergence — to the three highest-frequency agent surfaces: Guru (question answering), Wave Council, and Archetype Council. All changes are seed-level protocol additions with no infrastructure dependency; they are a sequential-execution prerequisite for the workflow-era parallel implementations planned in `1p3ao`.

## Changes

Change ID: `1p3q1-enh guru-multi-angle-research-protocol`
Change Status: `implemented`

Change ID: `1p3q2-enh council-protocol-null-findings-primer-independence-moderator-falsification`
Change Status: `implemented`

Completed At: 2026-06-06

## Wave Summary

Wave `1p3q4` (Agent Research Protocol Improvements) delivered two changes: Guru multi-angle research protocol and Council protocol — null findings, primer independence, moderator falsification, axis declaration. Notable adjustments during implementation: Council protocol — null findings, primer independence, moderator falsification, axis declaration: In-session fix (RC-ADV-1): added auditability-not-isolation explanation to seed-215 Step 1. "Do not read yet" without a why invites mechanical compliance; explaining that sequential execution makes true isolation impossible — and that the step is an auditability discipline — gives agents the intent they need to apply the step in good faith.; Council protocol — null findings, primer independence, moderator falsification, axis declaration: In-session addition: mandatory Recommendations Verdict table added to synthesis in seed-215 and seed-236. Every advisory and recommended finding must be verdicted fix-now / defer / accept with a one-line rationale before the council output is complete. Motivated by delivery council review revealing that the advisory aggregate was never acted on — the operator had to ask separately what to do with each finding.

**Changes delivered:**

- **Guru multi-angle research protocol** (`1p3q1-enh guru-multi-angle-research-protocol`) — 11 ACs completed. Key decisions: Sequential multi-angle protocol (not parallel); Exempt `instructional` question type from decomposition
- **Council protocol — null findings, primer independence, moderator falsification, axis declaration** (`1p3q2-enh council-protocol-null-findings-primer-independence-moderator-falsification`) — 17 ACs completed. Key decisions: One change doc covering both councils rather than two separate docs.; Pre-primer statement is one sentence, not a full independent review pass.
## Journal Watchpoints

- **watchpoint — seed edit gate:** Both changes touch framework seeds. `wave_gate_open(gate="seed_edit_allowed")` required before any seed edit; close immediately after each change.
- **watchpoint — adjacent section drift:** `1p3q1` and `1p3q2` insert into existing seeds without rewriting surrounding sections. Diff review AC is the guard; follow-up if any non-insertion-point lines change.
- **block if scope expands to `1p3ao` T1.1/T1.3:** These are sequential-protocol improvements only. If implementation surfaces a need to also change workflow-era surfaces, defer to `1p3ao` rather than expanding scope here.
- `1p3q1` and `1p3q2` edit independent seed files (`seed-211`, `seed-215`, `seed-236`) and can proceed in parallel; both must complete before final docs-lint.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-06: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: formal-compliance-without-substantive-application — agents can include falsification/pre-primer sections nominally without applying them genuinely; addressed by auditability design which makes compliance visible and reviewable; strongest-alternative: none stronger than framing-layer approach for sequential era)

## Review Evidence

- wave-council-readiness: approved 2026-06-06 — PASS WITH IN-SESSION FIXES (moderator: wave-council; seats: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; depth: standard; must-fix-count: 0; recommended-count: 1 applied in-session [DC-1 pre-primer format covers lightweight-tier skip]; advisory-count: 3; strongest-challenge: formal-compliance-without-substantive-application — addressed by auditability design; verdict: PASS)
- wave-council-delivery: approved 2026-06-06 — PASS (moderator: wave-council; seats: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, rotating-fifth-cross-cutting; depth: standard; must-fix-count: 0; advisory-count: 2 [Arch-ADV-1 deferred to council-protocol-depth-tiering follow-on; RC-ADV-1 fixed in-session]; strongest-challenge: protocol complexity growth across multiple review iterations; verdict: PASS)
- operator-signoff: approved 2026-06-06

## Dependencies

- No external wave dependencies.
