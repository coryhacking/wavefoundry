# Deprecated Alias Hint Exclusion

Change ID: `242k2-enh deprecated-alias-hint-exclusion`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-11-22
Wave: 242k3 deprecated-alias-hints

## Rationale

A distribution that serves a tool under its own name declares an alias in `mcp_tool_extensions.EXTENSION_TOOL_ALIASES`. Today the first plain alias of a tool also becomes the name every response hint uses for that tool, and no declaration turns that off. A distribution that returns to the upstream tool names and keeps an earlier name callable for one release therefore steers every agent back to the earlier name.

A planning probe on 2026-11-22 reproduced this in a scratch copy of the framework scripts (`.wavefoundry/work/242k3/planning/probe_alias_hints.py`, output in `probe_alias_hints.out`). With only `{"old_close_container": "wf_close_wave"}` declared, a lifecycle-busy response to a call of `wf_close_wave` itself returned `next_tools: ["old_close_container", "wf_current_wave"]`, `usage: "retry old_close_container after ..."`, and the same name in `recovery_tools` and `recovery_usage`.

Waveforge reported this in its 3.2.0 request, item 4 (`.wavefoundry/work/242k3/eval/waveforge-3.2.0-request.md`). It keeps one forwarding handler per earlier name in its own extension module so that hints do not name it. Each handler repeats the canonical signature and drifts when upstream adds a parameter, which is the failure the alias declaration exists to prevent. The evaluation (`.wavefoundry/work/242k3/eval/evaluation.md`, item 4) found the takeover generic to every distribution that renames a served tool. The operator decided on 2026-11-22 to deliver hint exclusion only (wave record, Wave Summary).

## Product Intent

A distribution maintainer who renames a served tool can keep the earlier name callable while agents are steered to the current name.

- **Before:** declaring the earlier name as an alias makes every response hint name it.
- **After:** the maintainer also lists the earlier name in one declaration. Calls to it work exactly as before. Response hints name the current tool: another alias that is not deprecated, or the canonical name when none exists.
- **Boundary:** the framework adds no notice to a call made through a deprecated alias. A distribution that wants a per-call notice keeps its own forwarding handler for that name. This change removes the forwarding handlers a distribution keeps only to control hints.
- **Proof of intent:** AC-1 establishes the outcome for the motivating case. AC-2 and AC-3 establish it when the current name is itself an alias.
- **After delivery:** success is observed when a distribution's next upstream note reports the declaration in use in place of a forwarding handler. Nothing in this change measures that.

## Requirements

1. **Declaration.** `mcp_tool_extensions.py` gains one distribution-edited constant, `EXTENSION_DEPRECATED_ALIASES: tuple[str, ...] = ()`. Each entry is an alias name that is a key of `EXTENSION_TOOL_ALIASES`. The shipped value is empty.
2. **Activation.** `mcp_tool_extensions.declared()` returns true when `EXTENSION_DEPRECATED_ALIASES` is non-empty or is not a tuple, so the server and the roster validate a declaration that sets only this constant.
3. **Serving is unchanged.** A deprecated alias is installed, listed and callable exactly as an alias is today. It keeps the canonical tier, its permission allow rule, its input schema, its parameter mapping and its response key renames. A plain deprecated alias still shares the canonical tool's wrapped callable, so the lifecycle lock, the publication guard and cost accounting apply as they do today.
4. **Hint selection rule.** Wherever the framework selects an alias to stand for a canonical name in a response hint, it never selects a deprecated alias. The hint fields are `next_tools`, `usage`, `diagnostics[].recovery_tools` and `diagnostics[].recovery_usage`. Two functions select today, and the rule governs any other selector found during implementation:
   1. `mcp_tool_extensions.served_name_map`, which picks the name for list items and whole names.
   2. `_alias_call_specs` in `wf_server/server_impl.py`, which lists the candidate aliases for a canonical name that has a parameter-mapped alias. `_rewrite_served_names` and `_alias_call_text` choose from that list.
