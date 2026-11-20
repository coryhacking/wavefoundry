# Preserve distribution planning names

Change ID: `23tcy-bug preserve-distribution-planning-names`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-19
Wave: 23td0 downstream-lifecycle-compatibility

## Product Intent

A distribution maintainer can upgrade and still invoke the same five planning workflows, while agents receive instructions using the project's names for the item and its container. AC-2 demonstrates continuity through a real render. AC-1 covers the independently useful wording correction. This supports dependable delivery on the existing foundation in Horizon 1 of the designated vision.

## Rationale

Waveforge reported that an upgrade to v1.44.1 could rename five workflows unless the distribution pinned each one. The vocabulary registry assigns `add-change-to-wave` the default slug `add-spec-to-wave` and shortcut “Add spec to wave.” The renderer uses the registered earlier prompt path as authority to move its files. Its named migration compares slugs without testing the distribution's item or container noun. The served council instructions also say “against the admitted specs” literally. The expected result on an existing custom profile is continued access by its established names and messages identifying its own planning document.

## Requirements

1. Inventory the terminology introduced by the planning-document rename in the served tool descriptions, results, diagnostics, lint and lifecycle gate messages. For each user-visible reference to the planning document, select the matching form of `planning_noun()`; use the configured container noun when that sentence also names its container. Preserve actual command names, registered prompt references, argument names, result keys, diagnostic codes and Markdown anchors. Ordinary uses of “specification” with another meaning are outside the rename.
2. For the five keys in `EARLIER_DEFAULT_PROMPT_SLUGS`, a profile with a non-shipped item or container noun must keep the effective names of registered prompts unless the distribution explicitly overrides the relevant name. Cover an old default known only from the registered public path, an explicit recorded slug and an already-migrated current default. Preserve public and agent prompt bytes in a no-move case. An explicit per-key override takes precedence through the existing migration, preflight and conflict rules.
3. Keep the slug, shortcut, aliases, manifest, public and agent paths and registered skills consistent. Use the established shortcut when registered. Retain explicit overrides for individual shortcut or alias fields when resolving a partial override. For a fresh custom installation with no applied name, derive defaults for the five keys from its configured vocabulary, using the same validation as explicit names. A profile with nouns that cannot yield a valid, unique slug receives an actionable preflight diagnostic naming the required override before any file move. The shipped profile continues its existing five migrations and new-install behavior.
4. In normal render output, identify the established names a custom distribution kept and where the maintainer can explicitly change them. Existing manifest authority, protected user edits, conflict and interruption recovery apply. Resolve effective names for the selected repository. A long-lived process can serve multiple checkouts that share a distribution profile but have different registered names.

## Scope

The change covers only the five renamed planning prompts and the planning-document vocabulary introduced by the rename. Write owners are the vocabulary and renderer maintainer and the lifecycle message maintainer. QA and the documentation contract reviewer inspect behavior read-only. Reconcile the distribution vocabulary guidance and the release note for these names. Protect the MCP protocol, historical wave records, unrelated seeds and operator-authored prompt bodies. Do not introduce profile-aware renaming for other workflows.

## Acceptance Criteria

- [x] AC-1: A served lookup refusal, a returned lifecycle or council instruction, a served tool description and a lint or gate diagnostic use the expected item noun under a custom profile. The shipped counterparts use spec wherever that rename applies. A census accounts for other changed user-visible strings and separately classifies machine identifiers and unrelated words.
- [x] AC-2: An upgrade fixture with custom item and container names and the five legacy registrations retains the public and agent files and bytes, shortcuts and registered skill routes. The render names the preservation decision. A second render makes no further moves. Cover an already-migrated registration, an explicitly recorded applied slug and a container-only customization. In one process resolve checkout A, then B, then A again with distinct applied names on the same distribution profile. Verify file, skill and served routes for each without restarting the process.
- [x] AC-3: Fresh shipped and custom renders resolve each of the five workflows through the intended paths, shortcuts and registered skills. An explicit override on one key wins while other established names stay in place. An invalid derived name or conflicting destination produces the actionable failure before moving files. The shipped-profile legacy migration and existing restart-after-interruption checks pass.

## Tasks

- [x] Census and repair the user-facing wording in served, gate and lint surfaces and exercise the changed messages with two profiles.
- [x] Reconcile prompt naming and migration with registration and override authority. Exercise upgrade, fresh install, idempotency, conflict and interruption cases through the renderer.
- [x] Document the preservation rule and verify that the affected public entry points resolve.

## Agent Execution Graph

| Workstream | Owner | Depends on | Evidence |
| --- | --- | --- | --- |
| Vocabulary and render behavior | Framework implementer | Readiness | Profiled render and migration fixtures |
| User-facing terminology | Lifecycle implementer | Agreed noun forms | Served tool and lint or gate results |
| Contract validation | QA and docs-contract reviewers | Integrated implementation | Shipped and custom control matrix |

## Serialization Points

- `.wavefoundry/framework/scripts/vocabulary_profile.py`, `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`, `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/tests/test_vocabulary_prompt_names.py`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

Review the existing vocabulary-profile and prompt-migration contract for the effective-name precedence. Update the distribution guidance that currently describes the shipped-default migration and its test coverage.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Agents receive instructions from the served tool and diagnostics. |
| AC-2 | required | The upgrade is the reported point of failure. |
| AC-3 | required | Fresh installs, explicit renames and shipped upgrades share the same resolver. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-19 | Confirmed the fixed registry entries and the manifest-driven move in source. | vocabulary_profile.DEFAULT_PROMPT_NAMES and render_agent_surfaces.migrate_profile_prompt_names |
| 2026-11-19 | Readback: keep each repository’s registered planning names and resolve fresh installations from distribution nouns. | Gapfill: the five-key rendering and migration census requires a bulk inventory of import-derived carriers as well as indexed source reads. |
| 2026-11-19 | Verified served and lint planning nouns under shipped and custom vocabularies, and registered prompt resolution across checkout roots. | The focused naming, tier and carrier tests passed (72 cases). |
| 2026-11-19 | Implemented and exercised repository-scoped prompt resolution for upgrades, fresh installs, explicit overrides, conflicts, repeated rendering and sequential checkouts. The reconciliation scan reads the manifest within its existing budget. | The naming, tier and record-layout tests passed together (72). The migration tests also passed after adding the preflight before earlier render operations (15). |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-19 | Preserve established registrations and derive defaults only where a fresh custom profile has no established name. | Teams keep existing entry points while new custom installs get names that fit their vocabulary. | Deriving every name forces existing users through another migration. Requiring five pins leaves each distribution to discover the break during upgrade. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A file happens to have an earlier slug but belongs to another prompt. | Use manifest registration and existing move preflight. Exercise a conflicting target and verify original bytes. |
| Rendering retains the file but a discovery tool points elsewhere. | Check manifests, command shortcuts and registered skill targets alongside filenames. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
