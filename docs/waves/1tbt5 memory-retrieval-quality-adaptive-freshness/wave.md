# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-25
review-evidence-source: events.jsonl

wave-id: `1tbt5 memory-retrieval-quality-adaptive-freshness`
Title: Memory Retrieval Quality Adaptive Freshness

## Objective

Improve memory retrieval with measured, kind-aware freshness while preserving
trust, status, evidence, and archive boundaries. Reconsider lexical+semantic
fusion only through the expanded evaluation gate, leaving it default-off unless
the evidence supports adoption.

## Changes

Change ID: `1t7ab-enh adaptive-memory-freshness-and-retrieval`
Change Status: `implemented`

Change ID: `1sufn-enh measured-lexical-semantic-memory-fusion`
Change Status: `implemented`

Change ID: `1tgkx-bug memory-propose-harness-token-target-misattribution`
Change Status: `implemented`

Completed At: 2026-07-24

## Wave Summary

Wave `1tbt5` (Memory Retrieval Quality Adaptive Freshness) delivered 3 changes: Adaptive memory freshness and retrieval, Measured lexical+semantic memory fusion (relevance separated from policy), and Memory-Propose Harness-Token Target Misattribution. Notable adjustments during implementation: Adaptive memory freshness and retrieval: Implemented adaptive cadence and policy partitions over the existing one-batch history read; expanded the hermetic corpus to 11 invariants and froze an aggregate-only 12-record live sample.; Measured lexical+semantic memory fusion (relevance separated from policy): Readiness review reconciled the plan to the shipped `1svuj` tie-break, the queryless brief path, in-process lexical ranking, and the expanded `1t7ab` gate.; Measured lexical+semantic memory fusion (relevance separated from policy): Evaluation-only BM25/RRF candidate completed with deterministic controls and a registered 1,000-record budget. The gate rejected adoption: candidate hermetic MRR `0.8485` vs baseline `1.0000`, and the frozen curated semantic pass was unavailable. No product fusion branch or flag was added.

**Changes delivered:**

- **Adaptive memory freshness and retrieval** (`1t7ab-enh adaptive-memory-freshness-and-retrieval`) — 6 ACs completed. Key decisions: Apply freshness as a kind-aware policy within comparable records.; Expand evaluation before altering ranking.
- **Measured lexical+semantic memory fusion (relevance separated from policy)** (`1sufn-enh measured-lexical-semantic-memory-fusion`) — 4 ACs completed. Key decisions: Fuse only lexical+semantic relevance; policy as constraints; Reranker out of scope
- **Memory-Propose Harness-Token Target Misattribution** (`1tgkx-bug memory-propose-harness-token-target-misattribution`) — 4 ACs completed. Key decisions: Filter the canonical `run_tests.py` entry token plus implementation-file tokens named by optional workflow-config `test_runner`; do not add cross-field suppression or test-module inference.; Preserve a promoted validation verdict when ordinary lifecycle supersession later retires the record; require the successor link.
## Watchpoints

- **Watchpoint:** Keep relevance scoring separate from policy constraints; recency must not
  demote durable decisions or operator preferences.
- **Watchpoint:** Evaluate and pin archive-pointer, archive-history, degraded-index, target
  churn, and old-authoritative cases before changing default ranking behavior.
- **Watchpoint:** Treat `1sufn` as adoption-gated: a measured default-off result is acceptable
  when fusion does not improve the representative corpus.
- **Watchpoint:** Freeze the curated sample before candidate scoring; baseline,
  freshness candidates, fusion variants, and single-stream controls use the
  same content fingerprint.
- **Watchpoint:** Evaluate fusion before product wiring. A failed or incomplete
  gate leaves the shipped response path unchanged and adds no dormant flag.
- **Watchpoint:** Preserve the one-batch freshness read and make lexical scoring
  a single in-memory traversal with a contention-aware registered budget.
- **Watchpoint:** Keep `memory_brief` queryless and outside relevance fusion.
- **Watchpoint:** Exclude only canonical/configured test-runner entry tokens
  from repaired-surface targets; do not infer product targets from test names
  or suppress every token repeated in a verification command.

## Participants

- wave-coordinator
- implementer
- architecture-reviewer
- security-reviewer
- qa-reviewer
- reality-checker
- performance-reviewer
- docs-contract-reviewer

## Prepare Review Evidence

- **red-team — no blocking finding after plan repair:** the strongest failure
  mode was tuning the curated corpus after seeing candidate results or landing
  an optional failed fusion experiment as dormant product code. The plan now
  freezes the sample fingerprint before scoring and gates product wiring on a
  strict improvement result.
