# Docs Lint Reports Control Characters in Markdown

Change ID: `23zl2-enh docs-lint-control-characters`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-21
Wave: 23z46

## Rationale

Docs lint accepts a markdown document that contains a C0 or C1 control character, so the character stays in the document until something downstream breaks. Field feedback against v1.46.0 (item 11, first bullet, in `.wavefoundry/work/23z45/field-feedback-v1.46.0.md`) asks docs lint to report an error on any C0 or C1 control character other than TAB, LF and CR.

The consequences are concrete in this repository:

- Executed 2026-11-20: a markdown file with one NUL byte is treated as binary by Git. `git diff --stat` reports `Bin 10 -> 11 bytes` and `git diff` prints `Binary files a/a.md and b/a.md differ`, so a reviewer reading the diff cannot see the edit.
- Verified by reading, not executed: `scan_file_raw` in `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py` (line 1652) skips content scanning for any file with a NUL byte in its first 8192 bytes (`BINARY_SNIFF_BYTES`) and records the skip as `binary file`. A stray NUL near the top of a document therefore removes that document from secret scanning.
- The closed record `docs/waves/1v79z reconciliation-self-healing-and-dispositions/1v7a1-bug reconciliation-findings-have-no-historical-record-disposition.md` line 141 describes the same slip in code: a literal NUL written as a separator made `reconcile_scan.py` unparseable. That Progress Log row itself still contains a literal NUL at column 56.

No docs-lint check catches this today. A keyword census of `.wavefoundry/framework/scripts/wave_lint_lib/` for `unicodedata`, `\x00`, `\x7f`, `control char` and `BOM` (run 2026-11-20 with `limit=0`) found no control-character check on document content. The only related behavior is the leading-BOM tolerance from change `20b32`: `read_doc_text` and `read_record_text` in `wave_lint_lib/helpers.py` strip one leading U+FEFF.

## Product Intent

Maintainers of any repository that runs docs lint benefit. Today a markdown document with a stray control character passes lint and later hides its diff, drops out of secret scanning or breaks a consumer. After this change, full and incremental docs lint name each such character by file, line, column and code point, so the author can delete it at the next validation. The check exempts closed history, so a repository never has to edit a closed record to pass lint. It leaves TAB, LF, CR (including CRLF checkouts on Windows), a leading BOM and all printable Unicode alone. AC-1 and AC-4 together test the intent: corruption in a live document is reported and blocks validation, while the same character in history is not.

## Requirements

