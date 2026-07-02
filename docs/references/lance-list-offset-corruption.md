# LanceDB list-offset corruption — trigger, signature, workaround

Owner: Engineering
Status: active
Last verified: 2026-07-01

Reference for the LanceDB list-column offset-corruption bug that motivated the index reclaim ladder
(wave `1p9aj`). Retire this note when a single-level-list upstream fix ships.

## Symptom

`table.optimize(cleanup_older_than=timedelta(0))` on a heavily-appended LanceDB table raises:

```
Max offset 1939874 exceeds length of values 1126298
  at lance-encoding-7.0.0/src/encodings/logical/list.rs:211
```

The table's on-disk size balloons far past its live working set (observed **`docs.lance` at 1.6 GB over
a ~55 MB / 16,992-row working set**) because in-place compaction can no longer run, so stale
fragments/versions accumulate unbounded.

## Trigger

Repeated **incremental appends** (the post-edit-hook reindex path — ~390 appends in the observed
session) to a table containing a **list column** (`lines list<int64>` in the docs/code schema). The Lance
encoder does not rebase the list **offset buffers** across page boundaries when writing across multiple
batches, so a later page's offsets reference positions beyond the values buffer they were rebased
against. Reads that don't cross the corrupted page succeed; the **compaction/decode** path that walks all
pages fails.

## Upstream

- lance-format/lance **#7538** — the bug report (offset buffers not rebased across page boundaries in
  multi-batch list writes).
- lance-format/lance **#7546** — the fix, merged but **unreleased**, covering the **nested-list** case
  only. The docs/code column is a **single-level** `list<int64>`, which the fix does **not** cover — so
  the exposure remains until a broader fix ships. This note + repro is the basis for a single-level
  upstream report.

## Minimal repro (single-level list, multi-batch append)

```python
# Reproduces "Max offset N exceeds length of values M" on optimize() with a single-level list column.
# Requires: pip install lancedb pyarrow
import lancedb, pyarrow as pa
from datetime import timedelta

db = lancedb.connect("/tmp/lance-offset-repro")
schema = pa.schema([("id", pa.int64()), ("lines", pa.list_(pa.int64()))])
tbl = db.create_table("t", schema=schema, mode="overwrite")

# Many small appends, each a separate batch, each with a variable-length list column.
for i in range(400):
    tbl.add([{"id": i, "lines": list(range(i % 37))} for _ in range(50)])

# Compaction walks all pages and hits the un-rebased offsets:
tbl.optimize(cleanup_older_than=timedelta(seconds=0))   # -> Max offset ... exceeds length of values ...
```

## Workaround (shipped — wave 1p9aj)

Normal **reads succeed** on the corrupted table (only the compaction/decode path fails), so the table is
reclaimed by **rewriting fresh**, which recomputes the list offsets from clean in-memory Arrow data:

```python
data = tbl.to_arrow()                                   # reads fine
db.create_table("t", data=data, mode="overwrite")       # fresh write -> correct offsets, no corruption
# then rebuild vector + FTS indices and optimize the fresh table
```

Proven: **`docs.lance` 1.6 GB → 55 MB, zero re-embedding**, FTS + vector search intact.

**Do NOT use `db.rename_table`** for the swap — it raises `NotImplementedError: rename_table is not
supported in LanceDB OSS`, and a drop-then-rename leaves the table missing if the rename fails. Use
`create_table(mode="overwrite")`.

This is implemented as the tiered `indexer.reclaim_lance_table` (optimize → compact-by-rewrite →
full-rebuild) behind the `wave_index_optimize` MCP tool, the self-heal in the build finalize + incremental
paths, and the automatic reclaim at the end of `setup`/`upgrade`. See
`docs/architecture/chunking-and-indexing-pipeline.md` → *Compaction and reclaim*.
