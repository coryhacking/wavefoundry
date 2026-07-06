# Churn-Aware Retrieval Decay

Change ID: `1ro43-enh churn-aware-retrieval-decay`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-04
Wave: `1ro44 agent-memory-and-retrieval-decay`

## Rationale

Retrieval currently treats every indexed chunk as equally current. The cross-encoder reranker orders candidates purely by query relevance; nothing in the pipeline knows that a doc was last touched fourteen months ago while the code it describes has churned through thirty commits since. Agents therefore receive confidently-ranked citations to documentation that no longer matches the code, and they have no signal to distrust them.

The key insight is that for documentation, decay is **not a function of the document's age**. A two-year-old doc describing a stable module is perfectly fresh; a two-week-old doc describing a file that has changed daily since is already stale. The decay signal that matters is **churn of the described code since the doc was last checked against it** — doc-code drift — not elapsed time. Wavefoundry is uniquely positioned to compute this locally: git history provides per-file churn with no network dependency, and the structural graph links docs to the code areas they describe.

A critical constraint discovered during planning: the existing `Last verified` frontmatter is **not** a verification event. `docs_gardener.refresh_last_verified` stamps the date mechanically on any git-changed doc — it means "this file was touched," not "an agent or operator confirmed this doc still matches the code." Drift must therefore anchor to signals that cannot be mechanically polluted: the doc's last *content* change in git, and an explicit **verification stamp** written only by a deliberate review. This splits decay into two tiers with a clean boundary. The mechanical tier (this change's index/annotation machinery) can only ever *propose* staleness — churn is suspicion, not a verdict, since code can churn thirty commits without invalidating a doc and a single rename can invalidate a doc whose referenced files never changed. The verdict requires the **agentic tier**: an agent reads the flagged doc against the current code and disposes it — verified (stamp), amend, or stale. That judgment loop cannot live inside the MCP server (tools are mechanical; synthesis belongs to the calling agent), so it ships as a prompt surface consuming the drift worklist, mirroring the propose/dispose reconciliation pattern of `1p8gy` memory records. By operator direction the agentic tier is planned separately as `1rolq-enh verify-docs-agentic-review` (future wave, after this wave lands); this change ships every mechanical contract that loop consumes — the stamp field, the drift anchor, the gardener exclusion, and the worklist.

The same reasoning extends per-content-kind, and it resolves into a three-class model. **Code chunks** are self-describing (a code chunk is never stale relative to itself — its embedding is refreshed on change via `chunk_hash`), so raw age should never penalize code. **Living docs** (architecture, references, guides, prompts) drift against the code they describe and are disposed by deliberate review. **Historical wave documents** (wave records and change docs under `docs/waves/`) are the third class and numerically the bulk of the docs index: they are frozen archives — the preservation policy forbids rewriting closed waves — yet they surface in retrieval constantly, describing code as it stood when the wave landed. For them decay is definitional and needs no prose parsing at all: the wave's **landing commit** (derivable from the repository's landing-commit message convention) is the anchor, the landing diff **is** the reference set, and staleness accumulates monotonically as later work touches that change set. They are never verified or amended — annotation is the complete treatment. Memory records (`1p8gy-enh graph-backed-agent-memory`) decay by kind: a `failed_attempt` decays as its target file churns (the failure may no longer reproduce), an `operator_preference` does not decay with code churn at all, an `environment_gotcha` decays with time and tool versions. A single global half-life would be wrong for every one of these; decay policy must be evidence-based and class/kind-aware.

Ranking safety is the central design constraint. The reranker's relevance ordering is the most valuable signal in the pipeline (wave 1p52p), and multiplying calibrated scores by a time factor would bury correct answers about stable code. This change therefore surfaces temporal evidence as **annotation first, demotion only on strong evidence** — mirroring the existing `demoted: true` partition mechanic (infrastructure partition, wave 1p4wz) rather than perturbing scores.

## Requirements

