# Vocabulary Profile for Record Names

Change ID: `1z826-feat vocabulary-profile-record-names`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-27
Wave: TBD

## Rationale

The RFC "Vocabulary profiles and an optional parent tier" (2026-09-27, delivery order step 2) asks for one declaration of what each lifecycle tier is called and how its records are named, so a fork with a different vocabulary can run Wavefoundry unmodified. A census on 2026-09-27 found no single owner for any record marker:

- The container record filename `wave.md` is spelled inline at 40 logic sites across 18 modules, including the discovery predicate `record_paths._has_wave_md` and code emitted into the Claude Stop hook by `render_platform_surfaces.claude_stop_source`.
- The header patterns are duplicated: `wave-id:` in three regexes (`wave_lint_lib/constants.py`, `server_impl._WAVE_ID_PATTERN`), `Change ID:` in four (`constants.py`, `lifecycle_gate_support._CHANGE_ID_PATTERN`, `memory_supply`, `commit_provenance`), and `Change Status:` in two.
- `## Changes`, `## Wave Summary` and the change-doc `Wave:` back-reference are parsed in the linter and written by hard-coded strings in `server_impl.create_wave`, `_insert_change_block_into_changes_section`, `_replace_wave_summary_section`, `wf_close_wave_response` and `wf_add_change_response`, and by `install/plan-template.md`.
- Dashboard tier labels come from `dashboard_lib.read_dashboard_config` (`dashboard.terminology`).

Discovery also passes silently. `discover_wave_dirs` returns an empty list when a root holds folders whose record has another name. Nothing reports an error unless a folder happens to carry a non-empty `events.jsonl`, in which case `check_orphan_wave_ledgers` fires. `list_waves` returns an empty list with no diagnostic. And `review_evidence.is_canonical_wave_events_path` hard-codes `docs/waves` at depth four, ignoring `record_paths.WAVES_ROOT` and `NESTED`, which is a pre-existing layout leak.

## Requirements

1. **One owner for record names.** A stdlib-only, fork-editable module `vocabulary_profile.py`, in the style of `record_paths.py` (module constants, validated on import, no configuration file), declares:
   - the container and work-item tier names, singular and plural;
   - the container record filename;
   - the container id key;
   - the member-list heading;
   - the member id and status labels;
   - the summary heading;
   - the work-item back-reference label.

   Every default is today's value (`wave.md`, `wave-id:`, `## Changes`, `Change ID:`, `Change Status:`, `## Wave Summary`, `Wave:`). The module also exports the compiled patterns built from those names. It rejects a profile whose names collide (for example the member-list heading equal to the summary heading), are empty, or cannot be matched unambiguously, naming the field.
2. **Every reader and writer goes through it.** The set is derived by rule: every production site outside `tests/` that parses, discovers, creates or renders one of these markers, including code emitted into rendered hooks and the change-doc template, uses the profile's names or patterns instead of a literal. The duplicated regexes collapse into the profile's patterns. Legacy synonyms that exist today (`## Items`, `Item ID`, `Item Status`) stay accepted as fixed aliases alongside the profile's names.
3. **A census test forbids new literals.** A test parses every production module and fails on any string literal equal to one of the profile's default markers outside `vocabulary_profile.py`, with a small, named allow-list for diagnostic prose. It proves detection by planting a literal in a scratch copy, the same pattern as the existing path-containment census.
4. **Discovery fails closed.** When the configured waves root contains candidate folders but none holds the profile's record file, `list_waves`, docs-lint and `wf_current_wave` report a named diagnostic that says so and names the expected filename, instead of an empty success.
5. **The layout leak is closed.** `review_evidence.is_canonical_wave_events_path` derives its root and depth from `record_paths` and its record name from the profile.
6. **Dashboard labels come from the profile.** The profile's tier names are the default dashboard labels. `dashboard.terminology` keeps working as an override for one release and is documented as superseded.
7. **The default profile changes nothing.** With no edits to `vocabulary_profile.py`, rendered surfaces, records, lint results, tool names and every existing fixture are unchanged.

## Scope

**Problem statement:** record names are spelled inline across the framework, so a different vocabulary needs about 100 edits, and a mismatch is found as zero records rather than as an error.

**In scope:**

- `vocabulary_profile.py` and its validation;
- routing every production reader and writer of the markers through it, including rendered hook code and `install/plan-template.md`;
- the census test, the fail-closed discovery diagnostic, the `is_canonical_wave_events_path` fix, and dashboard label defaults.

**Out of scope:**

- tool-name aliases (RFC section 4.3);
- the parent tier (RFC section 5);
- the read-only archive root (change `1z827`);
- renaming lifecycle-id kind tokens (`wave` in `lifecycle_id`), since ids are persistent;
- migrating existing records between profiles;
- seed and prompt prose that mentions `wave.md` (46 and 10 mentions). The rendered prose stays in the default vocabulary; a fork re-words its own prompts.

