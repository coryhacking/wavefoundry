# Vocabulary-Derived Lifecycle Prompt and Skill Names

Change ID: `1zxnw-enh vocabulary-derived-prompt-names`
Change Status: `implemented`
Owner: framework-operator
Status: planned
Last verified: 2026-10-06
Wave: 1zyb4 vocabulary-derived-names

## Rationale

Waveforge, a downstream distribution, renames the two lifecycle tiers through `vocabulary_profile.py` (container "Set", item "Wave"). That profile covers record markers only (wave 1z8mm): its docstring says a token is vocabulary "when its text embeds a tier name", yet the tier-named lifecycle prompt files, shortcuts and skills (`create-wave`, `implement-change`, **Close wave**, `wf-prepare-wave` and so on) are literals spread over eight framework modules. A distribution that wants **Implement set** for its container and **Implement wave** for its item must patch every literal at each merge, and some of them feed migrations and lint, so a partial patch breaks targets.

Code-grounded facts this plan relies on:

- `vocabulary_profile.py` is fork-edited constants, "Nothing is read from configuration", validated at import (`validate()`), failing closed. The test profile machinery (`tests/record_layout_support.apply_profile`) replaces each editable constant with a one-line regex (`^NAME ... = <rest of line>`), so an editable constant must be a single-line assignment; `SHIPPED_DEFAULTS` freezes the shipped values. `run_tests.py --profile NAME` runs the suite (or a `--file` selection) in a scratch copy with any asset under `tests/fixtures/profiles/` applied, so a new asset needs no runner change.
- Prompt destinations are literals in `render_agent_surfaces.py` (`CONTEXT_EFFICIENCY_DESTINATION`, `LIFECYCLE_PROMPT_BASELINES`, the `SKILL_REGISTRY` bodies via `_thin_pointer_body(title, prompt_doc, ...)`, `CLOSE_CHANGE_PROMPT`, `CLOSE_CHANGE_SHORTCUT`, the create-wave pointer body at the `carrier.destination ==` check), `review_policy.py` (`REVIEW_POLICY_SURFACE_BLOCKS` keys and `REVIEW_POLICY_CARRIER_REGISTRY` destinations), `review_policy_reconcile.py` (four path-keyed dict entries), `context_efficiency.LIFECYCLE_PROMPT_MAP`, `wave_lint_lib/constants.PROMPT_SURFACE_FILES`, `wave_lint_lib/core_validators.check_review_policy_carriers` (three paths) and `reconcile_scan.py` (suggestion strings). `Skill` has no `prompt_doc` field: the doc path is an argument of `_thin_pointer_body`.
- The 1zyc5 migration (`migrate_change_prompt_renames`, `_repair_change_prompt_manifest`) moves prompts byte-for-byte and repairs `public_prompt_surface` entries; it adds a Close change entry whenever no entry has `doc == CLOSE_CHANGE_PROMPT`. If a profile moved that prompt and the constant stayed literal, every render would re-add a stale entry, so these constants must be derived too.
- Waveforge's names form chains, not just renames: its item prompt **Implement wave** takes the file name `implement-wave.prompt.md` that today holds the container prompt, which itself moves to `implement-set.prompt.md`. A file name alone therefore cannot tell a migration whether `implement-wave.prompt.md` is the unmigrated container prompt or the migrated item prompt; the migration needs a record of the names already applied.
- `REVIEW_PLAN_OLD_PROMPT`/`REVIEW_PLAN_NEW_PROMPT` and `RETIRED_FINALIZE_PROMPT` name `review-plan`, `interrogate-plan` and `finalize-feature`, none of which embeds a live tier name; `UPGRADE_POLICY_DESTINATION` names the product (`upgrade-wavefoundry`), not a tier.

## Requirements

1. **Profile map.** Add to `vocabulary_profile.py`:
   - a fixed (not edited) table `DEFAULT_PROMPT_NAMES` of exactly the eleven tier-named lifecycle prompts, keyed by today's slug, each with `slug`, `shortcut` and `aliases`: `plan-change` (Plan change), `create-wave` (Create wave), `add-change-to-wave` (Add change to wave), `remove-change-from-wave` (Remove change from wave), `prepare-wave` (Prepare wave, alias Ready wave), `implement-wave` (Implement wave), `implement-change` (Implement change), `pause-wave` (Pause wave), `review-wave` (Review wave), `close-wave` (Close wave), `close-change` (Close change);
   - one fork-edited single-line constant `PROMPT_NAME_OVERRIDES: "dict[str, dict[str, object]]" = {}` mapping a key to `{"slug": ..., "shortcut": ..., "aliases": [...]}` (aliases optional, default none; list or tuple accepted so a JSON profile asset applies);
   - derived `PROMPT_NAMES` (defaults overlaid with overrides) and helpers `prompt_doc(key)` (`docs/prompts/<slug>.prompt.md`), `agent_prompt_doc(key)` (`docs/prompts/agents/<slug>.prompt.md`), `skill_name(key)` (`wf-<slug>`), `shortcut(key)`, `shortcut_aliases(key)`.
   With the shipped empty overrides every derived value equals today's literal.