5. **Order among the remaining aliases.** The existing preference order applies to the aliases that are not deprecated: plain aliases first, then mapped aliases without fixed parameters, then pinned aliases for a matching call, each in declaration order.
6. **No remaining alias.** When every alias of a served canonical name is deprecated, hints keep the canonical name, and `served_name_map()` has no entry for it. A call written in a hint keeps the canonical name and the canonical parameter names.
7. **The call path does not matter.** A response to a call made through a deprecated alias carries the same hint names as a response to the canonical call.
8. **Replacements are unchanged.** A replaced core name still maps to its `alias_for_core`. An `alias_for_core` cannot be deprecated, because the core behavior is reachable under no other name.
9. **Validation.** `mcp_tool_extensions.declaration_problems` reports each of the following, so `validate_declaration` raises `ExtensionDeclarationError`. The server then starts fail-closed and `mcp_tool_roster.all_tool_tiers()` raises, as they do for any invalid declaration. Each message names the constant or the offending entry.
   1. `EXTENSION_DEPRECATED_ALIASES` is not a tuple, or an entry is not a string.
   2. An entry is listed twice.
   3. An entry is not a key of `EXTENSION_TOOL_ALIASES`. This covers a name that is no tool, a canonical tool name, an `alias_for_core` and a new extension tool name.
   4. A name in `EXTENSION_HIDDEN_TOOLS` has no alias that is both without fixed parameters and not deprecated. A hidden name must keep one name that hints can use.
10. **Provenance.** `wf_server_info` reports the declared names as a sorted list under `extensions.deprecated_aliases`, empty for the stock declaration. `extensions.served_names` reports the map after exclusion.
11. **Reload.** `wf_reload_mcp` applies an edited `EXTENSION_DEPRECATED_ALIASES` through the existing reload path. This change adds no reload mechanism.
12. **Unchanged by design.** The following keep today's behavior:
    1. Names inside `data`, diagnostic messages, tool descriptions, docstrings and FastMCP argument-validation errors stay canonical.
    2. A parameter-mapped alias called with an argument it does not accept answers with the translator's own refusal. Its `usage` text ends with a comment that names the alias the caller used (`# see supported parameters for <alias>`). The comment stays, because the parameters it refers to are that alias's parameters (executed: probe case D).
    3. A hint that a distribution's own handler writes with a deprecated name in it is not rewritten. The declaration governs which name the framework selects.
13. **No tool contract change.** No tool docstring, tool description or input schema changes. `tests/fixtures/register-surface-handler-digests.json`, `tests/fixtures/tool-surface-golden.json` and `tests/fixtures/tool-surface-golden/declared.json` are not edited or regenerated by this change. If implementation finds that a handler docstring must change, the implementer refreshes the digest pin for that handler only and records it in the Progress Log.
14. **Platforms.** The change selects names from in-memory declarations. It reads no path, file name, process state or locale. Windows, macOS, Linux and WSL2 behave identically.

## Scope

**Problem statement:** A declared alias takes over response hints for its canonical tool, and a distribution has no declaration that keeps the alias callable without that effect.

**In scope:**

- The `EXTENSION_DEPRECATED_ALIASES` declaration, its validation and its effect on hint selection (Requirements 1 to 9).
- The `extensions.deprecated_aliases` provenance field (Requirement 10).
- Tests in the extension tool suite, the declaration support fixtures and the `declared` profile sample.
- The declaration contract in `docs/specs/mcp-tool-surface.md`, the declared-run description in `docs/architecture/testing-architecture.md` and a CHANGELOG entry.

**Out of scope:**

