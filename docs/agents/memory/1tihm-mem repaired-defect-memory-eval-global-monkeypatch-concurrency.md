# Repaired defect memory-eval-global-monkeypatch-concurrency

Owner: Engineering
Status: superseded
Last verified: 2026-07-25

Memory ID: `1tihm-mem repaired-defect-memory-eval-global-monkeypatch-concurrency`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-25
Updated: 2026-07-25
Source exploration cost: 224660
Source event: `finding:1tis8:memory-eval-global-monkeypatch-concurrency`
Validation: rewrite
Validated by: agent
Action delta: Before relocating a script into the MCP server (or exposing one as a tool), grep it for assignments to imported-module attributes; convert any temporary global mutation into explicit parameter threading before it ships, and pin the absence structurally with a source assertion.
Validation rationale: Verified against the terminal ledger chain and the current tree: the defect was real and reproduced by the reviewer's two-thread probe (restored_original false, subsequent lookup {}), the repair removes the mutation rather than serializing it, and re-running that same probe against the fixed code passes (restored_original true, 1.57e9 clean watcher samples). Rewritten rather than promoted because the drafted summary described only this instance; the durable lesson is the relocation hazard class, which applies to every future script promoted into the server. Targets are the two repaired modules.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1ti6d-mem relocating-cli-code-into-the-mcp-server-turns-process-global`
## Summary

Real defect fixed in wave 1tis8: Repair verified complete by re-running the reviewer's own failing probe against the fixed code. The global mutation is gone rather than merely serialized, which was required because the corruption was observable by unrelated readers and a…

## Evidence

- `memory-eval-global-monkeypatch-concurrency`
- `ev-memory-eval-global-monkeypatch-concurrency-3`
- `1tis8`

## Targets

- `test_memory_eval.py`
- `.wavefoundry/framework/scripts/memory_eval.py`
- `server_impl.py`
