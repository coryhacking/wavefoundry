# Parameter-Mapped Aliases Rename Their Parameter Names in Response Data and May Declare Their Own Description

Change ID: `1zimm-bug alias-parameter-names-in-response-data`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zime downstream-gap-fixes

## Rationale

Wave 1zim3 (change `1zim0-feat extension-alias-parameter-mapping`) added `EXTENSION_TOOL_PARAMETERS`. A distribution can serve an alias whose parameters are renamed (`rename: {alias_param: canonical_param}`) or pinned (`fixed`). `_mapped_alias_tool` builds a `translated` callable that maps the alias's arguments onto the canonical call. The hint rewrite (`_rewrite_served_names` with `alias_calls`) renames keyword names inside `usage` and `recovery_usage` calls, never values, and is bounded by `_HINT_CALL_TEXT_LIMIT` (8192 characters) and `_HINT_CALL_ATTEMPTS` (64 candidates). 1zim0 left response `data` with canonical names on purpose: its Requirement 3 says "`data`, diagnostic messages and descriptions keep canonical names", and its Scope excluded "Renaming parameter names inside response `data`".

A downstream fork reported this as an open gap. A caller of an alias sends `set_id` and gets back `data.wave_id` (most lifecycle handlers echo their arguments at the top of `data`, for example `{"wave_id": ..., "mode": ...}`), so the response does not use the vocabulary of the tool the caller called. The 1zim3 test distribution's swap alias shows the sharpest case. `fork_add_wave` renames `set_id` to `wave_id` and `wave_id` to `change_id`, so the echoed `wave_id` in `data` means the caller's `set_id`, while the caller's own `wave_id` comes back as `change_id`.

This change renames the echoed parameter names for an aliased call only, under the same discipline as the hint rewrite: names, never values; only that alias's own parameters; core callers untouched.

The same report names a second gap in the alias's vocabulary: its description. `_mapped_alias_tool` builds the served tool with `canonical_tool.model_copy(update={...})`, replacing `name`, `fn`, `fn_metadata` and `parameters` and keeping the canonical `description` (the handler docstring) unchanged. An alias that renames parameters is therefore described in the canonical names; the report's example is an alias `wf_get_item(container_id, item_id)` of `wf_get_change`, whose description still says to provide `wave_id` without `change_id` for bulk. Rewriting a docstring automatically is not safe (it is free prose; the same token can name a parameter, a field or a tool), so a distribution states the alias's description itself, in an optional `description` key of its `EXTENSION_TOOL_PARAMETERS` entry. Every entry there is for an alias in `EXTENSION_TOOL_ALIASES` (`_parameter_mapping_problems` refuses any other name, including an `alias_for_core`), and the entry kinds are `rename` and `fixed`; any other key is refused today. Core tool descriptions run to about 11,600 characters (`wf_graph_report`), measured over the `@mcp.tool` docstrings in `wf_server/`.

## Requirements

