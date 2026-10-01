# Archived Wave Ledgers Are Not Recognised as Machine Authority

Change ID: `1zicn-bug archive-ledger-exclusion`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-09-30
Wave: 1zilw validation-correctness-fixes

## Rationale

A downstream validation of v1.28.0 (request 8), verified: `review_evidence.is_canonical_wave_events_path` decides whether an `events.jsonl` is a wave's machine-authority ledger from its position under `WAVES_ROOT` (`record_paths.unvalidated_record_roots`), and never consults `ARCHIVE_ROOT`. Its callers are the indexer's retrieval exclusion (`indexer._filter_canonical_wave_event_ledgers` and the file walk) and `machine_authority.is_machine_authority_path`, used by the secrets scan. So with an archive root configured, an archived wave's raw ledger is semantically indexed and treated as ordinary content by the secrets scan. Every other wave-record reader that matters (chunk tagging, reconcile scan, memory backfill and supply, server lookups) already handles the archive root.

## Requirements

1. **Archive ledgers are canonical too.** `is_canonical_wave_events_path` also accepts `events.jsonl` in a wave folder directly under the configured archive root, with the same depth rule as the waves root (one segment, or 1 to `MAX_DEPTH` when nested). With no archive root configured, behaviour is unchanged.
2. **Local derivation.** The predicate derives the archive location from `record_paths.ARCHIVE_ROOT` itself, with the same canonical-part parsing it uses for the waves root; `record_paths.unvalidated_record_roots` and `RecordRoots` are not changed (they never fill `archive_rel`, and filling it would change the indexer's chunk-tagging fallback). Its docstring stops saying "under the waves root" only.
3. **Both callers follow.** The indexer exclusion and the machine-authority predicate pick this up through the shared function; no caller keeps its own rule.
4. **Platforms.** Windows, macOS, Linux and WSL2 behave the same (path predicate).
5. **Transition.** Applies from the next index update after the release; an already-indexed archived ledger leaves the index on that update. CHANGELOG under `### Fixed` in `## [Unreleased]`.

## Scope

**Problem statement:** archived wave ledgers are semantically indexed and secret-scanned as content because the ledger predicate ignores the archive root.

**In scope:**

- `review_evidence.is_canonical_wave_events_path` and its docstring; tests; CHANGELOG.

**Out of scope:**

- Changing archive semantics elsewhere (already archive-aware).

## Acceptance Criteria

- [x] AC-1: with an archive root configured, `events.jsonl` in an archived wave folder is canonical (excluded from semantic retrieval and recognised as machine authority); a file at the wrong depth or with another basename is not; with no archive root, results are unchanged.
- [x] AC-2: the indexer exclusion and `is_machine_authority_path` both reflect AC-1 through the shared predicate; tests set the archive root by patching `record_paths.ARCHIVE_ROOT` and cover the nested layout (depth `MAX_DEPTH` accepted, `MAX_DEPTH + 1` rejected).
- [x] AC-3: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Archive branch in the predicate.
- [x] Tests through the indexer filter and the machine-authority predicate.
- [x] CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Predicate | implementer | readiness | |
| Review | code-reviewer, qa-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`, `.wavefoundry/framework/scripts/tests/test_indexer.py`

## Affected Architecture Docs

N/A: one predicate.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The defect |
| AC-2 | required | Shared definition |
| AC-3 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-30 | Delivery review: red-team and the four lanes (code, qa, release, security) approved, every mutation killed by the suite. Advisory taken: the code and test comments cited wave 1zicq instead of 1zilw (corrected). Not taken: a boundary test pinning the 2 s pid-reuse tolerance (pre-existing gap from 1zc7n, out of scope; follow-up); the shared custom-marker fixture uses symlinks, which can error on Windows without symlink privilege (pre-existing exposure shared with `test_custom_marker_requires_exact_legacy_inventory`). Full suite: 10200 tests OK | Full suite; delivery review |
| 2026-09-30 | Implemented. `is_canonical_wave_events_path` checks the waves root and, when `record_paths.ARCHIVE_ROOT` is a string, its canonical parts, with the same depth rule; `unvalidated_record_roots` unchanged; docstring updated. Test `test_archived_wave_ledgers_are_canonical_too` (patching `ARCHIVE_ROOT`): unset archive unchanged; depth-1 archived ledger canonical (both separators); wrong basename, root-level and too-deep rejected; nested `MAX_DEPTH` 2 accepts depth 2 and rejects 3; `is_machine_authority_path`, `walk_repo` and `_filter_canonical_wave_event_ledgers` all follow. `test_indexer.py` 382 OK | Focused run |
| 2026-09-30 | Readiness round 1: approved by red-team and the lanes; notes folded in: derive the archive location locally (`unvalidated_record_roots` never fills `archive_rel`), patch `ARCHIVE_ROOT` in tests with a nested depth case, docstring, honest secrets-scan risk row | Prepare council and lane review |
| 2026-09-30 | Planned from the v1.28.0 downstream validation (request 8), verified: the predicate reads only `waves_rel`; callers are the indexer filter and walk and `machine_authority.is_machine_authority_path` (secrets scan); chunk tagging, reconcile scan, memory backfill and supply already handle `archive_rel` | Code reads |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Extend the shared predicate | One definition for every caller | Special-case the archive in the indexer only |

## Risks

| Risk | Mitigation |
| --- | --- |
| Secrets scan now skips archived ledgers | Parity with live ledgers, which it already skips. Ledgers are written through `wf_review_event` and can carry free-text evidence an agent or operator supplied, so this is an accepted exemption, not a claim that the content is machine-only. The exemption applies only in the scanner's non-git fallback walk; tracked files in a git repository are still scanned |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
