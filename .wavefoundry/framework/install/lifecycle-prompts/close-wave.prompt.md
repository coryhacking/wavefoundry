# Close Wave

Shortcut: **`Close wave`**

## Purpose

Finalize a delivered wave after implementation, review, documentation, and
handoff state are fully reconciled.

## Closure checks

1. Every AC and task is completed or intentionally deferred with rationale.
2. Required review lanes and configured council signoffs are current.
3. Change status, wave status, completion date, and chronology agree.
4. Architecture, specifications, public prompts, and release notes reflect the
   delivered behavior.
5. Journals, durable memory candidates, and the session handoff are reconciled.
6. The canonical test suite, docs gate, and relevant packaging checks pass.
7. The context-efficiency checkpoint has been projected from durable telemetry
   when telemetry is available.
8. Run `wave_close(mode='dry_run')` before requesting operator approval.

## Operator authority

Only an explicit operator instruction authorizes `wave_close(mode='create')`
or equivalent apply mode. Passing dry-run, finishing implementation, or asking
for review does not imply closure approval. Commit, tag, push, and release
authority remain separately operator-owned.

