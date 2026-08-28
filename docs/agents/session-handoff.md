# Session Handoff

Owner: Engineering
Status: idle
Last verified: 2026-08-27

## Current State

No wave is in progress. Wave `1wik9 fenced-diagram-and-spec-retrieval` CLOSED
2026-08-27 (operator-signoff recorded; all lane and council approvals current;
four delivery findings repaired and independently reverified). Delivered at
CHUNKER_VERSION 37 (WALKER 13 unchanged): `1whup` docs-embedded fences route
to the docs table as `doc-code`, `1whuq` standalone Mermaid/PlantUML/DOT
chunkers, `1wfso` AsyncAPI / GraphQL SDL / Protobuf spec family (all three
DEFAULT-ON on recorded measurements). The working tree is UNCOMMITTED and
also carries the earlier CLOSED waves `1wfsl structured-docs-retrieval` and
`1tmtx test-suite-performance`; CHANGELOG `[Unreleased]` holds all three
wave families' entries. The commit is operator-owned.

## Follow-Ups

- Add the seed-211 / `docs/agents/guru.md` pair to a byte-parity test (the
  shipped 16-test reference-doc module guards other template pairs only;
  parity currently verified by direct byte-diff — DOCS-DEL-1 disposition).
- Notebook code cells keep their preserved pre-existing state (kind="code",
  reaching neither table) — recorded dispositioned follow-up in `1whup`.
- `.drawio` generated-set membership remains a recorded open question
  (`1whuq`); duplicate-titled PROSE section ids remain a pre-existing known
  bound (out of scope per `1whup` Requirement 2).
- MCP hosts must reconnect after upgrade to see the `docs_search` kind
  Literal change (`doc-code`), per the standing hot-reload constraint.
- Consumer indexes converge automatically on the next index build after
  upgrade (CHUNKER 37 forces a re-chunk with embedding reuse by content hash).
