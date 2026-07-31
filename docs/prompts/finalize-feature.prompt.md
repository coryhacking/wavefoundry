# Finalize Feature

Owner: Engineering
Status: active
Last verified: 2026-07-31

Shortcut: **`Finalize feature`**

## Purpose

Single-change closure path. Use after **Implement feature** to close the wave containing a single admitted change.

## Steps

1. Confirm all required review lanes are complete with findings in `## Review checkpoints`.
2. When review is enabled, confirm readiness Council and confirm delivery Council only when selected by the current Prepare receipt (typed approval events on declared waves, projected into `## Review Evidence`; prose lines count only on legacy waves).
3. Mark the change as `complete` in the wave record.
4. Record docs-contract review disposition (performed or N/A with rationale) if `docs/specs/*.md` changed.
5. Validate any memory candidates recorded during the work.
6. Run `memory_propose(wave_id, mode='create')`; validate each generated
   candidate against its evidence and current target with
   `memory_validate` (promote, retain, reject, or rewrite). Zero-memory
   changes are valid.
7. Update wave record: `Status: completed`, `Completed at:` date.
8. Clear or refresh `docs/agents/session-handoff.md`.

See `docs/prompts/close-wave.prompt.md` for the full closure requirements — they apply to single-change waves too.
