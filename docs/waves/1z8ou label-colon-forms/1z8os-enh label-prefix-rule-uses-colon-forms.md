# Label Prefix Rule Compares Colon Forms

Change ID: `1z8os-enh label-prefix-rule-uses-colon-forms`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-28
Wave: 1z8ou label-colon-forms

## Rationale

`vocabulary_profile.validation_errors` rejects any two labels where one is a prefix of the other. A downstream vocabulary whose work items are "waves" and whose container is a "set" naturally has:

- `MEMBER_ID_LABEL = "Wave ID"`;
- `MEMBER_STATUS_LABEL = "Wave Status"`;
- a back-reference written `Wave: <set id>`, so `BACKREF_LABEL = "Wave"`.

The profile refuses it with "BACKREF_LABEL and MEMBER_ID_LABEL must not be a prefix of one another ('Wave', 'Wave ID')". Every label is written with a trailing colon, so the tokens on the page (`Wave:`, `Wave ID:`, `Wave Status:`) are not prefixes of one another. The rule guards against readers that match a bare label with `startswith(label)` or a substring test, where `Wave` would also match `Wave ID: ...`. Without this change, a downstream vocabulary needs a different back-reference label and a migration of every work-item record, which the profile exists to avoid.

## Requirements

1. **Refuse only exact-duplicate labels.** In `vocabulary_profile.validation_errors`, the label-pair loop over `ID_KEY`, `MEMBER_ID_LABEL`, `MEMBER_STATUS_LABEL`, `BACKREF_LABEL` and the derived previous-status label refuses only exact duplicates, compared after `casefold()`. Labels may not contain `:`, so comparing the colon forms (`label + ":"`) is the same as refusing duplicates. The heading loops are unchanged, because headings are still read by substring. The label-against-`FIXED_LABELS` prefix loop is kept and now also compares casefolded, because `memory_backfill._wave_status` and the rendered Stop hook read the fixed `status:` label case-insensitively. This changes no shipped default. The same applies to `ARCHIVE_PROFILE`, which goes through the same function.
2. **Anchor every label reader to the start of a line.** The readiness census found no reader that matches a label without its colon, but six match the colon form anywhere in the text. Those six are anchored with `(?m)^`:
   - the four `f"{ID_KEY}:" in text` tests in `wave_lint_lib/wave_validators.py` (in the functions containing lines 1134, 1171, 2227 and 2363 at the time of the review);
   - `wf_server/server_impl._change_block_pattern`;
   - the new-change template fill `re.sub(rf"{MEMBER_ID_LABEL_RE}:.*", ...)` in `server_impl`.
3. **Census test.** It fails on any non-test reader of a profile label that is not both colon-terminated and line-anchored. It uses a line scan with an allowlist and planted controls, modelled on `tests/test_vocabulary_census.py`, and states its predicate. Labels passed through variables (for example `status_label`, `_wf_id_prefix`, a `member_id_label_re` parameter) get allowlist entries with reasons, or a stated known limit.
4. **Tests and comments.**
   - `tests/test_vocabulary_profile.py::test_labels_must_not_prefix_each_other` is inverted to accept the `Wave`, `Wave ID` and `Wave Status` set; `test_labels_must_differ_from_each_other` stays.
   - The rationale comment in `validation_errors` and the `vocabulary_profile` module docstring point to `docs/architecture/layering-rules.md` as the single statement of the rule rather than restating it.
5. **Architecture doc and CHANGELOG.** `docs/architecture/layering-rules.md`'s vocabulary paragraph is the single statement of the rule: every label reader is line-anchored and colon-terminated; the profile refuses only duplicate labels (casefolded); the fixed-label check compares casefolded; a census enforces the reader rule. The CHANGELOG notes both behaviours: prefix-pair label sets such as `Wave`, `Wave ID` and `Wave Status` are now accepted, and a label that differs from a fixed label only in case (for example `status`) is now refused.

## Scope

**Problem statement:** the label rule is stricter than the written tokens require, and blocks a natural downstream vocabulary.

**In scope:**

- `vocabulary_profile.validation_errors` and its docstring and comments.
- The six anchoring fixes; the census test; the second-profile end-to-end test; `layering-rules.md`; CHANGELOG.

**Out of scope:**

- Changing the shipped default labels.
- A shared `label_line_re(label)` helper that readers would use to build anchored patterns. It is a follow-up (see Decision Log).

## Acceptance Criteria

