# Declared Response Key Renames for Mapped Aliases

Change ID: `1zlty-enh extension-response-key-renames`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-02
Wave: 1zls8 extension-surface-two

## Rationale

A parameter-mapped alias (wave `1zim3`, `EXTENSION_TOOL_PARAMETERS`) lets a distribution call a core tool in its own vocabulary, and wave `1zime` (change `1zimm-bug alias-parameter-names-in-response-data`) made the response follow part of the way: `_rename_echoed_parameters` renames each top-level `data` key that echoes a renamed parameter. Everything else in the response keeps canonical names. Nested keys never change, and a top-level key that is not an echoed parameter never changes either, so a distribution alias of `wf_get_change` that calls changes "items" in its parameters still answers with `data.changes` and `change_id` inside each entry. When a rename would produce the same top-level key twice, `data` is left unchanged. The downstream distribution (Waveforge) asked for a declared response-key rename, nested keys included, so an alias answers fully in its own vocabulary without the distribution overriding the tool.

The rename must stay a key rename only. Wave `1zim3` established that hints never rewrite argument values, and the `1zime` echo rename carries values by identity; a declared response map must keep both properties and must not touch diagnostics or usage strings.

## Requirements

1. **Declaration shape.** An `EXTENSION_TOOL_PARAMETERS` entry may carry an optional `"response_keys"` mapping, `{path: new_key}`, beside `rename`, `fixed` and `description`. `path` names one key in the canonical response `data`, written in canonical names: dot-separated key segments, where a segment ending in `[]` means "each element of the list at this key", for example `{"changes": "items", "changes[].change_id": "item_id"}`. The last segment names the key to rename and carries no `[]`. `new_key` is the new name for that last key only; a path never moves a value to another level.
2. **Import-time validation (stdlib, in `_parameter_mapping_problems`).** Refused, each reported never raised: a `response_keys` that is not a mapping; a path that does not match `[A-Za-z_][A-Za-z0-9_]*(\[\])?(\.[A-Za-z_][A-Za-z0-9_]*(\[\])?)*` under `re.fullmatch` (never `re.match`, whose `$` accepts a trailing newline) or whose last segment ends in `[]`; a path with more than `RESPONSE_KEY_MAX_DEPTH = 8` segments; more than `RESPONSE_KEY_MAX_ENTRIES = 64` entries; a `new_key` that is not an identifier or equals the path's last segment; two entries with the same parent path and the same `new_key` (a static collision); and a single-segment path naming a canonical parameter that the entry's `rename` maps, whose top-level echo is already renamed by `1zime`; and a single-segment path whose `new_key` equals an alias parameter name in the entry's `rename` (a key of `rename`), which would collide with that parameter's echoed key. A rename may swap two sibling keys (`{"a": "b", "b": "a"}`), as `rename` may. `response_keys` alone, with no `rename` or `fixed`, is a valid mapped alias. The `description` rule widens: a `description` needs a non-empty `rename`, `fixed` or `response_keys`, so an alias that declares only `response_keys` may describe its renamed response.
3. **Runtime application.** The alias translator in `_mapped_alias_tool` applies `response_keys` to the canonical result's `data` after the call, together with the `1zime` echo renames, in one walk over the canonical structure. At each object reached by a declared parent path, all renames for that object are applied in one simultaneous pass in the same key positions, so a swap does not chain; at the top level the echo renames and the single-segment `response_keys` form that one pass. A path whose intermediate value is absent, or is not a dict (for a plain segment) or a list (for a `[]` segment), is skipped for that object; non-dict list elements are skipped. The walk follows the canonical paths, so a parent rename and a child rename on the same branch both apply.
4. **Runtime collision.** When an object's renamed keys would hold the same key twice (a declared new key equals an undeclared key already present), that object is left unchanged and its other renames still apply elsewhere; the response gains one advisory diagnostic `response_key_rename_skipped` naming the declared `response_keys` paths that were skipped, each once, and never an echo-renamed parameter. A collision caused only by echo renames (no `response_keys` path at that object) emits no advisory and keeps the `1zime` rule, so a declaration without `response_keys` stays byte-identical to today's output. Status, other diagnostics, `next_tools` and `usage` are never changed.
5. **Values and inputs.** Values are carried by identity, never re-serialized or rewritten; the input result is never mutated (along each renamed branch every dict and every list on the path is a new container, a shallow copy, so no list or dict of the input is shared and then changed). A result that is not a dict, has no dict `data`, or is awaitable is returned unchanged, as today. The unknown-arguments refusal the translator builds itself is not renamed.
6. **Accounting is canonical.** Cost recording, extractors, the lifecycle lock and the publication guard keep running inside the canonical callable, before the rename, keyed on the canonical name, as for the `1zime` echo renames.
7. **Provenance.** `wf_server_info.extensions.parameters.<alias>` reports `response_keys` (the declared mapping, sorted by path; empty when none).
8. **Docs.** `docs/specs/mcp-tool-surface.md`: the declaration table row and the **Parameter-mapped aliases** paragraph describe `response_keys`, its validation, the one-pass application, skips, collisions and the advisory, and the `description` rule names `response_keys` beside `rename` and `fixed`; **Provenance** names the new key. One `### Added` entry in `## [Unreleased]`.
9. **Platforms.** Windows, macOS, Linux and WSL2 behave the same: the change is pure dict and list manipulation with no file, process or path behaviour.
10. **Transition.** Additive. A declaration without `response_keys` produces byte-identical responses to today's; an older server refuses the unknown key and serves only runner tools, which the spec states.

