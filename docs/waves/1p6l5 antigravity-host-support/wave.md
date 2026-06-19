# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-19

wave-id: `1p6l5 antigravity-host-support`
Title: Antigravity Host Support

## Objective

Add Google Antigravity as a supported host. Antigravity supports workspace-local configuration via `.agents/mcp_config.json`, which we render automatically via the platform surface renderer — mirroring Claude's `.mcp.json` and Cursor's `.cursor/mcp.json` — using the project-relative `.wavefoundry/bin/mcp-server` wrapper command to keep configuration local, portable, and clean. Tier-1 is native (Antigravity reads the project-root `AGENTS.md` natively).

## Changes

Change ID: `1p6l4-enh antigravity-host-support`
Change Status: `implemented`

Completed At: 2026-06-19

## Wave Summary

Wave `1p6l5` (Antigravity Host Support) delivered one change: Antigravity host support — workspace-local MCP configuration. Notable adjustments during implementation: Antigravity host support — workspace-local MCP configuration: In-flight change to workspace-local `.agents/mcp_config.json` rendering. Replaced global helper registration script with automatic platform surface rendering. Removed obsolete global helper files, added tests, and updated documentation.

**Changes delivered:**

- **Antigravity host support — workspace-local MCP configuration** (`1p6l4-enh antigravity-host-support`) — 5 ACs completed. Key decisions: --------; Workspace-local `.agents/mcp_config.json` rendering.
## Journal Watchpoints

- **Workspace-local, auto-rendered:** The config is rendered to `.agents/mcp_config.json` using the portable wrapper (no absolute paths or absolute venv Python in checked-in/local files), ensuring portability.
- **Auto-detection:** Detected from the existence of the `.agents` folder, matching the existing platform detection behavior.
- **No Tier-2 file:** Antigravity reads the project-root `AGENTS.md` (Tier-1 native), like Codex/Windsurf/Air — no thin-pointer entry file is rendered.
- **Follow-up:** Tier-3 native Skill support is moved to the subsequent skills wave `1p6lp` (`1p6lo-enh`).


## Review Evidence

- wave-council-readiness: approved (READY) — prepare-council passed 2026-06-19 (seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, security-reviewer, docs-contract-reviewer). Updated in-flight to project-local `.agents/mcp_config.json` config rendering.
- wave-council-delivery: approved (PASS) — delivery-council passed 2026-06-19 against the as-built CLI implementation (seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, security-reviewer, docs-contract-reviewer). `render_antigravity_mcp_json` → `.agents/mcp_config.json` with the portable `.wavefoundry/bin/mcp-server` wrapper; wired via detect/`--platform`/ladder; Tier-1 native. Verified end-to-end (`--platform antigravity` renders the exact stanza `ag` itself emits) and on a live `ag` install. The dropped global register-helper was fully removed (script + launcher + tests; stale-cleanup entry added; the `~/.gemini/config/mcp_config.json` test entry reverted) — no dangling refs; full suite 3335 green; docs-lint clean; host docs corrected (AGENTS.md MCP table + Windsurf/Warp rows, README badge + accurate tiers, platform-mapping, install prompt). Strongest challenge: did dropping the global helper leave anything dangling — no. Strongest alternative: keep the global helper too (rejected — operator chose CLI out-of-box; app path is manual/documented). Faithfulness N/A (config render; no detection/binding change; no network; project-local, no global mutation by the renderer).
- operator-signoff: approved — operator authorized closure ("close this wave") 2026-06-19.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-19: PASS** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, security-reviewer, docs-contract-reviewer; Fixed-seat: red-team; rotating-seat: security-reviewer; updated in-flight to target project-local `.agents/mcp_config.json` workspace rendering).
- **Delivery-phase Wave Council [delivery-council] — 2026-06-19: PASS** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, architecture-reviewer, qa-reviewer, security-reviewer, docs-contract-reviewer; fixed-seat: red-team; rotating-seat: security-reviewer (trust-boundary, now minimal — project-local config, no global mutation); scope: as-built CLI `.agents/mcp_config.json` auto-render, pivoted from the prepared global register-helper per operator direction; strongest-challenge: did dropping the global helper leave dangling code/config — no (script/launcher/tests removed, stale entry added, global test entry reverted, suite 3335 green); strongest-alternative: keep the global helper too (rejected — operator chose CLI out-of-box; app path manual/documented); verified end-to-end + on a live `ag` install; host docs corrected; no regression; faithfulness N/A).

## Dependencies

- No external wave dependencies.
