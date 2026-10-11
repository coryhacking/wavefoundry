# Docs-Lint Misreads Owner Metadata After a Leading BOM

Change ID: `20b32-bug docs-lint-leading-bom-owner-metadata`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-10
Wave: 20b39 windows-crlf-correctness

## Rationale

Brief: in a field session an editor saved a plan document with a UTF-8 BOM and docs-lint then reported "missing or invalid `Owner` metadata", which also failed `wf_prepare_wave`. The goal is that a leading BOM never changes docs-lint results. Consumers are operators on editors that add a BOM (common on Windows); constraint is no change for BOM-free files; success is observable through a docs-lint test with a BOM-prefixed document.

Verified at HEAD (including one read-only probe of the real patterns):

- The metadata check is `wave_lint_lib/metadata_validators.py:10-21` `check_metadata`, using `METADATA_PATTERNS` in `wave_lint_lib/constants.py:8-12` (for example `^Owner:\s+.+$` with `re.MULTILINE`).
- Text arrives through `read_doc_text` and `helpers.py:67-79` `read_text`, which decodes `utf-8` with `errors="replace"`; records under the waves and plans roots go through `read_record_text` (`helpers.py:175-210`), which also decodes plain `utf-8`. Neither strips a BOM and neither uses `utf-8-sig`.
- Probe: a document starting `﻿# T` with `Owner:` on a later line matches Owner, Status and Last verified. A document starting `﻿Owner: a` fails only Owner. So the error appears only when `Owner:` is the very first line of the file; the standard template (heading, blank line, Owner) is unaffected.
- Inconsistency: `gardener_metadata.py:283` strips the BOM (`text.lstrip`), and `render_agent_surfaces.py:4427` and `techdocs_audit_lib.py:1372` read as `utf-8-sig`. Docs-lint is the outlier.
- Bypass readers (decode without going through `read_text` or `read_record_text`, so a strip there does not reach them): `wave_validators.py` (`_read_member_doc_bytes(...).decode("utf-8")` feeding `change_doc_header_status`, anchored `^Status`, near `:1308`), `lifecycle_gate_support.py` (`_read_member_doc_text`, near `:513`), `core_validators.py` (carrier `read_text(encoding="utf-8")` calls near `:400` and `:423`), and `docs_constants_validators.py`. Dispositions are decided by the implementer from the code (see Requirement 6); they are not claimed fixed here.
- The field symptom included `wf_prepare_wave` failing on Owner. Prepare runs the full docs-lint step (the prepare dry run reports `lint_passed`), so the lint fix at the shared helpers is the expected cure for it; that Prepare reached the Owner finding through docs-lint rather than through the lifecycle gate readers is inferred, not traced. The gate readers `lifecycle_gate_support.py` `_read_wave_record_text` (near `:721`, `read_text(encoding="utf-8")`) and `_read_member_doc_text` (near `:513`) decode plain `utf-8` and are not reached by a strip in `wave_lint_lib/helpers.py`; Requirement 7 and AC-6 settle them.
- Test coverage gap: no docs-lint test covers a BOM (`grep` of `tests/test_docs_lint.py` and `wave_lint_lib/` found no `ufeff` or `utf-8-sig`).
- Not verified: which other `wave_lint_lib` checks assume the first line of the file (for example a title check) and could also be affected by a BOM.

## Requirements

1. Docs-lint must produce identical findings for a document with and without a leading UTF-8 BOM for every check that consumes text from `read_doc_text`, `read_text` or `read_record_text` in `wave_lint_lib/helpers.py`. Checks that decode bytes themselves are governed by Requirement 6, not by this requirement.
2. The chosen approach is an explicit strip of a single leading U+FEFF after the existing `utf-8` decode (keeping `errors="replace"`), applied in `read_text` and `read_record_text`. `utf-8-sig` is not used. Because `read_text` caches by `(mtime_ns, size)`, the strip happens before the text is stored in `_READ_TEXT_CACHE`, so a cached value never carries the BOM.
3. Only a single leading U+FEFF at the start of the file is stripped; a U+FEFF elsewhere in the content is preserved.
4. Line numbers and offsets reported in findings are unchanged for BOM-free files.
5. Whether to also report an advisory that a BOM is present is out of scope unless the implementer finds it needed; the default is silent tolerance, matching the gardener.
6. The bypass readers listed in the Rationale are enumerated from the code, each given a truthful disposition (BOM-stripped by this change with a test, not on a path that reaches a line-1-anchored pattern with the reason, or outside the reported Owner-check path with the exact remaining first-line BOM behavior), and recorded in the Progress Log. The bounded out-of-scope disposition matches AC-6; it must not claim that an exposed anchored parser lacks anchors or that every raw reader gains BOM tolerance. The set is derived by rule: every `.decode("utf-8")` or `read_text(encoding="utf-8")` under `wave_lint_lib/` and the lifecycle gate modules that feeds a `^`-anchored pattern. Stripping the BOM in a bypass reader file is a scope addendum: it is recorded in the Progress Log and the file is added to the review targets in Serialization Points at that time.
7. The Prepare and lifecycle-gate path is settled explicitly: either the change shows (test or traced evidence) that the Owner check Prepare applies runs through the docs-lint helpers this change fixes, or the gate readers `_read_wave_record_text`, `_read_member_doc_text` and `wave_validators.py` near `:1308` are given a disposition under Requirement 6. The field symptom (`wf_prepare_wave` failing on Owner) must not survive this change.

