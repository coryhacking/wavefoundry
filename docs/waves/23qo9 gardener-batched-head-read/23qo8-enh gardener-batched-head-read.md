# Read the committed versions of changed documents in one Git call

Change ID: `23qo8-enh gardener-batched-head-read`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-18
Wave: 23qo9 gardener-batched-head-read

## Rationale

Since change `23qfz`, the docs gardener's default mode decides whether a Git-changed document differs from its committed version outside the `Last verified` line. `docs_gardener._differs_from_head_outside_date_line` fetches that version with one `git show HEAD:./<path>` process per document, one after another, each with a 30 second timeout.

Measured on this repository on 2026-11-18 (macOS, Git 2.54.0, 167 Git-changed Markdown documents): 167 separate `git show` calls took 2.82 seconds; one `git cat-file --batch` call fed the same 167 names took 0.044 seconds and returned the same blobs. The delivery review of `23qfz` measured about 8.7 seconds for 500 documents. The gardener runs inside Prepare, Close, the upgrade docs gate and the package build under a 180 second limit, and Windows starts processes more slowly, so a large first-day change set is where the per-document cost can fail a docs gate.

The operator asked for this follow-up on 2026-11-18, quoted: "plan the batched git read in a new wave".

## Product Intent

Anyone running Prepare, Close, an upgrade or a package build on a repository with many edited documents gets the same stamping decisions as today in a fraction of the time, with no added risk of a docs gate timing out because of the number of changed documents. Before: one Git process per candidate document. After: one Git process for all of them. Boundaries: which documents are stamped does not change, and a Git failure still never suppresses a stamp.

## Requirements

1. In the default mode, the gardener reads the `HEAD` versions of all candidate documents with one Git process for the run, in place of one process per document. A candidate is a Git-changed document that already passed the changed-since-its-stamp check, as today, so a run with no candidate starts no such process.
2. The stamping decision for every document is identical to the per-document implementation: a document is stamped when it differs from its `HEAD` version outside the `Last verified` line after line endings are normalized, and a document with no `HEAD` version counts as differing.
3. Failure never suppresses a stamp, at the same granularity or coarser: if the batched call cannot be started, times out, exits with an error, or returns output the gardener cannot parse completely, every candidate whose `HEAD` version was not obtained counts as differing. The gardener never raises because of the batched read.
4. The batched call runs through the module's existing `_run_tree_kill` resolver with a single timeout for the call, stated in the tool reference. The process-routing census in `test_tree_kill_routing.py` keeps one entry for the new call site and loses the per-document one.
5. A document whose repository-relative path cannot be passed safely on one input line (a line break in the name) is not sent in the batch and counts as differing.
6. Paths are resolved as today relative to the gardener's root (`git -C <root>` with the `HEAD:./<path>` form), which was executed on 2026-11-18 from a subdirectory of the work tree with the batch form and resolved correctly. Behaviour is the same on Windows, macOS, Linux and WSL2; the blob bytes are compared after the same CRLF normalization as today, so a `core.autocrlf` checkout is unaffected.
7. Output size is bounded by what the run already reads: the gardener holds at most the `HEAD` bytes of the candidate documents, which the per-document implementation also read one at a time. No content is written anywhere.

## Scope

**Problem statement:** The default-mode `HEAD` comparison costs one Git process per candidate document, which is slow on large change sets and can approach the docs gate's time limit.

**In scope:**

- Replacing the per-document read in `docs_gardener.py` with one batched read and a parser for its output.
- Tests in `test_docs_gardener.py`, the census entry in `test_tree_kill_routing.py`.
- One sentence in the `wf_garden_docs` tool-reference entry (the read is one Git call with one timeout) and a changelog entry.

**Out of scope:**

- Any change to which documents are stamped, to the changed-since-its-stamp check, or to the explicit `--paths` and `--all-docs` modes.
- `collect_changed_markdown_paths` skipping non-ASCII paths (Git quotes them) and finding nothing when the root is below the Git top level. Both are older than `23qfz`, were recorded as follow-ups there, and are not fixed here.
- Parallel processes, caching between runs, or a dependency on a Git library.

## Acceptance Criteria

AC-1 and AC-2 together test the intent: same decisions, one process.

