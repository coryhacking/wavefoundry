# Drop the Distill journals alias

Change ID: `21255-maint drop-distill-journals-alias`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-18
Wave: 2136j drop-distill-journals-alias

## Rationale

**Migrate journals** (seed 210) retires leftover journal files into the memory system. It still carries a legacy alias, **Distill journals**, named in `AGENTS.md` and in the seed 100 `migrate-journals` entry. The same phrase is a retired close-time instruction ("At close, distill journals"), which `reconcile_scan.py` reports as a stale journal instruction. To avoid flagging the alias, the scan exempts any line that also names the live command (`_LIVE_JOURNAL_MIGRATION` on the `distill journals?` pattern), and `test_wf_cli.py` pins that exemption. The alias adds nothing over the command's own name and keeps that ambiguity alive.

## Requirements

1. `AGENTS.md` and seed 100 no longer name **Distill journals** as an alias of **Migrate journals**. The command, seed 210 and its shortcut phrase stay.
2. `reconcile_scan.py` reports every `distill journals?` occurrence outside wave archives, including on a line that names **Migrate journals**: the `_LIVE_JOURNAL_MIGRATION` exemption is removed from that pattern only. It stays on the `docs/agents/journals` path pattern, where seed 210's own instructions legitimately name the directory. The comment block that defended the alias exemption is rewritten. The `distill journals?` pattern gets its own suggestion, saying the phrase is retired, that a leftover alias of **Migrate journals** should be deleted, and that the **Migrate journals** command itself stays; the generic journal suggestion alone could lead an operator to delete the whole row.
3. `test_live_migrate_journals_alias_is_not_reported` becomes a test that an alias line naming both phrases is reported as a `journal instruction` on that exact line with the new suggestion, and that a `docs/agents/journals` line naming **Migrate journals** stays exempt.
4. `CHANGELOG.md` Unreleased gains a `### Changed` heading with a bullet saying the alias is gone, that a leftover alias in a target repository's `AGENTS.md` shortcut table now shows up in the reconcile scan, and that the remedy is to delete the "(legacy alias: **Distill journals**)" text and keep the **Migrate journals** row.
5. Behaviour is the same on Windows, macOS, Linux and WSL2: text and regex edits only, with no path, process or filesystem change.

## Scope

**Problem statement:** a redundant legacy alias doubles as a retired instruction and forces a scan exemption.

**In scope:** Requirements 1 to 4 in `AGENTS.md`, `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`, `.wavefoundry/framework/scripts/reconcile_scan.py`, `.wavefoundry/framework/scripts/tests/test_wf_cli.py` and `CHANGELOG.md`.

**Out of scope:**

- Removing **Migrate journals** or seed 210; target repositories may still hold journals.
- Wave archives, `CHANGELOG.md` history and the parked plan `docs/plans/1rolq-enh verify-docs-agentic-review.md`, which narrate history.
- Other "distillation" wording, which is unrelated.

## Acceptance Criteria

- [x] AC-1: A case-insensitive `git grep "distill journal"` outside `docs/waves/`, `CHANGELOG.md` and the parked plan matches only the `reconcile_scan.py` pattern and the `test_wf_cli.py` fixtures, which must keep the phrase to prove the scan reports it.
- [x] AC-2: The reconcile scan reports a line that names both **Migrate journals** and "Distill journals", and still exempts a `docs/agents/journals` line naming **Migrate journals**; the updated test fails against the unpatched exemption in a scratch copy.
- [x] AC-3: One whole-suite `--no-cache` run passes with a fresh green receipt.

## Tasks

- [x] Apply Requirements 1 to 4 under `framework_edit_allowed` and `seed_edit_allowed`.
- [x] Run the AC-2 mutant in a scratch copy.
- [x] Run the whole suite for the receipt.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| alias | implementer | none | Requirements 1 to 4 |

## Serialization Points

- `.wavefoundry/framework/scripts/reconcile_scan.py`, `.wavefoundry/framework/scripts/tests/test_wf_cli.py`, `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- AGENTS.md and CHANGELOG.md text edits.

## Affected Architecture Docs

N/A: a prompt-surface wording change and one scan exemption, with no boundary, flow or verification-architecture change.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The removal itself. |
| AC-2 | required | The scan must now report the alias. |
| AC-3 | required | The receipt must be current before close. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-18 | Readiness review folded in before approval: docs-contract asked for the `### Changed` heading, a testable AC-1 with the fixture carve-out and a named remedy; QA asked the test to pin the surface label and line; red-team asked for an alias-specific suggestion. | readiness lanes |
| 2026-10-18 | Planned after a census of `distill` outside wave archives: the alias appears only in `AGENTS.md`, seed 100, the `reconcile_scan.py` exemption comment and `test_wf_cli.py`; other hits are unrelated "distillation" wording or history. | `git grep -in distill` |
| 2026-10-18 | Implemented under `seed_edit_allowed` (seed 100) and `framework_edit_allowed` (scan and test). The `distill journals?` pattern has no exemption and a new `_DISTILL_JOURNALS_SUGGESTION`; the directory pattern keeps `_LIVE_JOURNAL_MIGRATION`. New test `test_leftover_distill_journals_alias_is_reported`. AC-1: the grep matches only `reconcile_scan.py` and `test_wf_cli.py`; in `reconcile_scan.py` it hits the pattern plus the comment and suggestion text Requirement 2 needs, and in the test file the fixtures plus a docstring. AC-2: in a scratch copy the exemption restored on the distill pattern and the exemption dropped from the directory pattern each fail the test. Delivery lanes approved; QA mutants (also suggestion reverted, pattern removed) all caught. Real `scan_repo` shows only the two pre-existing `docs/agents/journals` findings in `docs/architecture/data-and-control-flow.md` and `docs/specs/mcp-tool-surface.md`. AC-3: whole suite `--no-cache` ran 11902 tests, OK, with a fresh green receipt. Gapfill: shell and scratch copies for mutants and the grep census. | scratchpad ac2-2136j, del-2136j, 2136j-full.txt |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-18 | Drop only the alias; keep the command. | Target repositories may still have journals to migrate. | Retire Migrate journals too (deferred until no target holds journals). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A target repository's own AGENTS.md still lists the alias after upgrade. | The reconcile scan now reports it with the journal-retirement suggestion, so it surfaces for removal. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
