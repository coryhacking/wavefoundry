# Finalize Feature

Owner: Engineering
Status: active
Last verified: 2026-07-20

Shortcut: **`Finalize feature`**

## Purpose

Single-change closure path. Use after **Implement feature** to close the wave containing a single admitted change.

## Steps

1. Confirm all required review lanes are complete with findings in `## Review checkpoints`.
2. When `wave_review.enabled` is true, confirm both `wave-council-readiness` and `wave-council-delivery` are present in `## Review Evidence`.
3. Mark the change as `complete` in the wave record.
4. Record docs-contract review disposition (performed or N/A with rationale) if `docs/specs/*.md` changed.
5. Distill any journal lessons.
6. Run `wave_memory_propose(wave_id, mode='create')`; validate each generated
   candidate against its evidence and current target with
   `wave_memory_validate` (promote, retain, reject, or rewrite). Zero-memory
   changes are valid.
7. Update wave record: `Status: completed`, `Completed at:` date.
8. Clear or refresh `docs/agents/session-handoff.md`.

See `docs/prompts/close-wave.prompt.md` for the full closure requirements — they apply to single-change waves too.
