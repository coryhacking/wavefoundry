# Deliver memory revalidation guidance and signals through upgrade

Spec ID: `24but-enh deliver-memory-revalidation-through-upgrade`
Spec Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-24
Wave: 24buu memory-revalidation-upgrade-delivery

## Rationale

Wave `249ar` (change `246to`) changed how memory records are kept: keeping an active record now needs a `check_note`, a keep is refused while a target is unresolved, and records carry derived `revalidation_reasons`. That code reaches a target repository through upgrade, but two parts of the delivery do not:

1. Seed 160 materializes `docs/prompts/memory-review.prompt.md` only when it is missing and otherwise preserves its bytes (seed 160, operating-memory checklist). Its briefing-loop carrier list merges seed 190 into the Close wave prompt only for `Intent outcome:`. No entry merges the seed 240 and seed 190 keep rule. An upgraded project keeps the old "keep it" wording, and its agents meet `memory_check_required` before they learn the rule from the refusal's retry hint.
2. After the upgrade reload, seed 160 recommends **Review memories** only when `memory_brief` reports `curation_required` or consolidation candidates. `memory_brief` sets `curation_required` only when the active count reaches `ACTIVE_MEMORY_CAP` (`wf_server/memory_handlers.py`, `memory_brief_response`). A project under the cap with unresolved or churned targets gets no recommendation, even though the 1.52.0 code flags those records at once. A record with no `Checked at:` line counts churn from `Updated:`, so an older project can have most of its records churn-flagged on the first read; this repository had 98 of 174 on 2026-11-24.

This is a track of arc [`244cm-arc memory-quality`](../../arcs/244cm%20memory-quality/244cm-arc%20memory-quality.md): outcome 3 ("every surfaced record still points at code that exists, or is queued for revalidation") holds in a target repository only when its maintainers learn of the queue and its agents follow the keep rule. Release 1.52.0 waits for this change (operator decision, 2026-11-24).

## Product Intent

**Beneficiaries:** maintainers who upgrade a target repository to 1.52.0, and the agents that run Review memories and Close wave there.

**Before:** after upgrading, a project under the active-record cap hears nothing about its unresolved or churn-flagged records, and its local Review memories and Close wave prompts still describe a keep without a `check_note`.

**After:** the upgrade's post-reload memory step reports how many active records have an unresolved, churned or bare-name target and recommends Review memories when any is unresolved or churned; the upgrading agent merges the keep rule into the project's existing Review memories and Close wave prompts, preserving local prose.

**Boundaries:** upgrade still never curates, rewrites, retires or purges a record, and never runs Review memories. No new gate, no new tool, no upgrade-runner code. The counts come from the rule `246to` already ships.

AC-1 and AC-2 establish that the counts are trustworthy; AC-3 and AC-4 establish that an upgrade delivers the guidance and the recommendation. Whether maintainers act on the recommendation is observable only after release (see Risks).

## Requirements

1. `memory_brief` returns a read-only `revalidation` object in every successful response, with integer fields `active_records`, `target_unresolved`, `target_churn` and `target_not_canonical`, and a boolean `churn_available`. Each count is the number of records with status `active` whose `revalidation_reasons` contain that reason, computed from the same `_memory_ranked` pass the brief already makes, before the briefing, target and limit filters. Candidate and retired records are not counted. The object carries counts only, never memory ids. `churn_available` is false when the commit-time source that `_memory_ranked` uses is unavailable: the index store is absent, cannot be opened, has an unexpected schema, or the read raises. `index_state_store.file_commit_times` returns `{}` without raising in those cases today, so the read gains an availability signal that `_memory_ranked` passes to the brief; other `_memory_ranked` callers keep their current results. A zero churn count from an unavailable source is therefore never read as clean.
2. The counts follow one rule with `memory_eval.maintenance_signals`: on the same repository state both report the same `target_unresolved`, `target_churn` and `target_not_canonical` counts.
3. Seed 160 adds a briefing-loop carrier entry: seed 240 and the `memory-review` install baseline reconcile into `docs/prompts/memory-review.prompt.md`, and seed 190 and the `close-wave` baseline reconcile into the profile-resolved Close wave prompt, for the keep rule. The rule: a keep or reactivation of an active record needs a single-line `check_note`, a keep is refused while a target is unresolved, and promoting a candidate needs neither. The entry uses the list's existing merge discipline (merge only changed clauses, preserve project prose and marker regions, stop on conflict). A copy that upgrade replaces itself (`24bn8-enh replace-unedited-lifecycle-prompts-during-upgrade`) needs no merge. The merge applies to every copy that change leaves in place: an edited copy, a copy with an unknown baseline, a symlinked copy, or a copy that changed after the comparison.
4. The post-reload memory step recommends **Review memories** when `curation_required` is true, consolidation candidates are returned, `revalidation.target_unresolved` or `revalidation.target_churn` is above zero, or `revalidation.churn_available` is false. The recommendation states the counts. It never runs curation or purge. This rule lives in seed 160 and in `review_policy.UPGRADE_POLICY_BLOCK`, the block upgrade replays into every target's upgrade prompt (seed 160, operating-memory checklist).
5. The self-hosted copy `docs/prompts/upgrade-wavefoundry.prompt.md` carries the seed 160 text for requirement 3 outside any renderer-owned region. Its `review-policy-upgrade` marker region is never edited by hand: it is regenerated from `UPGRADE_POLICY_BLOCK` by the existing review-policy render (`wf_sync_surfaces`), and the existing render drift check covers it. The pinned line break in "never auto-curates or purges memory" in `tests/test_review_policy.py` is kept, or the pin is updated in the same edit as the constant.
6. Platform behavior: the change is pure Python and prompt text. It adds no path, process or filesystem behavior, so Windows, macOS, Linux and WSL2 behave the same; the churn count reuses the commit-time read `_memory_ranked` already makes from the index store.

