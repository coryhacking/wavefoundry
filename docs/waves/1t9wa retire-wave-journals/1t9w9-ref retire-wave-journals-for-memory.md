# Retire Wave Journals in Favor of the Memory System

Change ID: `1t9w9-ref retire-wave-journals-for-memory`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-22
Wave: `1t9wa retire-wave-journals`

## Rationale

Operator-agreed after a census: this repository has 121 journals and 100 of them are the untouched 52-line scaffold that `wf_create_wave` auto-generates — nothing has been written into a wave journal since the memory system landed. Every journal function now has a strictly better home: in-flight observations go to real-time Progress Log rows, decisions to the Decision Log, cross-session state to the session handoff, watchpoints to wave.md's own section, and durable lessons to memory candidates (`memory_add` mid-wave; `memory_propose` drafting from Decision Logs at close, with forced triage at validation). The journal's distill-and-promote pipeline was the v0 memory system; per-wave journals are dead weight now that v1 ships. Role journals are explicitly different (persona operating memory) and are folded into their proper homes rather than retired as a class.

## Requirements

1. **`wf_create_wave` stops scaffolding journals.** New waves create no journal file; the creation response no longer advertises a created journal (envelope fields adjusted or truthfully reporting no journal — decided against the tool-surface compat rules during implementation). Nothing in the lifecycle requires a journal to exist.
2. **Wave scaffold watchpoints survive, renamed:** the wave.md scaffold section becomes `## Watchpoints`; wave lint accepts the legacy `## Journal Watchpoints` heading on existing waves so history never breaks.
3. **Seeds and prompts stop teaching journaling:** every seed/prompt that instructs wave-journal creation, journaling cadence, or close-time distillation is updated to route those behaviors to the memory system (mid-wave `memory_add` candidates; close-time `memory_propose` + validation). The journal operating-memory contract (`docs/agents/journals/README.md`) retires.
4. **Upgrade path migrates target repositories mechanically (operator-directed):** a version-gated upgrade migration handles the deterministic cases in target repos — (a) deletes wave journals that provably match the pristine rendered scaffold (structure-matched against the template family with zero non-template content lines; zero information loss, counts reported in the upgrade summary), and (b) moves content-bearing wave journals into their corresponding wave folder when that wave directory exists (self-contained, mirroring this repository's treatment). Role journals and any journal the matcher cannot classify are left in place and listed in the upgrade report for the operator-invoked prompt in requirement 5. The migration is idempotent and interruption-safe.
5. **Distill journals becomes Migrate journals:** the prompt repurposes into the operator-invoked completion path for what the mechanical migration deliberately leaves behind — promoting still-valuable findings into memory candidates for validation and folding role-journal content into role docs. Judgment-requiring merges stay with an agent under operator direction, never inside the upgrade.
6. **This repository migrates fully (operator-approved):**
   - The ~100 untouched scaffold journals are deleted (they contain only the template; deletion approved by the operator in this design discussion).
   - Content-bearing wave journals (~a dozen, pre-memory era) move into their corresponding `docs/waves/<wave>/` folders; any still-current lessons are proposed as memory candidates and validated.
   - Role journals (`wave-coordinator`, `wave-coordinator-persona`, `implementer`, `guru`, `planner`, `framework-operator`) fold into their homes: identity/stance content merges into the corresponding `docs/agents/<role>.md`, durable role lessons become validated memory records; the files then retire.
   - `docs/agents/journals/` ends empty and is removed; links from live docs are updated (closed-wave archives keep their historical references untouched per the cleanup policy, with lint tolerating archive-internal references to the old paths if any exist).
7. **Docs lint and gardener remain clean** through the migration (link integrity on live surfaces; historical references preserved), and the semantic index is rebuilt so retired paths stop serving.

## Scope

**Problem statement:** every wave auto-creates a journal nobody writes to; the journal's purpose is fully covered by the memory system, and the artifact class costs scaffolding, indexing, and attention.

**In scope:**

- `wf_create_wave` journal scaffolding path (and the scaffold template it renders)
- Wave scaffold `## Watchpoints` rename + lint acceptance of the legacy heading
- Seeds/prompts teaching journal behavior; the distill prompt's repurposing; `docs/agents/journals/README.md`
- Upgrade migration for target repos (scaffold deletion by provable template match; wave-journal relocation; report of what was left for the prompt)
- This repository's migration (deletions, moves, role-journal folds, memory candidates, reindex)
- Tests for creation-path behavior, lint acceptance, and migration link integrity

**Out of scope:**

- Retiring wave.md watchpoints (they stay, renamed)
- The memory-naming convention (wave `1t9w8`, separate)

## Acceptance Criteria

- [x] AC-1: a newly created wave has no journal file and a truthful creation envelope; nothing downstream (prepare, implement, review, close, dashboard) requires one.
- [x] AC-2: new wave scaffolds carry `## Watchpoints`; lint passes on both new scaffolds and existing waves with the legacy heading.
- [x] AC-3: no shipped seed or prompt instructs wave-journal creation or distillation; the migration prompt exists and documents the opt-in flow.
- [x] AC-4: the upgrade migration, against a fixture target repo, deletes only provably-pristine scaffolds (a journal with one non-template line survives), relocates content-bearing wave journals into existing wave folders, leaves role/unclassifiable journals with a report, and is a no-op on re-run.
- [x] AC-5: this repository's `docs/agents/journals/` is gone — scaffolds deleted, content-bearing wave journals relocated into their wave folders, role journals folded into role docs with lessons as validated memory records; docs lint and link integrity clean; index rebuilt.
- [x] AC-6: full framework test suite passes.

## Tasks

- [x] Remove the creation-path scaffolding; adjust the envelope; rename the scaffold section with lint acceptance.
- [x] Update seeds/prompts; repurpose the distill prompt into Migrate journals; retire the journals README contract.
- [x] Run this repository's migration (delete/move/fold/propose-validate); rebuild the index.
- [x] Tests; full suite; docs gate.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| creation-path | implementer | — | create_wave + scaffold + lint |
| surfaces | implementer | — | Seeds, prompts, README retirement |
| migration | implementer | creation-path, surfaces | This repo only; destructive steps operator-approved |

## Serialization Points

- The local migration runs last, after lint accepts the post-journal world.

## Affected Architecture Docs

Surfaces documenting the journal contract and wave-record structure; no code-boundary change (the journal was a docs artifact scaffolded by the lifecycle, not a runtime dependency).

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The retirement itself. |
| AC-2 | required | History must never break on the heading rename. |
| AC-3 | required | Seeds ship to every target repo; stale journaling instructions would resurrect the artifact. |
| AC-4 | required | Operator directive: target repositories migrate mechanically where provably safe. |
| AC-5 | required | The operator-approved local migration, fully self-contained waves. |
| AC-6 | required | Standard gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-22 | Drafted from the operator-agreed design discussion. Census: 121 journals, 100 exactly at the 52-line untouched scaffold, ~a dozen content-bearing wave journals (pre-memory era), 6 role journals with real content. Operator rulings: retire wave journals in favor of memories; role journals are different and fold into role docs + memories; wave-specific artifacts belong inside the wave folder; scaffold deletion approved. The `-jrn` naming question from the 1t9w8 discussion is moot under retirement. | Journal census (line-count distribution); design discussion in session |
| 2026-07-22 | Operator directive: add the upgrade path — mechanical field migration (provable-scaffold deletion + wave-journal relocation) added as requirement 4 with AC-4; the prompt narrows to the judgment-requiring remainder; ACs renumbered. | Session design discussion |
| 2026-07-22 | Creation path retired: `wf_create_wave` scaffolds no journal, envelope fields removed, scaffold heading renamed `## Watchpoints` with legacy `## Journal Watchpoints` accepted via `WAVE_WATCHPOINT_HEADINGS`; lint's active-wave-journal-reference and persona `## Associated journal` requirements removed; journals removed from required-doc manifests. | `server_impl.py`, `wave_lint_lib/constants.py`, `wave_lint_lib/wave_validators.py`; `tests/test_server_tools.py` retirement tests |
| 2026-07-22 | Seeds/prompts sweep complete under `seed_edit_allowed`: seed 210 rewritten as the Migrate journals prompt, seeds 130/006 deleted, ~40 seeds and local prompts rerouted from journaling to typed memory candidates; AGENTS.md shortcut row updated (Migrate journals, legacy alias Distill journals). | `.wavefoundry/framework/seeds/210-migrate-journals.prompt.md`; seeds diff |
| 2026-07-22 | Upgrade migration `_migrate_journals` shipped (version-gated pre-1.15.0, pristine-template byte-match deletion, wave-journal relocation, rest left+reported). Running it live on this repo caught two hook bugs before any test existed: (1) relocation demanded all template fields so pre-template journals could not move (fixed: relocation needs only the wave identity); (2) role journals that merely REFERENCE a wave id were mis-relocated into that wave's directory (guru.md and three others; moved back by hand, fixed with the filename==wave-id check). Both are now pinned as regressions. | `upgrade_extensions.py`; `tests/test_upgrade_wavefoundry.py` `JournalMigrationTests` (8 tests OK) |
| 2026-07-22 | Local migration executed: 99 pristine scaffolds deleted, 16 content-bearing wave journals relocated into their wave directories, 6 role journals folded verbatim into their role/persona docs under an Operating Memory section, README deleted, `docs/agents/journals/` removed; all live references updated (docs/README, workflow-config journal_root, dashboard-adapter table, qa-reviewer, wave-council, prompt-surface manifest); zero live references remain. Durable role-journal lessons promoted as active memory records `1t7yx-mem lifecycle-epoch-is-fixed` and `1t78a-mem patch-the-impl-module-not-the-runner`; remaining distillation bullets were either historical status noise or already canonical in AGENTS.md. `wf_validate_docs` clean. | Migration run output; `wf_validate_docs` pass; memory records |
| 2026-07-22 | Full-suite run live-caught a fold side effect: the verbatim role-journal content carried pre-1.14.0 tool names (`wave_close`, `wave_current`, dashboard/index tool names) into live role docs, tripping the shipped `reconcile_scan` retired-surface guard (10 findings in implementer.md and wave-coordinator.md). Applied the canonical rename map to the folded sections; both scan test files green. | `tests/test_wf_cli.py` `NoLiveReferenceToRetiredWrapperTests`; `tests/test_reconcile_scan.py` |
| 2026-07-22 | Full suite green after the tool-name repair: 6,138 tests across 59 files OK in a single run. Docs index rebuilt (epoch generation 22, scope all, clean finish); retired `docs/agents/journals/` paths no longer serve — the relocated wave journals now surface from their wave folders flagged historical. AC-1 through AC-6 met. | Suite output; `index_build_status` epoch 22; `docs_search` verification |
| 2026-07-22 | Operator review found two stale public-surface issues the delivery council missed. P1: `wf_implement_wave` still returned the retired `journal_watchpoints` envelope key and said "Journal Watchpoints" in both docstrings while the wave claimed envelope fields were removed; repaired as a clean rename to `watchpoints` (no alias, matching the 1.14.0 no-aliases precedent), test now pins the new key and asserts the old key absent. P2: `project-overview.md` still taught journals as current lifecycle state ("journals live here"; close step "distill journals"); rewritten to memory-record language, and the sweep also fixed `docs/waves/README.md` presenting the legacy heading as the required form. Both recorded as typed ledger chains (cycle 1) with `wave-council-delivery` recheck. Miss classes for the record: the envelope key survived because the creation-path census stopped at `wf_create_wave`'s response, and teaching-language staleness has no mechanical guard, only reading. | `events.jsonl` findings `stale-journal-watchpoints-envelope-key`, `stale-journal-teaching-project-overview`; server_tools module run 1,410 OK |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-22 | Retire the per-wave journal class; keep watchpoints in wave.md. | Total functional overlap with the memory system, proven by 100/121 empty scaffolds; candidates force close-time triage where journal hunches rot unread. | Lazy/opt-in journal creation (keeps a redundant artifact class alive); keeping both (the census refutes the niche). |
| 2026-07-22 | Move content-bearing wave journals into their wave folders instead of deleting. | Operator: wave-specific artifacts should be self-contained in the wave folder; preserves pre-memory-era history where it belongs. | Deleting after distillation (loses narrative history); leaving them in a retired directory (orphaned). |
| 2026-07-22 | Fold role journals into role docs plus memory records. | Their content is two separable kinds — identity/stance (role-doc material) and durable lessons (memory material); no journal-shaped remainder. | Keeping a special-case surviving journal class (complexity without a niche). |
| 2026-07-22 | Upgrade migrates target repos mechanically where provably information-preserving; judgment-requiring merges stay operator-invoked (operator revision of the earlier opt-in-only ruling). | Deleting a byte-identical-to-template scaffold and relocating a file lose nothing, so the never-destructive principle is honored in substance while repos converge by default; role-journal folds need judgment and stay with the prompt. | Fully opt-in migration (convention drift persists by default; rejected by operator); auto-folding role journals in the upgrade (content merges without judgment). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Live links to moved/deleted journal paths break lint. | Migration updates live references and fails loudly on residue; closed archives are exempt historical record. |
| A seed or dashboard surface quietly assumes the journal exists. | Census of `journal` references across seeds, scripts, and dashboard during implementation; AC-1 exercises the full lifecycle without one. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
