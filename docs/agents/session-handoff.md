# Session Handoff

Owner: wave-coordinator
Status: active
Last verified: 2026-04-30

Working-memory snapshot for session continuity. Clear this file at wave start and refresh it at pause or compaction risk. This is transient state — durable decisions belong in wave records or canonical docs.

## Current Session

**Date:** 2026-04-30
**Active wave:** *(none — `129p8 mcp-docs-search-reliability` closed)*
**Last completed action:** Closed wave **`129p8 mcp-docs-search-reliability`** (MCP docs search reliability, lifecycle relocation, index control, multi-host MCP registration, bin wrappers, `wave_audit`, and related framework hygiene). See `docs/waves/129p8 mcp-docs-search-reliability/wave.md` **Wave Summary** for the delivery record.

## Next Actions

1. Start the next delivery wave with **Plan feature** → **Create wave** → **Prepare wave** when new work is scoped.
2. After substantive `docs/` edits, prefer MCP **`wave_validate`** (and **`wave_garden`** when metadata needs refresh); use **`.wavefoundry/bin/docs-lint`** for hooks/CI or when MCP is not attached.
3. For a one-shot readiness snapshot, call MCP **`wave_audit`** before chaining `wave_current` + `wave_validate` + `wave_index_health` manually.

## Blockers

None.

## Notes

- The framework content lives at `.wavefoundry/framework/`. This is the canonical self-hosting mode.
- Operator-approved waivers recorded before 2026-04-30 remain historical context in prior wave artifacts; do not delete wave records that reference them.
- Lifecycle ID epoch for Wavefoundry: `2022-04-28T00:00:00Z` — see `docs/references/project-context-memory.md` and `docs/workflow-config.json` `lifecycle_id_policy`.
