# Deliver memory revalidation guidance and signals through upgrade

Spec ID: `24but-enh deliver-memory-revalidation-through-upgrade`
Spec Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-11-24
Wave: TBD

## Rationale

Wave `249ar` (change `246to`) changed how memory records are kept: keeping an active record now needs a `check_note`, a keep is refused while a target is unresolved, and records carry derived `revalidation_reasons`. That code reaches a target repository through upgrade, but two parts of the delivery do not:

1. Seed 160 materializes `docs/prompts/memory-review.prompt.md` only when it is missing and otherwise preserves its bytes (seed 160, operating-memory checklist). Its briefing-loop carrier list merges seed 190 into the Close wave prompt only for `Intent outcome:`. No entry merges the seed 240 and seed 190 keep rule. An upgraded project keeps the old "keep it" wording, and its agents meet `memory_check_required` before they learn the rule from the refusal's retry hint.
2. After the upgrade reload, seed 160 recommends **Review memories** only when `memory_brief` reports `curation_required` or consolidation candidates. `memory_brief` sets `curation_required` only when the active count reaches `ACTIVE_MEMORY_CAP` (`wf_server/memory_handlers.py`, `memory_brief_response`). A project under the cap with unresolved or churned targets gets no recommendation, even though the 1.52.0 code flags those records at once. A record with no `Checked at:` line counts churn from `Updated:`, so an older project can have most of its records churn-flagged on the first read; this repository had 98 of 174 on 2026-11-24.

This is a track of arc [`244cm-arc memory-quality`](../arcs/244cm%20memory-quality/244cm-arc%20memory-quality.md): outcome 3 ("every surfaced record still points at code that exists, or is queued for revalidation") holds in a target repository only when its maintainers learn of the queue and its agents follow the keep rule. Release 1.52.0 waits for this change (operator decision, 2026-11-24).

## Product Intent

**Beneficiaries:** maintainers who upgrade a target repository to 1.52.0, and the agents that run Review memories and Close wave there.

**Before:** after upgrading, a project under the active-record cap hears nothing about its unresolved or churn-flagged records, and its local Review memories and Close wave prompts still describe a keep without a `check_note`.

**After:** the upgrade's post-reload memory step reports how many active records have an unresolved, churned or bare-name target and recommends Review memories when any is unresolved or churned; the upgrading agent merges the keep rule into the project's existing Review memories and Close wave prompts, preserving local prose.

**Boundaries:** upgrade still never curates, rewrites, retires or purges a record, and never runs Review memories. No new gate, no new tool, no upgrade-runner code. The counts come from the rule `246to` already ships.

AC-1 and AC-2 establish that the counts are trustworthy; AC-3 and AC-4 establish that an upgrade delivers the guidance and the recommendation. Whether maintainers act on the recommendation is observable only after release (see Risks).

## Requirements

1. `memory_brief` returns a read-only `revalidation` object in every successful response, with integer fields `active_records`, `target_unresolved`, `target_churn` and `target_not_canonical`. Each count is the number of records with status `active` whose `revalidation_reasons` contain that reason, computed from the same `_memory_ranked` pass the brief already makes, before the briefing, target and limit filters. Candidate and retired records are not counted. The object carries counts only, never memory ids.
2. The counts follow one rule with `memory_eval.maintenance_signals`: on the same repository state both report the same `target_unresolved`, `target_churn` and `target_not_canonical` counts.
3. Seed 160 adds a briefing-loop carrier entry: seed 240 and the `memory-review` install baseline reconcile into `docs/prompts/memory-review.prompt.md`, and seed 190 and the `close-wave` baseline reconcile into the profile-resolved Close wave prompt, for the keep rule. The rule: a keep or reactivation of an active record needs a single-line `check_note`, a keep is refused while a target is unresolved, and promoting a candidate needs neither. The entry uses the list's existing merge discipline (merge only changed clauses, preserve project prose and marker regions, stop on conflict).
4. Seed 160's post-reload memory step calls `memory_brief` as today and recommends **Review memories** when `curation_required` is true, consolidation candidates are returned, or `revalidation.target_unresolved` or `revalidation.target_churn` is above zero. The recommendation states the counts. It never runs curation or purge.
5. The self-hosted copy `docs/prompts/upgrade-wavefoundry.prompt.md` carries the same text as seed 160 for requirements 3 and 4.
6. Platform behavior: the change is pure Python and prompt text. It adds no path, process or filesystem behavior, so Windows, macOS, Linux and WSL2 behave the same; the churn count reuses the existing git read.

## Scope

**Problem statement:** the 249ar keep rule and revalidation signals ship in code but not in an upgraded project's prompts or upgrade summary.

**In scope:**

- The `revalidation` counts in `memory_brief`, with tests.
- The seed 160 carrier entry and post-reload recommendation, and the self-hosted upgrade prompt copy.
- `docs/architecture/contracts/mcp-tool-surface.md` (the `memory_brief` response fields) and a `CHANGELOG.md` `[Unreleased]` entry.

**Out of scope:**

- Any change to records, to `memory_reconcile`, or to the refusal codes.
- Running Review memories in this repository; that is the separate, operator-authorized pass on arc 244cm item 7.
- Upgrade-runner (`upgrade_wavefoundry.py`) or backfill-inventory changes.
- A "disputed in a session" signal (declined for wave `249ar`).