- **architecture-reviewer — no blocking finding:** freshness comparability and
  relevance calculations are shared pure memory-policy helpers; response
  orchestration retains prefilters and envelope ownership. This prevents the
  eval runner and live path from developing parallel formulas.
- **security-reviewer — no blocking finding:** the real-corpus pass persists
  only aggregate metrics, kind/status counts, and a content fingerprint. It
  records no bodies, summaries, or record identifiers, adds no index, and does
  not pass query text into shared FTS.
- **qa-reviewer — no blocking finding:** the gate is falsifiable and uses the
  same frozen sample for baseline, candidates, and lexical-only/semantic-only
  controls. Required cases cover archive/history boundaries, protected kinds,
  missing or sparse commit history, multi-target cadence, degradation, and
  queryless brief invariance.
- **reality-checker — no blocking finding:** the shipped `1svuj` order is
  already correct, so fusion is optional. If it ties, regresses, or cannot run
  the curated pass, the valid outcome is measured evidence plus no product
  wiring; adaptive freshness remains independently valuable.
- **performance-reviewer — no blocking finding:** adaptive cadence reuses the
  existing single batched timestamp read, and lexical scoring is constrained to
  one traversal of already-loaded surfaced records with no store/FTS calls and
  a registered representative-corpus budget carrying contention headroom.
- **docs-contract-reviewer — no blocking finding:** the affected reference,
  architecture, spec, and memory README surfaces are enumerated; they must
  describe the shipped gate result rather than implying fusion is always
  enabled, and must preserve the distinction between search relevance and
  queryless briefing.

## Review Checkpoints

- **Product-owner acknowledgment — 2026-07-23:** the operator explicitly
  requested review and preparation of wave `1tbt5`, including its user-visible
  memory retrieval and freshness behavior.
- **Pre-implementation review — passed:** the plans were reconciled to the
  shipped `1svuj` tie-break, current decay and batching seams, queryless
  briefing, archive/history boundaries, and the existing evaluation harness.
  Review repairs made comparability, fallback, privacy, corpus freezing,
  performance, and gate-before-wiring behavior executable.
- pre-implementation-review: passed (2026-07-23) — pre-mortem covered five
  likely churn sources: stale shipped-order assumptions, curated-corpus
  overfitting, accidental per-target I/O, over-broad harness-token filtering,
  and completion bookkeeping drift. The packet resolves them through the
  `1svuj` baseline, a pre-frozen fingerprint, one batched history read,
  canonical/configured runner-only exclusion, and real-time AC/task updates.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-23: PASS** (moderator: wave-council; primer-depth: full; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, performance-reviewer, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: prevent evaluation overfitting and dormant product code when optional fusion fails its gate; strongest-alternative: ship adaptive freshness alone and leave the existing semantic tie-break untouched — retained as the automatic outcome whenever fusion does not strictly improve the frozen representative corpus)
- **Prepare-phase Wave Council [prepare-council] — 2026-07-23: PASS (delta: late admission of `1tgkx`)** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the harness-token filter could suppress a genuine fragile signal if the runner itself is the repaired surface — resolved by accepting the conservative draft-nothing outcome explicitly in the plan and pinning it in the producer-derived corpus; strongest-alternative: fold the extraction fix into a standalone supply wave instead of 1tbt5 — rejected because the wave already owns the memory-quality arc and the change is independent of both retrieval changes, with no serialization point)
- **Delivery-phase independent review [wave-council-delivery] — 2026-07-23: PASS** (independent reviewer, fresh context; executed evidence: hermetic eval reproduced byte-for-byte (fingerprint 72ead292…d23f4a4, 11/11 invariants, adoption gate adopt=false with product path unchanged), full suite 6,193/59 OK reproduced, post-reload live probes: memory_propose on the real 1tg55 ledger drafts nothing (the misattribution producer), memory_brief queryless with adaptive decay_basis live in both directions, decay_basis consumer census pass-through only; one observation: the curated real-corpus semantic leg never executed (backend unavailable to the standalone interpreter), so any future fusion revisit needs a semantic-capable eval environment)

## Implementation Progress Log

- **Thought — ordered lane sequence:** (1) implementer + qa-reviewer repair the
  independent harness-target extraction defect; (2) qa-reviewer expands and
  freezes the retrieval evaluation corpus; (3) implementer adds shared adaptive
  freshness helpers and response orchestration; (4) performance-reviewer
  verifies the one-batch/no-FTS hot-path contract; (5) implementer evaluates
  lexical+semantic fusion and touches the product path only on a passing gate;
  (6) docs-contract-reviewer reconciles the documented shipped result.
