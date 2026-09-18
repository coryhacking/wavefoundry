# Tool Surface Snapshot Readiness Review

Owner: Engineering
Status: active
Last verified: 2026-09-17

Phase: readiness. Reviewer context: `snapshot-readiness-20260917-independent`. Scope: wave `1y0do`, change `1xzsl`; no implementation approval or delivery claims.

## Protocol and findings

Standard primer depth; configured seats: red-team and docs-contract-reviewer. The independent council reviewer ran the red-team primer first, applying adversarial, constructive and simplicity stances. A separate docs-contract reviewer received the primer and independently inspected the plan and current registration code. Initial agreement was unanimous, maximum severity medium. No challenge round was needed.

The strongest challenge was the mismatch between whole-public-surface coverage and implementation-only registration: runner survivor schemas were omitted. The strongest alternative was full runner registration with a stub handler and complete schema serialization, retaining the test-only boundary. This is better because it covers the actual published survivor without adding production machinery or a second schema source.

The primer asked which tools and schema fields the fixture actually protects, and whether wrapper mutation and regeneration tests exercise the real boundary safely. Four bounded clarifications followed: full runner coverage; all schema constraints/defaults with only schema-node prose descriptions excluded; actual registered wrapper-chain mutation across all five wrong orders; temporary fixture and scoped environment isolation. The revised Requirements 1–6 and AC-2–4 address these questions. Explicit UTF-8/LF output addresses platform stability; the architecture documentation task is now explicit.

## Executed readiness evidence

Current source was retrieved MCP-first through `code_ask`, `code_outline` and targeted `code_read`, then checked against existing test helpers. `server.py:544–696` registers the implementation surface, registers `wf_reload_mcp`, and normalizes the completed registry. `server_impl.py:35480–35486` applies cost, lifecycle lock and upgrade guard wrappers in that order. The existing two-wrapper guard test does not by itself prove the three-wrapper registration order.

Two bounded `python3 -B` probes used `server_tools_support.load_server()` followed by `load_thin_runner()` and temporary directories:

- Full runner feasibility: patch only `runner.server_impl.build_handler` to return `SimpleNamespace(root=temporary_root)`; invoke real `runner.build_server(root)`. Observed 90 actual tools, an exact empty-object `wf_reload_mcp` schema with `additionalProperties: false`, and `docs_search.kind` enum/default constraints. The temporary root remained empty. Expected complete registration without real handler startup was observed.
- Known-bad census control: compare real `register_mcp_surface(FastMCP(...), stub_get_handler)` against that full runner registry. An explicit assertion detected exactly `{'wf_reload_mcp'}` missing from the implementation-only registry. Thus the original incomplete-census claim was refuted through actual registration, not inferred from names alone.

Both probes completed without skipped checks or repository writes. The initial feasibility invocation omitted the documented prerequisite `load_server()` and failed before registration; the corrected invocation above completed successfully. No server reload, stdio serving, external requests, production mutation, or full framework suite was run.

## Verdict and limits

Readiness approved after focused reinspection of the amended plan. The improvements preserve the original whole-public-surface goal and the no-production-change scope. Independent docs-contract findings have been addressed; there are no remaining blocking plan findings.

This approval attests to the review and readiness-safe evidence, not unimplemented product behavior. The golden, comparison, regeneration and five-permutation tests still must be implemented and executed during delivery; native Windows behavior was not executed here. Required code-reviewer and qa-reviewer delivery lanes remain outstanding. The coordinator owns typed approval and readiness state.

## Authorized cross-wave clarification follow-up

The operator subsequently authorized correcting fixed-count and existing-stub claims here, registry scope in `1y0h1`, and incompatible module composition in `1y0h2`. A standard red-team primer and separate docs-contract seat reviewed the amended change and wave records. The snapshot now derives the complete roster without a fixed-count requirement and explicitly introduces a new handler stub adapted from runner tests that normally build the real handler. The earlier observation of 90 tools is probe evidence only, not an invariant.

Both reviewers approved the final text after the remaining task and wave-summary mirrors were repaired. No bounded findings remain. The original full-runner and deliberately incomplete-census probes still support this plan-only approval; no implementation source changed. Follow-up context: `snapshot-crosswave-readiness-20260917-independent`.
