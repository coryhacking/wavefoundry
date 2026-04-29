# Review Wave

Owner: Engineering
Status: active
Last verified: 2026-04-28

Shortcut: **`Review wave`**

## Purpose

Run all required review lanes against the admitted changes. Review is not optional when required lanes were confirmed at readiness.

## Steps

1. Read the wave record and each admitted change doc; confirm which review lanes were required at readiness.
2. Run each required lane:
   - `code-reviewer` — correctness, pattern compliance, branch completeness, re-entrant safety for mutable state
   - `qa-reviewer` — AC coverage, multi-step verification for stateful behavior
   - `architecture-reviewer` — boundary and layering impact
   - Other lanes as required per `docs/contributing/review-and-evals.md`
3. **AC scope gap check:** after confirming required ACs are met, surface important/nice-to-have items not in admitted scope; confirm not-this-scope deferrals.
4. **AC priority reconciliation:** reconcile the `## AC priority` table against delivered behavior; update if scope shifted; `qa-reviewer` must attest every required row has verification evidence or a recorded deferral.
5. Record all findings in the wave record `## Review checkpoints`.
6. Blocking findings return the wave to implementation (Level 2 loop).

## Code Review Specifics (Wavefoundry)

- Framework script changes: verify test coverage in `framework/scripts/tests/`
- Seed prompt changes: verify no project-specific guidance was added to generic seeds
- Manifest changes: verify `framework_revision` matches `framework/VERSION`

## Required Before Close

All required lanes from readiness must be reconciled in `## Review checkpoints` before **Close wave** can proceed.
