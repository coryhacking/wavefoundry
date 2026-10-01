# Extension Aliases Can Rename and Pin Parameters, and Overrides Can Delegate to the Core Handler

Change ID: `1zim0-feat extension-alias-parameter-mapping`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zim3 extension-alias-parameters

## Rationale

From a downstream distribution's note against `v1.28.0` ("Tool-name seams", requests 1 to 3; request 4, replacement tiers, shipped in wave 1zicq). With a vocabulary profile that renames the tiers (container "Set", item "Wave"), tool *parameter* names still carry the default vocabulary: `wf_add_change(wave_id, change_id)` means *set id, wave id*. A plain `EXTENSION_TOOL_ALIASES` entry cannot serve `wf_add_wave(set_id, wave_id)`, because an alias is a `model_copy` of the wrapped canonical `Tool` (`_install_served_names`) with the canonical schema. The other routes lose guarantees: a new extension tool that calls a core `*_response` function skips the name-keyed lifecycle lock, publication guard and cost accounting; an override removes the core handler and must copy upstream internals to delegate; and hints come back with canonical tool and parameter names.

The chosen seam keeps everything keyed on the canonical name: a parameter-mapped alias is served by a translating callable that validates the alias's arguments, renames and pins them, and calls the canonical tool's wrapped callable (captured at install), so the lock, guard, cost accounting, extractors and tier apply exactly as for the canonical name. A readiness spike on 2026-09-30 proved this through the real server and FastMCP `call_tool`.

## Requirements

1. **Declaration.** A new constant `EXTENSION_TOOL_PARAMETERS: {alias: {"rename": {alias_param: canonical_param}, "fixed": {canonical_param: value}}}` applies to names declared in `EXTENSION_TOOL_ALIASES`, and `declared()` counts it. `rename` lists only renamed parameters; every other canonical parameter that is not fixed passes through under its own name. The alias's parameter names (renamed plus pass-through) must be unique; an alias parameter may reuse a canonical name only when that canonical name is itself renamed away (so a swap such as `{set_id: wave_id, wave_id: change_id}` is valid). Refused: an entry for a name that is not an alias; a rename target that is not a canonical parameter or appears twice; a fixed name that is not a canonical parameter or is also renamed; a fixed value the canonical field's type rejects (checked by the server against the live schema); an alias parameter named `kwargs` or colliding with a model attribute (`model_*`); a mapping on an alias of a runner or edit-gate tool; and hiding a canonical name that has no alias without fixed parameters. A refused declaration serves only runner tools, as today.
2. **Served schema and call.** The alias's argument model is derived from the canonical tool's normalized (exact) argument model, with fields renamed and fixed ones removed, carrying annotations, defaults, descriptions and the required list (not `Tool.from_function` on a generated signature, which loses the exact handling). The translator refuses any argument outside the alias's parameters with `unknown_arguments` naming the alias parameters, and never forwards it, so an extra can neither collide with a renamed parameter nor override a pinned one. It then renames in one pass, adds fixed values, and calls the canonical tool's wrapped callable captured at install (with `functools.wraps`, so middleware markers carry over), not a per-call table lookup. The alias takes the canonical tier and annotations; its description keeps the canonical text and parameter names, stated in the spec.
3. **Hints.** List hints (`next_tools`, `recovery_tools`) name an alias only if it has no fixed parameters; if the only aliases are pinned, the canonical name stays. In `usage` and `recovery_usage`, a call `canonical(arg=..., ...)` is rewritten to an alias, preferring one without fixed parameters, by keyword name (values keep their source text); a pinned alias is chosen only when every fixed parameter is present with the pinned value (parsed as a Python literal) or absent with a canonical default equal to the pinned value; parameters are renamed in a single pass. Call occurrences of a canonical name that has a mapped alias are excluded from the existing whole-name substitution, so a call is never given the alias name with canonical parameter names; other occurrences map to the preferred alias without fixed parameters. A call that cannot be rewritten (unparseable, positional arguments other than a lone `...`, duplicate keywords, `**` unpacking, or only pinned aliases that do not match) keeps the canonical form, which names an unserved tool when the canonical name is hidden; the spec lists these cases. Outside the four hint fields, `data`, diagnostic messages and descriptions keep canonical names, as today.
4. **Override delegation.** For each name a module declares in `EXTENSION_OVERRIDES`, the staging surface offers `core_handler(name)` during `register`, returning the core tool's handler captured before argument normalization and middleware (registration runs before both), so delegating through the override's own name-keyed wrapper takes the lock and records cost once. Asking for a name the module did not declare as an override raises.
5. **Docs and provenance.** `docs/specs/mcp-tool-surface.md`: a row for the constant, the schema and refusal rules, the hint rule (including the pinned-alias rule), provenance of mappings, `core_handler` under Overrides, that descriptions keep canonical parameter names, and that the stdlib roster may emit allow rules for an alias the server later refuses (nothing is served under it). `docs/architecture/threat-model.md`: a mapped alias is a translator into the wrapped canonical callable, keeps the canonical lock, guard and cost, and never forwards unknown arguments. `wf_server_info` provenance lists parameter mappings.
6. **Platforms.** Windows, macOS, Linux and WSL2 behave the same (in-process schema and call translation).
7. **Transition.** Additive; an empty declaration changes nothing. CHANGELOG under `### Added` in `## [Unreleased]`.

