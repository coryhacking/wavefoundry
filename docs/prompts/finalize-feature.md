# Finalize Feature

Owner: Engineering
Status: active
Last verified: 2026-04-28

Shortcut: **`Finalize feature`**

## Purpose

Single-change closure path. Use after **Implement feature** to close the wave containing a single admitted change.

## Steps

1. Confirm all required review lanes are complete with findings in `## Review checkpoints`.
2. Mark the change as `complete` in the wave record.
3. Record docs-contract review disposition (performed or N/A with rationale) if `docs/specs/*.md` changed.
4. Distill any journal lessons.
5. Promote durable memory if applicable.
6. Update wave record: `Status: completed`, `Completed at:` date.
7. Clear or refresh `docs/agents/session-handoff.md`.

See `docs/prompts/close-wave.md` for the full closure requirements — they apply to single-change waves too.
