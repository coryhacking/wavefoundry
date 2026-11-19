# Allow an honest not-applicable control at specialist readiness

Change ID: `23mzz-bug readiness-known-bad-not-applicable`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-16
Wave: 23n00 honest-readiness-integrity

## Rationale

A downstream toolchain-only change reportedly passed specialist review but could not record security and performance readiness approvals: neither lane had an affected surface against which to exercise a meaningful known-bad control. The writer requires `known_bad_detected=true`. The operator reported that an earlier reviewer changed false to true merely to pass validation. That downstream history is reported evidence, not independently inspected here.

Current source confirms the constraint in `review_evidence._validated_integrity_checks` and `_validate_evidence_shape`. A read-only helper probe on 2026-11-16 accepted true, refused false, and refused null even with a scope explanation. This reproduces validation semantics, not the complete downstream incident. Seed 209 already permits readiness-safe negative controls, but neither its policy nor the validator allows specialist not-applicable assertions. Both must change together.

## Product Intent

Reviewers of a change outside their lane's affected surface can record an honest readiness assessment without inventing a defect or claiming a control ran. This supports [VISION.md](../../../VISION.md)'s Horizon 1: preserve dependable delivery while correcting a demonstrated operating limit. It does not weaken delivery evidence or authenticate reviewers' assertions.

## Requirements

1. Permit explicit `integrity_checks.known_bad_detected: null` only on a specialist approval whose effective approval phase is readiness and whose existing lane/actor identity is valid. Determine phase through the canonical phase resolver, including legacy record representation. Do not infer eligibility from an actor name alone. Council approvals, delivery approvals and findings gain no new exception; existing operator semantics remain unchanged.
2. Require a non-empty `known_bad_detection_method` explaining the inspected scope and why no relevant surface in that lane is affected. Reuse this existing field rather than add a record kind or schema field. Guidance must distinguish this assessment from merely finding no defects, failing to run a control, or lacking evidence. The validator checks presence and type; review evaluates the rationale's truth and adequacy.
3. Keep the other four integrity checks true for executed specialist readiness approvals. Keep false refused, never normalize false or an omitted value to null, and do not default to not applicable. Where a relevant surface exists, use a meaningful readiness-safe known-bad control.
4. Apply identical eligibility rules to the served writer, persisted-record validation and readiness consumption. Preserve the null and explanation in evidence and human-readable review output. Ensure existing request identity/retry behavior retains their meaning. Preserve valid historical records, existing operator null defaults and delivery rules without rewriting the append-only ledger.
5. Refusal messages and guidance must explain the honest routes: a refuted plan claim, deliberately omitted known census site or rejected invalid review input when applicable; explicit null with scope rationale for an unaffected specialist at readiness. Do not suggest affirming a check merely to pass or manufacturing a product finding. Do not imply council or delivery eligibility.
6. Update canonical seed 209, tool/schema descriptions and affected self-hosted review guidance consistently. Census the actual integrity-contract carriers before editing; preserve unrelated workflow text and downstream vocabulary/profile behavior. No automatic removal of required lanes, waiver, new review round or change to gate selection is introduced.

## Scope

**In scope:** narrow readiness applicability policy, shared validation, record presentation, actionable errors, canonical/local guidance and regression tests.

**Out of scope:** new no-surface record types; council or delivery exceptions; changes to other integrity checks; automatic historical corrections or a repository-wide attestation audit; authentication of reviewer identity; downstream ledger edits; implementation of the reported Rust upgrade.

## Acceptance Criteria

- [x] AC-1: Through the served review writer, a valid unaffected specialist readiness assessment with explicit null and a scope rationale records successfully and remains valid through ledger reading and Prepare consumption. The unchanged baseline rejects that input. This establishes the intended outcome without asserting a known-bad was detected.
- [x] AC-2: Negative controls refuse null on specialist delivery, council readiness/delivery and ordinary findings; refuse false on executed specialist approvals, missing/blank rationale, omitted known-bad value, invalid lane/actor identity, and null/false for each other integrity check. Existing operator approvals and ordinary true specialist controls still pass.
- [x] AC-3: Round-trip, effective-phase and retry tests prove writer/reader agreement and preserve the null rationale. Existing valid historical ledgers remain valid without mutation; review output distinguishes not applicable from detected and from failed.
- [x] AC-4: Canonical and local guidance and tool/schema descriptions agree on eligibility and readiness-safe controls. Refusal tests distinguish applicable-but-unproven checks from the unaffected-lane path. A reviewer can identify the correct request from the returned guidance without changing false to true dishonestly.
- [x] AC-5: Focused tests, applicable distribution-profile checks, the framework suite and full docs validation pass. Record exercised hosts and limits; do not claim downstream incident replay or cross-platform execution without running them.