1. At index build time, record per-file temporal metadata resolvable for every indexed chunk: `last_modified` (git last-commit timestamp for the source file, falling back to filesystem mtime when git history is unavailable), and `churn_score` (commit count touching the file over a trailing window, normalized). Computation must be local-only (git log against the local repository; no network). **Storage recommendation:** a per-file SQLite sidecar in the index directory following the graph state store pattern (WAL, single-transaction updates, derived/rebuildable-only content), rather than widening Lance chunk rows — `churn_score` changes on every build for active files even when chunk content is unchanged, and rewriting unchanged Lance rows would defeat `chunk_hash` reuse and add fragment churn. Vectors and chunk content stay in Lance; the sidecar holds only derived relational state (freshness, wave→files attribution, drift summaries) and rebuilds from git on any mismatch. Final storage choice recorded in the Decision Log at implementation.
2. Temporal metadata must ride the existing incremental-update path without rewriting unchanged vector rows: with the sidecar approach, freshness refreshes for all files on every build in one transaction; if chunk-row storage is chosen instead, unchanged chunks may carry stale churn values between rebuilds, refreshed when the file re-embeds. Either way, no per-query git invocation is permitted.
3. Compute a **doc-code drift** signal for docs chunks: a doc is drift-flagged when code files it references (via explicit path references in the doc and/or graph doc→code edges) have accumulated commits after the doc's **drift anchor**. The anchor is the most recent of: (a) the doc's last content change in git, and (b) the doc's verification stamp (Requirement 10) when present. Gardener-stamped `Last verified` dates are explicitly **not** an anchor — `docs_gardener` writes them mechanically on any touched file, so they carry no verification meaning. Drift computation summarizes per-doc as `{drifted: bool, drift_refs: [paths], commits_since: n, anchor_kind: "content" | "verification"}`.
4. Surface temporal metadata on retrieval responses: `docs_search`, `code_search`, and `code_ask` citations gain optional `freshness` fields (`age_days`, `churn_score`, `drifted`, `commits_since_verified`) when the index carries them. Absence of metadata (older index) degrades silently — no errors, no schema break.
5. Ranking policy — annotation first, evidence-gated demotion only:
   - Raw age must never change ranking for any content kind.
   - Drift-flagged docs chunks are stable-partitioned toward the end of the citation list (same mechanic as the infrastructure partition) **only when** non-drifted candidates of comparable relevance exist (relevance-band guard), and each such citation carries an explicit `demoted: true` + `partition_reason: "doc_code_drift"`.
   - Code chunks are exempt from demotion (a current code chunk is ground truth for itself).
6. Decay policy hooks for memory records (integration seam for `1p8gy`): the freshness computation must be callable per-path/per-doc so memory retrieval can apply kind-aware decay (e.g. `failed_attempt` confidence attenuated by target-file churn since `created_at`). This change ships the primitive; 1p8gy consumes it.
7. Staleness must also be visible outside retrieval: `wave_graph_report` or `wave_audit` (choose one during implementation; record in Decision Log) gains a compact drift summary — count of drift-flagged docs and the top offenders — so gardening has a worklist. `wave_garden` guidance references it.
8. All thresholds (churn window, drift commit threshold, relevance-band width) are named constants with rationale comments, not scattered literals.
9. A census task precedes ranking enforcement: before enabling the demotion partition by default, measure drift-flag precision on this repository (are flagged docs actually stale?) and record findings in the change doc. If precision is poor, ship annotation-only and record the decision.
10. Add a **verification stamp** distinct from gardener metadata: a frontmatter field recording the commit the doc was deliberately reviewed against (working form `Verified against: <commit-sha>`; exact field name finalized at implementation and recorded in the Decision Log). Semantics:
    - Written only by an agentic verification pass or the operator — `docs_gardener` must never create, update, or delete it.
    - Anchoring to a commit SHA makes drift exact and unambiguous: drift = commits touching referenced files after that SHA.
    - The drift clock resets only on doc content change or a new verification stamp.
