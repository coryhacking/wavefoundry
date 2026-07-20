# Decision: Incremental candidates: `run_secrets_scan.py` uses ALL trac…

Owner: Engineering
Status: superseded
Last verified: 2026-07-18

Memory ID: `mem-decision-incremental-candidates-run-secrets-scan-py-uses-all`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1rsha-enh incremental-secret-scan-cache:c8a6b38bde212073`
Validation: rewrite
Validated by: agent
Action delta: Preserve the distinct candidate semantics and full-scan bypass whenever secret-scan caching or file selection changes.
Validation rationale: Current source and tests still implement this non-obvious split, and losing it would silently reduce precision across branch switches or explicit full scans.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `mem-preserve-content-addressed-secret-scan-candidate-semantics`
## Summary

Decision (wave 1rsh9): Incremental candidates: `run_secrets_scan.py` uses ALL tracked files with the content-addressed skip (git gate replaced — precise across branch switches/touch-revert, decoupled from git status; first post-ship scan is a one-time cold-cache full pass); the indexer build path keeps its precise changed-set as candidates and cache-filters within it. `--mode full` and rules/scanner-version escalations bypass the skip entirely and repopulate the cache.. Rationale: The standalone scanner is where git-noise waste lived; the indexer already has exact change detection, so filtering within its changed-set adds robustness without re-hashing the repo every build. Full-mode bypass keeps an operator's explicit full scan a REAL full scan (cache-recovery escape hatch)..

## Evidence

- `1rsha-enh incremental-secret-scan-cache`
- `1rsh9`

## Targets

- `run_secrets_scan.py`
