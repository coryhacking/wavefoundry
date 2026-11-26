# Changing the finalize dangling-endpoint filter needs locality, boundary and non-resurrection tests plus a prose sweep

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24aqr-mem changing-the-finalize-dangling-endpoint-filter-needs-localit`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-26
Supersedes: `1x5yv-mem the-finalize-dangling-filter-s-outage-exemption-is-keyed-on-`
Checked at: 2026-11-26T06:32:44Z
Check note: Graph finalization uses unreadable paths when resolving endpoints. Test the affected boundary and adjacent unaffected paths. Reviewed .wavefoundry/framework/scripts/graph_indexer.py:15335.
Check flags: none

## Summary

When you change the assembly-time dangling-endpoint filter in GraphIndexSession.finalize (.wavefoundry/framework/scripts/graph_indexer.py), keep its walk-outage exemption keyed on the last published payload, not on the directory. The filter keeps an edge into an unreadable directory only when the last published generation served the same (source, target, relation) triple and every unservable endpoint lies under the reported directory. During an outage the store cannot tell a deleted file from an existing file that has no node (a .gitignore), and a stat raises. The first repair exempted the whole directory and resurrected edges the last readable build had dropped (wave 1x6ti, 1x5pc, CODE-DEL-1). Extend DanglingEndpointFilterTests with locality, boundary and non-resurrection cases. Sweep the prose that states the predicate in the same edit: the finalize comment, graph-index-system.md, CHANGELOG and the 1x6ti wave and change records.

## Evidence

- `1x6ti`
- `CODE-DEL-1`
- `CODE-RV1-1`
- `CODE-RV1-2`
- `QA-RV1-1`
- `QA-RV1-2`
- `DOCS-RV1-2`
- `test_graph_incremental_merge.DanglingEndpointFilterTests`

## Targets

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_graph_incremental_merge.py`