- [x] AC-1: a profile with `BACKREF_LABEL = "Wave"`, `MEMBER_ID_LABEL = "Wave ID"` and `MEMBER_STATUS_LABEL = "Wave Status"` validates, and so does the same as `ARCHIVE_PROFILE`.
- [x] AC-2: the second-profile driver (`tests/test_vocabulary_second_profile.py`), extended as follows, parses a real record set correctly under that profile. A work item carries a `` Wave: `<set id>` `` back-reference, and the dashboard reports the set id from it, not the folder fallback; member ids and statuses are unaffected; `wf_add_change` inserts a block and repairs the back-reference; the remove-change block pattern removes it; `_extract_change_ids_from_wave_text` reads the member ids. The control discriminates on the `Wave ID` and `Wave Status` lines, because `BACKREF_LABEL` equals the default. Fixture rules: (a) the `Wave:` value must satisfy docs-lint (`docs_constants_validators.check_wave_scaffolding_integrity` accepts only the folder name or a prefix of it) and still differ from the folder fallback, so it is a strict prefix of the folder name (for example `` Wave: `change-2026` `` in folder `change-2026-03`), or a fixture folder whose name begins with the set id; (b) a second document carries `Wave: TBD` and lives under `docs/plans/` (where `TBD` is the shipped template default and lint accepts it), because `wf_add_change` repairs only placeholder back-references; the test admits it with `wf_add_change` and asserts the repaired value, and lint runs before admission or after the repair; (c) a second scenario sets `ID_KEY = "ID"` beside `MEMBER_ID_LABEL = "Wave ID"` (a suffix pair), which reaches the four `f"{ID_KEY}:" in text` sites, and lint must report no spurious record errors on the change docs, while `_change_block_pattern` stays covered by the census; (d) mutation control: the driver run against a deliberately unanchored copy of one reader fails, proving the scenario discriminates.
- [x] AC-3: exact-duplicate labels, including case-only differences, are refused. The heading prefix checks are unchanged. The fixed-label prefix check now compares casefolded, so a case-variant of a fixed label (for example `status`) is refused, with a test.
- [x] AC-4: the census test fails on a planted colon-terminated but unanchored reader and on a planted bare-label reader, and passes on the tree.
- [x] AC-5: the change's own suites pass, and the documents it edits validate.

## Tasks

- [x] Relax the validator to casefolded exact-duplicate refusal; update the comment and module docstring; invert `test_labels_must_not_prefix_each_other`.
- [x] Anchor the six readers; add the census test with planted controls.
- [x] Extend the second-profile driver and fixtures (a `Wave:` line, lifecycle steps, the discriminating control); add the `ARCHIVE_PROFILE` half.
- [x] `layering-rules.md`; CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Readers and rule | implementer | readiness | Anchoring first, then relax the rule |
| Review | combined reviewer | Readers and rule | Code, QA, architecture |

## Serialization Points

- `.wavefoundry/framework/scripts/vocabulary_profile.py`, `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_vocabulary_profile.py`, `.wavefoundry/framework/scripts/tests/test_vocabulary_second_profile.py`, `.wavefoundry/framework/scripts/tests/test_vocabulary_census.py`, `.wavefoundry/framework/scripts/tests/fixtures/`
- `docs/architecture/layering-rules.md`
- `CHANGELOG.md`

## Affected Architecture Docs

