# Operator sign-off integrity checks read as not applicable

Change ID: `21s53-enh operator-signoff-checks-not-applicable`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-27
Wave: 21s6f operator-signoff-checks-not-applicable

## Rationale

Wave `21sld` (change `21qbb`) stopped operator sign-offs from claiming checks nobody ran. When the caller omits `integrity_checks`, the stored record now carries the five integrity booleans as `false`, with `known_bad_detection_method` reading "not applicable: operator approval attests the reviewed scope and runs no check". The first live record is `ev-approval-operator-signoff` in `21sld`.

`false` is still the wrong word. It reads as "the check was done and failed", while the truth is "no check applies". The operator asked for a third value, not applicable, on 2026-10-27. An operator who did check can still say so with `true` or `false`.

## Product Intent

An operator's sign-off records "not applicable" for checks the operator never ran, rather than a value that reads as a failed check. An operator who did check can still record `true` or `false` for each one. Agents never ask the operator for check values: they record not applicable unless the operator volunteers something. Specialist and council approvals and every historical record are unchanged. AC-1 and AC-3 together test this intent.

## Requirements

1. When an `operator-signoff` approval event omits `integrity_checks`, the stored record carries `null` for each of the five integrity booleans. `known_bad_detection_method` keeps the existing not-applicable text from `OPERATOR_APPROVAL_INTEGRITY_DEFAULT` in `review_evidence.py`.
2. When an `operator-signoff` approval event supplies `integrity_checks`, each boolean may be `true`, `false` or `null`. Values are stored verbatim, and the exact object shape is still required: all five booleans plus a non-empty method.
3. `null` is accepted only on an operator sign-off, meaning a request with signoff key `operator-signoff` and actor `operator` at write time, and, at read time, a record matching `is_operator_approval_record` that also has `claim_kind == "approval"`. Everywhere else the five fields stay strictly boolean, and executed specialist and council records keep the all-`true` rule. The write-time builder (`_validated_integrity_checks`) and the read-time record validator (`_validate_evidence_shape`, field-type loop and executed-integrity rule) apply the same rule.
4. Historical records keep their original values with no rewrite: `21sld`'s `false` operator record and about 670 older operator approvals with `true`. They remain valid, current and closable.
5. The retry fingerprint (`normalize_review_event_request`) uses the same `null` default as the stored record, so an omitted field and the same `null` values spelled out fingerprint alike.
6. The guidance stops agents from asking the operator for check values. They record an operator sign-off without `integrity_checks`, and pass values only when the operator states them. The text says `null` means not applicable, replacing the "may carry `false`" wording. The sites are every description of the five booleans:
   - seed 209: the integrity field-table rows typed "Boolean", the integrity paragraph, and the approval-evidence bullet;
   - the `wf_review_event` docstring: the integrity sentence in the body and the `integrity_checks` Args entry;
   - `docs/specs/mcp-tool-surface.md`: the integrity bullet.
7. The response-level `caller_input_schema` (`review_action_input_schema`) describes the integrity booleans so that a caller can learn `null` is allowed for operator sign-offs. The two lifecycle golden fixtures that pin this schema are re-pinned with a comment.

## Scope

**Problem statement:** an operator sign-off stores `false` for checks that do not apply.

**In scope:**

- `review_evidence.py`: the operator default, the builder's integrity validation, the record validator, the retry-fingerprint default and the caller input schema.
- The `wf_review_event` docstring in `wf_server/server_impl.py`, plus refreshing that handler's digest pin.
- Seed 209 and `docs/specs/mcp-tool-surface.md` wording.
- Tests in `test_review_evidence.py`, plus any frozen ledger pins that move.
- The golden fixtures `tests/fixtures/lifecycle-gate-golden.json` and `tests/fixtures/lifecycle-gate-pre-configured-golden.json`, which pin the input schema (compared by `test_lifecycle_golden.py`).

**Out of scope:**

- Rewriting any existing ledger record.
- Dashboard or `wave.md` display changes. Neither shows the five fields. Census on 2026-10-27: only `review_evidence.py` reads them; `server_impl.py`, seed 209 and the spec only describe them.
- `null` on findings, reverifications or non-operator approvals.
- Changing close-gate authority. The gate never reads operator check values.

## Acceptance Criteria

