# Repaired defect DEL-1ZIM2-FILES-SEAM-UNPINNED

Owner: Engineering
Status: superseded
Last verified: 2026-10-01

Memory ID: `1zg4l-mem repaired-defect-del-1zim2-files-seam-unpinned`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-10-01
Updated: 2026-10-01
Source exploration cost: 113318
Source event: `finding:1zim2:DEL-1ZIM2-FILES-SEAM-UNPINNED`
Validation: rewrite
Validated by: agent
Action delta: When an indexer exclusion is claimed on the explicit files= build path, pin it with a test that calls build_index(files=...) with an include prefix that would otherwise admit the path.
Validation rationale: A helper-only test left the build-path filter call unpinned (mutation survived); the include prefix is needed because the project-layer framework filter otherwise hides the mutation.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zfmd-mem indexer-exclusions-need-a-test-through-the-files-build-entry`

## Summary

Real defect fixed in wave 1zim2: Mutation killed.

## Evidence

- `DEL-1ZIM2-FILES-SEAM-UNPINNED`
- `ev-del-1zim2-files-seam-unpinned-3`
- `1zim2`

## Targets

- `tests/test_indexer.py`