- [x] AC-1: With several candidate documents in a temporary Git repository, a default-mode run starts exactly one Git process for the `HEAD` reads, observed by counting calls through the resolver; a run with no candidate starts none. The test fails on the per-document implementation.
- [x] AC-2: The existing `DefaultModeStampRuleTests` cases pass unchanged in outcome (first edit stamped, later run byte-identical, later edit stamped, date-only difference never stamped with LF and with `core.autocrlf=true`, future stamp, document with no `HEAD` version, run-date comparison), and a mixed run holding a document that differs, one that differs only in its date line and one with no `HEAD` version in the same batch stamps exactly the first and third.
- [x] AC-3: Failure counts as differing: when the batched call raises, times out, exits non-zero, or returns truncated or malformed output, every candidate without an obtained `HEAD` version is stamped and the run does not raise. Each of the four cases fails if its fallback returns "not differing".
- [x] AC-4: A candidate whose name holds a line break is not sent to Git and is stamped; names with spaces and non-ASCII characters passed explicitly to the comparison are read correctly.
- [x] AC-5: The `test_tree_kill_routing.py` census lists the one batched call site and no per-document call site, and the tool reference states that the default mode reads the committed versions with one Git call under one timeout. The documents this change authors or edits validate, and the changelog has an entry.

## Tasks

- [x] Replace `_differs_from_head_outside_date_line`'s per-document `git show` with one `git cat-file --batch` call for the run's candidates in the default branch of `resolve_metadata_targets`, parsing `<object> <type> <size>` headers and `missing` lines, and keeping `_without_date_line` as the comparison.
- [x] Tests for AC-1 to AC-4 on real files in temporary Git repositories; mutation checks in a scratch copy for each fallback and for the parser.
- [x] Move the census entry; update the tool-reference sentence and `CHANGELOG.md`.
- [x] Full framework suite last, then the second profile on the touched test files.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| batched-read-and-tests | implementer | none | Needs `framework_edit_allowed` |
| reference-text | implementer | batched-read-and-tests | Tool reference and changelog |

## Serialization Points

- `.wavefoundry/framework/scripts/docs_gardener.py`
- `.wavefoundry/framework/scripts/tests/test_docs_gardener.py`
- `.wavefoundry/framework/scripts/tests/test_tree_kill_routing.py`
- `docs/specs/mcp-tool-surface.md`

The gardener runs inside Prepare and the Close docs gate, so no other change edits it at the same time. The root changelog is also edited.

## Affected Architecture Docs

