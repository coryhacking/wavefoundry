# Decision: Move criterion is domain ownership; two close-gate composit…

Owner: Engineering
Status: rejected
Last verified: 2026-09-22

Memory ID: `1ym21-mem decision-move-criterion-is-domain-ownership-two-close-gate-c`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-21
Updated: 2026-09-21
Source exploration cost: 394325
Source event: `decision-log:1ymzj-ref memory-handler-module:dfae86d8a863b992`
Validation: reject
Validated by: agent
Action delta: No additional memory action: use the canonical handler-ownership map when planning future splits.
Validation rationale: Verified the admitted Decision Log, current stayers in server_impl, and docs/architecture/domain-map.md plus current-state.md. The partition is durable and accurate, but both canonical architecture docs already state the same ownership rule. The bare basename target is also less accurate than those maintained owners. High confidence in duplication; reject rather than create another active policy copy.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates

## Summary

Decision (wave 1ymzk): Move criterion is domain ownership; two close-gate compositions and three crediting extractors stay.. Rationale: The lifecycle callers live in `server_impl.py`, which already imports the module at module top, so moving memory services changes no edge direction; the stayers are lifecycle and crediting logic, not memory services..

## Evidence

- `1ymzj-ref memory-handler-module`
- `1ymzk`

## Targets

- `server_impl.py`
