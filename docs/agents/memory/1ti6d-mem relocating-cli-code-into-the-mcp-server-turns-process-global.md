# Relocating CLI code into the MCP server turns process-global mutation into corruption

Owner: Engineering
Status: active
Last verified: 2026-07-25

Memory ID: `1ti6d-mem relocating-cli-code-into-the-mcp-server-turns-process-global`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-07-25
Updated: 2026-07-25
Source exploration cost: 224660
Source event: `finding:1tis8:memory-eval-global-monkeypatch-concurrency`
Validation: promote
Validated by: agent
Action delta: Before relocating a script into the MCP server (or exposing one as a tool), grep it for assignments to imported-module attributes; convert any temporary global mutation into explicit parameter threading before it ships, and pin the absence structurally with a source assertion.
Validation rationale: Verified against the terminal ledger chain and the current tree: the defect was real and reproduced by the reviewer's two-thread probe (restored_original false, subsequent lookup {}), the repair removes the mutation rather than serializing it, and re-running that same probe against the fixed code passes (restored_original true, 1.57e9 clean watcher samples). Rewritten rather than promoted because the drafted summary described only this instance; the durable lesson is the relocation hazard class, which applies to every future script promoted into the server. Targets are the two repaired modules.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Before moving any script into the long-lived MCP server, audit it for temporary mutation of module-global state. memory_eval's run_curated rebound index_state_store.file_commit_times and restored it in a finally — safe in a single-shot CLI process, corrupting in the server: two overlapping wf_memory_eval calls restore out of order and leave one call's frozen-subset lambda installed permanently, while unrelated concurrent memory_search readers observe the replacement. A lock around the tool is NOT sufficient because the corruption is visible to readers that never take the lock; remove the shared mutation instead. The fix threads frozen histories explicitly (_memory_ranked commit_times_override) and seeds hermetic fixtures through the canonical writer rather than patching. Pin it structurally: assert the source contains no assignment to the global, so reintroduction fails even when a race does not reproduce.

## Evidence

- `memory-eval-global-monkeypatch-concurrency`
- `1tgws-enh memory-eval-shippable-mcp-tool`
- `test_eval_never_rebinds_the_shared_commit_times_global`
- `1tis8`

## Targets

- `.wavefoundry/framework/scripts/memory_eval.py`
- `.wavefoundry/framework/scripts/server_impl.py`
