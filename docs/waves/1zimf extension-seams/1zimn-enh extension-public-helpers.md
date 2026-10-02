# Public Helpers for Extension Handlers

Change ID: `1zimn-enh extension-public-helpers`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zimf extension-seams

## Rationale

The extension contract in `docs/specs/mcp-tool-surface.md` (**Overrides**) tells a distribution's handlers to pass `kwargs` to `server_impl._ensure_no_extra_args(tool_name, kwargs)` and return its envelope, and the loader's refusal messages (`_override_compatibility_problem` and the replacement check in `_install_extension_tools`) say the same. The same section says underscore-prefixed helpers "are reachable but are not a stable public API". So every conforming extension depends on a name the framework does not promise to keep. Extensions also build their own envelopes and diagnostics; the only builders are the private `server_impl._response` and `lifecycle_gate_support._diagnostic` (re-exported into `server_impl` under the same private name). A downstream distribution serving team-workflow tools asked for public names so its modules stay off private ones.

The distribution also asked for a public busy response for extension tools that take the lifecycle lock. That request does not hold once change `1zimo-enh extension-lifecycle-tools-and-artifact-credit` lands: an extension lifecycle tool is wrapped by the middleware lock, which already returns the busy response. A handler that took the lock itself would bypass the strict root resolution in `_wrap_lifecycle_mutation_lock` and the hold registry wave `1zimc` adds, so this change exposes no lock or busy helper.

## Requirements

1. **Three public helpers.** `server_impl` (reached as `import server_impl` through the retained flat alias, or `import wf_server.server_impl`) defines, in one marked block:
   - `ensure_no_extra_args(tool_name: str, kwargs: dict) -> dict | None`: the same result as `_ensure_no_extra_args`, including the empty `kwargs={}` compatibility payload and the `unknown_arguments` diagnostic;
   - `make_response(status, data=None, *, diagnostics=None, next_tools=None, usage="") -> dict`: the standard envelope, identical to `_response` (`isError: True` on `"error"`);
   - `make_diagnostic(code, message, *, recovery_tools=None, recovery_usage="", advisory=False) -> dict`: identical to `_diagnostic`.
2. **Thin, late-bound wrappers.** Each public helper is a `def` that calls its private counterpart by module-global lookup at call time, so `patch.object(server_impl, "_response", ...)` in tests and an in-place `wf_reload_mcp` both reach the current private function. The private names stay unchanged; no existing caller is migrated.
3. **Named contract.** A module-level tuple `EXTENSION_PUBLIC_HELPERS = ("ensure_no_extra_args", "make_response", "make_diagnostic")` lists the stable surface. A test pins that each name is callable, that its signature equals the documented one, and that its result equals the private helper's for the same arguments. Removing or renaming one is a breaking change recorded in `## [Unreleased]`.
4. **No name collisions.** None of the three names is a module-level name in `server_impl` today, nor a tool name. The tuple is not a tool-name collection, so the reserved-collection census in `test_extension_tool_modules` does not classify it; the change confirms the census still passes.
5. **Docs and messages name the public helper.** The **Registration** and **Overrides** paragraphs of `docs/specs/mcp-tool-surface.md` name `server_impl.ensure_no_extra_args` and list the three helpers as the supported surface; the sentence saying underscore helpers are not a stable API stays. The two loader refusal messages that say "pass them to _ensure_no_extra_args" say `server_impl.ensure_no_extra_args`; tests that match those messages are updated.
6. **No busy or lock helper.** The spec states that an extension tool needing the lifecycle lock declares it (change `1zimo-enh extension-lifecycle-tools-and-artifact-credit`) rather than taking the lock in its handler.
7. **Platforms.** Windows, macOS, Linux and WSL2 behave the same: pure Python functions with no file, process or path behaviour.
8. **Transition.** Additive. Extensions calling `_ensure_no_extra_args`, `_response` or `_diagnostic` keep working.

## Scope

**Problem statement:** conforming extension handlers must call private server helpers, and there is no public way to build an envelope or a diagnostic.

**In scope:**

- The three public helpers and `EXTENSION_PUBLIC_HELPERS` in `wf_server/server_impl.py`.
- The two loader refusal messages and the tests that match them.
- The extension test fixture modules switched to the public names, so the public path is the one exercised.
- The **Registration** and **Overrides** paragraphs of the tool-surface spec; one `### Added` entry in `## [Unreleased]`.

**Out of scope:**

- A public lifecycle-lock, busy-response or publication-guard helper (Requirement 6).
- A separate extension API module; the helpers stay on `server_impl`, the module extensions already import.
- Changing any private helper or any core caller.

## Acceptance Criteria

