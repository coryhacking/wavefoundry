# Canonical declared-wave test fixtures

Change ID: `1yd25-debt canonical-declared-wave-fixtures`
Change Status: `complete`
Owner: framework maintainer
Status: complete
Last verified: 2026-09-20
Wave: `1yd24 fixture-fidelity`

## Rationale

A declared wave has four prerequisites that nothing in the test tree states in one place, and missing any one silently collapses a fixture into a no-op rather than failing loudly. A sibling `events.jsonl` must exist or the prepare policy state refuses to compute; the wave header must carry `review-evidence-source: events.jsonl` or every typed review event is refused; the record needs exactly one `## Finding Synthesis` projection with its markers; and a `run` event with `run_kind="readiness"` must precede any approval or the marked wave is rejected. The workflow config adds a fifth trap: `wave_review` missing either `enabled` or `delivery_mode` is INVALID rather than absent, so the wave fails closed on `review_policy_reprepare_required`.

This was paid for in wave `1y0h0`. The AC-1 golden for the gate extraction was authored by hand and looked correct; in fact all three of its fixtures short-circuited on the same early diagnostic, so a golden that claimed to pin the prepare, review and close envelopes across three waves covered none of the spans being refactored. Four debug cycles recovered it, and the repair was not a better hand-authored record: it was to stop hand-authoring and drive the producers in sequence.

The census shows this is systemic rather than a single author's slip. A refreshed census finds 51 literal declaration occurrences across ten files and creator references in seven files. Occurrences include lifecycle setup, parser/projection inputs, assertions and tampering; they are not 51 independent header writes. The framework is not at fault here — it failed closed with an exact message on every one of the four prerequisites. What is missing is a shared builder, so the cheapest path for the next author is the correct one.

## Requirements

1. `server_tools_support` gains `make_declared_wave(srv, root, slug, *, status="planned", change_ids=(), ready=False, readiness_run=False, approvals=(), ...)`. The additional keyword parameters explicitly accept scoped doc-gate stubs. It calls the real producers in lifecycle order: `wf_create_wave_response(mode="create")`, `wf_add_change_response(mode="create")` per existing change ID, optional `wf_prepare_wave_response(mode="ready")` to publish the receipt, the optional readiness run, then approvals. Callers create admitted change documents through the canonical change creator before supplying their IDs; tests may customize change content when that content is their subject. Return the actual generated wave ID and record path; do not assume fixed IDs.
2. `review_policy_config(**overrides)` returns a complete valid `wave_review` block with `enabled=True` and `delivery_mode="targeted"` by default. Callers install that block in the existing `_make_repo` config; `_make_repo` retains its minimal defaults.
3. Receipt preparation requires at least one admitted change and explicit lint/garden stubs, applied in a scoped context and restored on all exits. Explicit scoped stubs also cover `_run_post_write_lint` and background refresh for the whole producer sequence; callers may supply their existing fakes, and every patch must restore on failure. The helper must assert successful producer results and a published receipt; the initial prepare may return only the expected missing-readiness-approval refusal while publishing that receipt. Unexpected errors must fail at their producing step, with the full diagnostic message. Approval/run refusal must not be swallowed. No network or unrequested real lint/garden subprocesses.
4. A status other than `planned` may rewrite only the produced `Status:` line as an explicitly synthetic test escape hatch. All other lifecycle state comes from producers. Tests exercising an intentional malformed state may mutate the resulting fixture afterward and label that mutation.
5. Migrate valid lifecycle prerequisites to the helper. Keep hand-authored negative fixtures, component inputs whose parser/projection/index representation is the subject, and direct producer-contract fixtures that must exercise creation itself. Each retained declaration occurrence must have an adjacent reasoned classification: `negative-fixture`, `component-fixture`, `producer-fixture`, or `declaration-check` for assertions/removal tokens. Do not relabel valid component inputs as malformed. Preserve immutable golden baselines; investigate changed behavior instead of refreshing expected outputs to fit the helper.
6. Implementation changes for this change stay inside `scripts/tests/`; no production modules. Normal wave documentation and the sibling seed change are separate scope.

## Scope

**Problem statement:** Building a valid declared wave requires four prerequisites plus a valid policy block, stated nowhere in one place, and a fixture that misses one passes as a green test that exercises nothing.

**In scope:**

- The two `server_tools_support` helpers and their unit coverage.
- The anti-vacuity guard test (AC-2), which is the durable protection.
- The census test (AC-3) and the migration of positive fixtures.

**Out of scope:**

