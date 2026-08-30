# A degenerate-input test does not pin a guard when an earlier fallback enforces the same outcome

Owner: Engineering
Status: active
Last verified: 2026-08-29

Memory ID: `1wllw-mem a-degenerate-input-test-does-not-pin-a-guard-when-an-earlier`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-08-29
Updated: 2026-08-29

## Summary

Wave 1wl7w delivery review (QA-DEL-1): the drawio decompression-bomb test asserted zero chunks, but its payload truncated to UNPARSEABLE bytes, so the XML ParseError fallback redundantly enforced the outcome and a mutant deleting the over-cap eof/unconsumed-tail guard survived the entire suite (538+312 tests). Lesson: a hostile-input test pins a security guard only when the guard is the ONLY deciding condition on that payload; construct the payload so every downstream fallback would ACCEPT it (here: pad the URL-quoted model to a 3-byte %0A boundary so the truncated-at-cap inflate is valid XML, making the guard the sole refusal point), and prove the pin by running the delivered test against the guard-removed mutant. Redundant-outcome oracles pass forever while guarding nothing.

## Evidence

- `QA-DEL-1`
- `ev-qa-del-1-3`
- `test_chunker.DrawioChunkerTests.test_escape_aligned_overcap_page_is_refused`
- `1wl7w`

## Targets

- `.wavefoundry/framework/scripts/chunker.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py`
