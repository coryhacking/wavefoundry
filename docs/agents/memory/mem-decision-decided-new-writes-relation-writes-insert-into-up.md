# Decision: **DECIDED: new `writes` relation** (writes = INSERT INTO/UP…

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-decided-new-writes-relation-writes-insert-into-up`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p9qd-enh sql-structured-statement-extraction:4693022da5852890`
Validation: reject
Validated by: agent
Action delta: None; use the current graph relation schema, report consumers, and executable tests as authority.
Validation rationale: The reads-versus-writes relation decision is now canonical architecture and too detailed for a supplemental action memory.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1p9qi): **DECIDED: new `writes` relation** (writes = INSERT INTO/UPDATE/DELETE FROM/MERGE INTO/ALTER/DROP/TRUNCATE targets); read direction reuses `reads`. **Consumer-sweep evidence (all sites from the Serialization Points list):** (1) `_resolve_fragment_edge` — the decisive fact: the `reads` branch is constant-gated (unique-CONSTANT-or-TOMBSTONE, 1p4ls), so table references need dedicated routing REGARDLESS of representation; a `mode` property would not have avoided that and would additionally hide direction from every relation filter. (2) `_GRAPH_SIGNAL_RELATIONS` (`server_impl.py:251`) + `_GRAPH_REL_LABEL`/`_GRAPH_REL_BUCKET`: `writes` JOINS them (`writer`/`writers` — "what uses table X" includes its writers); pinned test updated. (3) 1p4ls `reads` policy inheritance decided CONSCIOUSLY: table reads inherit opt-in 1-hop + clustering exclusion (graph-signal passes `reads` explicitly so `code_ask` is unaffected); `writes` is NOT opt-in (sparse, high-value). (4) `_DEFAULT_IMPACT_RELATIONS`: unchanged — instead a narrow data-layer exception in `graph_impact` (default traversals follow `reads`/`writes` edges touching a `sql_kind` node; explicit `relations` opts out, dispatch-seed precedent) delivers AC-3 without letting constant reads into blast radius. (5) `_path_edge_cost`: reads/writes stay structural tier (100) — a shared table never out-competes a call chain. (6) `graph_cluster`: no code change — `reads` exclusion inherited; `writes` clusters at dict-default weight 1 (was `calls` weight 3 — SQL clustering signal shifts, accepted; revisit on field evidence). (7) `wave_graph_report`: fan rankings count data-layer edges so tables stay visible (they lost their `calls` in-edges); rows carry `sql_kind`. (8) Dashboard (`dashboard_lib.py`/`dashboard_server.py`): grep-verified ZERO relation-name consumers — out of scope with evidence. (9) Incremental merge: no new fragment summary keys needed (edges ride the existing `edges` fragment; `sql_kind`/`sql_error_regions` are node-borne, recovered from per-file fragments by construction); `_edge_lookup_keys` extended so scope-(b) re-resolution consults call-shaped keys for SQL reads/writes.. Rationale: `mode: write` property on `reads` — rejected: hides direction from relation-level filtering (impact/path/signal/report all filter by relation), still requires the SQL-origin resolution routing, and leaves "reads" semantically false for a DELETE target. Reusing `calls` — rejected: perpetuates the direction-less model the change exists to fix..

## Evidence

- `1p9qd-enh sql-structured-statement-extraction`
- `1p9qi`

## Targets

- `server_impl.py`
- `dashboard_lib.py`
- `dashboard_server.py`