## Scope

**Problem statement:** Docs-lint reads Markdown with plain `utf-8`, so a leading BOM glues itself to the first line and breaks any `^`-anchored pattern on line 1, notably `Owner:`.

**In scope:**

- BOM stripping at the shared read helpers in `wave_lint_lib/helpers.py`.
- A docs-lint test covering a BOM-prefixed document with `Owner:` on line 1.
- Checking the other line-1 assumptions in `wave_lint_lib` and recording the result.

**Out of scope:**

- Rewriting files on disk to remove the BOM (the gardener already tolerates it).
- Editor configuration guidance.
- Other encodings (UTF-16 BOMs).

## Acceptance Criteria

All BOM fixtures are written with `write_bytes(b"\xef\xbb\xbf" + content)` (never `write_text`, which can translate or drop the mark depending on platform and encoding).

- [x] AC-1: Docs-lint on a document that begins with a UTF-8 BOM followed by `Owner:` reports no missing or invalid `Owner` finding (new test that fails on the unfixed code).
- [x] AC-2: For a corpus holding a BOM-free and a BOM-prefixed copy of two documents, one with `Owner:` as its first line and one in the standard heading-first layout, the FULL list of docs-lint findings is identical between copies (new test; the Owner-first pair is the one that fails on the unfixed code). The Owner-first BOM document is placed under a path that goes through `read_record_text` (the waves or plans roots) AND a second one under a path that goes through `read_doc_text` / `read_text`, since both helpers are patched.
- [x] AC-3: A U+FEFF that is not at the start of the file is not removed (new test on the helper).
- [x] AC-4: Reading the same BOM-prefixed file twice, cold and then from the cache (`read_text` keyed on `(mtime_ns, size)` and the record cache), returns BOM-free text both times for `read_text` and for `read_record_text` (new test; the cache is not pre-seeded).
- [x] AC-5: The Progress Log records the enumerated bypass readers from Requirement 6 with a disposition for each, and if any is disposed as "stripped" it has a BOM test (vacuously satisfied when none is stripped).
- [x] AC-6: The Prepare and lifecycle-gate path is settled per Requirement 7: a test drives `check_metadata` (`wave_lint_lib/metadata_validators.py`) through its reading path (`read_doc_text` / `read_record_text` in `wave_lint_lib/helpers.py`), the entry reached by `wf_prepare_wave_response` → `run_validate` → docs-lint `_run_full_checks`; it must not substitute the unrelated `_close_change_scoped_lint` call site, on a BOM-prefixed Owner-first change doc and reports no Owner finding, and the Progress Log records the disposition of `_read_wave_record_text`, `_read_member_doc_text` and `wave_validators.py` near `:1308` (stripped with a test, or out of scope with the reason).
- [x] AC-7: The suites `tests/test_docs_lint.py` and `tests/test_docs_gardener.py` (the gardener already tolerates a BOM and is untouched here, so this is a regression guard) and every test this change adds pass; the documents this change authors or edits validate.

## Tasks

- [x] Add the failing BOM tests in `tests/test_docs_lint.py` (AC-1, AC-2 with both read paths) and confirm they fail on the current code.
- [x] Strip a single leading U+FEFF explicitly in `read_text` (both the direct-read fallback and the cached read, before the cache store) and in the decode in `read_record_text`; do not switch to `utf-8-sig`.
- [x] Enumerate and dispose the bypass readers per Requirement 6, and log the result.
- [x] Settle the Prepare and lifecycle-gate path per Requirement 7 and add the AC-6 test.
- [x] Add the non-leading U+FEFF test and the cold-and-cached read test (AC-3, AC-4).

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| bom-test | implementer | 208l3 (test file) | Failing test first; serialized after 208l3 because both add tests to `tests/test_docs_lint.py` |
| helper-fix | implementer | bom-test | Two read points in one module |
| line1-audit | guru | none | Read-only |


