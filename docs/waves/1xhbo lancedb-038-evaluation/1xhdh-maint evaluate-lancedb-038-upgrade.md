# Evaluate LanceDB Upgrade vs SQLite Vector Storage

Change ID: `1xhdh-maint evaluate-lancedb-038-upgrade`
Change Status: `complete`
Owner: Engineering
Status: completed
Last verified: 2026-09-09
Completed at: 2026-09-08
Wave: 1xhbo lancedb-038-evaluation

## Closure Reconciliation (2026-09-08)

The operator requested closing this evaluation after accepting FP32 as the conversion baseline.
The delivered outcome is the evaluated unified-SQLite direction, an admitted gated conversion plan
in wave `1xjmm`, proposed ADR `1xjmn`, and the implemented CPU static-singleton reranker correction.
Production vector storage remains LanceDB 0.33.0. SQLite runtime deployment and conversion are not delivered.

Unexecuted production qualification is explicitly transferred to conversion G1–G5; optional quantization
is unselected. No self-query overlap is labeled recall, no aggregate experiment RSS is attributed to one
backend, and prepared transaction results do not establish watcher latency or uninterrupted availability.
The AC/task notes below distinguish completed evidence from narrowed or transferred obligations.
Final independent review passed after ARCH-001 documentation repair and receipt/snapshot reconciliation.
Full reports and known-bad controls are retained in vector-screen-results.json closure_review; historical
approvals below cover only their original surfaces. Closure authorized; no commit requested.

## Stage 2 Result — Shared SQLite Transactions (2026-09-08)

**PASS for the bounded current-corpus storage-layout evaluation. Prefer the unified SQLite layout
for the next integration stage.** It preserves the tested payloads and search results, saves about
83.73 MiB of steady database storage (33.8%), and removes the demonstrated vector/metadata split-commit
window. This completes the layout study, not production backend adoption. Earlier no-Stage2 statements
below are historical and are superseded by this result and the corrected Stage1 qualification.

Both lanes use SQLite 3.53.4 / APSW 3.53.4.0, sqlite-vec 0.1.9 exact float32 cosine, 384 dimensions,
27,995 docs and 8,747 code chunks, 256 MiB mmap/default cache, metadata indexes and the existing state.
The comparison here is **separate SQLite files versus unified SQLite**, not a new LanceDB timing run.

| Measurement | Separate SQLite files | Unified SQLite file |
| --- | ---: | ---: |
| Steady database files, excluding WAL/SHM |248.04 MiB|164.31 MiB|
| Allocated WAL after initial import/checkpoint |249.50 MiB|165.28 MiB|
| Combined vector + FTS + payload loading p95, 120 paired warm probes |38.53 ms|33.56 ms|
| Docs vector + payload loading p95, 60 warm unfiltered probes |21.87 ms|16.60 ms|
| Code vector + payload loading p95, 60 warm unfiltered probes |6.18 ms|5.07 ms|
| Prepared 1,000-chunk update + publication p95, 5 repetitions |260.11 ms|159.65 ms|
| Ten 250-chunk delete/reinsert cycles, writer p95 with four readers |356.71 ms|287.92 ms|

Nearest-rank p95; small samples and a shared host limit timing claims. Update lanes ran sequentially.
Adding the declared 100 ms debounce estimate gives 360.11 / 259.65 ms for the 1,000-chunk case; this is an
arithmetic estimate excluding embeddings and live watcher work. All frozen layout budgets passed.
The run took 82.09 s, with aggregate process RSS 1,030.98 MiB and disposable files 1,517.06 MiB. RSS includes
both layouts and retained fixtures, so it cannot compare per-backend memory. The evaluation-only APSW
installation adds 11,539,340 bytes (11.01 MiB); it is not an adopted production dependency.

Selected design: retain separate docs/code FTS populations and their BM25/tokenizer behavior; use
canonical per-layer chunk rows, shared integer keys, vector child tables with foreign keys, and
external-content FTS in the existing state database. Preserve public IDs, auxiliary tables and
per-file hash authorities. Prepare embeddings before acquiring the writer, then publish chunks,
vectors, FTS, registry/digests and file/layer bookkeeping in one transaction. Keep the existing FULL
build fence and attempt-ID completion for graph and other work outside that transaction. The
prototype also calls the existing lexical-statistics publisher after successful completion.

Measured query plans use metadata indexes before top-k. A single-SQL late-materialization alternative
preserved results but was slower: unified docs/code p95 were 17.11 / 5.22 ms versus 16.60 / 5.07 ms for individual
payload lookups. Retain the measured simpler path; fewer SQL calls alone are not an efficiency win.
Integer-key lookup also removed the prototype's repeated FTS ID scans. External-content FTS avoids
storing canonical text twice without changing the per-layer ranking population.

Correctness evidence: 120 paired retrieval probes and all golden query strings matched between layouts;
complete keyed payload/vector/FTS/registry digests matched. Optional string/list tags have explicit
roundtrip controls. Full-row rollback checks, missing/orphan/hash/model/version/digest negative controls,
prepared source-file hash/size commit and rollback, changed-source/model guards, stale-attempt refusal,
process exits before commit and before publication, idempotent recovery, and complete backup/reopen
checks passed. The separate-file split exit committed vectors alone; unified rolled back all data.
The build fence prevented either incomplete epoch from being accepted as complete.

Four readers per lane attempted 44 queries from complete snapshots: 4 were accepted and 40 discarded
after epoch changes. This proves the tested fail-closed interleavings, not uninterrupted availability.
The raw reader-latency field includes skipped building polls and is not a successful-query p95.
Churn deletes/reinserts canonical chunks, FTS, registry and vectors within transactions; path rename,
permanent corpus shrink and sustained-duration degradation remain untested. Mtime-only coverage is a
direct metadata/vector-byte invariant, not a production embedding-reuse test. Reopen uses warm OS cache.
Passive checkpoints drained all frames; free pages were retained for reuse and 0 bytes forcibly reclaimed.
Full VACUUM was used once when constructing the disposable migrated layout, never per update.

Independent `transaction_review` reviewed protocol, prototype and final evidence: **PASS within this
scope**. Initial findings about file/chunk hash confusion, missing tags, incomplete rollback fingerprints
and reader accounting were repaired and rerun; earlier timings omitted lexical-statistics publication
and are superseded. Reviewer verified source hash, numeric gates, equal final keyed maps and limits.

Reproduction source, raw numbers, identities, command, review findings and unqualified cases are in
[vector-screen-results.json](vector-screen-results.json), `sqlite_shared_transaction_layout`.
Raw run: `/tmp/wf-stage2-layout-v3/`; source: `/tmp/wf-stage2-layout-v3.py`.
Still required before adoption: live public-query/indexer adapter tests on this layout, full filter and
availability coverage, destination migration/rollback, supported-platform runtime delivery and the
broader scale/crossover study. Patched runtime provenance is established for this isolated lane only;
installed Python SQLite 3.50.1 remains unchanged. SQLiteAI sqlite-vector remains deferred for licensing.
No production backend, installed dependency, package, closure or commit changed in this stage.

## Stage 2 Layout Protocol (2026-09-09)

Operator authorized completion of this part after corrected Stage1 current-corpus parity. Evaluate
in disposable files only, preserving production code/index and installed dependencies. Inventory uses
`index_state_store._apply_chunk_deltas_locked`, `fts_search`, `begin_build_epoch`/`finalize_build_epoch`
and `indexer._lance_incremental_write`: current vectors commit before registry/FTS, with a FULL-durable
building fence and attempt-ID publication. Existing readers must never accept a changed epoch.

Compare two SQLite layouts on the same frozen27995docs/8747code vectors and current relational state:
separate vector DB plus contentful FTS/state DB, versus one DB with integer-keyed canonical chunk rows,
float32 vectors, external-content FTS and existing registry/state tables. Preserve stable public IDs,
all served payload fields, per-layer BM25/tokenizer, filter-before-limit and content hashes. Existing
auxiliary state tables remain intact; graph storage is outside this transaction boundary.

Freeze before measurement:100ms vector-call p95; zero keyed payload/vector/FTS or publication errors;
combined vector+FTS+hydration p95 no more than20% above separate at this corpus; incremental transaction
p95 under1s for batches up to1000 prepared chunks; source-event-to-searchable prototype p95 under2s
including100ms debounce but excluding unchanged embedding/model work. Report fixed100ms explicitly,
not as measured filesystem watcher latency. Limits30minutes,4GiB processRSS,8GiB disposable disk; stop
and report partial evidence on breach. Five update repetitions at batch10/50/250/1000;120 paired
warm search queries per layout with alternating order, plus startup/first-touch separately. Nearest-rank
p95; no p99 reliability claim. Same256MiB mmap/default cache, WAL/NORMAL data writes, FULL fences,
foreign_keysON, busy_timeout5000,4096byte pages, incrementalvacuum and passive checkpoints.

Required controls: exception/process exit before commit; separate-store crash window; reader snapshot
and changed token rejection; stale attempt and changed-source refusal; bounded busy contention;
FTS MATCH and external-content integrity-check negative control; missing/orphan/hash/model-version
mismatch detection; ten branch-shaped delete/reinsert cycles with four readers; backup/reopen and
idempotent recovery; mtime-only/vector reuse and stable-ID preservation. Record statements/roundtrips,
query plans, bytes copied/stored, update/search time, peak RSS and WAL/free/reclaimed bytes. Process
kill tests cover application crash, not power-loss durability. No live destination migration claim.

Runtime: isolated APSW3.53.4.0/SQLite3.53.4 and sqlite-vec0.1.9, loaded extension/version/source recorded
before WAL probes. This is a separate binding/runtime lane, not proof that deployed Python's3.50.1 is
patched or that APSW is selected for production. Recheck lexical/vector parity against frozen existing
payloads; full public query integration remains a later production adapter gate. Retain this
component/equivalence boundary even when the layout experiment passes.

## Current Qualification Result (2026-09-08)

The CPU static1 repair passes the original-baseline bounds (only the three operator-accepted changes).
Corrected Lance0.33 versus tuned float32 sqlite-vec passes all55 applicable query/tool pairs x3reps:
165 validated measured calls per lane, no metric/flag differences. This supersedes the historical
reranker-caused Stage1 relevance failure below. The attempted dynamic1 repair was rejected first;
its extra losses are not waived. Exact sources/receipts are retained in vector-screen-results.json.

At the frozen local corpus (27995docs/8747code), hydrated vector-call p95 is SQLite30.40ms docs and
9.65ms code, versus Lance25.56/30.04ms for the observed query/filter mix. Both fit100ms. Full code_ask
medians were3.138s SQLite/2.877s Lance; sequential shared-host timing is descriptive, not causal.
SQLite uses256MiB mmap, default page cache and docs.kind/code.language indexes. No quantization.

This supplied the prerequisite for the now-completed bounded transaction/layout evaluation at this corpus size after
final verification review. It does not certify large-scale crossover, destination migration, concurrent
WAL recovery, sustained churn or the combined transaction implementation. SQLiteAI remains deferred.

## Current Operator Acceptance

On 2026-09-08 the operator accepted the three specific CPU singleton ranking changes documented in
bug1xj6n and authorized implementation plus resumed SQLite qualification. This supersedes earlier
statements that the same three losses require a decision. It does not waive additional quality loss,
vector/filter contracts or runtime/migration qualification. Compare corrected Lance and tuned float32
SQLite on the same frozen corpus; preserve the original baseline and bounded exception evidence.
Stage2 remains conditional on that corrected comparison and recorded vector viability, not mere
acceptance of the CPU change. Native int8 vector quantization remains optional and unselected.

## Rationale

### Deferred candidate: SQLiteAI sqlite-vector (2026-09-08)

- [~] Evaluate SQLiteAI `sqlite-vector`, including FLOAT16 scans, quantized indexes, filtering,
  lifecycle and distribution compatibility. **Deferred by operator direction on 2026-09-08 because
  of licensing concerns.** This candidate is outside the current wave's implementation and benchmark
  scope; revisit only with renewed operator direction. No local benchmarks or adoption occurred.