11. Ship the consumer contracts for the future agentic loop (`1rolq-enh verify-docs-agentic-review`): the drift worklist output (Requirement 7) and the verification stamp field (Requirement 10) are documented as stable formats — worklist ordering fields (`commits_since`, drift refs) and stamp syntax/semantics — so the Verify docs prompt surface can consume them without changes to this change's code. No prompt surface, dispositions, or review workflow ship in this change.
12. Derive **wave→files attribution** from the commit log at build time: parse landing-commit messages matching the repository's landing convention (tolerant patterns for "Land wave <id>", "Land waves <id, id, …>", and observed wording variants), map each wave to its landing commit(s) and their diffs. Bundle commits attribute coarsely (all bundled waves share the change set) and this is recorded as wave-set attribution, not per-wave precision. Derivation is best-effort: unmatched history degrades to plain churn with no errors. (Deterministic close-time manifests that supersede this derivation when present are planned separately as `1rppn-enh wave-change-manifests-close-advisory`, future wave.)
13. Treat wave documents as the **historical** content class: docs chunks under `docs/waves/` are anchored at their wave's landing commit (from Requirement 12), their reference set is the landing diff (no prose reference extraction), and their freshness annotation carries `historical: true` plus decay in **waves-behind** units (count of later waves whose change sets intersect this wave's change set) alongside `commits_since`. Historical docs are excluded from the Verify docs disposal path by construction (they are never verified, amended, or marked stale for decay reasons) and excluded from the drift worklist; annotation is their complete treatment. Waves with no derivable landing commit fall back to the living-doc anchor rules.

## Scope

**Problem statement:** Retrieval ranks by relevance only; agents receive no signal that a highly-ranked doc citation describes code that has since changed, and stale documentation is indistinguishable from current documentation at action time.

**In scope:**

- Index-time temporal metadata (`last_modified`, `churn_score`) for docs and code chunks in `indexer.py`; recommended storage is a per-file SQLite sidecar (graph state store pattern), keeping Lance rows content-addressed.
- Git-history churn extraction helper (local subprocess, batched per-build, cached per-file).
- Doc-code drift computation for docs chunks (content-change/verification-stamp anchor vs referenced-code churn, using explicit path refs and graph doc→code linkage where available).
- Verification stamp frontmatter (commit-SHA-anchored, gardener-excluded) and its docs-lint awareness; documented worklist/stamp contracts for the future agentic consumer.
- Wave→files derivation from landing-commit messages (tolerant patterns, wave-set attribution for bundles, best-effort degrade).
- Historical content class for `docs/waves/` chunks: landing-commit anchor, landing-diff reference set, `historical: true` annotation with waves-behind decay, worklist/disposal exclusion.
- `freshness` annotation on `docs_search` / `code_search` / `code_ask` citations.
- Evidence-gated drift partition (post-rerank, stable, reason-tagged) with relevance-band guard and kill-switch env var.
- Drift summary surfacing in one audit/report tool + `wave_garden` pointer.
- Reusable per-path freshness primitive consumable by the 1p8gy memory layer.
- Census pass on this repository before default-on demotion.
- Tests: metadata stamping, incremental staleness tolerance, drift computation (frontmatter present/absent), partition behavior and guard, response schema back-compat with metadata-free indexes.

**Out of scope:**

- Multiplying or blending decay factors into cosine, RRF, or reranker scores — raw score perturbation is explicitly rejected (see Decision Log).
- Any time-based re-embedding or index rebuild scheduling.
- Memory-record kind-aware decay policies themselves (owned by `1p8gy`; this change only ships the freshness primitive they call).
- Cross-repository or historical trend analytics; dashboard visualization beyond the drift summary count.
- Network calls of any kind (GitHub API, remote git). Local `git log` only.
- The agentic **Verify docs** review loop (prompt surface, dispositions, pass reports, guidance pointers) — owned by `1rolq-enh verify-docs-agentic-review`, planned for a future wave after this one lands. This change ships the contracts it consumes, nothing more.
- Close-time wave change manifests, baseline capture, and declared/referencing docs advisories — owned by `1rppn-enh wave-change-manifests-close-advisory` (future wave); this change ships only the commit-log derivation those manifests will supersede when present.
- Demotion/partition of historical wave-doc chunks — annotation only in this change; any ranking treatment for the historical class waits on census evidence.

