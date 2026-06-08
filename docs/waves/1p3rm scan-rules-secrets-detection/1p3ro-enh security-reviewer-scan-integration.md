# Security Reviewer Scan Integration

Change ID: `1p3ro-enh security-reviewer-scan-integration`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-06
Wave: `1p3rm scan-rules-secrets-detection`

## Rationale

The security reviewer (seed-213) currently checks for runtime credential exposure (logging, echoing) but has no step for static credential presence in files. The scan-rules engine (`1p3rn`) provides the detection infrastructure; this change wires it into the agent's review protocol. The step runs pre-scope so it cannot be excluded by `explicit_non_goals` in the briefing packet. The agent provides the judgment layer the lint check cannot: distinguishing test fixtures, placeholder values, and environment-variable reads from actual hardcoded credentials, and presenting `pending` exceptions to the operator for confirmation.

## Requirements

1. A new pre-scope step is added to seed-213, executing before Step 0 (Scope Definition) and before `explicit_non_goals` is read.
2. The pre-scope step reads `docs/scan-exceptions.json`. If the file is absent, the step records a null-finding and continues.
3. For each entry the agent acts based on status:
   - `pending`: agent reads file and line, applies judgment heuristics (Requirement 6), and sets `status` to `false-positive`, `suspected-secret`, or `confirmed-secret`. Then proceeds as below.
   - `false-positive` (insufficient confirmations, current git user not in list): agent presents context, existing confirmations, and remaining count. Asks current user to confirm or escalate. If confirmed, appends confirmation entry with UTC datetime. If escalated, sets `status: suspected-secret`.
   - `false-positive` (insufficient confirmations, current git user already in list): agent shows progress message only — no action required from current user.
   - `false-positive` (confirmation count met): no action, no report.
   - `suspected-secret`: agent stops, reads the file and surrounding context, presents full analysis to operator, and asks to classify as `false-positive` or `confirmed-secret`. Must not proceed past this entry without resolution.
   - `confirmed-secret`: agent reports as `critical` finding regardless of `explicit_non_goals`; presents for wave-close acknowledgment if close is in progress.
4. For each entry with `status: false-positive` where confirmation count is met: no action, no report.
6. The judgment heuristics for `pending` classification are documented in the seed. Heuristics are evaluated in priority order — the first match wins:
   1. `env-var-read` (highest priority): RHS is a call to `os.environ`, `os.getenv`, `process.env`, or equivalent — set `status: false-positive`, append agent confirmation, no operator prompt required.
   2. `real-credential`: matched text has high specificity (provider prefix match, e.g. `AKIA`, `sk_live_`, `ghp_`, `-----BEGIN`) and does not match env-var-read — set `status: suspected-secret`, prompt operator.
   3. `test-fixture`: file path contains `test`, `fixture`, `mock`, `spec`, or `__test__` — recommend `false-positive`, prompt operator to confirm.
   4. `placeholder`: matched text contains `YOUR_`, `<`, `>`, `INSERT`, `REPLACE`, `example`, `fake`, `test`, `dummy`, or `xxx` (case-insensitive) — recommend `false-positive`, prompt operator to confirm.
   5. `ambiguous` (lowest priority): does not fit any of the above; set `status: suspected-secret`, present context to operator without a pre-formed recommendation.
7. The operator prompt includes: file path, line number, redacted matched text, rule ID, classification, recommended verdict, existing confirmations (git name + UTC datetime for each), and remaining count needed. On operator acceptance, the agent:
   - Runs `git config user.name` and `git config user.email` to capture the current user's identity.
   - Appends a confirmation entry to `confirmations[]` with the verdict, reason, git identity, and current UTC ISO-8601 datetime.
   - Sets `status` explicitly to the operator's verdict (`false-positive` or `confirmed-secret`).
   - For `confirmed-secret` acceptances intended for close, also writes `acknowledged_for_wave: "<current_wave_id>"`.
   - If the current git user's email already appears in `confirmations`, informs the operator their confirmation is recorded and a different reviewer is needed.
8. The pre-scope step emits a null-finding declaration when no entries require action: "No actionable entries in scan-exceptions.json."
9. The existing Step 4 (Sensitive Data Exposure) is updated to clarify it covers runtime exposure only and explicitly cross-references the pre-scope step for static credential presence.

## Scope

**Problem statement:** The security reviewer has no step for detecting hardcoded credentials in files, and agents can be configured via `explicit_non_goals` to skip security steps. Credentials need an ungated review path.

**In scope:**

