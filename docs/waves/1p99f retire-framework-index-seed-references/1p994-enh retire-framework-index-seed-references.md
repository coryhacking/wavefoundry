# Retire framework-index references in shipped seeds (single project index is the reality)

Change ID: `1p994-enh retire-framework-index-seed-references`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-01
Wave: `1p99f retire-framework-index-seed-references`

## Rationale

Wave `1p4ww` (ADR `1p4xx`) eliminated the separate framework index: there is now a **single project
semantic index** (`.wavefoundry/index/`, LanceDB `docs` + `code` tables) and a **single project
graph**; the framework graph layer and the `union` mode were removed; framework seeds + the top-level
`README` **fold into the project `docs` table** at setup/upgrade; and `build_pack.py` ships framework
**source only** (no framework index is built, compacted, shipped, asserted, or skippable — the
`--skip-framework-index` flag no longer exists). `.wavefoundry/framework/index/` is a deprecated
pre-`1p4ww` artifact the upgrade removes.

The self-hosted architecture/reference docs were reconciled to this reality (a separate docs-only
cleanup). But the **canonical seeds still ship the old narrative to every downstream consumer**, and
the rendered prompt surfaces (`docs/prompts/{package,upgrade,install}-wavefoundry.prompt.md`) inherit
it. This is a framework-source defect: a consumer's agent, reading these seeds, will believe a framework
index is built/shipped and will try to use a `layer="framework"` that no longer exists.

Seed edits are framework-source changes: they require the `seed_edit_allowed` gate. Admitted to wave
`1p99f` to ship in the 1.9.9 release alongside closed wave `1p93a`.

## Requirements

1. Correct every seed that presents a **framework index/layer** as a current built / stored / packaged
   / shipped / query-target thing, to the single-project-index reality (framework content is folded
   into the project `docs` index; `build_pack` ships source only; there is no `layer="framework"`).
