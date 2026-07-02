# Factor-review: stop the empty-applicable_factors warning on every install audit

Change ID: `1p9bp-enh factor-review-applicable-factors-autopopulate`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-01
Wave: `1p9bm install-experience-hardening`

## Rationale

Field feedback (real 1.9.8 install): `docs/repo-profile.json` marked 10 factors applicable, but
`docs/workflow-config.json`'s `factor_review_policy` had an empty `applicable_factors`, so **every
`wave_install_audit` call emitted a factor-review warning** and the factor-specific review agents were
never generated. The operator had to document it as a known warning. Either the config should be
populated at install, or the audit should tell the operator exactly what to run — silent recurring
warnings with no clear next step are the friction.

Note (`1p8` decision, preserved): the factor gate keys off **workflow-config `applicable_factors`**
(operational lanes), NOT the repo-profile assessment — so the fix is to seed workflow-config's list from
the profile's applicable factors as a starting point, not to make the gate read the profile.

## Requirements

1. On install (the seed that writes `workflow-config.json` / repo profile), `factor_review_policy.
   applicable_factors` is **seeded from the factors marked applicable in `repo-profile.json`** as a
   sensible default the operator can prune — so a fresh install does not sit with an empty list while the
   profile says factors apply.
2. If `applicable_factors` is (still) empty while the profile marks factors applicable, the factor-review
   advisory is a **single, clear, actionable instruction** — one consolidated line naming the applicable
   factor IDs and the real remediation (add the IDs to `applicable_factors` and regenerate the lane docs
   via the `Upgrade Wavefoundry` backfill, or align the assessments to `partial`) — not a bare recurring
   per-factor warning on every audit. (Note: there is no "Configure factor review" shortcut; the advisory
   must name only real mechanisms.)
3. The advisory does not fire when there is genuinely nothing to configure (profile marks no factors
   applicable) — no noise.
4. `run_tests.py` + `wave_validate` pass.

## Scope

**In scope:**

- The install seed / setup path that authors `workflow-config.json`: seed `applicable_factors` from the
  profile's applicable set. *(seed_edit_allowed if a seed; framework_edit_allowed if a setup script.)*
- The factor-review advisory (in the install audit / `wave_audit`) — make it a clear one-line next step
  keyed on the profile-vs-config mismatch.
- Tests: seeding produces the expected list; the advisory fires only on a real mismatch with actionable text.

**Out of scope:**

- Changing what the factor gate keys off (stays workflow-config `applicable_factors` per the `1p8` decision).
- Generating the factor review agents themselves (that is the existing **Configure factor review** flow).

## Acceptance Criteria

- [x] AC-1: a fresh install seeds `factor_review_policy.applicable_factors` from the profile's applicable
      factors (not an empty list). Evidence: `seed-050` step 5 now instructs — before generating factor docs
      — to populate `applicable_factors` from the sorted set of `repo-profile.json` `factor_review.<id>`
      entries with `status == "applicable"` when the lane set is absent/empty, as a prunable default. The
      gate still keys off `applicable_factors` (not the profile); the seeding is a one-time default.
- [x] AC-2: when `applicable_factors` is empty but the profile marks factors applicable, the audit emits a
      **single actionable** instruction, not N bare per-factor warnings. Evidence: `check_factor_surface`
      (wave_validators.py) now consolidates — when the lane set is entirely empty and ≥2 factors are
      applicable, it emits ONE advisory naming all the factor IDs + a single next step (add IDs to
      `applicable_factors` + regenerate via `Upgrade Wavefoundry`); a genuine partial drift (non-empty lane
      set) still emits the precise per-factor warning. Tests:
      `test_factor_surface_retired_lane_repo_profile_applicable_passes` (consolidated),
      `test_factor_surface_single_inactive_factor_stays_per_factor` (boundary),
      `test_factor_surface_assessment_only_factor_warns_not_errors` (partial-drift per-factor).
- [x] AC-3: no advisory when the profile marks no factors applicable. Evidence:
      `test_factor_surface_no_active_lanes_no_repo_profile_is_noop` + the loop only collects
      `status == "applicable"` factors — a `partial`/absent profile yields no warning.