- Any production behavior change.
- Negative and component fixtures, whose deliberate input representations remain hand-authored by design.
- The `isolated_run` docstring defect found during `1y0h0` review (its docstring claims `capture_output=True` triggers UTF-8 decoding when the code keys on `text=True`); it is real and recorded, but it belongs to the subprocess helper, not to fixture fidelity.

## Acceptance Criteria

- [x] AC-1: `make_declared_wave` produces a wave whose `validate_external_review_evidence(wave_md).ok` is true, and whose prepare `dry_run` response carries neither `review_evidence_invalid` nor `review_policy_reprepare_required`.
- [x] AC-2: A fixture seeded with `at least one canonically created/admitted change, ready=True, readiness_run=True, approvals=("wave-council-readiness",)` produces a prepare `ready` response whose status is not `error` and which carries no blocking diagnostic, proving the fixture REACHES the readiness span rather than short-circuiting before it. The test proves its known-bad by omitting the readiness run record, which must redden it.
- [x] AC-3: A token-based census walks the test tree and checks each Python string token (including f-string literal segments on Python versions that tokenize them separately) containing the literal `review-evidence-source: events.jsonl`. Each retained occurrence requires an adjacent nonempty reason with an allowed classification from Requirement 5, read with `tokenize`. A helper call or comment elsewhere in the file cannot exempt the site. Tests prove detection of an unannotated site even in a file that calls the helper, rejection of empty/misplaced annotations, acceptance of reviewed classified sites, and non-vacuity against named existing corpus files. This deliberately bounded literal guard is not a data-flow analyzer; computed declarations are covered by the reviewed migration census, not claimed as statically detected.
- [x] AC-4: Every positive fixture migrated to the helper still passes, and the full suite is green.
- [x] AC-5: The helper/migration implementation modifies only `scripts/tests/`, with no production modules or immutable golden baselines changed; review the per-change diff separately from wave bookkeeping and sibling seed/render changes.

## Tasks

- [x] Add `review_policy_config` and `make_declared_wave` to `server_tools_support.py`.
- [x] Write the AC-1 validity test and the AC-2 anti-vacuity test with its known-bad.
- [x] Refresh the declaration census and classify lifecycle prerequisites, negative/component/producer fixtures, and assertion/tamper tokens.
- [x] Migrate positive lifecycle prerequisites to the helper; annotate retained sites with their specific classification and reason.
- [x] Write the AC-3 census test with its non-vacuity floor.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.

## Agent Execution Graph

| Workstream  | Owner       | Depends On | Notes |
| ----------- | ----------- | ---------- | ----- |
| helper      | implementer | —          | the two `server_tools_support` additions |
| guards      | qa          | helper     | AC-1, AC-2 and its known-bad |
| migration   | implementer | guards     | census, classification, migration, AC-3 |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/server_tools_support.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

None. This is test infrastructure with no production surface and no boundary change.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Without it the helper could produce the same silently-invalid wave it exists to prevent |
| AC-2 | required  | The anti-vacuity guard is the actual protection; AC-1 only proves the record parses |
| AC-3 | required  | Without a census the corpus drifts straight back to hand-authored fixtures |
| AC-4 | required  | Migration must not weaken the tests it touches |
| AC-5 | required  | Keeps a test-infrastructure change from carrying production risk |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-18 | Change planned from a defect paid for in wave `1y0h0`: a hand-authored AC-1 golden whose three fixtures all short-circuited, recovered over four debug cycles. Census recorded: 51 header-writing sites across 10 files against 6 files using the canonical creator | this document |

| 2026-09-20 | Readback: valid lifecycle prerequisites currently mix canonical creation and hand-written state. Add a strict producer helper, migrate setup, and classify retained test subjects; preserve production code and immutable baselines. Thought: implement helper and non-vacuity tests first, then migration/census, then full-suite integration | AC-1 through AC-5; server_tools_support.py and tests only |

| 2026-09-20 | Gapfill: live MCP keyword/read established census and producer owners; local AST/token scans and mechanical edits cover bulk sites beyond targeted retrieval. Added strict producer helper with scoped four-stub contract; verification in progress | server_tools_support.py; /tmp/fixture-fidelity-census.json |

| 2026-09-20 | AC-1/2/3 implemented and focused green: strict canonical helper, exact missing-readiness-run final-Prepare control, token-local classifications including f-string segments. Migrated dashboard, memory, phase-alias and partial policy helper; root contributed docs-lint readiness migration and its eight annotations. Broader affected-file checks ongoing; full-suite integration remains coordinator-owned | /tmp/fixture-census-first.log; /tmp/fixture-policy-migration.log; test_declared_wave_fixtures.py |

