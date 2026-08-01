# Decision: Hash implementation lives once in `server_impl.compute_runn…

Owner: Engineering
Status: superseded
Last verified: 2026-07-31

Memory ID: `1u2vw-mem decision-hash-implementation-lives-once-in-server-impl-compu`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 777948
Source event: `decision-log:1u2ay-bug server-runner-version-never-distinguishes-stale-runner:6892998ab378d0ef`
Validation: rewrite
Validated by: agent
Action delta: Change the runner-identity hash only in server_impl.compute_runner_identity, never by adding a second hashing site in server.py, and keep server.py's getattr access to it so a torn mid-upgrade tree still launches on the "unavailable" sentinel.
Validation rationale: The decision is durable and correctly reasoned, but the draft targets only the bare basename `server.py` — the file that CALLS the helper — while the implementation and the constraint both live in server_impl.compute_runner_identity, so a future editor of that function would never see this record. Verified in the current tree: server_impl.py:23338 defines compute_runner_identity with a comment at :23329 explaining that a literal here would silently diverge; server.py:67-68 reaches it through `getattr(server_impl, "compute_runner_identity", lambda _files: None)` falling back to "unavailable"; server_impl.py:24887 recomputes the disk-side identity for the wf_server_info staleness comparison. Rewritten with full repo-relative targets and the divergence/sentinel rationale kept intact.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1u55k-mem runner-identity-hashing-has-exactly-one-implementation-site-`
## Summary

Decision (wave 1u2b0): Hash implementation lives once in `server_impl.compute_runner_identity`; `server.py` calls it at launch. Rationale: One canonical algorithm, no duplicated hashing that could silently diverge; server.py imports server_impl before the capture so ordering is safe. If a future wave changed the algorithm, the runner file ships alongside, so the resulting stale=true is truthful; an impl-only algorithm edit in a dev checkout yields an acceptable spurious stale (restart is the safe recovery, per req 5).

## Evidence

- `1u2ay-bug server-runner-version-never-distinguishes-stale-runner`
- `1u2b0`

## Targets

- `server.py`
