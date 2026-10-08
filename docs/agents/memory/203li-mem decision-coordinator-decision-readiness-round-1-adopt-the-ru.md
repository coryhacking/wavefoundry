# Decision: Coordinator decision (readiness round 1): adopt the rule pl…

Owner: Engineering
Status: rejected
Last verified: 2026-10-08

Memory ID: `203li-mem decision-coordinator-decision-readiness-round-1-adopt-the-ru`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-08
Updated: 2026-10-08
Source exploration cost: 1072877
Source event: `decision-log:1zyv2-bug contained-repo-reads-and-writes:fcc8585a22e2cda2`
Validation: reject
Validated by: agent
Action delta: Use the published whole-renderer containment contract and its named residual boundaries.
Validation rationale: Verified Decision Log and current renderer coverage are already described in cross-cutting-concerns.md:185 and threat-model.md:75; this generated record repeats that contract.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates

## Summary

Decision (wave 200ey): Coordinator decision (readiness round 1): adopt the rule plus a census for `render_platform_surfaces.py` and `render_agent_surfaces.py`, so every repository read and write in both, including the existing-config merge reads and the marker-block writes, goes through `contained_files`; `dashboard_lib.collect_activity`'s handoff read and `docs_gardener.ensure_session_handoff` become named follow-ups, and the CHANGELOG and threat-model text name only what is covered.. Rationale: One rule per module is reviewable; a partial list leaves sibling reads in the same module outside it..

## Evidence

- `1zyv2-bug contained-repo-reads-and-writes`
- `200ey`

## Targets

- `render_platform_surfaces.py`
- `render_agent_surfaces.py`
