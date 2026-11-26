# Retrieval demotion shares only the history components

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24an6-mem retrieval-demotion-shares-only-the-history-components`
Kind: `decision`
Confidence: 0.7
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 97308
Supersedes: `1zz0q-mem decision-the-server-impl-py-demotion-site-adopts-the-shared-`
Retarget reason: bare server_impl.py now matches both scripts/server_impl.py (alias shim) and wf_server/server_impl.py, which holds _doc_demotion_weight
Checked at: 2026-11-26T06:32:43Z
Check note: The shared history classifier covers only some demotion inputs. Keep document-specific weighting local to its own policy. Reviewed .wavefoundry/framework/scripts/wf_server/server_impl.py:209.
Check flags: none

## Summary

When changing _doc_demotion_weight in .wavefoundry/framework/scripts/wf_server/server_impl.py, share only the history components (journals, snapshots) through history_paths.is_history_path, apply them to document results only (kind != code), and keep the ranking heuristic's own extras: the reports directory and the feedback/journal name tests. Why: decision of wave 1zyb2 (1zxnt); it is a ranking heuristic with different members, so only the shared members are shared, and target source code under a directory named like a history component must not be demoted.

## Evidence

- `1zxnt-maint correctness-and-test-hygiene-round`
- `1zyb2`

## Targets

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/history_paths.py`