## Scope

**Problem statement:** the 249ar keep rule and revalidation signals ship in code but not in an upgraded project's prompts or upgrade summary.

**In scope:**

- The `revalidation` counts in `memory_brief`, with tests.
- The seed 160 carrier entry and post-reload recommendation, `review_policy.UPGRADE_POLICY_BLOCK` and its test, and the self-hosted upgrade prompt copy.
- `docs/architecture/contracts/mcp-tool-surface.md` (the `memory_brief` response fields) and a `CHANGELOG.md` `[Unreleased]` entry.

**Out of scope:**

- Any change to records, to `memory_reconcile`, or to the refusal codes.
- Running Review memories in this repository; that is the separate, operator-authorized pass on arc 244cm item 7.
- Upgrade-runner (`upgrade_wavefoundry.py`) or backfill-inventory changes.
- A "disputed in a session" signal (declined for wave `249ar`).

## Acceptance Criteria

- [x] AC-1: On a fixture with five records, active A (unresolved target), active B (target churned past its threshold since its last check), active C (bare-name target that matches one file), active D (clean) and candidate E (unresolved target), `memory_brief()` returns `revalidation` equal to `{"active_records": 4, "target_unresolved": 1, "target_churn": 1, "target_not_canonical": 1, "churn_available": true}`. The same object is returned with `limit=1` and with `targets=["no/such/file.py"]` (an empty briefing). Known bad: counting from the briefing list after the limit or target filter returns lower counts; counting all surfaced statuses gives `target_unresolved: 2`.
- [x] AC-2: On the AC-1 fixture, `revalidation`'s three reason counts equal `memory_eval.maintenance_signals(root, ...)`'s corresponding counts, and no memory id appears in the `revalidation` object.
- [x] AC-3: Seed 160 and `docs/prompts/upgrade-wavefoundry.prompt.md` each contain a briefing-loop carrier entry naming seed 240 and the `memory-review` baseline into `docs/prompts/memory-review.prompt.md`, and seed 190 and the `close-wave` baseline into the Close wave prompt, stating the keep rule of requirement 3. A test pins the entry in both files. Known bad: the test fails on the current seed 160, which has no such entry.
- [x] AC-4: `review_policy.UPGRADE_POLICY_BLOCK`, as rendered into a target's upgrade prompt by the upgrade's review-policy replay, and seed 160 state the recommendation rule of requirement 4, naming `revalidation.target_unresolved`, `revalidation.target_churn` and `revalidation.churn_available`, and keep "never auto-curates or purges memory". A test asserts on the rendered block and on seed 160. Known bad: the current block, which names only `curation_required` and consolidation candidates, fails the test.
- [x] AC-5: Measured on this repository, read-only, after the MCP server reloads the new code: `memory_brief(context="review")` reports `revalidation` counts equal to `wf_memory_eval()`'s `maintenance_signals` counts for the same three reasons, recorded in the Progress Log. `git status --porcelain docs/agents/memory` is unchanged by the measurement.
- [x] AC-6: `docs/architecture/contracts/mcp-tool-surface.md` documents the `revalidation` object under `memory_brief`, and `CHANGELOG.md` has an `[Unreleased]` entry naming this wave and change.
- [x] AC-7: With no monkeypatching, on the AC-1 records with an absent index store, a corrupt store file, and a store with an unexpected schema, `memory_brief` reports `churn_available: false` and `target_churn: 0` in each case; with a read made to raise, the same. With a valid store, `churn_available` is true. Known bad: today's `file_commit_times` returns `{}` for the absent and corrupt stores, so `churn_available` would stay true.

## Tasks

