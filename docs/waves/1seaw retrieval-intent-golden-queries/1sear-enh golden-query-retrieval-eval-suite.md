# Golden-Query Retrieval Eval Suite (the Standing Gate for Ranking Changes)

Change ID: `1sear-enh golden-query-retrieval-eval-suite`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-08-21
Wave: `1seaw retrieval-intent-golden-queries`

## Rationale

External code review (2026-07-12) + this repo's own history converge on the same gap: ranking/classification changes here ship eval-gated (the AC-8 gate that killed `code_risk_score` v1; the AC-10 recall comparison for agent-mode `code_ask`), but every gate so far has been BESPOKE — assembled per change, then discarded. There is no standing, repeatable retrieval evaluation, so (a) each ranking change re-pays the harness cost, (b) regressions between changes are invisible, and (c) observed quality issues (the review session's "where are the gaps?" queries ranking `.aiignore` comments above implementation; the session-8 "what value is X" constant-ranking weakness; the multi-token summary-first behavior) are recorded as memory anecdotes instead of failing test cases.

This change builds the suite; `1seas` (classifier/ranking improvements) is gated on it. It also seeds the review's proposed scheduled evaluation without committing to CI infrastructure yet.

Voyage Code 4's published evaluation supplies one useful benchmark shape without changing Wavefoundry's local-only model policy: ask with a natural-language issue description, then score whether retrieval finds the files that contain the fix. Wavefoundry will adopt that evaluation pattern using locally curated change records and Git provenance. It will not adopt a hosted embedding dependency or make `voyage-4-nano` a delivery assumption; the current shared embedder is the approximately 33.2M-parameter `Snowflake/snowflake-arctic-embed-s`, while the 0.3B class (`voyage-4-nano` is approximately 340M total parameters) has not met the operator's practical local runtime envelope.

## Requirements

1. **Golden-query corpus, versioned in-repo:** known-answer queries against THIS repo's indexed content, each with expected top-hit path(s)/symbol(s) and question-type expectations. Seed classes (from live evidence): architecture/review intent ("where are the biggest gaps in X"), known-symbol navigational, constant-value lookup, exact-identifier lexical, error-string lookup, enumeration ("which X are…"), direct ignore-file/manifest questions (the ONLY class where low-information paths are the right answer), abstention cases (absent topics must return low confidence, not fabrication), and **agentic fix localization** (a symptom/problem statement must retrieve the implementation and supporting paths that contain its fix).
2. **Metrics:** Recall@k and nDCG@k against expected hits; MRR@10 / first-relevant rank for agentic fix-localization cases; abstention correctness on the negative controls; p95 latency and response size per tool (`code_ask`, `code_search`, `docs_search`, `code_lexical`). Agentic cases use graded relevance (primary implementation paths above supporting tests/specs) and report nDCG@10. Cached-model runs only (no network).
3. **Frozen evaluation environment (plan-review addition; reconciled with wave `1sed7`):** before/after comparisons run against a FROZEN index state — the runner snapshots (or verifies unchanged) the index-state store's BUILD GENERATION across the run (post-`1sed7`, the store's generation row is the canonical index signature; `meta.json` is retired) and disables/defers the background staleness monitor and hook refreshes for its duration; a signature change mid-run invalidates the report. The report records model names/versions, execution provider, and hardware; p95 latency is computed from repeated samples after a documented warm-up (never from a cold first call).
4. **Calibration/holdout split (plan-review addition):** the corpus separates CALIBRATION cases (visible during `1seas` tuning — includes the verbatim misranked queries) from WITHHELD validation cases (paraphrases/novel instances of each class, not consulted during tuning); the gate verdict weighs the holdout set, so the classifier cannot be tuned to the exact queries that declare success.
5. **Local agentic fixture provenance:** add at least ten fix-localization cases sourced only from committed Wavefoundry bug/enhancement change docs and local Git history, split at least five calibration / five holdout. Each fixture records the natural-language query, source change/commit provenance, graded expected paths, and a short relevance rationale. At least half are symptom-only queries with filenames and implementation symbols removed. Human verification distinguishes primary implementation from supporting test/spec paths and excludes incidental generated, manifest, or mechanical files unless they are the subject of the change. The suite evaluates the CURRENT built index; it must not represent this small curated corpus as a historical pre-fix-snapshot benchmark.
6. **Runnable locally in one command** (a `run_tests.py`-adjacent entry or `wf` verb), producing a comparable scored report artifact; deterministic enough to diff across runs on the same index.
7. **Baseline recorded:** the current scores land in the change doc / a report artifact as the reference line `1seas` must beat-or-hold.
8. **Gate wiring:** documented (contributing/review docs) as the required evidence for future ranking/classification/chunking-relevance changes — the standing replacement for bespoke gates.

## Scope

**Problem statement:** ranking changes need an eval gate, and each one has been built from scratch and thrown away; known quality anecdotes aren't executable.

**In scope:** eval harness + nine-class golden corpus + locally curated, provenance-backed agentic fix-localization fixtures + metrics + baseline + gate documentation.
**Out of scope:** any ranking change itself (that is `1seas`); embedding-model replacement or training; hosted inference/API use; assuming a roughly 0.3B-parameter local model is viable; automatic mining and indexing of historical pre-fix repository snapshots; CI scheduling (operator infra decision — the suite must merely be CI-invocable later); consumer-repo query packs (the multi-language test-pack `p4ea` can extend this later).

## Acceptance Criteria

