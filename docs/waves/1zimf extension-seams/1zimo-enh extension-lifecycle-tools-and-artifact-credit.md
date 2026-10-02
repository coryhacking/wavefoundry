# Lifecycle Lock and Artifact Credit for Extension Tools

Change ID: `1zimo-enh extension-lifecycle-tools-and-artifact-credit`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zimf extension-seams

## Rationale

The lifecycle mutation lock is applied by `_wrap_lifecycle_mutation_lock` to the names in `_LIFECYCLE_MUTATION_LOCK_TOOLS`, a fixed frozenset of eleven core tools. A new extension tool cannot join it: `_install_extension_tools` refuses a new tool whose name is in any collection `_reserved_tool_name_collections` lists, and that set is one of them. So a distribution's team-workflow tool that writes wave lifecycle records runs unserialized against core lifecycle tools, and the spec's trust boundary says new extension tools "must not write wave lifecycle records directly", with no supported way to do it.

Derived-artifact credit has the same shape. `_wrap_first_party_tool_costs` credits written files through `_ARTIFACT_EXTRACTORS`, keyed by core name (the ten `wf_new_<kind>` tools use `_artifact_from_written_paths("path")`). Extension tools are cost-wrapped by prefix and record their request and response debit, but never get a credit, and `_ARTIFACT_EXTRACTORS` is a reserved collection too.

Both gaps close with declarations in `mcp_tool_extensions.py` that feed the existing name-keyed wrappers through main-pass keyword arguments, the pattern `_cost_pass_kwargs` and `_guard_pass_kwargs` already use for replacements, without editing the reserved collections.

## Requirements

1. **Two declarations.** `mcp_tool_extensions.py` gains, empty by default:
   - `EXTENSION_LIFECYCLE_TOOLS: tuple[str, ...]`: new extension tools that run under the lifecycle mutation lock;
   - `EXTENSION_ARTIFACT_PATH_FIELDS: Mapping[str, str]`: `{tool: data_field}`, naming the response `data` field that holds the repository-relative paths the tool wrote.
   `declared()` counts both.
