# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-10-07
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `203pu graph-call-attribution-integrity`
Title: Graph Call Attribution Integrity

## Objective

Prevent unresolved receiver-method calls from targeting unrelated project functions through name collisions, and expose call-edge attribution counts in graph reports. Preserve established bindings and existing report compatibility.

## Changes

Change ID: `201wg-bug graph-receiver-call-target-integrity`
Change Status: `implemented`

## Participants

- Coordinator: wave-coordinator (Codex)
- Write-owning roles: implementer
- Requested review lanes: code-reviewer, qa-reviewer, architecture-reviewer, performance-reviewer, docs-contract-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer

Completed At: 2026-10-08

## Wave Summary

Wave `203pu` (Graph Call Attribution Integrity) delivered one change: Preserve Unresolved Receiver Calls and Expose Graph Attribution Counts. Notable adjustments during implementation: Preserve Unresolved Receiver Calls and Expose Graph Attribution Counts: Docs: architecture (unowned member calls, legacy SQL-inclusive degree prose corrected, call_edge_counts semantics), MCP spec, wf_graph_report description, CHANGELOG 1.29.0 operator-action note plus Added/Fixed bullets, docs/RELIABILITY.md builder version.; Preserve Unresolved Receiver Calls and Expose Graph Attribution Counts: DEL-1 repair (regressions on established owned receivers, AC-2): `_ts_lexical_owner_receiver` keeps Ruby constant-only `scope_resolution` receivers (`M::K.baz()`, `::K.baz()`) and Java `Outer.this` / `Outer.super` (`field_access` ending in `this`/`super`) owned; the Rust declaration search strips one reference layer (`_rust_reference_inner_type`: `&S`, `&mut S`, `&'a S`) and `_rust_value_type` reads `let s = S;` as unit struct `S`. HEAD-vs-fixed probes: Ruby `a.rb::M.K.baz`, `a.rb::K.baz`, cross-file `k.rb::M.K.baz`, `k.rb::K.baz` and Java `Outer.foo` now match HEAD exactly (target, EXTRACTED, no unowned flag); Rust `&S`, `&mut S`, `let s = S;`, `let s: &S` bind `S.foo` same-file and cross-file as at HEAD, now at RECEIVER_RESOLVED instead of HEAD's name-only EXTRACTED with receiver_unknown. `&Vec<u8>` and `&mut u8` receivers stay unowned (bounded stripping, no inference). Builder version stays 53 (unreleased within this wave).; Preserve Unresolved Receiver Calls and Expose Graph Attribution Counts: Reverification found the callee-side paren unwrap untested; coordinator added `test_parenthesized_callee_keeps_its_computed_receiver_unowned` (JS `(b.subject().render)()` stays `external::render` unowned). Removing the unwrap in a scratch copy fails it; repo file 38 tests OK.

**Changes delivered:**

- **Preserve Unresolved Receiver Calls and Expose Graph Attribution Counts** (`201wg-bug graph-receiver-call-target-integrity`) — 8 ACs completed. Key decisions: Select structural ownership safeguards plus additive report attribution in one bug change.; Preserve unresolved edges and established bare/qualified/typed calls; classify syntax rather than blocking every receiver_unknown edge.
Closure reconciliation (2026-10-08): the change is implemented, all in-scope ACs/tasks complete, no deferred `[~]` ACs. Required specialist and docs-contract approvals, council-readiness and operator approval are current; the receipt does not select delivery council. DEL-1 and DEL-2 are terminal. Fresh DEL-2 verification passed 21 tests and rejected four source regressions; the shared 11,885-test framework receipt was proven at close.

Retrospective: constrain target assignment by receiver ownership, not confidence alone; classify effective call edges without changing legacy rankings. These decisions remain in the graph architecture, MCP specification and existing graph receiver-ownership memory `203ew`. Generic bookkeeping candidates were rejected; repeated memory proposal found no new or pending candidates. Known residual language heuristics remain disclosed in the change and CHANGELOG. Cleanup: retained the record, admitted change and authoritative ledger as unique evidence; no disposable artifacts were found. Historical readiness-only statements below are superseded by the delivery evidence and closure.

## Watchpoints