## Scope

**Problem statement:** a distribution with a renamed vocabulary cannot serve a tool whose parameter names match its vocabulary while keeping the canonical tool's lock, guard, accounting and tier, and an override cannot delegate to the core handler without copying internals.

**In scope:**

- `mcp_tool_extensions` (constant, `declared()`, validation), `wf_server/server_impl.py` (`_install_served_names`, the staging surface, `_rewrite_served_names` and the served-name rewrite, provenance); tests; spec, threat model, CHANGELOG.

**Out of scope:**

- Renaming parameter names inside response `data`, prose or tool descriptions.
- A public accessor that calls a served canonical tool by name from a new extension tool (the mapped alias covers the requested ground).
- Lifecycle-lock opt-in for arbitrary new extension tools.
- Test-suite portability under a distribution's declarations (`1zim4`).

## Acceptance Criteria

- [x] AC-1: a declared mapping serves the alias with the renamed schema (fixed parameters removed; annotations, defaults and required list carried over; titles normalized in the comparison), including the swap `{set_id: wave_id, wave_id: change_id}` on `wf_add_change` and a pin `phase="prepare"` on `wf_review_wave`; a call through FastMCP `call_tool` reaches the canonical behaviour with translated arguments; an extra argument (including one named like a fixed or renamed-away canonical parameter) is refused with `unknown_arguments` and never reaches the canonical body; each refusal case in Requirement 1 refuses at server start and serves only runner tools.
- [x] AC-2: a mapped alias of a lifecycle-locked, publication-guarded tool takes the lock once (observed held inside the canonical body), fails fast during an upgrade checkpoint, records cost once under the canonical name, and has the canonical tier in the allow rules.
- [x] AC-3: hints: with only a pinned alias declared, list hints keep the canonical name; a `usage` call is rewritten to a pinned alias only when the pinned parameter is present with the same value or absent with an equal canonical default (an absent parameter whose default differs, and a present one that differs, both keep the canonical form); a swap renames in one pass; a canonical name with a mapped alias is never rewritten to the alias name with canonical parameters.
- [x] AC-4: an override that calls `core_handler(name)` returns the core result with the lock taken once and cost recorded once; asking for an undeclared name raises at registration.
- [x] AC-5: the spec, threat model, provenance and CHANGELOG describe the mapping, the hint rules and delegation; the census classifies the new constant and the declaration tests save and restore it.
- [x] AC-6: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Constant, `declared()` and declaration validation.
- [x] Alias argument model and translator; capture at install.
- [x] Hint rules (list and usage) and exclusion from the whole-name rewrite.
- [x] Staging `core_handler`.
- [x] Provenance; docs; CHANGELOG.
- [x] Tests through FastMCP `call_tool` (driver modes), refusal fixtures, census classification.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Alias mapping | implementer | readiness | |
| Override delegation | implementer | alias mapping | same files |
| Review | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, security-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `docs/specs/mcp-tool-surface.md`, `docs/architecture/threat-model.md`

