# Architecture Decision Records

Owner: Engineering
Status: active
Last verified: 2026-05-03

Architecture Decision Records (ADRs) capture significant design decisions made for Wavefoundry.

## Naming Convention

Files use the pattern `DEC-NNN-<slug>.md` with zero-padded three-digit numbers and kebab-case slugs, e.g. `DEC-001-framework-location.md`.

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
| [DEC-001](DEC-001-embedding-model-and-format.md) | Embedding Model: BAAI/bge-base-en-v1.5 via fastembed ONNX INT8 | accepted |
