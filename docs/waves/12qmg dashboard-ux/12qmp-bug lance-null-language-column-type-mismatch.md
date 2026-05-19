# LanceDB Null-Column Type Mismatch on `language` Field

Change ID: `12qmp-bug lance-null-language-column-type-mismatch`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-18
Wave: `12qmg dashboard-ux`

## Bug Description

`_stream_embed_write` crashes on the third batch (chunks 513–768) when the docs index contains JSON files after an all-Markdown first batch.

**Root cause:** `_make_lance_rows` passes `None` through unchanged for the `language` field (and `section`). LanceDB infers the column schema from the first batch written via `db.create_table`. If that first batch contains only Markdown chunks — which produce `language: None` — LanceDB declares the `language` column as type `Null`. When a subsequent batch includes JSON chunks with `language: "json"` (a real UTF-8 string), LanceDB raises:

```
ValueError: Invalid input, cannot cast field 'language' from Utf8 to Null
```

**Affected path:** Any full rebuild where the first 256-chunk batch is all-Markdown and a later batch includes a structured-data file (JSON, YAML, TOML, etc.) that the chunker annotates with a non-None `language` value.

## Rationale

Full index rebuilds fail mid-way — the first two batches succeed, the third crashes — leaving operators with no docs index and no clear error at the surface level. The fix is two lines in `_make_lance_rows`: normalize `None → ""` for nullable string fields before writing to LanceDB. This ensures the `language` and `section` columns are always typed as non-null strings regardless of batch ordering.

## Requirements

1. In `_make_lance_rows` in `indexer.py`, normalize `None → ""` for the `language` and `section` fields before appending the row. Both are `Optional[str]` on the `Chunk` dataclass and are the only fields that can legally be `None` while mapping to a string LanceDB column.
2. The normalization must be applied before `rows.append(row)`, so all callers — both `_stream_embed_write` and `_lance_incremental_write` — benefit from a single fix point.
3. No change to the `Chunk` dataclass or chunker output — `None` remains valid at the chunker layer; only the LanceDB row dict is normalized.
4. A unit test asserts that `None` `language` and `section` values in input chunk dicts produce `""` in the returned row dict.

## Scope

**Problem statement:** Full index rebuild crashes when the first batch is all-Markdown (`language=None`) and a later batch includes JSON/YAML chunks (`language="json"`), because LanceDB infers the column type as `Null` from the first batch.

**In scope:**

- `_make_lance_rows` in `indexer.py` — add `None → ""` normalization for `language` and `section`
- Unit test for the normalization

**Out of scope:**

- Passing an explicit PyArrow schema to `db.create_table` (more robust long-term but larger change)
- Changing `Chunk.language` / `Chunk.section` to non-optional
- Any chunker changes

## Acceptance Criteria

- AC-1: `_make_lance_rows` with `language: None` in the input chunk dict returns a row where `row["language"] == ""`.
- AC-2: `_make_lance_rows` with `section: None` returns a row where `row["section"] == ""`.
- AC-3: Full index rebuild over a repo containing both Markdown docs and JSON docs completes without `ValueError: cannot cast field 'language' from Utf8 to Null`.
- AC-4: All existing indexer tests pass.

## Tasks

- In `_make_lance_rows`, after `row = dict(chunk)` and before `rows.append(row)`, add:
  ```python
  for _nullable_str in ("language", "section"):
      if row.get(_nullable_str) is None:
          row[_nullable_str] = ""
  ```
- Add unit test asserting AC-1 and AC-2

## Agent Execution Graph

| Workstream   | Owner              | Depends On | Notes                               |
| ------------ | ------------------ | ---------- | ----------------------------------- |
| indexer-fix  | framework-engineer | —          | Two-line change in `_make_lance_rows` |
| tests        | framework-engineer | indexer-fix | Unit test for null normalization   |

## Serialization Points

- `indexer.py` `_make_lance_rows` — single change point

## Affected Architecture Docs

N/A — internal implementation detail in `indexer.py`; no boundary, schema, or flow change visible to callers.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Core correctness |
| AC-2 | required  | Same nullable pattern on section; same latent failure mode |
| AC-3 | required  | End-to-end verification |
| AC-4 | required  | No regression |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-18 | Implemented. Added `None → ""` normalization loop for `language` and `section` in `_make_lance_rows` (indexer.py). Added 5 unit tests: AC-1 (language None→""), AC-2 (section None→""), both-None, non-None preserved, input chunk not mutated. 68 indexer tests pass. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_indexer.py'` — 68 OK |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-18 | Normalize `None → ""` in `_make_lance_rows` | Minimal, targeted; fixes both stream and incremental write paths in one place | Explicit PyArrow schema at `create_table` (larger change, deferred) |
| 2026-05-18 | Also normalize `section` | Same `Optional[str]` pattern; same failure mode possible if first batch has `section=None` and later batch has a real heading | Only fix `language` (leaves `section` as latent bug) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Existing rows in the Lance table may store `null` for `language`; incremental adds after this fix store `""` — mixed values until next full rebuild | Recommend full rebuild after deploying; acceptable until then |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
