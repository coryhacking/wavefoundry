# Decision: Name the package `wf_server` (was `wavefoundry_server` in r…

Owner: Engineering
Status: superseded
Last verified: 2026-09-25

Memory ID: `1yxn1-mem decision-name-the-package-wf-server-was-wavefoundry-server-i`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-25
Updated: 2026-09-25
Source exploration cost: 121337
Source event: `decision-log:1yxql-ref server-package-boundary:fdc79f316426e1ec`
Validation: rewrite
Validated by: agent
Action delta: Name new server-owned modules into scripts/wf_server/ (never a top-level `server` package); any flat name for a package module is a three-line sys.modules alias, and package code never uses `from wf_server import <evicted module>`.
Validation rationale: Evidence verified in the 1yzd0 change doc Decision Log (2026-09-25 rename row) and ADR 1yx4m: a `server/` package shadows server.py for every `import server` (demonstrated), the scripts root is on sys.path so the package name is a top-level import, and wf_server was unused in the repo and venv. The generated target `server.py` is the thing the name avoids, not the decision's subject, so the rewrite targets the package initializer and composition root, and adds the reload hazard found in delivery (from-import of an evicted package module keeps the stale module).
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1ywls-mem decision-the-server-package-is-wf-server-reached-through-fla`

## Summary

Decision (wave 1yzd0): Name the package `wf_server` (was `wavefoundry_server` in readiness). Rationale: Operator decision. `server` is taken: a `server/` package shadows the flat `server.py` entry point for every `import server` (`dashboard_lib`, `upgrade_handlers`, tests), verified by demonstration. The scripts root is on `sys.path`, so the package is a top-level import name and keeps a project prefix (PEP 8 naming; packaging guidance on unique top-level names); `wf_server` is unused in the repository and the tool venv.

## Evidence

- `1yxql-ref server-package-boundary`
- `1yzd0`

## Targets

- `server.py`
