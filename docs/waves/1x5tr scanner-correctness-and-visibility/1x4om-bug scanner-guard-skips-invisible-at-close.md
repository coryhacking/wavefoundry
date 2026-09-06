# A File the Secrets Scanner Skips Is Invisible to the Close Gate

Change ID: `1x4om-bug scanner-guard-skips-invisible-at-close`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-09-05
Wave: 1x5tr scanner-correctness-and-visibility

## Rationale

Raised by the security seat of wave `1x4ol`'s readiness council on 2026-09-04
and deliberately kept out of that wave's scope once the operator declined the
time bound that would have added a new route to it. This record exists so the
disclosed, unfixed gap survives that wave's close instead of evaporating with
the session.

The scanner already skips files it will not read: anything over
`MAX_FILE_BYTES`, any line over `MAX_LINE_BYTES`, and any file whose first 8 KB
holds a NUL byte. Each skip is surfaced two ways, a stderr line from
`_record_scan_skip` and an entry in `_SCANNER_SKIPS`, which is an in-process
list reset at the start of every `check_hardcoded_secrets` run. Discovery correction:
long-line guards currently emit no skip record, and process workers do not return
their skip lists. `scan-state.json.files_skipped` counts content-cache hits, not
guard skips; that existing meaning remains unchanged.

The close-time gate, `_check_secrets_gate`, reasons only over entries in
`docs/scan-findings.json`. A file that was never scanned produces no entry, so
a skipped file passes close with no signal. This is not theoretical: the
current build log shows `Wavefoundry_Executive_Presentation.pptx` skipped by
the binary guard, and that skip reached close silently.

The gate is fail-closed on findings it can see and blind to files it was never
shown. A secret in a skipped file is invisible by construction.

## Requirements

1. A guard skip SHALL leave a durable record naming the path and the reason,
   persisted alongside the scan state rather than only emitted to stderr.
2. `wf_close_wave` SHALL surface all outstanding recorded guard skips as
   `data.scanner_skips`, on success and normal gate-error responses, read-only.
3. Surfacing SHALL be advisory and SHALL NOT change existing finding-classification
   or close-blocking rules. Skip classification is not a new workflow in this change.
4. The record SHALL be cleared for a path only when that path is subsequently
   scanned or removed, never by a run that skipped it again.
5. Preserve outstanding records across incremental cache hits, unrelated scans,
   allowlisted/unreadable candidates, and full scans that do not evaluate a path.
   Worker results and serial fallback SHALL carry equivalent guard outcomes.
6. A malformed/unreadable ledger SHALL produce an explicit advisory at close;
   a scanner persistence failure SHALL be reported as a nonblocking WARNING and SHALL NOT silently replace
   malformed prior evidence with an empty ledger.

## Design

Use one root-local authority, `.wavefoundry/index/scan/guard-skips.json`, even
when an index build uses a custom index directory. The scanner entry point owns
publication, so direct, CLI, and index-driven scans converge on the close reader.
Store a versioned path-keyed JSON ledger containing relative paths and guard
reasons/details only, never source content or secret material. Atomically replace
under a short `RuntimeFileLock` protecting the read/merge/write; preserve unrelated
concurrent deltas. No lock spans file scanning. Missing is empty; malformed is an
error. Clear only affirmative complete scan outcomes (including empty text), or
confirmed filesystem absence; an I/O error is not removal. Re-skips replace that
path's reasons and remain outstanding. Cache hits are not scan outcomes.

