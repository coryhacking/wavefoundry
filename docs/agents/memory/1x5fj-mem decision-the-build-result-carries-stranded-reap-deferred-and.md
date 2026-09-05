# Decision: The build result carries `stranded_reap_deferred` and `stra…

Owner: Engineering
Status: superseded
Last verified: 2026-09-04

Memory ID: `1x5fj-mem decision-the-build-result-carries-stranded-reap-deferred-and`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-04
Updated: 2026-09-04
Source exploration cost: 1539381
Source event: `decision-log:1u8o3-debt eligibility-reap-mass-removal-hazard:77c224882b189d20`
Validation: rewrite
Validated by: agent
Action delta: Before claiming a build-result field is an envelope contract, check whether any registered tool relays the build_index return value; index_build spawns detached and index_build_status and index_health read only the log, the stats file and the store.
Validation rationale: The draft copied the Decision Log row written before SEC-RV1-1 qualified it. The verified fact (security seat census of run_index_rebuild, index_build_status_response and index_health_response; wf_list_plans listing 1x551) is that the two fields exist only in the Python result, stderr and the index-state log; the durable lesson is the transport gap, not the field names.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1x69c-mem reap-deferral-and-preservation-live-in-the-python-build-inde`
## Summary

Decision (wave 1x54z): The build result carries `stranded_reap_deferred` and `stranded_reap_preserved` at both seams (SEC-DEL-1); an `index_health` diagnostic is a recorded follow-on.. Rationale: The envelope is the contract surface of `index_build`, and a control the operator cannot observe is a control they cannot act on; persisting the deferral for `index_health` needs an epoch-free store write and a `server_impl.py` change that belongs to its own change..

## Evidence

- `1u8o3-debt eligibility-reap-mass-removal-hazard`
- `1x54z`

## Targets

- `server_impl.py`
