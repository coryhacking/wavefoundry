# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-08

wave-id: `12g27 wave-council-review-system`
Title: Wave Council Review System

## Objective

Define and implement Wave Council as a universal, seed-backed meta-review system for Wave Framework repositories, with explicit council-moderator ownership, two-phase review passes, and no replacement of existing specialist review lanes.

## Coordinator

- `wave-coordinator`

## Changes

Change ID: `12g1y-enh wave-council-review-system`
Change Status: `complete`

## Participants

| Role | Lane | Scope |
|------|------|-------|
| planner | planning | `12g1y-enh wave-council-review-system` — finalize council operating contract, moderator role, seat templates, and gating model |
| architecture-reviewer | review | `12g1y-enh wave-council-review-system` — lifecycle contract impact, role boundaries, and MCP/review-flow integration |
| code-reviewer | review | `12g1y-enh wave-council-review-system` — framework script changes, generated-surface consistency, and implementation correctness |
| qa-reviewer | review | `12g1y-enh wave-council-review-system` — AC coverage, lifecycle evidence, and regression verification across prompts and tooling |
| docs-contract-reviewer | review | `12g1y-enh wave-council-review-system` — seed/local prompt-surface contract, role taxonomy wording, and operator-facing lifecycle guidance |

## Dependencies

- No external wave dependencies identified.
- Depends on canonical seed and local prompt-surface alignment landing together once implementation starts.

## Current Assumptions

- Wave Council should be universal as a meta-review, but specialist lanes remain authoritative where already required.
- A dedicated council-moderator should own synthesis rather than `wave-coordinator`.
- Version 1 should use isolated first-pass reviews plus synthesis, with at most one targeted challenge round.
- The feature must be seeded canonically so target repositories receive it through framework install and upgrade.

## Outputs Produced Or Expected

- Updated canonical seeds and local prompt surfaces for Wave Council
- A seeded council-moderator role/prompt surface
- `docs/workflow-config.json` council policy additions
- MCP lifecycle/tooling updates for council evidence and gating
- Regression tests covering council policy and authority boundaries

## Review Checkpoints

