# LanceDB list-offset corruption — trigger, signature, workaround

Owner: Engineering
Status: active
Last verified: 2026-09-09

Reference for the LanceDB list-column offset-corruption bug that motivated the index reclaim ladder
(wave `1p9aj`). Retain the recovery guidance until the observed failure is reproduced and verified fixed.

## Symptom

`table.optimize(cleanup_older_than=timedelta(0))` on a heavily-appended LanceDB table raises:

```
Max offset 1939874 exceeds length of values 1126298
  at lance-encoding-7.0.0/src/encodings/logical/list.rs:211
```

The table's on-disk size balloons far past its live working set (observed **`docs.lance` at 1.6 GB over
a ~55 MB / 16,992-row working set**) because in-place compaction can no longer run, so stale
fragments/versions accumulate unbounded.

## Observed conditions and diagnosis limits

The original incident followed approximately 390 incremental appends to a table with a
single-level `lines list<int64>` column. Compaction failed with the signature above while
reading and rewriting the live rows succeeded. This establishes a useful recovery path,
but does not establish an append-time writer offset-rebasing defect as the root cause.

## Upstream and current probe

[Lance PR 7546](https://github.com/lance-format/lance/pull/7546), associated with issue
7538, describes a **nested-list decoder** correction. It does not by itself establish
that Wavefoundry's single-level-list incident has the same cause or is fixed.
[PR 8382](https://github.com/lance-format/lance/pull/8382) also concerns Arrow offsets;
its existence alone is not a regression test for this incident.

On 2026-09-08, wave `1xhbo` ran the previously documented 400-append example against
LanceDB **0.33.0 and 0.38.0**, both with PyArrow 25.0.0. Each produced 20,000 rows,
completed optimization, and retained identical keyed list payloads. The example below
is therefore a **stress probe, not a confirmed reproducer**. Because the baseline did
not fail, the upgrade's effect on the historical defect remains **inconclusive**.
Neither the recovery of an already affected table under 0.38.0 nor prevention of the
original failure was proven; the workaround remains enabled.

```python
# Use a fresh disposable directory; this probe may not reproduce the historical failure.
import lancedb, pyarrow as pa
from datetime import timedelta

db = lancedb.connect("/tmp/lance-offset-probe-fresh")
schema = pa.schema([("id", pa.int64()), ("lines", pa.list_(pa.int64()))])
tbl = db.create_table("t", schema=schema)
for i in range(400):
    tbl.add([{"id": i, "lines": list(range(i % 37))} for _ in range(50)])
before = tbl.to_arrow().to_pylist()
tbl.optimize(cleanup_older_than=timedelta(0))
after = tbl.to_arrow().to_pylist()
key = lambda row: (row["id"], row["lines"])
assert sorted(before, key=key) == sorted(after, key=key)
```

## Workaround (shipped — wave 1p9aj)

In the observed incident, reads succeeded despite the compaction failure, allowing reclamation by
**rewriting fresh** from in-memory Arrow data. If the read also fails, this tier cannot recover the table:

```python
data = tbl.to_arrow()                                   # reads fine
db.create_table("t", data=data, mode="overwrite")       # fresh write -> correct offsets, no corruption
# then rebuild the vector index and optimize; lexical FTS5 is stored separately
```

Proven: **`docs.lance` 1.6 GB → 55 MB, zero re-embedding**, FTS + vector search intact.

**Do NOT use `db.rename_table`** for the swap — it raises `NotImplementedError: rename_table is not
supported in LanceDB OSS`, and a drop-then-rename leaves the table missing if the rename fails. Use
`create_table(mode="overwrite")`.

This is implemented as the tiered `indexer.reclaim_lance_table` (optimize → compact-by-rewrite →
full-rebuild) behind the `index_optimize` MCP tool, the self-heal in the build finalize + incremental
paths, and the automatic reclaim at the end of `setup`/`upgrade`. See
`docs/architecture/chunking-and-indexing-pipeline.md` → *Compaction and reclaim*.
