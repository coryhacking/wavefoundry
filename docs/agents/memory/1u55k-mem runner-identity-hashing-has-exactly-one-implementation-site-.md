# Runner-identity hashing has exactly one implementation site: server_impl.compute_runner_identity

Owner: Engineering
Status: active
Last verified: 2026-07-31

Memory ID: `1u55k-mem runner-identity-hashing-has-exactly-one-implementation-site-`
Kind: `decision`
Confidence: 0.85
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 777948
Source event: `decision-log:1u2ay-bug server-runner-version-never-distinguishes-stale-runner:6892998ab378d0ef`
Validation: promote
Validated by: agent
Action delta: Change the runner-identity hash only in server_impl.compute_runner_identity, never by adding a second hashing site in server.py, and keep server.py's getattr access to it so a torn mid-upgrade tree still launches on the "unavailable" sentinel.
Validation rationale: The decision is durable and correctly reasoned, but the draft targets only the bare basename `server.py` — the file that CALLS the helper — while the implementation and the constraint both live in server_impl.compute_runner_identity, so a future editor of that function would never see this record. Verified in the current tree: server_impl.py:23338 defines compute_runner_identity with a comment at :23329 explaining that a literal here would silently diverge; server.py:67-68 reaches it through `getattr(server_impl, "compute_runner_identity", lambda _files: None)` falling back to "unavailable"; server_impl.py:24887 recomputes the disk-side identity for the wf_server_info staleness comparison. Rewritten with full repo-relative targets and the divergence/sentinel rationale kept intact.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

The runner identity hash is implemented once, in server_impl.compute_runner_identity, and both sides use it: server.py calls it at launch to capture SERVER_RUNNER_VERSION over SERVER_RUNNER_FILES, and server_impl recomputes the disk-side value at wf_server_info query time. A second copy of the algorithm in the thin runner would silently diverge and turn every comparison into a false stale report, so never inline or re-author the hash in server.py. server.py reaches the helper through getattr with an "unavailable" fallback so a torn mid-upgrade tree (new runner paired with an older impl that lacks the helper) still launches rather than crashing; comparisons then read null. Accepted tradeoff: if a future wave changes the algorithm, the runner file ships alongside so the resulting stale=true is truthful, and an impl-only algorithm edit in a dev checkout yields a spurious stale whose safe recovery is a host restart.

## Evidence

- `1u2ay-bug server-runner-version-never-distinguishes-stale-runner`
- `1u2b0`
- `.wavefoundry/framework/scripts/server_impl.py:23329-23338`
- `.wavefoundry/framework/scripts/server_impl.py:24887`
- `.wavefoundry/framework/scripts/server.py:60-70`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
