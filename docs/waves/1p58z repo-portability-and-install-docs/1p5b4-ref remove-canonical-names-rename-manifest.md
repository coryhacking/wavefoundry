# Remove the canonical-names rename manifest (retire in 1.6)

Change ID: `1p5b4-ref remove-canonical-names-rename-manifest`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-13
Wave: `1p58z repo-portability-and-install-docs`

## Rationale

`.wavefoundry/framework/canonical-names.json` was the single source of truth for framework-shipped renames (role slugs + config keys), driving docs-lint alias resolution and the upgrade config-key convergence migrator. Its job is essentially done: the convergence migration in `upgrade_extensions` runs **unconditionally on every upgrade** (no version gate, idempotent), so every maintained project has had `wave_execution`/`wave_council_policy` rewritten to canonical, and active surfaces already use `wave-council`/`guru`/`wave_implement`/`wave_review`. Operator decision: retire the manifest mechanism in **1.6** (pulling the published `removed_in: 2.0.0` config-key contract forward), keeping only a **one-shot convergence** safety net in the upgrade for skip-version operators.

## Requirements

1. Remove the manifest and its loader: delete `.wavefoundry/framework/canonical-names.json` and `wave_lint_lib/canonical_names.py`.
2. **Keep the config-key convergence migration** in `upgrade_extensions` but make it self-contained — a hardcoded `{wave_execution → wave_implement, wave_council_policy → wave_review}` map (no manifest load), marked for removal at `2.0.0`.
3. docs-lint: drop the manifest-driven checks — `check_workflow_config_removed_keys`, the legacy-alias affordance in the required-keys check (require canonical keys only), and the retired-role-reference warning. `constants.WORKFLOW_REQUIRED_KEYS` requires canonical keys; `RETIRED_ROLE_NAMES` and its check are removed.
4. **Sub-decision A (role-name warnings):** removed entirely — role aliases were courtesy `removed_in: null` warnings; with the manifest gone, docs-lint no longer warns on legacy role slugs.
5. **Sub-decision B (`server_impl._read_wave_council_policy` runtime fallback):** removed — read `wave_review` only. The one-shot upgrade convergence rewrites legacy configs, so runtime always sees the canonical key.
6. Behavior gate: the full suite + docs-lint stay green; the upgrade convergence still rewrites a legacy `workflow-config.json` to canonical (its test is rewritten to the hardcoded map).

## Scope

**Problem statement:** the canonical-names rename manifest is retired; keeping its loader, docs-lint alias machinery, and the server runtime fallback is now dead weight on a closed deprecation window.

**In scope:**

- Delete the manifest + loader; rework `upgrade_extensions` to a hardcoded one-shot convergence; strip the manifest-driven docs-lint checks in `constants.py`/`core_validators.py`; remove the `server_impl` legacy fallback.
- Update/remove the affected tests (`test_canonical_names.py`, `test_docs_lint.py`, `test_upgrade_wavefoundry.py`, `test_server_tools.py`).
- An ADR recording the pulled-forward (2.0.0 → 1.6) removal.

**Out of scope:**

- The 1p590 / 1p591 work in this wave.
- Renaming anything new (this only retires the existing alias mechanism).

## Acceptance Criteria

- [x] AC-1: `.wavefoundry/framework/canonical-names.json` and `wave_lint_lib/canonical_names.py` deleted; `git grep` for a source import of `canonical_names` is clean.
- [x] AC-2: `upgrade_extensions` converges a legacy `workflow-config.json` via a self-contained hardcoded `_CONFIG_KEY_RENAMES` map (removed-at-2.0.0); `test_upgrade_wavefoundry` (188) passes without the manifest.
- [x] AC-3: docs-lint requires canonical keys only; `check_workflow_config_legacy_aliases`, `check_workflow_config_removed_keys`, and `check_deprecated_role_references` (+ `RETIRED_ROLE_NAMES`) removed from `constants.py`/`core_validators.py`/`cli.py`; `test_docs_lint` (217) green.
- [x] AC-4: `server_impl._read_wave_council_policy` reads `wave_review` only (fallback + one-shot stderr note removed); `test_server_tools` reader tests updated (1047 green).
- [x] AC-5: full suite **3088 OK** + `wave_validate` docs-lint ok; ADR `1p5be-adr retire-canonical-names-rename-manifest` and a CHANGELOG `[Unreleased]` entry record the accelerated removal.

## Tasks

- [x] Rework `upgrade_extensions` convergence to a hardcoded 2-key map (removed-at-2.0.0); delete `canonical_names.py` + the manifest.
- [x] Strip manifest-driven checks from `constants.py` (`WORKFLOW_REQUIRED_KEYS` canonical-only; remove `RETIRED_ROLE_NAMES`) and `core_validators.py` (remove role + removed-keys checks).
- [x] Remove the `server_impl` legacy `wave_council_policy` fallback.
- [x] Update/remove tests; write the ADR; add a CHANGELOG note; run full suite + docs-lint + an import-grep.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| [workstream-1] | [role] | —            |       |
| [workstream-2] | [role] | workstream-1 |       |


## Serialization Points

- [Shared file or integration gate that requires coordination before parallel work proceeds]

## Affected Architecture Docs

A new ADR under `docs/architecture/decisions/` records the decision to retire the canonical-names rename mechanism and **pull its removal forward from the published `2.0.0` to `1.6`**, keeping only a one-shot upgrade convergence. No layering/data-flow/testing-architecture doc changes; a CHANGELOG entry notes the accelerated removal.

## AC Priority

| AC   | Priority      | Rationale |
| ---- | ------------- | --------- |
| AC-1 | required      | Deleting the manifest + loader is the change. |
| AC-2 | required      | The one-shot convergence is the agreed safety net — losing it would strand skip-version operators on legacy keys. |
| AC-3 | required      | docs-lint must stay correct and green after removing the manifest-driven checks. |
| AC-4 | required      | The server runtime fallback is part of the mechanism being retired; leaving it is half a removal. |
| AC-5 | required      | Suite + docs-lint green and the ADR/CHANGELOG record the pulled-forward contract change. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-13 | Implemented (operator-directed, folded into 1p58z): deleted `canonical-names.json` + `canonical_names.py`; reworked `upgrade_extensions` convergence to a self-contained hardcoded map (removed-at-2.0.0); stripped 3 manifest-driven docs-lint checks from `constants.py`/`core_validators.py`/`cli.py`; removed the `server_impl` `wave_council_policy` reader-fallback; updated the base lint fixture + tests (deleted 3 test classes + legacy methods, added canonical-only coverage); wrote ADR `1p5be` + CHANGELOG `[Unreleased]`. | suite 3088 OK; docs-lint ok; `canonical_names` import-grep clean |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
|      |            |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
