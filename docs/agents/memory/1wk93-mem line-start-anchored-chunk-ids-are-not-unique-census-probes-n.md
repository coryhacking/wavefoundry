# Line-start-anchored chunk ids are not unique; census probes need the same-line-sibling shape

Owner: Engineering
Status: active
Last verified: 2026-08-29

Memory ID: `1wk93-mem line-start-anchored-chunk-ids-are-not-unique-census-probes-n`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-08-29
Updated: 2026-08-29

## Summary

Wave 1wl7u delivery review (CODE-DEL-1): the prose-id ordinal census cleared the tree-sitter HTML markup chunker because its fixture placed one element per line, making the {slug}-L{start} id anchor look collision-free; an executed one-line sibling probe (the compact/minified-HTML shape) collided (#section-L1 x2, doc-kind, silent last-writer-wins in the id-keyed delta planner) on the DEFAULT dispatch path. A line-start anchor is NOT a uniqueness guarantee: same-line siblings share it. Repair: thread the repeat-only ~k dedupe over the anchored base and pin the one-line shape (test_treesitter_html_same_line_siblings_dedupe). Census discipline: id-collision probes must include the compact one-line form of every markup family, and a generalization like "line-anchored, no collision" needs a hostile same-line fixture before it is recorded.

## Evidence

- `CODE-DEL-1`
- `ev-code-del-1-3`
- `test_chunker.ProseIdOrdinalTests.test_treesitter_html_same_line_siblings_dedupe`
- `1wl7u`

## Targets

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