Keep `scan_file_raw`'s three-value public return contract. Add internal per-file
outcome transport to the parent, including process workers, without changing raw
finding evaluation. Report overlong-line coverage once per file, retaining findings
on ordinary lines; preserve the existing character-count guard threshold. Binary
extension and NUL-sniff guards are separate tested reasons. The new advisory reader
only reads the ledger and initiates no scanning or writes. Existing close validation
remains intact: `run_validate` reaches docs-lint's record-only scanner and may publish
scanner observations before the added reader runs. Persistence errors use WARNING
output, so they do not indirectly turn advisory skips into docs-lint close blockers.
When a run's observations are not published, none of that run's paths is cached as
scanned (a path the ledger cannot name is likewise left uncached), on the indexer scan and
the `wf_scan_secrets` subprocess alike, so the next run re-observes them; each path is
validated on its own so one unrecordable name never vetoes the rest of the delta.
Existing response notice plumbing propagates the advisory without blocking diagnostics.

Missing/empty means no recorded guard skips, never proof of complete coverage.
Deleting the index or this ledger loses observation history; it is populated again
only by subsequent scanning. Bump the existing scanner version so the first indexed
scan after this upgrade runs in full and observes previously cached candidates.

## Scope

**Problem statement:** The close gate cannot see files the scanner declined to
read, so a skipped file carrying a secret passes silently.

**In scope:**

- A persisted skip record beside `scan-state.json`.
- Close-time surfacing of recorded skips as an advisory.
- Tests for each existing guard reaching the record and the gate.

**Out of scope:**

- Any change to which files are eligible for scanning or to the guards
  themselves.
- Any time bound. Operator-declined in wave `1x4ol`.
- Candidate exclusions are owned by sibling change `1x550`; no new guard thresholds,
  secret classification state, cache schema, or background service.

## Acceptance Criteria

- [x] AC-1: File-size, line-length, binary-extension and NUL-sniff guards persist
      path/reason, in serial and process-worker flows; ordinary-line findings survive.
- [x] AC-2: A `wf_close_wave` dry run on a tree with a recorded skip surfaces
      that path and reason in its response, and a tree with none surfaces
      nothing.
- [x] AC-3: A recorded skip is cleared when the path is later scanned or
      removed, and is NOT cleared by a later run that skips it again.
      Cache hits, unrelated scans, unreadability, and allowlisting retain evidence;
      malformed and publication failures are explicit and prior bytes survive.
- [x] AC-4: Deleting the persistence makes a named test fail, recorded as a
      mutation before review.
- [x] AC-5: This change's own suites and every test it adds pass, the documents
      it authors or edits validate, and no failure elsewhere is attributable to
      it.

## Tasks