## Serialization Points

Windows (native), macOS, Linux and WSL2 behavior: the BOM comes from editors, most commonly on Windows, but the same file read on macOS, Linux or WSL2 hits the same code, so the fix is platform-neutral and has no OS-specific branch. BOM-free files, the default on macOS and Linux, are unchanged (Requirement 4).

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wave_lint_lib/helpers.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`

The bypass reader files (`wave_validators.py`, `lifecycle_gate_support.py`, `core_validators.py`, `docs_constants_validators.py`) are added here only if the Requirement 6 or 7 audit decides to strip in them; that is a scope addendum recorded in the Progress Log.

## Affected Architecture Docs

N/A: the change is confined to the read helpers of the docs-lint library with no boundary, flow or contract change.

## AC Priority


| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The reported failure |
| AC-2 | important | Proves uniform behavior across checks |
| AC-3 | important | Prevents over-stripping content |
| AC-4 | important | The strip must hold on a cached read, not only a cold one |
| AC-5 | important | Bounds the unverified bypass readers; Requirement 6 depends on it |
| AC-6 | required | The field symptom included Prepare failing on Owner |
| AC-7 | required | Change-local test and doc validity |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-10 | Planned from field report; pattern behavior probed read-only, narrower than reported (Owner on line 1 only) | Verification agent report |
| 2026-10-10 | Product Intent: waived (bug fix, no product scope; default applied by the planning agent, not yet confirmed by the operator) | Readiness review round 2 |
| 2026-10-10 | Round-2 readiness repair: suite name corrected to `tests/test_docs_gardener.py`, Prepare/gate path made an explicit requirement and AC, cold-and-cached read AC, both read paths in the Owner-first fixture, `write_bytes` BOM fixtures | Council round-2 findings |

| 2026-10-10 | Readback: strip exactly one leading U+FEFF after UTF-8 errors-replace decoding, before either shared cache; retain interior and a second leading U+FEFF. Before: BOM plus line-1 Owner produces missing Owner; after: same full findings as BOM-free documents through both read paths (AC-1–AC-7). Scope: wave_lint_lib/helpers.py and test_docs_lint.py; no disk rewrite, utf-8-sig, advisory or bypass-reader source edit. | Parent activation, memory briefing and explicit shared-reader scope |
| 2026-10-10 | Thought: add red full-findings corpus parity, Owner-first Prepare metadata seam, interior/double-BOM, direct-read fallback and cold/cache tests; normalize only the shared decoded text before storage. Trace and report raw bypass limitations instead of broadening scope. | Preflight reproduced Owner failures through ordinary and record readers |
| 2026-10-10 | Traced citation correction: server_impl at the plan's 13976–13981 is _close_change_scoped_lint. Actual Prepare calls run_validate, which runs docs_lint.py; wave_lint_lib.cli._run_full_checks calls check_metadata, which uses read_doc_text and then read_text/read_record_text. The AC-6 direct check_metadata test uses that same actual oracle. | Live Prepare call chain; no changed contract or new decision |
| 2026-10-10 | Observe: five new LeadingBOMDocsLintTests fail on the unchanged reader code, covering direct Prepare metadata oracle, full-findings corpus parity, ordinary/record cache storage, one-versus-two/interior mark handling and stat-failure fallback. Fixtures use raw BOM bytes; ordinary and record Owner failures match the field symptom. | temporary bom-red.log; no skips |
| 2026-10-10 | Reflect: the bypass census confirms several raw first-line parsers, so Requirement 6's two-option wording conflicted with AC-6's explicit bounded out-of-scope option. Clarified the owning requirement rather than pretending all bypasses lack anchors or adding inconsistent one-off parser fixes; corrected AC-6 to the traced Prepare chain. Owner/helper invariance and admitted source scope stay unchanged. | Salience: medium; impact: truthful scope/evidence, no new raw-byte normalization or integrity semantics. Current receipt refresh required before further code edits. |

| 2026-10-10 | Observe: all five LeadingBOMDocsLintTests pass after the shared-reader fix, including full findings equality for Owner-first and heading-first corpus copies through ordinary and record readers, both actual cache stores, stat-failure fallback, errors-replace decoding and interior/double-leading marks. | bom-green.log; 5 methods, 0 skips; no bypass source changed |
| 2026-10-10 | Bypass disposition: wave_validators.member_status_drift decodes member bytes and calls change_doc_header_status, which has an anchored Change Status pattern. A BOM on that first status line remains exposed; Owner-first and heading-first fixtures put status later and the shared metadata oracle repairs Owner. archive readability reads/discards bytes without a first-line parser. No stripping: these raw readers are outside the reported Owner-check path and retain byte provenance. | Live code_keyword/read census; bounded AC-5/AC-6 scope gap, not universal BOM invariance |
| 2026-10-10 | Bypass disposition: lifecycle_gate_support._read_member_doc_text and _read_wave_record_text retain raw UTF-8 text for lifecycle status/record/section consumers. A field or section at byte zero can still be hidden by a BOM; the Owner check reached by Prepare instead uses the fixed shared metadata readers. load_wave_policy_state retains raw body/hash identity and sectioned policy parsing, with the same first-line section limitation. No stripping: changing these authority/parser seams is outside this Owner repair. | Actual wf_prepare_wave_response → run_validate → docs_lint.py → _run_full_checks → check_metadata → read_doc_text/shared helpers; unrelated close-change lint not substituted |
| 2026-10-10 | Bypass disposition: core_validators carrier reads use unanchored obligation searches and verbatim marker/parity interpretation. A BOM before a first owned marker can remain a structural/parity defect; no blanket BOM normalization is added. docs_constants_validators reads Python/JSON declarations rather than Owner metadata; its changelog heading splitlines parsing may retain a first-line BOM. _claims readers use unanchored content searches, while scaffold-integrity record reads already use the fixed read_record_text. | Outside reported Owner-check path; preserve exact carrier/structural checks and existing file interpretation |
| 2026-10-10 | Bypass disposition: design_system_validators reads gaps.md directly and applies anchored _GAPS_SUMMARY_RE; a BOM before a first-line Critical/Important/Nice-to-have summary remains exposed. secrets_validators direct decode/read paths preserve scanner byte offsets and raw-byte authority; allowlist lines use existing splitlines/content rules, not Owner metadata. Other direct JSON/AST configuration reads are not Markdown metadata readers. None is stripped by this change. | Bounded remaining first-line BOM cases recorded under clarified Requirement 6; no new source path or advisory |
| 2026-10-10 | Observe: leading_bom_normalization_deleted fails the Owner, real-cache and stat-fallback controls (3 failures); single_leading_bom_guard_loosened_to_all fails the double-leading mark guard (1 failure). Temporary in-memory mutants restore the original functions or loosen stripping, leaving source unchanged. | bom-mutants.json; 4 selected controls, 0 skips; named guard deletion/loosening detected |

| 2026-10-10 | Thought: Requirement6/AC6 clarification superseded the receipt; run one focused independent readiness refresh on those effects, including current code/QA and Council approval. Retain unchanged admitted scope and named suite/guard results, avoid another whole-document critique. | Source gate closed; current receipt review-policy-7e9fe1da3b0ff5f90f1a, no code edits during review. |

| 2026-10-10 | Readback and Thought: integration found the new cache-hit reader mock lacked the structural census contract. Bind the forbidden reader mock, explain the cache-hit path as inert-by-design and explicitly assert no read; keep production and census unchanged. Then run the named cache and census tests plus a cache-miss known-bad control preserving statement lookup. | Parent reproduced structural failure; admitted test-only repair, no AC/scope expansion |

| 2026-10-10 | Observe: named BOM cache test and structural patch census pass after the test-only contract repair. Active record-cache-miss known-bad keeps the forbidden reader lookup, permits the real read and fails specifically at member_read.assert_not_called (1 failure, 0 errors/skips), so the inert explanation does not hide an active call. | cache-census-repair.log: 2 tests pass; cache-miss-knownbad.json; production and census unchanged |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-10 | Strip the BOM at the shared read helpers | One fix covers every check and matches the gardener and renderer, which already tolerate a BOM | A: patch only `check_metadata` (weakness: other line-1 checks stay exposed). B: report a lint error asking the author to remove the BOM (weakness: turns an editor artifact into a blocking failure, as in the field report). C (selected): tolerate the BOM at read time |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Stripping shifts character offsets used by a check | Requirement 4 and AC-2 compare findings between BOM and BOM-free copies |
| A stripped value is cached with the wrong content | The strip happens before the cache store and AC-4 reads the same file twice (cold and cached) |
| A bypass reader still sees the BOM | Requirement 6 enumerates them; AC-5 requires a disposition and a test for each stripped one |
| Prepare still fails on a BOM Owner-first document through a gate reader | Requirement 7 and AC-6 settle the Prepare path explicitly |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
