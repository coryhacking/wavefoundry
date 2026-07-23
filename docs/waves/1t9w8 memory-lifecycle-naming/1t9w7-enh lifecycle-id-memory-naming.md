# Memory Records Use Lifecycle-ID Naming

Change ID: `1t9w7-enh lifecycle-id-memory-naming`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-07-22
Wave: `1t9w8 memory-lifecycle-naming`

## Rationale

Operator directive: memory records are the only lifecycle-adjacent artifact without lifecycle-ID naming — waves (`1t9ti memory-publication-receipt`), changes (`1t9tj-enh changelog-first-pack-builds`), and journals all carry the ID, memories are bare `mem-<slug>`. Lifecycle-ID naming gives filesystem-level chronology (old vs new visible at a glance; v2 IDs sort by day) and one consistent convention. The `mem-` prefix is pure convention today — two production mint sites and one test assertion; nothing parses or routes on it — and the filename stem IS the memory_id, so the resolution model does not change.

## Requirements

1. **Memory ID format v2:** new records mint `<lifecycleId>-mem <slug>` — space-separated, mirroring the change-ID structure (`<id>-<kind> <slug>`). The lifecycle prefix comes from `lifecycle_id.build_prefix(kind="mem", slug=<slug>)` with the repository's policy; the filename remains `<memory_id>.md`.
2. **No mint fallback:** every supported install is at 1.10+ and carries a lifecycle policy (operator confirmation), so minting is unconditional; an unresolvable policy raises exactly as it would for a wave or change mint, never silently producing a legacy `mem-` ID.
3. **Validation accepts both forms forever:** `validate_memory_id` (and `MEMORY_ID_RE`) accepts the new space-separated form AND the legacy `[a-z0-9][a-z0-9-]*` form — field repositories keep their existing `mem-*` records untouched and every tool (`memory_validate`, `memory_reconcile`, `superseded_by` links, advisories) continues to resolve them. The containment check (`_contained_record_path`) must remain escape-proof under the widened charset.
4. **Both mint sites converted:** the `memory_add` default-ID builder and the propose/backfill drafter mint the new form; collision handling (`-2`, `-3` suffixing) and the id-length cap adapt to the prefixed shape (suffix attaches to the slug, never corrupts the lifecycle prefix).
5. **This repository's existing records are renamed (operator-directed):** each `docs/agents/memory/mem-*.md` is renamed to `<backdatedId>-mem <slug>` where the lifecycle prefix is minted with `build_prefix(timestamp=<record created_at>, kind="mem", slug=<slug>)` — deterministic (v2 entropy is blake2s of kind+slug) and therefore idempotent, and backdating preserves true chronology in filesystem order. The `Memory ID:` line inside each record and all cross-references among LIVE surfaces (memory records' `superseded_by`/related links, active docs) update together; closed-wave archives and events ledgers keep the old IDs as historical record per the cleanup policy. The migration is a one-time in-wave operation for this repository, not shipped machinery.
6. **Docs and seeds updated:** every surface that documents the `mem-<slug>` convention (memory spec docs, memory-related seeds if any state the format) describes the new form, with the legacy form noted as valid-but-frozen.
7. **Semantic index refreshed** after the rename so advisories and search serve the new IDs.
8. **Upgrade path migrates target repositories the same way (operator-directed; scope narrowed by operator ruling on the bare-id finding):** a version-gated upgrade migration renames each existing GENERATED legacy record — always `mem-*` — in the target repo to the backdated new form using the identical deterministic minting, rewrites the internal `Memory ID:` line and live cross-references (memory-to-memory `superseded_by`/related links and live doc surfaces), and reports old-to-new mappings in the upgrade summary. Append-only stores keep historical IDs as history (exploration-credit rows, closed-wave events ledgers); rows where identity is load-bearing for future behavior (validation state keyed by memory_id, if any) are updated with the mapping — the implementation censuses store references before writing. The migration is idempotent (deterministic IDs) and safe to re-run on interrupted upgrades; validation continues to accept legacy IDs indefinitely for anything the migration cannot prove safe to touch.

## Scope

**Problem statement:** memory filenames carry no chronology and break the repository-wide lifecycle-ID naming convention.

**In scope:**

- `memory_records.py` (`MEMORY_ID_RE`, `validate_memory_id`, `_contained_record_path`, collision/cap logic)
- `server_impl.py` mint sites (memory_add default-ID builder; propose/backfill drafter)
- One-time rename of this repository's `docs/agents/memory/` records + live-reference updates + reindex
- Upgrade migration applying the same rename to target repositories (upgrade_wavefoundry/upgrade_extensions seam, version-gated, idempotent, mapping-reported)
- Tests (both-form validation, new-form minting, collision/cap, containment; the `startswith("mem-")` expectation)
- Docs/seeds describing the convention

**Out of scope:**

