# Correctness and Test Hygiene Round: Linear Fence Scan, One History-Path Constant, Archive-Aware Journal Tests, Vendored-Script Audit Finding

Change ID: `1zxnt-maint correctness-and-test-hygiene-round`
Change Status: `implemented`
Owner: framework-operator
Status: implemented
Last verified: 2026-10-06
Wave: 1zyb2 correctness-and-test-hygiene
Depends on: wave B's change `1zxns-bug change-id-and-path-containment` lands first (ordering recorded in Risks and the Progress Log, not as a wave-record dependency); this change moves `offline_problems` as wave B leaves it (containment included) into a shipped module and does not alter its behavior.

## Rationale

A downstream distribution's verified report (checked against HEAD `06c02e63`) left five small items that do not belong with the lock, containment, extensibility or vocabulary changes. Each is independently verifiable and none changes a public tool schema.

- **Quadratic fence scan (R8).** `change_doc_checklist.fenced_line_flags` rescans to the end of the document from every opener that never closes. Measured here on `["```python"] * n` (an info string cannot close a fence, so every line is an unterminated opener): 1000 lines 0.12 s, 2000 lines 0.47 s, 4000 lines 2.2 s, a clean 4x per doubling. The function runs inside change-doc readers in `wf_server/server_impl.py` (six call sites) and in the checklist helpers, so a long unclosed-fence document stalls a tool call.
- **History-path exclusion duplicated nine times (R3).** The skip for journal and snapshot history is written inline in nine places, and the report's "one predicate" is not what the code has. Census predicate: a line in `.wavefoundry/framework/scripts/` (non-test, non-historical) that tests a path's components or parts for the literal `journals` or `snapshots` as a record-history exclusion. Command: `rg -n '"journals"|"snapshots"' .wavefoundry/framework/scripts --glob '!tests/**'`, then discard the non-record hits (`_tag_utils.py:96`, a `docs/agents/journals/` substring that assigns a retrieval tag and is not an exclusion, is excluded from the census; `model_bundle.py`, `accel_embedder.py`, `setup_index.py` and `upgrade_wavefoundry.py` name the Hugging Face model cache's `snapshots` directory, which is unrelated). Result: nine sites with four distinct predicates, not one.

  | Site | Components tested |
  | ---- | ----------------- |
  | `agent_surface_integrity.py:43` | `memory`, `journals` |
  | `render_agent_surfaces.py:296` | `journals`, `memory`, `personas` |
  | `upgrade_extensions.py:2220` and `:2445` | `journals` |
  | `wave_lint_lib/wave_validators.py:790`, `:812`, `:838` | `journals`, `memory` |
  | `reconcile_scan.py:435` (`_EXCLUDED_PATH_COMPONENTS`, used at `:847`) | `journals`, `snapshots` |
  | `wf_server/server_impl.py:16045` | `journals`, `reports`, plus a name containing `feedback` or `journal` (a retrieval-ranking demotion, not a lint skip) |

  Only `reconcile_scan` knows `snapshots`, so a directory named `snapshots` is history to one scanner and live to the other eight. The shared constant must make that one decision once.
- **Journal migration tests ignore the archive vocabulary (R5).** `JournalMigrationProfileTests` in `tests/test_upgrade_wavefoundry.py` builds wave folders through `_JournalMigrationFixture._make_wave` (`:11335`), which writes the live record filename (`_record_name()`) and a hardcoded `# Wave Record` heading. Archive discovery reads `vocabulary_profile.archive_profile().RECORD_FILENAME`, and `setUp` patches `record_paths.ARCHIVE_ROOT` but never `vocabulary_profile.ARCHIVE_PROFILE`, so no test shows that an archived folder is recognised under an archive vocabulary that differs from the live one. A regression that read the live name for the archive would pass today.
- **A schema test missing its base declaration (R7).** `test_hot_reload_reapplies_exact_argument_schema_to_whole_registry` (`tests/test_server_tools_retrieval.py:14194`) builds the server without `apply_base_declaration(self)`, which its sibling `test_review_ergonomics_preserves_review_event_schema_and_tool_roster` (`:13950`) calls first. It passes at HEAD; the gap is that its registry depends on whatever declaration state a previous test left behind.
- **The offline vendored-script check runs only at pack time (Part 3(c)).** `verify_vendored_scripts.offline_problems` hashes `dashboard/vendor/` files against the pinned table with no network, but its only caller is `build_pack._check_vendored_scripts`. A modified vendored script in a working tree is invisible until packaging. `wf_audit` is the default first call of a session and is documented read-only and advisory, so it is the natural report-only surface.

Code-grounded constraint on that last item: `scripts/verify_vendored_scripts.py` is listed in `build_pack.EXCLUDED_REL_PATHS` (it holds the network check), so it is absent from every distribution while `dashboard/vendor/` (1.7 MB) ships. The requester is a distribution, so the offline half must move into a small shipped module that the excluded script imports, and `wf_audit` must use the shipped module so targets are checked too.

## Requirements

1. `change_doc_checklist.fenced_line_flags` runs in time linear in the number of lines for any input with a bounded number of distinct opener keys, and returns exactly what it returns today for every input. The implementation computes `split_blockquote` once per line, and records for each opener key `(blockquote depth, fence character, fence length)` the line index up to which a failed scan proved no closer exists; a later opener with the same key before that index is unterminated without rescanning. A failed scan that ended at a blockquote-depth drop records that drop index, not the document end, so an opener after the drop is scanned afresh.
2. State the complexity honestly in the docstring: openers with `k` distinct keys cost at most `O(k * n)`; blockquote depth is the only unbounded key component and real documents use a handful of values. No attempt is made to beat that bound.
3. One shared constant names the history-path components, and one helper answers "is this path under a history directory". The helper takes a path RELATIVE to the scan root (a `Path` or POSIX string) and tests only its components; it never receives or inspects an absolute path. Verified: `agent_surface_integrity.py:43`, `wave_validators.py:790/812/838` and `upgrade_extensions.py:2220/2445` iterate `agents_root.rglob("*.md")` from an absolute `root / "docs" / "agents"` and test `path.parts` of the absolute result, so a repository checked out under an ancestor directory named `journals`, `memory` or `snapshots` silently skips every file today (an existing defect this change fixes for all three, since the `memory` literal at those sites is replaced by the same relative test); every site passes `path.relative_to(root)` (or the repo-relative string it already has). Value: `("journals", "snapshots")`. It lives in a new stdlib-only module `history_paths.py` in `.wavefoundry/framework/scripts/` (not `record_paths.py`: see the Decision Log). All nine sites call it. Sites that also skip `memory`, `personas` or `reports` keep those extras locally and combine them with the shared helper; the shared constant does not absorb them.
4. Behavior change, stated: eight of the nine sites gain `snapshots` as a history component. Each site's tests pin both a relative-path case and the ancestor case (the repository root placed under a parent directory named `snapshots`, `journals` and `memory`, which must NOT skip any file); each also pins both a `journals/` path and a `snapshots/` path as skipped, and a non-history sibling as still handled. The `server_impl.py` ranking site keeps `reports` and its `feedback`/`journal` name tests unchanged. No record directory named `snapshots` exists in this repository (checked: `find . -type d -name snapshots` outside `.git`, the index and `node_modules` returns nothing), so self-hosted output is unchanged.
5. The constant is documented as a stable contract. The home is `docs/references/project-overview.md` (not the tool-surface spec, which describes tools), beside the record-layout paragraph that already names `record_paths`, plus one sentence in `docs/architecture/layering-rules.md` (leaf module, imported by validators, renderer, scanner, upgrade and server). The contract text states: the tuple's members, that adding a member is a behavior change requiring a changelog line, that the match is on a path component (never a substring), and that Hugging Face `snapshots` directories are unrelated and not covered.
6. `JournalMigrationProfileTests` gets an archive-aware record name: a `_make_wave` variant (or parameter) that takes the record filename and heading from `vocabulary_profile.archive_profile()` for folders under the archive root, and from the live profile otherwise. One new test sets `vocabulary_profile.ARCHIVE_PROFILE` to a mapping that differs from the live profile in the record filename (and, if the mapping validator requires it, in nothing else), builds an archived wave folder with that filename and an archived journal, and asserts the existing behavior: the journal is left in place with the "wave is archived (read-only archive root)" report line and the archive tree is byte-identical. A mutation that makes archive discovery read the live filename must fail this test.
7. `test_hot_reload_reapplies_exact_argument_schema_to_whole_registry` calls `apply_base_declaration(self)` (imported from `declaration_support` exactly as the sibling does) before `build_server`, and still passes both its negative control and its repaired-schema assertions.
8. Move the offline half into a new shipped, stdlib-only module `vendored_integrity.py` (not listed in `build_pack.EXCLUDED_REL_PATHS`; added, with `history_paths`, to `FRAMEWORK_SCRIPT_MODULE_NAMES` in `mcp_tool_extensions.py`, a census pinned by `test_extension_tool_modules.py` and `test_tree_kill_routing.py`, whose expected lists are updated in the same change): `ReadmeError`, `VendoredFile`, `RegistryEntry`, the table header and row patterns, `_table_rows`, `parse_readme`, and `offline_problems`, plus whatever else those need to stand alone. Wave B also adds a confined file reader and `MAX_VENDORED_FILE_BYTES` in `verify_vendored_scripts.py`, used by both `offline_problems` and the network `verify`; the reader and the constant move into `vendored_integrity` and `verify` imports them back. Import rule: standard library plus shipped leaf modules only (for example `path_containment`, if wave B's reader imports it), enforced by a test that lists the module's imports against that allowlist. `verify_vendored_scripts.py` keeps the network check and imports these names from the new module, re-exporting them so `build_pack` and the existing tests keep working unchanged. The move is a pure relocation: the implementer moves the code as it stands after wave B lands, so wave B's containment edits to `offline_problems` travel with it, and no behavior changes in this change. `build_pack._check_vendored_scripts` may keep importing through `verify_vendored_scripts` or switch to the new module.
9. `wf_audit_response` (not the `@mcp.tool` handler `wf_audit`, so the handler digest fixture is untouched) adds an additive `data.vendored_scripts` object. It imports `vendored_integrity` and calls `offline_problems(root / ".wavefoundry" / "framework" / "dashboard" / "vendor")` once per audit, where `root` is the audited target root (the one `wf_audit_response` receives), not the running server's `SCRIPTS_DIR` parent (they coincide only in self-hosting); a test audits a temporary root holding its own vendor folder while the server's scripts live elsewhere. The audit loads the module through `_load_script`, which registers it as `_wavefoundry_vendored_integrity`, and catches `ReadmeError` as the attribute of that same loaded module object (never a separately imported `vendored_integrity.ReadmeError`, which would be a different class), uncached (the hash of 1.7 MB costs milliseconds). Statuses: `ok` (no problems), `mismatch` (one string per problem, as returned), `unavailable` (the vendor folder is absent, or the module cannot be imported) and `unreadable` (the README cannot be parsed, from `ReadmeError`). Report-only: it never changes `data.ready`, never raises, adds an advisory diagnostic only for `mismatch` and `unreadable`, whose text names no script and no runnable command ("vendored dashboard scripts differ from their pinned hashes; reinstall or upgrade the framework"), and opens no network connection (the offline function reads files only; the tests patch the network entry points, see AC-10). It is documented in the `wf_audit` entry of `docs/specs/mcp-tool-surface.md`. The shipped `.wavefoundry/framework/dashboard/vendor/README.md` command text (lines 34 to 36 and 50) is reworded so it says the verifier command exists only in the Wavefoundry source repository and that an installed framework reports drift through `wf_audit`; the file table and hashes are untouched.
10. Dependency: wave B (`1zxns-bug change-id-and-path-containment`) adds path containment to `offline_problems` and must land first; this change relocates that post-B code and reimplements nothing. The relocation tests assert only the contract visible through the function (a listed file that matches, differs, or is missing), so they hold before and after wave B.
11. `gardener_metadata._fenced_line_flags` was measured in a scratch process on the same `["```python"] * n` shape: 1000, 2000 and 4000 lines take 0.07, 0.12 and 0.23 ms, linear (it is a single pass with one open-fence variable). It is out of scope and unchanged.

## Scope

**Problem statement:** five correctness and test-hygiene gaps that a downstream reviewer verified at HEAD: a quadratic scan, a duplicated exclusion with inconsistent members, an archive-vocabulary blind spot in a test fixture, a schema test missing its base setup, and an integrity check that runs only at pack time.

**In scope:**

- `change_doc_checklist.fenced_line_flags` and its tests (Requirements 1 and 2).
- New `history_paths.py`, its nine call sites, their tests, `FRAMEWORK_SCRIPT_MODULE_NAMES`, and the contract documentation (Requirements 3 to 5).
- `JournalMigrationProfileTests` fixture and one divergent-archive test (Requirement 6).
- One line in one schema test (Requirement 7).
- New shipped `vendored_integrity.py` (relocation of the offline check), `data.vendored_scripts` in `wf_audit_response`, spec text and tests (Requirements 8 to 10).
- A CHANGELOG Unreleased entry covering the `snapshots` behavior change and the new audit field.

**Out of scope:**

- The other fence-flag implementation `gardener_metadata._fenced_line_flags`: measured, linear, unchanged (Requirement 11).
- Writing path containment (wave B does; this change only moves the result).
- Shipping `verify_vendored_scripts.py` itself, or adding the check to setup or upgrade.
- The lock, change-id, extensibility and vocabulary-name changes (waves A, B, D, E).
- Any change to `model_bundle`, `accel_embedder`, `setup_index` or `upgrade_wavefoundry` `snapshots` handling (Hugging Face cache, unrelated).

## Acceptance Criteria

- [x] AC-1: Differential equality. A test embeds the pre-change algorithm verbatim as a reference function and asserts `fenced_line_flags(lines) == reference(lines)` for at least 300 seeded random inputs (fixed `random.Random` seed; lines drawn from backtick and tilde openers of lengths 3 to 5, closers, info-string openers, plain text, and `>`-prefixed forms at depths 0 to 3) plus hand-written cases: a closed fence, nested blockquote fences, a fence whose blockquote prefix drops before its closer, an opener after a depth drop that does close, an unterminated fence followed by a terminated one of a different length, mixed backtick and tilde, empty input, and a single line.
- [x] AC-2: Scaling, not wall time. A test times `fenced_line_flags(["```python"] * n)` (best of three, `time.perf_counter`, with `gc.disable()` around the timed region and `gc.enable()` restored in a `finally`) at `n = 2000` and `n = 8000` and asserts `t(8000) / t(2000) < 8` (linear predicts 4, quadratic predicts 16, so the bound sits at the geometric midpoint and tolerates scheduler noise); it also asserts the result is all `False`. A second shape, `["~~~x"] * n` inside a `> ` blockquote, is checked the same way. The test records its measured ratio in the failure message. A mutation that removes the failure cache must fail it.
- [x] AC-3: Single definition. After the change, `rg -n '"journals"|"snapshots"' .wavefoundry/framework/scripts --glob '!tests/**'` returns only: the definition in `history_paths.py`, the Hugging Face `snapshots` hits in `model_bundle.py`, `accel_embedder.py`, `setup_index.py` and `upgrade_wavefoundry.py`, and the unchanged `journals` fragments that are not exclusions (`upgrade_extensions._JOURNALS_REL` and its migration code). The implementer records the output in the Progress Log.
- [x] AC-4: Each of the nine sites, driven through its public behavior, treats a file under `journals/` and under `snapshots/` as history and a sibling outside both as live: the agent-role and category validators, the integrity role-doc scan, the review-role slug (`render_agent_surfaces._review_role_slug`), the two `upgrade_extensions` loops, `reconcile_scan` and the demotion classifier. The `memory`, `personas` and `reports` extras still behave as before at their sites. Every site is also driven with the repository root placed under a parent directory named `snapshots`, `journals` and `memory`, and none of its live files is skipped for that reason.
- [x] AC-5: `history_paths.py` imports nothing outside the standard library, is listed in `FRAMEWORK_SCRIPT_MODULE_NAMES` (the census tests that pin that list pass), and a test imports it in a fresh interpreter started with `-I` and only the scripts directory on `sys.path`. The two `upgrade_extensions` sites import `history_paths` inside the function, after the scripts directory is on `sys.path`, never at module top, and never through an already-loaded `record_paths`.
- [x] AC-6: `docs/references/project-overview.md` and `docs/architecture/layering-rules.md` state the contract in Requirement 5, and a test pins the tuple value against the documented text so the doc and the constant cannot drift.
- [x] AC-7: The new divergent-archive test passes; the same test fails when archive discovery is patched to read the live `RECORD_FILENAME`; and every existing `JournalMigrationProfileTests` case still passes with the archive-aware helper.
- [x] AC-8: `test_hot_reload_reapplies_exact_argument_schema_to_whole_registry` calls `apply_base_declaration(self)` first and passes when run alone (`--file` focused mode) and after the sibling test.
- [x] AC-9: `wf_audit_response` returns `data.vendored_scripts` with `status` `ok` for this repository's real vendor folder, `mismatch` (naming the file) after one vendored byte is changed in a temporary copy, `unavailable` when the vendor folder is absent and when `vendored_integrity` is not importable (import patched to raise `ImportError`), and `unreadable` for an unparsable README; `data.ready` is identical in all five cases; a `mismatch` adds one advisory diagnostic and `ok` adds none.
- [x] AC-9b: Relocation. `vendored_integrity.py` imports only the standard library and the allowlisted shipped leaf modules (a test checks the import list), is not in `build_pack.EXCLUDED_REL_PATHS`, is kept by `build_pack.should_exclude` (asserted as `should_exclude('scripts/vendored_integrity.py', 'vendored_integrity.py') is False`, with the same call returning True for `verify_vendored_scripts.py`), and is in `FRAMEWORK_SCRIPT_MODULE_NAMES`; the confined reader and `MAX_VENDORED_FILE_BYTES` are defined once, in `vendored_integrity`, and the network `verify` uses them; `verify_vendored_scripts` still exposes `parse_readme`, `offline_problems`, `ReadmeError` and the network `verify`, and its existing tests pass unchanged; `offline_problems` and the reader have one definition each (`rg 'def offline_problems'` returns one hit outside tests).
- [x] AC-10: No network. The AC-9 tests run with `urllib.request.urlopen`, `socket.create_connection` and `socket.socket.connect` all patched to raise, as `test_verify_vendored_scripts.py` does, and none of them is reached.
- [x] AC-11: The `register-surface-handler-digests.json` test passes with the fixture unchanged (no `@mcp.tool` handler source changed), and `docs/specs/mcp-tool-surface.md` lists `vendored_scripts` under `wf_audit` response data.
- [x] AC-12: Visible contract only. The AC-9 `ok` and `mismatch` tests, and the relocation tests, assert only what is visible through the function (a listed file that matches, differs, or is missing), so they hold on either side of wave B; nothing asserts wave B's containment or equality with its text.
- [x] AC-13: `wf_validate_docs` passes, the CHANGELOG Unreleased section carries one entry for this change (the `snapshots` behavior change and `data.vendored_scripts`), and `python3 .wavefoundry/framework/scripts/run_tests.py` is recorded green last.

## Tasks

- [x] Open `framework_edit_allowed`; close it immediately after the framework edits.
- [x] R8: precompute per-line blockquote splits and add the per-key failure cache in `fenced_line_flags`; update its docstring (Requirement 2); add the differential and scaling tests (AC-1, AC-2) to the existing `change_doc_checklist` test module.
- [x] R3: confirm the census (AC-3 command) at implementation time and record it; add `history_paths.py`; add the name to `FRAMEWORK_SCRIPT_MODULE_NAMES` in `mcp_tool_extensions.py`; switch the nine sites; add per-site tests (AC-4, AC-5).
- [x] R3 docs: contract text in `docs/references/project-overview.md` and `docs/architecture/layering-rules.md`, plus the pinning test (AC-6).
- [x] R5: archive-aware `_make_wave` in `_JournalMigrationFixture` and the divergent-archive test with its mutation check (AC-7).
- [x] R7: add `apply_base_declaration(self)` to the schema test (AC-8).
- [x] Part 3(c): move the offline half into `vendored_integrity.py` after wave B lands (re-export from `verify_vendored_scripts`, `FRAMEWORK_SCRIPT_MODULE_NAMES` entry, AC-9b); add the `vendored_scripts` block to `wf_audit_response` outside the `@mcp.tool` handler; tests for the five statuses and the no-network guard; spec text (AC-9 to AC-11).
- [x] Confirm wave B is closed or applied before the Part 3(c) tests run against the wave B `offline_problems`; record the order in the Progress Log (AC-12).
- [x] CHANGELOG Unreleased entry; refresh the docs index; run `wf_validate_docs`; run `run_tests.py` LAST.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws-1 fence scan | software-engineer | - | `change_doc_checklist.py` and its tests; independent of the others |
| ws-2 history constant | software-engineer | - | new module plus nine sites; touches `server_impl.py`, `upgrade_extensions.py`, `wave_validators.py` |
| ws-3 test hygiene | qa | - | R5 fixture and test, R7 one line; both in tests only |
| ws-4 vendored integrity move and audit finding | implementer | wave B landed; ws-2 for the shared edit window on `server_impl.py` | new `vendored_integrity.py`, `verify_vendored_scripts.py` re-export, `wf_audit_response` block, spec text |
| ws-5 docs, changelog, gate | implementer | ws-1 to ws-4 | contract docs, CHANGELOG, validate, tests last |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/change_doc_checklist.py`
- `.wavefoundry/framework/scripts/history_paths.py`
- `.wavefoundry/framework/scripts/vendored_integrity.py`
- `.wavefoundry/framework/scripts/verify_vendored_scripts.py`
- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/dashboard/vendor/README.md`
- `.wavefoundry/framework/scripts/mcp_tool_extensions.py`
- `.wavefoundry/framework/scripts/agent_surface_integrity.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/reconcile_scan.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/references/project-overview.md`
- `docs/architecture/layering-rules.md`
- `docs/specs/mcp-tool-surface.md`

Shared-file notes for the parallel waves (A lock integrity first, B path containment second, this change third, D extensibility, E vocabulary names):

- `wf_server/server_impl.py` is touched by A (reload and lock readers), B (change-id and bulk lookup), E (prompt names) and here (the `:16045` demotion site and the `wf_audit_response` block). Rebase on the prior wave's tree; the edits here are two small hunks far from the `@mcp.tool` handlers, so the handler digest fixture should not need this change's input. If a rebase or an edit ever touches an `@mcp.tool` handler body (including a `wf_audit` docstring), recompute only that handler's digest in `register-surface-handler-digests.json` and extend its description sentence naming this change.
- `scripts/verify_vendored_scripts.py` is edited by B (containment) and then edited here (the offline half is cut out and re-imported); this change starts from B's merged tree, never from the pre-B function.
- `scripts/mcp_tool_extensions.py` is edited by D (extension declarations); the two-name addition (`history_paths`, `vendored_integrity`) to `FRAMEWORK_SCRIPT_MODULE_NAMES` here merges mechanically but must be re-checked against D's edits.
- `scripts/upgrade_extensions.py` is edited by D (journal migration extension points) and A (lock cut-over); the two one-line replacements here (`:2220`, `:2445`) must be rebased onto them.
- `scripts/render_agent_surfaces.py` is edited by E; the one-line change at `:296` must be rebased onto it.
- `tests/test_upgrade_wavefoundry.py` is edited by D (journal migration) in the same `JournalMigrationProfileTests` region as R5; the fixed order is C before D, so this change's fixture edit lands first and D rebases onto it.
- Root-level files edited (not path tokens): `CHANGELOG.md`.

## Affected Architecture Docs

`docs/architecture/layering-rules.md`: one sentence recording `history_paths` as a stdlib-only leaf module imported by validators, renderer, scanner, upgrade and server. `docs/architecture/testing-architecture.md`: N/A (no new test layer; the scaling-ratio technique is local to one test module). `docs/ARCHITECTURE.md` and the other child docs: N/A, since there is no boundary or flow change beyond that leaf module.

## Platform Behavior

- The history match is on path components of a `pathlib` path, so it behaves identically for POSIX and Windows separators. It is case-sensitive, as every current site is; on case-insensitive volumes (macOS APFS default, Windows NTFS) a directory spelled `Journals` is therefore not history at any site, exactly as today, and this change does not widen it (the case-insensitive-rename concern is not involved because nothing is renamed).
- `history_paths.py` is stdlib-only so it imports under the bare interpreters used by docs-lint hosts on Windows, macOS, Linux and WSL2 (including `/mnt/c`).
- The fence scan operates on already-split in-memory lines and has no platform dependence; the scaling test uses `time.perf_counter` ratios, so a slow Windows or WSL2 runner shifts both measurements together.
- `wf_audit` reads `dashboard/vendor/` files as bytes with no line-ending translation, so the SHA-256 comparison is identical on all platforms; a Git checkout that converts line endings on Windows would show as `mismatch`, which is the correct report because the pinned hashes are over the exact bytes.
- The audit block uses no locks, so it carries no lock-semantics difference across platforms.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Output equality is the whole safety case for changing a parser. |
| AC-2 | required | The point of R8; a ratio bound survives slow runners. |
| AC-3 | required | The census proves the duplication is gone. |
| AC-4 | required | Behavior change at eight sites must be pinned per site. |
| AC-5 | required | A non-stdlib or unlisted module breaks docs-lint hosts and the extension guard. |
| AC-6 | important | Documentation drift guard for a stable contract. |
| AC-7 | required | The blind spot is the defect; the mutation check proves the test bites. |
| AC-8 | important | Hygiene, passes today, protects ordering independence. |
| AC-9 | required | Defines the audit finding's four outcomes and its non-blocking nature. |
| AC-9b | required | One shipped reader, kept in the distribution, is what makes the audit check work in targets. |
| AC-10 | required | The no-network principle is a framework tenet. |
| AC-11 | required | Handler digest test fails otherwise, and the spec must match the response. |
| AC-12 | required | The cross-wave ordering must hold in either landing order. |
| AC-13 | required | Close gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-06 | Planned. Verified at HEAD `06c02e63`: quadratic fence scan reproduced (4000 unclosed openers 2.2 s); nine journal and snapshot exclusion sites with four distinct predicates (the report's single predicate is not what the code has); R5 fixture writes the live record filename; R7 sibling has `apply_base_declaration`; `verify_vendored_scripts.py` is excluded from distributions while the vendor folder ships. | `rg` census in Rationale; timing run; `build_pack.EXCLUDED_REL_PATHS`. |
| 2026-10-06 | Readiness revision: history helper takes scan-root-relative paths (ancestor-directory bug at six sites verified); census names `FRAMEWORK_SCRIPT_MODULE_NAMES`; moved module carries wave B's reader and size constant; audit checks the target root's vendor folder. Ordering: B lands before this change, and this change lands before D. | Readiness findings F1 to F9. |
| 2026-10-06 | Ordering: wave B (`1zxns`) is applied in the working tree (uncommitted) and this change moved its post-B `verify_vendored_scripts` code (confined reader, `MAX_VENDORED_FILE_BYTES`, `_row_path_problem` with control characters, `VendoredFile.row`, `_row_label`) verbatim into `vendored_integrity.py`; this change lands before D. | `vendored_integrity.py`; `test_verify_vendored_scripts.py` 61 tests unchanged and green. |
| 2026-10-06 | R8 (AC-1, AC-2): `fenced_line_flags` splits each line once and caches failed scans per `(depth, char, length)` at the stop index (first depth drop or end). Differential test vs the verbatim old algorithm (400 seeded inputs plus hand cases) and ratio test pass; mutation removing the cache fails both ratio tests at 16.08 and 16.00. | `tests/test_change_doc_checklist.py` (54 tests). |
| 2026-10-06 | R3 (AC-3 to AC-6): new stdlib-only `history_paths.py` (`HISTORY_PATH_COMPONENTS`, `is_history_path`, which refuses an anchored path); all nine sites switched and test root-relative paths; `_expected_agent_category` now receives the root-relative path from its validator caller (the renderer already passed one); the two `upgrade_extensions` sites import inside the function after inserting the target's scripts directory. AC-3 output (non-test lines): `history_paths.py:24` definition; Hugging Face hits `upgrade_wavefoundry.py:3044`, `model_bundle.py:190/236/317`, `accel_embedder.py:444/445`, `setup_index.py:1956`; `upgrade_extensions.py:1296` (`_JOURNALS_REL`), `:1428` and `:1684` (journal-walk checkpoint stage name). `_tag_utils.py` substring is not matched. Site mutants (absolute-path predicate or dropped `snapshots`) at every site all fail `test_history_paths.py`. | `tests/test_history_paths.py` (23 tests); `test_upgrade_wavefoundry` delegated-producer module list gains `history_paths.py`. |
| 2026-10-06 | R5 (AC-7): archive-aware `_make_wave` and the divergent-archive test pass; patching `record_paths.discover_archive_dirs` to read the live `RECORD_FILENAME` fails it. R7 (AC-8): `apply_base_declaration(self)` added; `test_server_tools_retrieval.py` green. | `tests/test_upgrade_wavefoundry.py` (640 tests), `tests/test_server_tools_retrieval.py` (1044 tests). |
| 2026-10-06 | Part 3(c) (AC-9 to AC-12): `vendored_integrity.py` holds the offline half; `verify_vendored_scripts` re-exports it, and `MAX_VENDORED_FILE_BYTES` read or set through the verifier forwards to the one value in `vendored_integrity` (module-class forwarding) so its existing tests that patch the cap there pass unchanged. `build_pack._check_vendored_scripts` imports `vendored_integrity`. `wf_audit_response` adds `data.vendored_scripts` through `_audit_vendored_scripts(root)` (outside the handler; digest fixture unchanged); its diagnostics carry no `advisory=True` gate flag, like the other audit findings, so the sanctioned advisory-tag set is unchanged. Audit mutants (separately imported `ReadmeError`, ignored problems, server's own vendor folder, mismatch flipping `ready`) all fail. Vendor README reworded; spec documents the field. | `tests/test_vendored_integrity.py` (12 tests); `test_mcp_tool_registry.py`, `test_build_pack.py`, `test_server_tools_lifecycle.py` green. |
| 2026-10-06 | Full scratch suite run 1 found `history_paths` missing from the server reload eviction set (`test_lifecycle_gates_structure.py`, 7 failures); added it beside `change_doc_checklist` in `server_impl`, file green (15 tests). The `run_tests.py`-last receipt in the repository is the coordinator's step. | `tests/test_lifecycle_gates_structure.py`. |
| 2026-10-06 | Delivery repair DEL-1: `reconcile_scan.is_excluded` passes `PurePosixPath(rel)` to `is_history_path` (a POSIX path is anchored only by `/`), so a repository file named like `c:notes.md` no longer makes `scan_repo` raise. Caller audit: every other site passes a root-relative `Path` (agent-role and category validators, integrity scan, review-role slug, both upgrade loops), which is never anchored, and the demotion classifier catches `ValueError`. | `test_history_paths.ReconcileScanSiteTests.test_a_drive_shaped_root_file_name_does_not_break_the_scan` (skipped on Windows); mutation probe (revert to the string call) fails it with `ValueError`. |
| 2026-10-06 | Delivery repair DEL-2: `_doc_demotion_weight` applies the history test to non-code result kinds only; code under `snapshots/` (and `journals/`) is not demoted, a document there is. CHANGELOG 1zxnt bullet updated. | `DemotionSiteTests.test_history_applies_to_document_results_only`; mutation probe (drop the kind gate) fails it. |
| 2026-10-06 | Delivery repair DEL-3: removed the `_SharedCapModule` module-class swap from `verify_vendored_scripts` (and the unused `types` import); the cap lives only in `vendored_integrity`, which the network `verify` reads at call time through `read_vendored_file`. Test cap patches retargeted to `vendored_integrity`; the class-swap pin in `test_vendored_integrity` removed; a new test proves `verify` honors the patched `vendored_integrity` cap. | `test_verify_vendored_scripts.py` 62 OK, `test_vendored_integrity.py` 12 OK. |
| 2026-10-06 | Delivery repair DEL-4: `vendored_integrity._table_rows` and `parse_readme` messages name a line or row number and the cause only (no row text, package name or path), so the audit `unreadable` reason, `build_pack` and the CLI carry no raw README text. The pre-existing `MalformedRowTests` now assert the row is not echoed. | Audit test asserts reason `line 5: malformed file table row` with no row fragment or control character; mutation probe (re-append the row) fails 1 audit test and 4 verifier tests. |
| 2026-10-06 | Delivery repair DEL-5 plus optional: `fenced_line_flags` docstring states depth and fence length are both unbounded key components, `O(k * n)` probes with `k = O(sqrt(B))`, `O(B^1.5)` worst case (measured 5.2 s at 8 MB of decreasing-length unclosed fences). The audit test asserts the no-script/no-path check on `vendored_scripts_unreadable`. Both `vendored_scripts_*` messages end with "(advisory; does not affect readiness)" without the advisory flag. | `test_change_doc_checklist.py` 54 OK; `test_vendored_integrity.py` 12 OK. |
| 2026-10-06 | Delivery repair round verification: full scratch suite after DEL-1 to DEL-5. | `run_tests.py --no-cache` in scratch: 11,499 tests across 165 files OK; `wf_validate_docs` passed (one advisory on AC-13 wording, unchanged). |
| 2026-10-07 | Gapfill: implementation and repairs ran in subagents whose sessions did not load the MCP code tools, so censuses and code reads used shell `rg`/`grep`/`sed`; every census was rerun and verified by the independent delivery reviewers. | Implementer and reviewer reports for 1zxnt; AC-3 census output. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-06 | The shared constant lives in a new stdlib-only `history_paths.py`, not `record_paths.py`. | During an upgrade the running process may hold an old `record_paths` in `sys.modules` (the memory bootstrap comment at `upgrade_extensions.py` records exactly this, a 1.27 `RecordRoots` without `archive`), so a new attribute on `record_paths` could raise `AttributeError` at the two `upgrade_extensions` sites; a new module imports fresh. `agent_surface_integrity` also does not import `record_paths` today. | `record_paths.HISTORY_PATH_COMPONENTS` as the report suggested: simpler placement, old-code-window hazard and a wider import for a leaf script. |
| 2026-10-06 | One constant `("journals", "snapshots")` applied to all nine sites; per-site extras (`memory`, `personas`, `reports`) stay local. | A single history definition is the goal; the extras are different decisions (role-doc exemptions, ranking). | Keep a second constant for the journals-only sites: preserves today's exact behavior but leaves two definitions of history. |
| 2026-10-06 | Cache the failure index per key `(depth, char, length)`, not a bare "no closer after here" flag. | A depth drop ends the scan window, so an unclosed opener at depth 2 proves nothing about an opener after the quote ended; keying by depth and recording the drop index keeps results identical. | Single global failure flag: breaks the "fence opened in a blockquote is unterminated when its prefix drops" rule. A parse rewrite: higher risk to exact output. |
| 2026-10-06 | Coordinator: move `parse_readme` and `offline_problems` into a shipped `vendored_integrity.py`; the network check stays in the excluded script, which imports the shipped module. `wf_audit` uses the shipped module, uncached. | The requester is a distribution; `unavailable` everywhere would defeat the finding. Hashing 1.7 MB costs milliseconds. | Degrade to `unavailable` in targets; pack-time only (status quo); cache by size and mtime. |
| 2026-10-06 | Coordinator: adding `snapshots` to all nine sites is accepted as one uniform history contract; `gardener_metadata._fenced_line_flags` measured linear and left alone. | Uniform contract; measurement shows no quadratic pattern. | Two constants; include the gardener function. |
| 2026-10-06 | The audit block is added in `wf_audit_response`, not the `@mcp.tool` `wf_audit` handler. | Keeps the handler digest fixture unchanged. | Edit the tool docstring: forces a digest update. |
| 2026-10-06 | The `server_impl.py` demotion site adopts the shared constant for `journals` and `snapshots` but keeps `reports` and the name tests. | It is a ranking heuristic with different members; only the shared members should be shared. | Leave it alone: keeps a tenth, undocumented definition of history. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The failure cache changes output for nested or mixed fences. | AC-1 differential test against the verbatim old algorithm over seeded random and hand-written inputs, including the depth-drop cases; the Decision Log keys the cache by depth. |
| A ratio-based timing test flakes on a loaded runner. | Best of three, bound at the geometric midpoint (8 between 4 and 16), sizes 2000 and 8000 so each run is short; failure message prints the ratio. |
| Eight sites silently start skipping `snapshots` directories in a target that keeps live docs there. | The behavior change is stated in Requirement 4, pinned per site (AC-4), documented as a stable contract, and has a changelog line; this repository has no such directory. |
| New module breaks an upgrade running old code, or the census tests. | `history_paths.py` is imported fresh inside the function, stdlib-only, listed in `FRAMEWORK_SCRIPT_MODULE_NAMES` with its pinned census tests updated (AC-5). |
| Merge conflicts with waves A, B, D and E in `server_impl.py`, `upgrade_extensions.py`, `render_agent_surfaces.py`, `mcp_tool_extensions.py` and the upgrade tests. | Serialization Points name each shared file and the hunk here; edits are one-line replacements or a small block; land after A and B, before D (C before D in the test file), and rebase on E. |
| Wave B changes `offline_problems` (confined reader, size cap) and this change moves it; a bad rebase could fork two copies. | B lands first and the implementer moves B's merged code; AC-9b requires one definition of each; AC-12 asserts only the visible contract. Ordering (B before C) is recorded in the Progress Log. |
| The audit field is read as proof the shipped scripts are intact when the module is absent. | `unavailable` is a distinct status with a stated reason, never `ok`; it now arises only when the vendor folder is absent or the module cannot import. |
| The relocation breaks `build_pack` or existing verifier tests, or diverges from wave B's containment. | Re-export from `verify_vendored_scripts`, AC-9b, and moving B's merged code verbatim (AC-12). |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
