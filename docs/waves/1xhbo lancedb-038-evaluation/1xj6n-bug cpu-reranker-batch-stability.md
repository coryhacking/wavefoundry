# Stabilize CPU Reranker Scores Without Hiding Relevance Loss

Change ID: `1xj6n-bug cpu-reranker-batch-stability`
Change Status: `complete`
Owner: Engineering
Status: completed
Last verified: 2026-09-09
Completed at: 2026-09-08
Wave: 1xhbo lancedb-038-evaluation

## Operator Acceptance and Selected Implementation

The operator explicitly accepted the three measured ranking changes on 2026-09-08 and authorized
CPU single-passage implementation and resumed SQLite qualification. The exception is bounded to
`agentic-calibration-int8-composition` code_ask (source9→10; nDCG .27614066→.26516478,
MRR .11111111→.1), `direct-named-file-calibration-aiignore-writer` code_ask (writer remains1;
support omitted, recall1→.5 and nDCG .95676808→.91731941), and
`direct-named-file-holdout-gitignore-renderer` code_search (writer1, support8→9;
nDCG .95865971→.95676808). Other metric/flag losses remain blocking. Three repetitions must hold
these bounds; do not accept further degradation in these fixtures or waive SQLite-specific losses.

Selected repair candidate: derive a CPU INT8 static graph with input shape [1,512] from the same
manifest-managed source, using the existing atomic static-graph builder and a shape-specific cache key.
Submit one real query/passage per inference without batch padding. Keep GPU FP16 static40 unchanged.
This returns to the shape used in the operator-accepted diagnostic. Re-Prepare this repair before code
edits; verify actual-source stability and all original-baseline outcomes rather than assuming parity.
Preserve old CPU static40 caches for rollback; no re-embedding. One derived CPU graph adds disk usage;
measure its bytes and offline cache reuse. No new model weights, fixture or relevance exceptions.

The attempted direct dynamic1 implementation is rejected: its full actual-source run drops the
INT8-composition relevant result outside top10 (accepted bound was rank10) and adds an assessment
nDCG loss .96100129→.95865971. Its green unit/framework tests do not certify relevance.

Readback: CPU score becomes independent of peer candidates; GPU batching stays40. Ordered work:
admit/re-Prepare → minimal CPU/inference/logging change → focused tests and known-bad mutation →
actual-model order/count/boundary checks → canonical tests → actual-source frozen-corpus Lance/SQLite
comparison with the three bounded exceptions only → independent review. No closure or commit.

## Rationale

The same query/passage receives different CPU INT8 reranker scores when unrelated passages in its
batch change. This can change final citations when vector backends produce slightly different
candidate pools. Users need stable relevance scoring without losing useful search results. The
vector evaluation in wave 1xhbo exposed this independently of SQLite storage correctness.

## Requirements

1. Preserve the query/passage score within a declared numerical tolerance when candidate count,
   order, batch boundaries and unrelated peers change. Retain one finite raw logit per input passage
   in input order, including correct empty-input behavior and existing token truncation.
2. Preserve the model identity, embedding pipeline, candidate budgets, public response contracts,
   final top-K and GPU provider behavior. Do not special-case a fixture, filename or desired score.
3. Compare current CPU INT8 batching, isolated-passage CPU INT8, and FP32 diagnostics before selecting
   a fix. Stable scores alone do not prove relevance parity. Re-run the unchanged labeled golden
   corpus; report every per-fixture change against the current production baseline.
4. Measure CPU latency, model/cache size and startup behavior before changing a default. Bind the
   actual model shape to runtime batching and report the effective batch. Preserve offline CPU
   model-source reuse and the existing atomic static-graph publication.
5. A production change requires admission and fresh readiness. Apply only the operator-accepted
   bounded ranking exceptions above; retain all other original-baseline checks and require SQLite
   parity against the corrected Lance baseline. No further exception is inferred.

## Scope

**In scope:** CPU reranker score stability, focused inference/cache/logging seams, meaningful regression
controls, same-corpus relevance/performance comparison and any directly affected model warmup guidance.

**Out of scope:** SQLite migration, embedding quantization, GPU changes, new trained model, calibrated
anchor passages, candidate/final-limit increases, fixture-specific ranking exceptions and automatic
relaxation of relevance requirements.

## Acceptance Criteria