- Rewriting closed-wave archives or events ledgers (historical record, per cleanup policy)
- Prefix-based memory resolution ergonomics (exact IDs remain the contract; may be a later enhancement)

## Acceptance Criteria

- [x] AC-1: `memory_add` and the drafter mint `<lifecycleId>-mem <slug>` IDs that validate, resolve, collide-suffix, and advisory-match end to end; a missing lifecycle policy raises rather than minting a legacy ID.
- [x] AC-2: legacy `mem-*` IDs still validate and resolve through every consumer (validate, reconcile, supersede, advisories, search); the containment check rejects escape attempts in both forms.
- [x] AC-3: this repository's memory directory carries only new-form filenames, backdated from each record's `created_at`, with internal `Memory ID:` lines and live cross-references consistent; a second migration run is a no-op (deterministic backdated minting); closed archives untouched.
- [x] AC-4: the upgrade migration renames a fixture target repo's `mem-*` records to backdated new-form IDs idempotently (second run no-op), updates live references, reports the mapping, and leaves append-only history untouched; interrupted-run re-entry is safe; an explicit bare-id record is skipped whole (file, references, and store rows untouched) rather than half-migrated.
- [x] AC-5: docs/seeds state the new convention; docs lint passes; full framework test suite passes.

## Tasks

- [x] Widen the ID contract (regex, validate, containment) to the two-form union.
- [x] Convert both mint sites; adapt collision/cap logic.
- [x] Write and run the idempotent backdated rename for this repository; update live references; reindex.
- [x] Update docs/seeds; tests for all of the above; full suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| id-contract | implementer | — | memory_records + mint sites |
| migration | implementer | id-contract | One-time, idempotent, this repo only |
| docs | implementer | id-contract | Convention surfaces |

## Serialization Points

- Migration runs only after the widened contract lands (renamed files must validate).

## Affected Architecture Docs

