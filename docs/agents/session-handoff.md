# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-07-03

## Current State (2026-07-03, post-close)

**Wave `1p9qm subagent-mcp-retrieval-posture` is CLOSED (2026-07-03, operator-approved)** — review PASS, all ACs `[x]`, `Completed At` stamped. Next up per operator direction: **Implement wave `1p9q3 graph-index-efficiency`**.

Both changes are `implemented` with **all ACs `[x]`**:

- `1p9qk-bug subagent-mcp-tool-access` — AC-2's final sliver (the council-mandated no-MCP spawn check) PASSED 2026-07-03: guru wrapper spawned cleanly in a fresh headless session with no wavefoundry MCP registered; unknown `mcp__wavefoundry__*` allowlist entries silently dropped (inert); render-time-conditional pivot NOT needed.
- `1p9ql-enh subagent-retrieval-posture-guidance` — AC-5 captured from this wave's own Review-wave fan-out: 9/9 lanes/seats made their first `code_*` call before any content grep (baseline: Solaris round-1 = 0 MCP calls); attribution-scope + claim-backing-variant qualifications recorded in the AC.

**Review wave ran 2026-07-03:** four delivery lanes (code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer) — all pass-with-findings — plus the full delivery council (red-team primer, four fixed seats, rotating docs-contract fifth seat). Synthesis verdict **PASS**; `wave-council-delivery` recorded in Review Evidence; full synthesis in wave.md Review Checkpoints. All severe findings were **fixed in-session at operator direction**:

1. `.codex/config.toml` restored (the AC-4 re-render had silently deleted the operator's `wave_close approval_mode` block — the known unlanded `1p9p7` renderer-overwrite defect, second field occurrence after `1p9j0`).
2. Carrier wiring (seed gate): seed-020 "Rendered carrier" bullet; seed-150 task 5 reconciles/backfills the `## Retrieval Posture (All Lanes)` section + review-and-evals pointer; seed-160 audit checklist names both (stale "six rules" count fixed); seed-050 requires the factor-wrapper body bullet (+ guru carve-out sentence).
3. Test regex hardening (body⊆frontmatter check now catches `seed_get`/`wave_*`/`mcp__` forms); evidence-note corrections in both change docs.

Gates: full suite **4,273 OK** after all fixes; docs-lint clean; no `__pycache__`; seed gate opened/closed per edit session.

**Close + commit executed 2026-07-03 at explicit operator direction** ("close and commit"); wave `1p9q3` implementation follows in the same session.

**⚠ Standing until `1p9p7 renderer-overwrite-safety` (wave `1p9pe`) lands:** every `render_agent_surfaces` run rewrites `.codex/config.toml` and deletes the operator's `wave_close approval_mode` block — restore it after ANY re-render (`git checkout -- .codex/config.toml`).

**Recommended follow-up change (from delivery council, not yet planned):** registry-derived allowlist test pin (compare `_REQUIRED_GRANTS` against `server_impl`'s `_READONLY_TOOL` set, both directions — also resolves the recorded `code_hover`/`code_risk_score` exclusion) + docs-lint `check_factor_surface` extension validating wrapper `tools:` lines (fleet-wide enforcement).

## Other Session Work (all readied, none OPEN)

Waves planned + council-readied earlier, awaiting `Implement wave` after 1p9qm closes:
- `1p9q3 graph-index-efficiency` (4 changes)
- `1p9q8 graph-index-accuracy` (4 changes)
- `1p9qh java-csharp-enterprise-accuracy` (3 changes)
- `1p9qi sql-graph-accuracy` (5 changes)
Suggested implement order: 1p9q3 → 1p9qh → 1p9qi (1p9q8 slots anywhere).

Pre-existing planned waves untouched: `1p9pe post-release-followup-hardening` (now more urgent — see standing note above), `1p6lp cross-host-skills`.

**Uncommitted working tree** spans the readied-wave planning docs + the full 1p9qm implementation + review fixes (seeds 020/050/100/150/160/180 + 22 role seeds, renderer + tests, 5 wrappers, AGENTS.md, contributing docs, wave records). Commits are operator-owned.

## Coordination Watchpoints

- The AGENTS.md auto-Guru paragraph was edited by `1p9qm`; wave `1p9q3`'s `1p9pz` docs rider also touches that section — coordinate when `1p9q3` opens.
- `docs/specs/mcp-tool-surface.md` has three readied waves wanting vocabulary edits (`1p9q3`, `1p9qh`, `1p9qi`) — one integration owner.
- After downstream repos upgrade, ask the Solaris reporter to re-run their transcript count — the true field verification for the retrieval-posture surfaces (recorded in 1p9ql AC-5 and the wave watchpoints).
- Host lessons from this wave (also in 1p9qk Progress Log): exact-name MCP grants in subagent `tools:` ARE honored; granted MCP tools arrive deferred (hence `ToolSearch` in allowlists); agent definitions reload on `/mcp` reconnect, not on file edit; MCP-less spawns silently drop unknown MCP allowlist entries; subagents report only `Read`+`Bash` of the granted built-ins in this host build.

## Current Session

**Active wave:** *(none)*
