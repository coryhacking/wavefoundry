# Decision: Apply the CA bundle at the model-download choke point insid…

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-apply-the-ca-bundle-at-the-model-download-choke-poi`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p92t-bug ca-bundle-non-setup-launchers:98a55f2cea6ea16d`
Validation: reject
Validated by: agent
Action delta: None; use the consolidated model-download path census memory instead of the original incomplete choke-point claim.
Validation rationale: This source claim was explicitly corrected twice in the same wave and is unsafe as standalone guidance.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1p939): Apply the CA bundle at the model-download choke point inside `accel_embedder` (`_hf_download_cached_first` / `_ensure_fastembed_model_cached`), reusing `setup_index`'s existing resolution functions.. Rationale: All non-setup launchers (MCP tool, dashboard watcher, background refresh) already funnel through these two functions, so fixing the choke point covers every launcher without touching each entrypoint. Reuses proven logic instead of duplicating CA discovery..

## Evidence

- `1p92t-bug ca-bundle-non-setup-launchers`
- `1p939`

## Targets

- `server.py`
- `indexer.py`
