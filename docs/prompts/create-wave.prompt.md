# Create Wave

Owner: Engineering
Status: active
Last verified: 2026-06-08

Shortcut: **`Create wave`**

## Purpose

Create a wave record at `docs/waves/<wave-id>/wave.md`. The wave is the coordination container for one or more admitted changes.

## Steps

1. Generate a wave ID: `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind wave --slug <slug>`
2. Create `docs/waves/<wave-id>/wave.md` with all required anchors (see `.wavefoundry/framework/seeds/110-wave-memory-bootstrap.prompt.md`):
   - `wave-id`, `Title`, `Status: planned`
   - `Objective`, `Coordinator`, `Participants`
   - `Planned or active changes`, `Dependencies`
   - `Current assumptions`, `Outputs produced or expected`
   - `Review checkpoints`, `Journal refs`, `Journal Watchpoints`
   - `Completion criteria`, `Handoff or next-wave notes`
   - `Wave Summary` placeholder: *(Populated at closure.)*
3. Only one wave may be **OPEN** (`active`/`implementing`) per `change-id` at a time — enforced at the activation step (wave 1p45l). Creating, admitting, and **readying** additional waves needs no pause; only opening one is single-gated.

## Wave Identity Rules

- `wave-id` is the folder name under `docs/waves/` in the format `<prefix> <slug>` (e.g. `0a3b2 mcp-read-only-surface`)
- Reserve `00000 wave-zero-plans-and-specs` for the legacy baseline wave only
- Do not insert a literal `-wave` token in the wave-id