1. Docs lint must report one finding for each occurrence of a flagged character in a scanned document. The flagged set is every code point from U+0000 to U+001F except U+0009 (TAB), U+000A (LF) and U+000D (CR), plus U+007F (DEL) and every code point from U+0080 to U+009F (C1). The check reads the decoded text that `read_doc_text` returns: UTF-8 decoded with `errors="replace"`, one leading U+FEFF removed, and CRLF and lone CR converted to LF.
2. The finding must have the form `<path>:<line>:<column>: control character U+XXXX (<name>) in markdown; delete it or write it as visible text such as U+XXXX`. `<path>` is POSIX repository-relative (`relative_to_root`). `<line>` is 1-based and counts LF characters only, never `str.splitlines()`, because `splitlines()` also splits on U+000B, U+000C, U+001C to U+001E and U+0085, which are flagged characters (executed 2026-11-20: `'a\x1cb\x85c\x0bd'.splitlines()` returns four lines). `<column>` is the 1-based code-point offset within that line; a TAB counts as one column. `<name>` is the standard abbreviation (for example `NUL`, `BEL`, `ESC`, `DEL`, `NEL`), or `C1` for a C1 code point without a common abbreviation.
3. The finding text must never contain a flagged character itself, so an ESC in a document cannot emit a terminal escape sequence through lint output. This applies to the displayed path as well as the body: in this sensor's findings, every non-ASCII character and every character of Unicode category `Cc`, `Cf`, `Cs`, `Zl` or `Zp` in the path displays as its `\uXXXX` escape (`\UXXXXXXXX` above U+FFFF), the category set and escape form that `_display_name` in `render_agent_surfaces.py` already uses. The whole finding is therefore ASCII. A POSIX filename can contain ESC, and a non-ASCII filename can fail to encode on a strict legacy console stream. Escaping trades readability of non-ASCII filenames for an output guarantee that does not depend on the stream's encoding.
4. A document with more than 10 flagged characters must report the first 10 in document order and then one finding `<path>: <N> control characters in total; first 10 shown`, where N is the total count in that document.
5. The check must scan the same documents as the `heading_without_blank_line_before` sensor: in full lint, `iter_markdown_docs(root)` plus the repository-root `*.md` files; in incremental lint (`--changed`), the changed documents under the markdown scan roots plus the changed root entry files. It must skip oversized documents that the size guard already skipped.
6. The check must not report history. It must reuse the predicate `_heading_check_history` in `wave_lint_lib/wave_validators.py`, which treats as history any document under the record archive root, under the memory archive, or in a record folder whose record `Status` is closed or completed.
7. The check must be registered in `SENSOR_POLARITY_REGISTRY` in `wave_lint_lib/constants.py` as `markdown_control_character` with `"polarity": "blocking"` and `"introduced_wave": "23z46"`, and must route its findings through `_route_sensor_findings`. A blocking finding is an `ERROR:` line that fails docs lint. The Decision Log records why this sensor ships blocking rather than advisory.
8. The check must not change gardener, indexing, search or secrets behavior, and it must not repair documents.
9. The check must cost at most one compiled regular-expression search per scanned document when the document holds no flagged character. It must use the cached text from `read_doc_text` and add no extra file read.
10. Behavior is the same on Windows, macOS, Linux and WSL2. `read_doc_text` normalizes CRLF and lone CR before the check runs, so a checkout written with `core.autocrlf=true` (Windows, or WSL2 on a `/mnt/c` checkout) reports the same lines and columns as an LF checkout. Paths in findings use `/` on every platform. The whole finding is ASCII (Requirement 3), so a cp1252 Windows console prints it without an encoding error even when `configure_utf8_stdio` could not reconfigure the stream. Windows filenames cannot contain C0 characters, so the ESC-in-filename case arises on macOS, Linux and WSL2 only.
11. The behavior documentation must name the check, the flagged and allowed sets, the history exemption and the remedy. That documentation is the Path 2 Docs Lint Gate steps in `docs/architecture/data-and-control-flow.md`, the docs-lint section of `docs/contributing/build-and-verification.md`, and an Unreleased bullet in the root `CHANGELOG.md`. The bullet must tell upgrading repositories that a pre-existing control character in a live document now fails docs lint and how to find and remove it. It must also say when the rule takes effect on an upgrade: it blocks at the docs gate of the upgrade that installs it, because that gate runs the extracted linter, and sibling `23zia`'s pre-flight refuses the same finding before extraction on that upgrade when it can load this change's scan (`23zia` Requirement 12 carries the sentence into seed 160).
12. The scan must be exposed as a public callable in `wave_lint_lib/wave_validators.py`, `scan_markdown_control_characters(root)`, that takes a repository root and returns one record per flagged occurrence with the fields `path` (POSIX repository-relative, unescaped), `line`, `column` and `code_point` (an integer), in document order. It covers the full-lint document set from Requirement 5, skips oversized documents by the same size cap, and applies the same closed-history predicate from Requirement 6. It must be usable outside the docs-lint CLI and have no side effects: no file writes, no stdout or stderr output, and no change to docs-lint's refusal-report state; an unreadable document is skipped. Docs lint formats its findings (Requirements 2 to 4) from these records, so both report the same occurrences. Sibling change `23zia-enh upgrade-lint-preflight-and-diff-log` calls it from the incoming framework during the upgrade pre-flight, so the name and record fields are a contract between the two changes.

## Scope

**Problem statement:** Docs lint passes markdown that contains C0 or C1 control characters or DEL. Those characters make Git show the document as binary, can remove it from secret scanning, and break downstream consumers.

**In scope:**

