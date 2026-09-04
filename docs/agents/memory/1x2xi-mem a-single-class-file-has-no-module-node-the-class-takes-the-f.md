# A single-class file has no module node; the class takes the file's id

Owner: Engineering
Status: active
Last verified: 2026-09-04

Memory ID: `1x2xi-mem a-single-class-file-has-no-module-node-the-class-takes-the-f`
Kind: `environment_gotcha`
Confidence: 0.9
Created: 2026-09-04
Updated: 2026-09-04

## Summary

In the graph index, a file whose only top-level construct is one class emits NO module node: the class node carries the file's bare id, so `svc/session.py` has `kind: class`. A file with any other top-level construct also gets its own `module` node. Verified by building both shapes through the real `update_graph_index` entry: the one-class file yields `class svc/session.py` plus `function svc/session.py::Session.open`, while a mixed file yields `module svc/mixed.py` alongside its class and function. Anything mapping a node back to its owning file must split on `::` and fall back to the node itself, which is what `graph_query.GraphQueryIndex.is_evidence_node` does; a module-node lookup silently misses every single-class file. Wave `1wpih` declared this as a known gap in the graph-quality corpus rather than repairing it, because changing the identity scheme would move every single-class file in every consuming repository -- far outside a measurement wave.

## Evidence

- `1wpih`
- `1wpie-enh graph-quality-evaluation-and-evidence-isolation`
- `graph_query.GraphQueryIndex.is_evidence_node`
- `test_graph_quality_eval.ScoringAgainstARealGraphTests.test_every_miss_is_a_declared_gap_and_every_declared_gap_still_misses`
- `1x42l-mem decision-record-the-single-class-file-node-identity-collapse`

## Targets

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/graph_query.py`
- `docs/evals/graph-quality-golden.json`
