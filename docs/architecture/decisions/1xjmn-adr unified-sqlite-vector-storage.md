# 1xjmn-adr — Unified SQLite storage for docs and code retrieval

Owner: Engineering
Status: accepted
Last verified: 2026-09-09

## Context

Before this conversion, Wavefoundry kept docs and code vectors in separate LanceDB stores, while SQLite held
FTS, chunk registry and indexing state. Text is duplicated across the stores, and vector writes
commit separately from their metadata and FTS updates.

The reviewed current-corpus experiment in wave 1xhbo compared separate SQLite vector/state files
with a unified layout. Tested results matched; steady database storage fell from 248.04 to
164.31 MiB and combined vector/FTS/payload p95 was 38.53 versus 33.56 ms. A process-interruption
probe demonstrated that a shared transaction removes the vector/metadata split-commit window.
These are bounded storage-prototype findings, not proof of production migration, all supported
platforms, larger-corpus performance or uninterrupted query availability.

The operator selected this conversion and requested an ADR. The production implementation passed
its local gates, packaged migration/recovery checks and technical reviews. This accepted record
captures the qualified runtime, schema and operating envelope. Acceptance does not substitute for
native testing on other platforms or the operator’s release decision.

## Decision

Use **SQLite with sqlite-vec for both docs and code in one project-local database file**:

```text
<project-root>/.wavefoundry/index/index-state.sqlite
```

Keep the existing database filename and location. Each configured project root owns its own index;
this is not a machine-global database or a database server. In the Wavefoundry source repository the
path is `/Users/coryhacking/Developer/wavefoundry/.wavefoundry/index/index-state.sqlite`.
Before migration, this file served FTS/state while vectors lived in `docs.lance` and `code.lance`.
After verified conversion, it also owns the canonical chunks and vectors; the legacy stores are retired
through the guarded cleanup described below. SQLite's `-wal` and `-shm` companions, when present,
belong to this same database, not separate docs/code stores.

Docs and code remain separate logical search populations inside the shared file. The evaluated
layout uses these table families, now frozen in the Gate 1 production contract:

| Content | Canonical text and metadata | Embeddings | Full-text search |
| --- | --- | --- | --- |
| Docs | `chunks_docs` | `vectors_docs` | `fts_docs` |
| Code | `chunks_code` | `vectors_code` | `fts_code` |

Store chunk text once in its canonical table. Vector child rows contain embeddings and their identity
metadata, with no text copy. External-content FTS indexes the canonical text by shared internal integer
key, retaining its own term/posting data without storing a second full-text copy. Preserve public chunk
IDs within their docs/code layer and keep FTS populations separate so BM25 corpus statistics do not change.

Use the evaluated float32 exact cosine path initially. Preserve models, chunking, filters before top-k,
candidate counts, hybrid fusion and reranking. A single transaction commits related chunk, vector, FTS,
registry/digest and file/layer-state mutations. Prepare embeddings outside the writer transaction.
Retain existing publication fences and current-generation checks for graph and other work outside
this database. The migration receipt records progress/recovery evidence; SQLite remains the semantic
publication authority. Other project databases and graph storage are outside this consolidation.

Convert destinations through the standard `wf_upgrade` and canonical setup paths: qualify runtime and
exclude stale processes, stage beside the original stores, reuse compatible embeddings, reconcile
sources, verify and publish, then verify from newly loaded processes. Only afterward may cleanup
remove proven obsolete `.wavefoundry/index/docs.lance/`, `.wavefoundry/index/code.lance/`,
`.wavefoundry/index/__manifest/`, staging files and the rollback snapshot. Verify all three legacy
directories stay absent after normal search, refresh/rebuild and reopen; retain them on failed
conversion. The project's source `docs/` and `code/` directories are never these cleanup targets. Retain dependencies
still needed by other projects or whose ownership/use cannot be proved. After successful cleanup,
downgrading requires rebuilding the old-format index with compatible older code/runtime.

## Qualified Local Runtime and Compatibility Contract

Use APSW 3.53.4.0 with its private SQLite 3.53.4 amalgamation and sqlite-vec 0.1.9. Local runtime
checks passed on macOS ARM64 with Python 3.11.13 and 3.13.5. Every connection to the shared semantic
file uses this binding; graph/memory files retain their separate contracts. Preserve Python 3.11 and
existing supported platforms. Native target tests follow local implementation/package testing by
operator direction; wheel compatibility metadata is not a native execution pass.

Schema version 7 uses the table families above, external-content FTS and FP32 cosine. Production
helpers are `sqlite_runtime.py`, `sqlite_vector_store.py` and `sqlite_storage_migration.py`. Existing
old-host shutdown confirmation and strict locks govern the standard upgrade restart/resume path;
a migration receipt survives generic checkpoint loss and is reconciled before further mutation.
No separate bridge release is permitted. Adapter, migration, performance and local package gates passed. Native execution on other supported
platforms remains pending the operator’s subsequent package testing; wheel metadata is not execution evidence.

The existing protocol-1 package path requires source version 1.8.0 or newer; the older migration
warning constant of 1.4.0 does not override that hard preflight boundary. Preserve both existing
behaviors without introducing a bridge release for this conversion. Staging explicitly recognizes
historical state schemas 4, 5 and 6 and preserves their auxiliary tables while adding later
bookkeeping tables. Normal runtime opens only schema 7; unknown formats are retained and refused.
Historical supported models use 384-dimensional vectors, but model identity still controls reuse
and normal reconciliation.