`docs/architecture/layering-rules.md`: the vocabulary profile paragraph (Requirement 5).

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The requested vocabulary |
| AC-2 | required | Readers must actually be safe under it |
| AC-3 | required | Real collisions still refused |
| AC-4 | required | The census is the lasting guard |
| AC-5 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-28 | Delivery repair DEL-F1 (operator review): the census anchored-reader shape matched a literal `^` character, so an escaped `\^` or a character-class `[^` counted as an anchor. The shape now requires a `^` not preceded by a backslash or `[`, and the planted-reader test adds both forms (lines 19 and 21 of the fixture). No shipped reader used either form | `tests/test_label_reader_census.py` 5 OK; reverted-pattern scratch control fails the planted-reader test |
| 2026-09-28 | Mutation control (AC-2 d), run in scratch copies under the session scratchpad, not in the repository: unanchoring `server_impl._CHANGE_STATUS_PATTERN` fails `test_member_ids_and_statuses` (list_waves reads the `Previous Wave Status` line); making the dashboard `_WAVE_RE` match the bare label fails `test_dashboard_reads_the_back_reference` (reads `planned` from the `Wave Status` line). Reverting the four `ID_KEY` tests or `_change_block_pattern` to the unanchored form does NOT fail the driver: the `ID_KEY` tests are also gated by the member heading and closed status (lines 1134/1171) or iterate only the record file (2227/2363), and the block pattern matches an exact change id, so the unanchored forms produce no observable error on this fixture. The census fails on all four mutated trees, naming each line. Focused suites green: test_vocabulary_profile (32), test_vocabulary_second_profile (11), test_label_reader_census (5), test_vocabulary_census (5), test_docs_lint (1115), test_server_tools_lifecycle (552), test_vocabulary_writers, test_archive_root, test_record_layout_lifecycle, test_record_layout_nested, test_record_layout_census, test_lifecycle_mutation_lock, test_review_policy | scratch mutation runs; `run_tests.py --file` |
| 2026-09-28 | Implemented Requirements 1 to 5. Census predicate: every non-test `.py` line under `scripts/` except `vocabulary_profile.py` naming `ID_KEY`, `MEMBER_ID_LABEL`, `MEMBER_STATUS_LABEL`, `PREVIOUS_STATUS_LABEL` or `BACKREF_LABEL` (optionally `_RE`) as a word; each reference must sit in a `^`-anchored colon-terminated regex field, a `re.fullmatch` of the colon form, or `startswith(f"{label}:")` on a `splitlines()` line, else inside an allowlisted snippet (message, writer, exact_key, newline_anchored, variable). Result: 63 reference lines outside tests and the profile module (matching the review's figure of about 63); the six colon-terminated unanchored readers were exactly those the plan named (four `f"{_vocab.ID_KEY}:" in text` tests in `wave_validators`, `_change_block_pattern`, the template fill in `server_impl.new_change`); no bare-label reader; no difference from the review census. Anchored with `(?m)^` (`\n?^` for the block pattern), then relaxed `validation_errors` to casefolded duplicate refusal with a casefolded fixed-label prefix loop. `test_labels_must_not_prefix_each_other` is inverted and renamed `test_labels_may_prefix_each_other`. New `tests/test_label_reader_census.py`; `PrefixLabelProfileTests` in the second-profile driver. Gapfill: `code_pattern` with a `scripts/**/*.py` glob skipped top-level modules and `server_impl.py` (over 1 MB), so the reference census was re-run with `grep -rnE` | `vocabulary_profile.py`, `wave_validators.py`, `server_impl.py`, tests |
| 2026-09-28 | Final readiness confirmation: adoptions correct; F1 (AC-3 wording and a case-variant test), F2 (`ID_KEY = "ID"` for the suffix scenario), F3 (`Wave: TBD` under `docs/plans/`) adopted, plus the red-team mutation control and the docs-contract single statement of the rule in `layering-rules.md` with both behaviours in the CHANGELOG | readiness confirmation |
| 2026-09-28 | Readiness confirmation: N1 to N7 resolved. Adopted the N4 leftover (casefold the fixed-label loop), R1 (a back-reference fixture that satisfies docs-lint and still discriminates, plus a `Wave: TBD` document for the repair step), and the red-team suffix-pair scenario. Census predicate note: `startswith(label + ":")` on `splitlines()` output, the Stop hook's prefix test and exact-key membership count as anchored, with allowlist reasons | readiness confirmation |
| 2026-09-28 | Readiness review. About 63 non-test reference lines reviewed; 30 places match a label against record text, of which 24 are already colon-terminated and line-anchored, 6 are colon-terminated but unanchored, and none is bare. Relaxing the rule in a scratch tree passed the current second-profile test, but vacuously, since no fixture carries a `Wave:` line. Adopted N1 (exact-duplicate refusal, stated as such), N2 (anchor the six, census requires anchoring), N3 (invert the prefix test, update comments), N4 (casefold), N5 (the AC-2 driver and control), N6 (`layering-rules.md` and the docstring), N7 (narrowed Serialization Points) | readiness review |
| 2026-09-28 | Planned from a downstream validation report. Confirmed the rule in `vocabulary_profile.validation_errors` | `vocabulary_profile.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-28 | Refuse only exact (casefolded) duplicate labels; keep the heading prefix rule; casefold the fixed-label prefix rule | Labels cannot contain `:`, so colon-form comparison is duplicate refusal; headings are still read by substring; some fixed labels are read case-insensitively | Relax every loop |
| 2026-09-28 | Anchor the six unanchored readers and enforce anchoring with a census | Safety moves from the import-time rule to the readers; the census keeps it | Relax the rule only |
| 2026-09-28 | A shared anchored-regex helper is a follow-up | Keeps this change small; the census already catches mistakes in this repository (readiness architecture seat) | Add the helper now |

## Risks

| Risk | Mitigation |
| --- | --- |
| A fork adds its own reader without running the census | The helper follow-up; `layering-rules.md` states the reader rule |
| A reader missed by the census mis-parses under the new vocabulary | AC-2 exercises the reader set on a real record set with a discriminating control |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