- Watchpoint: operator authorized implementation on 2026-10-07 (prepare, review and implement); close, commit and push remain operator-owned.
- Preserve unrelated working-tree changes and serialize future shared indexer/server edits.
- Generic isolated fixtures establish acceptance; Tensorwell remains historical field evidence.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| DEL-1 | do_now | no | completed | code-reviewer, qa-reviewer |
| DEL-2 | do_now | no | completed | — |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| council-readiness | approved | current executed approval by coryhacking follows every affected repair | none |
| code-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| qa-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| architecture-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| performance-reviewer | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
| operator-signoff | approved | current executed approval by coryhacking, not receipt-bound, follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: approved by explicit operator closure instruction on 2026-10-08; authority is the typed delivery approval in events.jsonl.

## Dependencies

- No external wave dependencies. Declare intra-wave dependencies with a `Depends On:` line containing full backticked change ids in each change's block under `## Changes`.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 180 | 1,556,462 |
| implement | 37 | 1,870,627 |
| review | 59 | 386,077 |
| **Total** | **276** | **3,813,166** |

<!-- wave:context-efficiency-state {"generation":137,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":37,"content_source_credit":1944285,"derived_artifact_credit":0,"direct_net":1870627,"estimated_tokens_saved":1870627,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":1662,"response_debit":73734,"source_credit_count":72,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1738},"plan":{"calls":180,"content_source_credit":2052145,"derived_artifact_credit":3210,"direct_net":1556462,"estimated_tokens_saved":1556462,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16364,"response_debit":491730,"source_credit_count":64,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":9201},"review":{"calls":59,"content_source_credit":461889,"derived_artifact_credit":1218,"direct_net":386077,"estimated_tokens_saved":386077,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":5639,"response_debit":73775,"source_credit_count":28,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2384}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":276,"content_source_credit":4458319,"derived_artifact_credit":4428,"direct_net":3813166,"estimated_tokens_saved":3813166,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":23665,"response_debit":639239,"source_credit_count":164,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":13323},"wave_id":"203pu graph-call-attribution-integrity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 1 | 0 | 1 | 769,690 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":769690,"surfaced_events":1} -->
<!-- wave:exploration-avoided end -->
## Review checkpoints

### Prepare wave — work allocation

- Primer depth: standard, as selected by the current review-policy evaluator; scope is bounded to existing graph binding/report mechanisms.
- Phase 1: isolated red-team primer, three stances and two questions.
- Phase 2: isolated architecture-reviewer, security-reviewer, qa-reviewer and reality-checker seats.
- Rotating fifth: performance-reviewer, strongest alternative after the fixed seats.
- Additional required lanes: code-reviewer and docs-contract-reviewer.
- Independent reviewers use fresh contexts with bounded read-only investigation and safe temporary probes; no implementation or lifecycle mutation authority.
- Model allocation: available inherited host model, three worker slots, sequential batches; actual model internals are not observable.
- Product-owner acknowledgment: the operator requested this bug fix/report enhancement and preparation, then explicitly deferred implementation. No additional product decision is proposed.

### Review plan — decision branches

Self-answered from current graph source and the admitted brief:

- Bindings: classify instance-member syntax and ownership evidence, not a name denylist or the broad receiver_unknown flag. Protect local extraction and cross-file fragment resolution together; retain bare, typed, associated and construction controls. Anchors: graph_indexer._resolve_rust_call_target, _ts_call_has_receiver, _ts_resolve_target and _resolve_fragment_edge.
- Reports: keep legacy SQL-inclusive degree fields and ranking, adding call-only attribution categories. fan_in uses incoming calls; fan_out/chokepoints/file_hubs use outgoing calls. Missing or contradictory resolved-plus-unknown confidence is unclassified; receiver_unknown overlaps the total. Anchor: GraphQueryIndex.report.
- Collapsed views: classify retained effective edges using existing representative metadata. These counts are not raw call-site multiplicities or provenance unions. Paired raw/collapsed mixed-provenance and input-order controls belong in AC-5; no transform rewrite is proposed. Anchors: collapse_generated_view, collapse_package_to_directory_view and collapse_class_module_view.
- Rollout: bump the graph builder through existing invalidation/publication; no consumer source edits, automatic consumer upgrade, bespoke migration or Rust compiler integration. Anchors: GraphStateStore.ensure_current and graph_query._ensure_graph_builder_current.
- Brief comparison: the plan addresses the observed topology defect and its opaque report presentation. Complete source coverage remains historical evidence, not a correctness oracle; only named Tensorwell examples were classified.

