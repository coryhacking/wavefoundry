# Derive tier nouns in skill descriptions from the vocabulary profile

Change ID: `2134r-enh profile-skill-description-nouns`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-19
Wave: `2134s distribution-vocabulary-portability`

## Rationale

`render_agent_surfaces.SKILL_REGISTRY` already derives skill names, prompt paths and shortcuts through the profile (`_vp_skill`, `_vp_doc`, `_vp_shortcut`), but about 12 of its 15 entries still carry literal tier nouns in descriptions and body titles: "Confirm a wave's readiness", "Prepare a wave", "Close one admitted change inside the open wave", "the open wave's required review lanes". On Waveforge (our wave is their Set, our change is their wave) these read wrongly in every host's skill list. The profile has no article or possessive helpers, so a renderer cannot derive them today.

## Product Intent

A renamed distribution's rendered skills describe its own tiers ("Prepare a Set", "Close one admitted wave inside the open Set") with no edits to our renderer. Boundaries: Wavefoundry's rendered skills are byte-identical under the default profile, ordinary-English uses of "change" stay as they are, and skill names keep coming from the prompt-name map. AC-1 and AC-2 test the intent.

## Requirements

1. `vocabulary_profile` gains tier-noun helpers for the container and the item: singular and plural (from the existing `*_NAME` and `*_NAME_PLURAL`), lower and title case, and an indefinite article from new constants `CONTAINER_NAME_ARTICLE` and `ITEM_NAME_ARTICLE` (default `"a"`), which `validate` checks are `"a"` or `"an"`.
2. In every `SKILL_REGISTRY` description and body title, each word that denotes the container or item tier (the wave or change record) is produced by those helpers; other uses of the words (for example "behaviour changes", "product code changes") stay literal. Implementation records the per-entry census in the Progress Log.
3. Under the default profile every rendered skill file is byte-identical to today's.
4. The helpers are pure functions of the profile constants; no prose outside `SKILL_REGISTRY` is rewritten by this change.

## Scope

**Problem statement:** Skill descriptions name our tiers literally on renamed distributions.

**In scope:** `vocabulary_profile.py` helpers and constants, `SKILL_REGISTRY` text in `render_agent_surfaces.py`, tests, one CHANGELOG bullet.

**Out of scope:** skill names (already derived), lifecycle prompt templates, seeds, `AGENTS.md` text, and MCP tool names.

**Platform behaviour:** the same on Windows, macOS, Linux and WSL2. The change produces strings at render time; rendered skill files keep the existing writer and its newline handling.

## Acceptance Criteria

- [x] AC-1: Under the default profile, rendering every skill host produces byte-identical skill files. Oracle: render into two temp roots before and after (or the existing render golden tests) and compare.
- [x] AC-2: Under a Set/Wave test profile (container "Set", item "Wave", articles "a"), every rendered skill description and body title names only the profile's tiers: no word census-listed as a tier noun still reads "wave" or "change" in our meaning. Oracle: a test that renders under the patched profile and checks the census-listed spans.
- [x] AC-3: `validate` rejects an article other than "a" or "an".
- [x] AC-4: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the helpers and article constants with validation.
- [x] Census `SKILL_REGISTRY` tier nouns and rewrite them through the helpers.
- [x] Add the AC-1 to AC-3 tests.
- [x] Add the CHANGELOG bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| helpers | implementer | none | `vocabulary_profile.py` |
| registry | implementer | helpers | `render_agent_surfaces.py` |

## Serialization Points

- `.wavefoundry/framework/scripts/vocabulary_profile.py`, `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: renderer-owned text only; the profile gains helpers inside its own module and no boundary or flow changes.

## AC Priority

| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required     | No change for Wavefoundry and its consumers. |
| AC-2 | required     | The distribution outcome. |
| AC-3 | important    | Guards the new constants. |
| AC-4 | required     | Standard change-local verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-19 | Planned from the Waveforge request (ask B). Optional within the wave: the distribution can also edit these strings itself; drop this change if the wave runs long. | Read-only map: 15 registry entries, about 12 with literal tier nouns. |
| 2026-10-19 | Readiness: no longer optional. Change `2134q` builds tier nouns in its contract-clause assertions with this change's helpers, so this change lands first. Known description pin: `test_review_plan_is_the_only_plan_review_skill` checks "current wave record" under the default profile. | Red-team primer report; receipt `review-policy-7c7c28e99e841ca1cae2` superseded. |
| 2026-10-19 | Implemented. `tier_noun(tier, plural, title, article)` and `tier_article_errors()` (kept out of `FIELD_NAMES`, per the readiness note). Census (requirement 2) of `SKILL_REGISTRY`: rewritten through `_vp_wave`/`_vp_change`: plan-change (description, title, kind sentence, gate reminder), prepare-wave (description, title, council step, OPEN reminder), implement-wave (description, title, tool sentence, gate reminder, single-change variant), review-wave (description, title), close-wave (description, title, single-change line), close-change (description twice, title, run-after line, only-close line), review-plan (description, named-doc line, delivery lanes line), pause-wave (description, title), council (open-lanes and stress-test sentence), code-cleanup (open-lanes). Kept literal: "Wave Framework", "wave lifecycle commands", "repo-local wave surfaces", tool names (`wf_close_change`, `wf_implement_wave`, `wf_add_change`), the kind list entry "change", "product code changes". AC-1: a JSON dump of every registry entry's name, description and body before and after the edit is byte-identical (scratch `2134r/before.json`, `after.json`). Note: `vocabulary_profile.py` is pinned in `tests/fixtures/profiles/qualification/coverage.json`; a changed contract makes release qualification fall back to a full profile run (documented behaviour), so the reviewed inventory was not edited. Gapfill: shell edits used because auto mode prefers Bash for file work. | `test_vocabulary_tier_nouns.py` 6 OK; render, skills and platform surface files 386 OK; profile, qualification and prompt-name files 160 OK. |
| 2026-10-19 | Delivery repair (QA): `TierNounHelperTests.test_default_nouns` asserted the live profile's nouns, so it failed under any renamed profile (`--profile second`). It now pins the shipped constants with `mock.patch.multiple` and runs on every profile. | `run_tests.py --profile second --file test_vocabulary_tier_nouns.py`: 0 of 1 failed; `2134s-del-qa-reviewer-2`. |
| 2026-10-19 | Whole framework suite (last, both waves 2134o and 2134s in the tree): `Ran 11945 tests across 201 files in 722.422s OK` (12 skipped); green receipt. | `python3 .wavefoundry/framework/scripts/run_tests.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-19 | Explicit helper calls per tier noun, with declared article constants. | Avoids corrupting ordinary-English "change" and double rewrites under name swaps. | Search-and-replace over descriptions: corrupts prose and double-rewrites Set/Wave. Computing the article from the first letter: wrong for names like "Hour" or "Unit". |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A tier noun is missed or an ordinary word rewritten. | Requirement 2's recorded census; AC-2 checks the census-listed spans. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
