# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-05-01

wave-id: `12axj chunker-and-pack-improvements`
Title: Chunker And Pack Improvements

## Changes

Change ID: `12avt-enh exclude-tests-from-framework-pack`
Change Status: `planned`

Change ID: `12avx-enh markdown-chunker-heading-hierarchy`
Change Status: `planned`

Change ID: `12aw5-enh structure-aware-code-chunker`
Change Status: `planned`

## Wave Summary

Three improvements to the framework packaging and indexing pipeline: exclude the test suite from the distribution zip and correct downstream seed guidance that mistakenly references it; add H1 breadcrumb context injection and threshold-gated `###` splitting to the markdown chunker; and add structure-aware declaration-boundary chunking across 15+ languages with doc-comment extraction, annotation handling, and a `CHUNKER_VERSION` rebuild signal.

## Journal Watchpoints

- **`12avx` blocks `12aw5`** — `12avx` introduces `CHUNKER_VERSION` in `chunker.py`; `12aw5` increments it. Both edit `chunker.py` and `test_chunker.py`; do not run them concurrently.
- **`framework_edit_allowed` and `seed_edit_allowed` guard windows** — `12avt` edits seeds and `build_pack.py`; `12avx` and `12aw5` edit framework scripts. Flip guards before each, restore after.
- **`12avt` is independent** — no dependency on `12avx` or `12aw5`; can run in parallel with either.
- **Index rebuild after `12avx`/`12aw5`** — `CHUNKER_VERSION` change triggers automatic full rebuild on next `build_index` call; no manual intervention needed, but note this in the closure checklist.

## Dependencies

- No external wave dependencies.
- Internal ordering: `12avx` must complete before `12aw5` begins (both edit `chunker.py`/`test_chunker.py`; `12avx` introduces `CHUNKER_VERSION`). `12avt` is independent of both.
