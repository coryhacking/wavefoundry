# Decision: Record the single-class-file node-identity collapse as a fi…

Owner: Engineering
Status: rejected
Last verified: 2026-09-04

Memory ID: `1x42l-mem decision-record-the-single-class-file-node-identity-collapse`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-04
Updated: 2026-09-04
Source exploration cost: 458752
Source event: `decision-log:1wpie-enh graph-quality-evaluation-and-evidence-isolation:9866459d7049053a`
Validation: reject
Validated by: agent
Action delta: Rejected as drafted because its only target is a corpus fixture path that does not exist in the tree; the underlying fact is real and is being recorded separately against the extractor and the resolver that compensates for it.
Validation rationale: The claim itself verifies. Building two files through the real `update_graph_index` entry: `svc/mixed.py` (a function plus a class) yields `module svc/mixed.py` alongside its class and function nodes, while `svc/session.py` (one class only) yields `class svc/session.py` and `function svc/session.py::Session.open` with NO module node, so the class carries the file's bare id. But the candidate's sole target, `svc/session.py`, is a path inside the graph-quality corpus fixture, not a file in this repository, so the record points at nothing a future reader can open and the validator correctly refuses it. A rewrite cannot repair that, because the target check runs against the candidate's stored targets rather than the replacement's. Recording the corrected record directly against `graph_indexer.py` and `graph_query.py` instead.
Evidence verified: true
Current target verified: true
Canonical overlap: none
## Summary

Decision (wave 1wpih): Record the single-class-file node-identity collapse as a finding rather than fixing it here.. Rationale: A file whose only top-level construct is one class gets no module node; the class takes the file's id, so `svc/session.py` is ambiguous between file and class. Correcting the identity scheme would change every single-class file in every consuming repository, which is far outside a measurement wave's scope..

## Evidence

- `1wpie-enh graph-quality-evaluation-and-evidence-isolation`
- `1wpih`

## Targets

- `svc/session.py`
