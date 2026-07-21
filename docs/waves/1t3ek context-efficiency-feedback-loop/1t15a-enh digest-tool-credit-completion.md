# Digest-Tool Credit Completion

Change ID: `1t15a-enh digest-tool-credit-completion`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

Operator-directed completion of the credit coverage (2026-07-20): the tools whose whole
purpose is digesting large read surfaces into small responses were still debit-only,
and two code-navigation tools shipped without any retrieval instrumentation at all.
A triage through the two deterministic lenses identified nine additions and confirmed
the rest of the debit-only set is correctly bare (verification tools stay credit-free;
full-content returners are net-zero and deliberately skipped).

## Requirements

1. **Native retrieval instrumentation** for the two omitted code tools, joining their
   siblings rather than the wrapper: `code_hover` (content-bearing current-size proof
   for the file it parses, the `code_definition` class) and `code_risk_score`
   (structural proofs from its ranked results' source-file fields, the `code_impact`
   class). Both join `_CONTEXT_RETRIEVAL_TOOLS` (and risk_score the
   reference-only-graph set), both join the wrapper's exempt set, and the reference
   doc's retrieval-tool census becomes 20.
2. **State-file reading credit via the wrapper**, bounded by what the response
   conveys or enumerates as live (three operator refinements, 2026-07-20):
   `wf_get_change` credits the change doc(s) whose content it returns (untruncated
   rows only, gated on a structural `truncated` response field); `wf_current_wave`
   and `wf_list_waves` credit only the NON-CLOSED wave records they list (the live
   working set — never the closed-history tail, so credit is bounded by work in
   flight, not repository age); `wf_list_plans` credits the pending plan docs it
   lists; `wf_map` credits its one resolved existing document; `memory_search` and
   `memory_brief` credit the capped set of record files they surface (an agent
   without the tool would open each surfaced record). The remaining counterfactual
   belongs to paired evaluations.
3. **Artifact writing credit via the wrapper** for `memory_backfill` (the records it
   drafted), crediting only paths the response exposes. `wf_sync_surfaces` deferred:
   its response exposes no file list (see Decision Log).
4. Extractors credit only what the response exposes; absent fields, containment
   failures, or error responses credit nothing (the established observational
   contract). Full-content returners (`seed_get`, `wf_get_prompt`, `wf_get_handoff`)
   and the verification family remain deliberately bare, recorded here as the
   decided boundary.

## Scope

**In scope:** the nine tools above; per-tool response-field verification before each
extractor; hermetic tests per lens; reference doc census update (18 to 20 plus the
digest-tool note).

**Out of scope:** counterfactual credit of any kind; net-zero full-content returners;
`wf_create_wave` bodies (still deferred per the 1t3s7 Decision Log).

## Acceptance Criteria

- [x] AC-1: `code_hover` and `code_risk_score` record native retrieval metrics
      (content current-size and structural proofs respectively) and are exempt from
      the wrapper, verified by test.
- [~] AC-2: Refined three times by operator direction mid-implementation
      (2026-07-20), settling on the bounded-enumeration boundary: `wf_get_change`
      credits conveyed content (untruncated rows), `wf_current_wave`/`wf_list_waves`
      credit only non-closed listed waves, `wf_list_plans` credits listed pending
      plans, `wf_map` credits its one resolved doc, and `memory_search`/
      `memory_brief` credit the capped set of record files they surface — each with
      once-only dedup, verified by test (closed rows and unresolved addresses
      credit nothing).
- [~] AC-3: `memory_backfill` credits its persisted records, verified by test.
      `wf_sync_surfaces` deferred: its response exposes no file list to credit from
      (Decision Log); queued as a next-wave response-enrichment candidate.
- [x] AC-4: Absent response fields or error responses credit nothing, verified by
      test.
- [x] AC-5: The reference doc census reads 20 retrieval tools and documents the
      digest-tool credit boundary; docs-lint passes.
- [x] AC-6: Full framework test suite passes (final: 6,024 tests across 56 files,
      OK, 2026-07-20, after the operator-review repairs).

## Tasks

- [x] Verify each of the nine tools' response shapes before writing its extractor
- [x] Native instrumentation for code_hover and code_risk_score
- [~] Reader extractors for the six digest tools plus wf_map — settled on the
      live-working-set boundary (operator direction): wave/plan listings credit
      non-closed rows only, wf_map its one resolved doc, wf_get_change conveyed
      content; memory views zero
- [~] Writer extractors for wf_sync_surfaces and memory_backfill — backfill landed;
      sync_surfaces deferred (no response file list; Decision Log)
- [x] Hermetic tests per AC
- [x] Reference doc update
- [x] Run full framework test suite

## Agent Execution Graph


| Workstream    | Owner       | Depends On | Notes |
| ------------- | ----------- | ---------- | ----- |
| digest-credit | Engineering | —          | Builds on landed 1t3s7/1t2zq machinery |


## Serialization Points