## Scope

**Problem statement:** a mapped alias answers in canonical names except for top-level echoed parameters, so a distribution cannot serve a core tool fully in its own vocabulary.

**In scope:**

- `response_keys` validation and the two bounds constants in `mcp_tool_extensions.py`.
- The combined rename walk and the advisory in `wf_server/server_impl.py`, replacing the direct `_rename_echoed_parameters` call in the translator (the echo behaviour is preserved exactly), and the provenance key.
- Tests in `tests/test_extension_tool_modules.py`.
- The spec paragraph, table row, **Provenance** and the CHANGELOG entry.

**Out of scope:**

- Renaming keys outside `data`, renaming values, or rewriting diagnostic messages and usage strings.
- Response renames for plain aliases, replacements, core-behaviour aliases or the canonical name.
- Wildcard or pattern paths.

## Acceptance Criteria

- [x] AC-1: the stock declaration validates, and `declaration_problems` reports each refusal in Requirement 2 (non-mapping, bad path syntax including a path with a trailing newline, trailing `[]`, depth over 8, more than 64 entries, non-identifier or unchanged new key, static collision, single-segment path on a renamed parameter, single-segment `new_key` equal to an alias parameter name in `rename`); a swap validates; a `description` on an alias declaring only `response_keys` validates; `mcp_tool_roster` refuses the same declarations without starting the server.
- [x] AC-2: through `call_tool`, an alias of `wf_get_change` declaring `{"changes": "items", "changes[].change_id": "item_id"}` answers a bulk request (`wave_id` given, no `change_id`) with `data.items` whose entries carry `item_id`, every value identical to the canonical call's; the canonical name, a plain alias and the translator's own unknown-arguments refusal answer unchanged. Without the change the alias answers `data.changes`.
- [x] AC-3: a nested rename whose new key collides with a key already present leaves that object unchanged, applies the other declared renames, and adds exactly one `response_key_rename_skipped` advisory naming each skipped `response_keys` path once and no echo-renamed parameter; status, existing diagnostics, `next_tools` and `usage` are unchanged.
- [x] AC-4: echo renames from `rename` still apply at the top level exactly as before (including swaps and the whole-top-level collision rule), now in the same pass as single-segment `response_keys`; a top-level collision caused only by echo renames adds no advisory and the response is byte-identical to today's; the existing `1zime` echo tests pass unchanged.
- [x] AC-5: the input result is not mutated (a deep copy taken before the call equals the result object after it), values are the same objects, every list and dict on a renamed branch is a new container while leaf values keep their identity, and absent or wrongly typed intermediate paths are skipped without error.
- [x] AC-6: `wf_server_info.extensions.parameters.<alias>.response_keys` reports the declared mapping, empty when undeclared; the exact dicts in `test_provenance_lists_parameter_mappings` gain `"response_keys": {}` (or the declared mapping).
- [x] AC-7: the spec and CHANGELOG entry describe the declaration, validation, application, collisions and provenance.
- [x] AC-8: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add `RESPONSE_KEY_MAX_DEPTH`, `RESPONSE_KEY_MAX_ENTRIES` and the `response_keys` checks to `_parameter_mapping_problems` (path regex under `re.fullmatch`, the alias-parameter `new_key` refusal), allow the key in the unknown-key check, and widen `_alias_description_problems` to accept `response_keys`.
- [x] Replace the translator's `_rename_echoed_parameters` call with one walk applying echo renames and `response_keys`, with the collision advisory.
- [x] Add `response_keys` to the `extensions.parameters` provenance entry and update the exact dicts in `test_provenance_lists_parameter_mappings`.
- [x] Tests for AC-1 to AC-6 through `call_tool`, including a fixture core response with nested lists.
- [x] Spec and CHANGELOG entry.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Validation | implementer | readiness, `1zltx-enh extension-helper-surface` delivered | stdlib declaration module |
| Rename walk and provenance | implementer | validation | translator in `server_impl` |
| Docs | implementer | rename walk | spec and CHANGELOG |
| Review | code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer | implementation | |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `docs/specs/mcp-tool-surface.md`

