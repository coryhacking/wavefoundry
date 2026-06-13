# Architecture Decision Records

Owner: Engineering
Status: active
Last verified: 2026-06-13

Architecture Decision Records (ADRs) capture significant design decisions made for Wavefoundry.

## Naming Convention

Files use the pattern `<id>-adr <slug>.md` — a lifecycle ID (same base-36 system as wave and change IDs), hyphen, `adr`, space, kebab-case slug. Example: `12dzj-adr embedding-model-and-format.md`. Generate a new ID with the MCP `wave_new_change` tool (preferred — it dedupes against existing IDs, including ADR stems); CLI fallback when MCP is unavailable: `.wavefoundry/bin/lifecycle-id` (or the `lifecycle_id.py` script).

## When to Create an ADR

Create an ADR when a decision:
- Affects module boundaries, integration contracts, or data flow
- Chooses between meaningfully different approaches with tradeoffs
- Introduces a constraint that future implementers must respect
- Changes how the framework interacts with target repositories

## Template

Copy `template.md` and fill in all sections. Link new ADRs from `docs/ARCHITECTURE.md`.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [12dzj-adr](12dzj-adr%20embedding-model-and-format.md) | Embedding Model: BAAI/bge-base-en-v1.5 via fastembed ONNX INT8 | accepted |
| [12tm5-adr](12tm5-adr%20semver-versioning-contract.md) | Semver Versioning Contract | accepted |
| [12tm5-adr](12tm5-adr%20python-tool-environment.md) | Python Tool Environment | accepted |
| [1p4xx-adr](1p4xx-adr%20fold-framework-index-into-project-docs.md) | Fold the framework index into the project docs index | accepted |
| [1p50s-adr](1p50s-adr%20docs-code-embedding-model-split.md) | Docs/code embedding-model split (arctic-embed-xs for docs) | accepted |
