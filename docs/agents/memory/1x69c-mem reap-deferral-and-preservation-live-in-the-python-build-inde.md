# Reap deferral and preservation live in the Python build_index result, not in any registered tool response

Owner: Engineering
Status: active
Last verified: 2026-09-25

Memory ID: `1x69c-mem reap-deferral-and-preservation-live-in-the-python-build-inde`
Kind: `decision`
Confidence: 0.9
Created: 2026-09-04
Updated: 2026-09-04
Source exploration cost: 1539381
Source event: `decision-log:1u8o3-debt eligibility-reap-mass-removal-hazard:77c224882b189d20`
Validation: promote
Validated by: agent
Action delta: Before claiming a build-result field is an envelope contract, check whether any registered tool relays the build_index return value; index_build spawns detached and index_build_status and index_health read only the log, the stats file and the store.
Validation rationale: The draft copied the Decision Log row written before SEC-RV1-1 qualified it. The verified fact (security seat census of run_index_rebuild, index_build_status_response and index_health_response; wf_list_plans listing 1x551) is that the two fields exist only in the Python result, stderr and the index-state log; the durable lesson is the transport gap, not the field names.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1x54z: build_index returns stranded_reap_deferred and stranded_reap_preserved at both seams, but the registered index_build tool spawns indexer.py detached and returns a spawn acknowledgement, and index_build_status and index_health read only the build log, the stats file and the state store, so under an MCP-driven or hook-driven build both states are visible only on stderr and in the index-state log. Plan 1x551 persists them epoch-free and reports them through index_build_status and index_health. When a build gains a result field an operator must act on, trace whether a registered tool relays it before calling the envelope a contract surface.

## Evidence

- `SEC-DEL-1`
- `SEC-RV1-1`
- `1x551-debt index-health-surfaces-reap-deferral-and-preservation`
- `1x54z`

## Targets

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/indexer.py`