## Acceptance Criteria

- [ ] AC-1: with the default profile, the full suite passes with no fixture changes, and a rendered target is byte-identical to one rendered before the change.
- [ ] AC-2: with a second profile (different filename, id key, headings and labels), a scratch repository's lifecycle runs end to end: create a wave, admit a change, prepare, record review evidence, and close. Explicit assertions check that the wave is discovered, its change is parsed and its record is written under the profile's names, and the counts are not zero.
- [ ] AC-3: the census test fails when a planted marker literal appears outside `vocabulary_profile.py`, and passes on the tree.
- [ ] AC-4: a waves root whose folders hold a record under a different filename produces the named discovery diagnostic from `list_waves` and docs-lint, not an empty success.
- [ ] AC-5: `is_canonical_wave_events_path` accepts a ledger under a relocated `WAVES_ROOT` and a nested layout, and rejects one outside it.
- [ ] AC-6: an invalid profile (colliding headings, an empty name) refuses to load with a diagnostic naming the field.
- [ ] AC-7: the change's own suites and every test it adds pass, and the documents this change edits validate.

## Tasks

- [ ] `vocabulary_profile.py` with defaults, patterns and validation.
- [ ] Route the census sites by module:
  - record_paths;
  - wave_lint_lib;
  - server_impl and the handlers;
  - review_evidence;
  - memory_backfill, memory_supply and memory_records;
  - context_efficiency;
  - dashboard_lib and dashboard_server;
  - commit_provenance and lifecycle_gate_support;
  - gardener_metadata;
  - review_policy_upgrade;
  - the render_platform_surfaces emitted code;
  - install/plan-template.md.
- [ ] Discovery diagnostic; `is_canonical_wave_events_path` fix; dashboard label defaults.
- [ ] Census test with a planted-literal control; the second-profile end-to-end test; the default-profile render comparison.
- [ ] Docs: `docs/architecture/current-state.md` (record naming owner), `docs/specs/mcp-tool-surface.md` (the diagnostic), and the fork guide. CHANGELOG `[Unreleased]`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Profile module | implementer | readiness | Defines names and patterns first |
| Routing | implementer | Profile module | Module by module; the census test gates completion |
| Tests and docs | implementer | Routing | Second-profile lifecycle test is the main oracle |
| Review | combined reviewer | Tests and docs | Code, QA, architecture, docs-contract |

## Serialization Points

- `.wavefoundry/framework/scripts/record_paths.py`, `.wavefoundry/framework/scripts/wave_lint_lib/`, `.wavefoundry/framework/scripts/wf_server/`, `.wavefoundry/framework/scripts/review_evidence.py`, `.wavefoundry/framework/scripts/dashboard_lib.py`, `.wavefoundry/framework/scripts/render_platform_surfaces.py`, `.wavefoundry/framework/install/plan-template.md`, `docs/architecture/current-state.md`, `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

`docs/architecture/current-state.md` and `docs/architecture/layering-rules.md`: a new flat sibling owns record names, next to `record_paths` (roots) and `marker_namespaces`. Record the ownership edge and the census.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Existing users must see no change |
| AC-2 | required | The feature's purpose |
| AC-3 | required | Keeps the single owner from eroding |
| AC-4 | required | Removes the vacuous-pass failure mode |
| AC-5 | required | Pre-existing leak that the profile would otherwise inherit |
| AC-6 | important | Fail closed on a bad profile |
| AC-7 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-27 | Planned from the RFC's delivery order step 2. A read-only census (a `guru` subagent: ripgrep plus an AST attribution script, because `code_keyword` with a `**/*.py` glob skipped top-level scripts) found 40 logic sites for `wave.md` in 18 modules, duplicated header regexes, code-string scaffolds in `server_impl.create_wave`, silent zero-discovery, and the `is_canonical_wave_events_path` layout leak | census report |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-27 | Profile is a fork-edited module, not a `workflow-config.json` block (RFC open question 1; needs operator confirmation) | Matches the existing decision for record roots (`record_paths` constants, wave `1y0gz`): read at import by every process including hooks and the upgrade runner, with no config parse on hot paths and no per-repository drift | A validated config block (per-repository flexibility, but a second source of truth next to `record_paths` and config reads in hooks) |
| 2026-09-27 | Record names only in this change; tool aliases and the parent tier later | The census shows record names alone touch about 18 modules; bundling aliases or a new tier would make review unmanageable | One change for the whole RFC |
| 2026-09-27 | Keep legacy synonyms as fixed aliases | They exist for old records and are not vocabulary | Route them through the profile too |

## Risks

| Risk | Mitigation |
| --- | --- |
| A missed site keeps a literal and breaks a second profile silently | The census test plus the second-profile lifecycle test with non-zero count assertions |
| Emitted hook code and templates drift from the profile | They are generated from the profile at render time, and the census covers the emitter |
| Performance of pattern construction on hot paths | Compile once at import |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
