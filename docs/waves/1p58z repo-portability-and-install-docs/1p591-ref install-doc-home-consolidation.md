# Consolidate install assets under framework/install/ + discoverability index

Change ID: `1p591-ref install-doc-home-consolidation`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-13
Wave: `1p58z repo-portability-and-install-docs`

## Rationale

This repo is the wavefoundry framework SOURCE — the framework is developed in place here, not "installed" as a target. Install-related assets follow a **source → ship → provision** flow, but they were scattered across four framework subtrees (`framework/install/`, `framework/release/`, `framework/docs/references/`, `framework/seeds/`) with no index, so a working architecture *read* as scattered duplication and a contributor could not find "where install lives." The byte-identical ship invariant (each framework template ↔ its canonical `docs/references/` copy) was also only enforced by hand.

Prepare-phase finding (load-bearing): the framework↔project `*-format.md` pairs are an intentional shipped-template ↔ provisioned-canonical relationship (`1p4dc` / `1p455`), NOT accidental duplication — the canonical project copies must NOT be removed. But the framework-side *source* assets can be consolidated into one home as long as every consumer reference is updated in the same change. (Operator directed the physical consolidation after seeing that an index alone left the files scattered.)

## Requirements

1. Consolidate the framework-side install assets under one home, `.wavefoundry/framework/install/`: move `install-block.md` (from `framework/release/`) and the `install-log-format.md` shipped template (from `framework/docs/references/`) to join the two existing `*.template.md` files. (`scan-findings-format.md` is a secrets reference, not install — it moves up to `.wavefoundry/framework/docs/`, which removes the now one-file `references/` subfolder.)
2. Update EVERY consumer of the moved paths in the same change: `build_pack` (`RELEASE_NOTES_INSTALL_BLOCK_REL` + docstring), the provisioning seeds (`012`, `160`), `test_build_pack`, `README.md`, `docs/references/release-flow.md`.
3. Add one **install-asset index** (`docs/references/install-assets.md`) mapping every install asset → role → location → consumer; link it from `docs/contributing/build-and-verification.md`.
4. Guard the byte-identical ship invariant with a test (each shipped template `diff`-equal to its canonical copy).
5. Behavior-neutral: the canonical `docs/references/` copies are unchanged; install / release / setup / upgrade flows produce identical output.

## Scope

**Problem statement:** install assets were scattered across four framework subtrees with no index (reading as duplication); the byte-identical ship invariant was unguarded.

**In scope:**

- Consolidating the framework-side install assets under `.wavefoundry/framework/install/` (and `scan-findings-format.md` up to `.wavefoundry/framework/docs/`) and updating every consumer reference.
- The install-asset index + the `build-and-verification.md` pointer.
- The byte-identical parity test.

**Out of scope:**

- Removing or relocating the canonical `docs/references/` copies (they are the provisioned canonicals / self-host source).
- Changing install/release/provision behavior or rewriting prompt content.
- The path-portability change (that is `1p590`).

## Acceptance Criteria

- [x] AC-1: `docs/references/install-assets.md` is the single index — it lists every install asset with its role, location, and consumer (install-flow seeds, install-prompt surface, bootstrap entry point, install-log template + live state, install-log-format spec, scan-findings-format spec, release-notes install block).
- [x] AC-2: the index documents the framework↔project format-spec pairs as shipped-template↔provisioned-canonical (`1p4dc`/`1p455`), explicitly NOT duplication, and `docs/contributing/build-and-verification.md` points to the index. The byte-locked/shipped files intentionally carry no inline pointer (an inline edit would break the byte-identical invariant) — the index is the single map, documented as such.
- [x] AC-3: `.wavefoundry/framework/scripts/tests/test_shipped_reference_docs.py` asserts each shipped template is byte-identical to its `docs/references/` canonical copy via an explicit pair map (`install-log-format` → `framework/install/`, `scan-findings-format` → `framework/docs/`), plus a guard that every `docs/references/*-format.md` has a registered pair; fails on drift.
- [x] AC-4: framework-side install assets consolidated under `.wavefoundry/framework/install/` (`install-block.md`, `install-log-format.md` + the two templates); `scan-findings-format.md` moved up to `.wavefoundry/framework/docs/` (one-file `references/` subfolder removed). All consumers updated (build_pack, seeds 012/160, test_build_pack, README, release-flow); canonical `docs/references/` copies unchanged. `build_pack`/setup/upgrade tests stay green (suite 3156 OK).
- [x] AC-5: `wave_validate` → docs-lint ok; no broken links.