## Acceptance Criteria

- [ ] AC-1: On a fixture with five records, active A (unresolved target), active B (target churned past its threshold since its last check), active C (bare-name target that matches one file), active D (clean) and candidate E (unresolved target), `memory_brief()` returns `revalidation` equal to `{"active_records": 4, "target_unresolved": 1, "target_churn": 1, "target_not_canonical": 1}`. The same object is returned with `limit=1` and with `targets=["no/such/file.py"]` (an empty briefing). Known bad: counting from the briefing list after the limit or target filter returns lower counts; counting all surfaced statuses gives `target_unresolved: 2`.
- [ ] AC-2: On the AC-1 fixture, `revalidation`'s three reason counts equal `memory_eval.maintenance_signals(root, ...)`'s corresponding counts, and no memory id appears in the `revalidation` object.
- [ ] AC-3: Seed 160 and `docs/prompts/upgrade-wavefoundry.prompt.md` each contain a briefing-loop carrier entry naming seed 240 and the `memory-review` baseline into `docs/prompts/memory-review.prompt.md`, and seed 190 and the `close-wave` baseline into the Close wave prompt, stating the keep rule of requirement 3. A test pins the entry in both files. Known bad: the test fails on the current seed 160, which has no such entry.
- [ ] AC-4: Seed 160 and its self-hosted copy state the recommendation rule of requirement 4, naming `revalidation.target_unresolved` and `revalidation.target_churn`, and keep "never run memory curation or purge automatically". A test pins it. Known bad: the current text, which names only `curation_required` and consolidation candidates, fails the test.
- [ ] AC-5: Measured on this repository, read-only, after the MCP server reloads the new code: `memory_brief(context="review")` reports `revalidation` counts equal to `wf_memory_eval()`'s `maintenance_signals` counts for the same three reasons, recorded in the Progress Log. `git status --porcelain docs/agents/memory` is unchanged by the measurement.
- [ ] AC-6: `docs/architecture/contracts/mcp-tool-surface.md` documents the `revalidation` object under `memory_brief`, and `CHANGELOG.md` has an `[Unreleased]` entry naming this wave and change.

## Tasks

- [ ] `wf_server/memory_handlers.py` `memory_brief_response`: compute `revalidation` from the unfiltered `_memory_ranked` output for active records; refresh the handler-digest pin.
- [ ] Tests for AC-1 and AC-2 in `tests/test_memory_records.py` (the existing `memory_brief` tests) using a temporary fixture repository; no test touches real records.
- [ ] Seed 160 (under `seed_edit_allowed`): the carrier entry and the recommendation rule; apply the same text to `docs/prompts/upgrade-wavefoundry.prompt.md`.
- [ ] Text-pin tests for AC-3 and AC-4.
- [ ] Docs: the contracts tool-surface entry and the changelog entry.
- [ ] AC-5 measurement; run `run_tests.py --profile second --file` on each touched test file and the full default suite with `--no-cache` last.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| brief-counts | implementer | — | Requirement 1 and 2, AC-1, AC-2 |
| upgrade-guidance | implementer | — | Requirements 3 to 5, AC-3, AC-4 |
| docs-and-measure | implementer | brief-counts, upgrade-guidance | AC-5, AC-6 |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/memory_handlers.py`, `.wavefoundry/framework/scripts/tests/test_memory_records.py`, `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`
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

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-24 | Planned. Wave `248o5` is open and edits seed 160, `memory_handlers.py` and the tool-surface contract, so this change implements after `248o5` closes. | `wf_current_wave` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-24 | Plan this as its own change in arc 244cm and release 1.52.0 after it. | Operator: "Yes" to committing 249ar and planning the upgrade change, then "Add it to the arc". | Ship 1.52.0 without it: declined, the first upgraded project would meet the refusals without the guidance. |
| 2026-11-24 | Selected: read-only counts in `memory_brief` plus seed 160 guidance. Efficacy: replaying this repository, the brief would report 7 unresolved and 98 churned, and the new rule would recommend Review memories where today's rule (174 active, cap 50) also fires; for a project under the cap the old rule stays silent and the new one fires. It advises only: the upgrade summary is what a maintainer acts on. It can over-fire in an old project where most records churn on first read; that backlog is real and the recommendation is one line. Most of the value comes from data `_memory_ranked` already computes. Measured after release by whether upgraded projects run Review memories (Risks). | Planner default. | (A) Seed text only, with the agent sampling `memory_search(order="least_recently_reviewed")`: gives no totals, so the recommendation would rest on a 15-record sample. (C) Report counts from the upgrade runner or backfill inventory: runs in the upgrade process across the old-code window and adds a git walk to every upgrade, and still needs the prompt merge. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Wave `248o5` (open, another session) edits the same seed, handler and contract files. | Ready in parallel; implement only after `248o5` closes and its tree is committed. |
| The host reports `spec_tool_unavailable` for `wf_get_spec`. Wave 248o5 renamed the admission tool to `wf_add_spec`. | Update the host allow rules and restart before admitting this spec. |
| Maintainers may ignore the recommendation. | Observe after release: the first target upgrades to 1.52.0 should show the counts and the recommendation in the upgrade summary. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