- Admission recorded 2026-05-08: `12g1y-enh wave-council-review-system` admitted to `12g27 wave-council-review-system`; product-owner: N/A because this is framework workflow and review-system behavior, not a target-product feature surface.
- Prepare wave — readiness verdict: **pass** on 2026-05-08. Admitted doc is wave-owned at `docs/waves/12g27 wave-council-review-system/12g1y-enh wave-council-review-system.md`; change-doc sections are complete; AC priority is recorded; required lanes selected: `architecture-reviewer`, `code-reviewer`, `qa-reviewer`, `docs-contract-reviewer`; `product-owner: N/A` remains valid because this wave changes framework workflow/review mechanics rather than a target-product behavior surface. Wave status advanced to `active`.
- Implementation state update (2026-05-08): Wave Council is now implemented across canonical seeds, Wavefoundry-local operating docs, the council-moderator role surface, and MCP lifecycle enforcement. Verification passed with `python3 .wavefoundry/framework/scripts/run_tests.py` (1008 tests) and `.wavefoundry/bin/docs-lint`; docs metadata refreshed with `.wavefoundry/bin/docs-gardener`.
- Review wave — delivery verdict: **pass** on 2026-05-08 after one Level 2 fix loop. Initial review found two blockers in the delivered implementation: canonical role seeds for `council-moderator` and `reality-checker` were referenced but not actually present in `.wavefoundry/framework/seeds/`, and MCP lifecycle enforcement read `wave_council_policy.transition_policy` without applying it during close. Both were fixed in-wave by adding seed files `215-council-moderator.prompt.md` and `216-reality-checker.prompt.md`, documenting transition semantics in `007-review-system-overview.md`, and updating `server.py` so `applies-from-next-prepare` does not retroactively require missing readiness signoff on close while still requiring the delivery-phase council pass. Regression coverage was extended and full verification reran clean: `python3 .wavefoundry/framework/scripts/run_tests.py` (1010 tests) plus `.wavefoundry/bin/docs-lint`.
- Wave Council — delivery roster (2026-05-08): fixed seats were `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, and `reality-checker`; the rotating fifth seat for this wave was `docs-contract-reviewer` because the change centered on seed prompts, lifecycle wording, role surfaces, and framework contract distribution.
- Council moderator synthesis summary (2026-05-08): `council-moderator` concluded that the implementation is shippable as a universal meta-review layer once two contract gaps are repaired. Architecture judged the coordinator/moderator split and non-waiver boundaries sound; security found no remaining trust-boundary blocker after the transition-policy fix; QA required regression coverage for council enforcement and pack contents; reality-checker surfaced the mismatch between "seeded role" claims and the actual seed inventory; docs-contract required the council role surfaces and transition semantics to be explicit in the canonical framework.
- Council moderator — disagreements resolved (2026-05-08): the main disagreement was not about whether to ship the feature, but about whether the implementation was already complete enough to count as a framework-level seeded capability. `reality-checker` and `docs-contract-reviewer` both objected that the repo claimed seeded `council-moderator` / `reality-checker` support without actual canonical seed files, while QA objected that the transition-policy contract was documented but not enforced at close time. Those objections were resolved by adding canonical seed files `215-council-moderator.prompt.md` and `216-reality-checker.prompt.md`, documenting transition semantics in `007-review-system-overview.md`, and extending server/tests so `applies-from-next-prepare` behaves as specified. After those repairs landed and verification reran clean, the council aligned on `approved`.
- Wave Council — final implementation review findings (2026-05-08): `architecture-reviewer` found the council now respects the framework boundary between lifecycle routing and synthesis ownership; `security-reviewer` found no remaining trust-boundary blocker once transition-policy enforcement matched the documented rollout contract; `qa-reviewer` required focused regressions for council enforcement and packaged seed contents, then accepted the implementation after the suite passed at 1010 tests; `reality-checker` identified the gap between claimed seeded support and the actual canonical seed inventory; `docs-contract-reviewer` required the framework docs to explicitly distribute the council role surfaces and record transition semantics. Moderator conclusion: **approved** for final implementation review, with no unresolved blocking findings and no additional follow-on work required before operator signoff.
- Review wave — AC priority reconciliation: required and important ACs remain delivered as planned; no AC reclassification was needed. No additional scope gaps or follow-on work are required before closure beyond normal operator signoff.

## Review Evidence

- architecture-reviewer: approved (none — council-moderator ownership, rotating-seat policy, and specialist-lane non-waiver boundaries are now consistent across the framework contract)
- code-reviewer: approved (none — server enforcement, regression tests, and packaged seed inventory align after the review-loop fixes)
- qa-reviewer: approved (none — focused council/pack regressions added and the full framework suite passes at 1010 tests)
- docs-contract-reviewer: approved (none — canonical seeds, local role docs, lifecycle prompts, and review-system overview now agree on Wave Council distribution and transition behavior)
- wave-council-delivery: approved (moderator: council-moderator; fixed seats: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating seat: docs-contract-reviewer — seats aligned that the implementation is shippable as a universal meta-review layer; no blocking specialist findings remain)
- operator-signoff: approved (2026-05-08 — operator requested wave closure after final council implementation review)

## Journal Refs

- `docs/agents/session-handoff.md`

## Journal Watchpoints

- **Seed-backed feature.** This change is not complete unless canonical seed prompts and generated local prompt surfaces both reflect Wave Council.
- **Authority boundary risk.** Council synthesis must not be able to waive missing or blocking specialist lanes.
- **Role split must stay explicit.** `wave-coordinator` owns lifecycle state; council-moderator owns council synthesis. Do not blur these in prompts or server diagnostics.
- **Protocol discipline.** Keep v1 on isolated seat reviews plus synthesis; avoid drifting into free-form council debate unless a later wave justifies it.

## Completion Criteria

- `12g1y-enh wave-council-review-system` reaches `complete`
- The council contract, moderator role, phase templates, and gating behavior are documented and implemented consistently
- Required review evidence and lifecycle tooling for council are aligned
- Seed and local prompt surfaces are reconciled and lint/test clean

Completed At: 2026-05-08

## Wave Summary

Delivered Wave Council as a seed-backed universal meta-review layer for Wave Framework repositories, with a dedicated `council-moderator`, two-phase council passes, explicit roster and disagreement-recording guidance, and transition-aware lifecycle enforcement in the MCP server.

During review, the wave exposed two contract gaps: the framework claimed seeded `council-moderator` / `reality-checker` support without canonical seed files, and closure-time council enforcement ignored the documented `transition_policy`. Both were fixed in-wave, with regression coverage added and the full framework suite rerun clean.

No follow-on implementation work was deferred in this wave. Residual closure dependency is operator-owned only: future waves must continue to record explicit council rosters, moderator synthesis, and disagreement resolution in `## Review checkpoints`.
