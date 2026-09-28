# Vocabulary Profile for Record Names: Profile and Readers

Change ID: `1z826-feat vocabulary-profile-record-names`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-27
Wave: 1z8mm vocabulary-profile-record-names

## Rationale

The RFC "Vocabulary profiles and an optional parent tier" (2026-09-27, delivery order step 2) asks for one declaration of what each lifecycle tier is called and how its records are named. The goal is that a fork with a different vocabulary can run Wavefoundry unmodified, for example a container record `set.md` with `set-id:`, a `## Waves` member list, `Wave ID:` and `Wave Status:` labels, and a `## Set Summary`.

A census on 2026-09-27 found no single owner for any record marker:

- The container record filename `wave.md` is spelled inline at about 40 logic sites across 18 modules.
- Header patterns are duplicated with *different* grammars. `constants.CHANGE_ID_PATTERN` is strict and anchored. `lifecycle_gate_support._CHANGE_ID_PATTERN` is unanchored. `commit_provenance._CHANGE_ID_RE` is case-insensitive. `server_impl._CHANGE_STATUS_PATTERN` already accepts the legacy `Item Status`. `dashboard_lib._WAVE_RE` requires backticks around the back-reference, while `docs_constants_validators._WAVE_FIELD_RE` does not.
- Discovery passes silently: a waves root whose folders hold the record under another filename yields zero waves with no diagnostic.
- `gardener_metadata._REVIEW_TRACKING_STATUS_LINE_RE` (`^(?:Change )?Status:`) excludes status lines from the review-policy digest. Under another member-status label, every status advance would change the digest and lapse approvals.

This change is the first of two in the wave. It adds the profile and routes every **reader**. Change `1z8qi` routes the writers and proves a second profile end to end.

The operator confirmed on 2026-09-27 that the profile is a fork-edited code module, the way `record_paths` works today.

## Requirements

1. **Which tokens are vocabulary (the derivation rule).** A record-format token is vocabulary when its text embeds a tier name or is the container record filename; every other token is fixed. The in/out table below applies that rule and is the authority for this change and `1z8qi`.
2. **One owner.** A stdlib-only, fork-editable module `vocabulary_profile.py`, a flat sibling of `record_paths.py`, declares module constants for every vocabulary token, with today's values as defaults. It also derives the dependent forms: `Previous <member status label>` and the regex-escaped fragment for each label and heading. It exports strings and escaped fragments, not whole patterns. Each consuming site keeps its own grammar (anchoring, backticks, case sensitivity, legacy aliases) around the fragment, so the default profile changes no match. Duplicate patterns collapse only where they are character-identical today (`constants.WAVE_ID_PATTERN` and `constants.WAVE_REFERENCE_PATTERN`).
3. **Validation fails closed.** On import the module validates the profile and raises a named error for:
   - an empty token;
   - two vocabulary labels or headings that are equal, or where one is a prefix of another before `:`;
   - a vocabulary label or heading equal to a fixed heading, a fixed metadata key or a legacy alias (`## Items`, `Item ID`, `Item Status`);
   - a record filename that is not a `.md` name, or is (case-insensitively) `README.md`, `plan-template.md` or `events.jsonl`.
4. **Readers route through it.** Every production site outside `tests/` that parses or discovers a vocabulary token uses the profile. That includes:
   - discovery in `record_paths`;
   - docs-lint (`wave_lint_lib`, required-section lists included);
   - the server's readers and resolvers;
   - `review_evidence` record lookups;
   - `review_policy`;
   - memory (backfill, supply, records);
   - `context_efficiency` and its handlers;
   - the dashboard server and library;
   - `commit_provenance`, `lifecycle_gate_support` and `lifecycle_gates`;
   - `review_policy_upgrade`;
   - `gardener_metadata`: its carrier keys, and its status-line digest exclusion, which is derived from the member-status label.
