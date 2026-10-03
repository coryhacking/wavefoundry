# Waveforge Review Follow-ups

Change ID: `1zodv-bug waveforge-review-follow-ups`
Change Status: `implemented`
Owner: implementer
Status: planned
Last verified: 2026-10-02
Wave: 1zls7

## Rationale

The 1zls7 delivery review and a later operator review left six items. Two are defects in the new vendored-script verifier: it follows redirects before it checks them, and it silently drops a file row it cannot parse, so the verifier can report success for a file it never checked. Two are path leaks on surfaces 1zlts made path-free, which remain on other routes. Two are verification gaps: the 1zltr parser census did not cover the `## AC Priority` join, and docs-lint is reported to skip per-change rules for documents with CRLF line endings. Each one weakens a check this wave adds or hardens, so they are fixed here rather than deferred.

## Requirements

1. **Redirects are checked before they are followed.** `verify_vendored_scripts.default_fetch` validates every redirect target against the registry prefix before following it, so an off-registry destination is never contacted, and a chain that leaves the registry and returns to it is refused. A redirect that stays on the registry is still followed. The refusal is a `FetchRefused` (printed `refused:`), as today.
2. **Malformed table rows are refused.** `parse_readme` finds each table by its exact header line (`| File | Package | Source in the tarball | Licence | SHA-256 |` and ``| Package | Tarball | `dist.integrity` |``), each present exactly once, otherwise `ReadmeError`. Every line after the header's separator row, up to the first line that does not start with `|`, is a data row of that table and must fully match that table's row pattern, otherwise `ReadmeError` naming the line, so the run exits 2. Rows are no longer collected with a whole-text `finditer`. A file present in the vendor directory but absent from the file table is unchanged by this requirement.
3. **Memory tools stay path-free under an upgrade hold.** `memory_consolidate` and `memory_purge` are registered as `fail_fast` writers in `publication_control.PUBLICATION_WRITER_REGISTRY` (the `memory_add` / `memory_propose` / `memory_reconcile` precedent), so the upgrade publication guard wraps them: during an upgrade checkpoint they are refused like `memory_add`, `memory_propose` and `memory_reconcile`, and a `ProjectPublicationUnavailable` refusal is rendered by `publication_unavailable_detail` with no absolute path, naming the repository-relative path. Registry pin tests are updated to match. The `memory_purge_failed` diagnostic, which renders a failure with `str(exc)` and can carry an absolute filename outside the upgrade hold, follows the Requirement 4 rendering rule.
4. **The remaining index_health rows are path-free.** The context-efficiency projection monitor's `monitor_error` row and the `authority_unavailable` row never carry an absolute path. An `OSError` is rendered as its class and errno name (`lifecycle_lock._cause_label`), followed by its `filename` made repository-relative when it lies under the root and dropped otherwise; its `strerror` is never echoed (a `RuntimeLockBusy` carries the absolute path in `strerror`). Any other exception's text is kept verbatim only when it contains neither the root (raw, resolved, JSON-escaped or backslash form) nor another absolute path, so diagnostic text such as `ambiguous_wave_id ... at docs/waves/...` survives; otherwise the row carries the class name only. The `authority_unavailable` row has no live producer of an absolute path today; this is defence in depth.
5. **The AC Priority join is censused.** Predicate: every change document (a `.md` other than `wave.md` with a `Change ID:` line) under `docs/waves` (recursive) and `docs/plans`. For each, compare HEAD (`4522b371`) with the working tree on: (a) the close gate's per-AC priority map and open-AC findings; (b) `_check_ac_priority_alignment` findings; (c) `_check_tilde_required_ac_has_inline_note` findings; (d) the `ac_priority_unpopulated` Prepare advisory. Record the count scanned, the count differing and each differing document, explained in the Progress Log. If a difference is a wrong reading, the reading is fixed and pinned by a test; if it is a correct reading, a test pins that shape.
6. **CRLF documents get the same per-change lint as LF ones.** The reported gap (docs-lint per-change rules not running for a CRLF wave record or change doc) is reproduced first. If it reproduces, docs-lint gives the same per-change findings for a document saved with CRLF endings as for the same document with LF endings, on every platform. If it does not reproduce, the Progress Log records the reproduction attempts, and a test pins LF/CRLF parity for the per-change rules either way.

## Scope

**Problem statement:** the verifier can contact an off-registry host and can pass with a file it never checked; two routes still leak absolute paths; one census and one platform parity claim are unverified.

**In scope:**

- `verify_vendored_scripts.py` redirect handling and README row parsing, with tests.
- Path-free refusal text for `memory_consolidate` and `memory_purge` under an upgrade hold.
- Path-free `monitor_error` and `authority_unavailable` rows in `index_health`.
- The AC Priority census, and any parser fix it shows is needed.
- Docs-lint LF/CRLF parity for per-change rules.
- CHANGELOG and docs updates where behaviour changes.

**Out of scope:**

