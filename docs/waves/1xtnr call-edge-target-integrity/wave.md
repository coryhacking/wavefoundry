# Wave Record

Owner: Engineering
Status: paused
Last verified: 2026-09-12
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1xtnr call-edge-target-integrity`
Title: Call Edge Target Integrity

## Objective

A name-guessed `calls` edge never targets a data-only variable or constant node; exact calls to callable-valued constants remain supported, `RECEIVER_RESOLVED` is never stamped on a bind that knew nothing about the receiver, and every `file:line` pair `code_callhierarchy` emits lies inside the named file. Planned now from a consumer field report on the Java agent codebase (framework `1.24.0+ppdh`, builder 51), where 127 call edges bound to fields and locals and 57 of them carried the documented refactor-safety trust tier.

## Changes

Change ID: `1xtnq-bug call-edge-callable-targets-and-callhierarchy-line-integrity`
Change Status: `implemented`

Change ID: `1xtns-bug callee-name-from-ast-leaf-for-chained-and-arrow-receivers`
Change Status: `implemented`

## Participants

- Coordinator: lifecycle coordinator
- Write-owning roles: implementer, qa-reviewer (selected at Prepare)
- Requested review lanes: performance-reviewer
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, performance-reviewer

## Wave Summary

Repair the language-generic call fallback in the graph builder (receiver expressions are no longer callee candidates, a named callable-target predicate at both binding choke points, a finalize invariant, and a promotion gate), fill the Java scope-walk gap for enhanced-for, catch, resource and typed-lambda receivers, give `code_callhierarchy` entries a nested `call_site` so file and line always agree, and derive callee names from the AST member leaf so chained, arrow, optional-chain and non-null receivers no longer lose the outer call or mint garbage external targets. Two changes, one shared bump of the graph builder to version 52.

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
| operator-signoff | withheld | repaired findings require fresh approval: CODE-DEL-1, ARCH-DEL-1 | record a fresh independent approval for operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

## Context Efficiency

<!-- wave:context-efficiency begin -->

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 153 | 4,255,602 |
| implement | 280 | 5,755,695 |
| review | 125 | 3,383,951 |
| **Total** | **558** | **13,395,248** |

<!-- wave:context-efficiency-state {"generation":514,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":280,"content_source_credit":6589836,"derived_artifact_credit":275,"direct_net":5755695,"estimated_tokens_saved":5755695,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9750,"response_debit":827633,"source_credit_count":66,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":2967},"plan":{"calls":153,"content_source_credit":4905280,"derived_artifact_credit":5066,"direct_net":4255602,"estimated_tokens_saved":4255602,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16127,"response_debit":646503,"source_credit_count":301,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7886},"review":{"calls":125,"content_source_credit":3673004,"derived_artifact_credit":2716,"direct_net":3383951,"estimated_tokens_saved":3383951,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":13461,"response_debit":278308,"source_credit_count":71,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":558,"content_source_credit":15168120,"derived_artifact_credit":8057,"direct_net":13395248,"estimated_tokens_saved":13395248,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":39338,"response_debit":1752444,"source_credit_count":438,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10853},"wave_id":"1xtnr call-edge-target-integrity"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 25 | 0 | 16 | 14,367,734 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":16,"estimated_exploration_avoided":14367734,"surfaced_events":25} -->
<!-- wave:exploration-avoided end -->
