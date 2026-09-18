# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-09-17
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xtnr call-edge-target-integrity`
Title: Call Edge Target Integrity

## Objective

A name-guessed `calls` edge never targets a data-only variable or constant node; exact calls to callable-valued constants remain supported, `RECEIVER_RESOLVED` is never stamped on a bind that knew nothing about the receiver, and every `file:line` pair `code_callhierarchy` emits lies inside the named file. Planned now from a consumer field report on the Java agent codebase (framework `1.24.0+ppdh`, builder 51), where 127 call edges bound to fields and locals and 57 of them carried the documented refactor-safety trust tier.

## Changes

Change ID: `1xtnq-bug call-edge-callable-targets-and-callhierarchy-line-integrity`
Change Status: `complete`

Change ID: `1xtns-bug callee-name-from-ast-leaf-for-chained-and-arrow-receivers`
Change Status: `complete`

## Participants

- Coordinator: lifecycle coordinator
- Write-owning roles: implementer, qa-reviewer (selected at Prepare)
- Requested review lanes: performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer

Completed At: 2026-09-14

## Wave Summary

Wave `1xtnr` (Call Edge Target Integrity) delivered two changes: Call Edges Bind Only Callable Targets; Call-Hierarchy Lines Stay Inside Their File and Callee Names Come From the AST Leaf, Not the Callee Text. Notable adjustments during implementation: Call Edges Bind Only Callable Targets; Call-Hierarchy Lines Stay Inside Their File: Readback and Observe: operator authorized resuming shipped work for verification and closure. Luna passed 61 focused tests; independent Astra passed 13 controls and killed receiver/kind-gate mutants. Call/citation seams unchanged from prior approved delivery. Consumer 127/57 follow-up received through operator reports: non-callable targets 127 to zero; false receiver binds removed or explicitly EXTRACTED; correct call_site locations. This is reported evidence, not a fresh consumer run.; Call Edges Bind Only Callable Targets; Call-Hierarchy Lines Stay Inside Their File: Final census: all 15 profiles pass; all nine pure paths and seven opaque/parenthesized-call controls pass. Duplicate inner emissions removed in eight profiles; fixture reads/defines unchanged. Live builder 52 has zero non-callable/malformed targets; callable-target edges 20,223 to 20,301. All 39 removed edges are attributed (one helper call moved into its nested declared function; 38 external hints follow changed candidates in unchanged JS). Consumer 127/57 re-derivation remains pending. Candidate helper benchmark: 2.933 us before, 2.646 us after; this is not whole-build timing.; Call Edges Bind Only Callable Targets; Call-Hierarchy Lines Stay Inside Their File: Independent checkpoint found a valid Java colon-switch scope regression: a local declared in an earlier case group remains visible in later groups, but lookup escaped to an outer field. Thought: model the shared colon-switch scope while retaining separate arrow/block scopes; add the javac-verified fixture.

**Changes delivered:**

- **Call Edges Bind Only Callable Targets; Call-Hierarchy Lines Stay Inside Their File** (`1xtnq-bug call-edge-callable-targets-and-callhierarchy-line-integrity`) — 9 ACs completed. Key decisions: Repair the fallback (no receiver candidates, kind gate, promotion gate) and fill the Java scope-walk gap; do not extend receiver typing to chained or subscript receivers.; Fix node identity (callable-wins) before gating on kind, and make the finalize invariant count rather than drop.
- **Callee Names Come From the AST Leaf, Not the Callee Text** (`1xtns-bug callee-name-from-ast-leaf-for-chained-and-arrow-receivers`) — 7 ACs completed. Key decisions: Derive the callee from the member-name field only when a non-identifier segment intervenes; keep the text path for pure identifier paths.; Share the `52` builder bump with `1xtnq` rather than bump separately.
## Watchpoints

- Single-OPEN guard: `1xq4f dashboard-lifecycle-integrity` is closed; the OPEN slot is available.
- Run the before-side census (Requirement 7) before the first code edit; both populations are re-derived from SQL predicates, never copied from the plan.
- The promotion gate lowers `RECEIVER_RESOLVED` counts on consumer graphs that wave `1p7dg` lifted; the per-language delta is reported, not hidden.
- `code_callhierarchy` outgoing entries change shape (`line` becomes the callee definition line; call site moves to `call_site`); tool-surface spec and CHANGELOG must say so.
- Any edit under `.wavefoundry/framework/` invalidates the test receipt; run the suite last before close.
- Ordering inside the wave: `1xtnq` (receiver rule, kind gate, promotion gate, finalize invariant) lands before `1xtns` (callee-leaf derivation, invariant extension); both edit `_ts_relation_candidates`, and `1xtns` depends on the `1xtnq` invariant and confidence gate.
- One builder bump (`51` to `52`) covers both changes; do not bump twice.
- `performance-reviewer` is requested by judgment: `_ts_relation_candidates` and `add_node` run per call node and per definition on the extraction hot path, and the callable-wins collision check adds work to every definition.

## Review Checkpoints

- **2026-09-12 delivery approved:** all five required specialist lanes and the receipt-selected targeted council approve. CODE-DEL-1/QA-DEL-1 was repaired with a permanent enhanced-for iterable regression test; ARCH-DEL-1 with the explicit standalone census reader exception. Independent reverification cleared both chains. Final suite: 8,940 tests, 12 documented skips; reports and receipt in `delivery-review.json`. Consumer census and native platform execution remain pending. Local test packaging authorized; wave closure and commit are not.

- **2026-09-12 implementation complete:** all ACs and tasks checked with evidence in `implementation-evidence.json`. Final suite 8,939 tests with 12 documented skips; docs validation clean; builder-52 live census has zero non-callable/malformed targets and no unexplained callable-edge losses. Subsequent delivery review is recorded below.

- **2026-09-12 optional full plan review: changes requested.** Six findings remain before implementation: cross-file confidence re-promotion, Java lexical-scope visibility, unsafe read-only SQLite URI construction, prior-constant membership after callable replacement, a deduplicated census baseline, and caller-path context attribution. Five executed counterexample groups and source inspection are retained in `plan-review.json`. This is Review Plan, not a typed lifecycle signoff; no implementation or activation was performed. Revise the identified requirements and tests, then re-Prepare the changed boundary.

- **Prepare-phase Wave Council [prepare-council] — 2026-09-12: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, qa-reviewer, reality-checker, security-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the kind gate as first planned would delete true method-call edges because `add_node` is first-wins and a Java field and method of one name mint a single `variable` node; strongest-alternative: a kind-aware `symbol_lookup` built from `node_map` at index time, which loses only because the same table serves `reads` binds that must reach `variable` nodes)
- `seat_agreement_aggregate`: seat_agreement `unanimous` (all six seats independently reached approve-with-repairs after the primer's blocking finding was repaired; security-reviewer ran as the alternative seat under the first receipt, and docs-contract-reviewer as the rotating seat the repaired receipt named); max_severity `medium` (the surviving Phase 2 findings were major-class plan-precision gaps, none blocking; no challenge round triggered).
- Red-team primer summary: adversarial, constructive and simplicity stances; RT-1 (blocking) reproduced with a built probe and repaired by callable-wins node identity before any kind gate; RT-2 to RT-7 repaired in the same pass. Every Phase 2 seat confirmed RT-1 in code and judged the repair sound.
- Phase 2 findings, all repaired in the change docs before readiness: architecture AR-1 to AR-6 (read kinds from the existing `ctx["node_map"]`, `indexer.py` merge line and pinned regex, `_context_paths` credits outgoing rows through `call_site.snippet`, subscript shapes owned wholly by `1xtns`, finalize-chain doc paragraphs, `reads` drop direction); qa QA-1 to QA-5 (Scala `val` minted `function` so it joins `_TS_VARIABLE_DEFINITION_TYPES`, the swallowed-method split becomes an extraction-time `callable_wins_collisions` count, the AC-5 mutation injects an edge before finalize, `merge_stats` key, builder-51 candidate literals pinned through a `_call_candidates` helper); reality-checker RC-1 to RC-9 (self-host holds zero `variable` nodes so that half of the census is vacuous here, fifteen profiles, `1p7dg` figures are 2026-06 spike counts, seed-180 sentence corrected, consumer re-derivation recorded as received or pending, CHANGELOG says present since 1.8.1); security SR-3, SR-6, SR-7, SR-8 (read-only root-confined helper, no parallel kind map, refused extraction binds emit nothing, the receiverless predicate named); docs-contract DC-1 to DC-5 (the lint-bound builder-version claim in `docs/RELIABILITY.md`, the trust-filter contract's real home in `guru.md` and seed 211, the no-seed-edit decision recorded against seed 211, the two finalize counters with distinct dispositions, stale scope wording). Prepare lanes outside the council, both approve-with-repairs, all applied: code-reviewer CR-2 to CR-6 and CR-8 (losing constant registration, `node_map` keyword threaded to all three resolver call sites and gated to `calls`, id-keyed extraction gate, one `_ts_call_has_receiver` helper covering Swift/Kotlin positional callees, member-name field primary with the recursive walker repaired as fallback, `assertRegex` pin); performance-reviewer PR-1 to PR-8 (no hot-path regression measured; census folded into the existing final-map loop; collision kind pairs; structural pure-path test). No security finding; confinement of `_scan_all_call_sites_in_file` is unchanged and its paths come from indexer-minted node records, not caller input.
- Strongest points of agreement: identity before kind; count-not-drop for the non-callable finalize invariant (the `1xtns` malformed-external predicate drops, deliberately); the Python `CallCollector` and legacy JS regex binds stay ungated because they are exact, not guesses.
- Material disagreements: none. Unresolved risk carried into implementation: the consumer's 127/57 split cannot be re-derived from their `index.sqlite`; it needs a builder-52 rebuild on their side, recorded under AC-7.
- improvements_recommended (non-gating): route `_scan_all_call_sites_in_file` through `_resolve_repo_path` as defence in depth; consider the kind-aware `symbol_lookup` as a follow-up once `reads` binds get their own table; bind the two `graph-index-system.md` builder-version mirrors to `docs_constants_validators._claims()` in a follow-up, since their current drift shows unbound mirrors do not hold.
- AC priority: recorded on both change docs (every AC required). Product-owner acknowledgment: not applicable (framework tooling, no product UX).
- Readiness verdict: READY. That readiness preceded the full plan review; refresh readiness for its accepted corrections.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ARCH-DEL-1 | do_now | no | completed | architecture-reviewer |
| CODE-DEL-1 | do_now | no | completed | code-reviewer, qa-reviewer |

*Machine review state — 2 findings; current: do_now 2, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| performance-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated context avoided uses whole eligible text-file, workflow-prompt and derived-artifact credits, minus recorded request and response tokens. This baseline does not prove what an agent otherwise would have read or spent. Any quality-equivalent paired-evaluation residual is recorded separately in the checkpoint state and included in the total.

| Stage | Tool calls | Estimated context avoided |
| --- | ---: | ---: |
| plan | 153 | 4,255,602 |
| implement | 280 | 5,755,695 |
| review | 192 | 117,996,725 |
| **Total** | **625** | **128,008,022** |

<!-- wave:context-efficiency-state {"generation":585,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":280,"content_source_credit":6589836,"derived_artifact_credit":275,"direct_net":5755695,"estimated_tokens_saved":5755695,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9750,"response_debit":827633,"source_credit_count":66,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2967},"plan":{"calls":153,"content_source_credit":4905280,"derived_artifact_credit":5066,"direct_net":4255602,"estimated_tokens_saved":4255602,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16127,"response_debit":646503,"source_credit_count":301,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7886},"review":{"calls":192,"content_source_credit":118498937,"derived_artifact_credit":4297,"direct_net":117996725,"estimated_tokens_saved":117996725,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17076,"response_debit":491322,"source_credit_count":102,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1889}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":625,"content_source_credit":129994053,"derived_artifact_credit":9638,"direct_net":128008022,"estimated_tokens_saved":128008022,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":42953,"response_debit":1965458,"source_credit_count":469,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":12742},"wave_id":"1xtnr call-edge-target-integrity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 29 | 0 | 16 | 16,994,362 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":16,"estimated_exploration_avoided":16994362,"surfaced_events":29} -->
<!-- wave:exploration-avoided end -->
## Closure Reconciliation

- Both admitted changes complete: 1xtnq AC-1–9 and 1xtns AC-1–7, all tasks checked; no intentionally deferred ACs.
- All five required specialist approvals and current typed readiness/delivery council remain valid; independent closure delta confirms unchanged call/citation boundaries and repaired tests.
- Docs-contract review performed: graph architecture and MCP spec agree with caller/callee locations and confidence semantics; release notes describe end-user value.
- Chronology reconciled to complete; closure tool owns final wave status/date. Historical no-close instructions are superseded by the current operator authorization.
- Consumer census follow-up received as operator-reported evidence (127 non-callable targets to zero, named false binds removed/demoted, corrected locations); no independent consumer rerun claimed. Native Windows/Linux qualification remains unproven.
- Retrospective: preserve paired positive controls so precision repairs do not delete valid callables; maintain the receiver confidence ceiling through incremental resolution. Prior repair evidence and canonical docs already retain these lessons.
- Memory proposal returned zero new candidates and retained one prior disposition; no new promotion needed.
- Handoff will be idle after closure, retaining pending decisions and the separate staged host-neutral orchestration change.
- No silent unchecked or deferred AC/task remains. Existing council follow-up suggestions remain outside this delivered scope.
- Full framework receipt remains current: 9,008 tests, no framework source edits in this closure pass.
- Operator approved sequential reopening, review and closure of both paused waves on 2026-09-14; no commit or new package requested.
