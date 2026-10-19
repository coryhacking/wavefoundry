# Resolve prompt shortcuts through the vocabulary profile

Change ID: `2134p-enh profile-shortcut-lookup`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-19
Wave: `2134s distribution-vocabulary-portability`

## Rationale

A renamed distribution (Waveforge, running 1.32.0 with `CONTAINER_NAME = "Set"` and `ITEM_NAME = "Wave"`) declares its own prompt names and shortcut phrases through `vocabulary_profile.PROMPT_NAME_OVERRIDES`, and `migrate_profile_prompt_names` moves the rendered prompt files to the profile's slugs. But `wf_server.server_impl.get_prompt`, which backs `wf_get_prompt`, never consults the profile or the manifest's `prompt_names` record. It slug-matches the requested phrase against file stems, then falls back to the first prompt whose content contains the phrase. Wave 1zyb4 (change 1zxnw) named manifest-based lookup as a follow-up that was never done.

The substring matching misroutes in both directions. A short phrase matches the first file stem containing its slug, and under a Set/Wave profile our default phrase "Close wave" means their "Close Set", while their "Close wave" means our "Close change". Only the profile can say which prompt a phrase names.

## Product Intent

An agent or operator on any distribution asks for a prompt by that distribution's shortcut or alias and gets the right prompt, including after a profile rename. Boundaries: under the default profile every declared shortcut and alias resolves to its own prompt, which changes one result today ("Ready wave" currently falls through to the content search and returns `docs/prompts/index.md`; it will return the prepare-wave prompt); phrases the profile does not declare keep today's file-name and content fallback, and MCP tool names are untouched. AC-1 and AC-2 test the intent.

## Requirements

1. Before any other matching, `get_prompt` resolves the requested phrase (case-insensitive, surrounding whitespace ignored) against the active profile's declared shortcut and aliases for every `vocabulary_profile.PROMPT_NAMES` key. A match returns the prompt at that key's applied path: the manifest's `prompt_names` record when present and valid (as `vocabulary_profile.applied_prompt_slugs` reads it), else the profile's `prompt_doc(key)`.
2. Default-vocabulary phrases are not accepted implicitly when the profile renames a prompt; only the profile's own shortcut and aliases resolve through requirement 1. (A distribution that wants an old phrase to keep working declares it as an alias.)
3. When the applied path is refused by the contained read or is a runtime lock target, `get_prompt` records it in `refused` as today and continues to the existing fallbacks. A merely missing applied path is not recorded (an entry in `refused` disables caching and triggers a warning in `wf_get_prompt`); the lookup falls through silently.
4. A phrase that matches no declared shortcut or alias keeps today's behaviour exactly: the file-stem slug match, then the content search.
5. A malformed manifest `prompt_names` record does not fail the lookup: resolution uses the profile's names, as `_applied_close_change_entry` does.
6. `get_prompt_text_cached` cannot serve a stale result after the manifest's `prompt_names` record changes: its cache key or fingerprint covers `docs/prompts/prompt-surface-manifest.json`.

## Scope

**Problem statement:** Prompt lookup ignores the vocabulary profile, so renamed distributions' shortcuts can misroute.

**In scope:** `get_prompt` in `wf_server/server_impl.py` (and its cached wrapper if it needs no more than passing through), tests, one CHANGELOG bullet, and the `wf_get_prompt` description in `docs/specs/mcp-tool-surface.md` if it describes the matching order.

**Out of scope:** MCP tool names (distributions alias them through `EXTENSION_TOOL_ALIASES`), prompt text, skill names, and `docs/prompts/index.md` rendering.

**Platform behaviour:** the same on Windows, macOS, Linux and WSL2. Paths are built with `pathlib` from repository-relative slugs and read through the existing contained read, which already handles case-insensitive filesystems and Windows path rules.

## Acceptance Criteria

