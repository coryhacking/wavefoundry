# Session Handoff

Owner: wave-coordinator
Status: active
Last verified: 2026-05-20

## Active Wave

**Wave:** `12rnv agent-prompt-harness`  
**Status:** active (Prepare wave passed 2026-05-20)  
**Changes:** `12rbe` (seed-213 + 007 security generalization), `12rnv` (harness core 209, specialists 217–219, inferential 212/214/221, bootstrap 007/050/100/020/180/215), `12rcp` (020 preflight rubric + role docs), `12rcd` (AGENTS.md implementation principles + seed-050), `12rp6-doc` (role-metadata lint + current journal behavior), `12rp6-enh` (new top-level Factor dashboard group), `12rpn` (factor agents move into shared taxonomy), `12rps` (category metadata drives dashboard grouping), `12rqn` (packaged prompt-surface manifest version bump), `12rqj` (dashboard wave framework visualization), `12rqs` (remove visible agent pill usage counters), `12rqt` (remove active-wave status pill)  
**Next:** Await operator signoff and closure. No further implementation is pending on this wave.

**Council items addressed during implementation:**
1. Verify seeds clean before opening gate.
2. `050` must prohibit `## Project harness extensions` from seed bodies.
3. `209` required packet fields: `wave_id`, `phase`, `change_ids`, `trust_boundaries_touched`, `files_in_scope`.
4. `100`/`180`: explicit `reality-checker` mode-dispatch.
5. Lane name `code-reviewer` (not `code-review`) for `221` in `007`.
6. Journal docs keep the current dashboard behavior and do not require `Role:`.
7. Factor is a distinct top-level dashboard group and must not be folded into specialists.
8. Factor agents live in the shared taxonomy; `.claude/agents/` is a pointer surface.
9. Category metadata drives dashboard grouping and propagates through seeds and host wrappers.
10. Packaging/version bumps must keep `VERSION`, `MANIFEST`, and `docs/prompts/prompt-surface-manifest.json` aligned.
11. The dashboard framework visualization must explain process flow using change/wave language without changing wave data contracts.
12. Active-wave cards should not show a visible status pill.
13. Dashboard agent pills should not show usage-count badges.

## Last Closed Wave

**Wave:** `12rbc mcp-impl-hot-reload` — closed 2026-05-20  
**Shipped:** `server.py` thin runner + `server_impl.py` split; `wave_mcp_reload` tool; in-process upgrade hook; version fields; dashboard browser suppression; 1482 tests green; package `2026-05-19h`.

## Open Questions / Deferred Decisions

- `close_warnings` path in `perform_mcp_reload` (when `ImplHandler.close()` raises) is not tested — advisory only; add test if close-error reporting becomes load-bearing.
- `wave_mcp_reload` does not add new tools to a live session (accepted limitation — requires client reconnect); revisit if FastMCP gains live tool-registration support.