5. **Census.** A test mirroring `tests/test_record_layout_census.py` scans every production module (outside `tests/` and `vocabulary_profile.py`) for each default vocabulary *marker* (the record filename, id key, title, labels, headings and back-reference; not the bare tier names, which occur throughout prose) as a boundary-aware substring of source lines and string constants, f-string parts included, so `upgrade-wave.md` does not match. Every hit is classified in a table (construction, parse, message, comment, docstring, frozen oracle) with an allow-list keyed on file and snippet. Construction and parse hits fail unless routed.
   - Frozen historical oracles are allow-listed, not routed: `upgrade_extensions._pristine_journal_template` and `_migrate_journals` handle retired journals byte-exactly.
   - Detection is proven with one planted control per shape: equality, f-string, regex source and concatenation.
   - Writer sites that `1z8qi` routes are allow-listed here under a named "pending 1z8qi" class. `1z8qi` removes that class.
6. **Discovery diagnostic, advisory.** When the configured waves root has candidate folders but none holds the profile's record file, `list_waves` and `wf_current_wave` add an envelope diagnostic naming the expected filename. Docs-lint emits a warning registered as `advisory` in `constants.SENSOR_POLARITY_REGISTRY`. A root with no candidate folders (a fresh install) is silent. Known limits, stated in the diagnostic's docs: a mixed state (some folders renamed) is not detected, and nested grouping folders or non-wave helper folders can trip it.
7. **Dashboard labels.** The profile's tier names are the default dashboard labels. `dashboard.terminology` keeps working as an override for one release and is documented as superseded.
8. **Registrations.** Add the module to:
   - the server reload purge set, next to `record_paths` and `marker_namespaces`;
   - `test_server_package.RETAINED_DECLARATIONS`;
   - `index_compatibility._SOURCE_NAMES`, only if an indexer, chunker or graph module imports it.

   Upgrade-time modules import it lazily inside a guard, as they do for other siblings. `record_paths` imports it at module level (both are stdlib-only flat siblings), and that edge is recorded.

**Vocabulary (routed; defaults shown).** Container:

| Token | Default |
| --- | --- |
| Record filename | `wave.md` |
| Id key | `wave-id:` |
| Record title | `# Wave Record` |
| Summary heading | `## Wave Summary` |

Work item:

| Token | Default |
| --- | --- |
| Member-list heading | `## Changes` |
| Id label | `Change ID:` |
| Status label | `Change Status:` |
| Derived previous-status label | `Previous Change Status:` |
| Back-reference label (change docs and plan overviews) | `Wave:` |

Tier names (singular and plural): Wave / Waves, Change / Changes.

**Fixed (not routed):**

- `events.jsonl` and the `review-evidence-source: events.jsonl` declaration;
- `<!-- wave:* -->` marker fences (owned by `marker_namespaces`);
- the headings `## Participants`, `## Objective`, `## Dependencies`, `## Watchpoints`, `## Journal Watchpoints`, `## Finding Synthesis`, `## Review Evidence`, `## Review Checkpoints`, `## Context Efficiency` and `## Progress Log`;
- the keys `Depends On:`, `Title:`, `Status:`, `Completed At:` and `Closed At:`;
- `wave-council-*` lane names, MCP response keys (`wave_id`), change-kind tokens and lifecycle-id kinds, and the folder-name grammar `<id> <slug>`;
- the legacy aliases `## Items`, `Item ID` and `Item Status`;
- the session-handoff `Active wave` lines;
- the `dashboard.js` status regex, which falls back to the plain `Status:` line;
- seed and prompt prose.

## Scope

**Problem statement:** record names are spelled inline across the framework. A different vocabulary needs about 100 edits, and a mismatch is found as zero records rather than as an error.

**In scope:**

- the profile module and its validation;
- routing every reader;
- the census with the pending-writer class;
- the advisory discovery diagnostic;
- dashboard label defaults;
- registrations and docs.

**Out of scope:**

- writers, scaffolds, the Stop-hook emitter and the end-to-end second-profile test (`1z8qi`);
- `is_canonical_wave_events_path` (`1z8qj`);
- tool-name aliases and the parent tier (later RFC steps);
- the read-only archive root (`1z827`);
- migrating records between profiles.

## Acceptance Criteria