## Qualified Local Implementation

Actual adapters passed three paired, alternated golden runs with zero additional relevance loss
against the corrected LanceDB baseline. Public query p95 stayed within the 1.10x budget. Registered
tool worker peak RSS, including query embedding and reranking models, was 808.52 MiB for SQLite
versus 857.69 MiB for LanceDB. These local measurements do not qualify other hardware.

Exact float32 scans with up to 240 hydrated candidates passed the 100 ms p95 budget through
55,990 docs vectors and 50,000 code vectors. Global p95 at those bounds was 67.03 and 60.36 ms,
respectively. The first measured failing tier was 250,000 per layer (approximately 282/292 ms);
larger tiers were not run. The crossover is an interval between each passing bound and 250,000,
not a claimed exact corpus size. Migration preflight retains a recoverable blocker above these
qualified bounds; later growth raises a health advisory while correct searches continue.

The production adapter uses one SQL statement for exact distance, filtering and hydration under
one read snapshot. Its measured production results supersede the prototype's slower one-SQL
variant; the earlier experiment did not establish a permanent query-shape requirement.

Actual semantic publication passed the 1,000 ms p95 budget at 10/50/250/1,000 chunks
(681/714/810/963 ms). The initial 1,000-chunk result failed at 1,175 ms; equivalent native
validation and indexed canonical digest queries repaired that bottleneck without removing guards.
The final-source 1,000-chunk semantic-publication recheck passed at 962 ms, leaving little
margin on this hardware. The full epoch in that same run was 6,159 ms p95; the 1,000 ms budget
applies to semantic publication, not embedding, graph preparation or the whole epoch.

Ten paired delete/reinsert cycles exercised 800 public queries per backend. Neither accepted a
mixed generation or returned an unexpected error. Expected epoch refusals were 211 for LanceDB
and 180 for SQLite; event-to-searchable p95 was 23.90 versus 15.20 seconds. These local G3 gates
passed. Standard packaged upgrades, parent-owned memory publication and ordinary interrupted retry,
receipt-bound cleanup and independent reopen also passed locally. All seven specialist reviews and
the final council approved technical/local delivery. Nine migration destinations reclaimed 9,791,112
bytes; shared dependencies remain installed where other consumers are not proven absent. Native
other-platform qualification and the operator’s release decision remain pending. Machine receipts,
raw outcomes and limitations are retained with the conversion change.

## Consequences

**Positive:**

- One text copy and one semantic database file per project reduce storage and synchronization work.
- Docs/code searches keep distinct ranking populations while related writes can share one transaction.
- Fresh SQLite installs and normal queries no longer need LanceDB; a lazy migration reader supports legacy upgrades.
- Backup, health and maintenance can inspect one semantic store; graph/memory/other databases retain their own contracts.

**Negative / tradeoffs:**

- Exact vector scans need a measured operating envelope; the experiment does not establish million-vector performance.
- A supported patched SQLite runtime/native extension must be delivered and tested on each supported platform.
- Migration temporarily requires old stores, a coherent rollback snapshot, staged SQLite and WAL space.
- Old loaded processes, native bindings and database handles require explicit exclusion/restart handling.
- Cleanup deliberately ends snapshot rollback; shared environments may retain LanceDB until other consumers migrate.

**Constraints imposed:**

- Conversion wave 1xjmm gates G0–G6 govern readiness, runtime, correctness, quality/resources/availability,
  migration/recovery, cleanup and release. No failed or missing gate is a pass.
- No new search-quality regression, silent unsupported-format reset, duplicate text, premature source deletion
  or false completion status. A migration failure retains actionable recovery state.
- Keep float32 as the conversion baseline. Quantization is a separate decision; SQLiteAI sqlite-vector
  remains deferred by the operator for licensing concerns.
- Treat source files as authoritative content and preserve existing auxiliary state. Do not delete the
  entire index directory, introduce permanent dual writes or create a second semantic publication authority.

## Alternatives Considered

| Alternative | Reason not selected |
| --- | --- |
| Keep or upgrade LanceDB as the normal backend | Retains duplicated content and cross-store synchronization; remains the installed behavior until conversion gates pass |
| Separate SQLite vector and FTS/state files | Keeps the demonstrated split-commit window and more duplicated text |
| Merge docs and code into one FTS population | Changes BM25 statistics and retrieval behavior without a requested benefit |
| Force all data into one physical table or every query into one SQL statement | Not necessary for text deduplication or shared transactions; one-SQL hydration was slower in the prototype |
| Rebuild every embedding during conversion | Wastes compatible vectors and can add model/download requirements; reserve rebuilding for incompatible or corrupt inputs |
| Keep permanent dual backends or delete old stores before verification | The former retains complexity; the latter destroys the recoverable source |

## References

- [Conversion plan and gates](../../waves/1xjmm%20unified-sqlite-vector-storage/1xj6o-ref%20unified-sqlite-vector-storage.md)
- [Evaluation and reviewed layout results](../../waves/1xhbo%20lancedb-038-evaluation/1xhdh-maint%20evaluate-lancedb-038-upgrade.md)
- [Evaluation machine evidence](../../waves/1xhbo%20lancedb-038-evaluation/vector-screen-results.json), `sqlite_shared_transaction_layout`
- [Search architecture](../search-architecture.md)
- `index_state_store.STATE_STORE_FILENAME` and `state_store_path`: existing `index-state.sqlite` filename/path contract
