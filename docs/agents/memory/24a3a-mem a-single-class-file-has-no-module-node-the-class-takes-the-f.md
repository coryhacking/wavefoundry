# A single-class file has no module node; the class takes the file id

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24a3a-mem a-single-class-file-has-no-module-node-the-class-takes-the-f`
Kind: `environment_gotcha`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-25
Supersedes: `1x2xi-mem a-single-class-file-has-no-module-node-the-class-takes-the-f`

## Summary

When code maps a graph node back to the file that owns it, split the id on '::' and fall back to the node itself, as graph_query.GraphQueryIndex.is_evidence_node does. Do not look up a module node. In the graph index, a file whose only top-level construct is one class emits no module node: the class node carries the bare file id (svc/session.py has kind class, plus svc/session.py::Session.open). A file with any other top-level construct also gets a module node. A lookup by module node silently misses every single-class file. Wave 1wpih recorded this as a declared gap in docs/evals/graph-quality-golden.json instead of changing the identity scheme, because a change would move every single-class file in every consuming repository.

## Evidence

- `1wpih`
- `1wpie-enh graph-quality-evaluation-and-evidence-isolation`
- `graph_query.GraphQueryIndex.is_evidence_node`
- `test_graph_quality_eval.ScoringAgainstARealGraphTests.test_every_miss_is_a_declared_gap_and_every_declared_gap_still_misses`

## Targets

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/graph_query.py`
- `docs/evals/graph-quality-golden.json`