1. **Where.** Only in `_mapped_alias_tool`'s `translated` callable, on the result of the canonical call. `_rewrite_served_names` is unchanged (its test `test_rewrites_only_the_hint_fields_and_never_mutates` keeps pinning that `data` is untouched there), so a call to the canonical name, a plain alias without `EXTENSION_TOOL_PARAMETERS`, a replacement and a core-behaviour alias return byte-identical responses to today.
2. **Which keys.** Only the TOP-LEVEL keys of `result["data"]`, and only a key equal to a canonical parameter that the alias renames (a `rename` value). Each is replaced by its alias name (the `rename` key) in one simultaneous pass, so a swap (`set_id` to `wave_id`, `wave_id` to `change_id`) maps `wave_id` to `set_id` and `change_id` to `wave_id` without chaining. Keys that are not renamed parameters, including parameters of the canonical tool that the alias keeps under the same name, are untouched. A pinned (`fixed`) parameter's echoed key keeps its canonical name, since the alias has no parameter to name it after. Nested objects and lists inside `data` are not walked: a nested `wave_id` (for example inside a list of changes) is a property of a record, not an echo of the call.
3. **Values never change.** Every value, including string values that happen to equal a parameter name, is carried over by identity. Key order is preserved, with each renamed key in its original position.
4. **Collisions keep the canonical form.** If the renamed result would contain the same key twice, the whole `data` mapping is left unchanged and the response is otherwise served as today. This happens when a renamed key's alias name is already a top-level key that is not itself renamed away. Silently dropping a value is never acceptable.
5. **Shape guards.** When the result is not a dict, has no `data`, or its `data` is not a dict, it is returned unchanged. The input is never mutated: a renamed `data` is a new dict in a shallow copy of the result. The canonical callables are synchronous today; if `target(**call)` returns an awaitable, it is returned unchanged rather than renamed, and a test pins that every canonical tool reachable by a mapped alias is synchronous, so a future coroutine handler is noticed.
6. **The refusal envelope follows the same rule.** The unknown-argument refusal that `translated` builds already reports `data.supported_arguments` in alias names; no further change there.
7. **Spec and changelog.** The parameter-mapped alias paragraph in `docs/specs/mcp-tool-surface.md` states the rule: for a mapped alias call, top-level `data` keys that echo renamed parameters use the alias names; nested `data` and diagnostic messages keep canonical names; the description is the canonical one unless the entry declares its own (Requirement 8). The `EXTENSION_TOOL_PARAMETERS` row of the declaration table names the optional `description` key. The closed wave 1zim3's records are historical and are not edited; this change's Decision Log records that it supersedes the `data` clause of 1zim0's Requirement 3. 1zim3 is unreleased, so the existing `## [Unreleased]` `### Added` 1zim3 bullet is amended with this rule instead of adding a `### Changed` bullet. The amended bullet replaces its clause "tool descriptions keep canonical parameter names" with "tool descriptions are the canonical ones unless the entry declares `description`".
8. **An alias may declare its own description.** An `EXTENSION_TOOL_PARAMETERS` entry accepts an optional `description` key beside `rename` and `fixed`:
   - **Validation** (`mcp_tool_extensions._parameter_mapping_problems`, so `declaration_problems` and `validate_declaration` refuse it before anything is served): the value must be a `str`, non-empty after stripping whitespace, and at most 16,384 characters (the cap clears the longest core description with room, and keeps a runaway declaration out of every tool listing). An entry that declares `description` must also declare a non-empty `rename` or `fixed`; a `description` on an entry with neither is refused with a message saying a plain alias keeps the canonical description. It is not required to differ from the canonical description: an identical text is harmless, and the stdlib declaration check cannot read the canonical docstring.
   - **Serving:** `_mapped_alias_tool` sets the served tool's `description` to the declared text, unchanged (no stripping or rewriting); without the key the canonical description is kept, as today. Plain aliases, core-behaviour aliases (`alias_for_core`) and replacements are unaffected, and the canonical tool keeps its own description.
   - **Provenance:** each `wf_server_info` `extensions.parameters` entry gains `"description"`: the declared text, or `null` when none is declared. The stock server's `parameters` stays `{}`.
   - **Declaration shape:** no new constant, so `tests/record_layout_support.SHIPPED_DECLARATION` and the profile guard from wave 1zimb (`declaration_support.declaration_profile_mismatch`) are unchanged; a profile asset that declares a description is compared like any other entry value. The shipped `declared.json` profile is not changed.
   - A distribution that declares `description` needs a framework that includes this change: an older server refuses the entry as an unknown key and serves only runner tools, which fails closed.
9. **Platforms.** In-process dict and string handling only; Windows, macOS, Linux and WSL2 behave the same.

## Scope

**Problem statement:** a parameter-mapped alias returns its arguments echoed under the canonical parameter names, so its responses do not match its own schema.

**In scope:**

- `wf_server/server_impl.py` (`_mapped_alias_tool`, a small rename helper, the provenance `parameters` entry); `mcp_tool_extensions.py` (`_parameter_mapping_problems` and the `EXTENSION_TOOL_PARAMETERS` comment); `tests/test_extension_tool_modules.py` (the `params` driver mode, `ParameterMappedAliasTests`, the invalid-declaration table and the provenance test); the spec and CHANGELOG.

**Out of scope:**

- Renaming inside nested `data` or in diagnostic messages, and rewriting the canonical description automatically.
- A `description` for plain aliases, core-behaviour aliases or replacements.
- Renaming tool NAMES inside `data` (for example a `next_step` value naming a canonical tool), which are values.
- Plain aliases, replacements and core-behaviour aliases (no parameter mapping).

## Acceptance Criteria

