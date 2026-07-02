# docs-lint file-size guard: skip content validators on an oversized doc (loud, non-blocking)

Change ID: `1p9cj-enh docs-lint-max-file-size-guard`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-01
Wave: `1p9bm install-experience-hardening`

## Rationale

Secrets scanning and indexing both cap file size after field testing — `secrets` skips files >
`MAX_FILE_BYTES` (5 MB), indexing skips files > `MAX_INDEX_FILE_BYTES` (5 MB) and does not tree-sitter-
parse files > `MAX_TREESITTER_PARSE_BYTES` (2 MB), all configurable and skip-with-record. **docs-lint has
no such guard.** Its content validators run regex/section passes over the *whole* file
(`link_validators` `_strip_code` + `_LINK_RE.finditer` DOTALL; `_extract_sections`; `splitlines`), and the
`1p9c6` read-cache now holds the whole file in memory. `1p9cf` fixed the link-*count* blowup, but a
pathological multi-MB generated markdown doc (an auto-generated API reference, a giant changelog, a data
dump committed as `.md`) is a *different* axis — file *size* — that hits the regex/memory path regardless.
This adds the same class of guard docs-lint was missing, consistent with secrets/indexing.

Because docs-lint is a **correctness gate** (unlike secrets/indexing, where skipping is lossless), an
oversized doc is skipped **loudly** — a non-blocking WARNING naming the doc, its size, the cap, and the
remedy — never a silent skip that would hide an unvalidated doc.

## Requirements

1. A configurable cap `docs_lint.max_file_bytes` in `docs/workflow-config.json`, default
   `5 * 1024 * 1024` (5 MB — matching the secrets/indexing file cap). A malformed/missing value falls back
   to the default (fail-safe), mirroring `docs_lint.hook_timeout_seconds`.
2. When a `docs/**` markdown file exceeds the cap, docs-lint **skips its content validators**
   (metadata, links, and the structural journal/persona/wave/plan/agent checks) for that file and emits a
   single non-blocking **WARNING**: the path, actual size, the cap, and the remedy (split it, move it under
   `docs/reports/`, or raise `docs_lint.max_file_bytes`). It is a WARNING, not an ERROR — it must not block
   the gate (a legitimately large generated doc should not fail close), consistent with secrets/indexing
   skip-with-record.
3. The size check is a single `stat` per doc (no read) computed once per run; an oversized doc is never
   read into the `read_text` cache by the skipped validators (memory protection).
4. Cross-platform (Windows/macOS/Linux/WSL2): `st_size` + a configurable byte cap — no platform-specific
   logic; the WARNING path is forward-slash (`relative_to_root` → `.as_posix()`, per `1p9cf`).
5. No false trips on normal repos: this repo's largest doc is 77 KB, so 5 MB is ~65× headroom — a full
   run emits zero size warnings. Existing docs-lint tests pass untouched.
6. `run_tests.py` + `wave_validate` pass.

## Scope

**Problem statement:** docs-lint has no file-size guard, so a pathological multi-MB markdown doc hits the
regex/section passes + the read-cache memory unbounded — the size axis secrets/indexing already guard.

**In scope:**

- `wave_lint_lib/constants.py`: `DOCS_LINT_MAX_FILE_BYTES_DEFAULT = 5 * 1024 * 1024`.
- `wave_lint_lib/cli.py`: read `docs_lint.max_file_bytes` (fail-safe); compute the oversized set once
  (one `stat` pass over `iter_markdown_docs`); emit a WARNING per oversized doc; skip oversized docs in the
  metadata/links loops and pass them as a `skip=` exclusion to the structural validators. Applies in BOTH
  full and incremental modes. *(framework_edit_allowed)*
- `wave_lint_lib/wave_validators.py`: add a `skip: set[Path] | None = None` exclude-filter to the six
  per-file validators (symmetric with the `1p9c1` `only=` include-filter; behavior-preserving when None).
  *(framework_edit_allowed)*
- Tests: an oversized doc → WARNING + skipped (not ERROR, not read); a normal doc unaffected; config
  override respected; full-lint output unchanged when nothing is oversized.

**Out of scope:**

- Chunked/streaming validation of a huge doc (skip-with-warning is the contract, matching secrets/indexing).
- The secrets/indexing caps themselves (already shipped).

## Acceptance Criteria

- [x] AC-1: a `docs/**` markdown file larger than the cap produces exactly one non-blocking WARNING (path +
      size + cap + remedy) and its content validators are skipped — docs-lint still exits 0. Evidence:
      `test_oversized_doc_warns_and_is_skipped_not_failed` (an >cap doc with no metadata → size WARNING, no
      metadata ERROR, exit 0) + `test_under_cap_doc_is_still_validated` (same broken doc under the cap DOES
      fail — proving only oversized docs are skipped). Live probe: 1 KB cap → 927 WARNINGs, 0 failures.
- [x] AC-2: the oversized doc is not read by the skipped validators (memory protection). Evidence: the
      guard is a single `stat` (no read) and the metadata/links loops + structural validators `continue`
      past oversized paths before any `read_text`; `test_oversized_doc_warns_and_is_skipped_not_failed`
      confirms no per-file error is produced for the skipped doc (it was never validated/read).
- [x] AC-3: `docs_lint.max_file_bytes` override is honored; a malformed/missing value falls back to 5 MB.
      Evidence: `test_cap_reader_override_and_fail_safe` (override read; `"nope"`/`True`/`0`/`-5` → default).
- [x] AC-4: no false trips — with no oversized docs, output is unchanged; the existing docs-lint tests pass
      untouched (475 module tests). Evidence: `test_default_cap_produces_no_size_warnings` + module green.