- [x] AC-1: An operator sign-off recorded through `wf_review_event` without `integrity_checks` stores `null` for all five booleans, with the not-applicable method. The ledger validates, and the wave's operator sign-off counts as current for close. A test asserts fixed literal expectations: `None` for each field. It fails against the current `false` default.
- [x] AC-2: An operator sign-off that supplies a mix of `true`, `false` and `null` is stored verbatim and validates. A non-boolean, non-null value (for example a string) is refused. So is a missing field.
- [x] AC-3: `null` is refused on every non-operator record at write time: a specialist approval, a council approval, a finding (including one recorded by actor `operator`), and an `operator-signoff` request from a non-operator actor. At read time, a record that has `null` but fails either half of the operator predicate (actor or claim) is refused. Mutants that drop either half of the predicate, or allow `null` everywhere, fail a test.
- [x] AC-4 (regression guard; it guards an implementation that breaks old records rather than failing against a no-op): Historical operator records validate unchanged: `21sld`'s `false` record and the older all-`true` ones. A full docs lint over every committed ledger passes in a fresh process.
- [x] AC-5: The retry fingerprint of an operator sign-off with omitted checks equals that of the same request with the five `null` values and the not-applicable method spelled out.
- [x] AC-6: Seed 209, the `wf_review_event` docstring and `docs/specs/mcp-tool-surface.md` describe `null` as not applicable, tell agents to omit `integrity_checks` for an operator sign-off unless the operator states values, and no longer say an operator sign-off "may carry false" as its default. A text test pins the seed (including the field-table rows) and both docstring sites.

## Tasks

- [x] Open `framework_edit_allowed`, and `seed_edit_allowed` for seed 209. Close both after the edits.
- [x] Change `OPERATOR_APPROVAL_INTEGRITY_DEFAULT` booleans to `None`.
- [x] Give `_validated_integrity_checks` an operator allowance for `None`, used only for operator sign-offs.
- [x] In `_validate_evidence_shape`, allow `None` on the five fields only when `is_operator_approval_record`. The executed-integrity rule exemption stays as it is.
- [x] Update `caller_input_schema` so the integrity booleans say `null` is allowed for operator sign-offs.
- [x] Update the docstring, seed 209 and the spec, refresh the handler digest pin, and re-pin any frozen ledger fingerprint that moves, with a comment.
- [x] Add tests for AC-1 to AC-6, run mutants in a scratch copy, then run the canonical suite last.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| null-acceptance | implementer | — | `review_evidence.py` and tests |
| contract-text | implementer | null-acceptance | seed 209, docstring, spec, digest pin |
| verification | qa-reviewer | contract-text | mutants and canonical suite |

## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/tests/fixtures/lifecycle-gate-golden.json`, `.wavefoundry/framework/scripts/tests/fixtures/lifecycle-gate-pre-configured-golden.json`, `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`, `.wavefoundry/framework/scripts/tests/test_review_evidence.py`, `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

N/A. The change is confined to the review-evidence record shape for one approval kind. Module boundaries, flows and the verification architecture are unchanged.

## Platform Behavior

