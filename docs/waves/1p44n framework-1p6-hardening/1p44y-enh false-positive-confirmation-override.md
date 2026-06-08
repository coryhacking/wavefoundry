# False-Positive Confirmation Override And Reviewer-Count Clamp

Change ID: `1p44y-enh false-positive-confirmation-override`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-08
Wave: 1p44n framework-1p6-hardening

## Rationale

A secrets-scan finding classified as `false-positive` can become an *unsatisfiable* hard gate failure with no escape path, which is strictly worse than the treatment of more-severe findings.

In `secrets_validators.py`, the `status == "false-positive"` branch (`secrets_validators.py:631-653`) suppresses the failure ONLY when `count >= required_confirmations` (`:633`). Every other path appends a failure — there is no `override_reason`, no `acknowledged_for_wave`, and no self-confirm escape. The confirmation count itself comes from `_unique_confirmation_count` (`secrets_validators.py:388-398`), which dedupes by `git_user_email` with no bot/activity filtering. `required_confirmations` is read from merged policy at `secrets_validators.py:699` (`false_positive_confirmations_required`, default 2); because the install threshold is derived from raw committer count with no live-reviewer clamp, bots and inactive co-authors inflate it. Example: a repo with 5 committer emails (including a GitHub `noreply` bot) yields a threshold of 2 that a lone active maintainer cannot meet — the gate is permanently red.

This is asymmetric: the MORE-severe statuses already have an escape. `_check_secrets_gate` in `server_impl.py:7908-7925` lets `confirmed-secret`/`suspected-secret` findings be dismissed via `acknowledged_for_wave == canonical_wave_id` plus a non-empty `override_reason`. The least-severe status (`false-positive`) is the only one with no operator override — the opposite of what severity should imply.

This change restores parity (an operator `override_reason` dismissal on the false-positive branch) and removes the structural deadlock (clamp `required_confirmations` to the count of currently-confirmable, non-bot reviewers) so a single active maintainer can always pass the gate on a genuine false positive.

## Requirements

1. The `false-positive` branch in `check_hardcoded_secrets` must accept an operator dismissal: a finding with a non-empty `override_reason` (mirroring the `_check_secrets_gate` contract at `server_impl.py:7908-7925`) is suppressed instead of producing a gate failure, even when `count < required_confirmations`.
2. `required_confirmations` used by the false-positive branch must be clamped to the count of currently-confirmable reviewer emails (recent, non-bot) before the `count >= required_confirmations` comparison at `secrets_validators.py:633`, computed in `check_hardcoded_secrets` before that line is reached.
3. "Confirmable reviewer" filtering must exclude obvious bot/no-reply emails (e.g. addresses matching the GitHub `noreply` / `*[bot]*` patterns) and inactive co-authors, so a lone active maintainer is never blocked by inflated thresholds.
4. The clamp must never RAISE `required_confirmations` above its policy value — it may only lower it toward the confirmable-reviewer count (floor of 1 when at least one confirmer exists).
5. The override dismissal and the clamp must be independent: either one alone must be sufficient to let a single active maintainer pass the gate; neither may weaken the multi-reviewer intent when more reviewers genuinely exist.
6. Failure-message strings emitted by the false-positive branch (`secrets_validators.py:636-653`) that change must be coordinated with change `1p451` (same message strings) so the two changes do not clobber each other.

## Scope

**Problem statement:** A `false-positive` secrets finding is the only gate status with no operator escape (`secrets_validators.py:631-653`), and its `required_confirmations` threshold (`:699`) is inflated by bot/inactive emails because `_unique_confirmation_count` (`:388-398`) does no activity filtering — so a lone active maintainer faces a permanently-failing, unsatisfiable hard gate, despite more-severe statuses being dismissible via `override_reason` (`server_impl.py:7908-7925`).

**In scope:**

- Add an operator `override_reason` dismissal path to the `false-positive` branch in `check_hardcoded_secrets`, mirroring the `_check_secrets_gate` confirmed/suspected-secret contract.
- Clamp `required_confirmations` against the count of currently-confirmable (recent, non-bot) reviewer emails before the `count >= required_confirmations` check at `secrets_validators.py:633`.
- A reviewer-confirmability helper (recent + non-bot filtering) used to compute the clamp.
- Updated failure-message wording on the false-positive branch where it must reflect the override/clamp behavior, coordinated with `1p451`.
- Unit tests for the override path and the clamp.

**Out of scope:**

- Changes to the `confirmed-secret`/`suspected-secret` gate logic in `server_impl.py` beyond reading it as the parity reference.
- A blanket `allow_self_confirm` option (explicitly rejected — it defeats the multi-reviewer intent; see Decision Log).
- Re-deriving the install-time `false_positive_confirmations_required` policy default in the installer (that threshold-at-install fix is a separate concern).
- Changes to `_unique_confirmation_count`'s dedupe semantics for the non-false-positive branches.

## Acceptance Criteria

