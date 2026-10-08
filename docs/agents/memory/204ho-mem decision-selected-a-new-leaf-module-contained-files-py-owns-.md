# Decision: Selected: a new leaf module `contained_files.py` owns read…

Owner: Engineering
Status: rejected
Last verified: 2026-10-08

Memory ID: `204ho-mem decision-selected-a-new-leaf-module-contained-files-py-owns-`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-08
Updated: 2026-10-08
Source exploration cost: 1072877
Source event: `decision-log:1zyv2-bug contained-repo-reads-and-writes:a98ba17d66bcd220`
Validation: reject
Validated by: agent
Action delta: Use the canonical contained-files ownership contract; no separate memory action is needed.
Validation rationale: The Decision Log is supported, but docs/architecture/cross-cutting-concerns.md:184-185 already owns standard-library containment and member-reader delegation; a second basename-only policy copy adds no durable action.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates

## Summary

Decision (wave 200ey): Selected: a new leaf module `contained_files.py` owns read and write containment, and `_read_member_doc_bytes` delegates to it.. Rationale: `lifecycle_gate_support` imports `review_policy`, `review_evidence`, `record_paths` and more, so importing it from `render_platform_surfaces`, `install_log_lib` or the hook path would pull the lifecycle stack into small processes and risk import cycles (`200v1` already needed a function-local import). A leaf module serves every caller, and delegation keeps one rule..

## Evidence

- `1zyv2-bug contained-repo-reads-and-writes`
- `200ey`

## Targets

- `contained_files.py`