- A new docs-lint check over scanned markdown in full and incremental modes, with the flagged set, message format, per-document cap and history exemption above.
- Registry entry with blocking polarity and its tests, including updating the existing test that asserts every registered sensor is advisory.
- Unit tests in `.wavefoundry/framework/scripts/tests/test_docs_lint.py`.
- The architecture, contributing and changelog updates named in Requirement 11.

**Out of scope:**

- U+FEFF anywhere but the first position, and other format characters (category `Cf`, such as zero-width joiners and bidirectional controls). These have legitimate uses in text, for example U+200D in emoji sequences and bidirectional marks in right-to-left text. The census found one mid-file U+FEFF, in the closed record `docs/waves/20b39 windows-crlf-correctness/20b32-bug docs-lint-leading-bom-owner-metadata.md` line 18, where it illustrates the BOM case.
- Invalid UTF-8. The reader decodes it as U+FFFD, so a lone byte 0x80 to 0x9F is not a C1 character here. A cp1252 or invalid UTF-8 document is a separate concern.
- Non-markdown files, files outside the scan roots, and closed history.
- Automatic repair, and exemption through `docs/lint-rules.toml`. The heading sensor does not honor that file, and the documented contract is that exclusions suppress generic metadata and outgoing-link findings only (`docs/contributing/build-and-verification.md`). Seeds 011, 012 and 040 restate that contract, so honoring it would require seed edits.
- Removing the NUL from the closed record `1v7a1`. Closed records are history and the exemption covers it.

## Acceptance Criteria

- [x] AC-1: A live document fixture under `docs/` containing one each of U+0000, U+0007, U+000B, U+000C, U+001B, U+001C, U+007F, U+0080, U+0085 and U+009F makes the full docs-lint run fail with one `ERROR:` finding per character. Each finding gives the expected line, column and code point in the Requirement 2 form. A line-number oracle places U+000B and U+0085 earlier on a line than a later flagged character and on earlier lines, and the reported line equals the count of LF characters before each occurrence plus one. Removing the characters makes those findings disappear. Without the fix, the fixture passes lint with no such finding.
- [x] AC-2: A fixture containing TAB, LF, a CRLF line, a lone CR, a leading U+FEFF, U+00A0, U+00E9 and an emoji produces no control-character finding. A CRLF-encoded copy of the AC-1 fixture reports the same lines, columns and code points as the LF copy.
- [x] AC-3: In incremental mode (`--changed`) in a Git fixture, a changed live document and a changed root entry file (`AGENTS.md`) that each contain U+001B produce the same `ERROR:` finding as full lint, and an unchanged document containing one produces none.
- [x] AC-4: The same U+0000 placed in a document under a closed wave record folder, under the record archive root and under the memory archive produces no finding. Placed in a document of a planned or active wave, it produces a finding.
- [x] AC-5: For a fixture containing U+001B and U+0007, no finding string contains any character in the flagged set. A document with 50 flagged characters yields exactly 10 per-character findings followed by one summary finding that states the total 50.
- [x] AC-6: `SENSOR_POLARITY_REGISTRY["markdown_control_character"]` is `{"polarity": "blocking", "introduced_wave": "23z46"}`. Patching that entry to advisory (with a `decided_wave`) turns the AC-1 findings into `WARNING:` lines, and docs lint then passes. This proves the findings route through the registry, so a later decision changes one value.
- [x] AC-7: `docs/architecture/data-and-control-flow.md` Path 2, the docs-lint section of `docs/contributing/build-and-verification.md` and the root `CHANGELOG.md` Unreleased section each name the check, the flagged and allowed sets and the history exemption. The changelog bullet also gives the upgrade remedy and the installing-upgrade sentence from Requirement 11.
- [x] AC-8: A document whose POSIX filename contains U+001B and a flagged character in its body yields a finding in which the path shows `\u001b` and no raw U+001B appears (skipped on Windows, where such a filename cannot exist). A document whose filename contains U+6587 and a flagged character in its body, linted with output written to a strict cp1252 text stream (`errors="strict"`), completes without `UnicodeEncodeError` and the path shows `\u6587`. With the fix absent, the first finding carries the raw ESC and the second write raises `UnicodeEncodeError`.
- [x] AC-9: On a scratch repository root containing a live document with U+0000 and U+001B and a closed wave record with U+0000, a direct call to `scan_markdown_control_characters(root)` from a test, without the docs-lint CLI, returns exactly the records for the live document's two occurrences (path, line, column, code point), matching the findings full docs lint reports on the same root. The call writes no file and prints nothing. With the fix absent the callable does not exist and the import fails.