- [x] AC-1: through the real `build_server` and FastMCP `call_tool` (the 1zim3 `params` driver), a renaming alias call returns the echoed parameter under its alias name with the same value. The swap alias `fork_add_wave` returns `set_id` and `wave_id` carrying the caller's `set_id` and `wave_id` values respectively, and no `change_id` key. Each assertion fails on the current tree. The `params` driver's `wf_add_change_response` spy returns `data` that echoes its `wave_id`, `change_id` and `mode` arguments at top level, as the real handler does.
- [x] AC-2: the same call made under the canonical name, and a plain alias call, return `data` byte-identical to the stock server's for the same arguments.
- [x] AC-3: a unit test of the rename helper shows (i) nested `data` objects and lists keep their keys; (ii) a string value equal to a parameter name is unchanged; (iii) key order is preserved; (iv) a pinned parameter's echoed key keeps its canonical name; (v) a collision leaves `data` unchanged; (vi) the input result is not mutated (compared by serialization before and after); (vii) a non-dict result or `data` is returned unchanged.
- [x] AC-4: a test enumerates every canonical tool targeted by a mapped alias in the test distribution and asserts its callable is not a coroutine function.
- [x] AC-5: the spec's alias section and the amended `### Added` 1zim3 CHANGELOG bullet state the new `data` rule and its limits, and the optional `description` key with its validation.
- [x] AC-6: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-7: through the real `build_server` (the 1zim3 `params` driver), a mapped alias declared with `description` is listed with exactly that text, while the canonical tool, a plain alias of it and a mapped alias without `description` keep the canonical description; after `wf_reload_mcp` the alias still carries the declared text; `wf_server_info` reports the text in the alias's `extensions.parameters` entry and `null` for an entry without one. The first assertion fails on the current tree.
- [x] AC-8: the declaration is refused, naming the alias, for a `description` that is not a string, is empty, is whitespace only, or exceeds 16,384 characters, and for a `description` on an entry with neither `rename` nor `fixed`; a 16,384-character description is accepted. Each refusal is a case in the existing invalid-declaration table and asserts its own message. Today every `description` key is refused as an unknown key, so the accepting case and each message assertion fail on the current tree.

## Tasks

- [x] Add a rename helper (top-level keys, simultaneous mapping, collision fallback, no mutation) and apply it in `translated` to the canonical result.
- [x] Extend the `params` driver to capture `data` for the renaming, swap and pinned aliases and for the canonical and plain-alias calls.
- [x] Unit tests for AC-3 and the synchronous-handler census for AC-4.
- [x] Accept and validate `description` in `_parameter_mapping_problems`; serve it from `_mapped_alias_tool`; add it to the provenance entry and update `test_provenance_lists_parameter_mappings` for the new key.
- [x] Tests for AC-7 and AC-8.
- [x] Spec and CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Data key rename | implementer | readiness | server_impl, alias translator only |
| Tests and spec | implementer | rename | |
| Review | code-reviewer, qa-reviewer, security-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

