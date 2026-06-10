# Secrets Gate Failure Messaging Clarity

Change ID: `1p451-enh secrets-gate-failure-messaging`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-06-09
Wave: 1p44n framework-1p6-hardening

## Rationale

The secrets false-positive gate emits two failure messages that misdescribe how to clear the gate, leaving operators with no actionable path. In `secrets_validators.py:641-645`, when the current reviewer has already confirmed, the message reads `... needs {needed} more from a different reviewer` — but for a lone maintainer (where `M` derives from the install-time committer count), this instructs an impossible action: there is no second reviewer to recruit. In `secrets_validators.py:647-653`, the `unconfirmed false positive — N of M confirmations ...` branch tells the reader to "review and confirm or escalate" without naming where the threshold lives or how to change it.

Neither message references `docs/scan-rules.toml`, the `false_positive_confirmations_required` policy key, the fact that the threshold is operator-tunable, or that `M` was auto-detected from committer count at install. The path constant `SCAN_RULES_PROJECT_PATH` (`'docs/scan-rules.toml'`, `constants.py:258`) is defined but never surfaced to the operator in these failures. This is the messaging sub-case of `1p44y`, which edits the same message region and introduces the override/escape semantics these messages must accurately describe.

## Requirements

1. Rewrite the already-confirmed branch (`secrets_validators.py:641-645`) so it names `docs/scan-rules.toml` and the `false_positive_confirmations_required` key, states the value is operator-tunable and was auto-detected from committer count at install, and removes the impossible "needs N more from a different reviewer" instruction for the lone-maintainer case.
2. Rewrite the unconfirmed branch (`secrets_validators.py:647-653`) so it names `docs/scan-rules.toml` and the `false_positive_confirmations_required` key, states the value is operator-tunable and install-derived, and points to the actual escape/override path.
3. Once `1p44y` lands, both messages must describe the real escape/override path it introduces rather than the misleading "needs N more from a different reviewer" guidance.
4. Sequence this change after `1p44y` so the override semantics referenced in the new message text exist and are stable; coordinate the shared `secrets_validators.py:641-653` region between the two changes.

## Scope

**Problem statement:** The two false-positive gate-failure messages misdescribe the fix path: they omit the policy file, the policy key, the tunability of the threshold, and the install-time derivation of `M`, and one of them instructs a lone maintainer to do the impossible.

**In scope:**

- Rewriting the message text in both branches at `secrets_validators.py:641-645` and `secrets_validators.py:647-653`.
- Referencing `docs/scan-rules.toml` and the `false_positive_confirmations_required` key (consistent with `SCAN_RULES_PROJECT_PATH` at `constants.py:258`) in the failure output.
- A test asserting the new message content.

**Out of scope:**

- Changing the gate's confirmation logic, thresholds, or override mechanism (owned by `1p44y`).
- Altering how `M` is computed at install time.
- The `suspected-secret` and `confirmed-secret` branch messages (`secrets_validators.py:655-667`).

## Acceptance Criteria

- [x] AC-1: The already-confirmed branch message names `docs/scan-rules.toml` and the `false_positive_confirmations_required` key, states the threshold is operator-tunable and auto-detected from committer count at install. — shared `_policy_hint` references `SCAN_RULES_PROJECT_PATH`. Test: `test_false_positive_below_threshold_user_already_in_list`.
- [x] AC-2: The unconfirmed branch message names `docs/scan-rules.toml` and the `false_positive_confirmations_required` key, states the threshold is operator-tunable and install-derived. — same `_policy_hint`. Test: `test_false_positive_below_threshold_user_not_in_list`.
- [x] AC-3: Both messages describe the actual escape/override path introduced by `1p44y` and no longer instruct an impossible action. — the hint lists "another reviewer's confirmation / lower the threshold / set an `override_reason`"; `more from a different reviewer` removed (asserted absent).
- [x] AC-4: A regression test asserts the content of both rewritten branch messages, including the policy file name, the policy key, and the tunability statement. — the two existing branch tests updated to assert the new content.
- [x] AC-5: This change is sequenced after `1p44y` and uses the override path semantics `1p44y` defines, with no conflicting edits to the shared region. — `1p44y` (control flow) then `1p451` (message strings) on the same branch, no clobber.

## Tasks

- [x] Confirm `1p44y` has landed and review the override/escape path it introduces for the false-positive gate.
- [x] Rewrite the already-confirmed branch message.
- [x] Rewrite the unconfirmed branch message.
- [x] Reference the policy path via `SCAN_RULES_PROJECT_PATH` / `docs/scan-rules.toml` and the `false_positive_confirmations_required` key in both messages. — via the shared `_policy_hint`.
- [x] Add or extend a test asserting both rewritten message strings. — the two existing branch tests updated.
- [x] Run the framework test suite and the secrets validator tests. — 11 false-positive-branch tests green; full suite at wave-end.

## Agent Execution Graph


| Workstream             | Owner       | Depends On   | Notes                                                        |
| ---------------------- | ----------- | ------------ | ------------------------------------------------------------ |
| message-rewrite        | Engineering | 1p44y        | Edit both branches at secrets_validators.py:641-653          |
| regression-test        | Engineering | message-rewrite | Assert new message content for both branches              |


## Serialization Points

- `secrets_validators.py:641-653` — same message region edited by `1p44y`; this change must be sequenced after `1p44y` to avoid conflicting edits and to reference the override path it introduces.

## Affected Architecture Docs

N/A — message-string change confined to a single validator module with no boundary, flow, or verification-architecture impact.

## AC Priority


| AC   | Priority   | Rationale                                                                 |
| ---- | ---------- | ------------------------------------------------------------------------- |
| AC-1 | required   | Core fix: already-confirmed branch must name policy file, key, tunability |
| AC-2 | required   | Core fix: unconfirmed branch must name policy file, key, tunability       |
| AC-3 | required   | Removes the impossible instruction and ties to the real override path     |
| AC-4 | important  | Regression test locks message content against future drift                |
| AC-5 | required   | Coordination with 1p44y prevents merge conflict and stale override text   |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-08 | Rewrote both false-positive failure messages via a shared `_policy_hint` (names `docs/scan-rules.toml` + `false_positive_confirmations_required`, states tunable/install-derived, lists the 1p44y override/escape paths); removed "needs N more from a different reviewer". Updated the two existing branch tests. | `secrets_validators.py`; `TestExceptionStatus` (updated). |


## Decision Log


| Date       | Decision                                                                 | Reason                                                                                          | Alternatives                                                                       |
| ---------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 2026-06-08 | Sequence after 1p44y and reuse its override path in the new message text | 1p44y owns the escape/override semantics and edits the same region; describing it before it lands would be inaccurate | Land independently and patch messages later — rejected, would ship stale guidance  |
| 2026-06-08 | Surface `docs/scan-rules.toml` + `false_positive_confirmations_required` directly in failures | Operators currently have no in-message pointer to the tunable policy; `SCAN_RULES_PROJECT_PATH` exists but is never shown | Document only in external docs — rejected, gate failure is the actionable moment    |


## Risks


| Risk                                                                 | Mitigation                                                                          |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Merge conflict with 1p44y on the shared `:641-653` region            | Sequence after 1p44y; rebase and re-apply message edits on top of its changes        |
| Message text drifts from the override path 1p44y actually implements | Reference the same override mechanism 1p44y defines; lock content with AC-4 test     |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
