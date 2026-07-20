# Session Handoff

Owner: Engineering
Status: generated
Last verified: 2026-07-20

## Current Session

**Active wave:** *(none)*
- **Active wave:** `1t3gt mcp-tool-hygiene` (OPEN, `implementing`). All four
  changes are `implemented`: `1t1b3` (shared `repo_root.py` cwd-independent
  `--root` discovery for `memory_backfill.py`/`memory_cli.py`), `1t3gs` (full
  MCP tool rename off the `wave_` prefix: 47 tools renamed to
  `wf_`/`memory_`/`index_`, `MCP_TOOL_PREFIXES` updated, all seeds/prompts/
  specs/rendered surfaces updated, repo-wide sweep clean), `1t3gu` (`wave.md`
  scaffold lint-valid from creation: projection sections rendered via the
  canonical renderers, Watchpoints placeholder carries marker words), and
  `1t3ld` (Context Efficiency three-stage model: only `plan`/`implement`/
  `review` are ever written, adoption lands in `plan`, fixed row order; manual
  one-time cleanup canonicalized the live sqlite store and 8 wave records).
- **IMPORTANT for the next session:** the MCP server now serves ONLY the new
  tool names (`wf_*`, `memory_*`, `index_*`; `docs_`/`code_`/`seed_`
  unchanged). Any session started before this change must reconnect (`/mcp`).
  The workflow-config KEYS `wave_review`/`wave_implement` are unchanged (they
  are config schema, not tool names).
- Renaming the reload-survivor tool itself (`wave_mcp_reload` to
  `wf_reload_mcp`) is a one-time process-restart boundary: the in-session hot
  reload correctly refused to re-register under the old surviving name.
  Verified instead via a fresh-process MCP `tools/list` probe: 83 tools, zero
  `wave_`-prefixed, all renamed tools present.
- Verification: final canonical suite **5,990/5,990 across 56 files** (one
  interference flake in `test_indexer` during a run concurrent with a server
  probe; clean isolated and clean on the final uncontended run); docs-lint
  clean; `server.py --dry-run` OK.
- Wave `1t3gt` still needs **Review wave** (delivery-phase council) and
  operator-owned **Close wave**. No commit has been made this implementation
  pass; commits remain operator-owned.

## Continuation

1. Reconnect MCP (`/mcp`) to pick up the renamed tool surface.
2. Run **Review wave** for `1t3gt` (delivery review lanes + council), then ask
   the operator about closure.
3. The dashboard was restarted earlier on PID 66431 (port 43128); unaffected by
   the rename.
