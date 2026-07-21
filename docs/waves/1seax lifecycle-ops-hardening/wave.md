# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-21
review-evidence-source: events.jsonl

wave-id: `1seax lifecycle-ops-hardening`
Title: Lifecycle Ops Hardening

## Objective

Land the right-sized remainder of the 2026-07-12 external code review: (1) lifecycle-mutation concurrency and interruption safety — an advisory per-root mutation lock, a write-ordering audit guaranteeing forward-recoverability, and idempotent-retry fixtures — deliberately NOT the review's proposed transaction-journal/rollback layer, which was assessed as disproportionate for git-versioned markdown with zero field incidents; (2) selective subprocess bounds (timeouts + bounded capture) for the short MCP-reachable ops (gardener, surface render), with upgrade/setup explicitly exempt as long-running-by-design; (3) the materially stale operational contracts (RELIABILITY.md, performance-budget.md) rewritten from measured evidence, plus a declarative docs-vs-code-constants lint check so documented facts fail the docs gate when they drift instead of waiting for the next external review to notice.

## Changes

Change ID: `1seat-debt lifecycle-mutation-lock-and-subprocess-bounds`
Change Status: `implemented`

Change ID: `1seau-doc ops-docs-refresh-and-constants-lint`
Change Status: `implemented`

Change ID: `1t3zv-debt contention-safe-performance-test-budgets`
Change Status: `implemented`

Completed At: 2026-07-21

## Wave Summary

Wave `1seax` (Lifecycle Ops Hardening) delivered 3 changes: Lifecycle Mutation Lock, Idempotent-Retry Guarantees, and Selective Subprocess Bounds, Operational Docs Refresh + Docs-vs-Code Constants Lint, and Contention-Safe Performance-Test Budgets. Notable adjustments during implementation: Lifecycle Mutation Lock, Idempotent-Retry Guarantees, and Selective Subprocess Bounds: Plan-review revision (external, validated) + council amendment: hand-written lock scope replaced by a required writer CENSUS (omissions caught: `wave_set_handoff` ~6492, gate tools ~6385); two validator-hardening items adopted into scope — close-gate signoff-token parsing (verified: only `<...>` placeholders are skipped at ~5151, so this session's unbracketed phrasing pre-approved closure on three waves before repair) and prepare seat-alignment validation (the structural parser accepted councils missing the brief's rotating seat).; Lifecycle Mutation Lock, Idempotent-Retry Guarantees, and Selective Subprocess Bounds: Pre-implementation review rebaselined AC-5: the current parser already fail-closes on exact final state lines and rejects conditional/future phrasing and placeholders. Scope is regression protection, not a duplicate parser rewrite.; Contention-Safe Performance-Test Budgets: Operator independent review (P2): the slowdown guard only exercised the helper with a synthetic 1s threshold. Repaired: PERF_BUDGETS is now the single registered table both tests consume (inline numbers removed and pinned absent); the guard injects 1.1x past each REAL budget (the 10s line-scan included), and a permissiveness invariant bounds every budget to 3x-50x of its isolated reference so inflation fails the guard itself

**Changes delivered:**

- **Lifecycle Mutation Lock, Idempotent-Retry Guarantees, and Selective Subprocess Bounds** (`1seat-debt lifecycle-mutation-lock-and-subprocess-bounds`) — 6 ACs completed. Key decisions: Advisory lock + forward-recoverable ordering + retry tests — NOT a transaction journal with rollback.; Upgrade/setup/index spawns exempt from deadlines.
- **Operational Docs Refresh + Docs-vs-Code Constants Lint** (`1seau-doc ops-docs-refresh-and-constants-lint`) — 5 ACs completed. Key decisions: Constants lint is declarative (pattern → constant mapping), scoped initially to the two refreshed docs + spec content values.
- **Contention-Safe Performance-Test Budgets** (`1t3zv-debt contention-safe-performance-test-budgets`) — 5 ACs completed. Key decisions: Characterize before mitigation; then choose measured headroom, a bounded retry/warm-up, or per-module serialization.
## Delivery Sequence

