# Canonical-names manifest as single source for framework renames

Change ID: `1p3j6-enh canonical-names-manifest`
Change Status: `implemented`
Owner: framework-maintainer
Status: implemented
Last verified: 2026-06-05
Wave: 1p3iv indexer-drift-skips-empty-files

## Rationale

Solaris-feedback meta-recommendation #3 from wave `1p3dk`: "One canonical declaration of every name." Today a role/key name lives in four places that can independently disagree — seed prose, consumer code, lint alias tables, hand-authored docs. The repo carries two hardcoded alias dicts in `constants.py` (`RETIRED_ROLE_NAMES`, `WORKFLOW_REQUIRED_KEYS`) that future renames must update by hand, in lockstep with seed-prose edits and docs-lint integrations. The result: when a rename ships, the framework currently allows both spellings indefinitely (no removal version), and "which name is canonical" is answered differently by each surface.

This change introduces `.wavefoundry/framework/canonical-names.json` as the single source of truth for framework renames, with a fail-safe loader that other surfaces can derive from. The convergence half of the config-key rename (candidate #4) depends on the `removed_in` field to bound the deprecation window — this change ships the field; #4 will populate values and add the convergence behavior.

## Requirements

1. `.wavefoundry/framework/canonical-names.json` exists with `schema_version: 1`, `role_renames` map, and `config_key_renames` map. Each rename entry is keyed by legacy name and carries `{canonical, removed_in}`. Initial content mirrors the existing `RETIRED_ROLE_NAMES` + `WORKFLOW_REQUIRED_KEYS` alias data (no new renames; just relocation).
2. `wave_lint_lib/canonical_names.py` provides a loader API: `load_manifest(repo_root)`, `role_alias_to_canonical(repo_root)`, `config_key_alias_to_canonical(repo_root)`, `canonical_to_aliases(alias_map)`, `role_removed_in(repo_root, alias)`, `config_key_removed_in(repo_root, alias)`, `framework_repo_root()`.
3. Loader fail-safes: missing manifest, malformed JSON, wrong `schema_version`, non-dict root all return an empty manifest. Malformed individual entries (missing `canonical`, non-string `canonical`, non-dict entries) are silently skipped. `docs-lint` stays operational under any of these conditions.
4. `constants.RETIRED_ROLE_NAMES` is derived from the manifest at module-load time; public name preserved for backward-compat with existing imports.
5. `constants.WORKFLOW_REQUIRED_KEYS` is derived from the manifest at module-load time; renamable canonical keys (`wave_implement`, `wave_review`) become alias tuples when manifest carries aliases for them; required keys without manifest entries stay as plain strings.
6. Tests cover: manifest path computation, fail-safe load on each malformed input class, alias-map extraction with skip-malformed behavior, `canonical_to_aliases` inversion + sort, `removed_in` lookups, and integration verifying the framework's own shipped manifest matches the public constants.
7. All existing framework tests continue to pass without modification — the public surface of `RETIRED_ROLE_NAMES` and `WORKFLOW_REQUIRED_KEYS` is unchanged.

## Scope

**Problem statement:** Framework renames have no single source of truth. Hardcoded alias dicts in `constants.py` must be updated in lockstep with seed-prose edits; future consumers (renderers, upgrade migrator) would need to either import the constants or maintain their own copies. The convergence half of any rename (bounded deprecation with a removal version) has no place to live.

**In scope:**

- Manifest file + schema (version 1).
- Loader module with full fail-safe semantics.
- `constants.py` derivation of `RETIRED_ROLE_NAMES` and `WORKFLOW_REQUIRED_KEYS` from the manifest.
- Test coverage for loader + integration.
- CHANGELOG bullet under `[1.5.0]` `### Changed`.

**Out of scope:**

- Populating `removed_in` values for any rename. This change ships the field; candidate #4 (convergence half) sets values.
- Migrating renderers or the upgrade migrator to consume the manifest. Those are downstream — this change ships the infrastructure; their migration can happen incrementally as each consumer needs it.
- A second-pass refactor of the existing `check_deprecated_role_references` / `check_workflow_config_legacy_aliases` validators. They read `RETIRED_ROLE_NAMES` and `WORKFLOW_REQUIRED_KEYS` (which are now manifest-derived) — no validator changes needed; the manifest is the upstream of those reads.

## Acceptance Criteria

- [x] AC-1: `.wavefoundry/framework/canonical-names.json` exists with `schema_version: 1` and `role_renames` + `config_key_renames` containing the current rename set (`council-moderator` → `wave-council`, `code-insight-agent` → `guru`, `wave_execution` → `wave_implement`, `wave_council_policy` → `wave_review`).
- [x] AC-2: `wave_lint_lib/canonical_names.py` exists with the loader API listed in Requirements #2.
- [x] AC-3: Loader fail-safes on missing/malformed/wrong-schema input (verified by unit tests).
- [x] AC-4: `constants.RETIRED_ROLE_NAMES` equals `canonical_names.role_alias_to_canonical(framework_repo_root())` at import time (verified by integration test).
- [x] AC-5: `constants.WORKFLOW_REQUIRED_KEYS` carries `("wave_review", "wave_council_policy")` and `("wave_implement", "wave_execution")` alias tuples plus the no-alias required keys (verified by integration test).
- [x] AC-6: Existing framework tests still pass (no behavior change in the public API surface of constants.py).
- [x] AC-7: New tests in `tests/test_canonical_names.py` cover the seven loader/integration scenarios.
- [x] AC-8: `docs-lint` returns clean.

## Tasks

- [x] Create `.wavefoundry/framework/canonical-names.json` with current renames.
- [x] Create `wave_lint_lib/canonical_names.py` loader module.
- [x] Refactor `constants.py`: derive `RETIRED_ROLE_NAMES` and `WORKFLOW_REQUIRED_KEYS` from the manifest.
- [x] Add `tests/test_canonical_names.py` with loader + integration tests.
- [x] Run framework tests. (2665 pass; +19 new canonical_names tests.)
- [x] Run docs-lint.
- [x] Add CHANGELOG bullet under `[1.5.0]` `### Changed`.

## Affected Architecture Docs

N/A — change is confined to `wave_lint_lib` internals and a new vendored data file. No domain map / layering / cross-cutting impact.

## AC Priority


| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required     | Manifest file is the artifact of the change. |
| AC-2 | required     | Loader is what makes the manifest consumable. |
| AC-3 | required     | Fail-safe behavior protects docs-lint operability under partial rollouts. |
| AC-4 | required     | Backward-compat with existing `RETIRED_ROLE_NAMES` callers. |
| AC-5 | required     | Backward-compat with existing `WORKFLOW_REQUIRED_KEYS` callers. |
| AC-6 | required     | No regression in existing suite. |
| AC-7 | required     | Loader behavior must be covered. |
| AC-8 | required     | docs-lint clean. |


## Progress Log


| Date       | Update                                                       | Evidence |
| ---------- | ------------------------------------------------------------ | -------- |
| 2026-06-05 | Change admitted into wave 1p3iv; manifest + loader + constants.py refactor + tests landed. | New `canonical-names.json` + `canonical_names.py`; constants.py edits; `tests/test_canonical_names.py` added. |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-05 | Manifest is canonical; constants.py derives from it at import time (preserving the public names `RETIRED_ROLE_NAMES` and `WORKFLOW_REQUIRED_KEYS`). | Backward-compat for existing callers (no need to change every import site). Manifest stays the single source — anything consuming the constants is transitively consuming the manifest. | (a) Replace the constants with `get_*()` functions; require all callers to migrate — rejected; large blast radius, no functional benefit for this change. (b) Maintain constants.py values alongside the manifest as a snapshot — rejected; reintroduces the dual-source-of-truth pattern this change exists to eliminate. |
| 2026-06-05 | Loader fail-safes to empty manifest on missing / malformed / wrong-schema / non-dict input. | A degraded `docs-lint` (no legacy-spelling warnings) is preferable to a crashed `docs-lint` if the manifest is missing or corrupted. Operator can fix the manifest without unblocking the entire lint surface first. | (a) Raise `FileNotFoundError` if manifest absent — rejected; turns a degraded state into a hard failure, breaking docs-lint and downstream consumers (wave MCP tools that auto-lint) for a file that's missing because someone deleted it manually. |
| 2026-06-05 | `removed_in` field present in schema v1 with all `null` values. Convergence behavior deferred to candidate #4. | Avoids a schema bump when #4 populates values. Schema v1 is forward-compatible with the deprecation-window mechanic. | (a) Omit the field; add it later in #4 — rejected; would require a schema bump and a migration step in the consumer pack. The field costs nothing structurally and lets #4 ship without touching the loader contract. |
| 2026-06-05 | Required-key list (`agent_memory`, `project_persona_generation`, etc.) stays in code, not the manifest. | The manifest is about renames specifically. Required-key-set membership is a different concern and shouldn't bloat the manifest schema. | (a) Move the required-key list into the manifest under `required_keys` — rejected; expands the manifest scope beyond renames and forces every consumer of the required-key set to load the manifest. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Loader behaves differently on first-time module load vs subsequent reload (Python module cache). | `constants.py` reads the manifest at module-load time; values are cached in module-level constants. Subsequent imports get the same values. Tests verify the canonical name happy path explicitly. |
| Future consumers (renderers, upgrade migrator) might import `RETIRED_ROLE_NAMES` directly and miss the migration to manifest-based lookups. | The public name is preserved; consumers don't need to know the data is manifest-backed. When a future consumer needs `removed_in` data (which isn't exposed by the constants), they migrate to the loader functions — explicit migration when needed. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
