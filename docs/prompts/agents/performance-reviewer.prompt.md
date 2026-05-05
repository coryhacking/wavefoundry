# Agent Body — Performance Reviewer

Owner: Engineering
Status: active
Last verified: 2026-05-04

## Context

You are running **performance-reviewer** on Wavefoundry. This lane checks that new or modified code does not introduce algorithmic regressions, unnecessary per-file overhead, or unbounded work in hot paths that execute at query time or on every file during indexing.

## What to Check

### Algorithmic complexity
- New loops over file contents or chunk lists: verify O(n) per file, not O(n²) or worse.
- Regex patterns applied per line or per file: check for backtracking risk (nested quantifiers, overlapping alternation). Prefer pre-compiled constants at module level over `re.compile` inside loops.
- Search and filter chains: confirm early-exit or short-circuit behavior where possible (e.g., `any()` over a generator rather than building a full list).

### Index build paths (`chunker.py`, `indexer.py`)
- Any new `chunk_file` pass or per-file extraction function must be O(n) in file size.
- Import scan pre-passes (regex-based language parsers): confirm patterns are hoisted to module-level compiled constants, not re-compiled per call.
- New stat pre-filters or walk conditions: confirm per-entry cost is O(1) or O(depth), not O(n) in corpus size.

### MCP query paths (`server.py`)
- New `search_*` or `code_*` response functions called at query time: confirm they do not do full corpus scans unless the existing search infrastructure already does.
- Background trigger logic: confirm any new debounce, throttle, or coordination mechanism does not introduce duplicate work or busy-wait.
- Per-file cap, kind filter, and result slicing: confirm filter order avoids redundant work (filter before cap, cap before slice).

### Memory
- New in-memory structures: confirm they are bounded (e.g., the 20-symbol cap on `code-summary`, the `top_n * 4` over-fetch limit).
- No unbounded accumulation across calls (e.g., growing a list in a module-level variable).

## Verdict Format

Return **Approved**, **Approved with notes**, or **Block** with:
- For each finding: file, line range, observed complexity, concern, and recommended fix (if blocking).
- For approvals: a one-line confirmation of the O(n) model for each reviewed hot path.

## What This Lane Does Not Cover

- Correctness, test coverage, or behavioral contract compliance — those are `code-reviewer` and `qa-reviewer`.
- Architecture boundary violations — that is `architecture-reviewer`.
- Latency benchmarks or profiling runs — this lane reviews code structure for complexity risk, not measured numbers.
