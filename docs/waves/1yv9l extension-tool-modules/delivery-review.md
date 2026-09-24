# Extension Tool Modules Delivery Review

Owner: Engineering
Status: active
Last verified: 2026-09-23

## Initial delivery round

Frozen tree: `evidence/delivery-fingerprint.txt` (git blob hashes over 13 reviewed paths), unchanged before and after every lane. Independent read-only contexts: red-team delivery primer; code and QA; architecture and security; docs-contract and rotating seat. Probes ran only in scratch copies of the scripts tree through `server.build_server` and `await mcp.call_tool(...)`.

Verdicts: architecture approve; code, QA, security and docs-contract block.

| Finding | Lanes | Claim | Reproduction |
| --- | --- | --- | --- |
| DEL-ASYNC-HANDLERS | red-team, code, security, docs-contract | `async def` extension handlers escape the synchronous wrappers: an async override of `wf_create_wave` runs without the lifecycle lock held, and an async write-tier tool raises `ToolError` during an upgrade checkpoint instead of returning `upgrade_in_progress`. | Async override probe reports the lock not held; the sync twin reports it held. Async write tool raises "object dict can't be used in 'await' expression"; the sync twin returns `upgrade_in_progress`. |
| DEL-UNRECORDED-REGISTRATION | red-team, code, security, docs-contract | `_install_extension_tools` validates only names recorded through `FastMCP.add_tool`, but installs every entry in the staging tool table, so direct `_tool_manager.add_tool` or table writes install undeclared overrides and untiered tools, and provenance under-reports them. | A module adding `wf_help` and `acme_hidden` through `_tool_manager.add_tool` starts cleanly, `call_tool("wf_help")` serves the replacement, and `wf_server_info` lists no tools or overrides for it. |
| DEL-CALL-PATH-TESTS | QA | Tests call `.fn` directly, never `mcp.call_tool`, so the lock claim is proven only by markers and argument validation is bypassed; this is why DEL-ASYNC-HANDLERS passed the suite. | Driver `call()` invokes `table(mcp)[name].fn(**kwargs)`. |

Non-blocking notes carried into the repair: resources and prompts registered on staging are silently dropped (refuse them); the spec Failure list omits several `declaration_problems` refusals; the roster-cannot-load parenthetical is ambiguous; repository-relative provenance paths are untested (QA mutant M5 survived); startup refusal is shown through `register_mcp_surface`, not `build_server`; a later framework script whose name matches an extension module is refused, which the spec should say.

QA mutation table (twelve mutants, eleven killed, M5 relative-path survived) and the implementer's six killed mutants are recorded in the lane reports; the implementer's script is `evidence/mutants.py`.

## Repair cycle 1

Implementer context `ext_tools_repair1`. Frozen repaired tree: `evidence/repair1-fingerprint.txt`.

- **DEL-ASYNC-HANDLERS:** `_install_extension_tools` refuses any staged tool whose `is_async` is true or whose handler is a coroutine function ("extension handlers must be synchronous"). Spec Registration and Failure paragraphs say handlers must be synchronous.
- **DEL-UNRECORDED-REGISTRATION:** per module, the staged tool table is diffed against the table before `register` ran. Names added without a recorded `FastMCP.add_tool` attempt, and replacement or removal of another module's staged tools, are refused. Resources and prompts registered on staging are refused too (non-blocking note folded in).
- **DEL-CALL-PATH-TESTS:** the driver now calls the lifecycle override, write-during-upgrade and unknown-argument cases through `await mcp.call_tool(...)`, with a probe around `_lifecycle_mutation_lock` showing the lock held inside the override body and released after. Six new refusal fixtures (async handler, `_tool_manager.add_tool`, direct table write, staging tamper, resource, prompt), a `build_server` startup-refusal mode, and repository-relative provenance paths (QA mutant M5) are asserted.
- **Editorial:** spec Failure list now enumerates every declaration refusal, names a later framework script with the same module name, and says no tool at all is served when the roster cannot load; testing-architecture counts updated.

Evidence: `test_extension_tool_modules.py` 18 tests OK; `evidence/mutants.py` nine mutants (six original plus async refusal, unrecorded check, relative path) each fail the file.

## Reverification and follow-up

All three findings were reverified closed by their originating lanes (code, security, docs-contract, QA) on `evidence/repair1-fingerprint.txt`. Non-blocking follow-ups from those passes, applied before final approvals:

- Withdrawn registrations: a module that removes a tool it registered is refused ("removes tools it registered"); this also turns the bare `KeyError` for a withdrawn override into a named refusal and stops provenance over-reporting.
- Served-table writes (code lane NB-1): the served tool table is snapshotted around each `register` call, and any change is refused ("changes the served tool table directly"), closing writes through `server_impl._MCP_INSTANCE`.
- DOCS-REP-1: the spec no longer claims a later same-named framework script is always caught; it states the public-name import condition and that such a script replaces the extension file on upgrade. The trust-boundary sentence now covers in-place rebinding of existing tool objects and post-registration mutation.

Evidence: two new refusal fixtures (27 total), 18 tests OK; `evidence/mutants.py` eleven mutants each fail the file. Final frozen tree: `evidence/final-fingerprint.txt`.

## Repair cycle 2 (independent delivery review)

Independent review (`independent-delivery-review.md`, context `1yv9l-second-review-20260924`) recorded DEL-OVERRIDE-VALUE-COMPATIBILITY: the structural check compared parameter names and required-ness but not value schemas, so an override changing `slug: str` to `slug: int` registered and a normal `wf_create_wave(slug="probe")` call then failed validation.

Implementer context `ext_tools_repair2`: `_override_compatibility_problem` now requires every replaced parameter's normalized value schema to match (local `$defs` references resolved; titles, descriptions, defaults and examples ignored) and refuses with "changes the schema of parameters [...]". Fixtures: `type_changed_override` refused; `default_changed_override` still registers (a changed default is call-compatible). Spec compatibility sentence and testing-architecture counts updated. Evidence: 18 extension tests and 13 golden tests OK; `evidence/mutants.py` twelve mutants each fail the file, including `no_schema_preservation`. Frozen tree: `evidence/repair2-fingerprint.txt`.

Operator-approved addition to repair cycle 2 (after the code/QA reverification confirmed that added optional parameters register and serve): positive fixture `extended_override` (an override adding optional `team` and a custom `title` on `slug`) registers and serves through `call_tool` both with and without the added parameter; spec now states that added optional parameters are allowed, added required parameters and type widening are refused, and `examples` is ignored. Mutant `title_significant` (QA survivor) is now killed. Evidence: 20 extension tests OK; `evidence/mutants.py` thirteen mutants each fail the file.