- [x] AC-1: A selected CPU path produces finite, order-preserving scores with at most 1e-5 raw-logit variation for fixed query/passage across unrelated peers, candidate counts and batch boundaries; a deliberately batch-dependent control fails the regression test.
- [x] AC-2: The selected path passes required labeled relevance outcomes against original production with only the three operator-accepted bounded exceptions; SQLite comparisons preserve the corrected baseline outcomes.
- [x] AC-3: The CPU static1 model submits one real row, GPU static batching and reported diagnostics agree; CPU startup/cache reuse and existing GPU routing tests pass with no change to GPU behavior.
- [x] AC-4: The change's focused tests, actual-model stability/relevance evidence and affected docs validate; latency/resource limitations and any remaining acceptance decision are explicit.

## Tasks

- [x] Reproduce peer-composition dependence and compare INT8 batch40, FP32 batch40 and INT8 batch1 in disposable CPU sessions.
- [x] Exercise the actual failing public query on baseline Lance and SQLite with an isolated batch1 override.
- [x] Complete the unchanged golden-corpus diagnostic and record every regression/improvement.
- [x] Resolve the relevance/stability acceptance decision: operator accepted the three measured changes; existing descriptive full-query latency policy remains.
- [x] Admit, prepare and implement only the selected eligible fix with targeted regression controls.
- [x] Review and record delivery evidence without closing or committing implicitly.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Candidate diagnostics | implementer | Existing frozen vector snapshot | Disposable only; no production writes |
| Acceptance and readiness | qa-reviewer, performance-reviewer, architecture-reviewer | Diagnostic evidence | Do not equate deterministic output with correct output |
| Implementation | implementer | Admission and readiness | CPU-specific, smallest eligible change |
| Delivery review | code-reviewer, qa-reviewer, performance-reviewer | Selected fix and verification | Independent code/model evidence |

## Serialization Points