Memory-layer spec surfaces that document the ID convention; no boundary or flow change (identity resolution model unchanged: filename stem = memory_id).

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The new convention. |
| AC-2 | required | Field stores keep legacy IDs forever. |
| AC-3 | required | The operator-directed rename with true chronology. |
| AC-4 | required | Operator directive: target repositories are migrated by upgrade, not left split-brain. |
| AC-5 | required | Standard gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-22 | Drafted from the operator's design discussion: space-separated form chosen for structural consistency with change IDs (operator overruled the hyphen variant); rename of this repository's records operator-directed; no mint fallback (operator: every install is 1.10+, policy universal). Verified: `mem-` prefix is convention only (two mint sites, one test assertion); `build_prefix` accepts explicit timestamps and v2 entropy is deterministic blake2s(kind, slug), making backdated migration idempotent. | code_keyword mint-site census; lifecycle_id.py API survey |
| 2026-07-22 | Operator directive: add the upgrade path so target repositories are renamed the same way — requirement 8, AC-4, and the revised field-migration decision added; the earlier out-of-scope line removed. | Session design discussion |
| 2026-07-22 | Implemented: two-form grammar in memory_records (MEMORY_ID_RE, Memory ID/Supersedes/Superseded-by line regexes), `mint_memory_id` (build_prefix under the repo policy, timestamp param for backdating), space-aware collision suffixing, `migrate_memory_ids_to_lifecycle_naming` (file rename + Memory ID line + backticked cross-refs + memory_backfill_sources rows), both server mint sites converted, version-gated upgrade hook in pre_docs_gate via a generalized `_fresh_installed_module` reload. Tests: grammar accept/reject, containment escapes in both forms, deterministic backdated mint with day ordering, collision shape, full migration fixture with store row + idempotence, upgrade-hook fixture with version-gate skip. Modules: memory_records 148 OK, upgrade 341 OK, memory_backfill 41 OK, docs_lint 828 OK, server_tools 1413 OK. | test_memory_records LifecycleMemoryIdTests; test_upgrade_wavefoundry pre_docs_gate migration test |
| 2026-07-22 | LIVE-CAUGHT census miss at the docs gate: the readiness claim that no lint surface carries a memory-id grammar was WRONG — `wave_lint_lib/constants.py` duplicates the Memory ID and Superseded-by line patterns, and the migrated repository failed docs-lint with 90 errors until the lint patterns were widened to the same two-form union (now sharing one `_MEMORY_ID_BODY` spelling with a mirror comment). The duplicated-vocabulary risk is exactly the docs-constants-lint class; recorded for a follow-up single-source candidate. | wf_validate_docs failure then clean; wave_lint_lib/constants.py |
| 2026-07-22 | Local migration executed through the shipped function: 66 records renamed with backdated chronological prefixes (1suok...1t7xx order), 1 skipped (README), second run no-op, one live journal reference updated, docs lint clean, docs index refresh dispatched. memory_backfill_sources had no rows here (no paused runs); the store-update path is covered by the fixture test. | migration output; wf_validate_docs; index_build(content=docs) |
| 2026-07-22 | AC-5 met: full framework suite 6,128/6,128 OK on the final tree; docs lint clean; live post-reload probe minted `1t7l9-mem memory-id-grammar-has-two-spellings-that-must-change-togethe` through the real memory_add path (the record captures the live-caught lint-grammar lesson), sorting after every backdated record as today's mint should. | run_tests.py output; live memory_add envelope |
| 2026-07-22 | Gapfill: implement-stage instrumented retrieval reads zero because post-activation work used harness surfaces — built-in Reads required as Edit preconditions and quick region views on files already located during the MCP-first design investigation (whose code_keyword/code_read calls attributed to plan via the general-bucket fold). The lapse was not free: the grammar-consumer census ran with a glob that excluded the wave_lint_lib subdirectory, which is precisely how the second grammar spelling was missed until the docs gate caught it. Corrective recorded in the review_finding memory: censuses route through code_keyword with repository-wide scope, not single-directory globs, regardless of instrument. | close dry-run advisory; 1t7l9-mem memory record |
| 2026-07-22 | TWO OPERATOR P1s repaired (typed chains in the ledger): (1) the migration was NOT interruption-safe as AC-4 claimed — renames completed before reference rewrites and every repair pass was driven by the in-run mapping, so the operator's live probes showed a rerun after a rename-only crash repairing nothing and a rerun after a write-before-unlink crash raising the self-created collision; (2) reference rewriting never left the memory directory, stranding live docs (operator's docs/live.md probe). Repair: every pass is now state-derived — same-internal-id targets are completed as crash residue (only a different internal id raises), stale mem-prefixed tokens are discovered by scanning and resolved by slug lookup against the migrated directory, the scope covers docs/** plus root markdown (closed/unclassifiable wave dirs skipped as history; only markdown touched, so ledgers are structurally out of reach), the store pass is likewise state-derived, and unresolvable stale tokens return as residual_references printed loudly by the upgrade hook. Both operator probes are now passing regression tests, plus a genuine-collision guard test and an archive/live-scope test; the local rerun on this repository was clean (0 repairs, no residuals). | test_rerun_repairs_references_after_rename_only_crash; test_rerun_completes_interrupted_rename_without_collision; test_migration_rewrites_live_docs_and_preserves_archives; test_genuine_collision_with_different_internal_id_still_raises; extended upgrade-hook test |
| 2026-07-22 | THIRD operator finding (bare-legacy-id-references-stranded), resolved by operator scope ruling: the migration renamed ANY legacy id but discovered references for `mem-*` only, so an explicit bare id like `custom-lesson` was renamed with its references and store row silently stranded. Ruling: generated legacy records are always `mem-*`; the migration scope is `mem-*` only, and explicit bare ids are frozen-valid, never auto-renamed. Repair: the rename pass now skips non-`mem-*` ids whole (no half-migration possible), requirement 8 and AC-4 state the scope, and a regression pins the frozen behavior (file, live doc reference, and store row all untouched with no residuals). A widened all-token discovery was started and reverted per the ruling — bare tokens are indistinguishable from prose and the case does not exist in supported generated data. | test_explicit_bare_id_records_are_frozen_not_half_migrated; requirement 8 / AC-4 wording |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-22 | Space-separated `<lifecycleId>-mem <slug>`, widening the ID regex to a two-form union. | Structural consistency with every other lifecycle artifact (operator directive); the ecosystem already handles space-bearing IDs (waves, changes). | Hyphen-only form (rejected by operator: inconsistent with the repo-wide convention); decoupling filename from memory_id (changes the resolution model for no benefit). |
| 2026-07-22 | Backdate migrated IDs from `created_at`. | Chronological filesystem order is the point; deterministic entropy makes it idempotent. | Minting at migration time (all records would sort at the migration date, defeating the purpose). |
| 2026-07-22 | Legacy IDs remain valid indefinitely; closed archives and append-only telemetry keep historical IDs. | Immutable history and safety margin for anything a migration cannot prove safe to touch. | Hard-invalidating legacy IDs after migration (breaks history and interrupted upgrades). |
| 2026-07-22 | Upgrade migrates target repositories with the same deterministic backdated rename (operator revision of the earlier local-only ruling). | Convention consistency across every project; deterministic minting makes the field migration idempotent and interruption-safe. | Local-only rename leaving field repos split-brain (rejected by operator); opt-in migration prompt (weaker: convention drift persists by default). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Widened charset weakens the path-containment check. | Explicit escape tests in both forms; the space joins two already-validated segments, never path separators. |
| Live references to renamed IDs missed. | Migration greps live surfaces for every old ID after renaming and fails loudly on residue outside closed archives; reindex follows. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
