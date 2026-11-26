# Server implementation file playbook

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `249gg-mem server-implementation-file-playbook`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-25
Supersedes: `1u8q1-mem server-impl-file-playbook`

## Summary

When changing .wavefoundry/framework/scripts/wf_server/server_impl.py, first name the seam you touch (lifecycle gate, context-efficiency extractor, gardener output contract with docs_gardener.py, memory-mint re-entry, or MCP response envelope) and verify its paired producer and consumer. Enumerate sibling lifecycle entries, forward every keyword through self re-entry, assign response fields under data only on success, mutate the claimed failure branch to prove the test can fail, and finish with focused tests plus a live probe after wf_reload_mcp. Each of these seams produced a repaired defect in the consolidated source records, and the file is reloaded in place, so hermetic tests alone missed them.

## Evidence

- `1t1wx-mem fragile-server-impl-py-context-efficiency-instrumentation`
- `1tboh-mem`
- `1tf7m-mem`
- `1tlaa-mem`
- `1tuyw-mem`

## Targets

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/docs_gardener.py`