- [x] AC-5: `run_tests.py` + `wave_validate` pass. Evidence: `wave_validate` clean; full `run_tests.py` at
      the wave's final run.

## Tasks

- [x] `constants.py`: `DOCS_LINT_MAX_FILE_BYTES_DEFAULT = 5 * 1024 * 1024`.
- [x] `cli.py`: `_docs_lint_max_file_bytes` reader (fail-safe); `_oversized_docs` one-stat pass; WARNING per
      oversized doc; skip in metadata/links loops; `skip=` to the structural validators; applied in full +
      incremental modes.
- [x] `wave_validators.py`: `skip=` exclude-filter on the six per-file validators (behavior-preserving when
      None), symmetric with the `1p9c1` `only=`.
- [x] Tests: `DocsLintFileSizeGuardTests` (oversized→WARNING+skip+exit0; under-cap still validated; config
      override + fail-safe; no-false-trip).
- [x] `run_tests.py` (final run) + `wave_validate` (clean).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Single lane in `wave_lint_lib` (`constants`/`cli`/`wave_validators`); the `skip=` filter mirrors the shipped `only=` pattern; gated by the existing docs-lint suite + new size-guard tests. |

## Serialization Points

- The `skip=` filter on the per-file validators must be behavior-preserving when `None` (existing suite is
  the regression gate); the cli owns the single stat pass + warning emission.

## Affected Architecture Docs

`N/A` — a defensive size guard + one config key; no boundary/flow/contract change. Consistent with the
existing secrets/indexing file-size caps.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The guard — oversized docs skip content validators with a loud non-blocking warning. |
| AC-2 | required | Memory protection — the oversized file is not pulled into the read-cache by skipped checks. |
| AC-3 | important | Configurable + fail-safe, consistent with the other docs-lint/indexing caps. |
| AC-4 | required | No false trips / no regression to the authoritative full lint. |
| AC-5 | required | Suite + docs gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-01 | Planned per operator: docs-lint lacked the file-size guard that secrets (`MAX_FILE_BYTES` 5 MB) and indexing (5 MB file / 2 MB tree-sitter) already have. `1p9cf` fixed the link-*count* axis; this covers the file-*size* axis (regex/section passes + `1p9c6` read-cache memory). Default 5 MB (matches the secrets/indexing file cap), configurable, skip-with-loud-WARNING (docs-lint is a correctness gate → never silent). Folded into `1p9bm` (7th change). | secrets `MAX_FILE_BYTES`; indexer `MAX_INDEX_FILE_BYTES`/`MAX_TREESITTER_PARSE_BYTES`; operator directive. |
| 2026-07-01 | Implemented under `framework_edit_allowed`: `DOCS_LINT_MAX_FILE_BYTES_DEFAULT` (5 MB) + `_docs_lint_max_file_bytes`/`_oversized_docs` in the cli + a `skip=` exclude-filter on the six per-file validators (symmetric with `1p9c1`'s `only=`), applied in full + incremental modes. Oversized → one `stat`, loud non-blocking WARNING, content validators skipped (never read). Live probe: 1 KB cap → 927 WARNINGs / 0 failures / exit 0. Tests: `DocsLintFileSizeGuardTests` + docs-lint module green (475). | `cli.py`/`wave_validators.py`/`constants.py` diffs; `DocsLintFileSizeGuardTests`. |
| 2026-07-01 | Pre-close multi-agent review noted the incremental-mode arm of the guard was untested (shipped-correct; the reviewer proved a dropped guard would be silent). Fixed: added `test_incremental_mode_skips_oversized_changed_doc` (oversized changed doc through `_run_incremental_checks` → size WARNING, no per-file ERROR). Test-only. | pre-close review checkpoint; `DocsLintFileSizeGuardTests`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-01 | Skip an oversized doc's content validators with a loud non-blocking WARNING (not an ERROR, not a silent skip). | docs-lint is a correctness gate: a silent skip hides an unvalidated doc; an ERROR would fail-close a legitimately large generated doc. A loud WARNING matches secrets/indexing skip-with-record and keeps the operator informed. | Silent skip (rejected — hides a validation hole); hard ERROR (rejected — blocks legit large docs). |
| 2026-07-01 | Default 5 MB, configurable via `docs_lint.max_file_bytes`. | Matches the secrets/indexing FILE cap exactly (the 2 MB is indexing's tree-sitter PARSE cap); ~65× this repo's largest real doc so zero false trips; configurable like the other caps. | 2 MB (rejected by operator in favor of matching the file cap). |
| 2026-07-01 | Implement via a `skip=` exclude-filter on the per-file validators, symmetric with the `1p9c1` `only=` include-filter, driven by a single cli stat pass. | Reuses the established scoping pattern with minimal churn; the cli owns config-read + warning emission in one place; behavior-preserving when no doc is oversized. | Enforce inside `read_text` (rejected — it can't skip validation or emit warnings); refactor structural validators to accept a file list (rejected — larger blast radius). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Skipping an oversized doc hides real structural/link errors in it. | It is a LOUD non-blocking WARNING naming the doc + remedy (split / move to reports / raise cap); the operator sees the doc was not fully linted — unlike a silent skip. |
| The `skip=` filter subtly changes full-lint behavior when nothing is oversized. | Behavior-preserving when `skip` is None/empty; the existing docs-lint suite runs untouched as the regression gate. |
| An operator sets the cap too low and legit docs get skipped. | Default 5 MB (65× the largest real doc here); the WARNING names the cap and how to raise it; never blocks the gate. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