N/A: one internal read inside the gardener changes from many processes to one; no boundary, flow or verification seam changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The change: one process |
| AC-2 | required | Decisions must not change |
| AC-3 | required | A failure must never suppress a stamp |
| AC-4 | important | Unusual names must not corrupt the batch |
| AC-5 | important | Census and reference accuracy |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-18 | Created with `wf_new_enhancement` and planned only. Executed on this repository: 167 Git-changed Markdown documents, 2.82 s for one `git show` per document against 0.044 s for one `git cat-file --batch`, same blobs (3,751,563 bytes returned); a missing path returns a `<name> missing` line; the `HEAD:./<path>` form resolves relative to the directory given to `git -C` in batch mode. The per-document call and its 30 second timeout were read in `docs_gardener._differs_from_head_outside_date_line`. Not executed: Windows process cost, a batch larger than this repository's change set. | Shell measurement, 2026-11-18; code read |
| 2026-11-18 | Readiness review and implementation notes (coordinator record). No blocking finding from any seat; `code-reviewer`, `qa-reviewer` and `docs-contract-reviewer` approved readiness; `red-team` and `security-reviewer` sat as council seats. The spec body is not edited. BINDING notes for the implementer, the reviewers' and coordinator's choices, not separately confirmed by the operator: (1) Bytes in and out: build the input as bytes (`HEAD:./` plus the file-system-encoded relative path plus a line feed per name) and never pass `text=True`; the resolver's text capture decodes with replacement and, on Windows, converts line endings, either of which breaks the size framing. Pass the input through `input=` so the resolver uses `communicate`; never a write-then-read loop. (2) Before sending, exclude any name containing a line feed, a carriage return or a NUL (wider than requirement 5's line break) and count it as differing. Handle per-document errors (`relative_to`, encoding, reading the working file) for that document only. (3) Strict parser, by input order: for each name sent, accept either a header of 40 or 64 hex characters, a type and a whole-number size followed by exactly that many bytes and one line feed, or a reply that ends in ` missing` for the exact name sent. A `missing` reply, a non-`blob` type (a tree, read through its size), the two-token `submodule` reply and an `ambiguous` reply mean no usable `HEAD` version for that one candidate only, which counts as differing. Any other violation (bad header, size beyond the data, too few or too many entries, trailing bytes) counts every candidate from that point on as differing. On a non-zero exit keep only entries that were fully framed before the failure, or discard all; test the exit after partial output. No exception escapes. (4) Never put Git's output into a diagnostic or log line. (5) Existing code to reuse or mirror: `index_state_store._batch_git_blobs` already parses `git cat-file --batch` output (the plan's statement that no existing mechanism exists is wrong on this point); check how it treats a stray `GIT_DIR` in the environment before reusing it. (6) Timeout: one value for the call that fits the callers' 180 second gardener limit beside the existing 120 second `git diff`; state the value in the tool reference, together with: a failed batch stamps every candidate whose committed version was not obtained. Extend the tool reference's existing "a Git failure or a timeout counts as differing" wording to output that cannot be parsed completely. Keep the dated execution evidence of requirement 6 out of shipped text. (7) Tests: `test_head_read_failure_or_timeout_counts_as_differing` filters on `"show" in cmd` and would pass vacuously after the change; rewrite it to filter on `cat-file`, assert the injection fired, and use a document that differs from `HEAD` only in its date line so only the fallback can stamp it; cover a raised `TimeoutExpired` and `FileNotFoundError`, exit 128, output cut mid-blob, a corrupted header (non-integer size, size larger than the data) and an injected extra entry. `test_document_with_no_head_version_is_stamped` is the other test tied to the current call shape. AC-1 counts only `cat-file` calls through the resolver (the `git diff` in `collect_changed_markdown_paths` uses the same resolver), with at least two candidates, and zero when there is no candidate. The AC-2 mixed batch gives each committed document a distinct body, sorts the document with no `HEAD` version into the middle, and includes a document with non-ASCII content and one with CRLF content; a swapped-blob mutation and an off-by-one mutation must each fail a test. AC-4 calls the helper with a path holding a line feed that need not exist on disk, asserts from the captured input bytes that it was not sent, and follows it with a date-only document that stays unstamped. (8) Census and prose: the `test_tree_kill_routing.py` key is the new function's name; remove the comment about the per-document read. Rewrite the docstring of the replaced function. The changelog entry goes under `Changed` in the top `[1.44.0]` section beside the gardener entry (there is no `Unreleased` section). (9) The Decision Log's reason for rejecting `git diff -I` is partly wrong: a hunk mixing the date line with another change is correctly not ignored; the real objections are that `-I` ignores every matching line while the gardener masks only the first, that it uses Git's own pattern dialect, and that it needs Git 2.30 or later. | Approvals `ev-approval-code-reviewer`, `ev-approval-qa-reviewer`, `ev-approval-docs-contract-reviewer`; reviewers' scratch executions on Git 2.54.0 (5,000 names in about 3.4 s through both resolvers, no pipe deadlock) |
| 2026-11-18 | Implementation (implementer record; the coordinator ticks criteria). Built: `docs_gardener._read_head_versions(root, paths)` sends every candidate as `HEAD:./` plus its file-system-encoded path and a line feed, as bytes, through `_run_tree_kill(..., input=..., capture_output=True, timeout=HEAD_READ_TIMEOUT_SECONDS)` with no `text=True`; one call per run, none when no candidate. Strict parser by input order per binding note 3: a 40 or 64 hex header with type and size, exactly that many bytes and one line feed; `<name> missing`, `<name> ambiguous`, the two-token `submodule` reply and a non-blob object leave only that document unread; any other framing violation leaves that document and every later one unread; trailing bytes, a non-zero exit (whatever was framed before it), a start failure or a timeout leave every document unread. Names with a line feed, carriage return or NUL, and names that fail `relative_to` or encoding, are not sent. `_differs_from_head_outside_date_line(path, head)` now compares given bytes (docstring rewritten); `None` or an unreadable working file counts as differing. Nothing from Git's output reaches a diagnostic. Timeout chosen: 45 seconds (with the 120 second `git diff`, inside the 180 second gardener limit). Choices beyond the spec: binding note 5, `index_state_store._batch_git_blobs` was read and mirrored, not imported: it decodes blobs as text with replacement, does not check the echoed name on `missing`, tolerates trailing bytes, and runs through `_run_git`, which strips `GIT_DIR` and the other repository-local variables; the gardener keeps its own unsanitized environment so the batch reads the same repository as its existing `git diff` and the replaced `git show` (as today). The call catches any exception, not only process errors, so a programming error in the call cannot raise out of the gardener. Oracles moved: the `test_tree_kill_routing.py` census key `_differs_from_head_outside_date_line` became `_read_head_versions` (count 1) and its per-document comment was removed; `test_head_read_failure_or_timeout_counts_as_differing` was replaced by `test_head_read_failure_counts_every_unread_candidate_as_differing` (filters on `cat-file`, asserts the injection fired, date-only documents, seven cases plus an intact-batch control) because the old filter on `show` would pass vacuously. New tests: `test_one_batched_head_read_for_all_candidates`, `test_no_candidate_starts_no_batched_head_read` (AC-1), `test_mixed_batch_stamps_exactly_the_differing_documents` (AC-2), `test_names_that_cannot_be_sent_are_not_sent_and_count_as_differing` and `test_names_with_spaces_and_non_ascii_characters_are_read` (AC-4). Mutation evidence (scratch copy, `DefaultModeStampRuleTests`, unmutated OK): per-document calls, swapped blob, off-by-one, each fallback returning the working bytes (raise, non-zero exit, truncated, bad header, trailing bytes), a line feed name sent, and `text=True` each fail at least one of the new tests. Read-only timing on this repository's 73 changed documents: 1.05 to 1.09 s per document against 0.035 s batched, same decisions. Gapfill: one `grep -rn` over the scripts tree for literals tied to the old helper and tool-reference wording, because a whole-tree multi-literal sweep including test files was quicker than per-literal `code_keyword` calls; all other lookups used `code_*` tools. Not verified: native Windows, WSL2, Python 3.11. | Focused runs and mutation output in `.wavefoundry/work/23qo9/` (disposable) |
| 2026-11-18 | Delivery repair pass (implementer, `DELIV-QO8-TRUNCATED-AT-BOUNDARY`, repair cycle 3; test-only, no product change). Added three cases to `test_docs_gardener.DefaultModeStampRuleTests.test_head_read_failure_counts_every_unread_candidate_as_differing`: `cut_after_first_entry` (exit 0, output ends after the first complete reply, the second document is stamped), `empty_output` (exit 0, both stamped) and `missing_reply_names_another_document` (the first reply is a `missing` line naming the second document, the second reply intact; both stamped, closing binding note 3). No byte-exact oracle moved. Gapfill: located the code with shell grep and targeted reads rather than the `code_*` tools, because the function and test were already named in the finding. | Scratch copy, `python3 -B`, macOS: making the no-further-header branch return every sent document's working bytes failed `cut_after_first_entry` and `empty_output` (failures=2); accepting any header ending in ` missing` failed `missing_reply_names_another_document` (failures=1); restored code passed. Focused run: "Ran 214 tests across 4 files in 19.170s", "OK". |