Implement in this order to protect release-critical operation first while
preserving the wave's deliberately narrow boundary:

1. `1seat`: lifecycle-mutation lock, forward-recoverability audit/retry
   fixtures, and prepare-council seat alignment.
2. `1seau`: canonical public-contract constants, then the narrow docs-lint
   rules that consume them (including admitted-change and signoff wording
   integrity).
3. `1seau`: evidence-based refresh of `RELIABILITY.md` and the performance
   budget after the constants contract is settled.
4. `1seat`: gardener and surface-render subprocess bounds, with generous,
   configuration-tunable limits that remain safe on slower computers.

All four steps are release scope. Existing subprocess isolation remains in
place; the new bounds must provide a clear timeout diagnostic and recovery
path, while upgrade/setup/index builds remain exempt because they are
legitimately long-running. Do not expand this sequence into a transaction
journal or blanket subprocess deadlines.

## Journal Watchpoints

- Watchpoint (right-sizing holds): the rejected alternatives (transaction journal, blanket subprocess deadlines, correlation IDs) are recorded with rationale in the change docs — reviewers should challenge the fixes' sufficiency, not silently re-expand toward the rejected machinery.
- Watchpoint (exemption pins): upgrade/setup/index-build spawns must be PINNED as timeout-exempt — a deadline there converts slow-network success into failure.
- Watchpoint (happy-path invariance): the mutation lock must be invisible uncontended; existing lifecycle tests pass unmodified except for additive envelope fields.
- Watchpoint (measured, not aspirational): the performance-budget rewrite cites the recorded measurements (1sc7c hook costs, heal timing, FTS rebuild duration) — no unquantified claims.

## Prepare Review Evidence

Delta readiness pass, 2026-07-20 (five weeks after the original 2026-07-12 council PASS; late-admitted `1t3zv` joins):

- reality-checker: aged claims re-verified against the CURRENT tree via MCP retrieval — `_move_change_doc` (server_impl.py:6211) still precedes the wave.md write in admission; `_lane_has_signoff_in_evidence` (5629) fail-closed with `test_full_attack_matrix` present (test_server_tools.py:22671); `wf_set_handoff_response` (7137) confirms the handoff writer; the two-truths constants gap HOLDS (`CONTENT_CHOICES` at indexer.py:156 is docs/code/all/graph while the public handler also accepts map/fts); both target docs remain stale at their cores (performance-budget.md:32 "None currently; all operations are local file I/O", plus a "Future: MCP Server" table with dot-form tool names; RELIABILITY.md:37 "Future MCP code index ... TBD in server design") though newer sections (1sed7 structural budgets) were appended around them — the refresh must integrate, not append.
- docs-contract-reviewer: one drift in 1seau's Rationale — the cited declarative-check exemplar `check_deprecated_role_references` no longer exists; the current `wave_lint_lib/*_validators.py` `check_*` family is the pattern to follow. Noted, no doc rewrite needed (the pattern intent is unambiguous).
- red-team (primer, standard): for `1t3zv`, the strongest challenge is threshold inflation masking real regressions; answered by the change's own AC-3 (a deliberately injected meaningful slowdown must still fail) and the characterize-before-mitigate serialization point. For the aged pair, the original council's right-sizing challenges stand unchanged.
- qa-reviewer: `1t3zv`'s two flake classes are same-day session-evidenced (drift-detection 200ms budget: 3 failures across today's runs, isolated 120ms; line-scan 3000ms budget: 3,215ms contended, 240ms isolated).
- architecture-reviewer / security-reviewer: no findings; the mutation lock joins the documented locking inventory beside the index-build lock and the new 1t72b exclusion discipline (check the other's lock only after acquiring your own; never wait while holding — the TOCTOU/phantom-hold lessons apply to the new lock's design directly).

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| contract-vocabularies-not-consumed-by-handlers | do_now | no | completed | — |
| fallback-reason-census-still-incomplete | do_now | no | completed | — |
| public-contract-missing-from-reload-eviction | do_now | no | completed | — |
| slowdown-guard-does-not-exercise-real-budgets | do_now | no | completed | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 44 records; 15 runs; 4 findings; current: do_now 4, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Delivery-phase Wave Council [wave-council-delivery] — 2026-07-20: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, code-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the right-sizing verdict again — does the advisory lock plus forward-recoverability actually hold under a real second process? Answered by execution: the contended-path fixture spawns a REAL second process (fcntl record locks cannot conflict intra-process, the 1t72b lesson applied at design time) and observes the structured busy response; the ordering audit found and FIXED the one non-forward-recoverable seam (close's handoff heal now converges on retry, fixture-pinned); strongest-alternative: wiring the lock per-response-function — rejected for the registration-layer chokepoint that covers the whole census column. Per-seat: code-reviewer verified the census against the live tool registry and the two consumers of the canonical public-contract module; qa-reviewer confirmed every fixture class runs (contention, three interruption seams, seat alignment, subprocess timeout/truncation/config/exemption, drift-seeded lint, slowdown guard) with suite 6,081/6,081 on the final tree; reality-checker confirmed the live proofs — the new lint rules caught a real Wave: TBD defect on an admitted 1p6lp doc on first run, the refreshed docs pass their own constants lint, both rebudgeted perf tests re-observed under live contention (1,805 ms line-scan during a concurrent run, inside the new budget), and this wave's own implement stage shows 3 census retrieval calls with the posture sensor correctly SILENT (the 1t67p loop steering the work that built on it); security-reviewer: no new trust boundaries, the lock is advisory and repo-contained; red-team: pressed lock-starvation (a crashed holder) — kernel-released OS locks, the proven pattern, no PID files; docs-contract-reviewer: both rewritten docs are evidence-cited with lint-bound claims, the policy doc names its recorded measurements)