- [x] AC-1: Under a test profile that renames prompts in the Set/Wave pattern (our `close-change` key declared as "Close wave", our `close-wave` key as "Close Set", with migrated files), `get_prompt` returns the `close-change` prompt for "Close wave" and the `close-wave` prompt for "Close Set", and returns each declared alias's prompt. Under the same profile, the old default phrase "Close change" does not resolve through the profile step.
- [x] AC-2: Under the default profile, every default shortcut and alias resolves to its key's prompt (including "Ready wave", which today returns `index.md`), and a phrase matching no declared name returns what it returns today (one fixture each for the file-stem and content fallbacks).
- [x] AC-3: A refused applied path is recorded in `refused` and the lookup falls through; a missing applied path falls through without a `refused` entry; a malformed `prompt_names` record resolves through the profile's names; changing the manifest's `prompt_names` changes the cached lookup's result.
- [x] AC-4: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the profile resolution step to `get_prompt`.
- [x] Add the AC-1 to AC-3 tests.
- [x] Update the `wf_get_prompt` matching description if the spec states one; add the CHANGELOG bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| lookup | implementer | none | `server_impl.py`, tests |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/tests/`, `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

N/A: the lookup stays inside `get_prompt`; no module boundary or flow changes. The tool spec is updated only if it states the matching order.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The distribution outcome. |
| AC-2 | required  | No regression for Wavefoundry and its consumers. |
| AC-3 | important | Fail-safe behaviour on bad state. |
| AC-4 | required  | Standard change-local verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-19 | Planned from the Waveforge request (follow-up to their #44) and a read-only map of the profile. | `get_prompt` matches file stems then content and never reads `prompt_names`. |
| 2026-10-19 | Readiness red-team primer: no blocker. Repaired before any approval: Product Intent and AC-2 state the "Ready wave" result change; a missing applied path no longer goes into `refused` (it would disable caching and warn); requirement 6 makes the cache notice manifest changes. Implementation note: check cross-key alias collisions are already refused by `prompt_name_errors`. | Red-team primer report; receipt `review-policy-7c7c28e99e841ca1cae2` superseded. |
| 2026-10-19 | Implemented. `_profile_prompt_path` casefolds the phrase against each `PROMPT_NAMES` key's shortcut and aliases (collisions are already refused by `prompt_name_errors`), reads the manifest's `prompt_names` through the contained reader (any read or parse failure, or an invalid record, falls back to the profile's slug), and `get_prompt` returns that file before the existing fallbacks; a missing file falls through without a `refused` entry, a refused one is recorded by the existing reader. `McpRepoCache._prompts_fingerprint` now includes the manifest's mtime and size. `docs/specs/mcp-tool-surface.md` states no matching order ("Resolves a Wave Framework shortcut phrase to rendered prompt content"), so it is unchanged. Gapfill: shell edits used because auto mode prefers Bash for file work. | `ProfileShortcutLookupTests` 7 OK; `test_server_tools_lifecycle.py` 651 OK. |
| 2026-10-19 | Implementation note (deviation from Requirement 1's wording, recorded here because the change doc is past readiness): with no `prompt_names` record the lookup uses the shipped slugs, as `vocabulary_profile.applied_prompt_slugs(None)` and the renderer read an absent record (prompts not yet migrated), not the profile's slug that Requirement 1 states; the profile's slug is used only for an invalid record (Requirement 5). Using the profile's slug for an absent record would send a renamed "Close wave" (the item close) to the unmigrated container-close file `close-wave.prompt.md`. Found by the 2134q implementer; docstring and comment corrected. | `_profile_prompt_path` docstring. |
| 2026-10-19 | Delivery repair (code-reviewer): `test_malformed_manifest_resolves_through_the_profile` ran only under the default profile, so it could not tell the profile slug from the shipped one (mutant M2 survived). Added `test_malformed_manifest_uses_the_profile_slug_not_the_shipped_one` under a Set/Wave swap; M2 now fails. Red-team note applied: the docstring says a hand-edited record that disagrees with the files misroutes exactly as the renderer would. | `ProfileShortcutLookupTests` 8 OK; `2134s-del-code-reviewer-1`. |
| 2026-10-19 | Whole framework suite (last, both waves 2134o and 2134s in the tree): `Ran 11945 tests across 201 files in 722.422s OK` (12 skipped); green receipt. | `python3 .wavefoundry/framework/scripts/run_tests.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-19 | Resolve declared shortcuts first, then keep the existing fallbacks. | Fixes misroutes without breaking free-text lookups. | Replace the fallbacks: breaks callers passing loose phrases. Accept default phrases implicitly: wrong under name swaps such as Set/Wave. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A default-profile phrase that used to hit a different file via substring now resolves differently. | Known case: "Ready wave" (from `index.md` to the prepare-wave prompt), an intended fix. AC-2 pins every default phrase. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