- Any new verifier feature (signature checks, lockfiles).
- Retrieval or index behaviour beyond the two rows.
- Reformatting existing closed wave records.

## Acceptance Criteria

- [x] AC-1: a test with a real local HTTP server shows a redirect to an off-registry URL is refused without that URL being requested, and an off-registry-then-back chain is refused; an on-registry redirect still succeeds.
- [x] AC-2: a README with one malformed file row among valid rows makes the verifier exit 2 and name the row, for a shortened SHA-256 and for a path cell without backticks; the same for a malformed registry row; the shipped README still parses.
- [x] AC-3: under an upgrade hold (a child process holding the locks, and the same-process other-thread branch), `memory_consolidate` and `memory_purge` return the `project_publication_busy` diagnostic with `publication_applied: False`, as the publisher tools do, and contain no absolute path (raw, JSON-escaped or backslash form); during an upgrade checkpoint they are refused.
- [x] AC-4: `monitor_error` and (injected) `authority_unavailable` rows from an `OSError` with an absolute `filename`, from `RuntimeLockBusy(errno.EAGAIN, f"Runtime lock busy: {absolute path}")`, and from a non-OSError whose message carries an absolute path contain no absolute path in raw, JSON-escaped or backslash form; a repository-relative diagnostic is kept verbatim.
- [x] AC-5: the AC Priority census is recorded with each differing document explained, and the shape behind each difference is pinned by a test.
- [x] AC-6: a docs-lint test writes the same wave record and change doc as LF bytes and as CRLF bytes and runs the real per-change lint entry over a temp root, getting identical findings (passing CRLF strings to validators does not count); a failing-first result or a recorded non-reproduction is in the Progress Log.

## Tasks

- [x] Verifier: a redirect handler that checks each target before following it; tests against a local HTTP server.
- [x] Verifier: refuse malformed data rows in both tables; tests.
- [x] Memory tools: register `memory_consolidate` and `memory_purge` as `fail_fast` publication writers; update the registry pin tests; tests.
- [x] index_health: path-free rendering for `monitor_error` and `authority_unavailable`; tests.
- [x] Re-run the parser census with the AC Priority predicate; explain and pin each difference.
- [x] Reproduce the CRLF lint gap; fix if real; add the parity test.
- [x] Update CHANGELOG, the vendor README, the package prompt and build-and-verification where behaviour changes.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| verifier | implementer | none | Requirements 1 and 2 |
| path-free | implementer | none | Requirements 3 and 4 |
| census-and-lint | implementer | none | Requirements 5 and 6 |


## Serialization Points

- `.wavefoundry/framework/scripts/verify_vendored_scripts.py`, `.wavefoundry/framework/scripts/tests/test_verify_vendored_scripts.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/wf_server/context_efficiency_handlers.py`, `.wavefoundry/framework/scripts/context_efficiency.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/`, `.wavefoundry/framework/scripts/change_doc_checklist.py`, `.wavefoundry/framework/scripts/docs_lint.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/dashboard/vendor/README.md`, `docs/prompts/package-wavefoundry.prompt.md`, `docs/contributing/build-and-verification.md`

## Affected Architecture Docs

