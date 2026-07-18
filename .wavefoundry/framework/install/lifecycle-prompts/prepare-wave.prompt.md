# Prepare Wave

Shortcut: **`Prepare wave`** | Alias: **`Ready wave`**

## Purpose

Confirm that an admitted wave is implementable before the first code edit.
Readiness and opening are separate: any number of waves may be readied, while
only one wave may be open for implementation.

## Readiness checks

1. Confirm every admitted change document is wave-owned and complete.
2. Resolve duplicate or staged-only placement drift.
3. Verify requirements, scope, acceptance criteria, architecture impact, and
   explicit dependencies.
4. Classify each acceptance criterion as required, important, nice-to-have, or
   not-this-scope, with rationale.
5. Select reviewer and builder lanes from repository evidence. Include QA for
   bug fixes and any additional lanes required by local policy.
6. Run the configured readiness council when enabled and record its actual
   seats, evidence, disagreements, and verdict.
7. Record product-owner acknowledgment when the change affects product
   behavior or acceptance expectations.
8. Use `wave_prepare(mode='ready')` to ready without opening, or
   `wave_prepare(mode='create')` to ready and open when the single-open-wave
   slot is available.

## Gate

Implementation may begin only after readiness is clean and the mandatory
pre-implementation review gate records `passed`. A readiness verdict confirms
admissibility; it is not delivery approval.

