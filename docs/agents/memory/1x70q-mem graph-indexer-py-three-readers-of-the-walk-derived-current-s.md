# graph_indexer.py: three readers of the walk-derived current set, and the impacted-docs pass touches disk

Owner: Engineering
Status: active
Last verified: 2026-09-04

Memory ID: `1x70q-mem graph-indexer-py-three-readers-of-the-walk-derived-current-s`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-09-04
Updated: 2026-09-04
Source exploration cost: 1539381
Source event: `repeated-repairs:1x54z:graph_indexer.py`
Validation: promote
Validated by: agent
Action delta: When a merge-side preservation widens the current set, widen it in the finalize prune, in _current_paths for link and memory resolution, and skip the record in the impacted-docs rescan; test with scandir denied AND os.stat raising EACCES for the subtree's children.
Validation rationale: The draft counted repairs without the mechanism. The verified mechanism (CODE-DEL-1, RED-RV1-1, ARCH-RV2-1) is that GraphIndexSession reads the walk-derived current set in three places and touches disk in the impacted-docs pass, where Path.exists raises EACCES under a real mode-000 directory on Python 3.13; the class's scandir-only injection left stat succeeding and missed the crash until a lane ran a real chmod.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

GraphIndexSession uses the walk-derived current set in the finalize prune (known minus current), in _current_paths for doc-link, backtick-path and memory-target resolution, and implicitly in the impacted-docs rescan, which calls Path.exists and read_text on stored records whose cached mentions intersect a changed symbol. Wave 1x54z widened the first two with the store's known paths under unreadable_dirs and made the rescan skip shadowed records, because Path.exists on a child of a mode-000 directory raises EACCES on Python 3.13 rather than returning False and every build during the outage raised. A scandir-only injection leaves stat succeeding and cannot see that crash; the faithful fixture denies scandir on the directory and makes os.stat raise for its children (the _mode_000_children helper).

## Evidence

- `CODE-DEL-1`
- `RED-RV1-1`
- `ARCH-RV2-1`
- `test_symbol_rename_during_outage_leaves_the_shadowed_doc_untouched`
- `test_doc_edited_during_outage_keeps_its_link_edges_into_the_subtree`
- `1x54z`

## Targets

- `.wavefoundry/framework/scripts/graph_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