| 2026-09-20 | Focused evidence: 11 helper/census tests, 66 policy/readiness tests, 43 migration/helper/golden tests and 35 dashboard snapshot tests green; coordinator ran all 1106 docs-lint tests green. Seven in-memory mutants killed: omitted run/approval, skipped receipt proof, leaked stubs, filewide helper exemption, dropped f-string segments, distant comments. Immutable golden files unchanged; full-suite receipt and AC-4 remain pending coordinator integration | /tmp/fixture-fidelity-mutants.json; /tmp/fixture-final-focused.log; /tmp/fixture-dashboard-focused.log; /tmp/1yd24-docslint-tests.log |

| 2026-09-20 | Observe: coordinator diff review confirms all helper/migration source edits are inside scripts/tests; production modules and immutable fixture/golden files are unchanged. Sibling guidance changes are separately accounted. Dashboard full module passed all215 tests with host process visibility | git diff against8877a000; delivery-fingerprint.json; full-suite module result |

| 2026-09-20 | Reflect: delivery review found six guards whose tests were absent or failed for a different reason. Thought: repair tests only using actual receipt publication before corrupting Prepare responses and explicit invalid inputs. Observe: 16 fixture/guidance tests pass; all six independent guard deletions now produce assertion failures with zero errors/skips. Initial draft correctly failed on reused admitted change and tuple/list mismatch; corrected to a fresh canonical change per case and the actual ledger error shape before freezing | fixture-helper-guard-pins; test_invalid_helper_inputs_fail_before_producer_entry; test_invalid_prepare_envelopes_reject_after_real_receipt_publication; repair-mutations.json and repair-mutation-probe.py |

| 2026-09-20 | Final integration: 9444 tests across117 files passed in281.625s with12 existing skips; fresh receipt independently recomputed by coordinator. Full docs validation passed with no errors; existing AC wording advisory remains nonblocking. All required ACs/tasks have evidence | run_tests.py; receipt inputs_hash `4decf445ea1e79f2584c875baea38b21ba8179d1aa445eb7abaa67b5107c6132`; delivery-evidence.md |

| 2026-09-21 | Readback / Thought: operator review identified the synthetic Status rewrite preceding Prepare. Move it after every producer and reject legacy status ready; pin canonical planned input at admission, Prepare, run and approval. This is a bounded helper fidelity repair; no runtime or seed changes. Reverify affected delivery lanes and refresh the suite receipt | server_tools_support.py; test_declared_wave_fixtures.py |

| 2026-09-21 | Observe / Reflect: synthetic escape moved to the final step; every real producer sees planned. Legacy ready rejected before producer entry. All 16 focused tests pass; independent old-order and ready-restoration mutants fail, as do all six prior guard deletions. Code and QA approvals refreshed; full suite pending. Preserve the distinction between producer-backed setup and the final synthetic test subject | status-order-review.md; status-order-mutation-probe.py |

| 2026-09-21 | Repair integration complete: 9444 tests across 117 files, 12 existing skips, 294.428s, OK. Receipt hash freshly recomputed and current; code and QA repair approvals recorded | receipt `1b37f7821ab1163954e6ac71e32ca64496ef88208578afbcd0c4118ca65845c5`; status-order-review.md |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-18 | A shared builder rather than documentation alone | The prerequisites were already discoverable and the framework already reported each one exactly; what failed was that hand-authoring was the cheapest path. Changing the cheapest path is the only durable fix | Document the prerequisites in a comment: leaves the cheap wrong path in place. Validate fixtures at test teardown: catches it later and in more places, without making the right path easier |
| 2026-09-18 | Negative fixtures stay hand-authored and are annotated | A record deliberately malformed to exercise a validator is correct precisely because it is hand-authored; forcing it through the builder would destroy the subject of the test | Migrate everything: would break the validator suites and misread what those fixtures are for |

| 2026-09-20 | Reconciled the current census, producer ordering, scoped stub contract, per-site classifications, and test-only boundary before readiness review | Feasibility probe reached final prepare with an admitted change/run/approval; missing run fails final prepare, while standalone evidence validation still parses. Filewide helper presence cannot exempt a handwritten site | Keep binary positive/negative census: misclassifies valid parser inputs; blanket migration: changes test subjects |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The migration silently weakens a test whose fixture differed from the builder's output in a way that mattered | Migrate per file with the suite run after each; a fixture whose behavior changes under the helper is a finding to investigate, not a diff to accept |
| The census test's classification becomes a rubber stamp, every site carrying a negative-fixture comment | The comment must name what it malforms, and the classification is reviewed at delivery against the census recorded in the Progress Log |
| The helper spawns real subprocesses through `mode="ready"` and slows the suite | Stubs are parameters, not defaults; a caller that does not need the receipt does not pass `ready=True` |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