- [x] Persist guard skips with path and reason beside the scan state.
- [x] Surface recorded skips in the close-wave response as an advisory.
- [x] Add per-guard tests and the clear-on-scan test.
- [x] Record the mutation.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| persist | implementer | — | Record beside scan-state.json. |
| surface | implementer | persist | Advisory in the close response. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py`
- `.wavefoundry/framework/scripts/scan_secrets.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_secrets_validators.py`
- `.wavefoundry/framework/scripts/scanner_skips.py` (small durable-ledger owner)
- `.wavefoundry/framework/scripts/tests/test_scanner_skips.py`
- `.wavefoundry/framework/scripts/tests/test_secret_scan_cache.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`

## Affected Architecture Docs

Update the secrets-gate description in `docs/specs/mcp-tool-surface.md` with the
advisory field, persistence lifecycle, fixed root-local authority, and error behavior.
Also update `docs/architecture/data-and-control-flow.md` State Ownership and
`docs/architecture/domain-map.md` Dependency Direction Rules item 6: distinguish
rebuildable index content from recorded scanner observations, identify scanner writers
and close reader, and disclose history loss on deletion. Update the registered
`wf_close_wave` tool description in `server_impl.py` with the advisory contract.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The record is the whole change. |
| AC-2 | required | Visibility at the gate is the point; visibility in a log is what exists today. |
| AC-3 | required | Without it a skip is either permanent or silently forgotten. |
| AC-4 | required | A guard that survives its own deletion is not landed. |
| AC-5 | required | Standard delivery gate. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-04 | Disclosed by the `1x4ol` readiness council and parked. | `_check_secrets_gate` loads only `docs/scan-findings.json`; `_record_scan_skip` writes stderr and a per-run list; `scan-state.json` keys are counts only; the current build log shows a `.pptx` binary-guard skip that reached close with no signal. |
| 2026-09-05 | Observe: ledger and scanner/close integration complete. Seven scanner integration tests pass, including real spawned workers with a parent-fallback sentinel, forced spawn failure, cache-hit retention, empty-text completion, degraded rules, and version escalation. Eighteen close tests pass, including successful create, dry-run, existing secret block, malformed/missing history and post-validation observation. | `GuardCoverageIntegrationTests` (0.379s); `WaveCloseSecretsGateTests` (1.503s); ledger suite 11 tests, including dangling-link retention, atomic failure and concurrent deltas. |
| 2026-09-05 | Mutation: no-op publication and omitted long-line record each kill the all-guards test with exactly one assertion failure. Removing the worker's fifth outcome field kills the real-worker test at durable-ledger assertion; restored source passes. | `test_all_guards_persist_without_hiding_ordinary_line_findings`; `test_real_workers_publish_all_guards_without_serial_fallback`. Mutants removed before full verification. |
| 2026-09-05 | Observe: tool contract and architecture ownership/deletion descriptions updated; full framework/docs gates remain. | `docs/specs/mcp-tool-surface.md`, architecture domain map and data/control flow, registered close description. |
| 2026-09-05 | Observe: standard delivery verification complete. Full framework runner passes 8,506 tests across 75 files, 3 skips, 185.072s; historical prefix-collapse reason census now includes the newly observable existing line guard. | `python3 .wavefoundry/framework/scripts/run_tests.py`; green test-cache receipt; `/tmp/1x5tr-framework-tests-final.log`. Full docs validation green before final bookkeeping; final handoff validation follows. |
| 2026-09-05 | Delivery review repairs (cycle 2): per-path ledger validation with a WARNING so one unrecordable name cannot veto the delta; guard-skipped paths whose observation was not published stay out of the scan cache; a decoder RecursionError is a malformed ledger; the per-run skip count is pinned. Scratch mutants of each repair fail the named test. | `GuardCoverageIntegrationTests` (two new cases), `ScannerSkipLedgerTests` nested-ledger subtests; findings CODE-DEL-1, RED-DEL-1, RED-DEL-2, RED-DEL-3, SEC-DEL-2, SEC-DEL-3, QA-DEL-1. |
| 2026-09-05 | Delivery review repairs (cycle 3): the `wf_scan_secrets` subprocess path shares the unpublished-outcome seam; a failed publication parks every path the run evaluated so a failed clear cannot pin a stale row; the ledger reader dedupes rows through a set. | `RunSecretsScanGuardHistoryTests`; `test_failed_publication_of_a_clear_does_not_pin_the_stale_row`; findings RED-DEL-9, RED-DEL-10, SEC-DEL-4, DOCS-DEL-5. |
| 2026-09-05 | Delivery review repairs (cycle 4): a removed-only delta now reaches the cache store so a removed file's row is deleted and an identical restore is re-observed rather than cache-hitting with its guard row already pruned; the ledger's duplicate-row dedupe is pinned. | `test_removed_then_restored_guard_skip_is_re_observed`; `test_duplicate_rows_collapse_to_one_on_publish_and_read`; findings CODE-DEL-5, QA-DEL-6. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-04 | Park rather than fold into `1x4ol`. | The finding's premise for inclusion was that `1x4ol` would add a third skip route. The operator declined that route, so `1x4ol` adds nothing to this gap, and a security-visibility change does not belong in a wave scoped to build cost. | **Fold in anyway:** widens a performance wave with a gate change. **Drop it:** the gap is real and live today. |


## Risks


| Risk | Mitigation |
| --- | --- |
| The advisory is ignored like the stderr line is today. | It rides the close response, which is the surface the operator already reads before closing. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