Diagnostic probes use disposable files only. No repository code edit until this change is admitted and
fresh readiness plus required lane approvals are current. No candidate may advance by comparing only
two equally regressed backends; compare each with the original production relevance evidence.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/accel_embedder.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_accel_embedder.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/architecture/search-architecture.md`

## Affected Architecture Docs

`docs/architecture/search-architecture.md` if CPU execution changes. Discover model warmup/cache
consumers before adding further implementation targets. No architecture changes for diagnostics alone.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Fix the reproduced defect, including candidate order/count variants |
| AC-2 | required | Do not mask relevance loss by moving the comparison baseline |
| AC-3 | required | Static graph and batching must agree across startup/providers |
| AC-4 | required | Decisions need measured, change-local evidence |

## Progress Log

Closure 2026-09-08: independent final code tests/mutants and fresh QA receipt/model provenance passed; all three accepted original-baseline exceptions and zero corrected SQLite deltas verified. ARCH-001 corrected sibling performance architecture; fresh council approved bounded delivery. Complete reports/control sources retained in existing wave machine evidence.

- Thought/Readback: readiness and five specialist lanes now passed; implementing the reviewed cached dynamic CPU model, independent passage scoring and accurate diagnostics. GPU construction/padding remain unchanged. Focused tests will exercise a deliberately peer-dependent fake and a cache-write prohibition.

- Readback: investigate a backend-independent CPU scoring defect; do not change production merely to unlock SQLite Stage 2.
- MCP code_ask, code_outline and targeted code_read verified `StaticShapeReranker.__init__`, `rerank`, CPU resolver and all RERANK_STATIC_BATCH occurrences. The CPU and GPU paths currently both use batch40; `server_impl` logs that global constant. Tests cover padding/order and GPU40 behavior but historical toy scores do not prove actual-model peer independence.
- Disposable same-passage probe: INT8 batch40 logit span 0.0681996 across peers; FP32 batch40 and INT8 batch1 both span zero in two repetitions of three conditions. INT8 batch1 took roughly 0.63–0.68s per 40 passages, comparable to batched INT8 in this small shared-host sample; FP32 about1.25–1.55s. These are diagnostic, not a frozen latency qualification.
- Actual public query `Which function writes the .aiignore file?`: batch1 keeps the correct writer first but drops the supporting .aiignore citation in BOTH baseline Lance and SQLite. This is stability evidence, not a quality pass. It must not replace the original baseline silently.
- Raw evidence: `/tmp/wf-reranker-stability-probe-results.json`, `/tmp/wf-reranker-batch1-trace-baseline.json`, `/tmp/wf-reranker-batch1-trace-sqlite.json`. No repository code, live index, installed model or dependency changes.


- Full original-baseline comparison completed and passed receipt validation: same frozen corpus,
  35 fixtures / 55 applicable fixture-tool pairs / three repetitions (165 measured calls, 172 total
  with warmup/degraded controls). Forty-seven pairs unchanged, five improved, three regressed.
  Regressions repeat across the three runs: INT8-composition code_ask relevant source rank9→10
  (nDCG .27614066→.26516478, MRR .11111111→.1); aiignore-writer code_ask primary writer remains1
  but supporting file disappears (recall1→.5, nDCG .95676808→.91731941); gitignore-renderer code_search
  primary remains1 and supporting file moves8→9 (nDCG .95865971→.95676808).
- Improvements: build-state code_search; fallback-reasons docs_search; direct-aiignore code_ask;
  semantic-degradation code_ask; negative-explanatory-gapfill code_ask. Descriptive medians versus
  earlier original run: code_ask3974→3037ms, code_search773→626ms, docs_search660→525ms. Shared-host
  observations do not establish causal latency savings. No GPU qualification.
- FP32 static40 actual aiignore public query also loses the supporting citation, with correct writer
  still1; its full-corpus run was not pursued after this decisive strict-gate failure. SQLite singleton
  received only the targeted public query, not a new full parity pass. Do not imply four full lanes.
- Retained-context independent diagnostic review (`vector_readiness`) found singleton the smallest
  general candidate, validated the wrapper's graph/inference shape consistency and isolated cache,
  and required original-baseline comparison plus broader invariance controls before implementation.
- Current recommendation: prefer singleton CPU scoring for stability, subject to explicit acceptance
  of the three measured ranking tradeoffs. The standing no-regression requirement has NOT been
  relaxed; no implementation/adoption is authorized by an equally-regressed backend comparison.
  Full numeric evidence, raw singleton report/trace and disposable sources are in the parent wave's
  `vector-screen-results.json`. These in-memory changes are explicitly additional to unchanged on-disk
  production hashes; startup's inherited40x512 log is not actual singleton shape evidence.

## Decision Log

| Approach | Strength | Weakness / disposition |
| --- | --- | --- |
| CPU INT8 one passage per inference | Same model/precision, peer-independent in initial probe, similar sampled CPU cost | Changes some scores and has not passed final relevance; leading diagnostic candidate only |
| CPU FP32 batch40 | Peer-independent in initial probe | Roughly twice the sampled inference cost and changed scores; not selected |
| Deterministically sort/group the existing batch40 pool | Small scheduling change | Added/removed candidates still alter peers; does not solve the defect |

## Risks

| Risk | Mitigation |
| --- | --- |
| Stable but worse ranking | Compare against original production golden results, retain all per-fixture changes |
| Fixture-specific overfitting | No path exceptions, synthetic anchor passages or tuned-to-answer calibration |
| CPU cache/model shape mismatch | Instance-specific batch contract and actual static-session input checks |
| Inflated performance confidence | Broader paired samples only after candidate quality warrants it |

## Session Handoff

CPU single-passage fix selected and operator acceptance recorded; admission/readiness precede code edits. See `docs/agents/session-handoff.md`.

### Implementation verification, 2026-09-08

Thought: retain the GPU FP16 precision tolerance but check the actual selected provider; a failed GPU
probe returns CPU INT8, which is not a valid FP16 comparison. Added an explicit CPU fallback skip.
Observe: acceleration suite passed 76 tests with one GPU-only skip (9.740s). Actual updated CPU model
probe passed counts 0/1/39/40/41/81 and reversed ordering with zero score deltas (limit 1e-5).
Receipt: `/tmp/1xj6n-live-probe.json`; source SHA256
`95fd3dbe929c0d9a0b3bdbaa408339159100671f18d7e1a0c92f070e60dd211c`.
Mutation: replacing CPU batch_size with 40 caused the named
`test_cpu_rerank_isolates_passages_from_batch_dependent_scores` to fail in five nonempty subcases.
The mutation runner initially expected one failure, but unittest counts each failing subtest; all
five failures were the intended score mismatch, with no test errors. No working-tree mutation retained.
Retrieval suite, full framework suite, frozen-corpus relevance and delivery review remain pending.

Observe: public retrieval focused suite passed 1033 tests in 61.370s. Full docs lint passed. Full framework runner is in progress.

### Independent bounded implementation checkpoint

Reviewer cpu_readiness_lanes passed the code checkpoint; no full-delivery or AC2 approval. Four focused
inference/cache tests and one lazy-loader logging test passed without skips. Frozen five-file hashes
(accel, server, accel tests, retrieval tests, architecture doc):
`32cd820a74ecfad2c0d9c1b92fd38ba6911c77d4`, `a3698d74aa1e673432a732faaeb4e20d472fa7f5`,
`b8eafc8c39f30c179e71c965a0afa1ea5940e7aa`, `9c8df3b0768160b1238d2554cdbcc7911530d853`,
`afbacd93eb99ea4d98d22069c1705f5a962d1920`; unchanged before/after review.

| Mechanism | In-memory mutant | Detection |
| --- | --- | --- |
| CPU singleton | batch_size=40 | Peer-dependent test fails five nonempty subcases |
| GPU batching | batch_size=1 | Content-order test survives; existing boundary test fails |
| CPU source reuse | Static-graph build call injected | No-static-cache-write test fails |
| Effective logging | Not mutated | CPU/GPU loader control passes |

Limits: no actual GPU execution, artifact-identity proof or final relevance approval from this checkpoint.

Observe: canonical full runner passed 8580 tests / 79 files, 3 skips, 246.682s on retry. Initial
run failed only an existing TechDocs timing assertion (192ms >150ms); isolated check passed72ms.
No threshold changed. Model artifact check confirms pinned INT8 SHA a13ec391ca99f49886694e12d3e800521f36d4267d7d448c34421c541a2baf50.
Reflect: dynamic1 versus prior static1 is NOT logit-equivalent on the target passage (difference
0.0361411572); three short controls agree. Earlier static1 relevance cannot certify actual dynamic1.
Actual-source full golden run underway; no additional ranking exception is assumed. Artifact receipt
and limitations retained in vector-screen-results.json.

Thought / Readback: refreshed static1 readiness passed with fresh isolated CLI red-team and council contexts. Restore only CPU atomic static1 graph construction; keep CPU1/GPU40 inference/logging. Replace dynamic no-cache assertion with cold static1 publication and warm reuse controls, then repeat actual-source qualification.

Observe: static1 acceleration suite passes76 tests/one GPU-only skip. Actual static1 source probe
passes peer/order/count variants0/1/39/40/41/81 with zero deltas. Cold graph matches prior accepted
diagnostic bytes SHA c507287de3d8282d15cfe96160e4ec05cb8274378a3ac6bf764868b77e3854ac; actual inputs[1,512],
output[1,1]. Pinned source unchanged; warm factory returns CPU reranker without rebuild. Added cache
23012322 bytes; one cold/warm startup observation122.8/31.8ms, not percentile qualification.
Full actual-source static1 relevance underway; prior full-suite receipt predates this repair.

Observe: actual static1 full golden baseline matches prior accepted diagnostic on all metrics/flags
in all three repetitions (47 unchanged,5 improved,3 operator-accepted regressions). No extra losses.
SQLite parity run against this baseline is underway; AC2 remains incomplete until it finishes.
Independent static repair checkpoint PASS: three focused tests pass, hashes stable, no new blocker.
Cold/warm builder batch40 mutation killed by `test_cpu_reranker_builds_static_singleton_and_reuses_cache`.
Reviewer limits: real GPU execution and new builder concurrency stress not run; existing atomic builder
is unchanged. Full framework receipt must be refreshed after the static repair.

Observe: corrected Lance0.33/static1 and tuned sqlite-vec float32 show zero per-repetition metric/flag
differences (55 applicable pairs x3 =165 measured calls per lane; both receipts validate). Source
manifests match. Backend calls docs/code p95: Lance25.56/30.04ms, SQLite30.40/9.65ms, descriptive mixed
query/filter workload at frozen docs27995/code8747. code_ask medians2.877/3.138s, shared-host sequential
runs; no causal full-query speedup claim. Full static-repair framework run in progress.

Independent evidence review PASS: validate_attempt confirms165 measured calls/lane,138 semantic
with actual reranking and27 lexical controls, no measuredfallback, generation1028 and corpuscounts
unchanged. Exact originalbounds and SQLiteparity confirmed. Reviewer corrections applied: measured
trace slicing is calls[7:] (seven initial probe/warmup calls),129codeevents not126; baselinecodep95
30.04ms, SQLite9.65ms unchanged. Actual report production_identity identifies live scripts, matching
source manifests; raw wrapper note saying frozen code is stale and explicitly corrected in summary.
No all-filter/scale/coldcache or full-wave delivery claim.

Final-suite attempt after static repair:8580 tests across79files, only TechDocs existing ancestor-walk
wallclock guard failed (227.6ms vs150ms). All other files passed. Retain this failure even if retry
passes; no threshold or unrelated code changed. Canonical retry underway.

Final computational verification: canonical static-repair suite passed8580 tests/79files/3skips in
239.257s. Current green receipt written; preceding TechDocs timing failure retained above. All four
bug ACs have evidence. Required full-wave delivery review remains pending with broader evaluation
work; bounded independent implementation/relevance checkpoints do not substitute for that gate.