## Tasks

- [x] Census validation, phase resolution, schema, projection and guidance carriers; confirm the narrow contract and baseline controls.
- [x] Implement shared eligibility and rationale validation across writer and reader, preserving existing operator behavior and record identity.
- [x] Add served-path positive/negative, historical, retry and presentation regression tests.
- [x] Update seed 209 and affected local guidance, tool descriptions and changelog.
- [x] Run focused/profile checks, required delivery review, framework suite and full docs validation; record outcomes and remaining limits.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Contract and implementation | implementer | — | One writer for shared validation and schema changes |
| Guidance | technical-writer | Contract and implementation | Synchronize canonical and local policy |
| Verification | qa-reviewer | Guidance | Served-path and boundary controls |
| Independent review | code-reviewer, security-reviewer, docs-contract-reviewer, architecture-reviewer | Verification | Check gate scope, phase semantics and truthful guidance |

## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/wf_server/`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/contributing/review-and-evals.md`
- `docs/agents/`

Census any additional contract carrier before touching it. Changes outside this integrity policy require separate scope assessment.

## Affected Architecture Docs

Update the review-integrity contract in `docs/specs/mcp-tool-surface.md` and `docs/contributing/review-and-evals.md`. Check `docs/architecture/testing-architecture.md` for assertions that all specialist checks must be boolean true; update only if present. Ownership and storage architecture remain unchanged.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Honest readiness approval is the intended outcome |
| AC-2 | required | Prevents authority and phase leakage |
| AC-3 | required | Durable evidence must remain valid and explicit |
| AC-4 | required | Reviewers need an honest usable route |
| AC-5 | required | Protects existing behavior and delivery contracts |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-16 | Planned from operator-approved field feedback; no implementation | Current writer/read validator inspection and read-only helper probe: true accepted, false and null refused |
| 2026-11-16 | Readback: permit only explicit specialist-readiness known-bad null with inspected-scope rationale; preserve four true checks, false rejection, council/delivery and operator semantics. Before: unaffected security readiness null is refused; after: it records and survives Prepare. AC-1–4 target shared review validation, presentation, schema and seed/local guidance; AC-5 verifies regression limits. | Single implementation owner; tests and guidance follow shared contract, independent delivery review follows integration. |
| 2026-11-16 | Gapfill: shell used for documentation orientation and mechanical prose edits; code discovery and targeted source reads use MCP. | No source edit before activation and edit gates. |
| 2026-11-16 | Observe: shared specialist identity/phase eligibility now governs writer and persisted reader; only explicit known-bad null is exempt. Existing operator signoff/close behavior remains unchanged. Readiness output includes the scope rationale, including a separate readiness note where the main status table defaults to delivery. | `test_readiness_known_bad.ServedReadinessKnownBadTests.test_registered_write_read_retry_and_prepare_consume_null`; `ReadinessKnownBadTests`; `OperatorApprovalHonestAttestationTests` |
| 2026-11-16 | Observe: 229 focused default tests pass; registered writer writes null, reader retains it, same-identity retry does not append, changed rationale conflicts, and Prepare consumes the current approval. Rejection tests cover phase, council/actor identity, ordinary finding, other four fields, false, omitted value and blank rationale. | `python3 -B -m unittest test_readiness_known_bad test_review_evidence -q` with tests on PYTHONPATH; macOS only |
| 2026-11-16 | Guard landing: all 16 in-memory mutants fail named tests by assertions, none by test errors. Deleted each specialist identity condition (nonempty key, exact actor, operator actor, council actor, operator key, council key, readiness phase); removed record claim-kind/effective-phase checks; removed or broadened writer null carve-out, false rejection and rationale check; bypassed reader type, execution and rationale checks. Two initial test assertions were tightened to isolate claim-kind and type failures before the final mutation pass. | `test_write_and_read_boundary_matrix`, `test_explicit_null_round_trip_and_other_checks_are_true`, `test_false_missing_and_other_null_checks_remain_refused` in `test_readiness_known_bad.py`; retained reproducible probe `docs/waves/23n00 honest-readiness-integrity/evidence/mutations.py` and its bounded `mutations.json` result |
| 2026-11-16 | Observe: policy carriers census identified seed 209, generated caller schema, served tool description, local MCP spec and review guide. Historical waves/memories are unchanged; no duplicated local role integrity table exists. Full docs lint passed; status drift warning corrected. | `review_action_input_schema`; source census through `code_keyword`; docs validation |
| 2026-11-16 | Observe: focused profile checks pass on final behavior: second 227 tests (one intentional profile skip), declared 229 tests (no skips), each across evidence and new readiness tests. These are compatibility diagnostics, not the full-suite receipt. | `run_tests.py --profile second/declared --file test_readiness_known_bad.py --file test_review_evidence.py`; macOS |
| 2026-11-16 | Observe: broader focused workers passed 1,972 tests across four files (two skips), including 681 lifecycle and 1,062 retrieval tests, but the aggregate runner correctly refused qualification because implementation/test edits overlapped the run. Do not treat it as a green receipt; settled full-suite execution remains required under AC-5. Both edit gates are now closed; full docs validation passes without warnings. | `run_tests.py --file test_readiness_known_bad.py --file test_review_evidence.py --file test_server_tools_lifecycle.py --file test_server_tools_retrieval.py`; aggregate exit 1 (input drift), worker failures zero |
| 2026-11-16 | Observe: first full suite ran 12,847 tests across 250 files (12 skips); only lifecycle golden and MCP handler digest fixtures failed. Read-only comparison found exactly nine intended schema additions across three golden envelopes and only the wf_review_event docstring digest changed. Updated those two fixtures after the suite stopped; no production correction. | Canonical suite reported two failed files; fixture deltas verified against the admitted nullable-check schema and guidance |
| 2026-11-16 | Observe: two fixture updates plus the lifecycle oracle consumer now assert exactly the admitted schema additions while preserving the extraction oracle. Focused canonical verification passes 33 tests across both files, no skips. Progress Log table spacing normalized without changing meaning; framework gate closed. | `run_tests.py --file test_lifecycle_golden.py --file test_mcp_tool_registry.py`; green focused result, full-suite rerun pending |