- [x] AC-1: with the default profile, no existing test changes except additions (checked as a diff of `tests/` limited to added lines), and every reader returns the same result as before on this repository's records: the same wave list, change parse, lint result and review-policy digest.
- [x] AC-2: with a second profile applied in a fresh interpreter over a copied scripts tree, the readers each find a hand-written record set under the second profile's names with non-zero counts: discovery, docs-lint, `wf_get_change`, dashboard parsing and memory backfill. A status advance under the second profile's status label leaves the review-policy digest unchanged.
- [x] AC-3: the census fails on each planted control shape (equality, f-string, regex source, concatenation) outside the profile module and passes on the tree.
- [x] AC-4: a waves root whose folders hold a record under another filename produces the advisory diagnostic from `list_waves`, `wf_current_wave` and docs-lint; a root with no candidate folders produces none.
- [x] AC-5: each validation rule in Requirement 3 refuses a profile violating it, with a diagnostic naming the field.
- [x] AC-6: the change's own suites and every test it adds pass, and the documents this change edits validate.

## Tasks

- [x] `vocabulary_profile.py`: constants, derived forms, escaped fragments and validation.
- [x] Route readers by module: `record_paths`; `wave_lint_lib` (`constants`, `wave_validators`, `docs_constants_validators`, `cli`); `server_impl` readers and handlers; `review_evidence` lookups; `review_policy` and `review_policy_upgrade`; memory backfill, supply and records; `context_efficiency` and its handlers; `dashboard_lib` and `dashboard_server`; `commit_provenance`, `lifecycle_gate_support` and `lifecycle_gates`; `gardener_metadata`
- [x] Census test with a classification table, a pending-writer class and four planted controls.
- [x] Advisory discovery diagnostic and its sensor registration; dashboard label defaults.
- [x] Registrations: purge set, `RETAINED_DECLARATIONS`, and `_SOURCE_NAMES` if needed.
- [x] Second-profile reader test (subprocess, copied tree).
- [x] Docs: `docs/architecture/layering-rules.md`: single-owner stdlib modules become five, and the `record_paths` to `vocabulary_profile` edge; `docs/architecture/current-state.md`; `docs/specs/mcp-tool-surface.md`: the diagnostic; `docs/references/dashboard-adapter-model.md`: the terminology supersession; CHANGELOG `[Unreleased]`

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Profile and readers | implementer | readiness | Profile module first; the census gates completion |
| Review | combined reviewer | Profile and readers | Code, QA, architecture, docs-contract |

## Serialization Points

- `.wavefoundry/framework/scripts/vocabulary_profile.py`, `.wavefoundry/framework/scripts/record_paths.py`, `.wavefoundry/framework/scripts/wave_lint_lib/`, `.wavefoundry/framework/scripts/wf_server/`, `.wavefoundry/framework/scripts/review_evidence.py`, `.wavefoundry/framework/scripts/review_policy.py`, `.wavefoundry/framework/scripts/gardener_metadata.py`, `.wavefoundry/framework/scripts/dashboard_lib.py`, `.wavefoundry/framework/scripts/tests/`
- `docs/architecture/layering-rules.md`, `docs/architecture/current-state.md`, `docs/specs/mcp-tool-surface.md`, `docs/references/dashboard-adapter-model.md`
- `CHANGELOG.md` (shared by the changes in this wave)

## Affected Architecture Docs