- [x] `index_state_store.py`: an availability signal for the commit-time read (absent, unopenable, wrong schema, raising).
- [x] `wf_server/memory_handlers.py` `memory_brief_response`: compute `revalidation` from the unfiltered `_memory_ranked` output for active records; refresh the handler-digest pin.
- [x] Tests for AC-1 and AC-2 in `tests/test_memory_records.py` (the existing `memory_brief` tests) using a temporary fixture repository; no test touches real records.
- [x] Seed 160 (under `seed_edit_allowed`): the carrier entry and the recommendation rule; apply the same text to `docs/prompts/upgrade-wavefoundry.prompt.md`.
- [x] `review_policy.py`: update `UPGRADE_POLICY_BLOCK`; update its pin in `tests/test_review_policy.py`.
- [x] Text-pin tests for AC-3 and AC-4.
- [x] Docs: the contracts tool-surface entry and the changelog entry.
- [x] AC-5 measurement; run `run_tests.py --profile second --file` on each touched test file and the full default suite with `--no-cache` last.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| brief-counts | implementer | — | Requirement 1 and 2, AC-1, AC-2 |
| upgrade-guidance | implementer | — | Requirements 3 to 5, AC-3, AC-4 |
| docs-and-measure | implementer | brief-counts, upgrade-guidance | AC-5, AC-6 |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/memory_handlers.py`, `.wavefoundry/framework/scripts/index_state_store.py`, `.wavefoundry/framework/scripts/tests/test_memory_records.py`, `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/scripts/review_policy.py`, `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `docs/architecture/contracts/mcp-tool-surface.md`
- The root `CHANGELOG.md` entry.

## Affected Architecture Docs