N/A. The change is confined to the alias translator in the MCP server module; the extension contract it adjusts is documented in `docs/specs/mcp-tool-surface.md`, which is updated.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The reported gap |
| AC-2 | required | Core callers must be unaffected |
| AC-3 | required | Names only, never values, never nested, never lossy |
| AC-4 | important | Guards the synchronous assumption the translator relies on |
| AC-5 | required | Distributions rely on the documented contract |
| AC-6 | required | Standard verification |
| AC-7 | required | The reported description gap |
| AC-8 | required | A declaration error must fail before anything is served |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Delivery-review repair round (C1). The test distribution's `fork_say` description now carries leading spaces and a trailing newline, and the listing, reload and provenance assertions compare it byte for byte, so serving a stripped or rewritten description fails `test_a_declared_description_is_served_only_on_its_alias` (mutant C1 killed) | `tests/test_extension_tool_modules.py` |
| 2026-10-01 | Implemented. `_rename_echoed_parameters` renames top-level `data` keys that are renamed canonical parameters to their alias names in one simultaneous pass (order kept, values by identity, collision or non-dict or awaitable result returned unchanged, input never mutated); `_mapped_alias_tool.translated` applies it to the canonical result only. `_alias_description_problems` validates the optional `description` (str, non-empty, not whitespace only, at most `ALIAS_DESCRIPTION_MAX_CHARS` = 16,384, and only with a non-empty `rename` or `fixed`); `_mapped_alias_tool` serves it unchanged; provenance entries gain `description` (null when absent). The `params` driver's `wf_add_change_response` spy now echoes `wave_id`, `change_id` and `mode` by the real signature; the test distribution gains `fork_say_plain` and `fork_get_change` (plain aliases) and a `description` on `fork_say`. Red first: in a scratch copy of the pre-change tree with the `description` key removed, the swap data, `say_call`, description and provenance assertions fail (4 failures); with the key present the original server refuses the declaration (setUpClass error) and all six refusal cases plus the accept-at-cap case fail; AC-2 and AC-4 pass on the old tree as regression guards. Spec paragraph, declaration row and the existing `### Added` 1zim3 CHANGELOG bullet amended | `wf_server/server_impl.py`, `mcp_tool_extensions.py`, `tests/test_extension_tool_modules.py` |
| 2026-10-01 | Extended with the alias description from the downstream report's fuller text. Verified: `_mapped_alias_tool`'s `model_copy` replaces `name`, `fn`, `fn_metadata` and `parameters` only, so the description is the canonical docstring; `_parameter_mapping_problems` accepts only `rename` and `fixed` and only names in `EXTENSION_TOOL_ALIASES`; provenance `parameters` entries are `{canonical, rename, fixed}` and `test_provenance_lists_parameter_mappings` pins them exactly; `SHIPPED_DECLARATION` lists constants only, so an entry key needs no change there; the longest core description is about 11,600 characters | `wf_server/server_impl.py`, `mcp_tool_extensions.py`, `tests/test_extension_tool_modules.py`, `tests/record_layout_support.py`, `tests/declaration_support.py` |
| 2026-10-01 | Planned from the downstream report (one-line description only). Verified: `_rewrite_served_names` rewrites only `next_tools`, `usage` and diagnostic recovery fields; `_mapped_alias_tool.translated` returns `target(**call)` unchanged; 1zim0's Requirement 3 and Scope kept `data` canonical by design; the `params` test distribution includes the `fork_add_wave` swap and pinned `fork_add_wave_now`; no handler registered in `register_mcp_surface` is a coroutine function | `wf_server/server_impl.py`, `docs/waves/1zim3 extension-alias-parameters/1zim0-feat extension-alias-parameter-mapping.md`, `tests/test_extension_tool_modules.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-01 | This change supersedes the `data` clause of 1zim0's Requirement 3 (data stays canonical) | The downstream fork reported canonical names in alias response data as a gap; 1zim3's records are closed and historical, so they are not edited | Edit the closed 1zim3 record |
| 2026-10-01 | Rename only top-level `data` keys that are renamed parameters of the called alias | Arguments are echoed at the top of `data`; nested keys are record properties whose meaning does not depend on the call, and renaming them could change the meaning of unrelated fields | Walk the whole `data` tree (renames record fields that only share a name) |
| 2026-10-01 | Apply in the translator, not in `_rewrite_served_names` | The translator is the only place that knows which alias was called; `_rewrite_served_names` also runs for canonical calls, which must stay unchanged | A flag on the shared rewrite (couples core calls to the alias table) |
| 2026-10-01 | An alias's description is declared, optional, capped at 16,384 characters, and allowed only on entries that rename or pin | Free-prose docstrings cannot be rewritten safely; a plain alias has the canonical parameters, so its canonical description is accurate; the cap clears every core description | Rewrite parameter names inside the canonical description (changes unrelated prose); require the text to differ from the canonical one (the stdlib check cannot read it, and identical text is harmless); allow it on every alias kind (widens the change to plain aliases and replacements, which the report does not ask for) |
| 2026-10-01 | A collision leaves `data` unchanged | A lossy rename would silently drop a value; keeping the canonical form is the same fallback the hint rewrite uses for a call it cannot rewrite | Prefer the renamed key (drops a value) |

## Risks

| Risk | Mitigation |
| --- | --- |
| A distribution already reads canonical keys from its alias responses | 1zim3 is unreleased, so no released behaviour changes; the amended CHANGELOG bullet states the rule, and the plain alias and canonical name keep today's keys |
| A top-level `data` key coincides with a parameter name but is not an echo | Only renamed parameters of the called tool are touched, so the coincidence would itself be a parameter of that tool; the collision rule prevents loss |
| A distribution declares `description` and runs an older framework | The older server refuses the unknown key and serves only runner tools (fail closed); the CHANGELOG bullet names the key and the version that accepts it |
| Wave 1zimf edits `server_impl.py`, `mcp_tool_extensions.py` (new `EXTENSION_*` constants, which do change `SHIPPED_DECLARATION`) and `test_extension_tool_modules.py` concurrently | Serialization points declared; rebase on whichever lands first |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