| 2026-11-18 | Delivery repair for DELIV-QO8-SIZE-CONVERSION. A second Git object header with a 5,000-digit decimal size raised ValueError before the repair. The reader now checks the size field’s width against the byte length of the whole response before conversion. The default gardener test confirms an unread second candidate is stamped while the successfully compared first candidate retains its date. | Local macOS run of test_docs_gardener.py passed all 44 tests in 4.328 seconds. The malformed response was injected into the output of an actual temporary Git repository. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-18 | Do this follow-up. Operator's instruction, quoted: "plan the batched git read in a new wave". | The operator asked for it. | Leave the per-document read: acceptable for normal change sets, slow for large ones. |
| 2026-11-18 | One `git cat-file --batch` call for the run's candidates. Planner's choice, not separately confirmed by the operator. | Measured about 60 times faster on this tree, one process whatever the count, plain Git with no new dependency, and a missing path is reported in-band. | `git diff -I` with a date-line pattern for the whole change set: one process too, but its ignore rule applies per hunk, so a hunk mixing the date line with another change needs separate handling, and line-ending conversion follows Git's settings instead of the gardener's normalization. Running the per-document calls in parallel: still one process per document and more moving parts. |
| 2026-11-18 | Coarser failure handling is accepted: if the batch fails, every candidate without an obtained version counts as differing. Planner's choice. | It keeps the rule that a failure never suppresses a stamp; the cost is extra stamps on a failed run, which is the behaviour before `23qfz`. | Falling back to per-document calls on a batch failure: keeps finer granularity but doubles the code paths to test. |

Mechanism efficacy (planner's assessment). Replay: on this repository's 167 changed documents the read drops from 2.82 s to 0.044 s; at the reviewer's 500-document case the per-document 8.7 s becomes one process. Control: the change decides how the bytes are fetched, not what is stamped, so it cannot make a decision wrong except through a parsing error, which AC-2 and AC-3 pin. Wrong results: a parser that misreads a header would compare the wrong bytes; the mixed-batch case in AC-2 and the malformed-output case in AC-3 are the guards. Existing mechanisms: none; Git offers the batch form and the gardener does not use it. Measure after release: gardener time in a Prepare on a large change set.

## Risks

| Risk | Mitigation |
| --- | --- |
| The output parser mismatches blobs and names. | Results are matched by input order and each header's size is honoured exactly; a count or size mismatch discards the rest of the batch as failed, which stamps. |
| A very large change set returns many megabytes at once. | The same bytes were already read, one document at a time; the candidates are only documents modified after their stamp. |
| One timeout for the whole batch stamps everything on a slow host. | Stamping on failure is the pre-`23qfz` behaviour and is stated; the timeout is stated in the tool reference. |
| Windows behaviour differs. | The batch form and `-C` are standard Git on every platform; the comparison keeps its CRLF normalization; native Windows remains unexecuted and is stated as such at delivery. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
