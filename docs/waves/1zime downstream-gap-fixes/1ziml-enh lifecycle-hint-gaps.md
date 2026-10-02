# Lifecycle Hints Name the Pending Readiness Lanes, the Unwritten Objective and the Right Verdict Record

Change ID: `1ziml-enh lifecycle-hint-gaps`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zime downstream-gap-fixes

## Rationale

A downstream fork reported three lifecycle hint gaps as still open at commit `5004296a`: "pending lanes at readiness", "objective-review reminder" and "wrong-doc verdict hint". Only those one-line descriptions are available. The hints are the `next_tools`, `usage` and diagnostic `recovery_tools`/`recovery_usage` fields of the lifecycle tool responses. Reading `wf_prepare_wave_response`, `wf_review_wave_response`, `wf_review_event_response` and `wf_close_wave_response` in `wf_server/server_impl.py`, and the gate units in `lifecycle_gates.py` and `lifecycle_gate_support.py`, gives this concrete reading of each:

- **(a) Pending lanes at readiness.** On a declared (`events.jsonl`) wave, readiness needs a `readiness` review run, one current readiness approval per required lane, and the `wave-council-readiness` approval. When Prepare is blocked on the missing council approval (`council_signoff_gate`, code `missing_wave_council_signoff`), the envelope's top-level hint is `usage="wf_validate_docs()"` with `next_tools=["wf_validate_docs", "wf_current_wave"]`: the generic fallback in the activation-blocked branch (`usage_hint = ... if other_active is not None else "wf_validate_docs()"`). The diagnostic's own recovery is `wf_current_wave()`. Validating docs is the wrong next step for a wave whose docs already passed. The pending lanes do appear, but only in the `readiness_lane_approvals_missing` advisory added by `_attach_prepare_readiness_advisories`, whose text ("Re-review the repaired packet and record approvals against the current receipt") is written for a repair round and misleads a first readiness pass. The data carries no list of pending lanes. `wf_review_wave(phase='prepare')` has the opposite defect: when lanes are missing it returns `status="error"` but still recommends `wf_implement_wave(..., mode='dry_run')`. Its `missing_required_lane` diagnostic (`review_lanes_gate`) recovers to `wf_current_wave()`, although the same response already computes `review_actions` with a recommended next action. The readiness-blocked branch of Prepare (`PREPARE_READINESS_GATES`) always recommends `wf_prepare_wave(mode='create')`, which would also OPEN the wave when the caller asked only to ready it. Close's blocked envelope likewise always recommends `wf_validate_docs()`.
- **(b) Objective-review reminder (interpretation, marked as an assumption).** `wf_create_wave` scaffolds `## Objective` with the placeholder `<Describe the wave's load-bearing goal in 1–3 sentences ...>`. Docs-lint only requires the heading to exist (`wave_validators`, "wave doc must declare `## Objective` section"), and no lifecycle tool notices that the placeholder is still there. A wave can therefore be readied, reviewed and shown on the dashboard wave card with no objective, and the readiness council reviews a wave whose goal is unstated. The reminder belongs at Prepare, before the receipt binds the readiness approvals: a later prose edit to the wave record does not rotate the receipt, but reviewers should have seen the objective.
- **(c) Wrong-doc verdict hint.** The council brief returned by every Prepare call (`_prepare_council_instructions` and `_prepare_council_verdict_template` in `lifecycle_gate_support.py`, rebuilt by `_bind_prepare_council_brief_to_receipt`) always tells the agent to "Record the verdict in ## Review Checkpoints with a structured 'prepare-council' line ... before calling wf_prepare_wave(mode='create')". On a declared wave that is the wrong record: the authority is the typed `wave-council-readiness` approval in `events.jsonl` (`council_signoff_gate` says so, and `review_policy_reconcile` states that the prose line "never changes a declared wave's lifecycle outcome"). The scaffold `wf_create_wave` writes has no `## Review Checkpoints` section at all, and `mode='create'` opens the wave. An agent following the brief writes prose the gate ignores, then gets `missing_wave_council_signoff`. On legacy (prose) waves the current text is correct and stays.