`docs/architecture/layering-rules.md` and `docs/architecture/current-state.md`. A fifth stdlib-only single-owner module is added, and `record_paths` gains an import edge to it.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Existing users must see no change |
| AC-2 | required | Readers must actually follow the profile |
| AC-3 | required | Keeps the single owner from eroding |
| AC-4 | important | Removes the silent zero-discovery case |
| AC-5 | required | Fail closed on a bad profile |
| AC-6 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-27 | Combined review round 1 (code, QA, architecture, docs-contract and readiness recheck): readiness, architecture and docs-contract approved; code and QA requested changes on B1, Requirement 3's prefix rule was not enforced. Repaired: `validation_errors` refuses a heading or label that is a prefix of another vocabulary token or of a fixed one, with one refusal test per case. Non-blocking notes also taken: the census matcher tolerates backslash-escaped markers, with a planted escaped control and its alternation limit stated (N1, N3); the `wf_get_change` reader test gains the lookup by wave, which only the profile finds (N2); the diagnostic's limits are stated in `mcp-tool-surface.md` (N5); the terminology register is documented as superseded (N4); 1z8qi scope and limits wording (N6, N8); test docstring wave ids (N7) | review report; `test_vocabulary_profile`, `test_vocabulary_census`, `test_vocabulary_second_profile` |
| 2026-09-27 | Implemented. The profile module and every reader are routed; `record_paths.record_discovery_mismatch` and the advisory `record_file_not_found` sensor (registered with a recorded decision, since it is a heuristic with stated limits) reach docs-lint, `wf_list_waves` and `wf_current_wave`; dashboard terminology defaults come from the tier names. Registrations: the server purge set and `RETAINED_DECLARATIONS`; `index_compatibility._SOURCE_NAMES` is unchanged because `record_paths` is not listed there either (neither changes an index build). AC-1 note: the `tests/` diff adds lines only, except four pinned sets that must name a new sibling or sensor: `RETAINED_DECLARATIONS`, the recorded-decision sensor set in `test_docs_lint`, the `record_paths` stdlib-import set in `test_record_paths` (a new test pins `vocabulary_profile` itself as stdlib-only), and the delegated-producer module list in `test_upgrade_wavefoundry`. No assertion about behavior changed. Found in passing, not changed: the `_tag_utils` by-path fallback for loading `record_paths` has failed since wave `1y0gz` (a path-loaded dataclass module is not in `sys.modules`), and `chunker` cannot load by path without the scripts directory on `sys.path` anyway, so the fallback is unreachable | `test_vocabulary_census` (four planted shapes, stale-entry and no-unrouted-site checks), `test_vocabulary_profile` (each validation rule, the discovery diagnostic from all three surfaces, fresh-install silence), `test_vocabulary_second_profile` (discovery, lint, `list_waves`, `wf_get_change`, dashboard, memory backfill and digest under a second profile, each with a default-tree control that finds nothing or reads differently); `docs-lint: ok` on this repository |
| 2026-09-27 | Gapfill: the marker census was taken with `rg` over the scripts tree rather than `code_keyword`, because `code_keyword` caps its results and its `**/*.py` glob skips top-level scripts (logged in the tool-quality log); the census test now re-derives the same predicate on every run | this entry |
| 2026-09-27 | Readiness round 1 requested changes; all adopted. B1: collapsing grammatically different regexes would change behavior, so the profile exports fragments and each site keeps its grammar. B2: an equality census is vacuous against f-strings and regex sources, so it now mirrors the record-layout census with four planted shapes. B3: the Stop-hook emitter (now `1z8qi`) imports the profile at runtime. B4: the events-path fix moved to its own bug `1z8qj` and stays content-free. B5: a derivation rule and an in/out table, adding the review-policy status-line exclusion (verified at `gardener_metadata._REVIEW_TRACKING_STATUS_LINE_RE`), `Previous Change Status`, the record title and the plan `Wave:` overview. Notes folded in: an advisory sensor with stated limits (N1), a subprocess second-profile test (N2), AC-1 as a tests-diff check (N3), registrations (N4), the fuller collision rules (N5) and real doc paths (N6). The change is split per N7 | readiness review |
| 2026-09-27 | Planned from the RFC's delivery order step 2 after a census | census report |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-27 | Profile is a fork-edited module, not a `workflow-config.json` block (RFC open question 1; confirmed by the operator on 2026-09-27: "code module the way it works today") | Matches record roots (`record_paths`), is read at import by every process including hooks, and has no per-repository drift | A validated config block |
| 2026-09-27 | Export fragments, not whole patterns | The duplicate regexes differ in anchoring, case and aliases; one shared pattern would change current matches | Collapse all duplicates |
| 2026-09-27 | Split readers (this change) from writers (`1z8qi`) and the events-path leak (`1z8qj`) | About 20 modules; separable review; the leak is independent and shippable alone | One change for everything |

## Risks

| Risk | Mitigation |
| --- | --- |
| A missed reader keeps a literal | Census with shape controls plus the second-profile reader test |
| Upgrade-time imports of a new sibling break old runners | The upgrade runner's imports of routed siblings (`memory_backfill`, `review_policy_upgrade`) are already lazy and run after the new tree, which ships the profile, is installed; the delegated-producer module set names it |
| Digest drift under a second profile | Exclusion derived from the profile's status label, tested in AC-2 |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
