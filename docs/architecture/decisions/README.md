# Architecture Decision Records

Owner: Engineering
Status: active
Last verified: 2026-05-10

Architecture Decision Records (ADRs) capture significant design decisions made for Wavefoundry.

## Naming Convention

Files use the pattern `<id>-adr <slug>.md` — a lifecycle ID (same base-36 system as wave and change IDs), hyphen, `adr`, space, kebab-case slug. Example: `12dzj-adr embedding-model-and-format.md`. Generate a new ID with `.wavefoundry/bin/lifecycle-id` (or the `lifecycle_id.py` script).

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