## Requirements

1. **Blocked envelopes recommend the first blocking remedy.** In `wf_prepare_wave`, `wf_review_wave` and `wf_close_wave`, an envelope returned with `status="error"` takes its top-level hint from the FIRST blocking diagnostic in emitted order. "Blocking" is the predicate that set the branch's status: `has_blocking_diagnostics` for Prepare and Close; for `wf_review_wave`, the diagnostics in `shared["blocking_diagnostics"]` (implementation phase) or the lint, lane and review-evidence diagnostics (prepare phase). If that diagnostic carries `recovery_usage`, that is the `usage`, and its `recovery_tools` followed by the branch's existing defaults, without duplicates, are the `next_tools`. If it carries none, the branch's existing defaults stand. A later diagnostic's recovery never overrides an earlier blocker. Requirement 4 takes precedence over this rule for the prepare-phase review. Requirement 5 changes the default of the readiness branch, which this rule falls back to. The `another_wave_active` branch keeps its explicit hint. One helper implements this for all three tools.
2. **Readiness remedies name the readiness path.** `missing_wave_council_signoff` (Prepare's `council_signoff_gate`, typed authority) and `missing_required_lane` (`review_lanes_gate`, typed authority) recover with `recovery_tools=["wf_review_wave", "wf_review_event"]` and `recovery_usage=f"wf_review_wave(wave_id={wave_id!r}, phase='prepare')"`, the form `wf_implement_wave`'s readiness diagnostic already uses. Legacy-authority wording and recovery are unchanged.
3. **Prepare reports the pending readiness lanes.** Every `wf_prepare_wave` response's `data` carries `pending_readiness_lanes`: the list `_prepare_lane_review_state` computes (empty when none), or `null` when it cannot be computed (unreadable record or ledger errors, the cases where the advisory is skipped today). The `readiness_lane_approvals_missing` advisory distinguishes the two cases. A lane with no readiness approval recorded at all reads "Readiness approvals still needed from: X" and points at the readiness review. A lane whose approval lapsed with a superseded receipt keeps today's re-review wording.
4. **The prepare-phase review never recommends implementation while it is failing.** `wf_review_wave(phase='prepare')` with `status="error"` follows Requirement 1. When `review_actions.recommended_next_action` exists, the envelope's `usage` names it; the `wf_implement_wave` recommendation is kept only for `status="ok"`.
5. **The readiness-blocked branch keeps the caller's mode.** Where Prepare's readiness-gate block recommends a retry, it recommends `wf_prepare_wave(wave_id=..., mode=<the caller's mode>)`, never `mode='create'` for a `ready` call.
6. **Unwritten objective advisory (assumption, see Decision Log).** `wf_prepare_wave` (every mode) adds an advisory `wave_objective_unpopulated` when the wave record's `## Objective` body, stripped, is empty or consists only of one angle-bracket placeholder (`<...>`), as the `wf_create_wave` scaffold leaves it. The message names the section and says the readiness council and the dashboard wave card read it. Advisory only: it never blocks and never changes status. It is computed in the observational wrapper so that error envelopes carry it too.
7. **The council brief points at the record that counts.** `_prepare_council_instructions` and `_prepare_council_verdict_template` take the resolved authority (typed or legacy) as well as the rotating seat. Both are keyed on the pair, so every producer, including `_bind_prepare_council_brief_to_receipt`, renders the same text for the same roster and authority. For a typed wave the instructions:
   - keep the seat and code-grounding guidance;
   - say to record the readiness run, each required lane's readiness approval and then the council verdict as a typed approval: `wf_review_event(event='approval', signoff_key='wave-council-readiness', ...)`;
   - say any `## Review Checkpoints` narrative is optional and not authority;
   - end with `wf_prepare_wave(mode='ready')`, or `mode='create'` to also open the wave.

   The legacy text is unchanged.
8. **Platforms.** Response text and data only; Windows, macOS, Linux and WSL2 behave the same.
9. **No gate change.** No diagnostic changes severity, no predicate changes, and no blocked response becomes unblocked or the reverse. Only hint fields, messages, one advisory and one data field change.

## Scope

**Problem statement:** lifecycle responses recommend the wrong next step when readiness is incomplete, do not notice an unwritten objective, and tell agents on declared waves to record the council verdict in a prose section the gate ignores.

**In scope:**

- `wf_server/server_impl.py` (`wf_prepare_wave_response`, `_attach_prepare_readiness_advisories`, `wf_review_wave_response`, `wf_close_wave_response`, `_bind_prepare_council_brief_to_receipt`); `lifecycle_gates.py` (`council_signoff_gate`, `review_lanes_gate` recoveries); `lifecycle_gate_support.py` (council instructions and template, `_build_prepare_council_brief`).
- Tests; the lifecycle golden fixture, regenerated deliberately and its diff reviewed; `docs/specs/mcp-tool-surface.md` where it documents these response fields; CHANGELOG `## [Unreleased]` bullet.

**Out of scope:**

- Requiring lane approvals before the council approval, or any other gate change.
- An objective reminder at delivery review or close (the alternative interpretation of (b); see Decision Log).
- Placeholder checks for other scaffold sections (Participants, Watchpoints).
- `wf_review_event`'s continuation `review_actions`, which already name the next action.

## Acceptance Criteria

- [x] AC-1: on a declared fixture wave with lanes recorded but no `wave-council-readiness` approval, `wf_prepare_wave(mode='ready')` returns `status="error"` with top-level `usage` `wf_review_wave(wave_id=..., phase='prepare')` and `next_tools` starting with `wf_review_wave`, not `wf_validate_docs()`. A fixture whose only blocker is a docs-lint failure still recommends `wf_validate_docs()`. The same rule holds for `wf_close_wave` on a fixture blocked by a missing delivery approval. A fixture with both a docs-lint error and a missing `wave-council-readiness` approval still recommends `wf_validate_docs()`.
- [x] AC-2: on a declared wave with no readiness approvals, `wf_prepare_wave` `data.pending_readiness_lanes` equals the required lanes and the advisory reads as a first pass. After one lane approves, that lane leaves the list. After a receipt supersession, the lapsed lane reappears with the re-review wording. An unreadable ledger yields `null` and no advisory.
- [x] AC-3: `wf_review_wave(phase='prepare')` with a missing lane returns `status="error"` whose `usage` is not `wf_implement_wave(...)`, and `missing_required_lane` recovers to `wf_review_wave(..., phase='prepare')` with `wf_review_event` among its tools on a typed fixture; the legacy fixture's wording and recovery are unchanged.
- [x] AC-4: a readiness-gate block in `mode='ready'` recommends `mode='ready'`, not `mode='create'`.
- [x] AC-5: a wave whose `## Objective` is the scaffold placeholder, and one whose section is empty, each get `wave_objective_unpopulated` (advisory) from `wf_prepare_wave` in every mode, including an error envelope. A wave with a written objective does not, and nor does one whose objective sentence merely contains an angle-bracketed term. The status is identical with and without the advisory.
- [x] AC-6: for a typed wave, the council brief's `instructions` and `verdict_format` name `wf_review_event` with `signoff_key='wave-council-readiness'` and do not tell the agent to record the verdict in `## Review Checkpoints` as the authority; for a legacy wave they are byte-identical to today's text; the receipt-bound brief and the unbound brief render the same text for the same seat and authority.
- [x] AC-7: no gate outcome changes. For every fixture in the lifecycle golden, every envelope's `status` and every diagnostic's `code` and `advisory` flag are unchanged. The regenerated envelopes differ from the committed ones only in: `usage`, `next_tools`, and diagnostic `recovery_tools` and `recovery_usage`; the messages of `missing_wave_council_signoff`, `missing_required_lane` and `readiness_lane_approvals_missing`; `data.council_brief.instructions` and `data.council_brief.verdict_format`; and the added `wave_objective_unpopulated` advisory and the added `data.pending_readiness_lanes`. `test_only_declared_observability_additions_since_extraction_golden` is extended to strip exactly these deltas, so the rule is enforced by a test. The reviewed golden diff is recorded in the Progress Log.
- [x] AC-8: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the blocked-envelope hint helper and use it in the Prepare, review and close blocked branches.
- [x] Repoint the typed recoveries of `missing_wave_council_signoff` and `missing_required_lane`.
- [x] Add `pending_readiness_lanes` and the first-pass versus lapsed advisory wording.
- [x] Fix the prepare-phase review's error hint and the readiness-block mode.
- [x] Add the `wave_objective_unpopulated` advisory.
- [x] Key the council instructions and verdict template on authority; update both producers.
- [x] Verified the council brief text is not a review-policy receipt input: `_prepare_policy_state` derives `council_seats` from the canonical change texts and passes no brief field to `policy_input_snapshot`.
- [x] Extend `test_only_declared_observability_additions_since_extraction_golden` with the AC-7 deltas.
- [x] Tests for AC-1 through AC-6; regenerate the lifecycle golden with `WF_UPDATE_LIFECYCLE_GOLDEN=1 WF_OVERWRITE_LIFECYCLE_GOLDEN=1` and review its diff for AC-7.
- [x] Spec and CHANGELOG updates.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Blocked-envelope hints and readiness remedies | implementer | readiness | server_impl and lifecycle_gates |
| Pending lanes and objective advisory | implementer | hints | observational wrapper |
| Council brief by authority | implementer | readiness | lifecycle_gate_support |
| Golden regeneration | implementer | all above | review the diff |
| Review | code-reviewer, qa-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/lifecycle_gates.py`, `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`, `.wavefoundry/framework/scripts/tests/test_readiness_convergence.py`, `.wavefoundry/framework/scripts/tests/test_lifecycle_golden.py`, `.wavefoundry/framework/scripts/tests/fixtures/lifecycle-gate-golden.json`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

N/A. Response hints and one advisory within the existing lifecycle handlers; no gate, flow or ownership change (Requirement 9).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The reported pending-lanes gap: the top-level hint must lead to readiness, not docs validation |
| AC-2 | required | Pending lanes named in data and with the right wording |
| AC-3 | required | A failing prepare review must not recommend implementation |
| AC-4 | important | A ready call must not be steered into opening the wave |
| AC-5 | important | The objective reminder, under the stated interpretation |
| AC-6 | required | The reported wrong-doc verdict hint |
| AC-7 | required | Proves hint-only scope |
| AC-8 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Delivery-review repair round. On a declared wave the delivery `missing_required_lane` (shared delivery evaluator) recovers to `wf_review_wave(wave_id=..., phase='implementation')`; legacy waves keep `wf_review_wave(wave_id=...)`. The prepare-phase review's `usage` is now a pure call expression, `wf_review_event(wave_id=..., <state_args>, actor=...)`, that the served-name hint rewrite renames; the explanation moved to `data.next_action_note`. Golden regenerated and re-reviewed against the committed original: still only AC-7 fields; `recovery_usage` deltas grow from 3 to 12 (the 9 delivery `missing_required_lane` entries in close and review captures); statuses, codes and advisory flags unchanged. Mutants D1 and P1 killed | `lifecycle_gates.py`, `wf_server/server_impl.py`, `tests/test_server_tools_lifecycle.py`, `tests/fixtures/lifecycle-gate-golden.json` |
| 2026-10-01 | Implemented. One helper, `_blocked_envelope_hint`, takes the top-level hint of a blocked Prepare (activation and readiness branches), review (prepare phase over the lint, lane and review-evidence blockers; implementation phase over `blocking_diagnostics`) and close envelope from the first blocking diagnostic; the prepare-phase review names `review_actions.recommended_next_action` as a `wf_review_event(...)` call when one exists and recommends `wf_implement_wave` only on `ok`; the readiness branch defaults to `wf_prepare_wave(wave_id=..., mode=<caller's mode>)`. Typed `missing_wave_council_signoff` and prepare-phase `missing_required_lane` recover to `wf_review_wave(wave_id=..., phase='prepare')` with `wf_review_event`. `_attach_prepare_readiness_advisories` sets `data.pending_readiness_lanes` (None before resolution and on ledger errors), splits first-pass from lapsed wording through `signoff_recorded`, and adds `wave_objective_unpopulated`. Council instructions and template take `typed`; both producers and the bind pass it. Red first: 17 failures and 5 errors in `LifecycleHintGapTests` (15 tests) on the pre-change code. Golden regenerated with both variables and reviewed: statuses, codes and advisory flags unchanged in all 18 envelopes; deltas are `usage` and `next_tools` (12 envelopes: prepare `missing_lane` x3 now `wf_review_wave(..., phase='prepare')`, close x6 and review:implementation x3 now the first blocker's `wf_current_wave()`), `recovery_tools`/`recovery_usage` of `missing_wave_council_signoff` (3), messages of `missing_wave_council_signoff` (3) and `readiness_lane_approvals_missing` (6), `council_brief.instructions` and `verdict_format` (9 each), `wave_objective_unpopulated` added (9) and `data.pending_readiness_lanes` added (9); no other field. The observability golden test strips exactly these deltas. Three existing tests updated for the new advisory: the sanctioned advisory-site set and two exact advisory lists in `WaveCouncilPolicyTests` | `wf_server/server_impl.py`, `lifecycle_gates.py`, `lifecycle_gate_support.py`, `tests/test_server_tools_lifecycle.py` (`LifecycleHintGapTests`), `tests/test_lifecycle_golden.py`, `tests/fixtures/lifecycle-gate-golden.json` |
| 2026-10-01 | Planned from the downstream report (one-line descriptions only). Verified by reading: Prepare's activation-blocked branch falls back to `usage="wf_validate_docs()"`; `council_signoff_gate` recovers to `wf_current_wave()`; `_attach_prepare_readiness_advisories` names missing lanes with repair wording only; `wf_review_wave(phase='prepare')` returns `wf_implement_wave` usage on error; the readiness-blocked branch recommends `mode='create'`; `_prepare_council_instructions` names `## Review Checkpoints` and `mode='create'` for every authority; the `wf_create_wave` scaffold has no `## Review Checkpoints` section and leaves `## Objective` as a placeholder nothing checks | `wf_server/server_impl.py`, `lifecycle_gates.py`, `lifecycle_gate_support.py`, `wave_lint_lib/wave_validators.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-01 | Read "pending lanes at readiness" as the wrong top-level hint plus unnamed pending lanes when readiness is incomplete | The lanes are only in an advisory with repair-round wording, and the top-level hint leads to `wf_validate_docs()`; the code offers no other reading of a readiness hint gap | Gate the council approval on lane approvals (a gate change, out of scope) |
| 2026-10-01 | Read "objective-review reminder" as an advisory for the unwritten scaffold Objective at Prepare (ASSUMPTION) | It is the only objective-related check missing from the lifecycle tools; the placeholder survives readiness unnoticed today, and Prepare is when reviewers first read the wave | Remind delivery reviewers or close to check delivery against the Objective (seed 200 asks closure to state whether the objective was met); confirm with the reporter, and add it as a follow-up if that was meant |
| 2026-10-01 | Read "wrong-doc verdict hint" as the council brief naming `## Review Checkpoints` on declared waves | On declared waves the authority is the typed `wave-council-readiness` approval; the brief names a prose section that the scaffold lacks and the gate ignores | Also add `## Review Checkpoints` to the scaffold (keeps a non-authoritative section alive) |
| 2026-10-01 | One helper derives blocked-envelope hints from the first blocking diagnostic | The defect is the same fixed fallback in three tools; deriving from the diagnostic keeps hint and cause together | Per-branch hard-coded hints (repeats the defect's shape) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Changing hint text churns the lifecycle golden and tests that pin `wf_validate_docs()` usage | Regeneration is explicit (both environment variables) and the diff is reviewed against AC-7's allowed fields |
| The council brief text feeds a receipt digest, so rewording rotates receipts on open waves | Task verifies this before the edit; stop and raise it if true |
| The objective interpretation is not what the reporter meant | Advisory only, cheap to keep; the alternative is recorded for follow-up |
| Wave 1zimf edits `server_impl.py` concurrently | Serialization point declared; rebase on whichever lands first |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
