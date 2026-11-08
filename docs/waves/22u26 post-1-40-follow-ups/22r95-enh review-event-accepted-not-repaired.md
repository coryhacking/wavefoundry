# Record accepted-not-repaired findings through the review-event tool

Change ID: `22r95-enh review-event-accepted-not-repaired`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-07
Wave: 22u26 post-1-40-follow-ups

## Rationale

In wave 22qr6, the council chair needed to record a real but accepted residual gap (`22qr6-chair-22qoy-writer-exhaustiveness`) as accepted and not repaired. That classification is `dont_do_later` with a non-`none` `rejection_basis`, and the validator then requires a `promotion_trigger`. The chair could not find where to supply it, so the finding was recorded as `maybe_later` with its repair pending, which misstates its real state in the ledger and in every later readout.

A probe on 2026-11-07 showed the field already works: `wf_review_event` merges `evidence` into the event, so `evidence.promotion_trigger` reaches the validator, and the finding records as `dont_do_later`, `repair_execution_state: not_required`, with the trigger kept. Nothing documents this. The tool description, the field-placement summary and the guided `review_event_inputs` schema never mention `promotion_trigger`, and `rejection_basis` appears only as a judgment enum. The defect is discoverability, with no contract test to keep it fixed.

## Product Intent

Reviewers can find, from the tool description and the guided input schema alone, how to record an accepted residual risk with its trigger, so the ledger shows accepted findings as terminal and honestly classified instead of as pending repairs.

## Requirements

1. The `wf_review_event` description names `promotion_trigger`, says it goes in `evidence`, says it is required for `insufficient_evidence`, `unsupported_reachability` and `disproportionate_repair` and refused for any other basis, matching the validator.
2. The guided `review_event_inputs` schema lists `promotion_trigger` with the rejection bases that require it, derived from the validator's own set rather than a copy.
3. A contract test fails if `promotion_trigger` is absent from the description or the schema, or if the schema's basis list differs from the validator's set.
4. Seed 209's rule for `promotion_trigger` matches the validator: it currently says the field is optional for `categorical`, but the validator refuses it for any basis outside the three.
5. The ledger behaviour is unchanged.

## Scope

**In scope:** the `wf_review_event` description in `wf_server/server_impl.py` and its `docs/specs/mcp-tool-surface.md` entry, `review_evidence.review_action_input_schema`, a named constant for the bases that require a trigger, the one sentence in seed 209, the handler digest fixture, and contract tests.

**Out of scope:** a new top-level tool parameter, changing disposition semantics or the close gate, and rewriting the 22qr6 ledger.

## Acceptance Criteria

- [x] AC-1: A regression guard (this path already works, so it has no known-bad on the current code; AC-2 carries the falsifiable control): a test builds its judgment and evidence from the fields `review_event_inputs` lists, and records a `dont_do_later` finding with `rejection_basis: disproportionate_repair` and `evidence.promotion_trigger` through the served `wf_review_event`, and it reads back as terminal with that trigger; the same call without the trigger is refused with `selected rejection_basis requires promotion_trigger`.
- [x] AC-2: A contract test fails when `promotion_trigger` is removed from the description or the schema, or when the schema's list of bases that require it differs from the validator's set.
- [x] AC-4: `docs/specs/mcp-tool-surface.md` states where `promotion_trigger` goes and which bases require or refuse it, and seed 209 no longer calls it optional for `categorical`; a recorded `categorical` finding with a trigger is still refused with `promotion_trigger is not valid for rejection basis`.
- [x] AC-3: The change's own suites and every test it adds pass, the documents it edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Name the trigger-requiring bases in one `review_evidence` constant used by both validator sites.
- [x] Add `promotion_trigger` to `review_action_input_schema`.
- [x] Update the tool description and spec, and refresh `tests/fixtures/register-surface-handler-digests.json` (the description is the `@mcp.tool` docstring that `HandlerDigestTests` hashes).
- [x] Correct the seed 209 sentence under the `seed_edit_allowed` gate.
- [x] Add the contract and round-trip tests.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| tool       | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/`, `.wavefoundry/framework/scripts/review_evidence.py`, `.wavefoundry/framework/scripts/tests/`, `docs/specs/mcp-tool-surface.md`, `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`

## Affected Architecture Docs

N/A: a tool-surface addition with no boundary change. Update `docs/specs/mcp-tool-surface.md`.

## Platform Behavior

Platform-neutral.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | important | Honest ledger state for accepted risks. |
| AC-2 | important | Prevents recurrence of schema drift. |
| AC-4 | important | The spec is the reference reviewers read. |
| AC-3 | required  | Change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-06 | Filed from the wave 22qr6 readiness-chair observation at operator request. | 22qr6 ledger finding `22qr6-chair-22qoy-writer-exhaustiveness` |
| 2026-11-07 | Scheduled at operator request. Probe: the field already passes through `evidence`; requirements narrowed to discoverability and contract tests. | Scratch probe through `wf_review_event_response`: without trigger refused, with `evidence.promotion_trigger` recorded `dont_do_later` / `not_required` with the trigger |
| 2026-11-07 | Readiness feedback applied: Requirement 3 narrowed to `promotion_trigger`; AC-1 marked a regression guard; digest refresh made a task; seed 209 `categorical` wording added (docs-contract review found it disagrees with `review_evidence`'s synthesis check). | readiness review |
| 2026-11-07 | Implemented. `review_evidence.PROMOTION_TRIGGER_REJECTION_BASES` used at both validator sites; `review_action_input_schema` lists `promotion_trigger` under `evidence.finding.conditional_fields`; the `wf_review_event` docstring, `docs/specs/mcp-tool-surface.md` and seed 209 (under `seed_edit_allowed`, opened and closed) state the placement and the require/refuse rule; only the `wf_review_event` digest in `register-surface-handler-digests.json` changed. `tests/test_review_event_promotion_trigger.py` 7 OK; `test_mcp_tool_registry.py`, `test_server_tools_retrieval.py` and `test_review_evidence.py` 1312 OK. Mutation probes in a scratch copy: description, seed revert and schema-set drift each fail one test. | implementation |
| 2026-11-07 | Full suite `run_tests.py --no-cache`: 12612 tests in 235 files OK, 12 expected skips, no framework bytecode (second run). The first run failed two files from this wave's own edits, both fixed before the second: `test_lifecycle_golden` (the 22r95 `conditional_fields` schema entry; golden regenerated through `check_golden` with both overwrite flags, diff exactly the three expected fixture paths, and the addition declared with its exact value in `test_only_declared_observability_additions_since_extraction_golden`) and `test_server_package` (22u24's new filesystem test read producers by path; now `framework_files.source_path`). | full suite |
| 2026-11-07 | Delivery code-review advisory applied after the code, QA and docs-contract delivery approvals: the docstring sentence said a finding with a trigger-requiring basis records as `dont_do_later`; that holds only when the finding needs no action (an action-required finding derives `do_now`, which refuses a non-`none` basis). Reworded to say so; only the `wf_review_event` digest refreshed. The full suite is rerun on this tree before the delivery council. | delivery review |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-07 | Document the existing `evidence` placement instead of adding a parameter | It already works; a parameter would duplicate a path and change the handler signature | New top-level `promotion_trigger` parameter |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A handler change requires the digest pin refresh | Refresh the pin as part of the change. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