Pure JSON record shape and Python validation, with no file-system, process or path behavior. Behavior is identical on Windows, macOS, Linux and WSL2.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | the operator's requested outcome |
| AC-2 | required | the operator asked to keep true/false available |
| AC-3 | required | `null` must not weaken specialist or council attestation |
| AC-4 | required | the operator asked to keep all original values |
| AC-5 | important | retry contract consistency, matching `21sld` |
| AC-6 | required | agents must not ask the operator for check values |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-27 | Implemented under `framework_edit_allowed`, with seed 209 under `seed_edit_allowed`; both gates are closed. `review_evidence.py`: `OPERATOR_APPROVAL_INTEGRITY_DEFAULT` booleans are `None`. `_validated_integrity_checks` gains `allow_not_applicable`, passed only for an operator sign-off request. Elsewhere a `null` value gets the specific refusal "must be boolean: null (not applicable) is accepted only on an operator-signoff approval". `_validate_evidence_shape` splits the five integrity fields out of the boolean loop and allows `null` only under `_accepts_not_applicable_integrity` (`claim_kind == "approval"` and `is_operator_approval_record`). Its executed-integrity message now says "false or null (not applicable)". `review_action_input_schema` marks each integrity boolean with `null_allowed_for: ["operator-signoff"]` and `null_meaning: "not applicable"`, and both lifecycle golden fixtures were re-pinned for exactly those 15 entries. `normalize_review_event_request` takes the `null` default from the same constant. Contract text: seed 209 (five field-table rows, the integrity paragraph with "Do not ask the operator for check values", the approval-evidence bullet), both `wf_review_event` docstring sites, and the spec integrity bullet. The handler-digest pin was refreshed for `wf_review_event` only. The frozen ledger pin did not move. Its fixture supplies all-true checks, as the QA readiness reviewer predicted. Tests in `OperatorApprovalHonestAttestationTests`: AC-1 null default, AC-2 stated true/false/null plus string and missing-field refusals, AC-3 write time (specialist, council, operator-actor finding, wrong-actor `operator-signoff`; null-specific message asserted) and read time (actor, claim, `claim_kind` alone), AC-4 `false` and `true` operator records, AC-5 fingerprint with `None`, AC-6 seed and docstring text. Eight scratch-copy mutants were all killed: request predicate drops actor, record predicate drops `claim_kind`, record allows all, write allows all, default back to `False`, findings allow `null`, schema back to plain boolean, seed sentence reverted. The unmutated scratch baseline passes. AC-4: fresh-process `wf docs-lint` over every committed ledger is ok. Canonical suite: 12,270 tests, 12 existing skips, OK, fresh receipt. | scratchpad m21s6f/run.py; canonical-21s6f.log; wf docs-lint |
| 2026-10-27 | Format repair after readiness: docs lint counted AC-6's three nested bullets as extra Acceptance Criteria (9 bullets vs 6 priority rows). AC-6 is now one sentence with the same three conditions and the same text test; no meaning changed. The receipt rotated, so the four readiness approvals are re-recorded against it. | wf_prepare_wave lint errors |
| 2026-10-27 | Readiness repair after the red-team primer. No blocking findings. Added: the two lifecycle golden fixtures that pin the input schema (scope, R7, Serialization Points); every seed 209 and docstring site (R6, AC-6); the operator-actor finding and non-operator `operator-signoff` request cases (AC-3); `claim_kind == "approval"` in the read-time allowance (R3); a Risks row for retry of a `21sld`-default record; AC-4 labelled a regression guard. Declined: defaulting the method on supplied checks, and refusing supplied `null` (Decision Log). Serialization verified by the primer: `canonical_review_event_bytes` and `parse_review_event_bytes` round-trip `null`. No prompt or skill tells agents to collect operator check values. | red-team primer |
| 2026-10-27 | Planned. Census of the five integrity field names outside tests: readers only in `review_evidence.py` (builder approval branch, `_validated_integrity_checks`, `_validate_evidence_shape` field-type loop and executed-integrity rule, `caller_input_schema`); descriptions in `server_impl.py` (`wf_review_event` docstring), seed 209 and `docs/specs/mcp-tool-surface.md`. The dashboard (`dashboard_lib.py` approvals carry key/state/why/next_action only) and the `wave.md` status table do not show the fields. | grep over `.wavefoundry/framework`, `.claude`, `docs/specs`, `docs/prompts`, `docs/agents`, `docs/architecture` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-27 | Store `null` per boolean as "not applicable" on operator sign-offs, and allow `true`/`false`/`null` when supplied. | Operator direction: `false` reads as a failed check; an operator who did check may still say so. `null` keeps the record shape, so readers handle no missing field. Efficacy: replaying `21sld`'s sign-off through the change stores `null`, which is exactly the requested outcome; the mechanism controls the stored value directly. | (a) Omit the five fields from operator records: a schema change for every reader, and 670 historical records keep the fields, so readers handle both shapes forever. (b) A record-level `execution_status: not_applicable`: touches three gate sites (rejected in `21sld` for the same reason). (c) Refuse supplied checks on operator sign-offs: the operator wants true/false available. |
| 2026-10-27 | Agents never ask the operator for check values; omit `integrity_checks` unless the operator states them. | Operator direction ("we don't have to ask the operator anything"). | Prompt the operator per check: adds friction for a value the close gate never reads. |
| 2026-10-27 | Supplied operator checks keep the exact shape, including a non-empty `known_bad_detection_method`; no method default is added when values are supplied. | Simplest: an operator who volunteers values is described in the method by the agent recording them. Red-team nit 7, declined. | Default the method when omitted: adds a second defaulting path. |
| 2026-10-27 | Caller-supplied `null` is allowed, not only the omitted default. | Operator direction: an operator may state true, false or null per check. | Red-team's strongest alternative, refusing supplied `null` to keep `_validated_integrity_checks` boolean-only: smaller leak surface, but contradicts the operator's direction. The leak surface is covered by AC-3 at both write and read time. |
| 2026-10-27 | No rewrite of historical records. | Operator direction ("we can keep all of the original values"); closed ledgers are sealed. | Migrate `21sld`'s `false` record to `null`: rewrites a sealed ledger. |

## Risks

| Risk | Mitigation |
| --- | --- |
| `null` leaks to non-operator records | Predicate is enforced at both write time and read time; AC-3 mutants cover each half |
| A reader does `record[field] is True` or a truthiness test that treats `null` differently from `false` | The census found only the executed-integrity rule, which exempts operator records; AC-4 runs every committed ledger |
| A retry of an operator sign-off recorded under the `21sld` `false` default gets `review_event_identity_conflict` instead of replaying | Retries happen only on an open wave. The only `false`-default record is `21sld`'s, and that wave is closed. Accepted, with no replay spelling added. |
| Frozen ledger pins move | Re-pin with a comment, after a probe confirms only operator default fields changed |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