2. **Validation (stdlib, in `declaration_problems`).** Each entry in either declaration must be a new extension tool: a key of `EXTENSION_TOOL_TIERS` with tier `write`. Refused: a name that is not declared in `EXTENSION_TOOL_TIERS`, a `read` tool, a core name (including override and replacement targets), an alias or `alias_for_core`, a runner tool, an edit-gate tool, a name declared twice in `EXTENSION_LIFECYCLE_TOOLS`, and a field that is not a non-empty identifier string. A core name's lock membership and extractors are fixed by core; overrides and replacements keep the core name's lock as they do today. An `EXTENSION_LIFECYCLE_TOOLS` that is not a tuple and an `EXTENSION_ARTIFACT_PATH_FIELDS` that is not a mapping are reported as problems, never raised.
3. **Server check.** `_install_extension_tools` additionally refuses a declared name that no module registered, with the same failure path as a tier without a tool (only runner tools stay served).
4. **Lock through the middleware.** The main `MIDDLEWARE` lock entry passes the declared lifecycle tools to `_wrap_lifecycle_mutation_lock` as an extra name set (a `_lock_pass_kwargs` helper beside `_cost_pass_kwargs`), so a declared tool gets exactly the core wrapper: strict root resolution, the non-blocking OS lock, the `lifecycle_mutation_locked` busy response naming the tool, and, after wave `1zimc`, the hold registered in `runtime_lock`'s process-hold registry and the re-entry behaviour `1zimc` specifies. `_LIFECYCLE_MUTATION_LOCK_TOOLS` is not mutated; `_CORE_BEHAVIOUR_MIDDLEWARE` is unchanged.
5. **Credit through the cost wrapper.** The main cost pass receives `{tool: _artifact_from_written_paths(field)}` for each declared tool (merged into `_cost_pass_kwargs`), and the wrapper uses it only for names absent from `_ARTIFACT_EXTRACTORS`. The credit contract is the core one: `status == "ok"` only; the field may hold a path string, a list of strings or `{"path": ...}` mappings, or a mapping with `path`; each path must resolve inside the repository root to an existing file; each artifact is floored at zero against the request tokens; the replay identity is the request-and-response digest. `_ARTIFACT_EXTRACTORS` is not mutated. The wrapper does not prove that the tool wrote a credited file; the declaration is the distribution's assertion, as core's extractors are core's, and the spec says so.
6. **Aliases and hidden names.** An alias (plain or parameter-mapped) of a declared tool is a copy of the wrapped tool, so it shares the lock and credit keyed on the canonical name. A declared tool may be hidden when it has an alias, as today.
7. **Name-keyed set audit.** The change records, in its Progress Log, each name-keyed set a declared tool passes through and its disposition: `_LIFECYCLE_MUTATION_LOCK_TOOLS` (extended by the pass set, not edited), `_COST_EXEMPT_TOOLS` (a declared tool is never exempt; it is reserved), `_ARTIFACT_EXTRACTORS` (extended by the pass map), `_COST_FOCUS_EXTRACTORS` and `_STATE_SOURCE_EXTRACTORS` (unchanged: no extension entry), the publication writer registry (unchanged: write-tier extension tools already consult the checkpoint), `extractor_free` (applies only to replacements; a declared tool is never a replacement), the setup-notice skip set (unchanged), and the roster tiers (unchanged: declared tools are already `write`); and, read by tool name inside core handlers or the registry and unchanged because no declared tool is in them: `_CONTEXT_RETRIEVAL_TOOLS`, `_INDEXED_CONTEXT_TOOLS`, `_REFERENCE_ONLY_GRAPH_TOOLS`, `_LIFECYCLE_CONTEXT_STAGES` and `_TRACKING_CONTEXT_TOOLS` (a declared lifecycle tool records only its cost-wrapper debit and credit, with no stage attribution or focus move), `mcp_tool_roster.TOOL_TIERS` and `RUNNER_TOOLS`, `render_platform_surfaces._RENAMED_MCP_TOOLS`, the `wf_prepare_wave` `readiness_receipts` special case in the lock and guard responses, and the served-name rewrite skip set `_EXTENSION_REPLACED_CORE`.
8. **Write tier is preserved.** Nothing in this change lets a declaration lower a tier, and both declarations require `write` (Requirement 2).
9. **Provenance.** `wf_server_info.extensions.declaration` adds `lifecycle_tools` (sorted list) and `artifact_path_fields` (sorted mapping); both are empty for the stock declaration.
10. **Trust boundary text.** The spec's sentence that new extension tools "must not write wave lifecycle records directly" becomes: a new extension tool that writes wave lifecycle records must be declared in `EXTENSION_LIFECYCLE_TOOLS`. The threat model row for extension modules gains the same sentence.
11. **Platforms.** Windows, macOS, Linux and WSL2 behave the same: the lock is the existing `runtime_lock` OS lock (`msvcrt` on Windows, `fcntl` elsewhere, including WSL2 on its own filesystem), and the credit reads only file sizes of contained paths. Path fields use `/` separators; the existing `_artifact_file_token_list` resolves them on every platform.
12. **Profile coverage.** `SHIPPED_DECLARATION` in `tests/record_layout_support.py` lists both new constants with their empty defaults, so `test_declaration_module_ships_empty` and the expected-profile guards (wave `1zimb`) cover them; the whole suite passes under `run_tests.py --profile declared`.
13. **Transition.** Empty declarations leave the served surface, wrapper application and provenance shape unchanged apart from the two new empty provenance keys.

## Scope

**Problem statement:** a distribution's extension tool cannot take the lifecycle mutation lock or earn derived-artifact credit, because both are keyed on reserved core-name collections.

**In scope:**

- The two declarations and their validation in `mcp_tool_extensions.py`, which `mcp_tool_roster` already applies through `validate_declaration` without starting the server.
- The lock and cost pass keywords, the registration check and provenance in `wf_server/server_impl.py`.
- Tests in `test_extension_tool_modules` with fixture extension modules; the reserved-collection census confirmed.
- `docs/specs/mcp-tool-surface.md` (declaration table, a **Lifecycle tools and artifact credit** paragraph, **Failure**, **Provenance**, **Trust boundary**), the threat model row, the current-state wrapper paragraph, one `### Added` entry in `## [Unreleased]`.

**Out of scope:**

