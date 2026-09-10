# Decision: Hash implementation lives once in `server_impl.compute_runn…

Owner: Engineering
Status: candidate
Last verified: 2026-09-09

Memory ID: `1xi58-mem decision-hash-implementation-lives-once-in-server-impl-compu`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-09
Updated: 2026-09-09
Source exploration cost: 818447
Source event: `decision-log:1u2ay-bug server-runner-version-never-distinguishes-stale-runner:6892998ab378d0ef`
Validation: pending

## Summary

Decision (wave 1u2b0): Hash implementation lives once in `server_impl.compute_runner_identity`; `server.py` calls it at launch. Rationale: One canonical algorithm, no duplicated hashing that could silently diverge; server.py imports server_impl before the capture so ordering is safe. If a future wave changed the algorithm, the runner file ships alongside, so the resulting stale=true is truthful; an impl-only algorithm edit in a dev checkout yields an acceptable spurious stale (restart is the safe recovery, per req 5).

## Evidence

- `1u2ay-bug server-runner-version-never-distinguishes-stale-runner`
- `1u2b0`

## Targets

- `server.py`