- **Prepare-phase Wave Council [prepare-council] — 2026-07-20: PASS** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, qa-reviewer, architecture-reviewer, security-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: five-week claim aging plus the late 1t3zv admission — resolved by MCP-grounded re-verification of every load-bearing claim against the current tree (orderings, parser, constants gap, doc staleness all reconfirmed; one stale pattern-name noted); strongest-alternative: re-run the full original council from scratch — rejected: the 2026-07-12 pass's reasoning stands, only its evidence needed refreshing)
- **Prepare-phase Wave Council [prepare-council] — 2026-07-12: PASS** (moderator: wave-council; primer-depth: standard; seats: reality-checker, red-team, qa-reviewer, architecture-reviewer; rotating-seat: red-team emphasis; strongest-challenge: the right-sizing itself — is an advisory lock plus retry fixtures ENOUGH, or does rejecting the review's transaction layer under-protect as multi-agent use grows? Resolved on evidence: the failure base rate is zero across the framework's entire wave history, every mutation's artifacts are git-versioned human-readable markdown (git IS the recovery journal), forward-recoverability converts any interruption into \"re-run the same call\", and the lock closes the one genuinely growing risk (concurrent sessions interleaving writes) using the OS-lock pattern the index-build lock has proven in the field — the journal/rollback machinery would add failure modes to defend against failures git already makes visible; strongest-alternative: the review's full transaction layer — kept ON RECORD in the change doc's Decision Log as the escalation path if multi-agent incidents ever materialize)
- Council seat notes: reality-checker — orderings verified against `2952df8f` (`_move_change_doc` ~6048 before `wave_md.write_text` ~6067; close's wave.md-then-handoff two-step); the zero-incident base rate is drawn from the full `docs/waves/` history; the stale-docs claims verified by direct read (performance-budget's \"None currently; all operations are local file I/O with small data volumes\" against a system with GPU embedding sessions and 100MB indexes); the measured inputs for the rewrite exist (1sc7c hook costs, 38s heal, 3.4s FTS rebuild). red-team — pressed lock-leak-on-crash (kernel releases OS locks on exit — the proven index-lock pattern, not a PID file); pressed the timeout exemption inversion (an exempt op that hangs forever): upgrade/setup already write persistent progress logs and the operator-facing status tools report liveness — observability, not deadlines, is the correct control there; pressed constants-lint brittleness (a renamed constant breaking lint): the check fails loudly naming the missing constant — self-announcing drift is the feature, not a bug. qa-reviewer — interruption fixtures are enumerated per mutation (admission, removal, close) at the specific inter-step seams, plus the contended-lock fixture and the drift-seeded lint fixture; happy-path invariance is an explicit AC. architecture-reviewer — the mutation lock joins the documented locking inventory (cross-cutting-concerns) beside the index-build and table locks with distinct scope; the constants-lint reuses the declarative check pattern (`check_deprecated_role_references` shape) rather than inventing a framework; the docs rewrite is evidence-cited by requirement. seat_agreement: unanimous.
- AC priority: confirmed at prepare as proposed (`1seat` AC-3 important, all else required). Product-owner acknowledgment: operator-directed 2026-07-12 ("build these waves now"); opportunistic scheduling.

- **Prepare-council amendment [prepare-council-amendment] — 2026-07-12:** external plan review caught that the recorded council lacked the brief's required rotating seat (`docs-contract-reviewer`); the seat was run post-hoc. **docs-contract-reviewer** — `1seau`'s deliverables ARE documentation contracts (RELIABILITY, performance-budget) with the evidence-citation requirement pinned; `1seat` names the cross-cutting-concerns locking-inventory entry. Seat findings (folded into scope by this amendment): the plan-review round exposed three VALIDATOR gaps that belong in this wave — (1) docs-lint must reject unbracketed pre-approval signoff phrasing (the placeholder convention is load-bearing for the close gate); (2) docs-lint must reject `Wave: TBD`/mismatched wave references on admitted change docs; (3) `wave_prepare` should compare recorded council seats against the generated brief instead of validating structure only. (1)+(2) added to `1seau`; (3) plus close-gate signoff-token hardening added to `1seat`. Verdict unchanged: READY.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- wave-council-readiness: approved 2026-07-12 — prepare council synthesis verdict READY: the deliberate severity downgrade from the review's P0 is evidence-based and recorded with the escalation path preserved; fixtures target the known seams instead of a fault-injection framework; the docs half is measurement-cited with a drift-preventing lint. Seats unanimous; full synthesis in Review Checkpoints.
- operator-signoff: approved 2026-07-21 — operator instructed "close the wave" after the fourth repair's independent reverification and the superseding council delivery approval.

## Dependencies

- No external wave dependencies. Opportunistic scheduling after `1seav`/`1seaw`; the docs change can land any time.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 25 | 1,990,878 |
| implement | 3 | 375,426 |
| review | 62 | 1,075,613 |
| **Total** | **90** | **3,441,917** |

<!-- wave:context-efficiency-state {"generation":88,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":3,"content_source_credit":377430,"derived_artifact_credit":157,"direct_net":375426,"estimated_tokens_saved":375426,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":672,"response_debit":1489,"source_credit_count":6,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":25,"content_source_credit":2017498,"derived_artifact_credit":0,"direct_net":1990878,"estimated_tokens_saved":1990878,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":643,"response_debit":31824,"source_credit_count":18,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5847},"review":{"calls":62,"content_source_credit":1148845,"derived_artifact_credit":1173,"direct_net":1075613,"estimated_tokens_saved":1075613,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":14700,"response_debit":60740,"source_credit_count":58,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1035}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":90,"content_source_credit":3543773,"derived_artifact_credit":1330,"direct_net":3441917,"estimated_tokens_saved":3441917,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":16015,"response_debit":94053,"source_credit_count":82,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6882},"wave_id":"1seax lifecycle-ops-hardening"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