2. **Validation at import.** `validate()` also refuses, naming `PROMPT_NAME_OVERRIDES` and the key: an unknown key; a slug not matching `^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$` or longer than 64 characters; two keys with the same slug; a slug equal to a fixed framework prompt slug (a fixed tuple `FIXED_PROMPT_SLUGS`: the untiered prompts `review-plan`, `memory-review`, `council-review`, `archetype-council`, `red-team-review`, `evaluate-decision`, `refresh-techdocs`, `codebase-cleanup-review`, `package-wavefoundry`, `install-wavefoundry`, `upgrade-wavefoundry`, `framework-config-review`, `agent-routing-concurrency`, `start-dashboard`, `stop-dashboard`, `restart-dashboard`, the agent bodies `init-wave-context`, `upgrade-wave-context`, `performance-reviewer` and `security-reviewer` (all present under `docs/prompts/agents/`), the retired `interrogate-plan`, `plan-feature`, `implement-feature`, `finalize-feature`, and `index`); a derived skill name equal to a fixed registry skill (a fixed tuple `FIXED_SKILL_NAMES`, copied because `vocabulary_profile` cannot import the renderer) or a `STALE_SKILL_PATHS` name; a shortcut or alias that is empty, multi-line, padded, longer than 64 characters, or contains `` ` ``, `*`, `|`, `[` or `]`; two shortcuts or aliases equal case-insensitively, including against a fixed tuple `FIXED_PROMPT_SHORTCUTS` of the framework's untiered shortcuts; and a rename cycle (a key whose slug is another key's default slug, transitively back to itself). A chain (container `implement-wave` to `implement-set` while item `implement-change` takes `implement-wave`) is valid.
3. **Every consumer reads the map.** Replace each literal in the census (Scope) with the profile helpers: `CONTEXT_EFFICIENCY_DESTINATION`, the `LIFECYCLE_PROMPT_BASELINES` destinations (template file names stay as they are: they are framework-internal sources), the create-wave pointer-body check, `CLOSE_CHANGE_PROMPT`, `CLOSE_CHANGE_SHORTCUT` (see Requirement 6 for which name the 1zyc5 manifest repair uses), `REVIEW_POLICY_SURFACE_BLOCKS` keys and the title-case names in their texts ("Prepare Wave is the single readiness authority", "Review Wave consumes", "Close Wave consumes", rendered from the shortcut in title case), `REVIEW_POLICY_CARRIER_REGISTRY` destinations, the `review_policy_reconcile.py` path keys, `LIFECYCLE_PROMPT_MAP` values, `PROMPT_SURFACE_FILES`, the three `check_review_policy_carriers` paths, the `reconcile_scan.py` replacement suggestions (`_RETIRED_CHANGE_PROMPT_PATTERNS` new names, `_RETIRED_FINALIZE_PROMPT_SUGGESTION`, `_CLOSE_CHANGE_OR_WAVE_SUGGESTION`, the guru description suggestion), and the two scaffold or message sites (`server_impl.create_wave` "roles selected during Prepare wave", `wave_validators` "relocate during Prepare wave"). Retired old names (`plan-feature`, `finalize-feature`, `interrogate-plan`) stay literal; `CHANGE_PROMPT_RENAMES` keeps moving feature names to the default change names, and the profile migration (Requirement 6) moves them on, so one render performs both steps. `REVIEW_POLICY_OBLIGATION_ANCHORS["single_prepare"]`, today `("prepare wave", "prepare is the single")`, becomes the tier-neutral `("is the single readiness authority", "prepare is the single")`, so the carrier obligation check needs no profile; both rendered blocks that carry the obligation contain that phrase.
4. **Names in renderer-owned text.** Every renderer-owned string that names a mapped prompt, shortcut or skill renders it from the map: `SKILL_REGISTRY` names, descriptions and bodies (for example "The Prepare wave / Ready wave workflow.", "Single-change variant: Implement change (`docs/prompts/implement-change.prompt.md`).", the `wf-council` and `wf-review-plan` references to Review wave and `wf-review-wave`), the Cursor `auto-guru.mdc` template, the Claude guru agent template description, and the framework-owned review-policy region texts that name a mapped shortcut in bold. Only replacement-side strings are derived (the text the renderer or reconciler writes, including bold and backticked names); legacy matchers, the old-side strings of `KNOWN_SECTION_REPLACEMENTS` and the retired-name patterns in `reconcile_scan.py`, stay literal because they must match text written by earlier releases. Only names are derived; ordinary prose words such as "wave" or "change" are not rewritten (the record profile does not rewrite prose either).
5. **Materialized baselines.** When a lifecycle baseline template or the create-wave pointer body is materialized (missing-only, as today), it is written at the derived path, and a new `localize_prompt_template(key, text)` rewrites only its line-1 `# ` heading (the shortcut in title case, which reproduces today's headings) and its `Shortcut:` line (shortcut and aliases). It is the identity under defaults, byte for byte, including the singular `| Alias:` form of the prepare-wave Shortcut line and the plural `| Aliases:` form where a template has several. Other body text is not rewritten.
6. **Migration of rendered files.** Add `migrate_profile_prompt_names(repo_root)` to `render_agent_surfaces.py`, called immediately after `migrate_change_prompt_renames` and before skills and baselines render:
   - Applied names are read from a new optional `prompt_names` object in `docs/prompts/prompt-surface-manifest.json` (key to applied slug, listing only keys that differ from the default; absent means every key is at its default). The target names are the current `PROMPT_NAMES`.
   - For each key whose applied slug differs from its target slug, the public prompt and the agent body each form a pair (applied path to target path). A pair whose source is absent is complete. A pair whose source exists and whose target is absent moves. A pair whose source and target both exist is allowed when the target is the source of another pair in the same plan (a chain), or when the two files are byte-identical and the target is not another pair's source (a copy completed before a crash; the migration then only unlinks the source); otherwise it is a conflict, as are a symlinked, non-regular or uncontained source (`_contained_review_carrier_path`) and a cycle in the plan.
   - The whole plan is preflighted before any write; any conflict raises one `RuntimeError` naming every conflicting pair, saying all files were preserved, and writing nothing (no move, no manifest write, so no skill or baseline render), as `migrate_change_prompt_renames` does.
   - Moves run in dependency order (a pair whose target is another pair's source waits for that pair), each by exact byte copy with exclusive create and then unlink of the source, with the existing rollback when the unlink fails. After both pairs of a key complete, the manifest is rewritten once: the key's `public_prompt_surface` entry gets the target `doc` and `shortcut`, and `prompt_names` records the key (or drops it when it is back at its default; the object is removed when empty). Recording per key before the next move starts is what makes a rerun after a crash at any point converge.
   - `_repair_change_prompt_manifest` (1zyc5) runs before this migration in the same render, so its Close change check uses the APPLIED name of key `close-change` (the manifest's `prompt_names` entry, the default when absent), not the target name: an entry is added only when no entry has that applied `doc`, and the migration then moves it. Using the target name would add a duplicate entry while a close chain is partly applied, for example after a crash.
   - When the manifest is absent or unparseable, nothing is moved and the render result carries a diagnostic; docs-lint already requires the manifest.
   - Prompt content is never rewritten. Markdown links to moved paths are reported as `file:line` through the existing `_moved_prompt_link_report` walk, generalized to the moved set.
   - Under defaults with no `prompt_names` key the function writes nothing.
7. **Skills.** Registry skills render under derived names. The default skill paths (`<host>/skills/wf-<default slug>/SKILL.md`) of every overridden key join the stale set removed on render, except a path that is also a current derived skill path (a chain reuses it and the render overwrites it).
8. **Lint.** `PROMPT_SURFACE_FILES` checks derived paths. A new docs-lint check reports a pending migration when the manifest's applied names (absent means defaults) differ from `PROMPT_NAMES`, naming the keys and the remedy (`wf render-surfaces`); silent under defaults with no key.
9. **Reconcile scan.** Under a non-default profile, `reconcile_scan` reports each overridden key's default public path, agent path, skill name and shortcut-shaped phrase (bold or backticked, as the 1zyc5 table does), and the bare phrase on the `.claude/agents/guru.md` `description:` line, each with the derived suggestion. A default token that equals any current derived token (the chain case) is never reported. Under defaults the scan reports nothing new.
10. **Seeds and catalog.** Seed text keeps the default names. Seed 100 and seed 160 each gain one paragraph: the names in the seed are framework defaults; a distribution may rename the tier-named lifecycle prompts through its vocabulary profile; the renderer moves default-named prompts and records the applied names under `prompt_names` in the manifest; when that key is present, author or reconcile each listed prompt (file, heading, Shortcut line, `docs/prompts/index.md` row, AGENTS.md shortcut row) at its listed name, otherwise use the defaults; repair each reconcile finding. The rendered `docs/prompts/upgrade-wavefoundry.prompt.md` carries the seed 160 paragraph.
11. **Zero change under defaults.** With the shipped empty overrides, a render of this repository writes nothing, every derived constant equals its pre-change literal, and the reconcile scan, docs-lint, the handler-digest fixture and the tool-surface goldens are unchanged.
12. CHANGELOG: one Unreleased entry describing `PROMPT_NAME_OVERRIDES`, the migration and its `prompt_names` record, the lint check, and that nothing changes under defaults.

## Scope

**Problem statement:** a distribution cannot rename the tier-named lifecycle prompts, shortcuts and skills without patching literals in eight modules, and a partial patch breaks migrations and lint in its targets.

**In scope:**

- The profile map, validation and helpers (Requirements 1 and 2); every consumer in the census (Requirements 3 to 5 and 7 to 9); the deterministic migration with its applied-name record (Requirement 6); the seed 100 and 160 paragraphs (Requirement 10); the default-identity proof (Requirement 11).
- Tests: the default literal pins, validation refusals, a `prompt-names` profile migration (chain, crash and retry, conflict), lint, scan, and an upgrade-path run.
- `tests/record_layout_support.SHIPPED_DEFAULTS` gains `PROMPT_NAME_OVERRIDES: {}`; a new profile asset `tests/fixtures/profiles/prompt-names.json` carries only a Waveforge-like chain override (container prompts to `-set` names, item prompts to `-wave` names) over the shipped vocabulary. `second.json` is not edited, so second-profile runs are unaffected.

**Out of scope:**

- MCP tool names, `wf_help` goals, tool docstrings and `usage` strings: the MCP surface is renamed through the declared tool aliases and per-profile goldens (waves 1zim4, 1zv8c), not through prompt names.
- Untiered and product-named prompts (`review-plan`, `memory-review`, `install-wavefoundry`, `upgrade-wavefoundry`, `package-wavefoundry` and the others in `FIXED_PROMPT_SLUGS`), so `REVIEW_PLAN_*_PROMPT`, `RETIRED_FINALIZE_PROMPT` and `UPGRADE_POLICY_DESTINATION` stay literal. Renaming the product is a packaging concern, not vocabulary.
- Seed file names and seed prose; prompt body prose beyond the materialized heading and Shortcut line; git commit-subject conventions (`build_pack.py` and `index_state_store.py` "Close wave" subjects); temp-file labels in `server_impl.py` (`"wf-close-change"` passed to `_atomic_replace_bytes`).
- Deriving names automatically from `CONTAINER_NAME`/`ITEM_NAME` (Decision Log).
- A profile change in this repository: it ships the defaults.
- Shortcut resolution in `server_impl.get_prompt` through the manifest (named follow-up; see Risks).

### Census

Predicate: a line in non-test framework Python under `.wavefoundry/framework/scripts/` (tests and benchmarks excluded) that contains a `docs/prompts/` path of one of the eleven mapped slugs (public or agent body), a mapped skill name `wf-<slug>`, or a mapped shortcut phrase (case-sensitive, including Ready wave). Command:

```
rg -c -g '*.py' -g '!**/tests/**' -g '!**/benchmarks/**' -e 'docs/prompts/(agents/)?(create-wave|prepare-wave|implement-wave|review-wave|close-wave|pause-wave|plan-change|implement-change|close-change|add-change-to-wave|remove-change-from-wave)\.prompt\.md' -e 'wf-(create-wave|prepare-wave|implement-wave|review-wave|close-wave|pause-wave|plan-change|implement-change|close-change)\b' -e '\b(Create|Prepare|Ready|Implement|Review|Close|Pause) wave\b|\b(Plan|Implement|Close) change\b|\b(Add|Remove) change (to|from) wave\b' .wavefoundry/framework/scripts
```

Result at HEAD `06c02e63` (matching lines per file) and disposition:

| File | Lines | Disposition |
| ---- | ----- | ----------- |
| `render_agent_surfaces.py` | 48 | derive (Requirements 3 to 7); comment lines and the `CHANGE_PROMPT_RENAMES` old names stay |
| `review_policy.py` | 17 | derive (block keys, carrier destinations, region prose names) |
| `review_policy_reconcile.py` | 9 | derive (path keys, bold shortcut names in region prose) |
| `reconcile_scan.py` | 9 | derive the suggestions; retired old names stay (Requirement 9 adds the profile table) |
| `context_efficiency.py` | 5 | derive `LIFECYCLE_PROMPT_MAP` |
| `wf_server/server_impl.py` | 5 | derive the `create_wave` scaffold line (1); keep the docstring example (1, MCP surface) and the three `_atomic_replace_bytes` labels |
| `wave_lint_lib/constants.py` | 3 | derive `PROMPT_SURFACE_FILES` |
| `wave_lint_lib/core_validators.py` | 3 | derive the three carrier probe paths |
| `wave_lint_lib/wave_validators.py` | 1 | derive the message |
| `index_state_store.py` | 3 | keep (commit-subject convention) |
| `build_pack.py` | 2 | keep (commit-subject convention) |

## Acceptance Criteria

- [x] AC-1: With the shipped `PROMPT_NAME_OVERRIDES = {}`, `PROMPT_NAMES` equals a test-pinned literal table of the eleven keys (slug, shortcut, aliases), and every consumer constant in Requirement 3 equals a test-pinned copy of its pre-change literal value (the one deliberate default change, the tier-neutral `single_prepare` anchor, is pinned to its new value, and `check_review_policy_carriers` reports nothing new on this repository).
- [x] AC-2: Each Requirement 2 rule, applied through the profile constants, raises `VocabularyProfileInvalid` with a message naming `PROMPT_NAME_OVERRIDES` and the key (one subtest per rule, including a case-insensitive shortcut clash with a fixed shortcut and a two-key cycle); a Set/Wave chain override validates. A test pins `FIXED_SKILL_NAMES` to the non-mapped `SKILL_REGISTRY` names and `FIXED_PROMPT_SHORTCUTS` to this repository's manifest shortcuts for non-mapped docs, so a copy cannot drift.
- [x] AC-3: Under defaults, `render_agent_surfaces` on a scratch copy of this repository writes no file (every rendered skill in the three hosts, `.cursor/rules/auto-guru.mdc`, `.claude/agents/guru.md`, `docs/prompts/**` and the manifest are byte-identical, and the manifest gains no `prompt_names` key); `reconcile_scan.scan_repo` returns the same findings as before the change; `register-surface-handler-digests.json` and the tool-surface goldens are unchanged.
- [x] AC-4: Under the `prompt-names` profile asset's override map, each Requirement 3 consumer yields the derived path or name, the skill registry renders `wf-<derived slug>` names whose descriptions and bodies carry the derived shortcuts and paths, and a materialized baseline carries the derived heading and Shortcut line with its other bytes equal to the template. Under defaults, one subtest per lifecycle template materializes it into an empty scratch target and asserts the bytes equal the template's stamped output today (prepare-wave's `| Alias:` reproduced exactly).
- [x] AC-5: Migration on a fixture target with the default-named public prompts and agent bodies (one customized with CRLF line endings), a manifest, and a project doc linking `docs/prompts/implement-wave.prompt.md`: one render moves the chain in dependency order byte-for-byte, rewrites each moved entry's `doc` and `shortcut`, records `prompt_names`, removes the default-named skill folders except those a chain reuses (registry `wf-` skills are unmarked under 1zxnu and are overwritten in place), materializes no baseline over a moved prompt, and reports the link as `file:line` without editing it; a second render writes nothing. A second fixture whose manifest has no Close change entry and no `close-change.prompt.md` ends with exactly one Close change entry, at the derived doc and shortcut, and the baseline materialized there.
- [x] AC-6: Crash and retry: for every interruption point (between a copy and its source unlink, after each move, and between a move and its manifest write), a rerun converges to the tree of an uninterrupted run without raising. The cases include the close chain (`close-wave` to its container name while `close-change` takes `close-wave`), where the rerun also leaves exactly one Close change manifest entry.
- [x] AC-7: Conflict: when a target path exists and is not the source of another pair in the plan, or the plan holds a cycle between applied and target names, the render raises naming every conflicting pair, and every prompt, the manifest and the skill folders are byte-identical afterwards.
- [x] AC-8: docs-lint checks the required prompt files at their derived paths and reports a pending migration naming the keys when the manifest's applied names differ from the profile; it is silent under defaults with no `prompt_names` key, and passes on the AC-5 fixture after the render.
- [x] AC-9: Under the `prompt-names` profile, the scan reports each non-ambiguous default path, skill name, shortcut-shaped phrase and guru-description phrase with the derived suggestion, and reports no default token that equals a current derived token.
- [x] AC-10: An upgrade-path test applies the change to a fixture target with the `prompt-names` profile through `upgrade_wavefoundry.phase_surface_rendering` with `SCRIPTS_DIR` patched to the new scripts (the 1zyc5 AC-15 pattern) and asserts the migration ran in that same upgrade.
- [x] AC-11: Seeds 100 and 160 and the rendered upgrade prompt carry the Requirement 10 paragraph, and the census command run over `.wavefoundry/framework/seeds/` returns the same per-file counts as before the change apart from that paragraph's own default-name mentions.
- [x] AC-12: The CHANGELOG Unreleased section carries the Requirement 12 entry.

## Tasks

- [x] Open `framework_edit_allowed` for scripts and tests; close it after.
- [x] `vocabulary_profile.py`: table, override constant, derived map, helpers, validation; `SHIPPED_DEFAULTS`; new asset `prompt-names.json`; profile tests (AC-1, AC-2).
- [x] Consumers: `render_agent_surfaces.py`, `review_policy.py`, `review_policy_reconcile.py`, `context_efficiency.py`, `wave_lint_lib/constants.py`, `core_validators.py`, `wave_validators.py`, `server_impl.create_wave`; `localize_prompt_template` (AC-4).
- [x] Migration, `prompt_names` record, profile-stale skills, link report (AC-5 to AC-7).
- [x] docs-lint pending-migration check; reconcile profile table (AC-8, AC-9).
- [x] Upgrade-path test (AC-10).
- [x] Open `seed_edit_allowed`, add the seed 100 and 160 paragraphs, close it; mirror the paragraph into `docs/prompts/upgrade-wavefoundry.prompt.md` (AC-11).
- [x] `docs/architecture/layering-rules.md` vocabulary paragraph; CHANGELOG entry (AC-12).
- [x] Default-identity run on a scratch copy (AC-3); `wf_validate_docs`; `run_tests.py` last.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws-1 profile map | software-engineer | - | constants, validation, helpers, test profile assets |
| ws-2 consumers | implementer | ws-1 | Requirements 3 to 5, 7 |
| ws-3 migration, lint, scan | software-engineer | ws-1, ws-2 | Requirements 6, 8, 9; upgrade-path test |
| ws-4 seeds, docs, default proof | implementer | ws-2, ws-3 | Requirements 10 to 12 |

## Serialization Points

- `.wavefoundry/framework/scripts/vocabulary_profile.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`, `.wavefoundry/framework/scripts/reconcile_scan.py`
- `.wavefoundry/framework/scripts/review_policy.py`, `.wavefoundry/framework/scripts/review_policy_reconcile.py`, `.wavefoundry/framework/scripts/context_efficiency.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`, `.wavefoundry/framework/scripts/wave_lint_lib/core_validators.py`, `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`, `.wavefoundry/framework/scripts/tests/record_layout_support.py`, `.wavefoundry/framework/scripts/tests/fixtures/profiles/prompt-names.json`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`, `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`, `docs/architecture/layering-rules.md`
- Root-level file edited (not a path token): CHANGELOG.md.

Notes: the `server_impl.py` edit is inside `create_wave`, not an `@mcp.tool` handler, so `register-surface-handler-digests.json` must stay unchanged (AC-3); if any handler source does change, recompute only its digest and say so in the fixture description. Goldens: the tool-surface goldens and `lifecycle-gate-golden.json` stay unchanged; the per-profile golden D adds and the second-profile run must stay unchanged (`second.json` is not edited). The targeted tests (AC-4 to AC-10) apply the `prompt-names` asset to scratch copies; `run_tests.py --profile prompt-names --file <those test files>` reruns them in profile mode. New framework Python must not spell record-vocabulary literals (for example the container record file name) that `test_vocabulary_census` flags; take them from `vocabulary_profile`.

## Affected Architecture Docs

`docs/architecture/layering-rules.md`: the vocabulary profile paragraph gains the prompt-name map (a fixed default table plus a fork-edited override, read by every consumer, migrated by the renderer). `docs/ARCHITECTURE.md` and the other child docs: N/A, the migration is one more pre-render step beside `migrate_change_prompt_renames` and no boundary or flow changes.

## Platform Behavior

- Moves are copy-bytes then unlink, never `os.rename`, so a chain behaves the same on Windows (where a rename onto an existing file fails), macOS, Linux and WSL2 (including `/mnt/c` DrvFs); bytes are copied without newline translation, so CRLF and LF survive (AC-5).
- Slugs are validated lowercase, so a derived name can never differ from another name only by case; APFS and NTFS case-insensitivity cannot collide two files, and the case-insensitive rename gate is not involved.
- A prompt locked by an editor on Windows makes the unlink fail; the existing rollback removes the new copy and raises, the manifest has not recorded that key, and a rerun completes it (AC-6).
- Symlinked or uncontained sources are refused on every platform. Manifest paths and `prompt_names` values are repo-relative POSIX on all platforms; the manifest is rewritten preserving its newline style.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Defaults must reproduce today's names exactly. |
| AC-2 | required | A bad profile must fail closed at import. |
| AC-3 | required | Zero change for every target on the default profile. |
| AC-4 | required | The feature itself: every consumer follows the profile. |
| AC-5 | required | Targets with default-named prompts must converge without losing customizations. |
| AC-6 | required | Chains are only safe if every interruption converges. |
| AC-7 | required | Never overwrite project prose. |
| AC-8 | required | Targets must not go lint-red silently. |
| AC-9 | important | Tells the target agent what prose still names defaults. |
| AC-10 | required | The migration must run on the upgrade that installs it (old-code window). |
| AC-11 | important | Installing agents need the rule; seeds keep defaults. |
| AC-12 | important | Release notes for distributions. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-06 | Planned from the verified Waveforge request R1(2) and R1(3); census taken at HEAD `06c02e63`. | Census command in Scope. |
| 2026-10-06 | Implementation note (optional, non-blocking): a test may pin `FIXED_PROMPT_SLUGS` against the stems of `docs/prompts/*.prompt.md` and `docs/prompts/agents/*.prompt.md` in this repository, so a new prompt cannot be missed. | Readiness re-check note. |
| 2026-10-06 | Implemented: profile map, validation and helpers in `vocabulary_profile.py`; every census consumer derived; `migrate_profile_prompt_names` with per-key `prompt_names` record; profile stale skills; lint pending check; reconcile profile table; seeds 100/160 paragraph mirrored into the upgrade prompt; layering-rules paragraph; CHANGELOG entry. Default render of a scratch copy writes nothing. Gapfill: shell retrieval used for the census and consumer reads. | `tests/test_vocabulary_prompt_names.py` 21 tests OK; profile mode 16 run (5 default-only skipped); 14 mutation probes all killed; `wf_validate_docs` ok. |
| 2026-10-06 | Delivery repair DEL-1b: new `test_reverting_to_the_defaults_drops_the_record` renders under the profile, then twice under the defaults, asserting the prompts move back, `prompt_names` is removed from the manifest, and the second render writes nothing. | Mutation probe: removing the `data.pop("prompt_names", None)` branch fails the test. |
| 2026-10-06 | Delivery repair DEL-1c: exclusive byte copies (both prompt moves, this change and 1zyc5, share `_write_review_carrier_text`) now go through `_write_bytes_atomic_exclusive`: a temporary file in the destination folder, then a hard link that refuses an existing target (Windows without hard links renames, which also refuses an existing target; other platforms without hard links fall back to the exclusive create), so an interruption never leaves a truncated target. New `test_a_locked_source_rolls_the_copy_back` (the source unlink raises as a locked Windows file does: copy removed, source kept, no `prompt_names`, tree byte-identical, rerun converges) and `AtomicPromptCopyTests` (interrupted copy leaves nothing; exact bytes; refusal with and without hard links). | Probes: removing the rollback unlink and removing the atomic branch each fail their tests. |
| 2026-10-06 | Delivery repair DEL-3b: `_profile_prompt_name_tables` adds each key's `shortcut_aliases` to the current-name set, so a live alias is never reported as retired; new `RetiredNameScanAliasTests`. | Probe: removing the alias line fails the test. |
| 2026-10-07 | Repair: `_write_bytes_atomic_exclusive` POSIX no-hard-link fallback now removes the target it created (identity-checked with `os.path.samestat`, never a pre-existing file) when the direct write fails, then re-raises; docstring says temp removal is best-effort after a successful link. New `AtomicPromptCopyTests.test_without_hard_links_a_failed_direct_copy_leaves_no_target` drives `_move_prompt_pair` with a failing fallback write: no target remains, source untouched. Scratch `--file`: test_vocabulary_prompt_names 28 ok, test_render_agent_surfaces 146 ok; mutant dropping the unlink fails the new test. CHANGELOG bullet attributed `Wave 1zyb4 / 1zxnw.` Gapfill: shell grep/sed used for discovery. | Repair session. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-06 | Explicit override map keyed by today's slug, with a fixed default table and an empty single-line override constant. | Matches the fork-edit model of `vocabulary_profile.py` and `EXTRA_CHANGE_KINDS`; a one-line constant works with `apply_profile`; explicit names express chains and aliases such as Ready wave. | Derive names from `CONTAINER_NAME`/`ITEM_NAME`: cannot tell container from item verbs, cannot express aliases, and would collide automatically in the Set/Wave case. |
| 2026-10-06 | Only the eleven tier-named lifecycle prompts are mapped. | The profile's own definition of vocabulary is a token that embeds a tier name; product-named and untiered prompts are not vocabulary. | Map every framework prompt: widens validation and touches required-file lint for install and upgrade prompts with no requester. |
| 2026-10-06 | Record applied names in the manifest (`prompt_names`), per key, after each key's moves. | Chains make file names ambiguous; a tracked record travels with the repository; per-key recording makes every crash point converge; under defaults no key is written. | Infer from files: ambiguous for chains. A gitignored state file: lost on a fresh clone, so a second clone would re-migrate. |
| 2026-10-06 | Seed text keeps the default names; seeds 100 and 160 point agents at the manifest record. | Seeds are shared framework source installed verbatim by every distribution; the renderer is the one translation point, and agents authoring default names is exactly what the migration expects. | Template the seeds: makes seed text profile-dependent and breaks the shared index. |
| 2026-10-06 | Keep `CHANGE_PROMPT_RENAMES` moving to the default change names and let the profile migration move on; derive `CLOSE_CHANGE_PROMPT`/`CLOSE_CHANGE_SHORTCUT`. | One render does both steps with no special case; the Close change manifest repair would otherwise re-add a stale entry every render. | Derive the 1zyc5 destinations directly: two migrations writing the same names. |
| 2026-10-06 | `prompt_names` in the tracked prompt-surface manifest (coordinator decision). | Travels with the repository; already renderer-managed and excluded from the reconcile scan. | A separate tracked state file: one more required artifact. |
| 2026-10-06 | Exercise overrides through a separate `prompt-names.json` profile asset, not `second.json` (coordinator decision). | Keeps the existing second-profile runs unaffected; `run_tests.py --profile` already accepts any asset under `tests/fixtures/profiles/`. | Extend `second.json`: perturbs every test in the second-profile run that pins default prompt names. |
| 2026-10-06 | Rewrite only the heading and Shortcut line of materialized baselines. | Gives a fresh target correct names without rewriting prose; identity under defaults (precedent `localize_template`). | Leave templates untouched: a fresh Waveforge target gets a "Create Wave" heading on its create-set prompt. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Shared files with the earlier waves: `server_impl.py` (A, B, C), `render_agent_surfaces.py` (C at the journals exclusion line, D in skill rendering and ownership), `reconcile_scan.py` (C), `wave_validators.py` (C), `tests/record_layout_support.py` and the profile assets (D's per-profile goldens), `layering-rules.md` (C). | This wave lands last; rebase on D's tree; `server_impl.py` edit is one line in `create_wave`. |
| `1zxnx` (same wave) also edits `render_agent_surfaces.py` registry text. | Land this change first in wave E; `1zxnx` rebases onto it. |
| Wave ordering: this change derives registry skill names and stale-skill cleanup on top of the skill rendering, ownership marker and per-profile goldens that `1zxnu` (wave D) changes. Cross-wave `Depends On` is not declared (docs-lint rejects it). | Fixed wave order: wave D closes before wave E opens; implement on D's tree. |
| Tests that pin default prompt names fail when run under the `prompt-names` asset. | Only the targeted test files are run under that asset; `second.json` and the second-profile run are untouched. |
| A target authors profile-named prompts before any render recorded `prompt_names`; in a chain the migration then sees source and target both present. | Preflight raises a conflict and writes nothing; seeds 100 and 160 tell agents to author defaults unless the manifest lists applied names. |
| Known limit: `server_impl.get_prompt` resolves a slug by file stem, then by the first prompt whose content contains the phrase. Under a chain, a default shortcut typed by habit (for example Implement wave meaning the container) resolves to the item prompt that now holds that file name, and a default phrase left in moved prompt bodies can resolve by content. | Out of scope here; named follow-up: resolve shortcuts through manifest `public_prompt_surface` entries and `prompt_names` before the stem and content fallbacks. Seeds 100 and 160 tell agents to update headings and Shortcut lines. |
| The tier-neutral `single_prepare` anchor drops `prepare wave`, so a target prompt that carries only that prose and not the rendered review-policy block would newly miss the obligation. | The renderer writes the prepare and implement blocks (renderer-owned carriers) before lint; a test runs `check_review_policy_carriers` on this repository and on the AC-5 fixture. |
| Old-code window: the upgrade that installs this runs some phases with old code. | The call sits beside `migrate_change_prompt_renames`, which runs from the fresh renderer; AC-10 proves it. |
| D's ownership rule (refuse overwriting an unmarked SKILL.md) might be read as covering registry skills. | It does not: 1zxnu marks and guards declared distribution skills only; registry `wf-` skills stay unmarked and are overwritten unconditionally, so a chain-reused folder is simply rewritten (AC-5). If D's delivered code differs, rebase and re-verify AC-5. |