## Tasks

- [x] Add `markdown_control_character_findings(root, paths, *, skip)` beside `heading_blank_line_findings` in `wave_lint_lib/wave_validators.py`, reusing `read_doc_text`, `relative_to_root` and `_heading_check_history`, with one module-level compiled pattern.
- [x] Register `markdown_control_character` as blocking in `wave_lint_lib/constants.py`, with a comment pointing at this change's Decision Log.
- [x] Route the findings with `_route_sensor_findings` in both `_run_incremental_checks` and `_run_full_checks` in `wave_lint_lib/cli.py`, over the same path sets as the heading sensor.
- [x] Add tests for AC-1 to AC-6 to `tests/test_docs_lint.py`, and update `test_both_advisory_sensors_carry_the_recorded_decision` so it asserts the advisory entries and the one blocking entry explicitly.
- [x] Expose `scan_markdown_control_characters(root)` per Requirement 12, make the docs-lint findings format from its records, and add the AC-9 test.
- [x] Escape the displayed path in this sensor's findings per Requirement 3, reusing `_display_name`'s category set, and add the AC-8 tests (the ESC filename case POSIX-only, the cp1252 stream case on every platform).
- [x] Update the three documents named in AC-7.
- [x] Run full docs lint on this repository and record the result in the Progress Log. The 2026-11-20 census predicts zero live findings (see Decision Log).
- [x] Time full docs lint before and after on this repository and record both figures in the Progress Log.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| lint-check | implementer | none | Validator, registry entry, cli routing, tests |
| docs | implementer | lint-check | Architecture, contributing and changelog text from the delivered behavior |
| 23zia pre-flight | implementer (23zia) | lint-check | Sibling change `23zia-enh upgrade-lint-preflight-and-diff-log` depends on the Requirement 12 callable and its record fields. |

## Serialization Points

- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/cli.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `docs/architecture/data-and-control-flow.md`
- `docs/contributing/build-and-verification.md`