## Acceptance Criteria

- [ ] AC-1: After a full index build, every docs and code chunk resolves `last_modified` and `churn_score` (via the chosen storage — per-file sidecar or chunk rows); builds in a repo without git history fall back to mtime with `churn_score` absent/zero and no errors; refreshing freshness for unchanged files rewrites no vector rows.
- [ ] AC-2: Doc-code drift is computed for docs chunks anchored to the doc's last content change or its verification stamp (whichever is newer) against churn of referenced code paths; a fixture doc referencing a churned file is flagged with `drifted: true` and its `drift_refs`; a fixture proves gardener-stamped `Last verified` dates do NOT move the anchor.
- [ ] AC-3: `docs_search`, `code_search`, and `code_ask` citations include `freshness` fields when the index carries metadata, and omit them cleanly (no error, no null-noise) against a pre-decay index.
- [ ] AC-4: Drift-flagged docs citations are stable-partitioned after comparable non-drifted candidates with `demoted: true` and `partition_reason: "doc_code_drift"`; ranking is unchanged when no comparable alternatives exist; raw age never changes ordering; code chunks are never drift-demoted. A kill-switch env var disables the partition entirely.
- [ ] AC-5: No per-query git subprocess is spawned: churn/drift computation happens at build time; a query-path test asserts zero git invocations during search.
- [ ] AC-6: A per-path freshness primitive is exposed internally (single function/API) and covered by a test demonstrating the 1p8gy consumption pattern (path in → `{age_days, churn_score, commits_since}` out).
- [ ] AC-7: One audit/report surface exposes the drift summary (flagged count + top offenders); the choice and rationale are recorded in the Decision Log.
- [ ] AC-8: Census findings (drift-flag precision on this repository, sample of flagged docs with true/false staleness judgments) are recorded in this change doc before the demotion partition defaults on; if shipped annotation-only, the decision and evidence are recorded.
- [ ] AC-9: Incremental updates preserve temporal metadata correctness for changed files and tolerate staleness for unchanged files without index-version errors; index/builder version bumps follow existing conventions.
- [ ] AC-10: Full framework tests run bytecode-free and docs validation passes.
- [ ] AC-11: The verification stamp is commit-SHA-anchored, resets the drift clock when written, and is untouched by `docs_gardener` (a gardener run over a stamped doc leaves the stamp byte-identical, proven by test); docs-lint accepts the stamp field and flags malformed SHAs.
- [ ] AC-12: The drift worklist format and verification stamp syntax/semantics are documented as stable consumer contracts (fields, ordering, reset rules) referenced from the drift summary surface, sufficient for `1rolq-enh verify-docs-agentic-review` to build against without code changes here; no review prompt surface ships in this change.
- [ ] AC-13: Wave→files derivation maps landing commits to waves from this repository's real history — including at least one single-wave landing and one multi-wave bundle commit (recorded as wave-set attribution) — and unmatched or convention-free history degrades to plain churn with no errors.
- [ ] AC-14: Chunks from `docs/waves/` carry `historical: true` with landing-commit anchor and waves-behind decay; they are absent from the drift worklist and never `drifted`-flagged; a fixture confirms a wave doc whose change set was later modified shows nonzero waves-behind while an untouched change set shows zero; waves without a derivable landing commit fall back to living-doc anchor rules.

## Tasks

