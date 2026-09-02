# Verdict-Gap and Install-Audit Hardening

Change ID: `1wybr-debt verdict-gap-and-install-audit-hardening`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-01
Wave: 1wybs review-churn-follow-ups

## Rationale

The `1wuju` delivery review (code lane CODE-DEL-3 and CODE-RV4-1, docs-contract
lane DOCS-FIN-1) carried six low observations as "maybe later" under the
frozen-tree rule rather than widening a repair round. Each has a named site
and a small fix, and is cheaper to land now than to re-find. (1)
`_strip_repository_root` replaces every occurrence of each root spelling: a
filesystem-root spelling (`/`) rewrites every `/` in the cause line, and a
relative spelling (`repo`) deletes that segment wherever it occurs while the
path stays absolute (readiness RT-RDY-4, executed); both are unreachable today
because `discover_root` resolves every root, but the helper has no guard of
its own. (2) `_docs_lint_verdict_gap_error` takes `root=None` by default, so a
caller that forgets it leaks the absolute path (the exact mutant CODE-RV4-1
found at the incremental runner); its only two callers are the two runners.
(3) The synthesized cause line is uncapped, so a long crash line rides into
every gate's diagnostic. (4) The `1viyu` synthesized-failure branch in
`wf_audit_install_response` (`passed` false with no errors) is unreachable on
the public path now that `run_validate` synthesizes an entry on every non-zero
exit (`passed` is `returncode == 0`, and the timeout branch returns an error
entry); its pin keeps it alive only by patching `run_validate`, so the branch
is dead code with a test that fixes its shape rather than proving a mechanism.
(5) The install-audit verdict-gap pin hand-builds its entry string instead of
deriving it from the producer, so a wording change breaks the pin instead of
the pin proving the contract. (6) The `install_log_checked_but_missing`
diagnostic, the `expected_artifact` field, `all_missing[].expected_artifact`,
and the `next_action` sentence render the artifact's absolute path (wave
`1p35d` behaviour), against the `1uu9z` convention that operator-facing
messages render repository paths repo-relative; the only documentation of the
envelope, `docs/references/install-log-format.md` and its byte-identical
shipped twin, names a field `expected` the producer never emits.

## Requirements