- [ ] AC-1: The suite runs in one local command against the current index with cached models and emits a scored report (Recall@k, nDCG@k, agentic MRR@10 / first-relevant rank, abstention, p95 latency, response size) per tool.
- [ ] AC-2: The corpus covers all nine seeded query classes, including the review session's misranked queries, at least two abstention controls, and at least ten agentic fix-localization cases (minimum five calibration / five holdout; at least half symptom-only) with graded expected paths.
- [ ] AC-3: The baseline run is recorded and reproducible (two consecutive runs on the same FROZEN index agree within a documented tolerance), with environment (models, provider, hardware) recorded and the monitor/hook-refresh freeze proven by an unchanged build generation across the run.
- [ ] AC-6: The corpus is split calibration vs holdout (every class represented in both), and the gate verdict is computed on the holdout set.
- [ ] AC-4: The gate is documented in the contributing/review surfaces as required evidence for ranking-behavior changes.
- [ ] AC-5: Full suite bytecode-free + docs validation (the eval itself is NOT part of the default test run — it needs the built index).
- [ ] AC-7: Every agentic fixture carries local change/commit provenance, human-verified graded relevance and rationale; no network, hosted model, historical-snapshot index, or incidental touched-file label is required to build or run the corpus.

## Tasks

- [ ] Harness (query runner + scoring + report artifact) under `scripts/benchmarks/` or eval-adjacent home.
- [ ] Golden corpus with the nine classes; encode the session's misranked queries verbatim.
- [ ] Curate and human-verify at least ten local change/Git-backed agentic fix-localization fixtures, including symptom-only holdouts and graded implementation/supporting-path labels.
- [ ] Baseline run + tolerance check; record scores.
- [ ] Gate documentation; suite + validate.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| harness | implementer | — | Runner + metrics + report |
| corpus | qa-reviewer | — | Nine classes + negatives + locally sourced agentic fix-localization fixtures |
| baseline-docs | qa-reviewer | both | Scores + gate wiring |


## Serialization Points

- `1seas` (same wave) is BLOCKED on this change's baseline — the suite must exist and score before any ranking edit lands.
- The eval keeps the current local model stack fixed; model comparison or migration requires a separate change after this gate can measure it.

## Affected Architecture Docs

- `docs/architecture/testing-architecture.md` (the eval tier); `docs/contributing/review-and-evals.md` (gate requirement). N/A otherwise.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The deliverable. |
| AC-2 | required | Coverage is the value; anecdotes become executable. |
| AC-3 | required | An unreproducible gate gates nothing. |
| AC-4 | required | The standing-gate contract. |
| AC-5 | required | Standard gate. |
| AC-6 | required | Calibration/holdout separation prevents tuning to the verdict. |
| AC-7 | required | Local provenance and graded relevance keep the agentic benchmark honest and reproducible. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-18 | Extended the standing suite with a local agentic fix-localization class inspired by Voyage Code 4's issue-to-fix-file evaluation shape. Kept the current approximately 33.2M-parameter embedder fixed; no hosted or 0.3B-class model dependency was added. | Operator direction; Voyage Code 4 evaluation article; current `DOCS_MODEL` / `CODE_MODEL` configuration. |
| 2026-07-12 | Reconciled with wave `1sed7` (operator-directed ordering): the frozen-run signature is the store's build generation, not a meta.json signature. | Operator ordering decision; 1sed6 build-state contract. |
| 2026-07-12 | Plan-review revision (external, validated): evaluation isolation was underspecified — implementing `1seas` edits indexed framework code while background refreshes mutate the signature mid-run. Added the frozen-environment requirement (signature-verified, monitor/hook deferred, env recorded, warm-up + repeated samples for p95) and the calibration/holdout split so the classifier cannot be tuned to its own verdict queries. | Plan review. |
| 2026-07-12 | Drafted from the external code review (P1 CI/eval finding, the retrieval-eval kernel) + accumulated quality-log anecdotes that should be executable cases (session-8 constant ranking, review-session ignore-file misranking, multi-token summary-first). Positioned as the gate `1seas` requires. | Review report; quality-log memory; AC-8/AC-10 gate precedents (1p41o gate-out, 1p4hj recall comparison). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-18 | Add a curated local agentic fix-localization class to the existing standing suite: natural-language issue/change symptoms are scored against human-graded implementation and supporting paths from committed change docs and Git provenance. | It captures the useful issue-to-fix-file benchmark shape while remaining small, deterministic, auditable, and compatible with the proven 33.2M-parameter local embedder. | **Automatically mine historical pre-fix snapshots:** rejected for this change because reconstructing/indexing historical trees and cleaning touched-file labels materially expands the harness. **Integrate Voyage hosted embeddings or `voyage-4-nano`:** rejected because hosted inference violates local-first and the approximately 340M-total-parameter model is outside the operator's proven local runtime envelope. |
| 2026-07-12 | Suite is local-first and index-dependent (NOT in the default unit-test run); CI scheduling deferred to an explicit operator infra decision. | The default suite must stay hermetic/fast; the eval needs a built index + cached models. CI is a separate adoption question the suite must not block on. | **Bundle into run_tests.py:** breaks hermeticity. **Wait for CI decision:** the gate is needed by `1seas` now. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Index drift makes runs incomparable | Report records the index build generation; comparisons are valid same-generation only, and the tolerance check quantifies noise. |
| Corpus overfits to this repo | Acceptable for the gate's purpose (this repo IS the dogfood); consumer packs (p4ea) extend later. |
| Treating every file touched by a historical fix as equally relevant rewards generated or mechanical noise | Human-review every agentic fixture, use graded primary/supporting relevance, record rationale, and exclude incidental paths. |
| Issue text leaks filenames or implementation symbols and makes localization trivial | Mark query form explicitly; require at least half of agentic cases to be symptom-only and keep at least five agentic cases withheld. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