`docs/architecture/threat-model.md` only if the verifier's redirect rule needs a sentence; otherwise N/A, since the change is confined to existing modules with no boundary or flow change.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The verifier must never contact an off-registry host |
| AC-2 | required | A skipped row is a false success |
| AC-3 | required | Path-free refusals are the 1zlts contract |
| AC-4 | required | Same contract on the remaining rows |
| AC-5 | important | Closes a census gap; no live document is affected |
| AC-6 | important | Windows checkouts deliver CRLF |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-02 | Reverification follow-up N1: a last table row without its leading pipe still renders as a row, so `_table_rows` now refuses any non-blank line containing `|` that does not start the table's next row, rather than ending the table at it. Docs name the shape. | `MalformedRowTests.test_a_last_row_without_its_leading_pipe_exits_two`; mutation (check disabled) killed in a scratch copy laid out like the framework tree; `test_verify_vendored_scripts` 32 OK. |
| 2026-10-02 | Delivery-review repairs F1 to F5. F1: `_table_rows` refuses an indented row (`indented <table> table row`) and any table-shaped line (`^\s*\|`) after the table's end and before the next `## ` heading (`<table> table row after the end of the table`), so a row after a blank line is no longer dropped. F2: `memory_consolidation_failed` renders the failure and a rollback failure with `path_free_exception_text(..., prefix_class=False)`. F3: `_repo_relative_filename` tries the normalised path first and drops any result with a `..` component; a message-only `OSError` (no errno, no filename) follows the text rule. F4: the two `test_index_source_guard` tests patch the modules `_project_context_efficiency_wave` resolves through its own globals and read `reason` with `.get`, so a miss fails instead of erroring; verified in normal and reload-purge modes (`rv_reload_sim.py`). F5: CHANGELOG, vendor README, build-and-verification and the package prompt name indented rows and rows after a blank line as refused. | Tests: `MalformedRowTests` (indented row at 1 and 3 spaces, file rows after a blank line, registry rows after a blank line, all on the shipped README, exit 2 naming the row; prose-after-table case kept), `MemoryToolPublicationRefusalTests` (consolidation failure with an OSError inside and outside the root; rollback failure), `PathFreeMonitorRowTests` (climbing filename, message-only OSError dropped when it carries a path and kept when path-free). Failing-first on the pre-repair tree: 9 failures of 20; the reload-purge run of `test_index_source_guard` errors with `KeyError: 'reason'` before the fix and passes after. Mutations in a fresh scratch copy: 7 run, 6 killed; trying the raw path before the normalised one survives as an equivalent mutant, because the `..` check already drops every raw result that differs from the normalised one. Full suite in a fresh scratch copy, `run_tests.py --no-cache`: 10753 tests across 156 files, OK, 34 skipped. |
| 2026-10-02 | Implemented all six requirements. R1: `_RegistryRedirectHandler.redirect_request` refuses an off-registry target (calling the module's `_is_registry_url`) before it is followed; `_open` builds the opener; the post-follow `geturl()` check is kept; `DefaultFetchTests` moved to the `_open` seam. R2: `parse_readme` finds each table by its exact header (exactly once) and full-matches every data row up to the first line not starting with a pipe, else `ReadmeError` naming the line. R3: `memory_consolidate` and `memory_purge` registered as `fail_fast` memory writers; `memory_purge_failed` rendered by `lifecycle_lock.path_free_exception_text`. R4: `monitor_error` uses `path_free_exception_text` (class and errno name plus repository-relative filename for an OSError; other text kept only when `path_free_text` finds neither a root form nor an absolute path); `authority_unavailable` keeps its text only when path-free, else the authority status. R5 census (predicate as written; HEAD `4522b371` readers vs working-tree readers over the working tree's documents, through the real functions): 1050 documents scanned, 3 differ, all on reader (b) only: `1t2zq-enh`, `1t3el-enh` and `1t3s7-enh` in closed wave `1t3ek` each carry a second, template-leftover `## Acceptance Criteria` section; HEAD's `_check_ac_priority_alignment` read only the last section (2 bullets), the working tree reads every section as the close gate does (8, 8 and 9 bullets). Both trees fail all three documents; the working reading is correct (it matches the close gate's walk), and the shape is pinned. Readers (a), (c) and (d) agree on every document. R6: not reproduced; attempts: the real CLI over a temp root (full run), the `--changed` incremental run in a git temp repo, and in-process `check_wave_docs` (one record and all), each with the same wave record and change doc as LF and as CRLF bytes, gave identical findings (5 per-change findings each); `helpers.read_text` decodes with universal newlines. Parity is pinned for the full and incremental CLI runs. | Tests: `test_verify_vendored_scripts` (`RedirectBeforeFollowTests` with two loopback servers, the second counting hits, proxies neutralised; `MalformedRowTests`; migrated `DefaultFetchTests`), `test_lifecycle_mutation_lock.MemoryToolPublicationRefusalTests` (child process holding the transaction, other-thread lifecycle hold with a child holding publication, upgrade checkpoint, purge rendering), `test_server_context_efficiency.PathFreeMonitorRowTests` (real monitor loop), `test_change_doc_checklist.LintAndPrepareMarkTests.test_every_criteria_section_counts_toward_the_priority_table`, `test_docs_lint.LineEndingParityTests` (2). Failing-first against the unfixed tree: verifier 8 failures and 6 errors of 28; memory tools 5 failures and 3 errors of 5; index_health rows 10 failures of 4 tests; census pin fails on HEAD readers (found 2, expected 5). Mutations in a scratch copy, each reverted singly: 17 run, 17 killed (handler refusal, opener handler, row skip, repeated header, geturl check, each registration, purge rendering, monitor and authority rendering, strerror echo, filename relativising, raw filename, text kept, absolute-path regex, root-form check, HEAD AC reading). Full suite in a scratch copy, `run_tests.py --no-cache`: 10747 tests across 156 files, OK, 34 skipped. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-02 | Fix the six follow-ups inside 1zls7 | Operator direction: they weaken checks this wave adds | Defer to 1zls8 or a separate wave |
| 2026-10-02 | Register the two memory tools as publication writers rather than adding local catches | The guard renders them path-free and also refuses them during an upgrade checkpoint, matching the other memory writers | Local `except ProjectPublicationUnavailable` in each handler |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A redirect handler changes proxy or TLS behaviour | Use urllib's redirect handler hook only; keep default TLS and proxy handling; test with a local server |
| Moving to an opener breaks the existing `urlopen` mocks so tests reach the network | Migrate `DefaultFetchTests` to the new seam or the local server; the default suite stays network-free |
| Stricter row parsing refuses the current README | Run the verifier's parser over the shipped README in a test |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