- [ ] Add build-time git churn extraction helper (batched `git log` per build, per-file cache, mtime fallback) in the indexer layer.
- [ ] Implement temporal metadata storage (recommended: per-file SQLite sidecar on the graph state store pattern; record the decision) and bump the relevant index builder version per convention.
- [ ] Implement doc-code drift computation: content-change/verification-stamp anchor resolution, referenced-path extraction, graph doc→code linkage lookup, drift summarization.
- [ ] Add the verification stamp frontmatter field: docs-lint acceptance + SHA validation, gardener exclusion (with byte-identity test), drift-clock reset semantics.
- [ ] Document the worklist/stamp consumer contracts (formats, ordering fields, reset semantics) for the future `1rolq` agentic loop.
- [ ] Implement landing-commit wave→files derivation (tolerant message patterns, bundle wave-set attribution, best-effort degrade) in the build-time churn pass.
- [ ] Implement the historical class for `docs/waves/` chunks: landing-commit anchor, landing-diff reference set, waves-behind computation, worklist exclusion.
- [ ] Annotate `docs_search` / `code_search` / `code_ask` citations with `freshness`; guarantee back-compat with metadata-free indexes.
- [ ] Implement evidence-gated drift partition post-rerank with relevance-band guard, `partition_reason`, and kill-switch env var.
- [ ] Expose the per-path freshness primitive for memory-layer consumption (1p8gy seam) with a consumption-pattern test.
- [ ] Add drift summary to the chosen audit/report tool; add `wave_garden` pointer text.
- [ ] Run the census pass on this repository; record precision findings and the default-on vs annotation-only decision in this doc.
- [ ] Tests: stamping, fallback, drift fixtures, partition + guard + kill switch, zero-git-at-query-time, back-compat, incremental tolerance.
- [ ] Update architecture docs (search-architecture, data-and-control-flow) and run `python3 .wavefoundry/framework/scripts/run_tests.py` + `wave_validate`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| churn-metadata | implementer | — | Git extraction, chunk schema, builder version bump |
| drift-computation | implementer | churn-metadata | Frontmatter + referenced-path drift model |
| retrieval-surfacing | implementer | drift-computation | Citation freshness fields, partition + guard |
| audit-surfacing | implementer | drift-computation | Drift summary in audit/report tool |
| verification-stamp | implementer | drift-computation | Stamp field, gardener exclusion, consumer-contract docs |
| census-and-tuning | qa-reviewer | retrieval-surfacing | Precision census, default-on decision |
| tests-docs | qa-reviewer | all implementation streams | Regression suite, architecture docs, validation |


## Serialization Points

- Chunk schema + builder version must land before any consumer reads temporal fields.
- The census gate sits between annotation surfacing and enabling demotion by default — do not flip the partition default before AC-8 evidence exists.
- The freshness primitive's signature must stabilize before 1p8gy's memory-decay consumption lands (cross-change seam; coordinate in the shared wave).
- No seed or prompt-surface edits in this change: the Verify docs prompt surface (and its `seed_edit_allowed`-gated seed work) belongs to `1rolq-enh verify-docs-agentic-review` in a future wave. The worklist/stamp contracts (Requirement 11) must be documented and stable before `1rolq` is admitted anywhere.
- Storage substrate seam: the per-file sidecar recommended in Requirements 1–2 is planned to be provided by `1rq4h-enh sqlite-index-state-store` (wave `1rsh9 sqlite-index-substrate`, freshness/attribution tables). If `1rsh9` lands before this change implements, consume its store directly; if this change implements first, ship the minimal sidecar and let `1rq4h` absorb/migrate it. One store file either way — parallel sidecars are a defect (seam mirrored in `1rq4h` Requirement 5 and both wave records).

## Affected Architecture Docs