- [x] AC-1: `server_impl.ensure_no_extra_args`, `server_impl.make_response` and `server_impl.make_diagnostic` exist with the signatures in Requirement 1, and for the same arguments each returns a result equal to its private counterpart, including `ensure_no_extra_args("t", {})` and `ensure_no_extra_args("t", {"kwargs": {}})` returning `None` and an unknown argument returning the `unknown_arguments` envelope with `isError: True`.
- [x] AC-2: patching the private helper on `server_impl` changes what the public helper returns (late binding), and the public helpers still resolve after `wf_reload_mcp` in an in-process reload test.
- [x] AC-3: `EXTENSION_PUBLIC_HELPERS` names exactly the three helpers; a test fails when one is removed, renamed or changes signature.
- [x] AC-4: an extension fixture module using only the public helpers registers, serves a tool, and rejects an undeclared argument with the `unknown_arguments` envelope through `call_tool` (not `.fn`).
- [x] AC-5: the two loader refusal messages name `server_impl.ensure_no_extra_args`; the reserved-collection census and the existing extension suites pass unchanged otherwise.
- [x] AC-6: the spec names the public helpers as the supported surface and states that lock-needing extension tools declare the lock instead of taking it; the CHANGELOG entry exists.
- [x] AC-7: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the three public helpers and `EXTENSION_PUBLIC_HELPERS` in a marked block in `server_impl`.
- [x] Update the two refusal messages and the tests matching them.
- [x] Switch the extension test fixture modules to the public helpers.
- [x] Tests for AC-1 to AC-4.
- [x] Spec paragraphs and CHANGELOG entry.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Public helpers | implementer | readiness | `server_impl` block, messages, fixtures |
| Docs | implementer | public helpers | spec and CHANGELOG |
| Review | code-reviewer, qa-reviewer, security-reviewer, architecture-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_extension_tool_modules.py`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

N/A: the helpers are names on the existing composition root, with no boundary, flow or verification change. The contract text lives in `docs/specs/mcp-tool-surface.md`.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The public helpers must behave exactly like the private ones |
| AC-2 | required | Late binding keeps tests and reload correct |
| AC-3 | required | The stable surface must be pinned |
| AC-4 | required | The public path must work end to end |
| AC-5 | required | Messages must point at the public name |
| AC-6 | required | Distributions need the contract documented |
| AC-7 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Implemented. `server_impl` gains the marked public-helper block: `EXTENSION_PUBLIC_HELPERS` and `ensure_no_extra_args`, `make_response`, `make_diagnostic`, each a `def` calling its private counterpart by module-global lookup at call time (change `1zimp` adds `change_doc_response` and the pin now names four). The two loader refusals name `server_impl.ensure_no_extra_args`; every extension fixture module in the driver uses the public names. Spec **Registration** names the supported surface and states that a lock-needing tool declares `EXTENSION_LIFECYCLE_TOOLS` instead of taking the lock; **Overrides** names the public helper; CHANGELOG `### Added`. Tests failed first (missing attributes, old message), then passed. AC-1, AC-3: `PublicHelperContractTests`; AC-2: `PublicHelperLateBindingTests` and the reload half of `PublicHelperServingTests`; AC-4: `PublicHelperServingTests`; AC-5: `ExtensionRefusalTests.test_refusals_name_the_public_helper` and the census suites. Verification: full suite (`run_tests.py --no-cache`) in a scratch copy, 10,567 tests in 153 files OK (34 skipped); `--profile second` 10,564 OK and `--profile declared` 10,567 OK; 16 mutations of the new guards, all killed. | `wf_server/server_impl.py`, `tests/test_extension_public_helpers.py`, `tests/test_extension_tool_modules.py`, `docs/specs/mcp-tool-surface.md`, `CHANGELOG.md` |
| 2026-10-01 | Planned from the downstream request. Verified: the spec's **Overrides** paragraph and two loader messages direct handlers to `server_impl._ensure_no_extra_args`; `_response` is defined in `server_impl`; `_diagnostic` comes from `lifecycle_gate_support` and is imported privately into `server_impl`; no module-level `ensure_no_extra_args`, `make_response` or `make_diagnostic` exists; the busy response `_lifecycle_mutation_busy_response` is produced only by the middleware lock wrapper | `wf_server/server_impl.py` (`_response`, `_ensure_no_extra_args`, `_wrap_lifecycle_mutation_lock`), `lifecycle_gate_support.py`, `docs/specs/mcp-tool-surface.md` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-01 | Public helpers live on `server_impl` as late-bound wrappers | Extensions already import `server_impl`; late binding survives reload and test patching | A new `extension_api` module, which would need a reserved module name and would bind stale functions after an in-place reload |
| 2026-10-01 | Names `make_response` and `make_diagnostic`, not `response` and `diagnostic` | Many `server_impl` functions use local variables named `response` and `diagnostic`; distinct names avoid a reader confusing them | Bare `response` and `diagnostic` |
| 2026-10-01 | No public busy-response or lock helper | Change `1zimo-enh extension-lifecycle-tools-and-artifact-credit` puts declared extension lifecycle tools under the middleware lock, which owns the busy response and the wave `1zimc` hold registry | Expose `_lifecycle_mutation_busy_response` and the lock context manager publicly |

## Risks

| Risk | Mitigation |
| --- | --- |
| A future refactor renames a private helper and silently breaks a public wrapper | The equality and signature tests in AC-1 and AC-3 fail first |
| Distributions keep calling the private names | Additive change; the spec and messages now name the public helper |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