## Affected Architecture Docs

`docs/architecture/threat-model.md` (extension declarations row).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The core capability, with extras refused |
| AC-2 | required | Controls follow the canonical name |
| AC-3 | required | Hints never change a call's meaning |
| AC-4 | required | Delegation without copying internals |
| AC-5 | required | Contract docs |
| AC-6 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Second independent reverification of the follow-up: NEW-1 and NEW-2 resolved (20,000 fuzzed calls kept every value; Python 3.11 and 3.13). Timing correction: the worst case found near the caps is about 0.36 s CPU per hint field (64 nested candidates each wrapping about 8 KB that fails to parse), not the 0.05 s stated in the row below; still bounded by 64 scans and 64 parses. Coordinator pinned the scanner's comment and triple-quote handling with four cases in `test_unparseable_call_bound_respects_quotes_and_escapes` (a `)` inside a comment, a comment without a newline, a `)` and a lone quote inside `'''` and `"""` strings); each of three scratch mutations (comment handling removed, unterminated comment not running to the end, triple-quote detection removed) fails the test. Known low residuals: a Python 3.12+ nested same-quote f-string inside hint text can misbound (no producer emits it); whitespace before `(` is dropped on a mapped rewrite (pinned, cosmetic) | `tests/test_extension_tool_modules.py`; focused 100 OK |
| 2026-10-01 | Reverification follow-up on DEL-1ZIM3-HINT-VALUE-REWRITE. NEW-1 (super-linear parsing): each candidate's extent now comes from one linear quote-aware scan (`_call_text_end`, now also triple quotes and `#` comments) and is parsed at most once; nested candidates inside an accepted span are skipped; `_HINT_CALL_ATTEMPTS = 64` candidates per string, after which the rest is left unchanged, and strings over `_HINT_CALL_TEXT_LIMIT = 8192` characters are left unchanged. NEW-2: `_alias_call_text` renames keyword names in place from the keyword node offsets (UTF-8 columns mapped to characters) and removes pinned keywords with their separating comma, keeping parentheses, comments and newlines; a removal that would touch a comment keeps the canonical form. Spec wording updated. Timings after: `a(`x400 0.013 s, x1600 0.036 s, the 1,530-char glob 0.014 s, a 60k hint unchanged in under 1 ms, worst case at the cap about 0.05 s | `tests/test_extension_tool_modules.py`: `test_call_parsing_is_bounded` (parse-count spy; before the fix every input exceeded 64 parses), `test_hint_strings_over_the_length_cap_are_unchanged`, `test_mapped_calls_keep_every_byte_but_keyword_names` and `test_pinned_keywords_are_removed_in_any_position` (6 subtest failures before the fix), `test_unparseable_call_bound_respects_quotes_and_escapes`. Scratch mutants (no quote handling, no escape skip, unknown unparseable protected, no attempt cap, no length cap, no comment fallback) each failed a named test. Focused file default, `--profile declared` and `--profile second`: 0 failures |
| 2026-10-01 | Delivery repair DEL-1ZIM3-HINT-VALUE-REWRITE: hint rewriting no longer changes argument values. `_hint_calls` (replacing `_rewrite_alias_calls`) finds top-level call spans for any callee: a `name(` that parses as a call of that name, or a served or mapped name followed by `(` after optional whitespace; known call text that does not parse ends at its matching `)` (quote-aware) or, with none, at the end of the string. Inside a span only the callee changes (mapped alias call text, else the whole-name map) and the argument text is byte-identical; name matching applies only between spans. An unknown name followed by whitespace and `(` stays prose. Spec hint paragraph gains the never-rewrite sentence. In-process string handling only, so Windows, macOS, Linux and WSL2 behave the same | `tests/test_extension_tool_modules.py`: `test_served_call_hints_never_rewrite_argument_values` in `ParameterMappedAliasTests` and `HiddenMappedAliasHintTests` (FastMCP `call_tool`, `usage` and `recovery_usage`), `ServedNameRewriteTests` mapped, whole-name, unparseable and prose cases; 15 subtest failures before the fix, focused file 95 OK, `--profile declared` and `--profile second` 0 failures |
| 2026-10-01 | Reverification round (independent reviewer, scratch copy): all three delivery findings resolved, every original repro and mutant killed, full suite 10252 OK in the scratch copy. Coordinator follow-ups from its non-blocking notes: a test pins the whitespace and newline handling around a call's `(` (the reviewer's surviving `\s*` mutant now fails `test_whitespace_before_the_call_parenthesis_is_still_a_call`, run in a scratch framework copy); the spec and Requirement 3 now list a positional argument beside keywords (`canonical(..., key=value)`, as `memory_add`'s duplicate hint emits), a nested canonical call and a newline before `(` among the kept-canonical cases, and Requirement 3's closing sentence names `data`, diagnostic messages and descriptions instead of prose. No product code changed | `tests/test_extension_tool_modules.py`; `docs/specs/mcp-tool-surface.md`; focused file 89 OK |
| 2026-10-01 | Delivery repair. DEL-1ZIM3-FIXED-VALUE-UNVALIDATED: fixed values are validated with `strict=True` (`_validated_fixed_value`) and the translator forwards the validated value, deep-copied per call. DEL-1ZIM3-HIDDEN-NAME-HINTS: calls are rewritten by keyword names keeping value source text (literal evaluation only for pinned matching); duplicate keywords, `**` and unparseable calls keep the canonical form; prose (no `(` follows) for a mapped name maps to its preferred unpinned alias; `served_name_map` prefers a plain alias, then an unpinned mapped one; the spec states when canonical call text remains and that it may then name a hidden tool. DEL-1ZIM3-UNPINNED-GUARDS: tests for `core_handler` after register, extension-tool alias checks against the staged table, leading-underscore names and per-call pin copies; Python keyword parameter names are refused. The staging surface no longer exposes the core table as an attribute (only `core_handler` read it). New tests failed before their fixes (11 pre-fix failures; duplicate keywords pre-fix produced `fork_add_wave(set_id='b')`); guards already present were proved by scratch mutation. In-process only, so Windows, macOS, Linux and WSL2 behave the same | `HiddenMappedAliasHintTests`, `ParameterMappedAliasTests`, `ExtensionRefusalTests`; focused 88 OK; full suite 10252 OK |
| 2026-10-01 | Full suite after implementation: one failure outside this change, `PhaseCleanupSetupBaselineTests.test_non_transient_results_are_not_retried` (waits `[0.001]`). Cause: the test patched `time.sleep` globally, and a subprocess waited on with a timeout during cleanup polls through `time.sleep` (stdlib first poll 0.0005 doubled to 0.001) when the child outlives the first poll under load. Test-only repair: the helper records only sleeps whose first non-mock caller is `_record_setup_baseline`; negative control: a 0.001 sleep from another function is ignored, the retry loop's 2.0 is recorded. No product code changed | `tests/test_upgrade_wavefoundry.py` `_cleanup_with_assessments`; file 567 OK |
| 2026-10-01 | Implemented. `EXTENSION_TOOL_PARAMETERS`, `pinned_aliases()`, `declared()` and the shape checks in `mcp_tool_extensions`; in `server_impl`, `_alias_parameter_problems` (canonical parameter, fixed type via the live field, duplicate names, model attributes) runs before install, `_mapped_alias_tool` derives the alias model from the canonical exact model and wraps the canonical callable as served, `_alias_call_specs` and `_rewrite_alias_calls` implement the usage rule, the staging surface offers `core_handler`, and provenance gains `parameters`. `name(...)` placeholders are rewritten only to an alias without fixed parameters (no parameter names are given, so Requirement 3 holds); the refusal envelope carries `data.supported_arguments`. In-process only, no path or subprocess behaviour, so Windows, macOS, Linux and WSL2 behave the same. Tests: `ParameterMappedAliasTests` (new `params` driver mode through `build_server` and FastMCP `call_tool`), 15 refusal fixtures in `ExtensionRefusalTests`, `ServedNameRewriteTests` hint cases, `DeclarationConstantCensusTests`, declaration helpers save and restore the new constant. Mutation runs in scratch copies: 15 of 16 mutants failed a named test; the survivor (fixed values merged after caller arguments) is unreachable while extras are refused | `tests/test_extension_tool_modules.py`; focused file 0 failures |
| 2026-10-01 | Implementation notes from readiness: when a canonical name has both a plain alias and a pinned mapped alias, the parameter-aware rewrite treats the plain alias as an identity mapping; the translator must detect extras itself (from the full dump or `__pydantic_extra__`), since the exact model allows extras | Readiness review |
| 2026-09-30 | Readiness round 1: spike (lanes reviewer, real `build_server`, FastMCP `call_tool`) proved the approach: alias model derived from the canonical exact model, lock held once in the canonical body, cost once under the canonical name, upgrade guard applied, canonical tier, extras refused when kept under `kwargs`. Red-team and code-reviewer blocked on the hint rule: an absent fixed parameter means the canonical default (probed: a dry-run `wf_add_change` hint became a `mode=create` alias call), and a pinned-only alias would capture list hints. Repaired: absent counts only when the default equals the pin; list hints prefer unpinned aliases; translator refuses extras itself (a plain `ArgModelBase` drops them, probed); pass-through parameters need no identity entries; swaps allowed; hiding requires an unpinned alias; capture the canonical callable at install; `declared()` includes the constant; docs list completed | Prepare council and lane review |
| 2026-09-30 | Planned from the downstream "Tool-name seams" note, verified: `_install_served_names` serves an alias as `table[canonical].model_copy(update={"name": alias})`, sharing the wrapped callable and schema; `_rewrite_served_names` rewrites tool names only in hint fields; replacements capture the core tool into `_EXTENSION_REPLACED_CORE` and serve it under `alias_for_core`, overrides capture nothing; FastMCP validates arguments through the tool's own `fn_metadata`, so a renamed schema needs its own argument model. Request 4 shipped in 1zicq (1zhme) | Code reads |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Parameter-mapped aliases rather than a public call-by-name accessor | Every control stays keyed on the canonical name with no new opt-in surface | Accessor plus lifecycle-lock opt-in (the note's alternative) |
| 2026-09-30 | `core_handler` returns the pre-middleware handler | The override's own wrapper already applies the name-keyed controls; a wrapped handler would lock twice | Return the wrapped handler |
| 2026-09-30 | Fixed arguments are part of the same constant | One translation path | Separate constant; a replacement delegating through `core_handler` (loses canonical keying unless declared write) |
| 2026-09-30 | Derive the alias model from the canonical exact model | `Tool.from_function` re-derives the model and loses the exact/extra handling (spike) | Generated signature |

## Risks

| Risk | Mitigation |
| --- | --- |
| Argument model divergence (titles, defaults, `Annotated` metadata) | Field-by-field schema comparison in tests, titles normalized |
| Hint rewrite misreads a call | Literal parsing of `name(args)` in `usage`/`recovery_usage` only; unparseable calls keep the canonical form |
| Double application of name-keyed wrappers | Tests observe one lock acquisition and one cost record |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