Operator Questions: none. Stop Condition: all branches in Requirements, ACs and Scope are resolved. Delivery must still prove the behavior and compatibility matrices; this optional review records no typed approval.

### Readiness evidence — frozen packet

Reviewed plan SHA-256: cb2a70a911879fa689e7751e1a0792536e3b9c64df374c4ebb162daadf2adf4a. Current graph_indexer SHA-256: e31053911014f2f9bd9b4fc4fde50f11a663a869578a00d0eef42d8d30ad86fb; graph_query: 3ff07433314cf72b62d2491df1478231c32226855d06ca4564b9282f369ea0c7. Builder: 52. Reviewed handler/server/test hashes also matched the frozen packet; no code edits in this effort.

Requested settings for architecture, QA, reality, code, docs-contract and performance: gpt-6.1-sol with high reasoning, selected for bounded multi-stage ownership/counting analysis. The primer used the inherited capable host model; the security remit reused its isolated context (only the primer retained, no other fixed-seat output or implementation/repair context). Actual runtime identities/effort are not observable. Independent read-only contexts supplied reviewer facts; the coordinator records them, without implementing or authoring their verdicts. Transient host thread-cap refusals delayed reviewer starts; sequential batches preserved independence.

| Context | Observation and readiness-safe known-bad control | Result |
| --- | --- | --- |
| graph-203pu-primer-v1 | GraphQueryIndex.report mixed graph: calls2 plus SQL read1 gave fan_out3; rejected resolved-only legacy-count claim. Strongest challenge: guard target assignment at both local and fragment stages, not confidence alone. | No blocker; two primer questions. |
| graph-203pu-architecture-v1 | Canonical disposable publication reproduced same/cross-file false binding and target-only edit; bare/typed/associated/construction controls resolved. Existing stored builder51 transitioned to52. Rejected confidence-only ownership claim; generated collapse raw3 to effective2 retained representative unknown metadata. | PASS readiness. |
| graph-203pu-qa-v1 | Real iterator same-file collect and cross-file edit/rename probes; production report handler on disposable published graph gave count2 and lacked new fields. Class/module collapse raw2 to effective1 retained first unknown flag. AC1–8 have feasible real seams and falsifiable assertions. | PASS readiness. |
| graph-203pu-security-v1 | Source AST census traces report to version guard and coordinated build with stdout isolation; rejected report cannot write internally claim. No new trust boundary or privilege path. | Approved with notes; no blocker. |
| 203pu-reality-readiness-20261007 | Six plan contract checks and source AST audit rejected confidence guard prevents target rewrite; confirmed effective-edge semantics and existing collapse keys. | PASS readiness. |
| graph-203pu-code-v1 | Five helper binding sites censused; deliberately omitted local fallback rejected. Actual _merge_call_evidence kept known witness in either order and unknown-only provenance; all frozen hashes matched. | PASS readiness. |
| graph-203pu-docs-v1 | Actual report fixture gave fan_in2/fan_out3 for calls2 and SQL read1, rejecting resolved-only/calls-only claims. Required docs updates already in scope. | PASS readiness. |

Durable source/test anchors: graph_indexer._resolve_rust_call_target, _ts_call_has_receiver, _ts_pure_callee_path, _ts_resolve_target, _raw_fragment_edge, _output_fragment_edge, _resolve_fragment_edge, _merge_call_evidence, GraphIndexSession._extract_tree_sitter_artifact; graph_query.GraphQueryIndex.report and all three collapse functions; test_graph_incremental_merge.test_builder_version_mismatch_forces_full_reextract; docs/architecture/graph-index-system.md and docs/specs/mcp-tool-surface.md. Exact reviewer observations are retained in typed approval events. Temporary JSON/probe files are exploratory aids, not durable delivery fixtures.

Implementation notes: preserve first-representative collapse metadata; pair raw/collapsed mixed-provenance and order controls. Reconcile existing confidence-only test expectations that allow false identity. Correct architecture report prose about SQL-inclusive legacy degrees. Use one bounded structural ownership decision across local and fragment stages, and classify counts once over effective edges. No new scope or unresolved operator decision was introduced.

