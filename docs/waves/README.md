# Waves

Owner: Engineering
Status: active
Last verified: 2026-06-09

Wave records for Wavefoundry delivery work. Each wave is a bounded, reviewable container for one or more admitted changes.

## Wave Lifecycle

`planned` → `active` → `paused` → `completed` | `superseded`

Wave records may use `Status: closed` in historical contexts, but current active records in this repo use the lifecycle statuses above.

## Wave ID Format

Generate wave IDs with the MCP `wave_create_wave` tool (preferred — it dedupes against on-disk IDs). CLI fallback when MCP is unavailable: `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind wave --slug <slug>`.

Output format: `<prefix> <slug>` (example: `0a3b2 mcp-read-only-surface`).

Reserve `00000 wave-zero-plans-and-specs` for the legacy baseline wave only.

## Wave Folder Layout

Each wave lives at `docs/waves/<wave-id>/wave.md`.

Admitted change docs are wave-owned at `docs/waves/<wave-id>/<change-id>.md`. `Add change to wave` is the canonical relocation step; `Prepare wave` validates placement and repairs drift if needed.

## Required Wave Record Contract

The live validator requires wave records to include:

- metadata lines: `Owner:`, `Status:`, `Last verified:`
- `wave-id: \`<wave-id>\``
- `Title: ...`
- `## Wave Summary`
- `## Journal Watchpoints`

The standard Wavefoundry scaffold also includes these operational sections and they should be treated as the normal working shape for active waves:

- `## Changes`
- `## Objective`
- `## Coordinator`
- `## Participants`
- `## Review Evidence`
- `## Review Checkpoints`
- `## Dependencies`

Use `Create wave` / `wave_create_wave` to generate the current scaffold instead of copying historical wave docs.