- [ ] AC-1: A `false-positive` finding with a non-empty `override_reason` is suppressed (no failure appended) by `check_hardcoded_secrets` even when `count < required_confirmations`, matching the dismissal contract in `server_impl.py:7908-7925`.
- [ ] AC-2: When the set of currently-confirmable (recent, non-bot) reviewer emails is smaller than the policy `required_confirmations`, the threshold compared at `secrets_validators.py:633` is clamped down to that confirmable count (floor 1), so a single active maintainer's confirmation satisfies the gate.
- [ ] AC-3: The clamp never raises `required_confirmations` above its policy value; when two or more confirmable reviewers exist, the original multi-reviewer threshold is preserved.
- [ ] AC-4: Bot / no-reply emails (e.g. GitHub `noreply` and `*[bot]*` addresses) are excluded from the confirmable-reviewer count, so they cannot inflate the effective threshold.
- [ ] AC-5: A `false-positive` finding with an empty/absent `override_reason` AND an unmet (post-clamp) confirmation count still fails the gate with an actionable message (deadlock removed, but the gate is not silently disabled).
- [ ] AC-6: Regression — existing `secrets_validators` test suite passes unchanged, and `python3 .wavefoundry/framework/scripts/run_tests.py` is green.
- [ ] AC-7: New unit tests cover (a) the `override_reason` dismissal path and (b) the reviewer-count clamp, including the bot-exclusion case from AC-4.
- [ ] AC-8: Any false-positive-branch failure-message string changes are reconciled with change `1p451` so both changes' expected message strings match the shipped text (verified by a shared-string check / coordinated test).

## Tasks

- [ ] Read the parity contract in `server_impl.py:7908-7925` (`acknowledged_for_wave == canonical_wave_id` + non-empty `override_reason`) and the false-positive branch at `secrets_validators.py:631-653` to confirm field names.
- [ ] Add a confirmable-reviewer helper (recent + non-bot email filter) near `_unique_confirmation_count` in `secrets_validators.py`.
- [ ] In `check_hardcoded_secrets`, compute the clamped `required_confirmations` (min of policy value and confirmable-reviewer count, floor 1) before the false-positive comparison.
- [ ] Add the `override_reason` dismissal check to the `false-positive` branch, suppressing the failure when an operator override is present.
- [ ] Update the false-positive failure-message strings as needed and coordinate wording with `1p451`.
- [ ] Add unit tests for the override path, the clamp, and bot exclusion (AC-7).
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and fix any regressions.
- [ ] Run `.wavefoundry/bin/docs-lint` on this plan and resolve findings.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| reviewer-clamp-helper | Engineering | — | Confirmable-reviewer (recent, non-bot) email filter helper in `secrets_validators.py`. |
| override-and-clamp-branch | Engineering | reviewer-clamp-helper | Wire override_reason dismissal + clamp into the false-positive branch / `check_hardcoded_secrets`. |
| message-coordination | Engineering | override-and-clamp-branch | Reconcile false-positive message strings with change 1p451. |
| tests | Engineering | override-and-clamp-branch | Override path, clamp, bot-exclusion tests; run full suite. |

## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py` — shared with changes `1p44s`, `1p44v`, `1p44x`, and `1p451`; edits must be coordinated to avoid clobbering. The false-positive failure-message strings overlap specifically with `1p451`.
- `.wavefoundry/framework/scripts/server_impl.py:7908-7925` — read-only parity reference for the `override_reason` / `acknowledged_for_wave` dismissal contract; do not diverge from it.

## Affected Architecture Docs

N/A — the change is confined to the secrets-gate validator module (`secrets_validators.py`) and reuses the existing dismissal contract already documented by `server_impl.py`'s `_check_secrets_gate`; it introduces no new module boundary, data flow, or verification surface.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Restores override parity; the core deadlock-escape for false positives. |
| AC-2 | required | Removes the structural unsatisfiable-gate condition for a lone maintainer. |
| AC-3 | required | Guards against the clamp silently weakening the multi-reviewer intent. |
| AC-4 | important | Bot exclusion is the concrete driver of inflated thresholds in the brief. |
| AC-5 | required | Ensures the gate is escaped, not disabled — still fails actionably when unresolved. |
| AC-6 | required | Regression safety; no existing behavior may break. |
| AC-7 | required | New behavior (override + clamp) is untrusted without dedicated tests. |
| AC-8 | important | Prevents message-string clobber with the parallel change 1p451. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | Ship BOTH an `override_reason` dismissal (parity with `server_impl.py:7908-7925`) and a reviewer-count clamp before `secrets_validators.py:633`. | The override is the cheap, immediate deadlock-breaker mirroring confirmed-secret; the clamp removes the root cause (inflated threshold from bot/inactive emails). | Override-only (leaves the inflated threshold latent); clamp-only (no operator escape when even one confirmer is genuinely required). |
| 2026-06-08 | Reject `allow_self_confirm`. | It lets a single reviewer satisfy a multi-reviewer requirement unconditionally, defeating the intent; the clamp already unblocks the lone-maintainer case without that. | `allow_self_confirm` flag (weakest option per the brief). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Clamp accidentally lowers the threshold when multiple real reviewers exist, weakening the multi-reviewer guarantee. | AC-3 + tests: clamp is `min(policy, confirmable_count)` with floor 1 and may only lower, never raise; preserve original threshold when ≥2 confirmable reviewers. |
| Message-string edits collide with change `1p451` on the same false-positive branch. | Serialization point + AC-8 coordinated string check; sequence message edits after the branch change and reconcile expected strings with 1p451. |
| Bot/no-reply detection is too narrow or too broad, excluding real reviewers or admitting bots. | Use the known `noreply` / `*[bot]*` patterns, cover with AC-4 tests, and keep the floor-1 behavior so a genuine maintainer is never fully blocked. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
