# Server implementation file playbook

Owner: Engineering
Status: active
Last verified: 2026-08-02

Memory ID: `1u8q1-mem server-impl-file-playbook`
Kind: `fragile_file`
Confidence: 0.95
Created: 2026-08-02
Updated: 2026-08-02

## Summary

Before changing server_impl.py, identify the affected seam—lifecycle gate, context-efficiency extractor, gardener output contract, memory-mint re-entry, or MCP response envelope—and verify its paired producer/consumer. Enumerate sibling lifecycle entries, forward every keyword through self-re-entry, assign response fields only on successful operations under data, mutate the claimed failure branch, and finish with focused tests plus a live post-reload probe.

## Evidence

- `1t1wx-mem`
- `1tboh-mem`
- `1tf7m-mem`
- `1tlaa-mem`
- `1tuyw-mem`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/docs_gardener.py`
