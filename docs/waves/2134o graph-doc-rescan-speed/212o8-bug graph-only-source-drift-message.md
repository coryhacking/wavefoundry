# Source drift message names embedding on graph-only builds

Change ID: `212o8-bug graph-only-source-drift-message`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-19
Wave: `2134o graph-doc-rescan-speed`

## Rationale

When a source file changes during an index build, the indexer's publish-time check raises `SourceChanged("Source changed during embedding: <path>; retry indexing")` and `build_index` retries once with fresh preparation. On 2026-10-19 a graph-only rebuild (`indexer.py --content graph --full`) hit this because a test file was edited mid-build, and the log said "during embedding" although a graph-only build embeds nothing. The neighbouring identity check says "Model/chunker/configuration changed during embedding" the same way. The wording sends an operator looking at the embedding pipeline when the cause is an edited file.

## Product Intent

An operator reading a failed or retried build log sees that a source file changed during indexing, with no suggestion that embedding was involved. Boundaries: the drift detection, the single retry and the exception types are unchanged. AC-1 tests the outcome.

## Requirements

1. The three source-drift messages in `indexer.py` say "during indexing" instead of "during embedding", for every content mode: the two in publish-time validation (the `SourceChanged` raise and the model/chunker/configuration `RuntimeError`) and the removal check's `SourceChanged("Removal source changed during embedding or became unreadable: ...")`. The setup OOM message ("ran out of memory during embedding") is accurate and unchanged.
2. Drift classification does not depend on the message text: `_is_source_drift` keeps recognising `SourceChanged` and `graph_indexer.GraphSourceChanged` by type. Implementation confirms this and records it in the Progress Log; if any consumer matches the old text, it is updated in this change.
3. Retry behaviour, exception types and the `retry indexing` suffix are unchanged.

## Scope

**Problem statement:** Source drift messages name embedding on builds that do not embed.

**In scope:** the three message strings in `indexer.py`, the test that pins the old text (`test_indexer.py`, the `assertIn("Source changed during embedding", ...)` assertion), and one CHANGELOG bullet.

**Out of scope:** moving the drift check earlier in the build, reusing first-pass work in the retry, and the source guard.

**Platform behaviour:** the same on Windows, macOS, Linux and WSL2; only message text changes.

## Acceptance Criteria

- [x] AC-1: A build whose source file changes before publication reports "Source changed during indexing: <path>; retry indexing", and still retries once. Oracle: the existing drift test in `test_indexer.py`, updated to the new text.
- [x] AC-2: No framework source or test still contains "changed during embedding". Oracle: a grep recorded in the Progress Log. ("ran out of memory during embedding" in `setup_index.py` and code comments do not contain the phrase.)
- [x] AC-3: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Change the three messages.
- [x] Confirm no consumer matches the old text; update the pinning test.
- [x] Add the CHANGELOG bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| message | implementer | none | `indexer.py`, `test_indexer.py` |

## Serialization Points

- `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/tests/test_indexer.py`

## Affected Architecture Docs

N/A: message text only; no boundary, flow or contract change.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The operator-visible fix. |
| AC-2 | important | No stale copy of the old wording remains. |
| AC-3 | required  | Standard change-local verification. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-19 | Planned. | Wave 212ym rebuild log: `FAILED — Source drift: Source changed during embedding: .wavefoundry/framework/scripts/tests/test_graph_indexer.py; retry indexing` on a graph-only build. |
| 2026-10-19 | Readiness red-team primer: the removal check in `indexer.py` raises a third "changed during embedding" message, so AC-2 could not pass as scoped. Repaired before any approval: requirement 1 and scope now cover three messages. | Red-team primer report; receipt `review-policy-35275841dd9d4a3ce1a8` superseded. |
| 2026-10-19 | Implemented. Three messages changed; `_is_source_drift` classifies by exception type (`isinstance` on `SourceChanged` / `graph_indexer.GraphSourceChanged`), so no consumer depends on the text. AC-2 grep: no framework file contains "changed during embedding"; the remaining "during embedding" mentions are the accurate setup OOM message and a code comment. | `grep -rn 'changed during embedding' .wavefoundry/framework`: no output; drift test in `test_indexer.py` passes with the new text. |
| 2026-10-19 | Implemented; all ACs and tasks done. Wave paused by operator instruction while 2134s is implemented; the whole framework suite runs before close. | `run_tests.py --file test_graph_indexer.py --file test_indexer.py`: 986 OK. |
| 2026-10-19 | Whole framework suite (last, both waves 2134o and 2134s in the tree): `Ran 11945 tests across 201 files in 722.422s OK` (12 skipped); green receipt. | `python3 .wavefoundry/framework/scripts/run_tests.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-19 | Use one neutral word, "indexing", for every mode. | Simplest; accurate for docs, code, graph and all. | Mode-specific wording: more branches for no operator benefit. Moving the check before finalize: a separate design question, not needed to fix the wording. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A log parser or dashboard matches the old text. | Requirement 2 and AC-2. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
