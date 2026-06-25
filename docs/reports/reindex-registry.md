# Reindex Registry

Owner: Engineering
Status: active
Last verified: 2026-06-25

## Purpose

This file registers the docs corpus sections that drift over time and specifies when a reindex pass is required. A reindex pass updates stale pointers, removes retired content, and re-validates index tables.

## Reindex Triggers

Perform a reindex pass when any of the following occur:

| Signal | Affected Docs |
|--------|---------------|
| Wave closed | `docs/waves/README.md` (active/completed wave tables); agent journals (distillation) |
| Feature finalized | `docs/waves/README.md`; `docs/PLANS.md` |
| New architecture doc created or retired | `docs/ARCHITECTURE.md` child docs table |
| New role doc added or retired | `docs/agents/README.md`; `docs/agents/platform-mapping.md` |
| New persona added or retired | `docs/agents/personas/README.md`; `docs/prompts/prompt-surface-manifest.json` |
| New prompt doc added or retired | `docs/prompts/index.md`; `docs/prompts/prompt-surface-manifest.json`; `AGENTS.md` Shortcut Phrases |
| `.wavefoundry/framework/VERSION` bumped | `docs/prompts/prompt-surface-manifest.json` (`framework_revision`); `docs/agents/session-handoff.md` |
| Missing doc created | `docs/missing-docs.md` (remove resolved entry) |
| Tech debt resolved | `docs/references/tech-debt-tracker.md` (retire item) |

## Drift-Prone Sections

These sections are known to drift without a reindex pass:

- `docs/waves/README.md` — active/completed wave counts update every wave
- `docs/agents/session-handoff.md` — updated at session boundaries; stale after any session
- `docs/agents/journals/` — distillation section grows at wave closure
- `docs/missing-docs.md` — entries should be removed as gaps are filled
- `docs/references/tech-debt-tracker.md` — items retire as debt is resolved
- `docs/repo-profile.json` `code_patterns` — transitions from `insufficient_history` once patterns stabilize

## Reindex Scope by Event

**Wave closure reindex** (minimum required at every Close wave):
1. Update `docs/waves/README.md` active → completed
2. Distill journal captures for roles that acted in the wave
3. Promote validated lessons to `docs/references/project-context-memory.md` if warranted
4. Update `docs/agents/session-handoff.md`

**Feature finalization reindex**:
1. Confirm the admitted change doc remains wave-owned under `docs/waves/<wave-id>/`
2. Verify `docs/PLANS.md` reflects current plans state

**Framework revision reindex** (on VERSION bump):
1. Update `docs/prompts/prompt-surface-manifest.json` `framework_revision`
2. Re-run MCP **`wave_validate`** (preferred) or **`wf docs-lint`** to confirm alignment
3. Update `docs/agents/session-handoff.md`

## Reports Output

Wave closure and reindex reports are written to `docs/reports/` as `<wave-id>-closure-report.md` when produced. No report file is required for routine reindex passes — update the relevant docs directly.