The root `CHANGELOG.md` is a documentation edit made by the same writer.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md`: Path 2 (Docs Lint Gate) step 3 gains one sentence naming the control-character check and its history exemption. No boundary, ownership or flow changes.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The requested behavior; with AC-4 it tests the intent. |
| AC-2 | required | Without it the check could flag CRLF checkouts and break every Windows repository. |
| AC-3 | important | The post-edit hook uses incremental lint; the full gate still catches what it misses. |
| AC-4 | required | Without the exemption this repository fails its own lint on the closed record `1v7a1`. |
| AC-5 | important | Prevents terminal escape injection and output floods from a corrupted file. |
| AC-6 | required | The blocking polarity is the recorded decision; routing through the registry keeps it reversible. |
| AC-7 | important | Upgrading repositories need the remedy before the gate refuses them. |
| AC-8 | important | The path is the one part of the finding the document body does not control; without it Requirement 3's guarantee fails on filenames. |
| AC-9 | required | Sibling `23zia`'s upgrade pre-flight depends on this callable. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-20 | Planned from field feedback v1.46.0 item 11 (first bullet). | Census and Git probe in the Decision Log. |
| 2026-11-20 | Operator decision recorded: the check ships blocking, and the upgrade pre-flight interaction belongs to `23zia`. | Decision Log row dated 2026-11-20 marked "operator decision"; Risks row on the upgrade docs gate. |
| 2026-11-20 | Plan review finding (advisory, relayed by the coordinator): the displayed path could carry ESC or characters a legacy console cannot encode. Requirement 3 now escapes the path to ASCII, Requirement 10 states the platform split, AC-8 and a task cover an ESC POSIX filename and a U+6587 filename written to a strict cp1252 stream. AC-6 is unchanged pending the operator decision on a `23zia` registry field. | Requirements 3 and 10, AC-8, Tasks, AC Priority, Risks. |
| 2026-11-20 | Coupling update (operator decision relayed by the coordinator): `23zia`'s upgrade pre-flight calls this change's scan directly from the incoming framework, with no registry field, so AC-6 stays two-field. Added Requirement 12 (public side-effect-free `scan_markdown_control_characters(root)`), AC-9, a task, an Agent Execution Graph row for the `23zia` dependency, and replaced the Risk text on the pre-flight. | Requirement 12, AC-9, Tasks, Agent Execution Graph, Risks. |
| 2026-11-20 | 2026-11-20 readiness repair pass 1. No finding was recorded against this change. Folded in the release reviewer's disclosure note from the review of findings `R1-23zl1-rerender-never-runs` and `R1-23zia-no-override-premise`: Requirement 11 and AC-7 now require the changelog bullet to say that the rule blocks at the docs gate of the installing upgrade. Sibling `23zia` reads this change's scan and does not edit `wave_validators.py`; the wave record's Watchpoints are corrected to say so (`R1-23z46-wave-dependency-record`). | Read of `phase_docs_gate`, which runs the extracted linter in a child; `.wavefoundry/work/23z46/review/release-reviewer.md` note F3. |
| 2026-11-21 | Readback: report each hidden C0, DEL or C1 character in live Markdown with its file, line and code-point column. An ESC that used to pass lint will block both full and changed validation. AC-1 through AC-9 cover the upgrade scan, safe console output, bounds and history. The lint validator, shared readers, routing, registry, tests and three behavior documents change. This check never edits a document. | Full and incremental fixtures, direct preflight contract, before/after repository lint. |
| 2026-11-21 | Implemented the shared scan, full and changed lint routing, the blocking registry entry and the documented upgrade remedy. The preflight gets uncapped raw coordinates. Lint prints ten ASCII-safe examples per file and the total. The direct scan preserves the lint caller’s refusal evidence and rejects an invalid record layout. | The new regression tests initially failed with no scan callable or no lint findings. All 13 focused tests and all 366 docs-lint tests passed. Omitting ESC failed the display/count test. Including closed records or publishing refusals each failed the direct scan test. The tests use a real Git changed set, nested relocated roots, a strict cp1252 text stream and LF, CRLF and CR files. Executed on macOS. |
| 2026-11-21 | Timed full read-only lint on this checkout before and after the change. Before: 12.40 s with two sibling review projections stale. After: 14.61 s with exit 0 and zero live control-character findings. Full MCP validation passed. | Single runs during parallel development. Changes in CPU load and fixture state prevent attributing the timing difference to this sensor. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-20 | Selected approach: a registered docs-lint sensor over the decoded text of live scanned markdown, mirroring the `heading_without_blank_line_before` sensor's path sets and history predicate, with one compiled pattern search per document. | It reuses the existing read cache, scan sets, history exemption and polarity routing, so it adds one function and one registry entry rather than a new pipeline. | (a) A byte-level scan before decoding: it would see CR and the BOM and need its own allow logic, and it would add a second read path. (b) Extending the secrets scanner, which already sniffs for NUL: secrets is record-only in docs lint and enforced at close only, so the finding would not reach the author at validation. |
| 2026-11-20 | The sensor ships **blocking**, against the default that new docs-lint sensors ship advisory (`SENSOR_POLARITY_REGISTRY` comment in `constants.py`; plan-spec prompt). This record is the recorded decision that policy asks for. | The default exists because a new sensor's false-positive rate is unknown until it meets field data. This sensor has no false-positive class in markdown: no flagged character renders, and the allowed set (TAB, LF, CR, leading BOM) covers every legitimate whitespace use. The reporter asked for an error, and the census below is the field data: zero live occurrences in this repository. An advisory `WARNING:` would leave the Git-binary and secrets-skip consequences in place for anyone who does not read warnings, and no automatic repair exists to fall back on. The repair is mechanical: the finding gives line, column and code point. | Advisory with a later flip: costs a second recorded change to reach the requested behavior, and leaves corruption passing every gate meanwhile. Advisory permanently: does not meet the request and leaves the consequences. |
| 2026-11-20 | Operator decision: the operator accepted the coordinator's recommendation in the main session that the check ships blocking, overriding the advisory-first default. Pre-flight work for the upgrade docs gate stays out of this change and belongs to `23zia-enh upgrade-lint-preflight-and-diff-log`. | These characters are corruption, not style. | Advisory first with a later flip (rejected above). Adding pre-flight work to this change: the 23zia planner already has the interaction. |
| 2026-11-20 | Census of the files docs lint scans (decoded as UTF-8, counted per code point, run 2026-11-20). `docs/**/*.md`: 2569 files, one flagged character, U+0000 in the closed record `1v7a1` line 141 column 56; no CRLF, no lone CR, no leading BOM, one mid-file U+FEFF in the closed record `20b32`. Root `*.md`: 11 files, none. `.wavefoundry/framework/**/*.md` (shipped seeds and docs that render into targets): 128 files, none. | With the history exemption the check reports nothing in this repository and in the shipped surfaces. Without the exemption this repository would fail its own lint on `1v7a1`, which is why Requirement 6 is required. Target repositories were not surveyed (unverified): a target with a stray character in a live document will fail docs lint after upgrading. | Grandfathering existing occurrences with a baseline file: a new mechanism for a defect whose fix is deleting one character. |
| 2026-11-20 | Mechanism efficacy. Replay: the `1v7a1` Progress Log NUL, had it been written in a live document, produces `...:141:56: control character U+0000 (NUL)...` at the next full lint and blocks Prepare and Close. Control: blocking at `wf_validate_docs`, Prepare, Close, packaging and the upgrade docs gate; the post-edit hook reports it but does not block the edit. Wrong flags: none expected inside markdown; a document that needs to show a control character writes it as text (`\x1b`, `U+001B`). Misses: format characters, invalid UTF-8 and non-markdown files (Scope). Existing data: the secrets scanner already sniffs NUL but records a skip rather than a finding, and covers no other flagged character. Measurement: zero findings in this repository at delivery, and later field reports of a control-character failure at an upgrade docs gate. | The check catches the motivating case where the author can act on it. | None further. |
| 2026-11-20 | Flagged set: C0 except TAB, LF and CR; DEL (U+007F); C1 (U+0080 to U+009F). The leading BOM stays allowed. | DEL is a control character in ISO 6429 and is already in the repository's control set in `vendored_integrity.py`. C1 code points in decoded text usually come from UTF-8 that was decoded as Latin-1 and then re-encoded (inferred, not observed here), which is corruption. The leading BOM is tolerated by the `20b32` contract, and the reader strips it before the check runs. | Adding mid-file U+FEFF and other `Cf` characters: legitimate uses exist (Scope). |
| 2026-11-20 | Pattern search on 2569 decoded `docs/` documents (32670 KiB): 86 ms on this machine, run 2026-11-20, text already in memory. | The cost is small compared with full lint, and most of that corpus is closed history that the exemption skips before searching. The implementation records before and after timings (Tasks). | Byte-level `bytes.translate` scan: no measured need. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A target repository with a pre-existing control character in a live document fails the upgrade docs gate. That gate runs after the framework tree is replaced, so the upgrade stops part-way. | The finding gives line, column and code point; the changelog bullet names the remedy. Sibling change `23zia-enh upgrade-lint-preflight-and-diff-log` calls this change's `scan_markdown_control_characters` (Requirement 12) from the incoming framework during its pre-flight, before the tree is replaced, so the occurrence is reported while the repository is unchanged. This change adds no pre-flight work; if the callable's name or record fields change, `23zia` breaks, which AC-9 guards. |
| An implementer counts lines with `splitlines()` and misreports lines after U+000B, U+000C, U+001C to U+001E or U+0085. | Requirement 2 forbids it and the AC-1 line-number oracle fails on it. |
| An ESC in a document, or in its filename, reaches lint output and emits a terminal sequence; a non-ASCII filename fails to encode on a strict console stream. | Requirement 3, AC-5 and AC-8. |
| The new blocking entry breaks the test that asserts every registered sensor is advisory. | A planned task updates that test to name the blocking entry explicitly. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