| 2026-11-16 | All 12,847 tests across 250 files passed (12 skips), but the aggregate receipt was refused because delivery review writes changed events.jsonl and wave.md during execution. No source changed. Finish review records before the next full run; do not treat this as a green receipt. | Canonical run 597.937 seconds; preserved report `.wavefoundry/cache/qualification/refused-0b8741ca7a3f46eb94681e57b806deb7.json` |

| 2026-11-16 | Final qualification passes: 12,847 tests across 250 files, 12 skips, 603.650 seconds; canonical green receipt recorded. The preceding sandbox run refused loopback test servers; the unchanged host-permission run passed every affected group. All five independent delivery lanes and council approve with no findings. Full docs validation passes; all ACs/tasks complete. | `run_tests.py` exit 0; current `test-cache.json`; macOS execution only; profile checks and guard mutants above |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-16 | Allow explicit null only for unaffected specialist readiness checks | Reuses the existing not-applicable convention without weakening delivery | Error text alone leaves the policy defect; a new typed no-surface record adds unnecessary machinery |
| 2026-11-16 | Put the rationale in the existing detection-method field | Already required and retained with the check; no extra field needed | Dedicated rationale field would duplicate the same explanation |
| 2026-11-16 | Keep council and delivery unchanged | The field case demonstrates a specialist readiness scope mismatch | Broad null permission would admit untested checks in materially different phases |

## Risks

| Risk | Mitigation |
| --- | --- |
| Not applicable becomes a shortcut for missing verification | Require inspected scope rationale, preserve other checks, review adequacy independently |
| Writer accepts evidence the reader later rejects | Shared eligibility and served round-trip/Prepare tests |
| Legacy internal phase representation widens or denies eligibility | Use effective approval phase and test both representations |
| Historical false attestations are mistaken for corrected evidence | No ledger rewriting; the change does not certify old assertions |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