2. **Seeds stay self-contained — no internal ADR/wave-ID references.** State the current reality plainly
   (e.g. "framework seeds are folded into the project docs index; there is no separate framework
   index"); do NOT add `wave 1p4ww` / `ADR 1p4xx` / `see decisions/…` pointers a downstream repo cannot
   resolve (per the shipped-seed convention).
3. **Preserve false positives.** Many seed occurrences of "Wave Framework **layer**" mean the *installed
   methodology* in a repo, not a semantic-index layer — leave those untouched. The `framework/index/`
   entry in the rendered `.gitignore`/`.aiignore` block (`seed-050`) is a deliberate defensive ignore of
   a possibly-leftover deprecated dir — leave it.
4. Reconcile the **rendered prompt surfaces** with the corrected seeds (regenerate via the surface
   render path if one produces them, otherwise mirror the seed change), so `docs/prompts/` no longer
   carries the drift.
5. No stale current-tense framework-index/`layer="framework"` claim remains in `.wavefoundry/framework/
   seeds/` or in `docs/prompts/`, verified by grep.
6. Framework tests and the docs gate stay green.

## Scope

**Problem statement:** shipped seeds (and the prompts rendered from them) still describe a framework
semantic/graph index that was removed in `1p4ww`, so downstream consumers get wrong guidance.

**In scope — the 6 seeds with real drift:**

- `011-install-wavefoundry-phase-1.prompt.md` — "Builds the framework semantic index at
  `.wavefoundry/framework/index/` (so `docs_search`/`seed_get` work after restart)" → builds the
  **project** index at `.wavefoundry/index/` (framework seeds fold into the project `docs` index).
- `040-docs-structure-bootstrap.prompt.md` — `build_pack.py` semantics "… then updates and compacts
  `framework/index/` before zipping" → drop the framework-index compaction; ships source only.
- `100-project-prompt-surface-bootstrap.prompt.md` — remove `--skip-framework-index` from the
  exceptional-use flag list (flag removed); keep `--skip-docs-gate` / `--skip-manifest-check`.
- `160-upgrade-wavefoundry.prompt.md` — two spots: the **Package Wavefoundry** blurb ("… then updates
  and compacts the packaged `framework/index/`") and the upgrade reindex note ("The framework index is
  shipped inside the pack … only reindex the framework layer when …") → single project index; source-only
  packaging. Keep the genuinely-current semantic-vs-graph reindex guidance.
- `009-framework-maintenance-contract.md` — "… `framework/index/` is updated and compacted before the
  zip is written" → drop; ships source only.
- `211-guru.prompt.md` — "Operators querying framework code use `layer="framework"` … the framework
  layer indexes its own seeds and architecture docs" → the framework layer was removed; framework seeds
  are folded into the project index (searchable via the normal project index); self-hosting repos opt
  framework subpaths into the project layer via `indexing.project_include_prefixes`.

**In scope — rendered surfaces to reconcile after the seed edits:**

- `docs/prompts/package-wavefoundry.prompt.md` (framework-index update/compact + `--skip-framework-index`)
- `docs/prompts/upgrade-wavefoundry.prompt.md` ("framework index shipped inside the pack" / framework
  rebuilds)
- `docs/prompts/install-wavefoundry.prompt.md` ("if the repository self-hosts the framework index …")

**Out of scope:**

- The self-hosted authored docs (`docs/architecture/*`, `docs/references/*`, `docs/contributing/*`,
  `docs/specs/*`) — already reconciled in the prior docs-only cleanup.
- "Wave Framework **layer**" = installed-methodology occurrences (`002`, `008`, `010`, `080`, `140`,
  `160` install-blurbs, `009` init-blurb) — correct, not touched.
- The `seed-050` rendered-`.gitignore` `framework/index/` ignore entry — kept (defensive).
- Historical wave records, journals, ADRs, `CHANGELOG`.
- Any code change — this is seed/doc content only (no behavior change; the code already dropped the
  framework index).

## Acceptance Criteria

- [x] AC-1: each of the 6 in-scope seeds no longer presents a framework index/layer as current; the
      wording matches the single-project-index / source-only reality. Evidence: edits to `011`, `040`,
      `100`, `160` (×2), `009`, `211-guru`.
- [x] AC-2: no seed edit adds an internal ADR/wave-ID reference; corrections are stated plainly and
      self-contained. Evidence: corrections use "framework seeds fold into the project docs index / no
      framework index" wording — no `1p4ww`/`1p4xx`/`decisions/` added (pre-existing `1p2q3`/`1316n`
      provenance parentheticals left untouched, out of scope).
- [x] AC-3: false positives preserved — the `seed-050` `.wavefoundry/framework/index/` gitignore entry
      and all "Wave Framework layer" methodology text (`140`/`080`/`160`/`009`/`010`/`002`) are unchanged.
      Evidence: grep confirms both present post-edit.
- [x] AC-4: the 3 rendered prompt surfaces are reconciled — `package-` (source-only zip + dropped
      `--skip-framework-index`), `upgrade-` (single project index), `install-` (removed the
      `layer="framework"` self-host block). Evidence: `docs/prompts/` grep clean.
- [x] AC-5: `grep` over `.wavefoundry/framework/seeds/ docs/prompts/` returns only corrected
      negation/fold statements + the intentional `seed-050` gitignore entry + pre-existing provenance
      refs. Evidence: grep gate output.
- [x] AC-6: `run_tests.py` passes (3,788 tests) and the docs gate (`wave_validate`) passes — no
      seed↔prompt or shipped-reference-doc guard tripped. Evidence: suite + docs-lint output.

## Tasks

- [x] Open `seed_edit_allowed`; edit the 6 seeds per In-Scope; close the gate immediately after. Done.
- [x] Reconcile the 3 rendered prompt surfaces (mirrored the seed change into `docs/prompts/`). Done.
- [x] Grep-verify seeds + `docs/prompts/` are clean (AC-5); confirm false positives preserved (AC-3). Done.
- [x] Run `run_tests.py` (3,788 OK) + `wave_validate` (ok) — no guard tripped. Done.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Seed edits (6 seeds) under `seed_edit_allowed`, then rendered-prompt reconciliation + grep/test verification. Single lane — the prompt reconciliation depends on the seed wording. |

## Serialization Points

- The rendered-prompt reconciliation must follow the seed edits (seeds are the source of truth). No
  overlap with the open wave `1p93a` (disjoint files: seeds/prompts vs `indexer.py`/`server.py`/
  `setup_index.py`).

## Affected Architecture Docs

N/A — the architecture/reference docs were already reconciled in the prior docs-only cleanup; this
change is confined to shipped seeds + the prompt surfaces rendered from them.

## AC Priority

| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The core fix — seeds must stop shipping the removed-framework-index narrative. |
| AC-2 | required   | Shipped-seed convention: no dangling internal ADR/wave refs downstream can't resolve. |
| AC-3 | required   | Avoid over-correction — methodology "layer" text and the defensive gitignore entry are correct. |
| AC-4 | required   | The rendered prompts consumers read must match the corrected seeds. |
| AC-5 | required   | Objective completeness check across seeds + prompts. |
| AC-6 | required   | No regression; catch any seed↔prompt / shipped-reference-doc guard. |

## Progress Log

| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-07-01 | Planned (not admitted). Found during the framework-index docs-drift sweep: 6 shipped seeds + 3 rendered prompts still describe the `1p4ww`-removed framework index/`layer="framework"`. Ground truth reverified in code (build_pack ships source only; framework/union graph layers removed; framework seeds fold into the project docs index). | seed grep (011/040/100/160/009/211); `build_pack.py` 1p4ww comments; `graph_query.py`/`graph_indexer.py` "single project graph — framework/union layers removed"; `test_build_pack.py` asserts no `/framework/index/` in the zip. |
| 2026-07-01 | Implemented. Admitted to wave `1p99f`; prepare-council PASS (rotating docs-contract-reviewer). Edited the 6 seeds under `seed_edit_allowed` (source-only build_pack wording; `011` project-index fold; `100`/`package-` dropped `--skip-framework-index`; `211-guru` removed `layer="framework"`) + reconciled the 3 rendered prompts. AC-1..6 met; false positives (`seed-050` gitignore entry, methodology "Wave Framework layer") preserved; no wave/ADR refs added. | 6 seed diffs + 3 prompt diffs; grep gate clean; 3,788 tests OK; docs-lint ok. |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-07-01 | Fix the seeds (source of truth) + re-render prompts, not the rendered prompts directly. | The prompts render from seeds; editing only the rendered file leaves the seed shipping the drift to consumers and would be overwritten on re-render. | Hand-edit the rendered prompts only (rejected — leaves the seed wrong for downstream). |
| 2026-07-01 | Seeds state the current reality with NO wave/ADR IDs. | Shipped-seed convention — downstream repos can't resolve internal `1p4ww`/`1p4xx`/`decisions/…` refs (prior 1.9.7 seed-ref bug). | Cite the ADR for provenance (rejected — dangling ref downstream). |
| 2026-07-01 | Own wave, not folded into `1p93a`. | Distinct concern (seed hygiene, `seed_edit_allowed`), and 1p93a is a precision/index-lifecycle wave; keeping it separate avoids an untested late-admitted docs change on that wave. Single-OPEN means implement after 1p93a closes (or the operator may choose to fold it). | Fold into 1p93a (available if the operator wants it in the same 1.9.9 pack). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Over-correcting a "Wave Framework layer" methodology mention. | AC-3: explicit false-positive list; diff review; the grep gate distinguishes `framework/index`/`layer=framework` from methodology "layer". |
| A seed↔prompt consistency guard or shipped-reference-doc test fails after editing seeds but before re-render. | AC-6 runs the suite; the render/reconcile step is a required task before verification. |
| Re-render path for `docs/prompts/` is unclear. | Task allows regenerate-or-mirror; the grep gate (AC-4/5) is the objective check regardless of mechanism. |
| Accidentally removing the defensive `framework/index/` gitignore entry. | AC-3 preserves `seed-050`; that entry is explicitly out of scope. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
