# Integrity-Check Booleans Have No Defined Semantics at Readiness, Inviting False Execution Claims

Change ID: `1uf64-bug integrity-checks-readiness-semantics-undefined`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-04
Wave: `1uf65 integrity-checks-guidance`

## Rationale

Field report (target repo, 2026-08-04, on 1.15.x), verified line-for-line against this tree: a
reviewer recording a `approval_phase: readiness` approval could not determine what the five
`integrity_checks` booleans assert. Seed-209 defines four of them with an identical contentless
gloss ("Boolean evidence-integrity result", seed-209:100-103) while every neighboring field in the
same table is execution-flavored (`public_path`, `command_or_fixture`, `execution_status`,
`probe_class`) and the fifth boolean's definition (`known_bad_detected`: "pre-fix /
focused-mutation / injected-old behavior failed as intended") describes mutation testing, which is
impossible before any code exists. Seed-209:124 then requires the exact object on "every executed
finding or approval" and states plainly that "false ... fields fail."

The validator confirms the trap and sharpens it: `_validated_integrity_checks`
(`review_evidence.py:2918-2956`) rejects an executed approval carrying any boolean that is not
True, with the message `executed approval requires integrity_checks.<field>=true` (:2946-2949).
So on an approval an honest `false` is structurally unrecordable. That is a defensible
attestation-gate design (you may not approve unless you can affirm; if you cannot affirm, do not
approve), and the docstring at :2926-2928 even says so ("Executed approvals and findings must
affirm every boolean"), but the ONLY place that intent is written is a code docstring no reviewer
reads. The seed-level result is a fail-dangerous ambiguity: an agent that resolves it the wrong
way writes a false execution claim into the permanent ledger whose purpose is preventing exactly
that. The field reporter stopped instead; the report notes stopping was the lucky path, not the
guided one. The intended readiness reading (the booleans describe the REVIEW PASS: it made
non-vacuous assertions, reached the real tree, considered realistic boundaries, demonstrated it
can detect defects) is currently discoverable only by inspecting an already-committed record's
auto-filled fields (`public_path: "wf_review_event"`, `execution_status: "executed"`).

## Requirements

1. **One clear meaning with five distinct definitions:** seed-209 defines each boolean in plain
   evidence terms: the selected check ran without an unintended skip; it reached the public or
   faithful boundary; it considered realistic boundaries; its assertion could fail; and it
   detected a safe known-bad control. One short phase rule follows the table: a readiness approval
   attests to the review of the current tree, plan, census, or feasibility probe—not unimplemented
   product behavior. A delivery approval and any executed finding attest to their test/probe
   evidence. A non-executed finding may honestly carry `false`. Wording stays generic (no
   Wavefoundry-internal IDs; seeds ship to all targets).
2. **The gate is stated plainly:** every executed approval must be able to affirm all five
   booleans. If one cannot be affirmed, do not approve: record a finding when there is one, repair
   and re-review when appropriate, or stop and report. Setting a field true merely to pass the
   gate is a false ledger entry. “No unintended skip” at readiness means no selected readiness
   review step was silently skipped; future delivery probes are outside that review, not skipped.
3. **One readiness-safe known-bad example:** the table/guidance names a safe control such as a
   refuted plan claim, a deliberately omitted known census site, or a rejected invalid review
   input, alongside the existing pre-fix/mutation examples. A clean plan does not need a product
   defect or code mutation merely to earn readiness approval.
4. **Both validator messages teach instead of mislead** (council census, 2026-08-04): the
   per-field message at `review_evidence.py:2946-2949` is label-parameterized (`executed
   approval event requires ...` / fires for executed findings too via :2606), so the reworded
   text must read correctly for BOTH: name the contract generically, for example `executed
   {label} cannot carry integrity_checks.<field>=false: affirm it honestly, or do not record
   the claim as executed (for an approval: do not approve; record a finding or repair first)`.
   The sibling all-five-true message in `_validate_evidence_shape`
   (`review_evidence.py:3199-3201`, "executed evidence requires all five evidence-integrity
   checks") joins the same wording family; its existing pin at `test_review_evidence.py:850-861`
   re-points in the same change. The :2946 message currently has NO test pin (council-verified);
   AC-2's new pins cover both messages. Semantics unchanged: false still fails on executed
   claims; only message text changes.
5. **Every live guidance carrier agrees** (council-verified census, 2026-08-04): the carriers
   are seed-209's field table (:100-105), seed-209's OWN second definition site at :138 (the
   "Evidence integrity and classification" sentence, which restates all five checks in
   execution-only terms and is byte-pinned by `test_docs_lint.py:2671-2677`; it is rewritten to
   agree phase-aware and its pin re-points to the new sentence), the `wf_review_event` tool
   description (`server_impl.py` :27611-27616, :27711-27714), and
   `docs/specs/mcp-tool-surface.md:638`. Carriers may point to the canonical seed table rather
   than duplicate it, but none may retain the execution-only summary. The rendered mirror
   question is RESOLVED: seed-209 has no full rendered mirror by renderer design
   (`render_agent_surfaces.py` excludes it from full-body copy; `docs/contributing/
   review-and-evals.md` is pointer-only and already conformant), so no mirror edit is needed.
   Two execution-only restatements are RETAINED BY DESIGN and deliberately not edited
   (lane census, 2026-08-04): seed-239's Evidence-integrity gate (:47-57) and the renderer's
   QA-evidence block (`render_agent_surfaces.py:842-855`, rendered into
   `docs/agents/qa-reviewer.md`) are the QA DELIVERY lane's checklist; :57 scopes their
   consequence to "a required delivery approval claim", so the readiness ambiguity cannot
   arise there, and editing them would trip three unrelated pin sites for no fix. The :138
   rewrite must preserve an equivalent load-bearing falsifiability clause ("would fail"),
   which is the property its byte-pin exists to protect.
6. **One focused regression guard:** extend the existing guidance-registry contract test to pin
   the five per-field definitions and the one phase rule in the canonical seed table, and that
   each of the other public carriers either carries the phase-aware meaning or points to the
   seed table (per Requirement 5), with none retaining the execution-only summary. Pin with
   short field-specific anchors, not full-sentence byte-pins: the five definition cells are
   pairwise distinct, none contains the retired gloss, each carries a short semantic anchor
   not derivable from its field name, plus one phase-rule anchor and the existing negative
   control. Do not add a new schema, event field, validator branch, or test module.

## Scope

**Problem statement:** the integrity-check booleans are required at readiness but defined only in
execution terms, and the validator's message reinforces the wrong reading; honest reviewers stall
and incautious ones write false execution claims into the permanent ledger.

**In scope:** seed-209 field-table, :138 definition sentence, and guidance text (gated
`seed_edit_allowed`); both validator message strings in `review_evidence.py` (:2946-2949 and
:3199-3201); the existing guidance-registry contract test, the :138 byte-pin in
`test_docs_lint.py:2671-2677`, and the :3200 message pin in `test_review_evidence.py:850-861`;
the `wf_review_event` tool description; and `docs/specs/mcp-tool-surface.md`.

**Out of scope:** validator SEMANTICS (executed approvals still require all-true; the
attestation-gate design is kept, not weakened); registry field names and shapes; the
`wf_review_event` auto-fill behavior (`public_path`, `execution_status`), which is correct.

## Acceptance Criteria

- [x] AC-1: Seed-209 gives each boolean a distinct plain-language definition, states the one
  readiness/delivery/non-executed-finding rule, the cannot-affirm-means-do-not-approve contract,
  and one readiness-safe known-bad control; the :138 sentence agrees phase-aware (no second
  execution-only definition survives in the seed) and its byte-pin re-points; docs-lint passes.
- [x] AC-2: Both validator messages name the contract (affirm honestly, or do not record the
  claim as executed) with wording that reads correctly for approvals AND executed findings;
  behavior is byte-identical for valid input (tests pin that false still fails on executed
  claims for both message sites and that non-executed findings may still carry an honest false).
- [x] AC-3: The `wf_review_event` tool description and MCP tool spec carry the same phase-aware
  meaning or point to the canonical seed table; no carrier retains the execution-only summary
  except the two delivery-scoped retentions Requirement 5 records (seed-239 gate and the
  renderer's QA-evidence block), which stay untouched.
- [x] AC-4: The existing guidance-registry contract test pins the five definitions and the phase
  rule; the full framework suite passes.

## Tasks

- [x] Census the seed table, the :138 sentence, tool description, and MCP tool spec
- [x] Rewrite the seed table, the :138 sentence, and one phase-rule paragraph under the gate;
  update the public carriers without duplicating a second detailed contract
- [x] Reword both validator messages; re-point the :138 byte-pin and the :3200 message pin;
  extend the existing guidance-registry contract test
- [x] Docs-lint + focused contract test + full suite
- [x] CHANGELOG bullet (next release section)

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| fix        | implementer | —          | Seed edit requires the `seed_edit_allowed` gate |


## Serialization Points

- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`; `review_evidence.py`;
  `test_docs_lint.py` (the :138 byte-pin), `test_review_evidence.py` (the :3200 message pin),
  and `test_server_tools.py` (the guidance-registry contract test)

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` is affected because it carries the current execution-only
summary. No contract shape changes are expected.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The definitions and contract are the fix itself; without them the fail-dangerous ambiguity persists |
| AC-2 | required | Message wording that misleads at the failure moment recreates the type-true pressure |
| AC-3 | required | A carrier retaining the execution-only summary re-opens the trap on that surface |
| AC-4 | required | Tripwire rule: contract-surface guidance ships with its updated contract test and a green suite |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-04 | Filed from a target-repo field report; every claim verified against this tree (seed-209:100-103 contentless glosses, :124 executed-object rule, validator rejection of false at review_evidence.py:2946-2949 with the quoted message). The same ambiguity was hit in this repo's own 1u8o5 readiness approvals, resolved by unguided improvisation that happened to match the docstring's intent (:2926-2928). | Field report 2026-08-04; code_keyword/code_read census this session |
| 2026-08-04 | Readiness council ran (red-team + docs-contract-reviewer, both code-grounded, MCP-first). Red-team refuted the census's completeness on three points, all folded in-phase: seed-209:138 is a second execution-only definition site byte-pinned by test_docs_lint.py:2671-2677; a sibling all-five-true message at review_evidence.py:3199-3201 is pinned at test_review_evidence.py:850-861 while the :2946 target message has NO pin; the :2946 message is label-parameterized and fires for executed findings, so the reworded text must read correctly beyond approvals. Docs-contract confirmed the five definitions map one-to-one onto the registries, verified committed ledger practice matches the codified phase rule, and resolved the mirror question (seed-209 has no full rendered mirror by renderer design; review-and-evals.md is pointer-only and already conformant). | Council seat reports 2026-08-04 |
| 2026-08-04 | Four prepare-lane reviews ran (code, qa-reviewer, docs-contract, qa; all fresh, code-grounded, MCP-first). Code and both QA lanes approved; docs-contract WITHHELD on two missed execution-only carriers (seed-239:47-57 Evidence-integrity gate; render_agent_surfaces.py:842-855 QA block rendered into docs/agents/qa-reviewer.md) and AC-3's stale mirror phrase. Resolution folded in-phase: both retentions recorded as delivery-scoped by design (editing them fixes nothing and trips three pin sites), AC-3 renamed to the real carrier set, Requirement 6 gained the anchor-not-byte-pin assertion shape, and the :138 falsifiability-clause preservation note added. Executed baselines recorded green: test_review_evidence 139 OK, CouncilSeedVerificationContractTests 9 OK, test_render_agent_surfaces 63 OK, the two contract tests OK. | Lane reports 2026-08-04 |
| 2026-08-04 | Implemented (all edits MCP-first census, harness edits). Seed-209: five distinct table definitions (each keeps its backticked field token, none retains the retired gloss), one phase-rule paragraph inserted directly after the Executable Evidence Record table (readiness attests to the review of the current tree/plan/census/feasibility probe, not unimplemented product behavior; non-executed finding may honestly carry false; cannot-affirm means do-not-approve; readiness-safe known-bad examples), :138 sentence rewritten phase-aware preserving "would fail against the known-bad behavior". review_evidence.py: per-field message at :2946 now label-parameterized attestation wording; all-five message at :3199 joined the same family; semantics untouched. Pins re-pointed: test_docs_lint.py :138 byte-pin (still pins the falsifiability clause), test_review_evidence.py :3200 substring pin. Three new methods: executed-approval false, executed-finding false (both assert the full new message per label), non-executed finding honest-false accepted at the build seam. Vocabulary contract test extended: parsed definition cells pairwise distinct, retired gloss absent from all three surfaces, five field-specific anchors, phase-rule anchor on seed + spec + tool description; eight lane-recipe anchors untouched and green. Carriers: wf_review_event docstring (:27611 region and integrity_checks arg doc) and mcp-tool-surface.md:638 now phase-aware and point at the seed table. CHANGELOG: new `## [Unreleased]` Fixed bullet. Seed-239 and render_agent_surfaces.py QA block untouched per Requirement 5. | test_review_evidence 142 OK (139 baseline + 3 new); CouncilSeedVerificationContractTests 9 OK; test_render_agent_surfaces 63 OK; both wf_review_event contract tests OK; wf_validate_docs pass; full suite 6801 tests across 62 files OK |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-04 | Keep the attestation-gate semantics; fix the guidance and the message | The all-true requirement on executed approvals is the designed integrity property (approve only what you can affirm); the defect is that its contract is written only in a code docstring | Allow honest false on approvals (rejected: converts the attestation gate into a survey and weakens the ledger); auto-derive the booleans (rejected: the tool must never manufacture the reviewer's judgment, per seed-209's own rule) |
| 2026-08-04 | Keep the table-first structure; rewrite :138 to agree rather than making it the single definition site | The operator's Requirement 1 puts the definitions in the field table where reviewers look them up; two short aligned sites with re-pointed tests stay simple, and restructuring the seed's narrative section exceeds the fix | Red-team alternative: make :138 the sole canonical definition and have the table point at it (rejected: inverts the operator-authored structure for equal simplicity at best) |
| 2026-08-04 | Regression anchors = the five council-named fragments (unintended skip, faithful boundary, realistic, could fail, known-bad) plus the phase anchor "not unimplemented product behavior" asserted on ALL three public carriers, with the retired gloss forbidden everywhere | Short fragments pin meaning without brittle full-sentence byte-pins (Requirement 6); asserting the phase anchor per carrier also machine-checks AC-3 conformance in the same existing test | Byte-pin the full definition sentences (rejected: brittle and contrary to Requirement 6); a separate carrier-conformance test module (rejected: forbidden by the simplicity constraint) |
| 2026-08-04 | Honest-false regression exercised at the build_compact_review_event seam with execution_status "unverified" | That is the exact seam the :2946 message guards (via :2606), so the test proves the honest-false path at the changed site without entangling unrelated non-executed evidence-shape rules | Route the honest-false row through full validate_records too (rejected: couples a message-only change to independent non-executed shape constraints) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Guidance regresses to generic field names without meanings | AC-4 extends the existing contract test with the five definitions and one phase rule |
| Public carrier drifts from the seed | AC-3 names the only additional live carriers and permits a canonical pointer instead of duplicate prose |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