1. `_strip_repository_root` SHALL use only root spellings that are absolute and are not their own parent (`candidate.is_absolute() and candidate.parent != candidate`), which skips a filesystem anchor on every platform and any relative spelling; the replacement loop SHALL live in `_strip_root_forms(text, forms)`, which also strips each spelling's repr-doubled variant (every backslash doubled, as a Windows traceback renders a path through `%r`), pinned at string level with a Windows-shaped forms list (delivery review DOCS-DEL-5); and `_docs_lint_verdict_gap_error` SHALL require `root` (no default). Both runners already pass it.
2. The synthesized cause SHALL be capped at a named constant of at least 240 characters, retaining the head and the tail around a middle marker so the exception class at the head and the quoted detail at the tail both survive, applied after the root is stripped so the marker never hides a path; the exact-cap boundary and the strip-then-cap order SHALL each be pinned (delivery review CODE-DEL-3, ARCH-DEL-2: a root straddling the head cut leaves a root fragment under the reversed order).
3. The `1viyu` synthesized-failure branch in `wf_audit_install_response` SHALL be removed. One parameterized test SHALL replace the patched-result pin and the hand-built gap pin: it patches `_mcp_subprocess_run` only, drives two crashed-subprocess shapes (a plain crash tail; an absence-marker tail on a log with pending seed rows) through the real `run_validate` parser into `wf_audit_install_response`, and asserts `lint_errors`, `pending_lint.count` zero, and equality of the entry with `_docs_lint_verdict_gap_error(rc, output, root)`. The RTD-1 property (an absence-marker tail is never deferred) is preserved by the verdict-gap prefix bypass, which stays.
4. The `checked_but_missing` envelope SHALL render the artifact path relative to the repository root in its diagnostic message, `expected_artifact`, `all_missing[].expected_artifact`, and `next_action`, through a tolerant wrapper around `_repo_rel` that falls back to a `..`-relative path (`os.path.relpath` over the resolved pair) when the artifact resolves outside the repository (an operator-authored row can carry an absolute or `../` value, and `_repo_rel` raises `ValueError` there; delivery review CODE-DEL-5 replaced the resolved-string fallback, which carried the repository's parent directories) and to the resolved string only when no common anchor exists (a different Windows drive), so a crash never replaces the envelope; the existing envelope pin is extended to assert that no absolute repository path appears and gains a subtest with an escaping artifact value.
5. `docs/specs/mcp-tool-surface.md` under `wf_audit_install` SHALL gain a new sentence naming `expected_artifact`, `all_missing[].expected_artifact`, and `next_action` and their repo-relative form (the field was undocumented until now), pinned beside the existing matrix anchor in `test_server_tools_retrieval.py` (delivery review DOCS-DEL-4), and both copies of `install-log-format.md` (`docs/references/install-log-format.md` and `.wavefoundry/framework/install/install-log-format.md`, pinned byte-identical) SHALL correct the envelope field list (`expected` to `expected_artifact`, adding `phase` and `all_missing`), with a content pin on the shipped copy's field list beside the parity pin (delivery review DOCS-DEL-3). The registered tool docstring enumerates no fields and needs no change.

## Scope

**Problem statement:** Six small, sited hardening and consistency defects on the verdict-gap and install-audit paths were carried out of `1wuju` rather than repaired, and the one document describing the install-audit envelope names a field that does not exist.

**In scope:**

- `server_impl.py`: the sanitizer guard, the required `root`, the cause cap, the branch removal, the tolerant repo-relative install-audit paths.
- `test_server_tools_lifecycle.py`: the parameterized real-parser test replacing the two pins, the extended envelope pin, the new sanitizer and cap pins.
- `docs/specs/mcp-tool-surface.md` under `wf_audit_install`; both `install-log-format.md` copies; the CHANGELOG bullet.

**Out of scope:**

- Unifying the two path-free vocabularies for one `PermissionError` (`_read_error_detail` and the sanitizer). Both are path-free, and unifying would alter a `1uu9z`-pinned message for no operator benefit.
- Windows execution of the sanitizer (separator handling stays checked at string level; the `is_absolute` guard covers a drive root by construction).
- `install_log_lib.checked_rows_missing_artifact`, which keeps returning resolved paths; rendering is a response concern.

## Acceptance Criteria

- [x] AC-1: For a filesystem-root spelling and a relative spelling the cause line returned by `_strip_repository_root` is byte-identical to its input, a real root is still stripped in both its given and resolved spellings, a repr-doubled Windows spelling is stripped by `_strip_root_forms` at string level, and `_docs_lint_verdict_gap_error` called without `root` raises `TypeError`; pinned, and the guard-removed and doubled-variant-removed mutants each fail their assertion.
- [x] AC-2: A cause longer than the cap is truncated to the head and tail around the marker, still carries the exception class and the final quoted token, and carries no absolute repository path; a cause under the cap and a cause of exactly the cap are unchanged while cap+1 is truncated to the cap; a root straddling the head cut leaves no fragment (the strip-then-cap order is asserted by equality with the documented composition); pinned, and the boundary-loosened and order-reversed mutants each fail.
- [x] AC-3: The `1viyu` branch is gone, and the parameterized test drives both crashed-subprocess shapes through the real `run_validate` parser into `wf_audit_install_response`, asserting `lint_errors`, `pending_lint.count` zero, and equality with the producer's entry; the `run_validate` synthesis removed fails both subtests and the prefix bypass removed fails the absence-marker subtest (mutant table).
- [x] AC-4: The `checked_but_missing` diagnostic, `expected_artifact`, `all_missing[].expected_artifact`, and `next_action` carry the artifact path relative to the repository root and never the absolute repository path, an escaping artifact value still returns the envelope with a `..`-relative path carrying no absolute segment, and the spec's `wf_audit_install` sentence and both `install-log-format.md` copies name the fields as emitted; pinned by the extended envelope pin, the byte-identical-copies pin, the shipped copy's field-list content pin, and the spec-sentence pin.
- [x] AC-5: The tests this change adds pass, the documents this change authors or edits validate, and no failure elsewhere is attributable to this change.

## Tasks

- [x] Open `framework_edit_allowed`; guard the sanitizer with `is_absolute` and `parent != self`, require `root`, cap the cause with head-and-tail retention.
- [x] Remove the `1viyu` branch; write the parameterized real-parser test through `_mcp_subprocess_run`; delete the patched-result pin and the hand-built gap pin it replaces.
- [x] Render the `checked_but_missing` paths through the tolerant repo-relative wrapper; extend the envelope pin (no absolute path; escaping artifact subtest).
- [x] Spec sentence under `wf_audit_install`; correct both `install-log-format.md` copies identically.
- [x] CHANGELOG Unreleased bullet; close the gate; run the lifecycle test module and the full suite last.
- [x] Record the mutant table in this Progress Log (sanitizer guard removed, `root` default restored, cap removed, `run_validate` synthesis removed, prefix bypass removed, repo-relative render removed, tolerant fallback removed).

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Sanitizer and cause cap | implementer | — | Gate opened and closed around the edits |
| Install audit branch and real-parser test | implementer | Sanitizer and cause cap | Patch `_mcp_subprocess_run` only |
| Repo-relative paths, spec, and format docs | implementer | — | Both format copies byte-identical |


## Serialization Points

- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
- `docs/specs/mcp-tool-surface.md`, `docs/references/install-log-format.md`, `.wavefoundry/framework/install/install-log-format.md`
- The root `CHANGELOG.md` Unreleased section (a root-level file cannot be declared as a path; it is named here in prose).

## Affected Architecture Docs

N/A: the change is confined to the lint-parse and install-audit paths inside `server_impl.py` and their pins; no module boundary, contract flow, or test seam moves. The `wf_audit_install` envelope's field names and path rendering are spec and reference-format details, recorded in `docs/specs/mcp-tool-surface.md` and `install-log-format.md`.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | important | Hardening of an unreachable case plus the one-line leak guard the mutant found. |
| AC-2 | important | Bounded diagnostics at every gate without losing the actionable ends. |
| AC-3 | required | Deleting code needs the surviving mechanism proven on the real path. |
| AC-4 | required | Operator-facing path convention (`1uu9z`), the envelope must survive an escaping row, and the only documentation must name real fields. |
| AC-5 | required | The change's own evidence. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-02 | Delivery round 1 repair (ARCH-DEL-2 merging CODE-DEL-2; CODE-DEL-3 merging RT-DEL-3, QA-DEL-2; DOCS-DEL-5 merging RT-DEL-2; CODE-DEL-5 merging RT-DEL-4; DOCS-DEL-3 merging QA-DEL-3; DOCS-DEL-4). `_strip_root_forms(text, forms)` now carries the replacement loop and adds each spelling's repr-doubled variant (its doubled separator handled before the single one), so `_strip_repository_root` is unchanged on POSIX and the Windows `%r` case is pinned at string level (`test_the_sanitizer_strips_a_repr_doubled_windows_spelling`). `test_a_long_cause_keeps_its_head_and_tail` asserts the exact cap unchanged, cap+1 truncated to the cap, and, with the temp root straddling the head cut, equality with `_cap_cause_line(_strip_repository_root(line, root))` plus no 20-character fragment of either root spelling (the reversed order leaves `/private/var/folders...` beside the marker). `_install_artifact_display` falls back to `os.path.relpath` over the resolved pair (a `..`-relative path) and to the resolved string only when no common anchor exists; the escaping subtest asserts `../outside/config.json` and no parent-directory segment; the spec sentence and both format copies say relative to the repository root with leading `..` segments. The spec sentence is pinned in `test_audit_install_public_carriers_pin_status_and_pending_lint_matrix`; the shipped format copy's field list is pinned in `test_install_log_format_names_the_checked_but_missing_fields_the_audit_emits`; the CHANGELOG bullet gains the doubled-spelling and `..` clauses and is pinned. Landing rule (scratch `mut16`, controls first): strip and cap order reversed CAUGHT; cap boundary loosened CAUGHT; doubled-variant expansion removed CAUGHT; relpath fallback replaced by the resolved string CAUGHT; both format copies renamed CAUGHT; spec sentence deleted CAUGHT; CHANGELOG lead deleted CAUGHT. `RunValidateTests` + `WaveInstallAuditTests` 34 OK; the real-subprocess leak pin, the every-gate crash pin, and the install-audit advisory pin 4 OK. | `mut16_run.log`; `1wybs_r1_targeted_a.log`, `_b.log`, `_d.log`; `full_suite_1wybs2.log` (8,051 OK). |
| 2026-09-02 | ARCH-DEL-1 (blocking, architecture lane): `server_impl.py` is a member of `retrieval_eval.PRODUCTION_RETRIEVAL_MODULES`, so this change moved `production_identity` (`2cb07c8f` on the `1wuju` receipt to a new digest, `server_impl.py` the only module that differs; evaluator identity `aa5a57e4` unchanged). Under the policy `1wybq` writes, this wave is the one that changes production retrieval bytes and owes the before/after pair; the `1wuju` receipt is the before-receipt (pre-change tree, current evaluator). The after-receipt is recorded on the final tree after every round-1 repair landed; its row follows. OPERATOR FOLLOW-UP: whole-module identity (`1wur7` RT-RDY-4) means a lifecycle-only edit to `server_impl.py`, which cannot change retrieval results, still costs a receipt; a finer production identity is an operator decision, recorded in the wave record's watchpoints. | `1wuju` receipt identity block; ledger `ev-arch-del-1`, `ev-arch-del-1-2`. |
| 2026-09-02 | Gapfill (process): the final `wf_prepare_wave(mode='ready')` re-stamped `Last verified` on `docs/references/install-log-format.md` but not on its shipped twin under `.wavefoundry/framework/install/`, so the byte-identical parity pin `test_shipped_templates_are_byte_identical_to_canonical` failed the full suite on the final tree (the only failure in 8,051). The shipped copy was re-synced from the canonical one and the suite re-run; lesson: after any gardening pass, re-check every shipped/canonical pair before the last suite run. | `full_suite_1wybs5.log` (one failure), `full_suite_1wybs6.log`. |
| 2026-09-02 | Cycle-2 reverification editorial notes (inline): ARCH-RV2-1, row 38 of `testing-architecture.md` called the `1wuju` before-receipt incomparable although the compatibility rule accepted it as this wave's `--baseline`; it now distinguishes a superseded evaluator identity (incomparable) from superseded production bytes (no longer the reference). ARCH-RV2-2, the session handoff's commit obligation named the `1wuju` receipt as the standing baseline and omitted the untracked `docs/reports/retrieval-quality-post-1wybs.json`; corrected. | Cycle-2 architecture reverification report. |
| 2026-09-02 | Delivery round 2 (editorial, inline): ARCH-RV1-1, the two ARCH-DEL-1 rows above were malformed (the finding row lacked its Evidence cell and the receipt row carried five cells); refolded into three cells each. QA-RV1-2, the stale comment in `test_checked_but_missing_artifact_returns_diagnostic` and the Risks row still said the fallback carried the resolved string; both now say a `..`-relative path. ARCH-RV1-2 (merging QA-RV1-1, ledger finding): the reference-receipt pointer in `review-and-evals.md` and `testing-architecture.md` row 38 moves to `docs/reports/retrieval-quality-post-1wybs.json` with its verdict and drift disposition disclosed, pinned in `EvaluatorEditBaselinePolicyPinTests`; the `1wuju` receipt is described as the before-receipt this wave consumed. | Round-1 reverification reports (architecture, qa); `mut18_run.log`. |
| 2026-09-02 | ARCH-DEL-1 receipt: `docs/reports/retrieval-quality-post-1wybs.json` (run `2691fb866569380d`, index generation 211 at start and end, evaluator identity `aa5a57e4` = the `1wuju` receipt, production `aea5d119` against `2cb07c8f`, comparison `cross_generation`, `end_digest_verified` on the production block). Recorded with the `1wujt` recipe (index brought current, `reindex-pending` touched every 45 s, foreground, 345 s). Verdict `fail`: five `quality_regression` violations on `code_ask` holdout, all under the zero-tolerance rule (`cur + 1e-12 < base`), largest 0.055 nDCG@10 on `assessment_boundary_control`; nine case metrics moved across the run, three up (including `code_ask` calibration recall 0.25 to 0.50) and six down, two on `code_search`. Attribution: the pre-wave `server_impl.py` was reconstructed by reversing this change's edits and its production digest equals the `1wuju` receipt's `2cb07c8f` byte for byte, so the wave's whole production change is the 168-line diff on `_docs_lint_verdict_gap_error` (with `_cap_cause_line` and the cap constants), `_strip_repository_root` (with `_strip_root_forms`), `_install_artifact_display`, and `wf_audit_install_response`; the call-site census shows each is reached only from `run_validate`, `run_validate_changed`, and the lifecycle gates, never from `code_ask`, `code_search`, `docs_search`, or `code_lexical`. Disposition: corpus drift across 37 generations (this wave's review-shaped documents entered the index), not a regression; routed to operator review; the `1wybq` policy now discloses the attribution. | `baseline_1wybs_1.log`; `recon_vs_current.diff`; `mut16_run.log`. |
| 2026-09-01 | Landing rule: seven scratch-copy mutants under session scratch `mut15`, each caught on an otherwise green base (controls run first): the sanitizer guard removed (`test_the_sanitizer_ignores_a_filesystem_root_or_relative_spelling`, four subtests fail: `/`, `repo`, `.`, `docs`); the `root` default restored (`test_the_gap_producer_requires_the_root`); the cause cap removed (`test_a_long_cause_keeps_its_head_and_tail`); the `run_validate` synthesis removed (`test_a_lint_crash_reaches_the_install_audit_through_the_real_parser`, both subtests); the prefix bypass removed (the same test, the absence-marker subtest only); the repo-relative render removed and, separately, the tolerant fallback removed (`test_checked_but_missing_artifact_returns_diagnostic`, the second as an error from `ValueError`). | `mut15_run.log`: 16 of 16 caught across the wave. |
| 2026-09-01 | Implemented. `server_impl.py`: `_strip_repository_root` uses only spellings that are absolute and not their own parent; `_docs_lint_verdict_gap_error` requires `root` and caps the cause through `_cap_cause_line` (`DOCS_LINT_VERDICT_GAP_CAUSE_CAP` 240, head and tail around `DOCS_LINT_VERDICT_GAP_CAUSE_MARKER`) after the root is stripped; the `1viyu` passed-false-with-no-errors branch in `wf_audit_install_response` is removed with a comment naming the real-parser proof; `_install_artifact_display` renders `checked_but_missing` paths through `_repo_rel` with a `ValueError` fallback to the resolved string, used by `expected_artifact`, `all_missing[]`, `next_action`, and the diagnostic. Tests: three new `RunValidateTests` pins; `test_a_lint_crash_reaches_the_install_audit_through_the_real_parser` (patches `_mcp_subprocess_run` only; two subtests; asserts equality with the producer's entry) replaces `test_lint_failure_without_error_lines_fails_closed` and `test_a_verdict_gap_error_blocks_the_install_audit_even_when_it_quotes_an_absence_marker`; `test_checked_but_missing_artifact_returns_diagnostic` extended (repo-relative fields, no absolute root in any operator-facing text, escaping-row subtest). Spec: new `checked_but_missing` sentence under `wf_audit_install`; both `install-log-format.md` copies name `phase`, `row`, `expected_artifact`, `all_missing`, `next_action`, `pending_lint` and stay byte-identical. CHANGELOG Changed bullet. Gapfill: region reads during implementation used shell `sed` over the anchors located with MCP `code_keyword` at planning; edits are exact-string replacements. | `1wybs_targeted_2.log` (`RunValidateTests` + `WaveInstallAuditTests`, 33 OK); `1wybs_targeted_3.log` (the `1uu9z` real-subprocess leak pin, the every-gate crash pin, the install-audit advisory pin: 4 OK); `test_shipped_reference_docs` green in `1wybs_targeted_1.log`. |
| 2026-09-01 | Readiness council amendments applied (RT-RDY-4 to RT-RDY-7, RT-RDY-9, DOCS-RDY-8): the guard is `is_absolute` and `parent != self` with a byte-identity assertion (a "slashes intact" assertion passes on the unguarded code for a relative root); `_repo_rel` raises `ValueError` outside the root, so the render is tolerant with an escaping-row subtest; the cap keeps head and tail (existing pins assert tail tokens such as `'advisry'` and the quoted path); Requirements 3 and 4 collapse into one real-parser test through `_mcp_subprocess_run`; the spec sentence is new and both `install-log-format.md` copies are corrected. | Readiness council checkpoint in `wave.md`; `_repo_rel` executed on an outside path; `install-log-format.md` line 82 in both copies. |
| 2026-09-01 | Drafted from the `1wuju` code-lane and docs-contract-lane residual observations. Sites read, not remembered: `server_impl.py` lines 4638 to 4667 (producer and sanitizer), 12580 to 12600 (the `1viyu` branch), 12660 to 12690 (the `checked_but_missing` envelope); pins at `test_server_tools_lifecycle.py` lines 13880 and 14005. | `1wuju` ledger records CODE-DEL-3 (limitations), CODE-RV4-1, DOCS-FIN-1 (limitations), and the code lane's delivery approval. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-01 | Land all six as one debt change, plus the format-doc field correction the readiness council found. | Each has a named site and a named pin, and together they fit one review round. | **Keep the `1viyu` branch as defence in depth:** a dead branch with a patch-only pin is the "pin that passes for an unrelated reason" the landing rule forbids. **Route the sanitizer through `_read_error_detail`'s vocabulary:** changes a `1uu9z`-pinned message for no operator gain. **Render through `_repo_rel` directly:** an escaping artifact row would turn the envelope into an unhandled exception at the tool boundary. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Removing the `1viyu` branch removes a fail-closed guard if `run_validate` ever again returns `passed` false with no errors. | The real-parser test proves the `run_validate` contract (a non-zero exit always yields an error entry) end to end, and the timeout branch already returns an error entry. |
| The repo-relative `expected_artifact` changes a field a consumer parses. | The field was undocumented until this change (the format document named a different field and stated no path form); the spec and both format copies now record its name and form. |
| An artifact path outside the repository crashes the render. | The tolerant wrapper falls back to a `..`-relative path (and to the resolved string only across drives) and a subtest drives that row. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
