# Question Classification: Artifact Anchoring + Low-Information-Path Penalty (Eval-Gated)

Change ID: `1seas-enh question-classifier-artifact-anchoring`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-12
Wave: `1seaw retrieval-intent-golden-queries`

## Rationale

External code review (2026-07-12), validated against `2952df8f`: `_classify_question` (`server_impl.py` ~17145) is phrase-driven — any question containing "where are" classifies as navigational before broader intent is considered. Live effect in the review session: broad assessment queries ("where are the biggest gaps/opportunities…") were treated as navigational lookups and ranked `.aiignore` comment lines above substantive implementation evidence — twice. Two distinct weaknesses:

1. **Intent precedence:** phrase signals fire before artifact/path anchoring; assessment/review intent ("where are the gaps", "what are the weaknesses") has no class of its own and collides with navigational ("where is the rate limiter").
2. **No low-information-path prior:** ignore files, lock metadata, manifests, and generated surfaces rank purely on token match, though they are almost never the answer — EXCEPT when the query names them, which must keep working.

Hard constraint: this is ranking-behavior change, so it ships **eval-gated on `1sear`** (the golden-query suite) — improvement demonstrated, no regression on the other classes, or it does not merge. That is the discipline that gated out `code_risk_score` v1.

## Requirements

1. **Anchoring precedence:** artifact/path anchoring (query names a file, extension, config key, or tool) is evaluated BEFORE phrase-signal classification; a query that names `.aiignore` still reaches it.
2. **Assessment intent:** separate the assessment/review intent ("where are the gaps/weaknesses/opportunities", "review X", "assess X") from navigational; assessment routes like explanatory (broad synthesis, doc demotion applied) rather than symbol-lookup.
3. **Low-information-path penalty:** a bounded down-weight (mirroring `_demote_doc_results` mechanics — down-weight, never exclusion) for ignore files, lockfiles, dependency manifests, and generated surfaces, suppressed when the query names the artifact class. Constants named and documented.
4. **Eval gate:** `1sear` baseline exists first; this change's evidence is the before/after suite report — improved on the misranked classes, non-regressing elsewhere (documented tolerance). A regression on any class blocks merge.
5. **Tests:** classifier unit fixtures for the new precedence + intent; penalty fixtures (penalized by default, exempt when named); the golden-suite diff as the AC evidence.

## Scope

**Problem statement:** phrase-driven classification misroutes assessment queries and lets low-information paths outrank implementation evidence.

**In scope:** `_classify_question` + candidate-side penalty in the selection path; constants; tests; suite-report evidence.
**Out of scope:** the eval suite itself (`1sear`); reranker/embedding changes; chunking.

## Acceptance Criteria

- [ ] AC-1: The review session's misranked queries (encoded verbatim in the golden suite) rank implementation evidence above ignore-file comments post-change.
- [ ] AC-2: Queries NAMING an ignore file/manifest still surface it top-ranked (exemption fixture-pinned).
- [ ] AC-3: Assessment intent classifies distinctly from navigational; "where is <symbol>" stays navigational (both fixture-pinned).
- [ ] AC-4: Golden-suite before/after: improved on targeted classes, within tolerance on all others — the merge gate.
- [ ] AC-5: Full suite bytecode-free + docs validation; classifier/penalty constants documented in the spec.

## Tasks

- [ ] Classifier: anchoring precedence + assessment intent.
- [ ] Selection path: low-information-path penalty (bounded, named constants, exemption).
- [ ] Unit fixtures; golden-suite before/after runs; spec/seed wording.
- [ ] Suite + validate.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| classifier | implementer | 1sear baseline | Precedence + intent |
| penalty | implementer | 1sear baseline | Bounded down-weight |
| gate-evidence | qa-reviewer | both | Suite diff = the verdict |


## Serialization Points

- BLOCKED on `1sear`'s recorded baseline (same wave, ordered). No ranking edit before the gate exists.

## Affected Architecture Docs

- `docs/specs/mcp-tool-surface.md` (question-type semantics); seed-211 (question-type recipes). N/A otherwise.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The live-observed failure. |
| AC-2 | required | The penalty must not break direct questions. |
| AC-3 | required | Intent separation without navigational regression. |
| AC-4 | required | The eval gate IS the merge criterion. |
| AC-5 | required | Standard gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-12 | Drafted from the external code review (P1 classification), validated: `"where are"` in `navigational_signals` at ~17148, checked before artifact anchoring; the reviewer's two live misrankings recorded for the golden corpus. Explicitly eval-gated on `1sear` per house ranking-change discipline. | Review report; `_classify_question` source; AC-8/AC-10 precedents. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-12 | Penalty is a bounded down-weight with a query-names-it exemption — never exclusion, never unconditional. | Mirrors the proven `_demote_doc_results` shape; direct questions about ignore files are legitimate (the review itself noted this). | **Exclusion list:** breaks direct questions. **No exemption:** same. **ML classifier:** heuristics + eval gate are proportionate; revisit only if the suite shows heuristics plateauing. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Intent changes regress existing recipes (seed-211 routing) | Golden suite covers every class; tolerance-gated. |
| Penalty misclassifies legitimate generated-surface questions | Exemption on naming + bounded weight + fixtures. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