The CHANGELOG entry is a root-level file and is listed here as prose only.

## Affected Architecture Docs

N/A: the rename runs inside the existing alias translator after the canonical callable returns; no boundary, wrapper order, flow or verification layer changes. The contract text lives in `docs/specs/mcp-tool-surface.md`.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | A careless map must be refused before serving |
| AC-2 | required | Answering in the alias vocabulary is the point of the change |
| AC-3 | required | Collisions must never lose or overwrite data |
| AC-4 | required | The delivered `1zime` echo behaviour must not change |
| AC-5 | required | Key renames must never change values or the canonical result |
| AC-6 | important | Provenance lets an operator see what the alias serves |
| AC-7 | required | Distributions need the contract documented |
| AC-8 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-03 | Delivery-review repair (N2, N4). N2, plan correction: AC-2's example path `changes[].change_id` is a plan error, because bulk `wf_get_change` entries carry `id`; the AC-2 evidence uses `changes[].id` (the AC text is left unchanged), and `change_id` collisions are covered by the nested-list fixture. N4: the `response_key_rename_skipped` advisory now reads "These declared response keys stayed canonical because a rename at the same object would duplicate a key already present: ..."; `ResponseKeyRenameTests` pins the phrase. Failing-first on the pre-repair tree: the collision test failed on the new phrase. Mutation (old wording restored) killed. Full suite in a fresh scratch copy (`run_tests.py --no-cache`): 10,813 tests OK | `wf_server/server_impl.py` (`_rename_response_keys`); `test_extension_tool_modules.py` (`ResponseKeyRenameTests.test_a_collision_keeps_that_object_canonical_with_one_advisory`) |
| 2026-10-03 | Implemented. `_parameter_mapping_problems` accepts `response_keys` and `_response_key_problems` checks the mapping type, `re.fullmatch` path syntax, trailing `[]`, `RESPONSE_KEY_MAX_DEPTH = 8`, `RESPONSE_KEY_MAX_ENTRIES = 64`, identifier and unchanged new keys, static collisions, a single-segment path on a renamed parameter and a single-segment new key equal to an alias parameter name; the `description` rule accepts `response_keys`. `server_impl` builds a key tree once per alias (`_response_key_tree`) and `_rename_response_keys` walks it with the echo renames in one pass (`_rename_echoed_parameters` now delegates to it, so the 1zime echo tests run through the new walk unchanged); the advisory `response_key_rename_skipped` names each skipped declared path once; provenance reports `response_keys` sorted by path. Deviations: AC-2 uses `changes[].id`, not `changes[].change_id`, because bulk `wf_get_change` entries carry `id`; the nested-list fixture (a spied `wf_add_change_response`) covers `change_id` collisions. The `description` refusal message now names `response_keys`, so the two existing needles were updated; the advisory site is added to the sanctioned set in `test_server_tools_lifecycle`. Failing-first on the unfixed tree: all 21 new response-key tests and the provenance test failed or errored. Mutations all killed: key not allowed, `re.match` for `fullmatch`, collision renamed anyway, echo collisions in the advisory, list renamed in place, alias-parameter refusal off, description rule not widened, provenance key dropped, translator kept on the echo-only rename, depth bound off. Suites: as recorded for 1zltx (default 10,811 OK; second and declared profiles pass) | `test_extension_tool_modules.py` (`ResponseKeyRenameTests`, `ResponseKeyServingTests`, `ResponseKeyDeclarationTests`, `EchoedParameterRenameTests`, `ParameterMappedAliasTests.test_provenance_lists_parameter_mappings`, `ExtensionRefusalTests`); `test_server_tools_lifecycle.py` |
| 2026-10-02 | Planned from the downstream request. Verified in the tree: `EXTENSION_TOOL_PARAMETERS` entries accept exactly `rename`, `fixed` and `description` (the request's "pin" is the `fixed` key); `_rename_echoed_parameters(result, rename)` renames only top-level `data` keys equal to a renamed canonical parameter, in one simultaneous pass, returning the result unchanged on any duplicate; the translator in `_mapped_alias_tool` applies it to `target(**call)`, where `target` is the canonical callable as served, so cost and lock run before the rename; `extensions.parameters` provenance reports `canonical`, `rename`, `fixed` and `description` | `mcp_tool_extensions.py` (`_parameter_mapping_problems`), `wf_server/server_impl.py` (`_rename_echoed_parameters`, `_mapped_alias_tool`, `_install_extension_tools`) |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-02 | Paths in canonical names with `[]` for list elements; the value is a bare new key name | Canonical paths make entries independent of each other and of application order; a bare target keeps every rename at its own level, so no value moves and no path can rewrite structure | Full target paths (`{"changes[].change_id": "items[].item_id"}`), which duplicate the parent rename and allow inconsistent targets; or a flat `{old: new}` applied at every depth, which renames unrelated keys that share a name |
| 2026-10-02 | Per-object collision leaves that object unchanged and adds one advisory | Data is never lost or overwritten, the rest of the response still answers in the alias vocabulary, and the caller learns which paths did not apply | Leave the whole `data` unchanged (the `1zime` rule), which hides every rename for one unrelated collision; or fail the call |
| 2026-10-02 | Echo renames and single-segment `response_keys` share one top-level pass; a `response_keys` path on an echoed parameter is refused | One pass keeps swap semantics consistent; refusing the overlap removes two declarations for one key | Apply the two maps in sequence, which makes the result depend on order |
| 2026-10-02 | Readiness amendments: an echo-only collision emits no advisory, so output without `response_keys` stays byte-identical; the advisory names only `response_keys` paths, each once; a single-segment `new_key` equal to an alias parameter name in `rename` is refused statically; the path regex runs under `re.fullmatch`; lists as well as dicts are copied along renamed branches; `description` is allowed on an alias that declares only `response_keys`; `test_provenance_lists_parameter_mappings` is named for the provenance change | Readiness review findings N5, N6 and N8. A `response_keys`-only alias serves a response whose shape the canonical description no longer matches, which is the reason the `1zime` rule lets `rename` and `fixed` aliases carry a description | Keep the `description` rule unchanged, which leaves a `response_keys`-only alias describing keys it no longer returns |
| 2026-10-02 | Bounds of 8 segments and 64 entries | The walk cost stays proportional to the declared paths and the response size; core responses nest well under 8 levels | No bound |

## Risks

| Risk | Mitigation |
| --- | --- |
| A core response shape changes and a declared path silently stops matching | Absent paths are skipped by design; the spec tells distributions to pin their alias responses in their own tests |
| A renamed key collides only on some responses | Requirement 4 and AC-3: that object stays canonical with an advisory naming the path |
| Agents read canonical names from hints and usage strings on an alias response | Hints and usage are out of scope by design (Requirement 4); the spec says so, matching the `1zime` rule for diagnostics |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
