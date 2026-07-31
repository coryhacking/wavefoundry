# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-29
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1tvbs review-workflow-ergonomics`
Title: Review Workflow Ergonomics

## Objective

Make executable review state straightforward to operate without weakening its gates: make the
existing `wf_review_wave` response provide one state-derived recommended next action, continue from
the same projection on successful event writes, align the registered schema and recovery guidance,
and prove the guided path reaches the same terminal state with fewer calls and no exploratory
rejected writes or repeated full-lint scans.

## Changes

Change ID: `1ttp6-enh review-workflow-ergonomics`
Change Status: `implemented`

## Participants

- Coordinator: implementation coordinator
- Write-owning roles: implementer, docs-contract implementer, QA fixture owner
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer

Completed At: 2026-07-29

## Wave Summary

Wave `1tvbs` (Review Workflow Ergonomics) delivered one change: Review Workflow Ergonomics.

**Changes delivered:**

- **Review Workflow Ergonomics** (`1ttp6-enh review-workflow-ergonomics`) — 12 ACs completed. Key decisions: Improve the existing review tools instead of introducing a new review protocol or UI.; Measure successful guided transitions and rejected writes, not elapsed time.
## Watchpoints

- Blocking watchpoint: do not introduce a second review-state derivation; consume the current synthesis and approval
  currency authorities delivered by `1tuoc`.
- Behavioral watchpoint: a deterministic recommended reviewer lane is presentation ordering, not a new serialization rule;
  every otherwise-valid lane order must remain legal.
- Compatibility watchpoint: preserve the complete `wf_review_event(event="list")` contract; recovery diagnostics use `wf_review_wave`.
- Verification watchpoint: tool-schema changes require a fresh-client registration test and an explicit reconnect limitation.
- Simplification watchpoint: add no MCP tool, event/list mode, production sensor, or mandatory transition; multi-lane and multi-cycle fixtures must use fewer inspection/recovery calls.
- Performance watchpoint: `wf_review_wave` remains a full-corpus gate and runs once in the guided
  flow; accepted event writes carry post-commit continuations so they do not trigger repeated lint.
- Evidence watchpoint: action templates prefill only state-derived fields and explicitly enumerate caller-owned evidence, judgment, integrity, context, freshness, and independence inputs.
- Authority watchpoint: one structured `review_evidence.py` projection owns current findings, approval-affect relationships, currency, and legal actions; neither `server_impl.py` nor diagnostics may parse presentation prose.
- Product-owner readiness acknowledgment: operator directed creation and preparation of this scoped
  follow-on after reviewing the `1tuoc` delivery outcome and the proposed ergonomics boundary.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| caller-input-vocabulary-is-not-canonically-owned-or-pinned | do_now | no | completed | docs-contract-reviewer, qa-reviewer |
| ergonomics-evaluation-misses-promised-shapes | do_now | no | completed | qa-reviewer |
| ergonomics-evaluation-remains-narrower-than-required-ac9 | do_now | no | completed | qa-reviewer |
| guided-approvals-ignore-phase-prerequisites | do_now | no | completed | architecture-reviewer |
| guided-nonzero-lane-can-recommend-repair-actor | do_now | no | completed | code-reviewer, qa-reviewer, architecture-reviewer |
| guided-recovery-phase-trusts-invalid-caller-fields | do_now | no | completed | code-reviewer |
| guided-repair-start-uses-finding-local-cycle | do_now | no | completed | code-reviewer, architecture-reviewer |
| postbuild-review-rejections-omit-guided-recovery | do_now | no | completed | code-reviewer |
| review-action-cap-bypassed-by-quadratic-alternatives | do_now | no | completed | code-reviewer |
| stale-guided-lane-action-can-resurrect-cleared-lane | do_now | no | completed | qa-reviewer, architecture-reviewer |
| zero-lane-finding-has-no-terminal-guided-route | do_now | no | completed | qa-reviewer |

*Machine review evidence — 163 records; 39 runs; 11 findings; current: do_now 11, maybe_later 0, dont_do_later 0, not_issue 0*
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
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare council — red-team primer — 2026-07-29: PASS after plan revision.** The strongest
  challenge was that the draft simultaneously promised additive compatibility and removal of the
  default historical listing, while also calling one reviewer transition uniquely valid even though
  unresolved lanes may legally clear in any order. The revised plan preserves the default response,
  adds an optional compact action view, and labels its stable lane choice as a recommendation rather
  than a protocol restriction. Strongest alternative considered: a new orchestration tool or batched
  lane clearer; rejected because it adds authority or weakens independent actor ownership.
- **Prepare council — docs-contract-reviewer — 2026-07-29: PASS.** Code-grounded checks confirmed
  that the current list response derives chain state from `current_synthesis_heads` and approval
  currency from `review_status_rows`, currently returns up to 500 historical records, and that the
  registered tool surface owns `approval_phase` and the exact `integrity_checks` fields. Seed 209 is
  the canonical executable-evidence contract. The revised scope names these existing authorities and
  forbids a parallel state model.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-29: PASS** (moderator: wave-council;
  primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat:
  docs-contract-reviewer; strongest-challenge: preserve the default list contract and legal lane
  ordering while making the recovery path compact; strongest-alternative: a new orchestration tool,
  rejected in favor of an additive view derived from existing authorities)
- **Post-Prepare operator refinement — 2026-07-29:** The operator restated the governing objective:
  this third simplification wave must reduce the workflow itself, not add another explanatory layer.
  The plan now makes existing `wf_review_wave` the sole guided status surface, leaves the list tool
  unchanged as forensic history, replaces the proposed production sensor with existing-suite
  fixtures, and adds a no-new-tool/mode/transition acceptance gate. This supersedes the earlier
  checkpoint's reference to an additive compact list view and requires refreshed readiness approval.
- **Post-Prepare council refresh — 2026-07-29: PASS.** Red-team verified the narrower plan removes
  the proposed list mode and production sensor rather than renaming them. Docs-contract review
  confirmed `wf_review_wave` already resolves `ReviewAuthority`, whose validated `records` contain
  the canonical ledger input needed by the existing current-head and approval-currency derivations;
  the list tool can therefore remain unchanged. Strongest challenge: an additive `next_actions`
  field could still become a second authority; resolved by requiring direct derivation from
  `ReviewAuthority.records`, source pins against parallel logic, and unchanged validation gates.
  Strongest alternative: keep the current tools and change prompts only; rejected because it leaves
  rejected-call discovery and hand-assembled arguments in place.
- **Final independent readiness lanes — 2026-07-29: PASS after revision.** Code, architecture, QA,
  and docs-contract reviewers independently rechecked the corrected plan. The revisions define a
  discriminated schema-completable action union, one canonical authority projection, bounded action
  overflow, narrow recovery routing, a frozen public-path baseline, and exact no-new-surface
  censuses. A final architecture challenge found that repeatedly calling `wf_review_wave` would
  rerun full docs-lint; the resolved design keeps it as the sole full-validation entry point and
  carries canonical post-commit continuations only on successful event writes. Baseline and
  candidate now each require exactly one navigation validation plus the unchanged final close
  validation. All four required lanes returned PASS with no remaining blocker.
- **Independent delivery review — 2026-07-29: CHANGES REQUESTED.** Code, QA, architecture, and
  docs-contract lanes reviewed the current implementation without relying on checked ACs or the
  implementer's suite summary. Architecture found that approval actions remain available before
  the mandatory phase run (and the live current-wave call also exposed them under a stale policy
  receipt). Code and QA reproduced an accepted zero-lane finding that cannot reach terminal state
  and loops through a withheld operator approval; code additionally measured 3,950 embedded
  alternatives in a capped 50-of-80 response, found post-build validation errors with no guided
  recovery, and proved invalid caller phase/status heuristics can prescribe the wrong review phase.
  QA mutation-proved the claimed five-shape oracle incomplete: an operator-actor product mutation
  survived the complete baseline/candidate test. Docs-contract passed contingent on those repairs.
  Six typed finding chains are open; delivery and council approval are withheld.
- **Cycle-1 repair implementation — 2026-07-29: COMPLETE, REVERIFICATION PENDING.** All six
  findings were repaired under recorded `repair_start` heads. Guided approval actions now require
  the phase run and fail closed under stale policy authority; zero-lane accepted history has an
  originating-reviewer terminal route; truncation bounds embedded alternatives; all review-event
  rejection paths carry phase-authoritative recovery; and successful continuations use the same
  authoritative phase derivation. The executable evaluation now covers every promised workflow
  shape and includes a public product-seam operator-actor mutation that fails as intended. Focused
  review-evidence and server-tool regressions pass; the finding chains remain pending until their
  owning architecture, code, and QA lanes independently reverify the final tree.
- **Cycle-1 independent reverification — 2026-07-29: PASS.** Architecture cleared the phase-run
  and stale-authority prerequisite finding across readiness, delivery, reprepare, and known-bad
  controls. Code cleared cap, post-build recovery, and phase-authority findings with the original
  public probes. QA cleared the complete evaluation oracle and, after finding two adjacent
  same-actor zero-lane variants, independently executed four accepted-state variants through the
  final distinct-reviewer fallback; every chain reached terminal state. All six typed finding
  heads are completed with their owning lanes cleared. Final canonical verification passed 6,466
  tests across 61 files; docs-lint and `git diff --check` are clean. Delivery approvals remain a
  separate review/signoff step and have not been inferred from repair completion.
- **Cycle-2 specialist-readiness repair — 2026-07-29: PASS.** Re-Prepare exposed one adjacent
  phase-routing case: a specialist's valid readiness approval on an already OPEN wave must remain
  readiness-scoped. The repair accepts that explicit valid phase without trusting invalid specialist
  values or council/operator mismatches, while finding continuations still follow their originating
  review run. The ledger explicitly discloses that this bounded code repair preceded its typed
  `repair_start`; a fresh code reviewer independently re-executed the valid/invalid phase matrix and
  the two-process publication-lock control. The cycle-2 finding head is terminal. The exact final
  code tree passed 6,466 tests across 61 files; delivery approvals and operator signoff remain
  separate and have not been inferred.
- **Cycle-3 final-review repair implementation — 2026-07-29: COMPLETE, REVERIFICATION PENDING.**
  Five recorded repair starts now bound the final-review findings. The writer rejects repair
  actors that remain in their own blocking lanes and rejects stale reverification lane sets that
  would resurrect cleared work. Guided repair cycles now derive from the wave-global repair
  chronology. Exported registries own every guided-action, caller-input, judgment, and evidence
  field name and are cross-pinned to the seed, specification, and registered tool description.
  The frozen evaluation adds a deterministic single-lane/stale-approval/operator twin-tree oracle
  and zero-append controls for actor swap, same-context reverification, stale lane replay, wrong
  cycle, missing repair start, wrong approval phase, and malformed integrity. Focused verification
  passed 178/178; delivery approvals remain withheld until independent code, QA, and docs-contract
  reverification clears the five chains.
- **Cycle-3 independent reverification — 2026-07-29: PASS.** Code independently removed each new
  writer/cycle guard in memory and reproduced the repaired defects; QA re-executed the public
  actor-ownership, stale-action, registry, and frozen-evaluation controls; docs-contract proved an
  added registry field cannot disappear from production or public guidance silently. The owning
  actors cleared one current lane per typed event after re-listing. All five cycle-3 chains are now
  terminal with no unresolved lanes. Focused verification passed 178/178 and docs-lint remains
  clean. A distinct architecture pass then confirmed state-machine ownership, transaction-bound
  monotonicity, and compatibility across all 43 current typed ledgers. All four specialist delivery
  approvals now post-date the repairs; readiness/delivery council and operator decisions remain
  separate and have not been inferred from repair completion.

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 80 | 1,224,171 |
| implement | 131 | 3,176,154 |
| review | 252 | 7,281,699 |
| **Total** | **463** | **11,682,024** |

<!-- wave:context-efficiency-state {"generation":474,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":131,"content_source_credit":3602710,"derived_artifact_credit":0,"direct_net":3176154,"estimated_tokens_saved":3176154,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4921,"response_debit":422996,"source_credit_count":88,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1361},"plan":{"calls":80,"content_source_credit":1318436,"derived_artifact_credit":3493,"direct_net":1224171,"estimated_tokens_saved":1224171,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":7854,"response_debit":101457,"source_credit_count":56,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":11553},"review":{"calls":252,"content_source_credit":8059281,"derived_artifact_credit":3476,"direct_net":7281699,"estimated_tokens_saved":7281699,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":43024,"response_debit":739380,"source_credit_count":282,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":463,"content_source_credit":12980427,"derived_artifact_credit":6969,"direct_net":11682024,"estimated_tokens_saved":11682024,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":55799,"response_debit":1263833,"source_credit_count":426,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":14260},"wave_id":"1tvbs review-workflow-ergonomics"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 16 | 0 | 6 | 9991442 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":6,"estimated_exploration_avoided":9991442,"surfaced_events":16} -->
<!-- wave:exploration-avoided end -->
