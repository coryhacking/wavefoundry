# Indexer exclusions need a test through the files= build entry

Owner: Engineering
Status: active
Last verified: 2026-10-01

Memory ID: `1zfmd-mem indexer-exclusions-need-a-test-through-the-files-build-entry`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-10-01
Updated: 2026-10-01
Source exploration cost: 113318
Source event: `finding:1zim2:DEL-1ZIM2-FILES-SEAM-UNPINNED`
Validation: promote
Validated by: agent
Action delta: When an indexer exclusion is claimed on the explicit files= build path, pin it with a test that calls build_index(files=...) with an include prefix that would otherwise admit the path.
Validation rationale: A helper-only test left the build-path filter call unpinned (mutation survived); the include prefix is needed because the project-layer framework filter otherwise hides the mutation.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Testing an exclusion helper directly does not pin its call in _build_index_locked: replacing the call with pass survived. The pinning test drives build_index(content='code', files=[...]) with project_include_prefixes re-admitting the subtree; without that prefix the project-layer .wavefoundry filter drops the path anyway and the test is vacuous.

## Evidence

- `DEL-1ZIM2-FILES-SEAM-UNPINNED`
- `ev-del-1zim2-files-seam-unpinned-3`
- `1zim2`

## Targets

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