- Lock or credit declarations for core names, overrides or replacements.
- Focus or state-source extractors for extension tools.
- A public lock helper (decided in change `1zimn-enh extension-public-helpers`).
- Changes to the lock itself; wave `1zimc` owns the hold registry and re-entry.

## Acceptance Criteria

- [x] AC-1: the stock declaration validates, and `declaration_problems` reports each refusal in Requirement 2: undeclared name, `read` tier, core name, override target, replacement target, alias, `alias_for_core`, runner tool, edit-gate tool, duplicate lifecycle entry, invalid field, a non-tuple lifecycle declaration, a non-mapping field declaration. `mcp_tool_roster` refuses the same declarations without starting the server.
- [x] AC-2: a declared lifecycle tool that no module registers, or an artifact field for one, refuses registration and leaves only runner tools served.
- [x] AC-3: through `call_tool`, a declared extension lifecycle tool returns the `lifecycle_mutation_locked` busy response naming the tool while another process holds the lifecycle lock, and runs normally when it is free; an undeclared write-tier extension tool runs while the lock is held; a plain alias and a parameter-mapped alias of the declared tool are refused the same way.
- [x] AC-4: under wave `1zimc`, a declared extension lifecycle tool's hold appears in `runtime_lock`'s process-hold registry while it runs and is gone after it returns; a handler that re-enters `lifecycle_lock.lifecycle_mutation_lock`, or calls another lifecycle-locked tool through the served surface, gets `LifecycleLockBusy` without the lock file being opened, the call returns `lifecycle_mutation_locked`, and a second process still finds the lifecycle lock held until the outer call returns.
- [x] AC-5: a declared tool whose `ok` response names a file it wrote in the declared field records a derived-artifact credit equal to the core contract (per-artifact floor, contained existing files only); an error response, a path outside the root, a missing file and an undeclared extension tool record none; a replay of an identical request and response credits once.
- [x] AC-6: `_LIFECYCLE_MUTATION_LOCK_TOOLS` and `_ARTIFACT_EXTRACTORS` are unchanged after registration with declarations, the reserved-collection census passes, and a new tool may still not take a reserved name.
- [x] AC-7: `wf_server_info.extensions.declaration` reports `lifecycle_tools` and `artifact_path_fields`, empty for the stock declaration.
- [x] AC-8: `SHIPPED_DECLARATION` lists both constants, a tree that ships a non-empty value fails `test_declaration_module_ships_empty`, and the suite passes under the default run and `--profile declared`.
- [x] AC-9: the spec, threat model and current-state text describe the declarations, the refusals and the trust-boundary sentence; the CHANGELOG entry exists.
- [x] AC-10: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the declarations, `declared()` coverage and validation in `mcp_tool_extensions.py`.
- [x] Add `_lock_pass_kwargs`, extend `_cost_pass_kwargs`, and the extra-names and extra-extractors parameters on the two wrappers.
- [x] Add the registration check and provenance keys.
- [x] Record the name-keyed set audit (Requirement 7) in the Progress Log.
- [x] Fixture extension modules and tests for AC-1 to AC-8, including a cross-process lock holder; add both constants to `SHIPPED_DECLARATION`.
- [x] Docs and CHANGELOG entry.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Declarations and validation | implementer | readiness, wave `1zimc` closed | stdlib module and roster path |
| Wrapper passes and provenance | implementer | declarations | `server_impl` |
| Docs | implementer | wrapper passes | spec, threat model, current-state |
| Review | code-reviewer, qa-reviewer, security-reviewer, architecture-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`, `.wavefoundry/framework/scripts/tests/record_layout_support.py`
- `docs/specs/mcp-tool-surface.md`, `docs/architecture/threat-model.md`, `docs/architecture/current-state.md`

## Affected Architecture Docs

`docs/architecture/threat-model.md` (extension modules row: the lifecycle-tool sentence) and `docs/architecture/current-state.md` (tool registry and wrapper chain paragraph: the lock and cost passes take declared extension names).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | A careless declaration must not reach the lock or credit |
| AC-2 | required | Fail closed on a declaration without a tool |
| AC-3 | required | The lock is the point of the change |
| AC-4 | required | Extension holds must follow the same registry and re-entry rules as core holds |
| AC-5 | required | Credit must follow the core contract and nothing more |
| AC-6 | required | Reserved collections must stay core-only |
| AC-7 | important | Provenance lets an operator see what the declaration grants |
| AC-8 | required | Ships-empty and the expected-profile guards must cover the new constants |
| AC-9 | required | Distributions need the contract documented |
| AC-10 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-02 | Reverification repair. The duplicate-credit test drops the symlink name when the account cannot create symlinks (Windows without Developer Mode) instead of writing an empty stand-in file, which resolved to its own path and added a second zero-token artifact. The spec credit contract and the CHANGELOG bullet now say each resolved file is credited once per response, core extractors included. | `test_declared_artifact_field_credits_by_the_core_contract` passes with `symlink_to` forced to raise, in a scratch copy |
| 2026-10-02 | Delivery review repair (red-team and QA, non-blocking). `_artifact_file_token_list` now credits each resolved file once, so one file named twice, through `./`, `..` or an in-root symlink earns one credit (pre-existing, exposed by declared fields). New test: dropping both declarations and reloading stops the lock and the credit. The start-of-install clears stay as a defensive reset: a reload re-executes `server_impl`, which recreates both sets, so no served path reaches the clears with stale entries and a mutation removing them is not observable. | `ExtensionLifecycleToolTests` (duplicate credit case, `test_reload_after_dropping_the_declarations_stops_lock_and_credit`); dedupe mutation killed in a scratch copy |
| 2026-10-01 | Implemented. `mcp_tool_extensions` gains `EXTENSION_LIFECYCLE_TOOLS` and `EXTENSION_ARTIFACT_PATH_FIELDS` (counted by `declared()`) and `_lock_and_credit_problems` in `declaration_problems`; `server_impl` records the installed declarations in `_EXTENSION_LIFECYCLE_TOOLS` and `_EXTENSION_ARTIFACT_PATH_FIELDS` (cleared at install start and on any registration failure), refuses a declaration no module registered, passes them through `_lock_pass_kwargs` (`extension_tools`) and `_cost_pass_kwargs` (`artifact_extractors`, used only for names absent from `_ARTIFACT_EXTRACTORS`), and reports `lifecycle_tools` and `artifact_path_fields` in provenance. Name-keyed set audit (Requirement 7): `_LIFECYCLE_MUTATION_LOCK_TOOLS` extended by the pass set, not edited; `_COST_EXEMPT_TOOLS` reserved, so a declared tool is never exempt; `_ARTIFACT_EXTRACTORS` extended by the pass map, not edited; `_COST_FOCUS_EXTRACTORS` and `_STATE_SOURCE_EXTRACTORS` unchanged (no extension entry); publication writer registry unchanged (write-tier extension tools already consult the checkpoint); `extractor_free` applies only to replacements; setup-notice skip set (runner tools and `index_health`) unchanged; roster tiers unchanged (declared tools are already `write`); `_CONTEXT_RETRIEVAL_TOOLS`, `_INDEXED_CONTEXT_TOOLS`, `_REFERENCE_ONLY_GRAPH_TOOLS`, `_LIFECYCLE_CONTEXT_STAGES`, `_TRACKING_CONTEXT_TOOLS`, `mcp_tool_roster.TOOL_TIERS` and `RUNNER_TOOLS`, `render_platform_surfaces._RENAMED_MCP_TOOLS`, the `wf_prepare_wave` `readiness_receipts` special case and `_EXTENSION_REPLACED_CORE` are keyed on core names and unchanged (a declared tool records only its cost-wrapper debit and credit). Lock-file check (wave `1zimc` Requirement 9): a declared tool's call passes only the setup, rewrite, guard, lock and cost wrappers; the lock re-entry consults the hold registry before opening the file, and the credit uses `stat` only, so no declared path opens the lifecycle lock file in-process (pinned: re-entry and a served locked call open no lock file, and crediting the lock file's own path keeps the hold). Tests failed first, then passed: AC-1 `LockAndCreditDeclarationTests`; AC-2, AC-6 `ExtensionRefusalTests` (`lifecycle_unregistered`, `artifact_unregistered`, `lifecycle_reserved_name`, `lifecycle_invalid_declaration`); AC-3 to AC-7 `ExtensionLifecycleToolTests` with a real second-process lock holder; AC-8 `LockAndCreditDeclarationTests.test_shipped_declaration_lists_both_constants_and_a_non_empty_value_fails` and the declaration census. Verification: full suite (`run_tests.py --no-cache`) in a scratch copy, 10,567 tests in 153 files OK (34 skipped); `--profile second` 10,564 OK and `--profile declared` 10,567 OK; 16 mutations of the new guards, all killed. | `mcp_tool_extensions.py`, `wf_server/server_impl.py`, `tests/test_extension_tool_modules.py`, `tests/record_layout_support.py`, `tests/declaration_support.py`, `docs/specs/mcp-tool-surface.md`, `docs/architecture/threat-model.md`, `docs/architecture/current-state.md`, `CHANGELOG.md` |
| 2026-10-01 | Planned from the downstream request. Verified: `_LIFECYCLE_MUTATION_LOCK_TOOLS` is a frozenset of eleven core names, read by name in `_wrap_lifecycle_mutation_lock`; `_reserved_tool_name_collections` lists it, `_COST_EXEMPT_TOOLS`, `_ARTIFACT_EXTRACTORS`, `_COST_FOCUS_EXTRACTORS`, `_STATE_SOURCE_EXTRACTORS`, the publication writer registry and the retired names, and a new tool taking any of them is refused; the cost wrapper applies to any name with a served prefix (core or extension) and looks up extractors by name; `_cost_pass_kwargs` and `_guard_pass_kwargs` already pass replacement-specific sets into the main pass only; write-tier extension tools already consult the publication checkpoint | `wf_server/server_impl.py` (`_wrap_lifecycle_mutation_lock`, `_wrap_first_party_tool_costs`, `MIDDLEWARE`, `_install_extension_tools`), `mcp_tool_extensions.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-01 | A declared lifecycle tool gets no supported way to compose core lifecycle operations in this change (readiness strongest challenge) | Letting `core_handler(name)` return any core lifecycle-locked tool's unwrapped handler to a module declaring `EXTENSION_LIFECYCLE_TOOLS` is the right shape, but it widens the override contract and needs its own review | Extend `core_handler` now; recorded as a follow-up change |
| 2026-10-01 | Two declarations, one for the lock and one for the artifact field | A tool that writes a change doc wants credit without the lock (core `wf_new_<kind>` tools are not locked), and a lifecycle tool may write nothing creditable | One `EXTENSION_LIFECYCLE_TOOLS` declaration that grants both |
| 2026-10-01 | Credit requires a declared field, not a response-shape convention | An undeclared convention would let any tool, including a read tool, claim credit for existing files by returning their paths | Credit any extension response carrying `data.written_paths` |
| 2026-10-01 | Both declarations accept only new `write`-tier extension tools | Core lock membership and extractors are fixed by core, and overrides and replacements already keep the core name's lock; a read tool neither mutates lifecycle state nor writes artifacts | Allow lock or credit on overrides and replacements |
| 2026-10-01 | Extend the wrappers through main-pass keywords, never by mutating reserved collections | The reserved-collection census pins those collections to served core or retired names, and `_CORE_BEHAVIOUR_MIDDLEWARE` must keep stock sets | Union the declared names into `_LIFECYCLE_MUTATION_LOCK_TOOLS` at install |
| 2026-10-01 | Build on wave `1zimc` | The extension tool goes through the same lock wrapper `1zimc` changes, so its hold and re-entry behaviour come from there | Implement first and adapt later |

## Risks

| Risk | Mitigation |
| --- | --- |
| A later core wrapper keyed on names misses declared extension tools | Requirement 7's audit is recorded, and the spec states that only the lock and artifact credit are extended |
| An extension lifecycle tool calls another locked tool through its wrapped callable | Wave `1zimc` refuses re-entry with `LifecycleLockBusy`, mapped to `lifecycle_mutation_locked` with no state change; AC-4 pins the same behaviour for extension tools, and the spec states that a declared tool calls core functions directly, never a served locked tool |
| A distribution writes lifecycle records from an undeclared tool | The spec and threat model state the obligation; extension modules are trusted code, so this is documentation, not a sandbox |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