- [x] AC-4: `run_tests.py` + `wave_validate` pass; the factor gate still keys off workflow-config. Evidence:
      docs-lint subsuite green (253); full `run_tests.py` at the wave's final run; the `1p8` gate-keying
      decision preserved (canonical-doc requirement reads `applicable_factors`, not the profile — the
      profile only seeds a default + drives the advisory).

## Tasks

- [x] Seed `applicable_factors` from the profile's applicable set at install. Done in `seed-050` step 5
      (the config-authoring path is the agent-entry-surface bootstrap that reads `applicable_factors` to
      generate factor docs — the seeding lead-in is the natural home).
- [x] Make the factor-review advisory a clear one-line next step keyed on the mismatch. Done: consolidated
      advisory in `check_factor_surface` for the empty-lane-set case; per-factor precision kept for real drift.
- [x] Tests (consolidated advisory; single-factor boundary; partial-drift per-factor; no-op when nothing
      applicable); docs-lint subsuite green; full `run_tests.py` + `wave_validate` at the wave's final run.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Locate the config-authoring path + the advisory; both small. Preserve the `1p8` gate-keying decision. |

## Serialization Points

- Preserve the `1p8` invariant: the factor gate reads workflow-config `applicable_factors`, not the
  profile. This change only seeds a default + improves the advisory.

## Affected Architecture Docs

N/A — install-config default + advisory text; no boundary/flow change.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Removes the empty-list-on-fresh-install root cause. |
| AC-2 | important | If still empty, the operator gets a next step, not a bare warning. |
| AC-3 | important | No noise when nothing is applicable. |
| AC-4 | required | Suite + docs gate; preserve the gate-keying decision. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-01 | Planned from the 1.9.8 install report (item 10). Preserves the `1p8` factor-gate-keying decision (gate reads workflow-config, not the profile). Admitted to the pre-1.10.0 `1p9bm` wave. | operator field report; `project_factor_gate_keying_and_1p8_validation`. |
| 2026-07-01 | Implemented. AC-1 in `seed-050` step 5 (seed `applicable_factors` from profile-applicable set as prunable default, `seed_edit_allowed`); AC-2/3 in `check_factor_surface` (`framework_edit_allowed`) — consolidate the empty-lane-set advisory to one actionable line, keep per-factor precision for real drift. **Scope correction:** the plan text referenced a "Configure factor review" flow — that flow does not exist; the advisory instead names the real mechanism (edit `applicable_factors` + regenerate via the public `Upgrade Wavefoundry` backfill), so the shipped warning carries no dangling flow name. `1p8` gate-keying preserved. Two existing factor tests reconciled (one now asserts the consolidated form) + one boundary test added. | `seed-050` diff; `wave_validators.py` `check_factor_surface` diff; `test_docs_lint.py` factor tests (253 green). |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-01 | Seed workflow-config `applicable_factors` from the profile as a default, keep the gate keyed on workflow-config. | Removes the empty-list-on-fresh-install without violating the `1p8` operational-lanes decision. | Make the gate read the profile (rejected — reverses `1p8`). |
| 2026-07-01 | If still empty vs a non-empty profile (≥2 applicable), emit one consolidated instruction instead of N per-factor warnings; keep per-factor precision for genuine partial drift (non-empty lane set). | A recurring N-line warning block with no single next step is the friction; one consolidated line names all IDs + one action, while precise per-factor lines still help when only a specific factor drifted. | Suppress the warning (rejected — hides real unconfigured state); always per-factor (rejected — the N-line noise the operator hit). |
| 2026-07-01 | Reference the real remediation (edit `applicable_factors` + `Upgrade Wavefoundry` regenerate) in the advisory, NOT a "Configure factor review" flow. | No such flow exists in the framework; a shipped warning that names a non-existent command would strand downstream agents (per the seeds-no-dangling-refs lesson, applied to warning strings too). | Invent/add a `Configure factor review` shortcut (rejected — out of scope, and the entry-surface generation already does this). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Auto-seeding the full applicable set generates review lanes the operator didn't want. | It is a starting default the operator prunes; the advisory names Configure factor review to (re)generate; the gate still respects whatever workflow-config ends up with. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
