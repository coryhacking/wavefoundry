# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-01

wave-id: `12as1 design-system-extraction`
Title: Design System Extraction

## Changes

Change ID: `12akr-enh design-system-directory-structure-extraction`
Change Status: `done`

Change ID: `12arn-enh design-system-pattern-and-surface-depth`
Change Status: `done`

Change ID: `12arn-enh design-system-bootstrap-and-governance`
Change Status: `done`

Completed At: 2026-05-01

## Wave Summary

Land a machine-readable design-system extraction contract under `docs/design/` across three sequenced changes: 12akr establishes the core tree, DTCG tokens, `manifest.json`/`gaps.md` schemas, install/upgrade backfill, `chunker.py` JSON-as-doc routing, rollback path, and the `design-language.md` coexistence rule; 12arn (pattern-and-surface-depth) extends with `patterns/{navigation,feedback,data,trust}`, deep `foundations/`, deep `accessibility/`, extended tokens, asset contract, and semantic validators; 12arn (bootstrap-and-governance) adds the no-design-system bootstrap path, multi-surface `targetSurfaces`/`platformStandards[]` with HIG reference versions, deprecation/lineage fields, and conditional product-class extensions (email/print/offline/notifications).

## Journal Watchpoints

- **Sequenced implementation required.** 12akr is a hard prerequisite for both 12arn changes — it owns the tree and `manifest.json` schema; Splits B and C extend without renaming. Implement 12akr → then 12arn-pattern-and-surface-depth and 12arn-bootstrap-and-governance (parallel-safe between themselves).
- **`seed-040` is the primary serialization point.** All three changes edit it. Only one in-flight change should modify `seed-040` at a time; coordinate edit windows.
- **`seed_edit_allowed` guard window.** All three changes edit seeds. Flip `.wavefoundry/guard-overrides.json` `seed_edit_allowed.enabled: true` before edits and restore after, per CLAUDE.md guardrail.
- **`framework_edit_allowed` guard window.** 12akr changes `chunker.py` and adds validators under `wave_lint_lib/`; Splits B and C add more validators. Flip `framework_edit_allowed.enabled: true` for those edits; restore after.
- **`design-language.md` is operator-owned.** Extraction never rewrites the body — only idempotent cross-link additions. Verify reviewers check this in docs-contract lane.
- **Reserved `spec.json` behavioral keys emitted as `null` in 12akr core seed.** Split B populates values only — never adds or removes keys. Validator in 12akr asserts presence; Split B validator asserts population where evidence exists.
- **`chunker.py` routing change affects non-design JSON.** 12akr tests must cover: token JSON → doc chunks; malformed JSON → fallback; non-design JSON → unchanged routing. Do not let Split B validator work land before the chunker test passes.
- **`manifest.json` schema compat.** `schemaVersion` lives in 12akr. Splits B/C must add fields (not rename or retype existing fields) so upgrade reconciliation stays merge-safe.

## Review Evidence

- **code-reviewer** — All three changes reviewed. Validator modules (`design_system_validators.py`, `design_system_surface_validators.py`, `design_system_governance_validators.py`) and CLI integration reviewed for branch completeness and re-entrant safety. Local `_load_json` helpers per module prevent circular imports. 39 surface-validator tests and 25 governance-validator tests pass. Backfill implementation reviewed: merge-safe path creation, no operator file overwrites, metadata-compliant stubs via `_md()` helper.
- **architecture-reviewer** — `docs/design/` extraction contract coexists with operator-owned `design-language.md`. Semantic index routing via `chunker.py` doc-branch confirmed for all JSON design files. `docs/architecture/design-system.md` hub doc added and cross-linked from `docs/ARCHITECTURE.md`.
- **docs-contract review** — `docs/design/` tree seeded with 96 stub files; all carry Wave Framework metadata headers. `docs/workflow-config.json` `design_review_triggers` extended. `design-language.md` coexistence rule applied (no body overwrites). `docs/design/index.md` created. `docs/repo-index.md`, `docs/README.md`, and `docs/ARCHITECTURE.md` updated.
- **seed review** — Five seeds updated: `seed-030` discovery globs for pattern/product-class signals; `seed-040` two-phase gap policy; `seed-050` Split B subtrees in AGENTS.md guidance; `seed-100` voice/tone extraction guidance; `seed-170` and `seed-190` `platforms/` delta reference added to Design Intent and design-language closure checkpoint.
- **product-owner: N/A** — Framework-only tooling; no product semantics moved.
- **security review: N/A** — No network, notification, or persistence surfaces introduced.
- **performance review: N/A** — No hot-path or scheduling changes.

## Dependencies

- No external wave dependencies.
- Internal ordering: 12akr must implement first. 12arn-pattern-and-surface-depth and 12arn-bootstrap-and-governance depend on 12akr; independent of each other.
