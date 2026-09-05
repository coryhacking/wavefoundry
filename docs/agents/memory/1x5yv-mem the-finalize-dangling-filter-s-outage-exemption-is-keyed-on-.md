# The finalize dangling filter's outage exemption is keyed on the last published payload, not on the directory

Owner: Engineering
Status: active
Last verified: 2026-09-05

Memory ID: `1x5yv-mem the-finalize-dangling-filter-s-outage-exemption-is-keyed-on-`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-09-05
Updated: 2026-09-05

## Summary

Wave 1x6ti (1x5pc): the assembly-time dangling-endpoint filter in GraphIndexSession.finalize drops every edge whose endpoint is not a node, an external:: id or a widened current path. During a walk outage a node-less file under the unreadable directory (a .gitignore) has no store row to widen from; the first repair exempted any endpoint under the directory and resurrected edges the last readable build had dropped, because a deleted file and an existing node-less file look identical to the store there and a stat raises. The shipped predicate keeps such an edge only when its (source, target, relation) triple is in the last published payload (read once per merge, only during an outage) and every unservable endpoint's file is under the reported directory. Any change to this predicate needs its own locality, boundary and non-resurrection tests (DanglingEndpointFilterTests) and a sweep of the eleven prose sites that state it (finalize docstring, graph-index-system.md, CHANGELOG, wave and change records).

## Evidence

- `1x6ti`
- `CODE-DEL-1`
- `CODE-RV1-2`
- `QA-RV1-1`
- `CODE-RV1-1`
- `QA-RV1-2`
- `DOCS-RV1-2`
- `test_graph_incremental_merge.DanglingEndpointFilterTests`

## Targets

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py`
