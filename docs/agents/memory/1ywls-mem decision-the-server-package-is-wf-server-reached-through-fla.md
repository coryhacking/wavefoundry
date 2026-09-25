# Decision: the server package is `wf_server`; only server_impl and dashboard_handlers keep flat sys.modules aliases

Owner: Engineering
Status: active
Last verified: 2026-09-25

Memory ID: `1ywls-mem decision-the-server-package-is-wf-server-reached-through-fla`
Kind: `decision`
Confidence: 0.9
Created: 2026-09-25
Updated: 2026-09-25
Source exploration cost: 121337
Source event: `decision-log:1yxql-ref server-package-boundary:fdc79f316426e1ec`
Validation: promote
Validated by: agent
Action delta: Name new server-owned modules into scripts/wf_server/ (never a top-level `server` package) and give them no flat name; import them as `import wf_server.<m> as <m>` or `from wf_server.<m> import ...`, never `from wf_server import <evicted module>`. Only server_impl and dashboard_handlers keep a three-line flat alias (wave 1yxyw).
Validation rationale: Evidence verified in the 1yzd0 change doc Decision Log (2026-09-25 rename row) and ADR 1yx4m: a `server/` package shadows server.py for every `import server` (demonstrated), the scripts root is on sys.path so the package name is a top-level import, and wf_server was unused in the repo and venv. The generated target `server.py` is the thing the name avoids, not the decision's subject, so the rewrite targets the package initializer and composition root, and adds the reload hazard found in delivery (from-import of an evicted package module keeps the stale module).
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Decision (wave 1yzd0, ADR 1yx4m): the MCP server's composition root, registry and handlers live in `.wavefoundry/framework/scripts/wf_server/`. A top-level `server/` package is refused because it shadows the flat `server.py` runner for every `import server`; the scripts root is on sys.path, so the package name is a top-level import and keeps the `wf_` prefix. Only `server_impl` and `dashboard_handlers` keep flat names, as three-line `sys.modules[__name__] = importlib.import_module("wf_server.<name>")` aliases (one module object per implementation), because installed 1.25/1.26 upgrade runners resolve the upgrade-mandatory modules' imports against flat stems; the package refuses to import when either is not that exact text. Wave 1yxyw retired the other ten flat names (`_RETIRED_FLAT_NAMES`): code outside the package names them as `wf_server.<name>`, and a leftover flat file is reported, never refused. Inside the package, a module the reload purge evicts is imported with `import wf_server.<m> as <m>` or `from wf_server.<m> import ...`, never `from wf_server import <m>`, which reuses the stale module bound on the never-evicted parent package.

## Evidence

- `1yxql-ref server-package-boundary`
- `1yzd0`
- `1yx4m-adr`
- `1yxwn-ref retire-optional-flat-server-aliases`

## Targets

- `.wavefoundry/framework/scripts/wf_server/__init__.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
