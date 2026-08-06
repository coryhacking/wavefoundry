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
5. Select reviewer and builder lanes. Automatic lanes are derived from the
   explicit repo-relative paths each change doc declares in
   `## Serialization Points`, never from Scope or other narrative; a change doc
   that declares no path keeps legacy whole-document scoring so coverage is
   never silently lost. That derivation is a FLOOR, not the whole answer:
   add any lane your own judgment calls for to the wave record's
   `Requested review lanes`, which is always honored and costs no receipt
   churn because `wave.md` is not part of the review-policy digest. Architecture,
   security and performance risk in particular are usually judgment calls that
   no file path expresses — an ownership shift or a protocol change can live
   entirely in files that recruit only the code lane. Include QA for bug fixes
   and any additional lanes required by local policy, and never read an empty
   automatic roster as evidence that no review is warranted.
6. Run the configured readiness council when enabled and record its actual
   seats, evidence, disagreements, and verdict.
7. Record product-owner acknowledgment when the change affects product
   behavior or acceptance expectations.
8. Use `wf_prepare_wave(mode='ready')` to ready without opening, or
   `wf_prepare_wave(mode='create')` to ready and open when the single-open-wave
   slot is available.

## Gate

Implementation may begin only after readiness is clean and its current approval
is recorded. The readiness verdict is the single pre-code review decision; it
confirms admissibility, not delivery approval.
