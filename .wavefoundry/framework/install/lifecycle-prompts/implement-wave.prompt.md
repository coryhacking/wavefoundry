# Implement Wave

Shortcut: **`Implement wave`**

## Purpose

Open a readied wave and execute all admitted changes through a focused
implement and verify loop, then hand the completed evidence to `Review wave`.

## Readiness handoff

Before the first code edit, confirm `Prepare wave` completed and its current
typed readiness approval is recorded. Prepare owns the failure-first critique
and packet-completeness decision; implementation does not repeat that review.

## Execution

1. Use repository-native navigation and the Wavefoundry code tools to identify
   ownership, callers, and established patterns before editing.
2. Implement only admitted scope and preserve unrelated working-tree changes.
3. Update AC and task checkboxes as evidence is produced.
4. Run focused tests after each bounded repair and the canonical project suite
   before delivery review.
5. Record findings when discovered during an exceptional named checkpoint or
   the later delivery review, record `repair_start` before mutation,
   repair immediately, and reverify in the currently open partial repair cycle.
   Advancing a cycle number is chronology, not a reason to delay the repair or
   summon another council.
6. Re-prepare only when scope, required contracts, architecture ownership,
   trust boundaries, or readiness semantics materially change.

## Completion

Implementation is complete only when the admitted behavior, docs, tests, and
review evidence agree. It does not authorize commit, release, or wave closure.
