# Waves

Owner: Engineering
Status: active
Last verified: 2026-04-30

Wave records for Wavefoundry delivery work. Each wave is a bounded, reviewable container for one or more admitted changes.

## Wave Lifecycle

`planned` → `active` → `completed` | `superseded` (wave records may use **`Status: closed`** for a completed delivery — same meaning as **completed** for the index in this repo)

## Active Waves

*(none)*

## Completed Waves

- `129p8 mcp-docs-search-reliability`
- `1293d mcp-server-foundation`

## Wave ID Format

Generate wave IDs with: `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind wave --slug <slug>`

Output format: `<prefix> <slug>` (e.g. `0a3b2 mcp-read-only-surface`).
Reserve `00000 wave-zero-plans-and-specs` for legacy baseline waves only (Wavefoundry was installed as a greenfield — no baseline wave was needed).

## Wave Folder Layout

Each wave lives at `docs/waves/<wave-id>/wave.md`. After **Prepare wave**, admitted change docs are relocated here alongside `wave.md`.

## Required Wave Anchors

See `.wavefoundry/framework/seeds/110-wave-memory-bootstrap.prompt.md` for the full anchor contract. Required: `wave-id`, `Title`, `Status`, `Objective`, `Coordinator`, `Participants`, `Planned or active changes`, `Dependencies`, `Current assumptions`, `Outputs produced or expected`, `Review checkpoints`, `Journal refs`, `Journal Watchpoints`, `Completion criteria`, `Handoff or next-wave notes`, `Wave Summary` (populated at closure).