- **A per-call deprecation diagnostic.** Operator DECLINE, 2026-11-22. The notice is the distribution's own user experience and stays in its fork.
- **Retired aliases (request item 4b).** Operator DECLINE, 2026-11-22. A stub that refuses and names its replacement is a few lines in the distribution's own extension module, which is the supported seam. It has no signature to keep in step, so upstream gains nothing by serving it.
- **Request item 1a, a record-vocabulary migration.** Operator DECLINE, 2026-11-22. The rewrite is a one-time migration of one distribution's records. Upstream has never renamed those names and could not exercise the tool. The distribution's `vocabulary-records` upgrade item owns it.
- **Request item 1b, a lint error for an earlier record file name.** Operator DECLINE, 2026-11-22. It guards a one-time migration window. The distribution's migration preview already lists every unmigrated record and can report one itself. Upstream would need an earlier-profile declaration that it has no other use for.
- **Request item 2, the council spelling as a profile constant and a digest from the canonical key.** Operator DECLINE, 2026-11-22. The profile constants already exist (`EXTRA_LEGACY_COUNCIL_SIGNOFF_KEYS`, `EXTRA_LEGACY_COUNCIL_ACTORS`). The digest hashes an undeclared spelling as written, so a target config that keeps the earlier spellings produces the same digest on stock code. Changing the digest input would lapse approvals on in-flight waves in every target.
- **Request item 3, declared earlier skill names.** Operator DECLINE, 2026-11-22 (the operator accepted the coordinator's narrowing). The cleanup happens once; upstream would carry a file-deleting declaration that a distribution's configuration drives; the distribution's inventory-then-remove approach, which upstream suggested on 2026-11-21, already covers it.
- **Refreshing the pins in `tests/fixtures/profiles/qualification/coverage.json`.** Not part of this change. `docs/contributing/build-and-verification.md` states that pins are never refreshed automatically and that a changed contract falls back to the full profile run. Nine of the sixteen pins were already stale on 2026-11-22 (executed, including `mcp_tool_extensions.py` and `tests/record_layout_support.py`), so the fallback is already in effect.

**Files this change shares with wave 241lp.** Wave `241lp operator-selected-small-change-review` is open in another session with uncommitted edits. The implementer re-checks the tree before the first edit and edits only the regions this change owns.

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`: both waves edit it. This change touches `_alias_call_specs`, the extension provenance builders and the `extensions` object of `wf_server_info_response`.
- `docs/specs/mcp-tool-surface.md`: both waves edit it. This change touches the **Distribution Extension Tools** section only.
- `CHANGELOG.md`: wave 241lp added the `[1.49.0]` section. This change adds one bullet under `[Unreleased]`.
- `.wavefoundry/framework/scripts/tests/fixtures/tool-surface-golden.json` and `.wavefoundry/framework/scripts/tests/fixtures/tool-surface-golden/declared.json`: wave 241lp edits both. This change must not edit or regenerate either (Requirement 13).
- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`: unmodified on 2026-11-22. Wave 241lp adds the flat script `small_change_lane.py`, which is not yet in `FRAMEWORK_SCRIPT_MODULE_NAMES`, so that wave may edit this file too (inferred).

## Acceptance Criteria

Each criterion is verified by an automated test in the framework suite unless it says otherwise. AC-1 tests the Product Intent directly.

- [ ] AC-1: A server built from a declaration with one plain alias of a served lifecycle tool, listed in `EXTENSION_DEPRECATED_ALIASES`, steers hints to the canonical name. The test reads the hints of a lifecycle-busy response through FastMCP's client path. Without the change the same declaration names the alias in all four fields (executed: probe cases A and B).
  1. For a call of the canonical name, `next_tools`, `usage`, `diagnostics[].recovery_tools` and `diagnostics[].recovery_usage` name the canonical tool and never the alias.
  2. For a call of the deprecated alias, the four fields carry the same names as in sub-point 1.
  3. `mcp_tool_extensions.served_name_map()` returns no entry for that canonical name.
- [ ] AC-2: With two plain aliases of one canonical name, the first-declared one deprecated, the hints of the same response name the second alias. Without the change they name the first-declared alias (executed: probe case C).
- [ ] AC-3: Deprecation composes with parameter-mapped aliases. Without the change the plain alias wins in sub-point 1 (executed: probe case D).
  1. A canonical name has a deprecated plain alias and a mapped alias that renames parameters. Whole-name hints name the mapped alias, and a parseable call in `usage` or `recovery_usage` is rewritten to the mapped alias with its parameter names.
  2. A canonical name has a deprecated pinned alias and another alias. A call whose arguments match the pinned values is not rewritten to the deprecated alias.
  3. A canonical name whose only alias is mapped and deprecated keeps its canonical name and canonical parameter names in every hint field.
- [ ] AC-4: A deprecated alias is served exactly as a non-deprecated alias. A known-bad implementation that drops, hides or re-wraps a deprecated alias fails this criterion.
  1. For one declaration built twice, with and without the deprecated entry, the served tool names, tiers, input schemas and permission allow rules are equal.
  2. A plain deprecated alias shares the canonical tool's wrapped callable, and a call through it returns the canonical response.
  3. A call through the deprecated alias under a held lifecycle lock returns `lifecycle_mutation_locked`.
- [ ] AC-5: `declaration_problems` reports a problem for each invalid declaration below, and reports none for the valid declarations of AC-1 to AC-3. Without the change every case below is accepted silently, because the constant is not read (executed: probe case B declared an unknown name and the server served normally).
  1. `EXTENSION_DEPRECATED_ALIASES` is a list, or holds a non-string entry.
  2. An entry appears twice.
  3. An entry is a name that is no tool.
  4. An entry is a canonical tool name that has an alias.
  5. An entry is the `alias_for_core` of a declared replacement.
  6. A hidden canonical name has aliases, and each one is deprecated or pinned.
- [ ] AC-6: An invalid deprecated declaration is refused at both validation entry points. A declaration that sets only `EXTENSION_DEPRECATED_ALIASES` is validated, which requires `declared()` to return true for it.
  1. Building the server leaves only runner tools served and reports the declaration problem.
  2. `mcp_tool_roster.all_tool_tiers()` raises `ExtensionDeclarationError`.
- [ ] AC-7: A hidden canonical name with one deprecated alias and one non-deprecated plain alias is valid, its hints name the non-deprecated alias, and a declared replacement in the same declaration still maps its core name to its `alias_for_core`.
- [ ] AC-8: `wf_server_info` reports the declaration, and a reload applies an edit to it.
  1. `extensions.deprecated_aliases` is the sorted list of declared names, and `extensions.served_names` omits a canonical name whose aliases are all deprecated.
  2. With the stock declaration, `extensions.deprecated_aliases` is an empty list and `served_name_map()` is empty.
  3. After the declaration file gains a deprecated entry and `wf_reload_mcp` runs, the hints of AC-1 change from the alias to the canonical name.
- [ ] AC-9: The new constant is registered wherever the test support enumerates declarations, and the `declared` profile sample exercises it.
  1. `SHIPPED_DECLARATION` in `tests/record_layout_support.py` carries `EXTENSION_DEPRECATED_ALIASES` as an empty tuple, and `DeclarationConstantCensusTests` passes, including its check of the refusal driver's reset line.
  2. `tests/fixtures/profiles/declared.json` lists `wf_alias_help` in `EXTENSION_DEPRECATED_ALIASES`, and `apply_profile` writes it as a tuple.
  3. `python3 .wavefoundry/framework/scripts/run_tests.py --profile declared --file test_declaration_support.py --file test_tool_surface_golden.py --file test_profile_support.py --file test_extension_tool_modules.py` reports no failed file, with no golden regenerated. The per-profile golden test passing against an unregenerated `declared.json` golden shows that the served surface of the sample did not change.
- [ ] AC-10: The documentation states the contract. Each sub-point is checked by reading the document.
  1. `docs/specs/mcp-tool-surface.md` lists `EXTENSION_DEPRECATED_ALIASES` in the declaration table of **Distribution Extension Tools**.
  2. Its **Aliases and hidden names** and **Response hints** text states that a deprecated alias stays callable, that hints never select it, which name hints use when no other alias remains, the validation rules of Requirement 9, and the unchanged cases of Requirement 12.
  3. Its `wf_server_info` text names `extensions.deprecated_aliases`.
  4. `docs/architecture/testing-architecture.md` says that the `declared` sample marks `wf_alias_help` deprecated.
  5. `CHANGELOG.md` has a bullet under `[Unreleased]` that ends "Wave 242k3 / 242k2.".
- [ ] AC-11: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change. `git diff` shows no edit by this change to `tests/fixtures/register-surface-handler-digests.json` or to either tool-surface golden.

## Tasks

- [ ] Re-check the working tree for wave 241lp's uncommitted edits to the shared files listed in Scope, and plan each edit around them.
- [ ] Open the edit gate with `wf_open_gate(gate="framework_edit_allowed")`.
- [ ] Add `EXTENSION_DEPRECATED_ALIASES` to `mcp_tool_extensions.py` with its declaration comment, and name it in the module docstring.
- [ ] Add the constant to `declared()`.
- [ ] Exclude deprecated aliases in `served_name_map`, and update its docstring.
- [ ] Add the Requirement 9 checks to `_alias_hide_replacement_problems`, including the hidden-name rule.
- [ ] Exclude deprecated aliases from the candidates that `_alias_call_specs` builds in `wf_server/server_impl.py`.
- [ ] Add `deprecated_aliases` to the extension provenance: `_empty_extension_provenance`, the provenance built in `_install_declared_extension_tools`, and the `extensions` object of `wf_server_info_response`.
- [ ] Run a census for any other selector of an alias name for a hint field, and apply Requirement 4 to each one found. Record the census result in the Progress Log.
- [ ] Add `EXTENSION_DEPRECATED_ALIASES` to `SHIPPED_DECLARATION` in `tests/record_layout_support.py` and to the reset line of the refusal driver in `tests/test_extension_tool_modules.py`.
- [ ] Add pure declaration tests to `DeclarationValidationTests` for AC-5 and for the `served_name_map` cases of AC-1, AC-2 and AC-7.
- [ ] Add a serving mode to the subprocess driver in `tests/test_extension_tool_modules.py`, with a test class that covers AC-1 to AC-4, AC-6, AC-7 and AC-8.
- [ ] Add rewrite tests for the mapped-alias cases of AC-3 beside `ParameterMappedAliasTests` or `ServedNameRewriteTests`.
- [ ] Add `"EXTENSION_DEPRECATED_ALIASES": ["wf_alias_help"]` to `tests/fixtures/profiles/declared.json`, and adjust any test that pins the sample's declaration.
- [ ] Update `docs/specs/mcp-tool-surface.md` for AC-10 sub-points 1 to 3.
- [ ] Update the declared-alias run paragraph in `docs/architecture/testing-architecture.md`.
- [ ] Add an `### Added` bullet under `[Unreleased]` in `CHANGELOG.md` that ends "Wave 242k3 / 242k2.".
- [ ] Run the focused suites: `python3 .wavefoundry/framework/scripts/run_tests.py --file test_extension_tool_modules.py --file test_declaration_support.py --file test_profile_support.py --file test_tool_surface_golden.py --file test_mcp_tool_registry.py --file test_qualification_report.py`.
- [ ] Run the declared-profile command of AC-9 sub-point 3.
- [ ] Confirm with `git diff` that this change did not edit the handler digest fixture or either tool-surface golden.
- [ ] Close the edit gate with `wf_close_gate(gate="framework_edit_allowed")`.
- [ ] Run `wf_validate_docs` and fix any error in the documents this change edits.
- [ ] Run the full framework suite last, with `python3 .wavefoundry/framework/scripts/run_tests.py`, and record the result in the Progress Log.

## Agent Execution Graph

The work is one sequence owned by one implementer. The declaration and its validation come first, because the server change and every test read them.

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| declaration-and-validation | implementer | none | `mcp_tool_extensions.py` |
| server-selection-and-provenance | implementer | declaration-and-validation | `wf_server/server_impl.py`, shared with wave 241lp |
| tests-and-profile-sample | implementer | server-selection-and-provenance | extension suite, declaration support, `declared.json` |
| docs-and-changelog | implementer | server-selection-and-provenance | tool-surface spec, testing architecture, CHANGELOG |
| verification | implementer | tests-and-profile-sample, docs-and-changelog | focused suites, declared profile, docs validation, full suite last |

## Serialization Points

- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `.wavefoundry/framework/scripts/tests/record_layout_support.py`
- `.wavefoundry/framework/scripts/tests/fixtures/profiles/declared.json`
- `docs/specs/mcp-tool-surface.md`
- `docs/architecture/testing-architecture.md`

The root-level `CHANGELOG.md` also changes; a root-level file cannot be declared as a path token.

## Affected Architecture Docs

- `docs/architecture/testing-architecture.md`: the **Declared-alias run** paragraph describes the `declared` sample and gains the deprecated alias.
- The other architecture documents need no update. The change adds one declaration to an existing module and filters candidates inside two existing functions. It moves no module boundary, adds no wrapper to the middleware chain and changes no data or control path.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The motivating case: an earlier name stays callable and hints name the canonical tool. |
| AC-2 | required | A distribution's current name is often itself an alias. |
| AC-3 | required | The second selector serves mapped aliases; missing it leaves the takeover in place for them. |
| AC-4 | required | The operator's decision keeps a deprecated alias callable exactly as today. |
| AC-5 | required | A mistyped or unsupported entry must be refused, not ignored. |
| AC-6 | required | Refusal must reach both the server and the permission roster. |
| AC-7 | required | Deprecation must compose with hidden names and replacements. |
| AC-8 | important | Provenance lets a maintainer confirm the declaration is live; reload follows the existing path. |
| AC-9 | required | An unregistered constant breaks the declaration test support and the profile writer. |
| AC-10 | required | The declaration contract is documented where distributions read it. |
| AC-11 | required | The change's own evidence, and proof that pinned fixtures stay untouched. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-22 | Planning probes run against a scratch copy of the framework scripts. A plain alias takes over all four hint fields, for calls of the canonical name and of the alias. Declaration order decides between two plain aliases. A plain alias beats a mapped alias. An undeclared `EXTENSION_DEPRECATED_ALIASES` constant with an unknown name is ignored today. | `.wavefoundry/work/242k3/planning/probe_alias_hints.py`, `.wavefoundry/work/242k3/planning/probe_alias_hints.out` |
| 2026-11-22 | The `declared` profile applies its alias sample in a temporary copy and the two focused files pass (34 tests). A search of the test tree found no assertion that a hint names `wf_alias_help`. | `.wavefoundry/work/242k3/planning/profile_declared_focused.out` |
| 2026-11-22 | Nine of sixteen contract pins in the qualification inventory were already stale, by SHA-256 comparison. The `wf_server_info` handler docstring does not list the `extensions` keys. | Planning session commands; not saved as files |
| 2026-11-22 | Operator decision 2026-11-22: DECLINE this change and remove it from wave 242k3 before readiness. The readiness primer showed that Waveforge's forwarding handlers also emit the per-call deprecation notice, so hint exclusion alone lets them delete no code. Restoring the notice would add a permanent extension-contract feature for one distribution's one-release transition. Upstream declares no tool aliases and does not rename tools. Reopen if a second distribution needs supported tool-alias deprecation, or if the need outlasts one release. | Readiness red-team primer, 2026-11-22 (disposable review notes, not retained); `EXTENSION_TOOL_ALIASES` in `mcp_tool_extensions.py` is empty |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-22 | Deliver request item 4a as hint exclusion only. | Operator decision, recorded in the wave record's Wave Summary. | The evaluation's full option added a per-call `deprecated_alias` diagnostic. |
| 2026-11-22 | DECLINE the per-call diagnostic, retired aliases (4b) and request items 1a, 1b, 2 and 3. | Operator decision 2026-11-22. The reasons are in Scope. Those for the diagnostic, 4b and items 1a, 1b and 2 come from the evaluation. Item 3: Operator decision 2026-11-22 (accepted the coordinator's narrowing): the cleanup happens once; upstream would carry a file-deleting declaration that a distribution's configuration drives; the distribution's inventory-then-remove approach, which upstream suggested on 2026-11-21, already covers it. | Deliver any of them upstream. The evaluation recommended delivering item 3. |
| 2026-11-22 | Selected approach: a flat tuple `EXTENSION_DEPRECATED_ALIASES` of alias names, excluded at the two selection functions. | Planner default. It is the smallest declaration that states the fact, it matches the existing tuple declarations such as `EXTENSION_HIDDEN_TOOLS`, and it leaves the serving path of the alias untouched. | Three alternatives were rejected. A `"deprecated"` key in `EXTENSION_TOOL_PARAMETERS`: an alias with a parameters entry is installed through `_mapped_alias_tool` and is no longer a plain alias for `served_name_map`, so a plain alias would stop being served exactly as today. A map of preferred hint names per canonical tool: it adds a second authority for hint names and needs its own validation for pinned and hidden names. Documentation of declaration order only: it cannot prefer the canonical name over a single alias (probe case A) or a mapped alias over a plain one (probe case D). |
| 2026-11-22 | Mechanism efficacy for the selected approach. | Planner assessment. Replaying probe case A: with the alias excluded, `served_name_map()` has no entry for the tool, so nothing is rewritten and the hints keep the canonical name. The mechanism controls the outcome, because the two selection functions are the only places that choose an alias for a hint (search of the framework scripts for readers of `served_name_map` and `EXTENSION_TOOL_ALIASES`; the other readers assign tiers, validate names, install tools or report provenance). It misses a deprecated name that a distribution's own handler writes into a hint, and the mapped translator's comment (Requirement 12). It flags nothing wrongly, because it only narrows a choice. A mistyped entry is refused, so the declaration cannot be silently ignored. Declaration order already handles two plain aliases but not the two cases above. Success after release is a distribution reporting the declaration in use. | None. |
| 2026-11-22 | Report the declaration in `wf_server_info` under `extensions.deprecated_aliases`. | Coordinator decision, 2026-11-22: for consistency with the extension declarations that `wf_server_info` already lists. It is a report, not the declined per-call diagnostic. | Leave provenance unchanged and infer the declaration from `served_names`. |
| 2026-11-22 | Keep the alias name in the mapped translator's refusal comment. | Coordinator decision, 2026-11-22: it is the smaller change. The comment also identifies whose parameters the refusal lists, and those are the alias's parameters. | Rewrite the comment to the canonical name, which would point at a different parameter list. |
| 2026-11-22 | Mark the existing sample alias `wf_alias_help` deprecated in the `declared` profile instead of adding an alias. | Planner default. A deprecated alias is served unchanged, so the per-profile golden needs no regeneration. That golden carries wave 241lp's uncommitted edits. | Add a new sample alias, which changes the golden. |
| 2026-11-22 | Do not refresh the qualification inventory pins. | Planner default, following the documented rule that pins are never refreshed automatically. The fallback to a full profile run is already in effect. | Refresh the pins in this change, which needs a review of each independence claim. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Wave 241lp has uncommitted edits in `wf_server/server_impl.py`, `docs/specs/mcp-tool-surface.md`, `CHANGELOG.md` and both tool-surface goldens. Line numbers in `server_impl.py` moved during planning. | This spec cites symbols, not lines. The first task re-checks the tree. The goldens are never regenerated (Requirement 13, AC-11). |
| A third selector of alias names for hints exists that planning did not find. | The census task applies the rule of Requirement 4 to whatever it finds. AC-1 to AC-3 read real responses through the client path, so a missed selector on those paths fails a test. |
| A test under the `declared` profile depends on hints naming `wf_alias_help`. | The planning search found none. AC-9 sub-point 3 runs the four affected files under the profile; the release profile run covers the rest. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