- `docs/architecture/search-architecture.md` — temporal metadata, freshness annotation, drift partition placement in the ranking pipeline.
- `docs/architecture/data-and-control-flow.md` — build-time churn extraction flow and query-time zero-git guarantee.
- `docs/architecture/graph-index-system.md` — only if doc→code linkage for drift uses graph edges (confirm at implementation).
- ADR recommended: annotation-first temporal decay vs score-blended decay (records the rejected score-perturbation approach).

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Temporal metadata is the substrate; nothing else works without it. |
| AC-2 | required | Doc-code drift is the core insight of the change — decay by churn-of-described-code, not age. |
| AC-3 | required | Annotation is the primary, always-safe delivery of the signal. |
| AC-4 | required | Ranking safety guarantees (no age-based reordering, guard, kill switch) are the contract that makes this shippable. |
| AC-5 | required | Query-path latency must not regress; build-time-only is a hard boundary. |
| AC-6 | required | The 1p8gy seam is a stated goal of the shared wave. |
| AC-7 | important | Gardening worklist is valuable but not load-bearing for retrieval. |
| AC-8 | required | Evidence gate before behavior change — prevents shipping a mis-calibrated demotion. |
| AC-9 | required | Incremental path is the default path; metadata must survive it. |
| AC-10 | required | Standard framework verification gate. |
| AC-11 | required | Without gardener-proof verification semantics the drift anchor is polluted and the whole decay signal is untrustworthy. |
| AC-12 | important | Stable consumer contracts keep the future `1rolq` loop buildable without reopening this change; annotation value ships regardless. |
| AC-13 | required | Wave attribution is the shared primitive the historical class and the future `1rppn` manifests both stand on; degrade-to-churn keeps it safe everywhere else. |
| AC-14 | required | Wave docs are the bulk of the docs index and the cheapest, highest-yield decay class — precise anchor, zero prose parsing, no review burden. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-04 | Drafted from operator request to explore decay in vector search (time, change rate, churn vs documentation). Grounded in current pipeline: rerank-first `search_combined`, `chunk_hash` incremental reuse, `Last verified` frontmatter + `wave_garden`, local git history. | `server_impl.py` `search_combined` docstring; `indexer.py` chunk_hash incremental path; `docs/architecture/search-architecture.md` Decision 3. |
| 2026-07-04 | Operator review surfaced that `wave_garden` stamps `Last verified` mechanically (no evaluation), so it cannot anchor drift. Re-anchored drift to content-change/verification-stamp (Req 3), added commit-SHA verification stamps (Req 10) and the agentic Verify docs disposal loop; ACs 11–12. | `docs_gardener.py` `refresh_last_verified` (mechanical date substitution on git-changed docs). |
| 2026-07-04 | Operator proposal: track wave-attributed change sets via the commit log. Added Req 12 (landing-commit derivation) and Req 13 (historical class for wave docs); ACs 13–14; companion plan `1rppn-enh wave-change-manifests-close-advisory` drafted for deterministic close-time manifests and close advisories (future wave). | This doc's Decision Log; `docs/plans/1rppn-enh wave-change-manifests-close-advisory.md`. |
| 2026-07-04 | Storage direction from operator question (SQLite availability): Reqs 1–2, AC-1, scope, and tasks reworded storage-neutral with a per-file SQLite sidecar as the recommended implementation, replacing the original Lance chunk-row widening and its stale-churn-between-rebuilds compromise. | Graph state store pattern (`graph_indexer.py` `project-graph-state.sqlite`, WAL/transactional, wave 1p9q3); `chunk_hash` reuse model in `indexer.py`. |
| 2026-07-04 | By operator direction, the agentic Verify docs loop moved out to `1rolq-enh verify-docs-agentic-review` (docs/plans, future wave). This change retains all mechanical contracts: stamp field, anchor semantics, gardener exclusion, worklist, and documented consumer formats (Req 11, AC-12 reworked). | `docs/plans/1rolq-enh verify-docs-agentic-review.md`. |
| 2026-07-04 | Operator proposal adopted: wave-attributed decay via the commit log. Added landing-commit wave→files derivation (Req 12) and the historical content class for wave docs (Req 13, ACs 13–14): landing-commit anchor, landing-diff reference set, waves-behind decay, annotation-only treatment, worklist exclusion. | Landing-commit convention in git history (single-wave and multi-wave bundle commits observed); preservation policy for closed-wave archives (AGENTS.md Cleanup section). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-04 | Index-time temporal metadata + annotation-first surfacing, with evidence-gated post-rerank drift partition; raw scores untouched. | Deterministic, local-only, build-time-cheap and query-time-free; preserves the calibrated reranker ordering (the pipeline's most valuable signal) while reusing the proven `demoted`/`partition_reason` mechanic; drift (churn of described code since the doc was last checked against it) is the correct decay variable for docs — age is not. | **Rank-time decay multiplier** (score × exp(−age/half-life), churn-adaptive): weakness — perturbs calibrated cross-encoder scores and buries correct answers about stable code, since old ≠ wrong; per-query freshness math also risks query-path git calls. **Gardening-only staleness reporting** (no retrieval change): weakness — the signal never reaches the agent at action time, which is exactly where stale citations cause damage. |
| 2026-07-04 | Two-tier decay: the mechanical tier proposes (churn/drift annotation + worklist), an agentic Verify docs pass disposes (verified/amend/stale), with commit-SHA verification stamps that only deliberate review may write. | Mechanical churn is suspicion, not a verdict — semantic applicability requires reading the doc against current code, which is judgment the MCP server must not perform (tools stay mechanical; synthesis belongs to agents). Stamps anchored to commit SHAs make drift exact and reset the clock only on genuine verification, mirroring the 1p8gy propose/dispose reconciliation pattern. | **Treat mechanical drift as staleness truth** (auto-demote/auto-mark on churn thresholds): weakness — false-staleness rate is structurally high (churn ≠ invalidation) and would erode trust in the signal. **LLM evaluation inside the MCP server** (server judges doc applicability at build/query time): weakness — violates the mechanical-tools boundary, adds model cost/nondeterminism to builds, and duplicates what a prompted agent already does better with full context. **Reuse gardener `Last verified` as the verification event:** weakness — gardener stamps are mechanical file-touch records; anchoring to them silently launders non-verification into verification. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Drift flags fire on docs that reference churned-but-compatible code (false staleness) | Census gate (AC-8) before default-on demotion; relevance-band guard; annotation always available even if demotion ships off. |
| Build-time git extraction slows index builds on large repos | Single batched `git log` walk per build with per-file aggregation, not per-file subprocesses; measure in build log timings. |
| Schema change breaks older indexes or the numpy fallback path | Optional-field semantics everywhere; back-compat AC-3 test against a metadata-free index; builder version bump per convention. |
| Churn window/threshold constants are wrong for other target repos | Named constants with rationale; census documents this repo's calibration; annotation-only degradation is safe by construction. |
| Freshness primitive seam drifts from 1p8gy's needs | Same wave, explicit serialization point; consumption-pattern test locks the signature. |
| Verification stamps rot: docs get verified once and never re-reviewed, so stamps become false comfort | Stamps age visibly by construction — drift resumes accumulating from the stamp SHA and the worklist re-surfaces stamped docs once post-stamp churn crosses the threshold; the recurring review cycle itself ships in `1rolq`. |
| Drift flags accumulate with no disposal path until the `1rolq` loop ships | Annotation and the worklist are still net-positive alone (agents see the suspicion signal); the demotion partition stays census-gated; `1rolq` is planned and contract-locked against this change. |
| Landing-commit derivation misattributes: bundle commits blur per-wave change sets, convention wording drifts, target repos lack the convention | Bundle attribution is explicitly wave-set-scoped (coarse, never silently per-wave); tolerant patterns cover observed variants; unmatched history degrades to plain churn; deterministic manifests (`1rppn`, future wave) supersede derivation when present. |
| Historical annotation on wave docs misleads when a wave doc is the best available answer | `historical: true` + waves-behind is context, not a penalty — no ranking change ships for the class; the reranker still decides relevance, and the annotation tells the agent to cross-check current code when waves-behind is high. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
