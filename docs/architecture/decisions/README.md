# Architecture Decision Records

Owner: Engineering
Status: active
Last verified: 2026-07-20

Architecture Decision Records (ADRs) capture significant design decisions made for Wavefoundry.

## Naming Convention

Files use the pattern `<id>-adr <slug>.md` — a lifecycle ID (same base-36 system as wave and change IDs), hyphen, `adr`, space, kebab-case slug. Example: `12dzj-adr embedding-model-and-format.md`. Generate a new ID with the MCP `wf_new_change` tool (preferred — it dedupes against existing IDs, including ADR stems); CLI fallback when MCP is unavailable: `wf lifecycle-id` (or the `lifecycle_id.py` script).

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
| [1p5be-adr](1p5be-adr%20retire-canonical-names-rename-manifest.md) | Retire the canonical-names rename manifest (removal pulled forward to 1.6) | accepted |
| [1p6q5-adr](1p6q5-adr%20dashboard-navigation-shell.md) | Dashboard navigation shell (collapsible sidebar + section registry) | accepted |
| [1p8t4-adr](1p8t4-adr%20stage-gate-canonical-structure.md) | Keep the stage gate canonically structured; add an anti-drift guard; decline consolidation and anchors | accepted |
| [1p92d-adr](1p92d-adr%20embedding-precision-policy.md) | FP16 end-to-end on GPU machines, INT8 end-to-end on CPU-bound machines (embed + rerank); queries on CPU; precision folded into model_versions | accepted |
| [1p9qj-adr](1p9qj-adr%20lifecycle-id-v2-daily-entropy-scheme.md) | Lifecycle-ID scheme v2: daily time index + 12-bit deterministic entropy, provisioning-time epoch/offset, graceful 6-char overflow | accepted |
