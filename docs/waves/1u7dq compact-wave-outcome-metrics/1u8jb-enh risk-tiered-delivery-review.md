# Risk-tiered delivery review

Change ID: `1u8jb-enh risk-tiered-delivery-review`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-02
Wave: 1u7dq compact-wave-outcome-metrics

## Rationale

The current default (`delivery_mode: universal`) invokes the full delivery
Council for ordinary work even when the existing risk-selected specialist
roster is sufficient. This adds repeated review work without a corresponding
boundary change. Keep readiness review and required specialist lanes, but make
the full delivery re-review an escalation for elevated work.

## Requirements

1. Make `targeted` the default delivery mode for fresh installs and this
   self-hosted project; legacy enabled projects upgraded to the current policy
   must receive the same targeted default and a re-Prepare marker.
2. Preserve the readiness Council and risk-selected required specialist lanes
   for every enabled project. Targeted mode may reduce delivery Council work,
   never suppress a required specialist lane or a blocking finding.
3. Require a full delivery Council re-review in targeted mode when the admitted
   or delivered work involves an upgrade/release boundary, permission or trust
   boundary, cross-platform behavior, or an existing full-Council trigger.
4. Ordinary features without an escalation trigger receive the selected
   specialist delivery review and focused repair reverification. A repair
   broadens back to full Council only when it introduces an escalation trigger.
5. Update policy validation, migration, rendered workflow guidance, and tests
   so the same trigger/roster decision is used by Prepare, Review, Close, and
   upgrade.

## Scope

**Problem statement:** Full multi-lane delivery re-review is normal policy,
rather than an exception for work with a materially larger blast radius.

**In scope:**

- `review_policy.py` default, migration, trigger selection, and policy tests.
- `review_evidence.py` and lifecycle evaluator tests that enforce targeted
  delivery Council selection while retaining required specialist lanes.
- `docs/workflow-config.json` and rendered policy guidance for the changed
  default and explicit escalation cases.

**Out of scope:**

- Disabling readiness Council, required specialist lanes, finding repair, or
  independent reverification.
- Per-model, billing, or timing telemetry.
- Changing the four transition-only evidence model planned separately.

## Acceptance Criteria

- [x] AC-1: A normal framework feature in `targeted` mode requires its
  risk-selected specialist lanes but not the full delivery Council.
- [x] AC-2: Upgrade/release, permission/trust-boundary, and cross-platform
  fixtures each require the full delivery Council in `targeted` mode.
- [x] AC-3: A post-repair escalation trigger requires full Council; a
  non-escalating repair remains focused and preserves its required lanes.
- [x] AC-4: Fresh-install and upgraded enabled policy fixtures resolve to
  `targeted`, mark non-closed declared waves for re-Prepare, and leave disabled
  policy disabled.
- [x] AC-5: Prepare, Review, Close, lint, and rendered guidance agree on the
  same required roster and delivery-Council decision.

## Tasks

- [x] Define the narrow escalation trigger set and change the default/migration
  behavior in the shared policy authority.
- [x] Route all lifecycle evaluators and rendered policy surfaces through that
  authority; update the self-hosted configuration.
- [x] Add normal, elevated-boundary, repair-escalation, migration, and
  cross-surface regression coverage.
- [~] Run focused tests, the framework suite, and documentation validation. *(Focused policy coverage and docs validation passed; the full suite exits at the host ONNX/CoreML embedding regression before a test result.)*

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| Policy and migration | implementer | — | One shared policy authority. |
| Verification and guidance | qa-reviewer / docs-contract-reviewer | Policy and migration | Prove normal and elevated paths differ only as intended. |


## Serialization Points

- `review_policy.py` owns defaults, triggers, migration, and the shared
  delivery decision consumed by lifecycle paths.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` and
`docs/architecture/testing-architecture.md` — update the delivery-policy
default and verification matrix. `docs/specs/mcp-tool-surface.md` — update
the policy/receipt contract if its reported mode changes.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Normal work no longer receives full Council by default. |
| AC-2 | required | Elevated boundaries retain multi-lane protection. |
| AC-3 | required | Repairs cannot bypass new boundary risk. |
| AC-4 | required | New and upgraded projects converge on the same default. |
| AC-5 | required | Prevents policy drift across lifecycle surfaces. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-02 | Change drafted from the wave-overhead review. | Current policy has `universal` default and a shared targeted evaluator. |
| 2026-08-02 | Implemented targeted default with explicit release/upgrade, permission/trust, cross-platform, and existing boundary escalation. | `test_review_policy.py`; self-hosted config and lifecycle guidance. |
| 2026-08-02 | Corrected the upgrade-policy projection to match targeted legacy migration and point to the compact post-upgrade checks. | Canonical `UPGRADE_POLICY_BLOCK`; regenerated `upgrade-wavefoundry` prompt. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-02 | Use the existing `targeted` policy mode as the default and add only explicit high-risk triggers. | It changes behavior through one authority instead of adding a second review system. | Keep universal default — rejected: contradicts the simplification objective. Remove Council entirely — rejected: loses the elevated-boundary safeguard. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| An elevated class is missed by a text trigger. | Use explicit upgrade/release, permission/trust, and cross-platform fixtures plus the existing full-Council fields; fail closed on malformed policy. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