## Tasks

- [x] `git mv` `framework/release/install-block.md` and `framework/docs/references/install-log-format.md` into `framework/install/`; `git mv` `framework/docs/references/scan-findings-format.md` up to `framework/docs/` (removes the `references/` subfolder).
- [x] Update consumers: `build_pack` constant + docstring, seeds `012`/`160` provisioning sources, `test_build_pack`, `README.md`, `docs/references/release-flow.md`.
- [x] Author `docs/references/install-assets.md` (asset→role→location→consumer map) and link it from `build-and-verification.md`.
- [x] Add the byte-identical parity test; run the full suite + docs-lint + an old-path straggler grep.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| [workstream-1] | [role] | —            |       |
| [workstream-2] | [role] | workstream-1 |       |


## Serialization Points

- [Shared file or integration gate that requires coordination before parallel work proceeds]

## Affected Architecture Docs

N/A for core architecture docs (layering/data-flow/testing-architecture unaffected; no ADR needed). The change is a behavior-neutral relocation of framework source files plus the new `docs/references/install-assets.md` index (the authoritative map of install-asset locations) and a pointer from `docs/contributing/build-and-verification.md`.

## AC Priority

| AC   | Priority      | Rationale |
| ---- | ------------- | --------- |
| AC-1 | required      | The install-asset index is the deliverable — "a clear place to find them." |
| AC-2 | required      | Documenting shipped-template↔provisioned-canonical prevents a future agent "deduping" a load-bearing pair. |
| AC-3 | important     | A drift-guard test hardens the byte-identical invariant `1p4dc` only enforces by hand; high value, not the core deliverable. |
| AC-4 | required      | The consolidation is the operator-directed deliverable; updating every consumer in lockstep is the safety invariant (a missed reference breaks `build_pack`/provisioning). |
| AC-5 | required      | docs-lint + no broken links is the regression gate for a docs change. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-13 | Initial (documentation-only) pass: added `docs/references/install-assets.md`, `test_shipped_reference_docs.py`, and the `build-and-verification.md` pointer. No asset moved. | suite 3156 OK; docs-lint ok |
| 2026-06-13 | **Operator-directed re-scope → real consolidation.** Moved `install-block.md` (from `framework/release/`) and `install-log-format.md` (from `framework/docs/references/`) into `framework/install/`; moved `scan-findings-format.md` up to `framework/docs/` (removed the one-file `references/` subfolder). Updated build_pack constant+docstring, seeds 012/160, test_build_pack, README, release-flow; rewrote the parity test to explicit pairs + a `*-format` coverage guard; updated the index. Canonical `docs/references/` copies unchanged (parity preserved). | suite 3156 OK; docs-lint ok; old-path straggler grep clean (only closed-wave history remains) |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-13 | Physically consolidate framework-side install assets under `framework/install/` (not index-only). | Operator directed it after the index alone left files scattered across four subtrees. | Index-only (rejected by operator); leave as-is. |
| 2026-06-13 | Keep the canonical `docs/references/` copies; move only the framework *source/template* copies. | The canonical copies are the provisioned targets / self-host source and are referenced by `install_log_lib`/`server_impl`; removing them breaks provisioning. | Remove the duplicates (rejected — breaks the source→ship→provision invariant). |
| 2026-06-13 | Put `scan-findings-format.md` at `framework/docs/` (not `framework/install/`). | It is a secrets reference, not an install asset; moving it up removes the one-file `references/` subfolder per operator request. | Leave it in `framework/docs/references/` (rejected — single-file folder). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
|      |            |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
