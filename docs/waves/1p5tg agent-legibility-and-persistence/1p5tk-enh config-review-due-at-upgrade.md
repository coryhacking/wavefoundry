# Config-review recommendation at major/minor upgrade

Change ID: `1p5tk-enh config-review-due-at-upgrade`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-16
Last verified: 2026-06-16
Wave: `1p5tg agent-legibility-and-persistence`

## Rationale

A documented config-review prompt (`1p5tj`) only gets used if something reminds a human to evaluate it. The natural, low-friction moment is the **major/minor upgrade install** — a point a human is already actively engaging with the framework. Rather than build a marker + dual time/wave-count threshold subsystem to decide when the review is "due," keep it as simple as possible: on **every** major/minor upgrade, the framework surfaces a recommendation that a senior/principal owner **evaluate** whether to run the config review. The owner decides each time; the framework just makes sure the question is asked. No state to track, nothing to get out of sync, nothing that can silently suppress the reminder.

This is a generic framework capability: every project that installs a major/minor upgrade inherits the same recommendation. The upgrade never runs, schedules, or blocks on the review — it only recommends.

## Requirements

1. **Generic + seed-rooted.** The recommendation text and its trigger ship in the framework, so every downstream project gets it on a major/minor upgrade. No wavefoundry-repo-specific names, paths, or values.
2. **Trigger = every major/minor upgrade.** On a **major or minor** upgrade install (not patch), the upgrade output includes the recommendation. Patch upgrades do not trigger it. No marker, no thresholds, no wave-count — the cadence is simply "evaluated at each major/minor upgrade."
3. **Recommend, never execute.** The recommendation points at the `1p5tj` review, is addressed to a **senior / principal architect / engineer**, and states they must initiate it. The upgrade does not run, schedule, or block on the review.
4. **Fail-safe + quiet otherwise.** The recommendation step never blocks or fails an upgrade: on any error it degrades silently. It adds one clear line to the major/minor upgrade summary and nothing on patch upgrades.

## Scope

**Problem statement:** The config-review prompt needs a reliable, zero-maintenance trigger. A wall-clock daemon or a stateful due-check is more machinery than the job warrants; the major/minor upgrade is the right generic, human-present moment to simply ask.

**In scope:**

- A recommendation line emitted in the major/minor upgrade output (gated off patch), pointing at the `1p5tj` review, role-addressed, human-initiated.
- Seed-first wording + cross-links to `1p5tj` and the upgrade prompt.
- Tests: appears on major/minor, absent on patch, fail-safe (never raises into the upgrade).

**Out of scope:**

- Any marker / last-review state, time thresholds, or wave-count tracking (explicitly dropped — simplest-possible per operator direction).
- The review prompt and audit/policy content itself (that is `1p5tj`).
- Auto-executing, scheduling, or blocking the upgrade on the review.
- Enforcing *who* runs it programmatically (role is a recommendation/convention).

## Acceptance Criteria

- [x] AC-1: On a **major/minor** upgrade install, `_print_operator_summary` emits the recommendation (via `_config_review_recommendation_lines`) addressed to a senior/principal architect/engineer and pointing at `docs/prompts/framework-config-review.prompt.md`; **patch**/same/downgrade emit nothing. Covered by `ConfigReviewRecommendationTests`.
- [x] AC-2: The step holds no state — no marker, threshold, or wave-count — and is fully fail-safe: `_config_review_recommendation_lines` returns `[]` on unparseable/missing versions and is only called when `not failed_phase`. Tests cover major/minor present, patch/same/downgrade absent, unparseable + None silent.
- [x] AC-3: Wording is generic (no project-specific values) and cross-links `1p5tj` (the recommendation points at the prompt) + the upgrade prompt doc (`upgrade-wavefoundry.prompt.md` "Config review recommendation" section); **full suite 3160 OK**; docs-lint clean.

## Tasks

- [x] Add the recommendation line to the major/minor upgrade output (gated off patch; role-addressed, human-initiated; points at `1p5tj`).
- [x] Author the wording seed-first; cross-link `1p5tj` + the upgrade prompt.
- [x] Add tests (major/minor present, patch absent, fail-safe error path); full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| recommend  | Engineering | —          | recommendation line in major/minor upgrade output + gating |
| wording    | Engineering | recommend  | seed-first text + cross-links to 1p5tj |


## Serialization Points

- Points at `1p5tj`'s prompt by reference only — no shared state. Settle `1p5tj`'s prompt name/location so the cross-link is stable.

## Affected Architecture Docs

`N/A` for runtime/index architecture. Touches the upgrade flow (operational); a pointer is added to the upgrade prompt + cadence docs.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The major/minor-upgrade recommendation is the trigger that makes the cadence real. |
| AC-2 | required | Statelessness + fail-safe are the whole point of the simplification; an upgrade must never break. |
| AC-3 | required | Generic seed-rooted wording + a stable cross-link keep it discoverable and not orphaned. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | Simplified per operator direction: dropped the marker + dual time/wave-count threshold subsystem. New design = recommend the review on every major/minor upgrade, stateless. This also removed the only intra-wave shared contract (the former "record completed review" marker). | this session |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-16 | Recommend the review on every major/minor upgrade, stateless | Simplest possible trigger; the human evaluates each time, so no marker/threshold can get out of sync or silently suppress the reminder. Operator-directed | Marker + dual time/wave-count due-check (rejected — more machinery than the job warrants); wall-clock cron/daemon (rejected — heavy, unattended) |
| 2026-06-16 | Recommend-only, role-addressed, human-initiated | The review retires standing constraints — authority-bearing; must stay with an experienced owner who decides whether to run it | Auto-run at upgrade (rejected — judgment + authority needed); block upgrade until reviewed (rejected — must never block) |
| 2026-06-16 | Major/minor only, not patch | Patch upgrades are frequent + low-surface; recommending a config review on each would be noise | Every upgrade incl. patch (rejected — nag); time/wave-gated (rejected — reintroduces the state we removed) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Recommendation breaks/blocks an upgrade | Fully fail-safe: never raises into the upgrade; degrades silently; tested |
| Reminder becomes noise | Major/minor only (not patch); one concise line; recommend-only |
| Recommendation ignored in a solo repo | Still surfaced; the senior/principal framing is guidance for multi-user repos, not an enforced gate |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