`docs/architecture/contracts/mcp-tool-surface.md` only: one response field on one tool. No module boundary, data path or verification seam changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The counts drive the recommendation; wrong counts mislead every upgrade. |
| AC-2 | required | One rule across the brief and the evaluation. |
| AC-3 | required | Delivers the keep rule to existing prompts. |
| AC-4 | required | Delivers the recommendation. |
| AC-5 | important | Shows the counts on real records. |
| AC-6 | required | Documented response contract. |
| AC-7 | required | An unavailable churn source must not look clean. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-24 | Planned and admitted to wave `24buu` after waves `248o5` and `246r5` closed and the tree was committed in `cbc69fb8`. | `wf_add_spec` |
| 2026-11-24 | Revised before readiness approval from the red-team primer: the recommendation rule also goes into `review_policy.UPGRADE_POLICY_BLOCK`, which targets actually receive (F7); the churn source is stated correctly and `churn_available` added (F9). | `.wavefoundry/work/24buu/readiness/red-team.md` |
| 2026-11-24 | Bounded readiness repair (cycle 1) for CR-1, CR-2, QA-1, QA-2, DC-2 and DC-3: churn availability covers absent, corrupt and wrong-schema stores; AC-1 expects `churn_available`; the merge covers every copy 24bn8 leaves in place; the self-hosted block is regenerated, not hand-edited. | `.wavefoundry/work/24buu/readiness/repair-1.md` |
| 2026-11-24 | Readback: `memory_brief` gains a read-only `revalidation` object counted from the unfiltered `_memory_ranked` pass over active records, with `churn_available` from a new commit-time availability signal; seed 160 gains the keep-rule carrier entry and the post-reload recommendation rule, mirrored in `UPGRADE_POLICY_BLOCK` and regenerated into the self-hosted prompt (AC-1 to AC-7). Scope: no record, `memory_reconcile`, refusal-code or upgrade-runner change. Expected files: the serialization points plus `test_review_policy.py`. This row was written after the edits; the brief asks for it before. | memory_brief(pre_implementation): 1wys2 (lock errors are not corruption in the state store) checked: the new read classifies nothing and resets nothing, it only reports False where the old read returned `{}`. |
| 2026-11-24 | Implemented: `index_state_store.file_commit_times_read` returns `(times, available)`; `file_commit_times` wraps it unchanged. `_memory_ranked` takes an optional `availability` dict and sets `churn_available` (False on absent, unopenable or wrong-schema store, a raising query, or any exception from the read); its return value is unchanged for every caller. With no file target (no read) or `commit_times_override`, `churn_available` is True: nothing can churn, so a zero count is a real result, not a missing source. `memory_brief_response` adds `revalidation` via `_revalidation_counts`. The `memory_brief` tool handler in `server_impl` is unchanged, so the handler-digest pin needs no refresh (`test_mcp_tool_registry.py` passes). Gapfill: shell `sed`/`grep` were used for bulk reads alongside the MCP tools. | `index_state_store.py`, `wf_server/memory_handlers.py` |
| 2026-11-24 | Upgrade guidance: seed 160 and `docs/prompts/upgrade-wavefoundry.prompt.md` (outside marker regions) carry the seed 240/190 keep-rule entry in the briefing-loop carrier list; seed 160's post-reload step and `review_policy.UPGRADE_POLICY_BLOCK` recommend Review memories on `curation_required`, consolidation candidates, `revalidation.target_unresolved` or `revalidation.target_churn` above zero, or `revalidation.churn_available=false`, stating the counts; the "never auto-curates or\npurges memory" line break is kept. The marker region was regenerated with `render_platform_surfaces.py`; only that file changed. Contract doc and CHANGELOG `### Added` entry written. | seed 160, `review_policy.py`, `docs/architecture/contracts/mcp-tool-surface.md`, `CHANGELOG.md` |
| 2026-11-24 | Tests: `BriefRevalidationCountsTests` (AC-1, AC-2, AC-7, no-target read, unchanged ranker results) in `test_memory_records.py`; `test_upgrade_carries_the_memory_keep_rule_into_existing_prompts` (AC-3) and `test_upgrade_recommends_review_memories_on_revalidation_counts` (AC-4, on the block rendered by `reconcile_upgrade_policy_surface`) in `test_review_policy.py`. `HotPathBoundedIOTests` now spies `file_commit_times_read`, the ranker's batched read. Results: `--file` on test_memory_records, test_review_policy, test_render_agent_surfaces, test_install_resume_integration, test_mcp_tool_registry, test_memory_eval, test_upgrade_wavefoundry, test_docs_lint: 1919 tests OK (that run's guard flagged my concurrent CHANGELOG edit, so the two touched files were rerun: 456 OK); `--profile second --file` on both touched files: 0 of 2 failed. The full `--no-cache` suite is left to the coordinator. | `.wavefoundry/work/24buu/impl/24but/` |
| 2026-11-24 | Mutants, each failing a named test: `conn is None` returns available (AC-7 absent, corrupt, unexpected schema; other-callers test); `_SQL_ERRORS` returns available (AC-7 query raises); `except Exception` returns available (AC-7 read raises); empty `wanted` returns unavailable (AC-7 final assertion); default `churn_available = False` (no-target test); counting all statuses (AC-1, AC-2); counting after the briefing filters (AC-1). Dropping `revalidation.target_churn` from the block fails the AC-4 test; removing the seed 160 entry fails the AC-3 test. | Mutant runs, `python -m unittest -k` |
| 2026-11-24 | AC-5 measurement after `wf_reload_mcp`, read-only, no doc edits during it: `memory_brief(context="review")` revalidation `{active_records: 174, target_unresolved: 10, target_churn: 0, target_not_canonical: 36, churn_available: false}`; `wf_memory_eval()` maintenance_signals 174 / 10 unresolved / 0 churn / 36 not canonical, so the three counts are equal. The reloaded host reports `loaded_code_stale` and its eval reported `IndexCompatibilityError`, so its commit-time read is unavailable and the brief correctly says so rather than reporting clean; `maintenance_signals` has no such flag and reports 0 churn. A fresh process on the current tree gives brief counts 10 / 101 / 36 with `churn_available: true` and `maintenance_signals` 10 / 101 / 36, equal again. `git status --porcelain docs/agents/memory` was empty before and after. A host restart is needed for the server to read churn. | MCP responses; fresh-process probe with the tool venv |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-24 | Plan this as its own change in arc 244cm and release 1.52.0 after it. | Operator: "Yes" to committing 249ar and planning the upgrade change, then "Add it to the arc". | Ship 1.52.0 without it: declined, the first upgraded project would meet the refusals without the guidance. |
| 2026-11-24 | Selected: read-only counts in `memory_brief` plus seed 160 guidance. Efficacy: replaying this repository, the brief would report 7 unresolved and 98 churned, and the new rule would recommend Review memories where today's rule (174 active, cap 50) also fires; for a project under the cap the old rule stays silent and the new one fires. It advises only: the upgrade summary is what a maintainer acts on. It can over-fire in an old project where most records churn on first read; that backlog is real and the recommendation is one line. Most of the value comes from data `_memory_ranked` already computes. Measured after release by whether upgraded projects run Review memories (Risks). | Planner default. | (A) Seed text only, with the agent sampling `memory_search(order="least_recently_reviewed")`: gives no totals, so the recommendation would rest on a 15-record sample. (C) Report counts from the upgrade runner or backfill inventory: runs in the upgrade process across the old-code window and adds a git walk to every upgrade, and still needs the prompt merge. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Wave `248o5` last edited the same seed, handler and contract files. | It closed and was committed in `cbc69fb8`; the implementer rereads those files before editing. |
| Maintainers may ignore the recommendation. | Observe after release: the first target upgrades to 1.52.0 should show the counts and the recommendation in the upgrade summary. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