- Fourth late admission into wave `1t3ek` (operator direction); a fourth superseding
  delivery approval follows implementation.

## Affected Architecture Docs

`docs/references/context-efficiency.md` (retrieval census + digest boundary). `N/A`
otherwise.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Instrumentation omissions on shipped tools; native parity with siblings |
| AC-2 | required | The digest readers are where response is much smaller than the read surface — the honest wins |
| AC-3 | important | Writers are rare-call tools; correctness matters more than volume |
| AC-4 | required | The observational failure contract |
| AC-5 | required | The census is the operator-facing contract |
| AC-6 | required | Suite-green delivery gate |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-20 | Response shapes verified for all nine tools against real response builders; two omission classes confirmed (native instrumentation, wrapper credit) | Task 1 census in this doc |
| 2026-07-20 | Native instrumentation landed for code_hover (content) and code_risk_score (structural); both joined `_CONTEXT_RETRIEVAL_TOOLS` + exempt set + `_OBSERVATIONAL_TOOL` annotation (registration census test caught the missing annotation) | `test_registered_envelope_census_is_exact`, census case tests |
| 2026-07-20 | Operator narrowed reader credit mid-implementation: listing digests to zero; `wf_get_change` conveyed-content only with structural `truncated` field | AC-2 tests; Decision Log |
| 2026-07-20 | memory_backfill artifact credit landed; wf_sync_surfaces deferred | AC-3 test; Decision Log |
| 2026-07-20 | Second operator refinement: zero-credit for listings replaced by the live-working-set boundary (non-closed wave rows, pending plans, wf_map's resolved doc); tests rewritten to assert the boundary from both sides | `test_wave_listings_credit_live_working_set_only`, `test_map_credits_resolved_doc_only_when_it_exists` |
| 2026-07-20 | Third operator refinement: memory views join the credited readers — `memory_search`/`memory_brief` credit the capped set of record files they surface | `test_memory_views_credit_surfaced_record_files` |
| 2026-07-20 | Live-caught defect (fourth fixture-echo instance): hover census read `path` but the envelope names `file` — zero credit despite live instrumentation; repaired by reading the canonical field plus a canonical-producer oracle test; full typed chain recorded (finding, repair, reverification cycle 3) | `ev-hover-census-keys-path-but-envelope-names-file*`; live probes: hover credits 24,871 source tokens, risk_score dedups to 0 on the same version |
| 2026-07-20 | Live verification of the wrapper credits: `wf_current_wave` credited the 4 non-closed wave records (9,790 tokens), `memory_brief` its 5 surfaced records (1,729 tokens), all open_wave-attributed in review | live store source_credit rows |
| 2026-07-20 | Operator static review (P2, this change): `code_risk_score` request arguments omitted `layer`/`include_tests`, undercounting request debit; repaired at the registration with a source-census regression test; typed chain cycle 4 | `ev-risk-score-request-arguments-incomplete*` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-20 | Listings and views credit the BOUNDED LIVE SET they enumerate: `wf_current_wave`/`wf_list_waves` credit non-closed listed waves, `wf_list_plans` its listed pending plans, `wf_map` its one resolved doc, `memory_search`/`memory_brief` the capped record files they surface (three-step operator refinement) | Whole-corpus credit scales with repository history, not information delivered — but zero was too harsh: the enumerated live rows are exactly the documents an agent acting on the response would open, so credit is bounded by work in flight / response caps | Whole-file credit for every listed doc (rejected: counterfactual at corpus scale); zero credit (rejected by operator: undercounts the bounded live set); partial conveyed-size credit (rejected: no partial-file machinery; residual counterfactual belongs to `wf_context_efficiency_eval` paired evaluations) |
| 2026-07-20 | `wf_get_change` bulk rows gained a structural `truncated` boolean; the extractor gates credit on `content and not truncated` | A 300-line-capped row conveys an excerpt, not the doc; detecting the producer's truncation marker by substring would echo the fixtures-from-canonical-producers defect class | Marker substring match (rejected); credit truncated rows anyway (rejected: overstates) |
| 2026-07-20 | `wf_sync_surfaces` artifact credit deferred | Its response data exposes only `{dry_run, mode, skipped}` — no file list to credit from; crediting would require response enrichment, queued as a next-wave candidate | Parsing render logs (rejected: not response-exposed, violates the observational contract) |
| 2026-07-20 | `code_hover` credits whole-file content-bearing (gated on `symbol`), consistent with `code_outline`/`code_definition` census treatment | The census's established baseline: a targeted response that answers the question the file-read would have answered credits the file | Excerpt-only credit (rejected: no sibling does this; inconsistent census) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| An extractor assumes a response field that does not exist (the fixture-echo class) | Task 1 verifies every response shape against the real response builders before the extractor is written; failure paths credit nothing |
| Wrapper/native double-counting on the two code tools | Exempt-set membership asserted by the existing exemption test, extended to both |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
