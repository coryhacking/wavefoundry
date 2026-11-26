# Decision: Do not modify global stdout isolation.

Owner: Engineering
Status: archived
Last verified: 2026-11-10

Memory ID: `1t6yr-mem decision-do-not-modify-global-stdout-isolation`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-21
Updated: 2026-11-25
Source exploration cost: 134080
Source event: `decision-log:1t59o-bug wf-audit-bounded-index-health:7c0651e234bb60e4`
Validation: promote
Validated by: agent
Action delta: When protecting the MCP stream from native fd-1 writes, rely on the startup-level isolation in server.py and never add per-call process-global fd redirects; remember runner changes need a full host restart, and triage old-install hang reports against the 1.9.7 isolation boundary.
Validation rationale: The drafted summary echoed the Decision Log line verbatim with doubled periods; the durable content is the single-authority rule (startup isolation, no per-call dup2 due to process-global races), the reload-vs-restart boundary for runner code, and the version triage anchor. Verified against server.py:104-150 on the current tree; supplements the stdout-protection gotcha memory.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Checked at: 2026-11-25T16:09:19Z
Check note: Item 7 review: target gone or duplicate. The bare target 'server.py' is ambiguous (it also matches docs/waves/1yzd0 server-package-boundary/evidence/demo/main_alias/server.py). The decision is carried at its own code: the _isolate_native_stdout_from_protocol docstring (.wavefoundry/framework/scripts/server.py:555-573) states fd 1 is isolated once process-wide and that a per-call os.dup2 is unsafe.
Check flags: target_unresolved
Archived: 2026-11-25
Archive reason: Retired in the 244cm item 7 review, gone or carried by The bare target 'server.py' is ambiguous (it also matches docs/waves/1yzd0 server-package-boundary/evidence/demo/main_alias/server.py). The decision is carried at its own code: the _isolate_native_stdout_from_protocol docstring (.wavefoundry/fr.
Archive path: `docs/agents/memory/archive/1t6yr-mem decision-do-not-modify-global-stdout-isolation.md`

## Summary

Decision (wave 1t59p): startup-level stdout isolation in `server.py` (`_isolate_native_stdout_from_protocol`: the MCP protocol gets a private dup of stdout; OS fd 1 points at devnull before transport starts) is the single authority for native fd-1 protection. Do not add per-call `os.dup2` redirects around individual operations: fd 1 is process-global, so a per-call redirect races concurrent operations (the background prewarm thread lesson from 1p8vd). Two operational corollaries: (1) runner (`server.py`) updates only take effect after a full host restart, not `wf_reload_mcp` (the reload swaps `server_impl`, not the running runner); (2) hang reports on old installs must be triaged against whether their runner predates the isolation (shipped 1.9.7).

## Evidence

- `1t59o-bug wf-audit-bounded-index-health`
- `1t59p`

## Targets

- `server.py`