Documentation screening is retained as background: [API](https://github.com/sqliteai/sqlite-vector/blob/main/API.md)
and [license](https://github.com/sqliteai/sqlite-vector/blob/main/LICENSE.md).
The active comparison remains LanceDB versus SQLite with `sqlite-vec`. Existing CPU reranker work,
three bounded accepted ranking exceptions and conditional transaction-consolidation evaluation remain
in scope. SQLiteAI's documented FLOAT16 support does not change `sqlite-vec`'s measured capabilities.

Choose the simplest reliable local vector backend for Wavefoundry and its destination projects without losing current capabilities. Compare the installed LanceDB 0.33.0 baseline, the latest stable embedded LanceDB, and SQLite with `sqlite-vec`. Determine whether SQLite actually reduces dependencies and integration complexity enough to justify migration, or whether a LanceDB upgrade provides the better user outcome. Realistic local corpora anchor the decision; bounded larger scale probes locate headroom and crossover limits. Retaining the current backend is a valid evidence-based outcome. This wave is not automatically assigned to release 1.22.0.

## Operator Addendum: Scale, Configuration and Consolidation (2026-09-08)

**Plan revision; new measurements are pending.** The operator supplied a broader scale and SQLite
maintenance protocol after the reviewed full-query result below. Preserve all previous receipts and
review findings as historical evidence; they do not certify this extension. Re-Prepare before further
harness or runtime edits. Installed LanceDB 0.33 remains unchanged. The strict Stage 1 relevance
failure still blocks Stage 2; independent vector scale measurements may proceed within Stage 1.

The decision now needs a **measured operating envelope**, with the highest passing and first failing
corpus sizes for each required filter/workload on the declared hardware. Distinguish SQLite exceeding
the 100 ms vector budget from Lance having a material agent-facing advantage. A faster ANN query alone
is not a reason to retain Lance if both satisfy local needs. Conversely, consolidation does not excuse
quality, recovery or resource regressions. Report a bounded crossover interval, or “not reached through
N measured vectors”; never infer a universal X-million threshold or count quality-failing runs as
qualified capacity. The current evidence is tens of thousands of rows per searched table, not millions,
and does not yet prove integrated branch switching, file-change publication or long-running behavior.

### Measurement extension

- Retain the real current corpus as the decision anchor. Screen approximately 50K, 250K, 500K and 1M
  vectors; 2M+ is an optional headroom probe where practical. This explicitly replaces the earlier
  million-vector exclusion for bounded evaluation only. Declare **rows per searched table**, docs/code
  mix, total rows, filter selectivity and payload sizes. Bracket the first budget failure with additional
  intermediate sizes instead of requiring costly larger runs after an informative limit is established.
  Freeze RAM, free-disk and elapsed-time stop limits before execution; report every skipped size.
- Keep embeddings, float32 representation, dimensions, cosine metric, chunking/content hashes, FTS
  tokenizer/query behavior, candidate budgets, fusion, reranker/provider and final top-K identical.
  Quantization is a separate experiment. Repeated vectors may screen scaling cost, but cannot establish
  realistic ANN recall: record duplicate/tie distributions and use a representative distinct-vector
  workload plus an independent exact reference before making quality/crossover claims.
- Report vector-only and hydrated filtered-vector p50/p95/p99, FTS latency and full hybrid latency,
  including embedding, fusion/refill, reranking and context assembly. Separate quality against exact
  neighbors from final relevance. Freeze sample counts, seeds, warmup/cache conditions and percentile
  estimator; use enough observations for a meaningful p99 and report uncertainty. Earlier seven-sample
  slices and three full-query repetitions cannot be relabeled as reliable p99 evidence. Randomize or
  alternate paired backend order and capture host load; retain the 100 ms median/p95 vector gate and
  descriptive full-query deltas rather than inventing a percentage gate.
- Measure CPU time/utilization, RSS/peak memory, steady and peak disk including WAL/temp/backup space,
  ingestion/upsert throughput, and repeated delete/reinsert/branch-shaped churn. Stage 2 additionally
  measures actual file-change-to-searchable latency, high-churn branch transitions, concurrent readers,
  startup/recovery and a predeclared sustained workload window. Keep logical free space, reusable
  capacity and reclaimed physical bytes separate, and compare equivalent Lance compaction policies.
- Every new result carries Python version, linked `sqlite_version()` and `sqlite_source_id()`, SQLite
  compile options, sqlite-vec version/binary identity, schema/SQL hash, effective PRAGMAs, and exact
  vector path. Distinguish `vec0` KNN from ordinary-table `vec_distance_cosine` scan: a scalar B-tree
  accelerates predicates, not the cosine scan itself. For Lance record package/engine versions,
  actual ANN index type/parameters, filtering/scalar indexes, refinement and actual bypass/materialization
  evidence. Record connection counts, hardware/OS, model identities, corpus/query hashes and limits.
  [sqlite-vec documents the ordinary-table distance-function path separately](https://alexgarcia.xyz/sqlite-vec/features/knn.html).

### SQLite settings are experimental candidates

The operator's baseline is a starting configuration to measure, not an approved deployment default.
Keep an untuned control and vary one factor at a time, then confirm the selected combination; avoid
an exhaustive Cartesian product. Re-run resource measurements after tuning: an allowance for a
128 MiB cache cannot inherit the earlier roughly 39 MiB query-process RSS result.

| Area | Candidate / comparison | Evidence required before selection |
| --- | --- | --- |
| Database creation | 4096-byte pages, incremental auto-vacuum, then WAL before workload | Set creation-only options before tables; read back effective values. Existing NONE-to-INCREMENTAL conversion is a separately measured migration with rebuild/space costs. |
| Connections | `synchronous=NORMAL`, foreign keys enabled, 5000 ms busy timeout | Derived-index durability decision only; compare current baseline semantics, bound observable wait, and exercise crash/recovery. Exclude OFF. Do not apply NORMAL indiscriminately to non-derived state. |
| Memory | `temp_store=MEMORY`; cache 64/128/256 MiB; mmap 0/256/1024 MiB | Compare default/temp-file behavior too; measure simultaneous reader/writer process RSS and spill/I/O. mmap is an address-space allowance, not reserved resident RAM. |
| Write batching | One logical writer; `BEGIN IMMEDIATE`; coalesce 100–500 ms; batches 10/50/250/1000 chunks | Measure throughput, lock hold and file-change-to-searchable latency together. Compute embeddings outside the transaction, then revalidate source hashes/generation before committing. Inventory all writer processes before choosing an integration topology. |
| Checkpoints | Auto-checkpoint 1000/2000/5000 pages; observe PASSIVE progress | Record actual page size, busy/log/checkpointed values, WAL peak and reader latency. PASSIVE performs work; it is not a read-only metric. 2000 pages is about 7.8 MiB of page payload at 4 KiB, not a hard WAL-size cap. No routine TRUNCATE. |
| Reclamation | Prefer free-page reuse; conditional incremental vacuum in bounded batches | The suggested 20/40% thresholds are heuristics to test. Compare default NONE plus reuse with INCREMENTAL plus reuse/reclaim; measure fragmentation and subsequent regrowth. Full VACUUM remains an explicit maintenance/migration option, not routine per-update work. |
| Planner / FTS maintenance | `optimize=0x10002` on long-lived open, periodic `optimize`; separate FTS5 optimize/merge | Planner statistics and FTS segments are distinct. Benchmark bulk/churn triggers versus automatic merging; do not optimize FTS after each small update. |

[SQLite's PRAGMA reference](https://www.sqlite.org/pragma.html) defines these controls; unknown
PRAGMAs may be silently ignored, so capture effective settings. Cache is connection/database-scoped,
and changing auto-vacuum on an existing database may require VACUUM. NORMAL in WAL permits recent
commits to be lost on system/power failure. [Memory-mapping documentation](https://www.sqlite.org/mmap.html)
describes platform limits and trade-offs. [Planner maintenance guidance](https://www.sqlite.org/lang_analyze.html)
is version-sensitive; settings must be verified against the linked runtime.

### Runtime correctness qualification

The retained evaluation used SQLite 3.50.1, including the separate Python 3.11 probe; no vendor
backport provenance was recorded. Upstream now
explicitly documents a rare WAL-reset corruption race involving concurrent write/checkpoint activity,
fixed in 3.51.3 and later, with named backports including 3.50.7 and 3.44.6. Use a verified patched
runtime for new concurrency qualification and record its source/build identity. Historical passing
probes do not prove absence of this race or qualify an unpatched runtime. A single indexing writer
is not sufficient evidence if a separate connection can checkpoint concurrently.
[SQLite WAL-reset documentation](https://www.sqlite.org/wal.html#walreset),
[3.51.3 release notes](https://sqlite.org/releaselog/3_51_3.html).

Audit the dependency/deployment cost of obtaining that runtime: installing sqlite-vec does not itself
upgrade Python's linked SQLite. Any replacement binding or bundled runtime belongs in the dependency,
platform, startup and upgrade comparison. Apply the audit to the SQLite FTS/state store in the Lance
configuration too; keep the original baseline and label patched-runtime comparisons as new lanes.
This is a qualification finding, not evidence of observed corruption in this repository.

### Conditional transactional integration

Only after Stage 1 passes, compare the separate-vector-store layout with the colocated registry/FTS/
vector/state layout already required by AC-6. One SQLite engine or multiple ATTACHed WAL databases do
not by themselves yield an atomic cross-database commit. Demonstrate one file/transaction containing
all participating mutations, rollback and reader-generation consistency before crediting consolidation.
[SQLite documents the ATTACH/WAL atomicity limitation](https://www.sqlite.org/wal.html).

Evaluate an internal integer chunk key shared with FTS/vector rows without replacing stable public
IDs or collapsing duplicate identities. Treat external-content FTS as a candidate: preserve existing
indexed fields, tokenizer/BM25 behavior and payloads; maintain inserts/updates/deletes explicitly and
populate/rebuild preexisting rows. Counts from a non-MATCH external-content query alone cannot prove
FTS synchronization. Test MATCH results and FTS integrity-check with external-content comparison;
planner optimize and FTS optimize are distinct operations.
[FTS5 external-content and integrity documentation](https://www.sqlite.org/fts5.html#external_content_tables).

Add bounded quick_check, deeper integrity_check/foreign_key_check where appropriate, and keyed
checks for missing/orphan vectors/FTS entries, content hashes and embedding versions. A successful
SQLite integrity check does not prove application-level publication consistency. Preserve source-hash,
model/version/chunker invalidation and embedding reuse under mtime-only changes, moves and branch
switches. Filesystem reconciliation, safe backup and build-generation fences remain necessary even
if cross-engine synchronization can be removed. Credit simpler migration/recovery only after the
layout experiments and interruption tests demonstrate it.

## Carried-forward tuning and next bounded screen (2026-09-08)

Operator accepted carrying forward **256 MiB mmap plus selective metadata indexes**, retaining the
normal page-cache setting initially. This is the leading experimental configuration, not a deployed
default. The next decision remains whether SQLite preserves retrieval quality; transactional
consolidation is a conditional benefit to prove in Stage 2, not a completed saving.

The read-only warm screen used the frozen 27,995-document / 8,747-code scalar store, top-100 hydrated
results, three stored-vector queries per table, six warmups and 24 timed calls per slice. Configurations
ran in shuffled order with a repeated default control. All checked result payloads/scores matched.
Default → mmap256 plus indexes median/p95 ms: docs 41.64/45.13 → 21.80/24.56; code 13.20/15.00 →
7.44/8.49; seed filter 24.75/26.57 → 1.85/2.03; CSS filter 7.41/8.78 → 0.93/0.95. B-tree indexes on
docs.kind and code.language were used by EXPLAIN QUERY PLAN and added 0.45 MiB. Fresh-process peak
RSS increased from about 37 to 175 MiB (including mapped file pages). Larger cache helped less;
1 GiB mmap, temp_store=MEMORY and the combined larger-cache configuration offered no clear extra win.
Raw results and executable probe: `/tmp/wf-vector-tuning-1xhbo/results.json` and
`/tmp/wf-vector-tuning-1xhbo.py`. These small-sample results are not cold-cache, p99, full-query,
concurrency or platform qualification. The first attempt failed in result-summary serialization;
the corrected rerun completed and is the reported receipt.

**Next isolated Stage 1B screening protocol (freeze before measurement):** compare native float32
and native int8 scalar cosine on the same current corpus with the carried-forward settings and
metadata indexes. Preserve physical row IDs and all payloads. Use sqlite-vec 0.1.9's fixed
`vec_quantize_int8(vector, 'unit')` for both stored vectors and queries; no fitted calibration or
model change. Reject nonfinite, out-of-unit-range and zero-norm float32 converter inputs. Validate
converted outputs as signed int8 with 384 dimensions/bytes and nonzero norm; the [-1,1] input range
does not apply to int8 outputs. Fail the screen rather than silently dropping invalid rows or queries. Explicitly tag BOTH stored/query BLOBs with
`vec_int8` at distance evaluation, verify `vec_type` and 384 dimensions, and reject a wrong-tag control.
Record the pinned converter's clipping/truncation behavior and verify native int8 distance against
an independent float64 cosine reference on the converted values. This is a native implementation
screen; unsupported int16/float16 and optional binary/rescoring remain explicitly unexecuted.

Use deterministic sampled stored vectors (seed 42, 30 per table), K=10/50/100/200 exact-neighbor
set overlap, and four timed slices (docs/code unfiltered, seed/CSS filtered). Alternate float32/int8
order, six warmups and 30 measured hydrated top-100 calls per slice; nearest-rank p95, no reliable
p99 claim. These self-query overlap diagnostics do not establish labeled recall or final relevance:
no eligibility or Stage 2 pass can be issued from this screen. Check keyed payload and vector-byte
identity, conversion/build time, full DB sizes and effective runtime/extension/config identity.
Bound this screen to ten minutes, 2 GiB additional disk, at least 10 GiB remaining free disk and
2 GiB process RSS; stop and retain partial results on a limit. No live index, installed dependencies,
production code or concurrent WAL writes are touched. The unpatched historical runtime may support
this isolated read-only search screen, but cannot qualify the pending WAL/concurrency work.

Readback: continue vector viability first, then shared-data integration only after the unchanged
quality gate passes. Ordered next actions: record tuning → independent readiness check of expanded
protocol → isolated quantization screen → preserve limitations and next qualifying experiment.
Existing AC-7/8 stay open until their full scale, quality, resource and runtime evidence exists.

### Native int8 screen results (2026-09-08)

The bounded Stage 1B screen completed on the same 36,742 rows and 384-dimensional embeddings.
Both lanes used mmap256, default cache and the same metadata indexes/payloads. Native conversion and
all keyed payload/vector representations passed verification; native int8 cosine agreed with the
independent float64 reference within 1.49e-8. Untagged int8 bytes were demonstrably interpreted as
float32[96], confirming why both operands must use vec_int8. No rows or queries were excluded.

| Measured item | Float32 | Int8 |
| --- | ---: | ---: |
| Complete experimental DB, MiB | 141.06 | 81.96 |
| Docs unfiltered median / p95, ms | 21.92 / 23.62 | 19.76 / 20.72 |
| Code unfiltered median / p95, ms | 7.32 / 7.99 | 6.45 / 7.47 |
| Seed filter median / p95, ms | 1.92 / 2.04 | 1.73 / 1.90 |
| CSS filter median / p95, ms | 0.93 / 1.08 | 0.82 / 0.94 |

Complete DB storage fell 41.9%; median query savings were about 10–12%, not a presumed 2–4x.
The float32 reference remained outside the int8 serving file, but both files were retained for this
experiment. Whole-screen peak RSS was 773.08 MiB, including simultaneous stores and independent
reference arrays; it is **not** a per-backend memory measurement. Build timings are single ordered
observations (float32 first), not a comparative ingestion qualification. Warm timing has 30 calls per
slice, alternating lane order, six warmups; query quantization occurs outside the timed region.
These timings include search/payload hydration but omit that preparation cost. No cold-cache or
meaningful p99 conclusion.

Mean top-100 exact-neighbor set overlap was 93.83% for documents and 93.63% for code (worst sampled
queries 87% and 88%). These are 30 deterministic stored-vector self-queries per table, not labeled
user-query recall; near-boundary/tie differences can affect overlap. K=10/50/100/200 samples and exact
runtime/configuration identities are preserved in [machine evidence](vector-screen-results.json),
alongside the earlier tuning screen and executable disposable probe sources. No indexed text or
vectors are included in that evidence file. Total screen elapsed 5.46 seconds, within frozen caps.

Independent retained-context evidence review by `vector_readiness` verified arithmetic, DB sizes,
script/source/extension hashes and representation/oracle controls without rerunning benchmarks. No
material flaw in the limited diagnostic conclusion; query-preparation exclusion is now explicit.
No new tag, public-query, reranker, lifecycle or migration qualification was inferred.

**Decision:** retain tuned float32 as the leading quality-preserving SQLite evaluation lane. Int8
is a promising optional space optimization, not selected for migration. Next qualifying work is the
unchanged labeled public-query comparison after a separately scoped reranker-stability repair; no
Stage 2 consolidation or production change follows from these diagnostic results. AC-7/8 and full
scale, cold-query, independent per-lane memory, incremental/WAL and final-quality work remain open.

## Quantization Evaluation Addendum (2026-09-08)

The operator confirmed **SQLite**, not MySQL. Extend this same change with an isolated quantization
track; no additional database service or production default is introduced. This is planned work,
with only the small in-memory capability probes below executed. Keep the existing stage names:

1. **Stage 1A — engine comparison:** unchanged float32 corpus and retrieval pipeline, baseline/latest
   Lance and SQLite. A float32 data column does not prove the ANN index itself is unquantized;
   record its actual index type, compression and refinement separately.
2. **Stage 1B — quantization:** compare SQLite float32 with native int8 first, after preserving the
   float32 measurements. Int16/float16 require an actually supported native search implementation;
   otherwise record unsupported, not an emulated speed comparison. Binary is optional and later.
   A measured quality failure in float32 remains visible; quantization does not waive it. Isolated
   probes may establish optimization potential, but require a complete passing candidate before
   any Stage 2 integration work.
3. **Stage 1 decision:** compare the best qualified SQLite configuration with production Lance and
   relevant latest-Lance alternatives under the same final quality, latency and resource gates.
   Then, and only then, **Stage 2** compares existing-data layouts and transactional consolidation.

### Released capability check

The documentation site currently labels itself `v0.1.10-alpha.4`; its examples alone cannot certify
stable 0.1.9. An in-memory probe using `/tmp/wf-vector-eval-1xhbo/bin/python`, SQLite 3.50.1 and
sqlite-vec 0.1.9 observed the following. It changed no files/indexes and is not a timing or concurrency
qualification; the patched-runtime requirement in the previous addendum remains in force.

| Format / operation | Actual 0.1.9 observation | Evaluation disposition |
| --- | --- | --- |
| float32 | Existing baseline; four dimensions occupy 16 bytes | Primary unquantized control |
| int8 | `vec_int8`, scalar cosine and `vec0(... int8[4] distance_metric=cosine)` work; two-row KNN materializes distances 0 and 0.3333333433 | First quantized candidate; benchmark native filtered scalar and applicable vec0 paths |
| Quantizer API | `vec_quantize_int8('[0.1,-0.2,0.3,-0.4]', 'unit')` returns `[12,-26,37,-51]`; `vec_quantize_i8` is absent | Pin the actual callable API and conversion semantics, not the unfinished API-reference spelling |
| int16 | `vec0(... int16[4])` is rejected | Unsupported in tested release; reassess only when a released native implementation is verified |
| float16 | Declaration accepted but 8-byte/four-float16 payload rejected as two dimensions; 16-byte float32 payload accepted and reported as float32; `vec_quantize_float16` absent | Not native float16 support; declaration success is insufficient evidence |
| binary | Documented packed-bit/Hamming path | Optional separate metric/representation experiment; no claim of cosine equivalence |

`vec_debug()` reports commit `e9f598abfa0c06b328d8fe5da9c3760cce74be10`, build date
2026-03-31 and `neon`. This is a build flag, not proof that every int8 distance kernel is vectorized.
Inspect the pinned kernel and measure actual execution on target hardware; do not promise 2–4x
throughput from byte counts. Sources: [sqlite-vec API](https://alexgarcia.xyz/sqlite-vec/api-reference.html),
[scalar-quantization guide](https://alexgarcia.xyz/sqlite-vec/guides/scalar-quant.html).

### Measurement and quality contract

Freeze conversion/calibration, clipping, rounding, zero-vector handling, query conversion and
normalization before quality measurements; fit calibration on a separate representative corpus,
not the evaluation answers. Persist quantizer identity/parameters with embedding identity. Verify
int8 BLOB round trips and distance-function type interpretation explicitly. Compare native quantized
distances with an independent reference on those quantized values; report their distortion relative
to original float32 separately. The float32 cross-engine 1e-5 equality rule does not assert that lossy
int8 conversion preserves original distances to 1e-5.

Measure both **nearest-neighbor set overlap** against exact float32 and **relevant-document recall**
against the labeled query corpus; those are different metrics. Report K=10/50/100/200 where applicable,
and the actual per-query candidate budget, dense candidate pool, post-fusion reranker input and final
results. These diagnostic K sweeps do not increase production candidate limits. Keep the same queries,
filters, fusion, reranker/provider and final top-K. A reranker cannot recover excluded relevant chunks.
Use paired runs and include the known CPU reranker batch-sensitivity fixture; do not interpret a
candidate-pool change as storage precision alone or treat reranking as guaranteed compensation.

Preserve the current no-regression final-quality requirement. Report candidate-recall deltas and
per-fixture losses explicitly; the operator's illustrative 98.7%/98.3% example is not a numeric loss
budget. Predeclare candidate-recall acceptance at readiness; absent an explicit relaxation, do not
certify a candidate with lost required relevant candidates. Exact-neighbor ordering/overlap is a
separate diagnostic, not interchangeable with labeled relevance. Any different loss tolerance needs
an explicit decision before results, rather than quietly changing the existing gate.

Report raw and complete database/index size, RSS, CPU time, cold/warm hydrated query p50/p95/p99,
full hybrid latency and final relevance, conversion/build cost, incremental write throughput and WAL/
maintenance/backup cost. Apply the same bounded scale ladder and report whether the qualifying
crossover interval moves; do not extrapolate a larger capacity from compression ratios alone.

The current evaluation uses **384 dimensions**; the operator's 1,536-dimension examples are illustrative.
Raw payload arithmetic for one million 384-dimensional vectors (excluding all metadata/index overhead):

| Representation | Bytes/vector | Raw payload (MiB) | Status |
| --- | ---: | ---: | --- |
| float32 | 1,536 | 1,464.84 | Baseline |
| int16 or float16 | 768 | 732.42 | Theoretical; not supported natively in the tested extension |
| int8 | 384 | 366.21 | Candidate |
| packed binary | 48 | 45.78 | Optional candidate |
| int8 plus retained float32 | 1,920 | 1,831.05 | Optional rescoring design; 125% of float32 raw bytes |

Start with int8-only serving plus the unchanged reranker; retain the experimental float32 reference
outside that serving-store measurement. Separately account for every persistent original retained by
any deployable design. Optionally test int8 candidate generation plus float32 rescoring, with bounded
oversampling, original-vector fetch/decompression and full storage costs charged to that lane.
Rescoring cannot recover candidates excluded by the quantized first stage. Original-vector retention,
re-embedding/rollback cost and crash-safe publication of any dual representation must be explicit.

Avoid favoring one backend through unequal tuning. [Lance documents quantized ANN alternatives](https://docs.lancedb.com/indexing/quantization);
verify their availability in the exact embedded release and preserve existing ANN/refinement evidence.
A best-SQLite comparison must not describe production Lance as an unquantized scan merely because
its stored source vectors are float32. No custom int16 kernel, extra vector extension or model change
is implicitly authorized by this quantization track.

## CPU Reranker Follow-up (2026-09-08)

Scoped bug plan [1xj6n](1xj6n-bug%20cpu-reranker-batch-stability.md) records the reproduced
CPU peer-composition defect and unchanged golden-corpus diagnostic. Single-passage INT8 scoring
removes peer variation without changing weights or candidate limits, but 3/55 query-tool pairs
regress versus original production, 5 improve and 47 remain unchanged. The losses are the supporting
.aiignore citation, supporting .gitignore rank8→9, and INT8-composition source rank9→10. Both named-file
primary writers remain first. FP32 also loses the aiignore support in the targeted query.

The full singleton Lance run contains165 measured calls; SQLite singleton and FP32 have targeted
query checks only. Existing receipt validators verified corpus/generation/fixture identity and trace
completeness. Full evidence and override identities are in `vector-screen-results.json`. The static
singleton shape was asserted1x512; inherited logging still reports40x512 and is not shape evidence.

No production fix is selected under the standing strict no-regression gate. Accepting singleton's
specific ranking changes requires an explicit operator acceptance revision. Until then, preserve the
current default and do not begin Stage2, change vectors/dependencies or silently reset the baseline.
The new bug remains staged, with no code edits, admission or readiness claimed for that production fix.

## Prior Reviewed Outcome (before the operator addendum)

**Retain the installed LanceDB 0.33.0 backend for now.** SQLite scalar satisfies the measured
vector, filtering, resource and lifecycle budgets, but does not pass the strict public relevance
gate. Stage 2 was not started. This is a measured retrieval-pipeline limitation, not a finding that
SQLite cannot provide the required vector storage. No production backend, dependency pin or recovery
behavior changed. Required specialist and council delivery reviews passed; operator closure is not requested.

Four full public-path runs used the same current isolated generation 1028: 27,995 docs chunks,
8,747 code chunks, 35 fixtures, 55 applicable fixture/tool pairs, three measured repetitions each.
Each lane ran 138 semantic calls with actual CPU embedding and reranking, plus 27 lexical-only
controls. Canonical corpus, health,
generation and source checks remained intact. The SQLite adapter replaced dense search only; it
did not claim to be a production SQLite integration or forge readiness. Evidence:
`tests/fixtures/vector_backend_eval_1xhbo_public.json` under the framework scripts directory;
raw results/traces remain under `/tmp/wf-vector-eval-1xhbo-public-*`.

| Public path | Baseline ANN median / p95 (ms) | Latest ANN median / p95 (ms) | Latest exact median / p95 (ms) | SQLite scalar median / p95 (ms) |
| --- | --- | --- | --- | --- |
| code_ask | 3,974 / 7,237 | 4,139 / 5,579 | 3,973 / 4,878 | 4,195 / 5,898 |
| code_search | 773 / 1,089 | 884 / 1,056 | 823 / 898 | 858 / 1,149 |
| docs_search | 660 / 698 | 833 / 1,313 | 780 / 864 | 760 / 820 |
| code_lexical | 14 / 29 | 19 / 37 | 18 / 33 | 19 / 32 |

These are descriptive shared-host observations, not causal backend speed claims. The live project
performed background indexing during this work; the experimental corpus stayed frozen. All measured
providers matched CPUExecutionProvider. Candidate child GPU probes did not inherit the shared site
path, so cold model warmups are not a fair cross-environment startup comparison; the earlier isolated
fresh-process resource tests cover storage/import startup only, not full-query cold model
initialization. Nine docs-search samples make its p95 the maximum.
Canonical absolute-latency review flags remain in the receipts; no invented 10% acceptance rule was used.

Latest ANN had **zero per-repetition relevance changes**. Both exact paths had the same one-fixture
regression in all three repetitions: “Which function writes the .aiignore file?” retained the correct
`render_aiignore` declaration at rank 1, but lost the secondary `.aiignore` source at rank 9. Recall
fell 1.0 → 0.5 and nDCG 0.95676808 → 0.91731941. Six reported metric failures represent two metrics
across three repetitions of one case, not six separate bugs. All other fixture metrics and
abstention/classification checks were preserved.

SQLite's slowest individual hydrated dense call was 73.19 ms. Median cumulative vector work across
all dense calls in one code_ask was 64.99 ms (baseline 28.34 ms); cumulative p95 was 124.30 ms because
some requests issue multiple searches. The previously declared individual vector slices all retain
their below-100 ms result. All four public filter smoke lanes passed 13 cases plus invalid-kind
rejection, including prefiltering, nonempty/OR/quoted/wildcard/case-sensitive tags and duplicate IDs.
Those fixtures explicitly stub loading, embedding and identity reranking; they establish public
predicate contracts, not model quality or publication behavior.

### Where the quality difference occurs

The focused trace proves that `.aiignore` is retrieved at dense rank 6 with the same text and cosine
score in ANN, exact Lance and SQLite. It reaches reranking at the same position. ANN's merged pool
contains 128 candidates; both exact pools contain 127. The file's CPU reranker score changes from
0.35932 to 0.33444, below the competing code chunk near 0.337, and final selection drops it. Exact
Lance and SQLite have identical dense candidate identities in this probe, with score differences
below 6×10⁻⁷.

A separate actual CPU INT8 reranker probe held query, passage and position fixed while changing only
the other 39 passages. Two repetitions per condition yielded identical within-condition scores but
different scores across conditions: 0.29823 / 0.28086 / 0.30324. This demonstrates batch-composition
sensitivity in the tested CPU pipeline. It does not establish a particular quantization operator as
the cause or imply the same behavior on GPU. No answer-specific injection or changed quality budget
was used to make an exact backend pass.

### Scoped follow-up and resumption criteria

Investigate CPU reranker stability in `accel_embedder.py:StaticShapeReranker.rerank` and final agent
selection in `server_impl.py`. Add a fixed-passage/changed-peer regression control, characterize the
CPU precision/batching trade-off, and verify identical queries under varied candidate order, count
and batch boundaries. Avoid a special case for `.aiignore`; keep current candidate limits, model
identity and relevance requirements unless a separately planned change explicitly revises them.
Re-run the unchanged 35-fixture comparison after the repair. Only an evidenced Stage 1 pass permits
the separate-vector-store versus colocated-registry/FTS layout experiment. No Stage 2 schema or
migration work is delivered by this evaluation.

Latest Lance ANN is a qualified retrieval candidate, not an approved destination upgrade. Its new
Linux wheel floor and unexecuted platform/runtime and old-index upgrade/rollback qualification remain
gaps. The historical list-offset stress probe still did not reproduce the baseline defect, so its
workaround stays. Future adoption must follow the existing standard `wf_upgrade` design below;
neither a timing win nor roadmap work authorizes removing the old store or shared dependencies.

## Current Budget and Evaluation Status (operator revision, 2026-09-08)

The operator clarified that vector retrieval below **100 ms** is acceptable because reranking
accounts for much of the overall query time. The prior relative vector-step limit was stricter
than the intended user outcome. Use **median and p95 below 100 ms per declared hydrated vector
query slice**, preserving the same corpus, predicates, candidate counts and correctness checks.
Measure full query latency with embedding, vector retrieval, payload handling and reranking broken
out; report both the vector share and total-query delta against baseline. The assertion that the
difference is below 10% of total query time requires measurement, not inference from vector timing.
Cold process startup remains separate from warmed vector retrieval. Other parity, lifecycle,
resource and deployment gates remain in force unless explicitly revised.

On continuation, use the operator's explicit below-100 ms vector ceiling and report full-query
latency without inventing an additional 10% pass/fail threshold. The earlier percentage question
was coordinator-proposed, not an operator requirement; its non-answer is not treated as approval.
Freeze this measurement rule before full-query results: report paired total median/p95 and phase
breakdown, retain strict relevance/contract gates, and flag any material total slowdown in the
viability verdict. Stage 2 still requires an evidenced Stage 1 pass; production adoption remains
conditional on complete parity and a readied concrete implementation scope.
The measured boundary is the public tool call, using identical query fixtures, candidate budgets,
embedding/reranker identities and cache conditions. Record separate phase timing without excluding
hydration, adaptive candidate refill, lexical work or reranking from the total.

This budget changed **after** the first measurements at the operator's direction. Preserve the
original receipt and thresholds as historical evidence; apply this revision explicitly to retained
samples and freeze it before new evaluation. The original no-change decision is **superseded**,
not a current rejection of SQLite or LanceDB 0.38.0.

Reassessment of every recorded warm slice (not only the unfiltered example):

| Measured path | Highest recorded p95 | Revised vector-latency result |
| --- | --- | --- |
| LanceDB 0.38.0 | 24.82 ms | All tested slices below 100 ms |
| SQLite ordinary-table scalar cosine | 81.97 ms | All tested slices below 100 ms, including 2x growth |
| vec0 KNN with scalar filtering on auxiliary columns | 276.46 ms | Tag fallback still over budget: docs OR tags 138.63 ms, growth OR tags 276.46 ms, growth quoted tag 153.86 ms |

SQLite therefore remains viable for continued evaluation through the scalar path. The native
auxiliary-column fallback's failure does not disqualify a different released path that satisfies
the same filtering contract. **Stage 1 is now not passed on relevance:** the full-query continuation above completed the local
lifecycle/resource and public-path checks, then found the shared exact-search/CPU-reranker quality
gap. The two existing-data layouts remain untested under the sequencing rule. The amended wave was
re-prepared before code edits. The installed backend stays unchanged.

## Comparison Coverage and Long-Term Decision (operator clarification)

The comparison must evaluate the best relevant released capabilities of both systems, rather than
compare only today's Lance configuration with the first SQLite prototype. Recheck latest stable
package and underlying-engine versions before the next measurement round; retain 0.33.0 as the
installed baseline. Any newer release gets a separate versioned result, never relabeled old data.

| Comparison lane | Required evidence |
| --- | --- |
| LanceDB installed and latest stable | Current production ANN configuration plus exact vector search with explicit index bypass; evaluate supported scalar metadata indexes where existing predicates benefit. Distinguish query bypass from omitting ANN index construction entirely when measuring build/maintenance savings. |
| SQLite latest stable extension | Specialized vec0 KNN and ordinary-table exact cosine SQL; preserve all predicates before top-k and fully hydrate equivalent payloads. Compare supported partition/metadata options only within Stage 1 vector viability scope, not as premature existing-data layout design. |
| Relevant released optimizations | Inventory filter pushdown, projection/batching, index options, precision/quantization and rerank hooks. Give each a test or an explicit applicability disposition; bound configurations and freeze tuning before measurement. Quantized candidates retain original vectors for verification/refinement and must pass quality gates; no embedding-model change or silent default substitution. |
| End-to-end behavior | Same query/candidate fixtures, embedding and reranker, including selective/nonempty tag cases, citations, duplicate identities, relevance and total latency. Separate quality-equivalent exact comparisons from ANN speed/recall trade-offs. Apply the 100 ms vector ceiling and report reranking-inclusive latency. |
| Operational cost | Platform/CPU compatibility, extension loading, full installed dependency closure, backend-only memory, update/reclamation/recovery, format/API compatibility and upgrade/rollback. Distinguish prototype scaffolding from production adapter and migration work. |
| Existing-data integration | Only after a complete SQLite Stage 1 pass, compare at least two layouts using existing registry/FTS/state workloads, query plans, hydration, transactions and failure boundaries. Measure simplification and total-query cost, not table count alone. |

For every potentially relevant capability, record: exact release/API, available local/open-source
versus hosted-only surface, current use or benefit, measured evidence or reason not exercised,
and any additional dependency or migration burden. Hosted/distributed features receive no adoption
credit unless they affect the local embedded implementation. Thorough means every material capability
has a disposition, not that every upstream feature needs a benchmark.

### Roadmap evidence and decision sensitivity

The final comparison includes a long-term section for each backend. Each item records its official
source, last-checked date, status (stable release / prerelease / merged but unreleased / active PR /
proposal), relevant local benefit, API/storage compatibility implications, confidence and a concrete
re-evaluation trigger. Dates are upstream targets only; absent or stale schedules stay unknown.
Experimental probes, if justified, use separate disposable environments/results and cannot certify
stable adoption. Report whether the recommendation still holds if every roadmap item slips or is
cancelled, and whether waiting for a specific release would materially improve the decision.

Initial watchlist checked 2026-09-08; verify exact release inclusion before giving shipped credit:

Rechecked the current package pages on 2026-09-08: [LanceDB](https://pypi.org/project/lancedb/)
still publishes 0.38.0 as latest stable, and [sqlite-vec](https://pypi.org/project/sqlite-vec/)
still publishes 0.1.9. The separate [lancedb-compat 0.38.0](https://pypi.org/project/lancedb-compat/)
ships one Linux x86-64 wheel requiring glibc 2.28 or newer. It uses an older x86 CPU baseline and
runtime SIMD dispatch, but occupies the same Python namespace as lancedb: the two packages conflict
and must not be installed together. It does not supply macOS Intel or Windows compatibility wheels.
This is a released packaging alternative with unexecuted host compatibility, not evidence that our
supported-platform gaps are resolved. Ordinary 0.38.0 wheels cover macOS ARM64, Linux ARM64/x86-64
and Windows x86-64; the Linux glibc floor and CPU requirements need destination qualification.

| System and direction | Why it may matter here | Evidence status and next check |
| --- | --- | --- |
| sqlite-vec IVF/DiskANN experiments | A possible faster path if local repositories outgrow exact scans; compare recall, filters, incremental writes and recovery, not only unfiltered speed | [0.1.10-alpha.4](https://github.com/asg017/sqlite-vec/releases/tag/v0.1.10-alpha.4) documents fixes involving these experimental paths. No stable eligibility credit until released and tested. |
| sqlite-vec shared ARM NEON cosine work and ANN benchmarking | Potentially improves exact distance calculations on local ARM machines as well as ANN; could change the scalar/native cost comparison | [Upstream TODO](https://raw.githubusercontent.com/asg017/sqlite-vec/main/TODO.md) lists the shared NEON optimization as unfinished and branch benchmark consolidation. This is engineering intent, not a dated release commitment. |
| Lance segmented index model | Potential impact on incremental indexing, maintenance and search across fragments | [Current LanceDB-team roadmap for Lance](https://github.com/lance-format/lance/issues/7290) describes completion work; inspect released engine/API behavior and remaining implementation gaps. |
| Lance stability, memory and temporary-space bounds | Directly relevant to reliable local setup, compaction and update workloads | Same [roadmap](https://github.com/lance-format/lance/issues/7290) prioritizes these bounds; require concrete fixes and measurements, not a general stability promise. |
| Lance transactions, conflict handling and merge-insert efficiency | Could simplify safe updates and reduce memory/maintenance costs, but format changes may complicate rollback | [Active milestones](https://github.com/lance-format/lance/milestones) track unfinished work; verify exact commits/releases and old-reader/write compatibility. |
| Lance blobs/branches and broader feature growth | Lower priority for our current text/code-vector workload; may create future options but also adds API/format surface to maintain | The roadmap describes these directions; give an explicit current-use disposition rather than counting them as automatic advantages. |

Milestone bookkeeping is not proof of availability: sqlite-vec's milestone page still contains old
0.1.7/0.1.8 targets despite later releases; the old Lance WIP roadmap is closed. Prefer current release
artifacts and the active issue/PR chain. Also audit maintainership activity, unresolved correctness
bugs, breaking-change policy, release cadence and platform packaging so the long-term recommendation
accounts for maintenance risk as well as promised functionality.

## Requirements

1. Inventory every current LanceDB use and its observable contract from code and tests before selecting a SQLite schema. Map each to native support, application-side implementation, or a blocking gap. Include docs/code storage, vector/metadata round trips, cosine distances and public scores, kind/language/tag predicates before top-k, candidate budgets, deterministic tie handling, reranking, citations, lexical fallback, incremental changes, and maintenance/health APIs. Keep the embedding model and query fixtures identical across candidates.
2. Resolve and freeze exact versions at evaluation start, including the underlying Lance engine, Python SQLite runtime, extension, and transitive packages. As of 2026-09-08, upstream latest stable release pages identify LanceDB 0.38.0 and sqlite-vec 0.1.9; recheck before running. Evaluate released capabilities separately from prereleases and roadmaps. Do not base required parity on promised ANN, filtering, or reclamation work.
3. Use isolated environments and disposable index copies. Compare the baseline and both candidates on a small fixture, the representative current corpus, and a bounded growth corpus whose sizes are recorded before measurement. SQLite evaluation must compare `vec0` filtered KNN with an exact SQL/scalar-distance fallback if needed; filtering after a bounded top-k is not equivalent. Include selective/combined predicates, multiple tags with OR semantics, empty matches, quotes, ties, and large requested candidate counts.
4. Preserve retrieval quality and public tool behavior. Use identical float vectors and an independent exact cosine reference, predeclared floating-point/tie tolerances, and existing relevance evaluations. Require no relevance-metric regression or contract violation. Record cold/warm query p50/p95, peak memory, startup, full build, incremental update, maintenance time, disk growth, and dependency footprint. Record numeric acceptance thresholds from existing budgets and the baseline before examining candidate results; do not relax them to admit a preferred backend.
5. Exercise repeated append/delete/compact cycles and the historical Lance list-offset failure. Distinguish prevention from reading/reclaiming already affected data; a baseline that does not reproduce the defect is inconclusive. Probe SQLite deletion, VACUUM/reclamation, interrupted writes, rollback, reader/writer contention, and process restart. Verify vector, metadata, FTS, and index-state publication consistency; sharing SQLite storage must not silently weaken existing authority or locking boundaries.
6. Measure simplification rather than assuming SQLite removes all dependencies. Audit LanceDB, PyArrow, and other transitive dependencies for remaining consumers; account for the sqlite-vec binary, extension-loading support, packaging, licenses, and any new adapter code. Verify supported Python and macOS, Linux/WSL2, and native Windows combinations, including available wheels and extension loading. Missing platform execution evidence must be explicit and cannot count as success.
7. Review both projects' release notes, open defects, maintenance activity, compatibility policy, and documented roadmap. Apply Comparison Coverage and Long-Term Decision: assess exact and approximate modes, released optimizations, stage-specific integration, evidence maturity, and a recommendation that remains valid if roadmap items do not ship. Separate local embedded capabilities from hosted/enterprise features and shipped features from proposals. Evaluate roadmap relevance to local repository workloads, not feature count. Correct the local compaction reference only from verified upstream and reproducer evidence; retain the Lance workaround unless its removal is independently justified.
8. Produce a decision comparing upgrade, migration, and no change against the same gates. For any selected implementation, specify file-level scope and destination upgrade behavior: existing-index detection, conversion versus rebuild, embedding reuse, space/time requirements, interrupted-upgrade recovery, rollback, and when obsolete stores/dependencies can safely be removed. Preserve the standard `wf_upgrade` path. Implement only the selected, evidenced option after its concrete scope meets readiness; if evaluation exposes materially larger migration work, record a separately scoped implementation follow-up rather than silently expanding this wave.

## SQLite Evaluation Sequence

**Stage 1 — vector-store viability.** First evaluate sqlite-vec in isolation with representative vectors and only the metadata needed to exercise the current retrieval contract. Prove correctness, filtering, performance, mutation/recovery behavior, and platform/dependency feasibility against the declared gates. Record a pass, fail, or inconclusive result with evidence before beginning Stage 2. A fail or inconclusive result stops SQLite integration evaluation; continue the LanceDB comparison and record the blocker. Do not optimize a combined schema to compensate for an unproven vector store.

**Stage 2 — efficient integration with existing data (only after Stage 1 passes).** Inventory the existing SQLite data, keys, ownership, FTS, metadata, and index-state consumers. Compare at least two viable layouts: a separate vector store linked by stable IDs, and vector tables colocated with existing data using shared IDs and SQL joins. Evaluate selective metadata duplication/partitioning only where measurements justify it. Do not assume one file or fewer tables is inherently faster.

Use equivalent end-to-end search and update workloads to compare query plans, filter placement, joins and result hydration, SQL/Python round trips, repeated scans, serialization/copies, duplicated data, transactional write cost, lock contention, memory, disk use, and build/update/recovery time. Define layout-comparison budgets before measurements. Select the most efficient measured layout for representative local workloads that preserves all correctness and authority boundaries, documenting trade-offs and rejected layouts; microbenchmark wins alone do not establish the best integration. Re-run retrieval parity and recovery checks on the selected layout before SQLite can be recommended over LanceDB. Keep both stages' evidence in this change doc and the existing ledger.

## Execution Protocol (original experiment; timing gate revised by operator)

The evaluation harness is development-only at `.wavefoundry/framework/scripts/tests/vector_backend_eval.py`; its focused contract tests belong at `.wavefoundry/framework/scripts/tests/test_vector_backend_eval.py`. The companion `vector_lifecycle_eval.py` in the same development-only directory measures fresh-process startup and three paired Lance lifecycle cycles. Store reproducibility parameters and compact machine results beside test fixtures, and keep corpus copies, package environments, and raw logs under `/tmp/wf-vector-eval-1xhbo*`. Do not ship evaluation dependencies or copy live index data into tracked fixtures.

Stage 1 measures vector retrieval plus the same minimal ID/path/kind/language/tags/text payload on every backend. It does not compare bare distances with fully hydrated Lance rows. Storage-only times are reported separately from end-to-end retrieval and never establish adoption by themselves. A Stage 1 pass requires intrinsic correctness/filter/candidate parity, measured local performance within the declared limits, successful local failure probes, and distribution feasibility for supported targets. Missing nonlocal runtime evidence remains an adoption gap even if wheel availability permits Stage 2 experimentation. Architecture-dependent uncertainty is inconclusive, not a pass.

| Gate | Predeclared rule |
| --- | --- |
| Correctness | Zero metadata/vector round-trip mismatches; cosine absolute error at most 1e-5 against float64 reference; ties within 1e-5 compared as equivalent boundary sets; no filter violation or lost eligible results |
| Retrieval quality | No decrease in per-fixture or aggregate required relevance metrics; exact candidate overlap must not decrease from baseline; public contract tests retain candidate limits and score conversion |
| Timings | At least 2 warmups and 7 measured repetitions per fixed query slice; current operator limit: warm hydrated vector median/p95 below 100 ms. Report full query latency including reranking and its phase breakdown. Original 1.10x/+2 ms vector limit remains only in the historical receipt. Cold startup/retrieval remains at most 1.25x baseline (allow 100 ms noise floor), measured separately. |
| Build/update/maintenance | Median at most 1.25x baseline across 3 paired cycles; report vector storage separately from embedding time; zero extra embedding calls when stored vectors remain compatible |
| Resources | Peak RSS and post-maintenance storage at most 1.25x baseline; plateau after 10 bounded churn cycles, with no lost live rows; dependencies and migration working-space cost reported separately |
| Corpora | 512-row deterministic fixture, full frozen docs/code tables from a disposable snapshot, and 2x current rows using unique IDs and deterministic duplicates; record actual row counts and hashes before candidate measurements |
| Failure probes | Finite set: rolled-back transaction, process exit before commit, reader during write, lock contention with bounded timeout, reopen after maintenance, and 10 add/delete/compact cycles; original Lance corruption is inconclusive unless the baseline actually reproduces it |
| Decision | Any proven required failure disqualifies adoption; incomplete evidence permits a documented no-go/follow-up, not a weakened gate or a silent scope reduction |

For an over-budget provisional SQLite path, classify viability as inconclusive unless the failure is isolated to a required released capability or reproduced across the declared viable Stage 1 paths. Both outcomes stop Stage 2; neither permits a blanket claim that SQLite cannot work.

| Failure boundary | Required observation |
| --- | --- |
| Insert/replace/delete interrupted before commit; then process restart | Last committed IDs, metadata, and vectors remain equal; uncommitted rows never appear |
| Reader during writer; contention below/above bounded timeout | Coherent committed snapshot, bounded wait or explicit busy failure, no data damage |
| Registry/FTS transaction exception (existing baseline contract; repeat on any Stage 2 integration) | Registry, FTS payload, and digest roll back together; keyed payload checks, not only counts |
| Build fence, vector mutation, derived commit, pre/post publication (Stage 2 integration) | Mixed generations never served as complete; changed reader token discarded and stale writer completion refused |
| Reopen and repeat recovery/rollback after completed update | Stable keyed payload/vector equality and idempotent recovery, or explicit refusal without silent success |
| Interrupted reclamation or destination migration (conditional integration) | Prior coherent store recoverable and no cleanup before verified publication |

Stage 1 exercises the isolated-store rows for docs/code-shaped records; baseline publication contracts are grounded in existing tests. Stage 2 repeats integration-specific rows only after viability passes. Every unexecuted row carries a reason and limits the eligibility claim.

These are engineering comparison tolerances, not a relaxation of semantic parity. Stage 2 will freeze layout-specific budgets before its first measurements, keeping the end-to-end gates above. Verify corpus consistency before benchmarking; if an atomic live export is unavailable, record version-bound per-table snapshots and their limitations rather than claiming cross-store atomicity. A no-go can stop expensive downstream probes once decisive evidence exists, but all omitted measurements must be recorded as not run and cannot support a complete comparison claim.

## Scope

**In scope:** capability inventory, isolated prototypes and comparative evaluation, current compaction defect investigation, dependency/platform audit, roadmap assessment, decision and migration design, and conditional focused implementation of the selected option.

**Out of scope:** hosted databases, network services, production million-vector support guarantees, embedding-model changes, new user-facing search capabilities, a permanent configurable multi-backend architecture, unrelated release work, automatic packaging or publication. Planning this wave does not authorize changing the live index or installed tool environment.

## Acceptance Criteria

- [x] AC-1: A code/test-linked capability matrix accounts for every current LanceDB use and identifies native support, required adaptation, or a blocker for both candidates; released capabilities and roadmap claims are clearly distinguished.
- [~] AC-2: A reproducible three-way evaluation records frozen versions, corpus/query/vector fixtures, commands, predeclared tolerances and numeric budgets, and results for retrieval quality, filtering, latency, memory, build/update/maintenance time, disk growth, and dependency footprint. A candidate can be reported eligible only if it meets all parity gates; failures remain visible. — 2026-09-08 closure reconciliation by coordinator following operator selection of FP32 and conversion planning: frozen three-way and corrected two-way current-corpus evidence is retained; a fully refreshed three-way scale/resource qualification is not claimed. Production envelope and adapter comparisons continue at 1xjmm G1/G3.
- [~] AC-3: Failure and maintenance probes record the historical Lance defect outcome and both candidates' mutation, reclamation, contention, restart, and publication behavior. An untriggered baseline is marked inconclusive, and no workaround is retired without evidence. — 2026-09-08 coordinator scope discovery: mutation/reclamation/reopen probes completed for both stores; rollback, interruption-before-commit and contention probes were SQLite-only. The baseline corruption did not reproduce. Lance interruption and actual destination migration/rollback remain unexecuted. The corrected Stage1 gate now permits the bounded integrated SQLite publication probes recorded above; those passed. Production adoption remains unqualified; baseline publication contracts remain covered by the framework suite.
- [~] AC-4: The decision records supported-platform evidence, dependency and maintenance trade-offs, a source/status-linked roadmap assessment with re-evaluation triggers and a no-roadmap-delivery scenario, and a concrete destination upgrade/recovery/rollback design. The latest relevant released capabilities, including Lance exact/ANN and both SQLite paths, each have measured evidence or an explicit applicability disposition; missing evidence and blocking gaps are explicit. — 2026-09-08 closure reconciliation by coordinator: capability/roadmap/dependency audit and upgrade design are recorded; supported-platform execution and actual destination recovery remain unqualified and are carried into 1xjmm G1/G4/G5 and proposed ADR 1xjmn.
- [x] AC-5: The selected outcome is delivered consistently: a focused upgrade/migration with its own integration and destination smoke evidence, a scoped implementation follow-up when migration exceeds readiness, or an explicit no-change decision. No backend switch or dependency removal precedes proof of required parity; edited user guidance matches the delivered outcome. — Scoped follow-up delivered as admitted conversion change 1xj6o in wave 1xjmm, with G0–G6 and proposed ADR 1xjmn; production Lance storage and dependencies remain unchanged.

- [x] AC-6: SQLite integration evaluation begins only after an evidenced Stage 1 viability pass. If passed, at least two viable data layouts are compared against predeclared budgets using existing-data query and update workloads, and the selected layout has measured efficiency, parity, and recovery evidence. Otherwise the Stage 1 blocker and the reason Stage 2 was not run are recorded; no SQLite migration is recommended.

- [~] AC-7: The scale/configuration extension records versioned implementation identities, representative workload measurements and a bounded crossover interval or explicit not-reached/not-run limits; new WAL concurrency qualification uses a verified patched SQLite runtime. Configuration and atomic consolidation benefits are credited only to their measured stage, with prior results preserved. — 2026-09-08 closure reconciliation by coordinator: bounded tuning and patched-runtime shared-transaction experiments completed, but no large-corpus crossover was established. Representative scale and production memory/availability limits remain mandatory in 1xjmm G3; no million-vector capacity claim.

- [~] AC-8: The separate quantization track records native format support, frozen conversion semantics, candidate-pool and final-quality results, full resource/crossover measurements, and a supported or explicitly unsupported disposition for float32/int8/int16/float16; optional binary/rescoring results remain separate. No quality relaxation or integration is inferred from compressed size alone. — 2026-09-08 operator accepted FP32 for conversion and quantization as a separate optimization. Native INT8 capability/storage/timing and self-query overlap screen completed; labeled candidate recall, final reranked quality, per-backend RSS and scale qualification were not completed. INT8, binary and 16-bit alternatives are not selected; revisit only as separate qualified work.

## Tasks

- [x] Verify released SQLite quantization capability and distinguish native storage/search support from misleading declaration/API examples.
- [~] Prepare the separate Stage 1B quantization protocol with fixed conversion, candidate-recall criteria and native execution proof. — 2026-09-08 closure scope reconciliation: Bounded screen protocol executed; broader labeled-quality protocol deferred with AC-8 under the FP32 decision.
- [~] Benchmark float32 versus int8, record unsupported 16-bit formats, and assess optional binary/float32-rescoring only as separately costed lanes. — 2026-09-08 closure scope reconciliation: Native diagnostic screen recorded; optional rescoring and full quantization qualification deferred with AC-8.
- [~] Compare the best qualifying SQLite configuration with baseline/latest Lance and update measured crossover limits without bypassing Stage 2 prerequisites. — 2026-09-08 closure scope reconciliation: Corrected current-corpus Lance0.33/FP32 parity completed; refreshed latest-Lance/scale crossover qualification is carried into conversion G3.

- [~] Freeze and review the addendum protocol, including scale limits, sample counts, effective configuration controls and patched SQLite runtime/dependency provenance. — 2026-09-08 closure scope reconciliation: Bounded tuning/shared-layout protocols reviewed and executed; broader scale/platform qualification remains in conversion G1/G3.
- [~] Execute the bounded Stage 1 scale/configuration extension and record crossover bounds, unresolved quality/runtime gates and unexecuted probes. — 2026-09-08 closure scope reconciliation: Configuration and current-corpus evidence retained; larger scale ladder not executed, transferred to conversion G3.
- [x] If Stage 1 passes, extend AC-6 layout measurements with transactional FTS/vector/state consistency, batching, file-change publication and maintenance workloads; otherwise record why these remain unrun.

- [x] Inventory current backend contracts and freeze candidate versions, fixtures, tolerances, and numeric performance gates.
- [x] Build isolated LanceDB and SQLite comparison paths using identical stored vectors and metadata.
- [x] Re-freeze latest stable versions and compare LanceDB exact/ANN with SQLite vec0/ordinary-table exact paths; disposition other relevant released optimizations before bounded measurements.
- [x] Run retrieval, predicate, relevance, performance, and dependency-footprint comparisons.
- [~] Run compaction, mutation, crash/restart, contention, and publication/recovery probes. — 2026-09-08 coordinator: both stores have mutation/reclamation/reopen evidence; isolated rollback/interruption/contention coverage is SQLite-only. Lance interruption/destination rollback and actual SQLite migration remain unexecuted. Bounded integrated SQLite publication probes now passed in Stage2, as detailed above; this does not cover live migration.
- [x] Complete the refreshed capability/platform/upstream audit and long-term roadmap assessment, including maturity, migration costs, re-evaluation triggers and a no-roadmap-delivery scenario.
- [x] Record the SQLite Stage 1 viability verdict before starting existing-data integration evaluation.
- [x] Only after a Stage 1 pass, inventory existing data/keys and compare at least two integration layouts with predeclared end-to-end efficiency budgets; otherwise record why this conditional step is not run.
- [~] Verify the chosen SQLite layout's retrieval parity and recovery, and carry its end-to-end results into the final LanceDB comparison; record non-applicability if Stage 1 blocks SQLite. — 2026-09-08 closure scope reconciliation: Prepared-layout parity/recovery passed; complete public-adapter end-to-end comparison remains a conversion G2/G3 gate.
- [x] Record the decision and concrete implementation or follow-up scope, including standard destination upgrade and rollback.
- [x] Apply the selected focused implementation or documented follow-up/no-go outcome; update affected references and external-use guidance.
- [x] Run required reviews and change-specific verification; record evidence in this change and the existing wave ledger.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Contract inventory and evaluation | implementer | Readiness | MCP-first code exploration; isolated environments only |
| SQLite viability review | architecture-reviewer, qa-reviewer, performance-reviewer | Stage 1 evaluation | Record pass/fail/inconclusive before combined-data work |
| SQLite data-layout evaluation | implementer | SQLite viability pass | Compare existing-data integration layouts and recheck parity/recovery |
| Evidence review | architecture-reviewer, qa-reviewer, performance-reviewer | LanceDB evaluation and SQLite staged outcome | Verify completeness, comparisons, and eligibility |
| Conditional integration | implementer | Evidence review and concrete scope readiness | One selected backend; follow-up if migration exceeds scope |
| Delivery review | code-reviewer, qa-reviewer, architecture-reviewer | Integration or decision | Required lanes finalized at Prepare |

## Serialization Points

Prepare/readiness precedes repository code edits, including evaluation harnesses. Freeze budgets before candidate measurements. A recorded SQLite Stage 1 pass must precede Stage 2 layout design/prototypes and benchmarks; a Stage 2 parity/recovery pass must precede recommending SQLite adoption. Complete comparative evidence and review before selecting an implementation. Re-prepare when the selected design materially changes the admitted implementation scope. No commit, closure, or publication is authorized by this planning request.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/index_state_store.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/ann_reference_eval.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/references/lance-list-offset-corruption.md`

Read-only discovery covers these targets and their discovered consumers. Any seed, prompt, packaging, or configuration edits needed by the chosen migration must be named in the concrete implementation scope before execution. Protect project-authored content, live index data, embedding identity, and current MCP contracts.

## Affected Architecture Docs

Update `docs/architecture/search-architecture.md` and `docs/architecture/chunking-and-indexing-pipeline.md` if storage or maintenance behavior changes; review `docs/architecture/data-and-control-flow.md` and `docs/architecture/performance-budget.md` for publication and budget implications. Record evaluation evidence and the decision here by default; create no separate Markdown reports without a distinct lasting purpose. Amend `docs/references/lance-list-offset-corruption.md` only where evidence corrects its diagnosis or workaround guidance.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | No omitted capability |
| AC-2 | required | No backwards step in user outcomes |
| AC-3 | required | Reliability beyond happy-path queries |
| AC-4 | required | Sustainable deployment and recovery |
| AC-5 | required | Deliver the evidenced outcome |
| AC-6 | required | Prove vector viability before optimizing existing-data integration |
| AC-7 | required | Bound local capacity and verify runtime/configuration claims |
| AC-8 | required | Measure quantization benefits without hiding candidate loss or unsupported kernels |

## Implementation Readback

Readback: Preserve current backend behavior while adding a development-only, reproducible three-way evaluation. Before: only the pinned LanceDB path has local evidence. After: candidate eligibility is determined from recorded parity, performance, recovery, and platform facts; SQLite existing-data layout work occurs only after viability passes. Initial writes are the harness/tests, compact evidence, and corrected compaction reference. Production storage and dependency pin stay unchanged until conditional adoption is justified.

Ordered execution: freeze protocol and corpus → implement/test independent oracle and adapters → baseline/candidate Stage 1 probes → record verdict → conditional Stage 2 or explicit no-go → decision/reference updates → framework/docs verification.

## Progress Log

Closure 2026-09-08: final code/QA/architecture/performance/release and docs/council reviews passed. ARCH-001 corrected CPU1/GPU40 prose; independent repair cycle2 cleared. Briefing snapshot drift was only gardener verification-date metadata, independently reconstructed and cleared; no source/contract drift. All intentional deferrals remain inline and in Wave Summary.

- Observe: carried-forward tuning and native-int8 diagnostic screen are now recorded above and in one machine-evidence JSON. Independent red-team and fresh CLI docs-contract/council readiness passed for this bounded screen. Prepare succeeded; activation correctly withheld because five specialist readiness approvals have not been refreshed for the expanded scope. No checked-in harness/runtime edits were made; the executed screen was disposable and isolated. Keep those approvals and concrete broader protocols pending before repository implementation resumes.

- Readiness feedback for bounded quantization screen: isolated red-team requested explicit int8 tags and zero-norm rejection; accepted. Independent docs-contract review caught ambiguous application of the float32 unit range to int8 outputs; clarified input/output domains before execution. Review reports retained in `/tmp/wf-sqlite-screen-readiness-result.txt` and the reviewer context. No runtime behavior changed.

2026-09-08 quantization amendment: operator clarified SQLite. Added AC-8/tasks and Stage 1B without beginning Stage 2. Small in-memory release-capability probes verified int8 cosine/KNN and native quantizer; int16 rejected, apparent float16 declaration actually stored float32. No performance measurements or code/config changes ran. Expanded scope still requires re-Prepare.

2026-09-08 operator addendum: reopened AC-2/4/5 and final review, added AC-7/tasks, and expanded bounded scale scope. No new benchmark or production edit ran. Prior review/test evidence remains historical; re-Prepare is required for the expanded scope. Gapfill: direct document reads and mechanical edits were used for this docs-only plan amendment; upstream SQLite/sqlite-vec claims were checked against official documentation.

Final delivery review found two development-only proof gaps: VP-NaN (nonfinite filter scores) and
VP-Phase (missing model-phase traces). Both are recorded in the typed ledger with cycle-1 repairs.
The coordinator added finite numeric validation and required embedding/tool-specific rerank events,
with targeted bad-input controls. Actual benchmark traces remain unchanged. The same pass clarified
semantic/lexical call counts, storage-only cold-start coverage and AC-3 engine-specific probe limits;
fresh independent reverification passed, and readiness authority was refreshed to
`review-policy-98de8aa0da53bf1c5bc6`. Final verification and reviewer reports appear below.

Full-query continuation readback/thought (2026-09-08): fresh readiness and activation passed. Add a development-only public-path adapter, retaining the canonical evaluator's corpus, health, epoch and source guards. Run four explicit experimental lanes (0.33 ANN, 0.38 ANN, 0.38 exact, SQLite scalar) against one frozen updated snapshot. Instrument actual backend calls and phase timings; compare per-fixture quality externally because canonical baseline compatibility correctly rejects different dependency environments. These are prototype measurements, not production SQLite certification. The vector ceiling is 100 ms; total-query timing is descriptive. Stage 2 remains conditional on Stage 1 evidence.

Full-query probe review: reviewer `vector_fullquery_council` identified VP-1: the production dense wrapper suppresses substrate exceptions, so wrapper invocation alone cannot prove execution. Interrupted the first baseline pilot in `/tmp/wf-vector-eval-1xhbo-public-baseline` (exit 130; partial calls retained; no accepted measurement). Added query-builder proxies that require successful materialization and observe actual exact-index bypass; missing proof invalidates the attempt outside the suppressed boundary. Two focused proof controls pass, including an injected materialization error. Restarted baseline as `public-baseline-v2`. This failed pilot is additional spent work, not a hidden successful slot. The isolated CoreML probe cannot initialize in the sandbox; the actual reranker uses CPUExecutionProvider. Comparisons must match that provider and do not claim GPU performance.

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-08 | Observe: latest Lance exact-with-index and exact-without-index each passed all five frozen corpora and all nine hydrated query slices (90 slice summaries total), including round trips and ten churn cycles. Maximum p95: 29.75 ms with index bypass; 28.81 ms with ANN construction omitted. Both pass the revised vector limit. These are vector/oracle results, not public relevance or adoption certification. | `/tmp/wf-vector-eval-1xhbo-revised-*/result.json`; independent bounded code/QA source review by vector_revised_contract found no actionable defect. Reviewer confirmed lifecycle contract status must not substitute for exact nearest-set checks; child RSS is a complete query process, not engine-only/build peak. |
| 2026-09-08 | Observe: new exact-mode control passes with six focused tests. In-memory mutants removing bypass and forcing ANN construction for lance-flat each fail `test_exact_modes_bypass_an_inexact_index_and_flat_avoids_building_it`; original methods restored. Candidate 0.38.0 exact synthetic 512-row run passes all slices/churn. Frozen Arrow SHA256 values reverified unchanged. | Mutation controls distinguish wrong ANN neighbors from exact results and query bypass from build avoidance; candidate environment only. Real-corpus measurements and generalized lifecycle probes remain in progress. |
| 2026-09-08 | Readback / Thought: fresh bounded readiness passed. Extend development harness with exact Lance index bypass and no-ANN-build modes, then generalize lifecycle/cold-process probes to SQLite. Before: ANN-only Lance and Lance-only cold driver; after: explicit modes with identical hydration and payload/vector checks. Order: harness modes, focused controls, frozen-corpus vector measurements, paired lifecycle probes, full framework/docs checks. Stage 1 certification, full-query comparative measurement, Stage 2 and adoption remain held for the pending total-query decision. | Current typed council approval `ev-approval-wave-council-readiness-2`; successful Prepare/create and Implement/create; files limited to existing evaluation scripts/tests and compact receipt. |
| 2026-09-08 | Thought: implement isolated comparison after successful Prepare and required readiness lane approvals; memory briefing reviewed. Freeze warm limit as max(1.10 × baseline, baseline + 2 ms), cold limit max(1.25 × baseline, baseline + 100 ms); percentile is nearest-rank (ceil(p × n)); cold means fresh process, OS cache not flushed. Query timing includes fully materialized equivalent payload and score conversion. | Typed readiness ledger; `/tmp/wf-vector-eval-1xhbo-data/manifest.json`: docs v8023 / 27948 rows, code v2607 / 8743 rows, both 384 dimensions. Baseline0.33.0/candidate0.38.0 share PyArrow25.0.0 and NumPy2.5.1; sqlite-vec0.1.9 / SQLite3.50.1. |
| 2026-09-08 | Operator budget correction: original no-go superseded; reopened AC-2 through AC-6 and dependent tasks. Scalar SQLite max p95 81.97 ms and LanceDB 0.38 max 24.82 ms pass below-100 ms latency; vec0 tag fallback reaches 276.46 ms. Raw receipt remains unchanged. | Current Budget section; all recorded slices recalculated from existing JSON, no new benchmark or code edit. |
| 2026-09-08 | Verification: canonical framework suite passed 8,565 tests across 76 files, three skips, 198.4 s; candidate-environment oracle tests passed all five. Full docs lint and diff whitespace checks passed. Formal delivery review remains before closure. | `run_tests.py` green receipt; focused unittest command; `wf_validate_docs`. |
| 2026-09-08 | Gapfill: `wf_mark_ac(state="~")` failed before writing with `cannot import name is_recordable_path from scanner_skips`; applied the canonical checkbox and inline rationale directly. AC-2/3 now truthfully record incomplete qualification after the permitted no-go. | No lifecycle approval or closure inferred; full docs validation required. |
| 2026-09-08 | Observe: 20 corpus/backend runs plus three paired Lance lifecycle/cold cycles completed. SQLite measured paths fail the warm budget; Lance remains uncertified. Historical stress probe succeeds on both versions, so retain recovery and correct the unsupported root-cause claim. | Machine receipt and final decision below; live backend not switched. |
| 2026-09-08 | Initially planned LanceDB upgrade evaluation | Existing baseline and upstream release references |
| 2026-09-08 | Expanded on operator request to latest LanceDB vs SQLite vectors | Revised requirements and five required ACs; no evaluation or implementation performed |

### Revised resource measurements (2026-09-08)

The operator explicitly requested memory and disk requirements as part of dependency management.
These are measured macOS ARM64 results for the same 27,948 docs vectors (384 dimensions), not minimum
requirements for every project. Each query/resource number is the median across three independent
process cycles; query cycles each include seven measured fresh processes. Units below are MiB.

| Storage path | Storage-library disk space (MiB) | Steady index disk space (MiB) | Fresh query peak RAM (MiB) | Streamed build peak RAM (MiB) |
| --- | ---: | ---: | ---: | ---: |
| Installed LanceDB 0.33 ANN | 232.81 | 91.61 | 199.77 | 574.22 |
| LanceDB 0.38 ANN | 256.84 | 95.43 | 159.84 | 600.28 |
| LanceDB 0.38 exact, no ANN construction | 256.84 | 64.03 | 239.92 | 362.56 |
| sqlite-vec 0.1.9 vec0 | 0.16 | 91.82 | 37.83 | 91.55 |
| sqlite-vec 0.1.9 ordinary-table cosine | 0.16 | 109.74 | 38.55 | 86.64 |

Latest Lance exact with an existing ANN index used 95.54 MiB on disk and 239.80 MiB query RSS;
its build path is identical to the ANN lane and was not redundantly measured in the streamed probe.
All 18 lifecycle runs and 15 streamed builds passed keyed vector/payload checks; all cold query
nearest-set checks passed independently of the lifecycle driver's contract-only status.

Installed sizes count logical files owned by distributions, excluding bytecode. The dependency
graph starts from the actual `setup_index.REQUIRED_IMPORTS` plus shared `onnx`; 90 common packages
occupy 256.69 MiB in the baseline environment and remain common costs. NumPy, Pydantic and the
embedding/reranking dependencies are not removable savings. The Lance-only closure includes PyArrow,
namespace packages, deprecation, python-dateutil and six. SQLite's marginal binary is about 0.16 MiB;
replacing the installed Lance closure could save about 232.65 MiB in the shared tool environment,
subject to migrating remaining Lance consumers and older destination projects first. Model caches
and the Python interpreter are additional shared costs, not included in this table. These are local
installed-file measurements, not cross-platform wheel-size guarantees.

Query RSS excludes the embedder/reranker and corpus/oracle snapshots. Build RSS includes Python,
the backend, resident numpy mmap input pages and identical 512-row payload batches; the peak is
captured before full verification snapshots. It is process memory, not engine-only allocation or
the full production server. The common prepared benchmark input occupies 81.22 MiB and is excluded
from store size; production migration need not materialize that same intermediate format.

Disk high-water sampling covers visible files under the store work directory every 10 ms, so it is
a lower bound that misses unlinked/out-of-tree temporary files and shorter peaks. Median visible
peaks were 127.84 MiB (baseline Lance), 127.76 MiB (latest ANN), 127.80 MiB (latest flat), 184.30 MiB
(vec0) and 220.28 MiB (scalar SQLite). SQLite's post-maintenance open connection retained WAL;
the steady index column above is measured after reopen, which clears that transient storage.
LanceDB is not maintenance-free: the same probes call `optimize(cleanup_older_than=timedelta(0))`,
then recreate ANN where selected; SQLite runs checkpoint/VACUUM. The
[LanceDB API](https://lancedb.github.io/lancedb/python/python/#lancedb.table.Table.optimize)
describes optimization as compaction, pruning old versions and updating indexes. Compare both
backends' rewrite/copy-on-write space, retained versions, temporary files, duration, memory and
post-reclamation size. The shared 10 ms sampler has the same observational limits for both engines.
Neither measured peak establishes worst-case required free space. In particular, do not compare
SQLite's documented upper-bound guidance below with Lance's observed lower bound as if they were
the same measure. Lance's rewrite recovery path also needs separate headroom from normal optimize;
its `to_arrow()` materialization and replacement index build are not covered by the streamed-build
RSS figures. Complete that recovery/migration budget before adoption.
[SQLite documents](https://www.sqlite.org/lang_vacuum.html) that VACUUM can require up to twice
the database size in additional free space. For the isolated 109.74 MiB scalar store that is about
219.48 MiB extra headroom. Retaining the 91.61 MiB old index while constructing and vacuuming that
new store would occupy roughly 420.83 MiB in total before any separately chosen staging/backup.
This is a planning calculation, not an executed destination migration. Stage 2 must include the
whole combined SQLite database, FTS/state data and chosen retention policy when computing its budget.

Evidence: [revised machine receipt](../../../.wavefoundry/framework/scripts/tests/fixtures/vector_backend_eval_1xhbo_revised.json).
It retains 10 exact-vector runs, 18 lifecycle runs, 15 build runs, input/function hashes and the
dependency closure. The original receipt is unchanged. The new truncated-input control fails when
its row/vector count assertion is removed; the first mutation-driver attempt had an unrelated mock
binding error and was discarded, then the corrected control failed for the intended missing error.
Seven focused tests passed. Independent bounded code/QA review found no blocking defect and prompted
the explicit JSON disk-sampling limitation. Full framework verification passed 8,567 tests across
76 files, three skips, in 203.581 seconds; full docs validation passed.

This evidence favors SQLite on dependencies and memory, but not on steady scalar-index disk size.
It does not certify Stage 1 or select a backend: full-query relevance/latency, platform qualification,
remaining optimization dispositions and conditional existing-data layout work remain.

## Decision Log

2026-09-08 quantization divergence: changing the primary backend comparison to int8 would confound engine and representation; implementing custom int16 would add unrequested maintenance and cannot demonstrate released-extension efficiency. Selected a separate native int8-first track, with unsupported-format evidence and optional binary/rescoring lanes. Preserve original stage names and strict relevance requirements; compare best qualified SQLite against actual Lance index configurations.

2026-09-08 addendum, diverge → critique → select: (1) adopt the proposed PRAGMAs and unified schema immediately—assumes memory and atomicity benefits and bypasses Stage 1; (2) run every size/configuration combination through 2M+—expensive and unnecessary after a clear limit; (3) selected: bounded scale screening and one-factor tuning, then conditional transactional layout experiments. This makes the capacity limit and simplification falsifiable while preserving quality, resource and sequencing gates.

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-08 | Operator requested a thorough latest-capabilities and long-term comparison | Added explicit Lance exact/ANN and both SQLite lanes, capability dispositions, roadmap maturity and decision sensitivity. Existing experiments remain evidence, not a completed latest-capability qualification. | Feature-count comparison overweights irrelevant hosted features; roadmap-dependent adoption would risk current guarantees. |
| 2026-09-08 | Operator revised vector retrieval acceptance to below 100 ms; assess latency with reranking included | The earlier relative vector-step gate rejected small absolute delays without measuring their user-visible impact. Retained measurements show the scalar SQLite path passes the revised latency ceiling. | Keep the original gate: misstates operator tolerance. Immediately approve migration: skips remaining parity/reliability and layout evidence. Select renewed staged evaluation with unchanged correctness guarantees. |
| 2026-09-08 | Select a three-way measured comparison, then conditionally implement | Tests current guarantees and the claimed simplification before committing to storage changes | Upgrade-only misses possible dependency savings; immediate SQLite migration assumes parity and understates migration risk |
| 2026-09-08 | Keep current wave/change identifiers | This extends the admitted planned evaluation | Renaming paths or creating duplicate plans adds tracking work without changing the deliverable |
| 2026-09-08 | Evaluate SQLite vector viability first, then compare existing-data integration layouts only if it passes | Operator requires sequential evidence and the most efficient suitable integration | Designing integration first risks wasted work on an unsuitable store; accepting the first viable layout can miss avoidable joins, copies, and duplicate data |

## Research Starting Points

Version observations checked 2026-09-08; refresh at evaluation start. These links establish research inputs, not compatibility or defect-resolution proof.

- [LanceDB 0.38.0 release](https://github.com/lancedb/lancedb/releases/tag/v0.38.0) and [upstream issues](https://github.com/lancedb/lancedb/issues).
- [sqlite-vec 0.1.9 release](https://github.com/asg017/sqlite-vec/releases/tag/v0.1.9), [KNN capabilities](https://alexgarcia.xyz/sqlite-vec/features/knn.html), and [roadmap milestones](https://github.com/asg017/sqlite-vec/milestones). Inspect prereleases separately; milestone dates alone are not delivery commitments.
- [Lance nested-list decoder fix 7546](https://github.com/lance-format/lance/pull/7546) and [Arrow-offset validation 8382](https://github.com/lance-format/lance/pull/8382): neither alone proves our compaction failure fixed.

## Risks

| Risk | Mitigation |
| --- | --- |
| SQLite filtering or query limits change recall | Adversarial predicate fixtures and independent exact reference before eligibility |
| Fewer packages require more integration code | Compare total installation and maintenance cost, including remaining consumers |
| Historical defect cannot be reproduced | Mark inconclusive and retain the workaround |
| Benchmark noise hides a regression | Paired repeated measurements, fixed vectors, and predeclared budgets |
| Migration leaves mixed or unrecoverable stores | Disposable destination drills, interrupted-upgrade checks, and rollback before cleanup |
| Roadmap or unavailable platform evidence is mistaken for support | Label unshipped and untested capabilities explicitly; keep adoption blocked on required gaps |

## Session Handoff

Implementation remains open. The operator replaced the relative vector-latency budget with a 100 ms ceiling. Recorded scalar SQLite and LanceDB 0.38.0 timings pass that ceiling; native vec0 auxiliary tag fallbacks do not. Re-prepare the revised evaluation, finish remaining Stage 1 checks and measure reranking-inclusive query time, then record a new viability verdict before conditional Stage 2. No production backend, dependency pin, or release assignment has changed.

## Capability Matrix (source audit, 2026-09-08)

This inventory separates native engine capability from Wavefoundry adaptation. It is not a runtime pass report; measured results and the adoption decision are recorded separately. Current-source checks used MCP outlines and targeted reads; semantic search reported stale chunks, so current file contents controlled the audit. `N` means a native API/capability to verify; `A` means application adaptation is required; `G` means a known gap in the direct proposed path. Neither `N` nor `A` establishes eligibility.

| Current contract and source/test evidence | LanceDB 0.38.0 | SQLite + sqlite-vec 0.1.9 |
| --- | --- | --- |
| Full streaming docs/code writes: `indexer._StreamingLayerWriter`, `_make_lance_rows`; [indexer tests](../../../.wavefoundry/framework/scripts/tests/test_indexer.py), `test_lance_row_count_matches_chunk_rows` | N: create/overwrite/add and vector-index build; recheck real schemas and flush boundaries | A: transactional batch insert and dimension-checked float32 blobs; ordinary metadata/list serialization must round-trip |
| Payload identity: `indexer._normalize_chunk_row_metadata`, `_row_metadata_matches_current`; `index_state_store.chunk_id_collision_census` | N: existing Arrow rows, including variable-length `lines`; public chunk IDs need not uniquely identify physical rows | A: stable storage-row identity separate from public chunk ID; preserve ID/path/kind/language/section/text/hash/tags/lines and vector bytes; do not impose a new public-ID uniqueness constraint |
| Cosine scores and hydrated results: `WaveIndex._lance_search`; [retrieval tests](../../../.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py), `TestLanceDBIndex` | N: cosine distance, `to_list`, score conversion; retain certified `ANN_REFINE_FACTOR` | N/A: cosine distance native; conversion to `1-distance`, path qualification, payload hydration and public score shape remain application work |
| Predicate-before-top-k: `WaveIndex.search_docs`, `search_code`; retrieval tests `test_search_docs_tags_pre_filter`, `test_search_docs_tags_and_kind_compose_with_and_semantics` | N: current SQL prefilter path, including kind/language plus OR-combined substring tag predicates; quotes and wildcards must retain existing behavior | G/A: direct vec0 metadata KNN does not provide current `LIKE` semantics; evaluate scalar-distance SQL with all predicates applied before ranking/limit. Post-filtering a limited KNN result is ineligible |
| Candidate windows, refill, diversity and fusion: `WaveIndex.search_code`, `search_combined`; [candidate-generation tests](../../../.wavefoundry/framework/scripts/tests/test_retrieval_candidate_generation.py) | A unchanged: engine must feed current bounded source windows and truthful exhaustion/ceiling diagnostics | A: preserve the same budgets, filter behavior, duplicate handling and fallback outcomes; exact exhaustive search is acceptable only within performance gates |
| ANN/exact certification: `ann_reference_eval._apply_bypass`, `_base_query`, `exact_search`; [ANN tests](../../../.wavefoundry/framework/scripts/tests/test_ann_reference_eval.py), `ExactSeamTests`, `CertificationTests` | N: retain explicit exact bypass; no fallback from unavailable exact mode to ANN. Production tuning and independent float64 oracle must both be represented | A: stable exact scan may replace ANN, but adapt the Lance-specific evaluation seam; tie-aware overlap and per-slice relevance remain required |
| Incremental vector reuse: `indexer._read_lance_rows_for_paths`, `_plan_lance_delta_rows`, `_lance_incremental_write`; [indexer tests](../../../.wavefoundry/framework/scripts/tests/test_indexer.py) | N/A: existing path/ID selects, deletes, append, metadata-only updates and index rebuild ordering | A: equivalent keyed read/update/delete with no extra embedding for compatible stored vectors; absent tags in real tables stay absent/empty, not invented labels |
| Drift, excluded paths and orphan cleanup: `indexer._detect_lance_drift`, `_reap_stranded_lance_rows`; indexer tests `test_detects_drift_when_path_missing_from_lance`, `test_reap_dry_run_preserves_lance_and_reports_path_count` | N/A: enumerate current rows and apply bounded deletes; retain dry-run behavior | A: backend-neutral scans/deletes and identical reconciliation bookkeeping; preserve tombstone, zero-chunk and eligibility distinctions |
| Compaction/reclamation: `indexer.reclaim_lance_table`, `_compact_by_rewrite`, `optimize_index_tables`; indexer tests around `test_optimize_lance_table_returns_bool` | N/A: optimize, Arrow rewrite without embedding, rebuild fallback; existing defect workaround stays until independently justified | A: deletion, WAL checkpoint, VACUUM/optimize and integrity/restart probes; translate public maintenance outcomes without pretending Lance tiers are native SQLite operations |
| Lexical search and published state: `IndexStateStore._apply_chunk_deltas_locked`, `fts_search`, `begin_build_epoch`, `finalize_build_epoch`; [state-store tests](../../../.wavefoundry/framework/scripts/tests/test_index_state_store.py), [FTS tests](../../../.wavefoundry/framework/scripts/tests/test_fts_lexical_layer.py) | A unchanged: FTS5 already lives in index-state.sqlite; no Lance/Tantivy FTS is currently built | A: retaining SQLite FTS is straightforward in principle; colocating vectors must not bypass generation fences, attempt-ID CAS, transaction rollback or reader-token checks. These integration layouts remain Stage 2 only |
| Fresh handles, availability and public diagnostics: `WaveIndex._open_lance_table`, `_layer_health`, `index_health_response`, `_index_optimize_response`; retrieval tests `test_docs_lance_dir_counts_as_present`, `test_optimize_runs_store_pass_even_with_no_lance_tables` | N/A: existing table handles and `.lance` layout checks, row counts, bloat and maintenance reports | A: replace backend-specific existence/handle/fragment assumptions while preserving missing/stale/unavailable distinctions and bounded health operations |
| Dashboard and rebuild counts: `dashboard_lib._lance_table_stats`, `server_impl._read_index_rebuild_stats`; [dashboard tests](../../../.wavefoundry/framework/scripts/tests/test_dashboard_server.py), `test_collect_dashboard_snapshot_reads_lance_chunk_counts_without_legacy_json` | N: `count_rows` metadata reads; no full table materialization | A: equivalent bounded counts and layout detection; dashboard must not acquire a vector-payload scan to show summary tiles |
| Evaluation startup/provenance: [retrieval_eval.py](../../../.wavefoundry/framework/scripts/retrieval_eval.py) checks `docs.lance`/`code.lance` and records LanceDB package version; [retrieval-eval tests](../../../.wavefoundry/framework/scripts/tests/test_retrieval_eval.py) | N/A: current evaluator opens same layout; freeze engine/package versions | A: update readiness detection and reproducibility provenance, plus the independent ANN/exact seam; replacing only production queries leaves evaluation broken |
| Installation, packaging and destination recovery: `setup_index.LANCEDB_REQUIREMENT`, `indexer._auto_install_lancedb`, `build_pack.collect_files`; [setup tests](../../../.wavefoundry/framework/scripts/tests/test_setup_index.py), [upgrade tests](../../../.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py) | A: one validated pin, compatible dependency installation and standard wf_upgrade; test old/new on-disk readers before downgrade promises | A: extension-loading feasibility and dependency audit, migration/rebuild detection, embedding reuse, rollback and obsolete-store cleanup; development harness/fixtures remain excluded under scripts/tests |

Source families: [indexer.py](../../../.wavefoundry/framework/scripts/indexer.py), [server_impl.py](../../../.wavefoundry/framework/scripts/server_impl.py), [index_state_store.py](../../../.wavefoundry/framework/scripts/index_state_store.py), [dashboard_lib.py](../../../.wavefoundry/framework/scripts/dashboard_lib.py), [ann_reference_eval.py](../../../.wavefoundry/framework/scripts/ann_reference_eval.py), [setup_index.py](../../../.wavefoundry/framework/scripts/setup_index.py), [build_pack.py](../../../.wavefoundry/framework/scripts/build_pack.py). Import/layout census also covered venv bootstrap ABI guidance and secret-scanner `.lance` binary exclusions; these are surrounding compatibility/documentation surfaces, not additional vector-query consumers. Downstream memory and code-question tools inherit retrieval behavior through the shared search paths.

## Dependency, Platform, and Roadmap Audit

Released optimization dispositions (full-query continuation, 2026-09-08):

| Capability | Current evaluation disposition |
| --- | --- |
| Lance prefilter and exact bypass | Both exercised with identical payload hydration. ANN retains the existing certified refinement factor; exact bypass also has an explicit no-index-build resource lane. |
| Lance BTree/Bitmap scalar indexes | Released options for equality/range predicates; Bitmap fits low-cardinality kind/language. They add index maintenance and do not fix arbitrary tag-LIKE semantics. No speedup is claimed without a dedicated indexed comparison; current measured unindexed predicates already meet the vector budget. |
| Lance LabelList/FM indexes | LabelList requires list-valued tags, unlike the current string representation. FM accelerates `contains`, not a drop-in replacement for wildcard LIKE. Both need a separately specified predicate/schema change before adoption credit. |
| Projection and batching | Current measurements fully hydrate equal payloads. Projecting out stored vectors before Python materialization is a possible follow-up saving, not included in these numbers. Streamed 512-row builds are measured; batching independent interactive queries is not the present request pattern. |
| Vector precision and quantization | Existing Lance ANN uses scalar quantization and refinement. Exact lanes retain float32 vectors. sqlite-vec float/int8/binary support does not justify changing precision or embedding dimensions without a separately frozen quality experiment; no additional quantization saving is claimed. |
| Reranker integration | Both candidates retain the same application-owned cross-encoder and fusion/refill policy. A database rerank hook is not an extra quality capability when the existing shared pipeline already supplies it. |
| sqlite-vec metadata/partition/auxiliary columns | Native metadata filtering and auxiliary-tag scalar fallback were exercised. Splitting by kind/language cannot establish parity for OR/quoted tags; the measured fallback remains over budget. Ordinary-table cosine SQL is the viable released alternative under continued review. |

Sources: [Lance scalar indexes](https://docs.lancedb.com/indexing/scalar-index),
[Lance vector search](https://docs.lancedb.com/search/vector-search),
[sqlite-vec 0.1.9 source README](https://raw.githubusercontent.com/asg017/sqlite-vec/v0.1.9/README.md),
[SQLite KNN alternatives](https://alexgarcia.xyz/sqlite-vec/features/knn.html).
The pinned sqlite-vec README explicitly identifies the project as pre-v1 with possible breaking
changes. Its small native dependency and broad wheel coverage are benefits, but upgrades still
require pinned versions, compatibility probes and rebuild/recovery capability. The recommendation
must work using released exact search even if every ANN/NEON roadmap item slips; an upstream release
with measured filter-compatible acceleration is a re-evaluation trigger, not a prerequisite or promise.

Checked 2026-09-08 against released package metadata and official upstream material. Download availability is evidence about distribution feasibility, not a successful supported-platform execution test. Installed LanceDB 0.38.0 carries Apache-2.0 LICENSE text; sqlite-vec 0.1.9 metadata declares MIT / Apache-2.0. A further macOS ARM64 Python 3.11.13 / SQLite 3.50.1 probe successfully loaded sqlite-vec 0.1.9 and evaluated scalar cosine; this is narrower than full application qualification.

| Distribution fact | Installed baseline LanceDB 0.33.0 | Candidate LanceDB 0.38.0 | Candidate sqlite-vec 0.1.9 |
| --- | --- | --- | --- |
| Published platform wheel families | macOS ARM64, Linux x86_64/ARM64, Windows x86_64; Linux includes glibc 2.17 and 2.28 tags | Same broad CPU families; Linux wheels require glibc 2.28 | macOS ARM64 and Intel, Linux x86_64/ARM64 (glibc 2.17), Windows x86_64 |
| macOS Intel gap | No matching wheel or source distribution in the inspected release | Same gap; **not a new 0.38 regression** | Matching wheel published; load/runtime still requires validation |
| New Linux compatibility constraint | glibc 2.17 distribution available | glibc 2.17-only environments lose the prior wheel path; no silent supported-platform narrowing | Prior glibc floor is feasible at wheel level |
| Selected macOS ARM64 download, package only (MiB) | Not used as a whole-environment comparison | Approximately 57.7 | Approximately 0.157; excludes Python, SQLite and retained embedding dependencies |

Evidence: [LanceDB 0.33 metadata](https://pypi.org/pypi/lancedb/0.33.0/json), [LanceDB 0.38 metadata](https://pypi.org/pypi/lancedb/0.38.0/json), [sqlite-vec 0.1.9 metadata](https://pypi.org/pypi/sqlite-vec/0.1.9/json). WSL2 uses Linux wheels; this does not replace a WSL2 runtime check. Native Windows extension loading and Python build compatibility remain explicit execution obligations. A package wheel cannot establish all supported Python/interpreter combinations.

LanceDB 0.38 raises its Pydantic requirement to `>=2.7.4,<3` (0.33 allowed `>=1.10`); its dependency set includes PyArrow `>=16`, NumPy, deprecation, packaging, tqdm and lance-namespace. Freeze the actual resolved environment, not only the top-level pin. sqlite-vec removes that particular dependency chain only after every production consumer is adapted. NumPy remains required by the embedding/inference stack. The source census found PyArrow use through Lance operations rather than a separate production import, so removal is plausible, not yet proven across the resolved environment. Arrow export in this wave's development harness does not justify shipping PyArrow permanently. Package-size differences are not total installed footprint or a measured maintenance saving. [LanceDB metadata](https://pypi.org/pypi/lancedb/0.38.0/json)

LanceDB 0.38 ships computed-column/materialized-view/function and streaming work, Pydantic 2 migration, and Lance engine 11.0.0. Those are released changes, but most do not directly simplify this repository's narrow local vector/search workload. Prioritize compatible local read/write/filter/maintenance behavior over feature count; hosted/enterprise capabilities receive no parity credit. The release and issue tracker show active upstream work, not a guarantee that the historical compaction failure is fixed. [0.38 release](https://github.com/lancedb/lancedb/releases/tag/v0.38.0), [versioned Cargo manifest](https://github.com/lancedb/lancedb/blob/v0.38.0/Cargo.toml)

sqlite-vec 0.1.9 is the stable candidate; its release specifically fixes DELETE behavior. The 0.1.10 alpha line and its ANN/DiskANN work are separate experimental inputs, not an adoption dependency. Current documentation is labeled `v0.1.10-alpha.4`, so stable capability claims require checking the pinned 0.1.9 implementation/probes. The documented vec0 metadata operators do not include LIKE, auxiliary payloads cannot supply arbitrary KNN predicates, and scalar cosine SQL is the flexible exact alternative. A small dependency does not remove the need for an adapter or efficient payload access. No dated milestone is treated as a delivery commitment. [0.1.9 release](https://github.com/asg017/sqlite-vec/releases/tag/v0.1.9), [releases](https://github.com/asg017/sqlite-vec/releases), [milestones](https://github.com/asg017/sqlite-vec/milestones), [KNN methods](https://alexgarcia.xyz/sqlite-vec/features/knn.html), [metadata constraints](https://alexgarcia.xyz/sqlite-vec/features/vec0.html)

The historical Lance list-offset diagnosis remains unproven at the exact failure mechanism. Upstream [7546](https://github.com/lance-format/lance/pull/7546) repairs nested-list decoding; [8382](https://github.com/lance-format/lance/pull/8382) concerns offset slicing. Neither alone proves this repository's observed compaction failure is resolved. Record actual reproduction results separately, distinguish a healthy new table from reading an affected historical table, and retain `_compact_by_rewrite` unless the wave obtains decisive evidence. Open issues and roadmap entries identify what to test; they do not satisfy acceptance criteria.

## Original SQLite Stage 1 Verdict (superseded budget)

**Historical result under the original relative budget: FAIL.** This conclusion is superseded by the operator revision above; Stage 1 is now pending continued evaluation. On the frozen
27,948-row docs corpus, unfiltered top-40 warm median/p95 were 4.928/5.223 ms for
LanceDB 0.33.0, 16.482/16.672 ms for native vec0, and 38.060/38.554 ms for ordinary
SQLite scalar cosine. The frozen median/p95 limits are 6.928/7.223 ms. Both SQLite
paths exceed them without tags, joins to existing data, or integration-layout choices.
The independent evidence review found equal vector/payload hashes and materialized
payloads across paths; this is sufficient to reject adoption under this wave's budget.

SQLite passed the tested float32 vector/payload round trips, exact cosine/filter
checks, and isolated insert/replace/delete rollback, reader isolation, bounded writer
contention, process exit before commit, and reopen probes. Its slower tag fallback on
vec0 auxiliary columns is a provisional-layout cost and is not the deciding evidence.
This result does **not** establish that every possible SQLite implementation is too
slow. It rejects the declared stable native-KNN and scalar paths on this local workload.

Independent architecture/QA/performance evidence inspection by `vector_readiness`
confirmed the scope of this verdict. Other bounded corpus runs continue for comparison
breadth; no combined-data schema, join-layout optimization, or migration is started.
Machine results are retained in the evaluation receipt. Cold startup and full public
relevance are distinct from these warm raw-vector measurements and are not claimed.

## Measured Comparison

The development-only [machine receipt](../../../.wavefoundry/framework/scripts/tests/fixtures/vector_backend_eval_1xhbo.json)
retains all 20 corpus/backend runs, query samples, churn measurements, package versions,
corpus hashes and commands. It contains no indexed source text or vectors. Exact real-corpus
replay requires the matching disposable Arrow exports; the synthetic corpus is generated
from the fixed seed. The two first docs Lance runs were pilots before reporting/failure-probe
additions; their exact historical harness hash was not captured. Search/storage code was
unchanged. The remaining corpus runs bind to the recorded final harness hash.

All timing runs used the same local arm64 host, macOS 27.0 build 26A5421a and Python 3.13.5. CPU/RAM hardware identification was unavailable through the sandbox; these measurements do not claim cross-machine or supported-release qualification. Backend runs were sequential, with no intentional concurrent test-suite or other backend benchmark. Normal host activity and unflushed OS caches remain sources of noise.

Unfiltered top-40 **median / p95 milliseconds**, two warmups and seven measured samples:

| Corpus | Rows | LanceDB 0.33 | LanceDB 0.38 | sqlite-vec KNN | SQLite scalar |
| --- | --- | --- | --- | --- | --- |
| Synthetic | 512 | 3.99 / 5.15 | 4.36 / 5.00 | 0.39 / 0.40 | 0.44 / 0.45 |
| Current docs | 27,948 | 4.93 / 5.22 | 5.73 / 6.14 | 16.48 / 16.67 | 38.06 / 38.55 |
| Current code | 8,743 | 5.11 / 5.47 | 5.52 / 5.92 | 5.29 / 5.40 | 13.03 / 14.11 |
| Docs growth | 55,896 | 4.97 / 5.21 | 5.67 / 5.94 | 32.56 / 33.14 | 78.85 / 79.51 |
| Code growth | 17,486 | 5.10 / 5.28 | 5.93 / 6.08 | 10.54 / 10.70 | 25.36 / 25.85 |

All paths preserved keyed payloads and float32 vector bytes over ten append/delete/maintenance/reopen
cycles. SQLite returned exact results for all tested slices. Baseline Lance approximate-neighbor
misses are visible in the receipt; they are not evidence of payload/filter corruption. Candidate
Lance passed the independent nearest-set checks for these sampled queries, but this is not a claim
of improved user relevance. Real table tags were absent, so nonempty OR/quoted-tag correctness comes
from the synthetic fixture; no representative tag workload is invented.

The candidate Lance synthetic kind-filter p95 was 8.23 ms against a 7.82 ms limit. Preserve this failed
sample; it is not sufficient to diagnose a durable regression, nor may it be silently dropped from
an eligibility claim. All other candidate Lance warm slices met the frozen timing limits in these
runs. Separate lifecycle/startup measurements and their verdict follow below.

Docs post-maintenance storage was approximately 91.58 / 95.33 / 91.82 / 109.74 MiB in the table's backend order (converted from the original decimal-byte display).
All runs retained live rows; SQLite sizes were constant across ten churn cycles, and Lance sizes
varied within a bounded plateau. Whole-harness peak RSS on current docs was approximately
2.05 / 2.25 / 0.95 / 0.94 GB. This includes Python corpus records, Arrow conversion, snapshots and
the float64 oracle, so it cannot establish production backend memory usage. No embedding calls
were made: all stores received the same previously computed vectors.

LanceDB 0.33 uses Lance engine 9.0.0, while 0.38 uses 11.0.0; the historical error cited engine 7.0.0.
The untriggered baseline does not establish when or whether that incident was fixed.
[Versioned 0.33 Cargo manifest](https://github.com/lancedb/lancedb/blob/v0.33.0/Cargo.toml)

## Lance Lifecycle and Original Decision (superseded)

Three paired fresh-store docs cycles used the companion development driver; all keyed vectors and
payloads survived append/delete/maintenance/reopen. Median times (baseline → candidate) were:
full storage write 584.51 → 621.81 ms; initial maintenance 821.28 → 1009.26 ms; append
6.376 → 7.395 ms; delete 2.036 → 1.994 ms; subsequent maintenance 848.23 → 942.36 ms.
Each is within the frozen 1.25x lifecycle limit. These are storage operations without embedding.
Fresh-process unfiltered startup/open/hydration had median 839.96 → 812.96 ms and p95
876.13 → 854.67 ms, using the median of each cycle's seven-sample statistic. All individual
samples remain in the receipt; OS caches were not flushed. Reopen-only latency was
0.928 → 1.427 ms and is reported separately, not substituted for full startup.

**Original outcome under the superseded relative budget: no production change.** The current decision is reopened by the operator revision above. Retain LanceDB 0.33.0 and the existing
reclaim ladder. sqlite-vec fails the measured Stage 1 performance gate, so no Stage 2 layout or
migration work is authorized by a viability pass. LanceDB 0.38.0 is **not certified**, rather than
proven generally unsuitable: one required warm p95 sample failed, while public relevance and
supported-platform execution have not been established. Its sampled nearest-neighbor and lifecycle
results warrant later qualification, not silently bypassing the no-regression requirement.

The delivered changes are the reusable development-only comparison drivers, adversarial oracle
tests, durable measured evidence, and corrected historical-compaction diagnosis/reference.
No dependency pin, production query/storage path, release assignment, or destination migration changes.
Evaluation drivers and receipts live under scripts/tests and are excluded from distribution.
No end-user changelog entry is needed for an evaluation that changes no delivered search behavior.

### Previously unexecuted gates (now reconsidered in the current wave)

The original protocol permitted stopping downstream adoption work after a failed required gate. The revised budget reopens that decision; the following omissions
are recorded as **not run**, not inferred successes or a claim of complete compatibility:

- Full public relevance/reranking/citation/candidate-window evaluation on both package versions.
  Existing `retrieval_eval` requires a coherent published source/index/FTS/graph snapshot; the
  per-table Arrow exports do not establish it. Its `--baseline` comparison also rejects differing
  package versions by design. A future qualification must run standalone reports on the same
  isolated coherent snapshot and explicitly compare per-fixture metrics without forging report identity.
- Lance-specific interrupted-write/reclamation and old/new-reader/destination recovery drills;
  reading a historically affected table was not possible from the healthy stress probe.
- SQLite fresh-process startup and three paired full-build cycles after its decisive warm-latency
  failure; ten local churn cycles and isolated transaction/crash probes were run. Registry/FTS/build
  publication is covered by standing tests only, not by a new integrated SQLite implementation.
- Nonlocal macOS Intel, Linux/WSL2 and Windows execution; additional Python-version installation
  and extension-loading checks. Wheel availability and local macOS ARM64/Python 3.13.5 execution
  are the evidence available. No supported-platform narrowing is accepted implicitly.
- Backend-only peak memory and total destination dependency-footprint measurements. Whole-harness
  RSS and package metadata/download sizes remain labeled proxies.

To reconsider LanceDB 0.38.0, freeze a coherent isolated golden corpus and actual target platform
matrix, investigate/repeat the failed kind-filter slice with unchanged budgets, run public relevance,
verify old-index read/update/maintenance and interruption/rollback, then change only the centralized
Lance requirement plus directly affected compatibility code. Retain the compaction fallback unless
an actual failing historical fixture is fixed. Re-prepare that concrete scope before adoption.
To reconsider SQLite, first provide a released query path that passes Stage 1; only then compare
separate and colocated vector/data layouts as originally required. Roadmap ANN work is not such proof.

### Destination upgrade, recovery and rollback

For the selected no-change outcome, destination projects continue the standard `wf_upgrade` path.
Their backend/store format, embedding identity, existing-index detection, normal incremental/rebuild
policy, and rollback requirements do not change. No conversion, extra migration space, or obsolete
store cleanup is introduced by this wave; users receive no speculative downgrade guarantee.

For a future Lance upgrade, test the existing index in a disposable copy before allowing new-version
writes. Preserve an old-format backup and dependency environment until publication is verified;
rollback must restore that coherent backup plus old dependencies, rather than assume the old reader
can consume newly written fragments. Continue ordinary generation fences and existing retry recovery.
For a future SQLite migration, retain Lance as the source until vector/payload conversion and derived
registry/FTS publication verify, reuse compatible stored vectors, budget temporary disk for both
stores, and recover interrupted conversion by discarding only the unpublished staging store.
Switch authority only after verified publication; rollback restores the prior coherent store and
state together. The required Stage 2 layout experiment decides transaction boundaries before this
becomes implementation guidance. No old store/dependency is removed on a partial migration.

## Bounded Implementation Review

Independent reviewer `vector_readiness/primer` found no actionable issue in the implemented
no-change outcome. This is implementation verification, **not** required delivery-lane or council
approval. The reviewer used the candidate interpreter, ran all five oracle tests without skips,
and verified the following counterexamples and receipt facts:

| Probe | Expected | Observed |
| --- | --- | --- |
| Wrong normalization/filter timing; omitted closer row; duplicate physical ID; wrong or NaN distance; empty-filter leakage | Oracle rejects incorrect result | All adversarial cases rejected |
| Existing destination directory passed to either CLI | Refuse before writes | FileExistsError; sentinel and contents unchanged |
| Evaluation artifacts included in distribution | Packaging excludes them | should_exclude true for both drivers, tests and receipt |
| Incorrect query summary arithmetic | Recompute from retained samples | All 180 medians/p95 matched seven samples |
| Invalid SQLite rejection or driver provenance | Matching hashes, frozen thresholds, matching driver bytes | Verified both paths exceed limits and both driver SHA256 values match |

Reviewed Git objects: vector driver `4e28a69d566e8d0c1d4755e15b3e0e71b5adb0e6`,
lifecycle driver `2f63d552e861ee4c6dffc1af0471141917cb2154`, oracle tests
`ac8970f12e86c8fd5a6f1dc383728517f675e8f1`, receipt
`c9d02c5b0d70bf7419b98d5b655ac13a530e42d8`, indexer
`b65b624f86d1467079066140698a4574de6d8fea`, compaction reference
`989275aa92f53bf97bf559161e408ccfbe21dbd3`. Production runtime diff is documentation-only.
The review did not rerun performance, platform, crash or destination probes, and does not fill the
explicit qualification gaps. Pilot revision provenance remains incomplete as documented.


## Final Delivery Review and Verification (2026-09-08)

**PASS for the evaluation/no-production-change outcome.** Required code, QA, architecture,
performance and release approvals and readiness/delivery council approvals are recorded in
`events.jsonl`. This does not approve SQLite adoption or close the wave. All tasks are reconciled;
AC-3 remains explicitly `[~]` with engine-specific executed and unexecuted reliability scope.

The standard council ran the isolated red-team primer first (`vector_readiness/primer`), followed
by docs-contract review. Its strongest challenge was causal attribution: the shared exact-path
quality loss cannot establish intrinsic SQLite deficiency or a sole reranker cause. Its strongest
alternative was retaining 0.33 and investigating reranker stability under unchanged quality gates.
Both were accepted. No material disagreement remains about the no-change outcome or Stage 2 stop.

Initial independent code/QA review found VP-NaN and VP-Phase. The coordinator repaired both in
cycle 1, then a fresh independent reviewer (`vector_final_reverification`) verified them through
actual validator boundaries and in-memory mutants. The earlier reviewer also rechecked them but
retained initial-review context; that recheck was not used as fresh typed clearance. The fresh
reviewer's code/QA/docs-contract synthesis and architecture/performance/release perspectives share
one context, not multiple independent votes. Other independent specialist and docs reviews support
the same result; the original comparator author did not independently approve their own code.

| Reviewer perspective / control | Before repair or known-bad input | Final executed observation |
| --- | --- | --- |
| Code / QA: VP-NaN, `vector_public_filter_smoke.assert_response` | NaN survived cosine tolerance | Eight nonnumeric/nonfinite controls reject; valid finite response passes; deleting the guard in memory makes the targeted test fail |
| Code / QA: VP-Phase, `vector_public_compare.validate_attempt` | Removing embedding or rerank events still accepted a semantic trace | 24 actual trace omissions across all four lanes reject; deleting each new guard produces six targeted assertion failures |
| Docs-contract: repetition and numeric proof | Missing/duplicate repetitions or nonfinite metrics | Rejected; repaired real receipts validate with 138 semantic and 27 lexical calls per lane |
| Architecture / performance | Incomplete integration evidence; potential timing overclaim | AC-3 omissions explicit, no Stage 2/adoption claim, single-call versus cumulative vector timings distinct, full-query latency descriptive |
| Release | Potential implication of destination/platform qualification | Installed dependencies and runtime behavior unchanged; platform, Lance interruption/destination rollback and migration gaps remain explicit |

Frozen reviewed tree fingerprint: `cd4ddba471cb5157df7cfd6b979c3d11e3e723277e40bf0402d3b711b705ebc4`
(SHA256 of ordered `<git-object> <repo-relative-path>\n` entries). It covers the three public
drivers, their three test files, public JSON receipt, and the change document before this
report-only update. The comparator Git object is `d6334e653adf722a7b0b6e9b47d3b57129b239f4`;
filter smoke is `d1a4aebf0fe8b5946ce2a334526e73aaa7a8f55c`; public receipt is unchanged at
`d176391f7ecf9a08edfa1c242069d140f1030d09`. Review budget was five minutes for focused
reverification; sweep rule used targeted tests per mutant, with no broad model/benchmark reruns.
All five integrity checks were affirmed for the executed, bounded evidence; public-path claims
refer to the development comparator/filter boundaries and the separately retained model runs.

Final validation:

- Eleven focused public-evaluation tests passed without skips; replay of all four retained receipts
  preserves 165 measured calls per lane and zero / six / six metric failures for latest ANN /
  latest exact / SQLite. Historical raw receipts were not overwritten.
- All four repaired real-storage public filter CLI runs passed 13 cases plus invalid-kind rejection.
  Additional receipts: `/tmp/wf-vector-eval-1xhbo-filter-<lane>-repair.json`.
- Canonical full suite: **8,578 tests across 79 files, three skips, PASS in 207.949 seconds**.
  The preceding run failed only the unchanged TechDocs ancestor-walk timing assertion
  (297.76 ms versus 150 ms); it passed in isolation in 57 ms, then the complete canonical rerun
  passed. No TechDocs code, timing threshold or test coverage was changed.
- Review-derived memory proposal returned zero candidates. Framework edit gate is closed.
  Operator signoff/closure and commit remain unrequested.