Limitations: indexed discovery intermittently reported stale/not-ready; direct current MCP outlines/reads and local fixtures supplied validation. No reviewer claims corrected behavior, complete language/report compatibility matrices, MCP transport coverage, a fresh framework-suite receipt or replay of historical Tensorwell measurements. Those remain delivery work.

Rotating performance seat graph-203pu-performance-v1: PASS; mixed call1/SQL read1 report fixture returned legacy count2/chokepoint2 and rejected call-only count1. Strongest cheaper alternative report-only separation/resolved-only filtering leaves incorrect targets and changes preserved rankings. One classification per effective edge with directional tally reuse is preferable; O(E)/O(V) is an estimate, not a benchmark. The four fixed seats explicitly weighed this alternative; no verdict or scope changed.

### Prepare wave — Council synthesis

Independent moderator: wave-council, context graph-203pu-council-v1; requested gpt-6.1-sol/high for evidence synthesis, runtime identity unknown. First synthesis weighed anonymized Seat1–5 before identity reattachment. Roster: reality-checker, qa-reviewer, security-reviewer, performance-reviewer (rotating best-alternative seat), architecture-reviewer; red-team supplied the isolated primer. Additional required approvals: code-reviewer and docs-contract-reviewer.

Final verdict: PASS readiness. seat_agreement: unanimous; max_severity: low (implementation/verification notes only). No blocker, disagreement, challenge round or bounded repair was needed. The four fixed seats explicitly weighed the performance alternative and retained their verdicts.

Strongest challenge confirmed: confidence-only protection leaves false project identity at local and fragment target assignment. Selected structural ownership safeguards and additive counts address both the topology defect and report ambiguity. The cheaper report-only/resolved-filter alternative is weaker because it retains incorrect identity or changes required ranking/count compatibility. Shared ownership classification and once-per-effective-edge directional tallies are implementation guidance, not a new abstraction requirement or measured performance claim.

Moderator independently validated current binding order, scoped callee detection, SQL-inclusive degree code and first-representative collapse semantics. Executed readiness control accepted the complete five-seat census, rejected deliberately omitted Seat5 (invalid census: [1,2,3,4]), and rejected the confidence-guard-prevents-target-assignment claim. The initial supplementary AST assertion had a source-spelling mismatch; corrected complete probe succeeded. Evidence: graph-203pu-council-v1-readiness-probe; actual symbol anchors named in the frozen packet above; exploratory JSON at /private/tmp/graph-203pu-council-v1-readiness-probe.json.

This verdict concerns the current plan and review completeness. It is not delivery approval, corrected graph behavior, a latency benchmark or a suite receipt. Required lane authority remains separate.

### Prepare wave — readiness verdict

PASS on 2026-10-07: wave-owned plan complete; all eight AC priorities required and justified; five required typed readiness approvals plus independent council-readiness are current. Canonical Prepare returned readied=true, transitioned_to_active=false, lint_passed=true, garden_passed=true and no pending readiness lanes. No blocking findings or unresolved operator questions. Product-owner acknowledgment and implementation deferral are recorded above. The wave stays planned/readied; no activation, implementation, commit or closure is authorized here.

### Final tracking publication — readiness currency

The successful initial Prepare was followed by marking the admission/readiness task complete, adding the change Progress Log row and updating its Session Handoff. Those three tracking edits rotated the review-policy receipt. Reconstructed predecessor SHA-256 matches the originally reviewed plan exactly; final plan SHA-256: 10284445fe79d3fef09df474814d21411914d9c3d540cccf8ad37ebc68401dd6. Rationale, Requirements, Scope, ACs and six source hashes are unchanged. Each required lane independently reviewed that exact delta, rejected an artificial contract omission and re-recorded approval under its tracking-v2 context. This is administrative publication currency, not a plan repair or another full review.

Concurrent work changed unrelated indexer/setup code. MCP module reload succeeded (runner current, implementation matches disk), but its setup assessment remains indeterminate with loaded_code_stale/setup_inputs_changed and recommends a full host restart. No setup, dependency install or production rebuild was run here. Current graph source and direct-file contract/diff evidence remain valid; semantic readiness is not claimed.