- seed-213 (`213-security-reviewer.prompt.md`) — pre-scope step addition and Step 4 clarification
- Judgment heuristics documented in the seed
- Operator prompt format

**Out of scope:**

- The exceptions file schema — defined in `1p3rn`
- The lint validator — defined in `1p3rn`
- Wave close gate — defined in `1p3rp`
- PHI/PII/PCI classification heuristics — follow-on wave

## Acceptance Criteria

- [x] AC-1: seed-213 contains a pre-scope step that runs before Step 0 and before `explicit_non_goals` is applied.
- [x] AC-2: Pre-scope step reads `docs/scan-exceptions.json`; absent file is a null-finding, not an error.
- [x] AC-3: `env-var-read` classification sets `status: false-positive` and appends an agent confirmation automatically with no operator prompt.
- [x] AC-4: `placeholder` and `test-fixture` classifications recommend `false-positive` and prompt operator before setting status and appending confirmation.
- [x] AC-5: `real-credential` classification sets `status: suspected-secret` and prompts operator to classify as `false-positive` or `confirmed-secret`.
- [x] AC-6: `confirmed-secret` entries are always reported as `critical` findings regardless of `explicit_non_goals`.
- [x] AC-7: Operator prompt includes file, line, redacted text, rule ID, classification, recommended verdict, existing confirmations (names + dates), and remaining count needed.
- [x] AC-8: Agent appends to `confirmations[]` with git user identity, verdict, reason, and UTC ISO-8601 datetime. Agent sets `status` explicitly — validator does not change status.
- [x] AC-9: Null-finding declaration emitted when no entries require action (no `pending`, `suspected-secret`, or `confirmed-secret` entries needing attention).
- [x] AC-10: Step 4 updated to clarify runtime-only scope and cross-reference the pre-scope step.
- [x] AC-11: If the current git user's email already exists in `confirmations` for an entry, agent informs operator their confirmation is already recorded and a different reviewer is required.
- [x] AC-12: `confirmed-secret` acceptance for close writes `acknowledged_for_wave` in addition to the confirmation entry.

## Tasks

- [x] Open seed edit gate (`wave_gate_open(gate="seed_edit_allowed")`)
- [x] Add pre-scope step to seed-213 with judgment heuristics and operator prompt format
- [x] Update Step 4 in seed-213 with runtime-only clarification and cross-reference
- [x] Close seed edit gate (`wave_gate_close(gate="seed_edit_allowed")`)
- [x] Verify seed-213 renders correctly and lint passes

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| seed-213 pre-scope step | software-engineer | `1p3rn` complete (schema stable) | Single seed edit; open/close gate wraps the edit |
| seed-213 Step 4 update | software-engineer | pre-scope step | Edit in same session after pre-scope step |

## Serialization Points

- Seed edit gate must be open for the duration of seed-213 edits and closed immediately after.

## Affected Architecture Docs

N/A — seed-level protocol addition only. No infrastructure, schema, or boundary change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Pre-scope placement is the core safety property |
| AC-2 | required | Absent file must not block reviews in new projects |
| AC-3 | required | env-var-read auto-classification reduces noise |
| AC-4 | required | Placeholder/fixture must prompt, not auto-approve |
| AC-5 | required | Real credentials must always prompt |
| AC-6 | required | confirmed-secret cannot be suppressed by caller |
| AC-7 | required | Operator needs full context to decide |
| AC-8 | required | Write-back closes the review loop |
| AC-9 | required | Null-finding discipline |
| AC-10 | important | Step 4 clarification prevents confusion |
| AC-11 | required | Prevents single-user re-confirmation loop |
| AC-12 | required | acknowledged_for_wave closes the close-gate loop |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| | | |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-06 | Pre-scope placement (before explicit_non_goals) | Prevents briefing packet from suppressing the check | Inside Step 0 — rejected: explicit_non_goals could exclude it |
| 2026-06-06 | env-var-read auto-classifies as `false-positive` (no prompt) | `os.environ.get("KEY")` is the correct pattern; prompting every env-var read causes prompt fatigue | Always prompt — rejected |
| 2026-06-06 | Agent writes back to exceptions file | Closes the review loop; lint check reads confirmed status on next run | Operator writes manually — rejected: error-prone |

## Risks

| Risk | Mitigation |
|---|---|
| Agent misclassifies ambiguous matches | `ambiguous` classification always prompts operator without a pre-formed recommendation; human judgment is final |
| Pre-scope step adds latency to every review | Step exits immediately with null-finding when no pending/confirmed-secret entries exist |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