- **Observe — packet complete:** all three admitted changes have requirements,
  prioritized ACs, builder/reviewer lanes, affected docs, explicit degraded
  behavior, and bounded serialization points. No unresolved implementation
  unknown remains before activation.
- **Observe — harness-target repair:** the canonical/configured runner-only
  filter is implemented and the two producer-derived regression probes pass;
  genuine repeated product-module repair signals remain draftable.
- **Observe — adaptive freshness:** the shared policy layer derives
  median-cadence half-lives from the existing one-batch history read, uses named
  clamps/fallbacks, preserves protected/fragile boundaries, and is covered by
  the 11-case hermetic corpus.
- **Observe — measured fusion rejection:** hermetic baseline recall@3/MRR was
  `1.0000/1.0000` versus candidate `1.0000/0.8485`; the frozen 12-record
  curated pass could not load the semantic backend in the standalone
  interpreter. Per the adoption contract, the shipped semantic tie-break
  remains unchanged and no dormant product branch or flag was added.
- **Observe — lifecycle validation repair:** superseding the prior promoted
  decision memory exposed a docs-schema mismatch. The schema now treats
  `Validation: promote` as historical provenance when ordinary lifecycle
  supersession supplies `Superseded by:`, pinned by the full docs-lint module.
- **Gapfill:** framework internal tests are deliberately excluded from the
  semantic code index; exact test-class and performance-registry locations were
  resolved with bounded `rg` queries after MCP retrieval returned the indexed
  implementation seams.
- **Verify — implementation complete:** targeted suites (memory eval 9,
  memory records 176, performance policy 5, docs lint 574) passed; the canonical
  full runner then passed 6,193 tests across 59 files in 289.113s and
  `wf_validate_docs` returned clean.
- **Observe — existing performance flake:** an intervening back-to-back suite
  run measured the pre-existing CE 10-candidate warm p95 at 18.403 ms against
  its 10 ms threshold; the first immediate isolated rerun measured 10.329 ms,
  the next isolated rerun passed, and the final quiet full suite passed. No
  wave code touches that CE path; retain it as the already-known
  contention-headroom cleanup candidate rather than rebudgeting it here.
- **Repair — delivery-review blocking P2 (2026-07-24):** an independent
  re-review found that the eval candidate's `_policy_order` treated an empty
  relevance union as unrestricted, so a query matching neither stream surfaced
  every record, violating the positive-match-union and lexical-degradation
  contract. The query path now admits only the relevance union (empty -> zero)
  and `_shipped_baseline_order` opts into a `prefiltered=True` so its
  containment union is not double-restricted; a zero-match regression covers
  the candidate and both controls plus the prefiltered baseline. Shipped
  `memory_search` was never affected (fusion stays evaluation-only). Chain
  terminal via repair_start + a fresh independent code-reviewer reverification;
  full suite 6,194 OK and the hermetic eval fingerprint reproduced unchanged;
  delivery re-approved post-repair.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| fusion-empty-relevance-union-surfaces-unrelated-records | do_now | no | completed | wave-council-delivery |

*Machine review evidence — 19 records; 5 runs; 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- Consumes the archive and pointer contract completed by wave
  `1t8la memory-archival-and-retention`; that closed wave is not reopened.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 57 | 1,437,016 |
| implement | 101 | 2,537,276 |
| review | 46 | 439,389 |
| **Total** | **204** | **4,413,681** |

<!-- wave:context-efficiency-state {"generation":179,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":101,"content_source_credit":2786988,"derived_artifact_credit":193,"direct_net":2537276,"estimated_tokens_saved":2537276,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4977,"response_debit":246501,"source_credit_count":103,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1573},"plan":{"calls":57,"content_source_credit":1546253,"derived_artifact_credit":1367,"direct_net":1437016,"estimated_tokens_saved":1437016,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":4273,"response_debit":113670,"source_credit_count":106,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":7339},"review":{"calls":46,"content_source_credit":500267,"derived_artifact_credit":855,"direct_net":439389,"estimated_tokens_saved":439389,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9814,"response_debit":53131,"source_credit_count":23,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1212}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":204,"content_source_credit":4833508,"derived_artifact_credit":2415,"direct_net":4413681,"estimated_tokens_saved":4413681,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":19064,"response_debit":413302,"source_credit_count":232,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":10124},"wave_id":"1tbt5 memory-retrieval-quality-adaptive-freshness"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
