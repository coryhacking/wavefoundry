# docs-lint link check: per-link `Path.resolve()` realpath syscalls blow up on large/link-dense docs

Change ID: `1p9cf-bug docs-lint-link-check-resolve-syscall-blowup`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-01
Wave: `1p9bm install-experience-hardening`

## Rationale

A field user reported the post-edit docs-lint timing out at **>30s** on their system, while the same lint
runs in **<2s** here. Root-caused with the `1p9c6` `--timings` instrument + a targeted probe:
`check_markdown_links` calls **`Path.resolve()` for every unique link** in a doc
(`link_validators.py:79`). `Path.resolve()` is realpath — it stats *every path component* and follows
symlinks — so link checking is **O(link count) × per-syscall filesystem latency**. It is invisible on
this repo (small, link-light docs on fast APFS, ~36 µs/link) but explodes on a **link-dense doc**
(a generated API reference, a large changelog, a vendored doc with thousands of links) on a **slow
filesystem** (Windows / WSL2 / network mount) where each `resolve()` runs ~100× slower: 8,000 links ×
~2–5 ms ≈ 16–40 s — matching the field timeout.

We already added a 2 MB file-size guard to **secrets scanning** and **indexing** after field testing, but
the docs-lint validators never got any protection — and the link validator uses the most syscall-heavy
primitive available. `1p9bf` only band-aided the symptom (an advisory hook timeout) and `1p9c1` reduced
post-edit exposure (incremental), but the **full gate** (prepare / close / install / upgrade) still
processes every doc, so the blowup persists there. This fixes the cost at its source.

Measured (this repo / macOS APFS): replacing the per-link `Path.resolve()` + `.relative_to(root)` +
`.exists()` with `os.path.normpath` (string-level containment, no realpath) + a single `os.path.lexists`
is **~67× faster** (297.7 ms → 4.5 ms for 8,000 links) with identical results; the gap is larger on the
slow filesystems where the field timeout occurred.

## Requirements

0. **Cross-platform `rel` paths (Windows/WSL2 correctness).** `relative_to_root` returns a POSIX-style
   (forward-slash) path on ALL platforms (`.as_posix()`), not `str(WindowsPath)` (backslashes). Backslash
   `rel` silently broke every `rel.startswith("docs/…/")` forward-slash comparison on Windows — including
   the `docs/reports/` and `docs/waves/00000 ` **link-check skips**, so those large historical/report docs
   were being link-checked on Windows (compounding this very timeout) — and printed `\` paths in lint
   messages against the standing keep-`/` operator directive. This is a no-op on POSIX and the fix on
   Windows; it must support macOS, Linux, Windows, and WSL2.
1. `check_markdown_links` no longer calls `Path.resolve()` per link. Containment (does the target stay
   within the repo root?) is decided by **string normalization** (`os.path.normpath` on the joined path,
   compared to the normalized root) — no realpath / per-component stat. Existence is a **single**
   `os.path.lexists` (or `os.path.exists`) stat per unique link.
2. Behavior is preserved: the same relative links are flagged broken, URLs/`mailto:`/anchors/empty/
   trailing-slash/`docs/reports/`+`00000` skips are unchanged, fragments are still stripped, percent-
   encoding is still decoded, root-escaping links are still skipped (not flagged), and dedup within a file
   is unchanged. Existing docs-lint link tests pass untouched.
3. A symlink that pointed outside the root previously would have been caught by `resolve()`'s realpath;
   with normpath the escape check is lexical. This is acceptable and even safer for lint purposes (we do
   not want realpath to follow a symlink out of the repo and then stat an arbitrary external path); the
   containment check operates on the *declared* link path. Document this as an intentional semantics note.
4. Optional backstop (nice-to-have): if a single doc contains an extreme number of links (e.g. > a large
   threshold), emit one **loud advisory** and still check them — never silently skip (docs-lint is a
   correctness gate). Only add if it does not complicate the core fix.
5. `run_tests.py` + `wave_validate` pass; a test demonstrates the link check is linear and syscall-light
   (no `Path.resolve()` call in the hot loop) and that correctness (broken vs resolvable, root-escape) is
   preserved.

## Scope

**Problem statement:** `check_markdown_links` uses `Path.resolve()` per link → O(links) realpath syscalls
→ >30s on link-dense docs on slow filesystems.

**In scope:**

- `wave_lint_lib/link_validators.py`: replace the per-link `Path.resolve()` + `.relative_to()` +
  `.exists()` with `os.path.abspath` containment (via `os.sep`) + a single `os.path.lexists`.
  *(framework_edit_allowed)*
- `wave_lint_lib/helpers.py`: `relative_to_root` returns `.as_posix()` (forward slashes on all platforms)
  — the centralized cross-platform fix for every `rel`-vs-forward-slash comparison + lint message.
  *(framework_edit_allowed)*
- Tests: behavior-preserving (broken/resolvable/root-escape/`..`-within-root/skip-schemes/fragments/
  percent-encoding/dedup) + a guard asserting the hot loop does not call `Path.resolve()`; a
  `PureWindowsPath`-based test proving `rel` normalizes to forward slashes (Windows-simulated on any host).

**Out of scope:**

- A byte-size gate on docs-lint (rejected — it would miss small-but-link-dense docs and silently skip
  validating a doc, a correctness hole; the `resolve()` fix addresses the real cost axis, link count ×
  syscall latency).
- The secrets/indexing 2 MB gate (already shipped; different scanners over arbitrary/binary files).
- Parallelizing docs-lint (separate, measured follow-up per `1p9c6`).

## Acceptance Criteria

- [x] AC-0: `relative_to_root` returns forward-slash `rel` on all platforms (`.as_posix()`), so the
      `rel.startswith("docs/…/")` skip-comparisons fire on Windows/WSL2 and lint messages use `/`. Evidence:
      `RelativeToRootCrossPlatformTests` — POSIX nested-path case + a `PureWindowsPath` case proving a
      Windows path normalizes to `docs/reports/…` (with a regression guard that the old `str()` backslashes
      broke the skip). No-op on POSIX (existing tests untouched).
- [x] AC-1: `check_markdown_links` contains no `Path.resolve()` call in the per-link loop; containment is
      `os.path.abspath`+`os.sep`-based and existence is a single `os.path.lexists`. Evidence:
      `test_link_check_does_not_call_path_resolve` (patches `Path.resolve` to fail if called; 0 calls over a
      100-link doc) + source.
- [x] AC-2: behavior is preserved — broken flagged, resolvable not, root-escape skipped, `..`-within-root
      resolves, and URLs/anchors/`mailto:`/empty/trailing-slash/`docs/reports/` skips + fragment-strip +
      percent-decode + per-file dedup all behave as before. Evidence: 15 link tests (incl.
      `test_root_escaping_link_is_skipped_not_flagged`, `test_dotdot_within_root_still_resolves`) pass.
- [x] AC-3: the link check is syscall-light and linear — one stat per unique link, no realpath. Evidence:
      the `Path.resolve`-not-called guard + the recorded ~67× local speedup (297.7 → 4.5 ms / 8,000 links).
- [x] AC-4: `run_tests.py` + `wave_validate` pass. Evidence: docs-lint module green; full suite at the
      wave's final run; `wave_validate` clean.

## Tasks

- [x] `helpers.py`: `relative_to_root` → `.as_posix()` (forward slashes on all platforms).
- [x] `link_validators.py`: swapped the per-link `Path.resolve()` + `.relative_to(root_resolved)` +
      `.exists()` for `os.path.abspath` containment vs the abspath'd root (`os.sep` boundary guard) + a
      single `os.path.lexists`; kept all skip/strip/decode/dedup logic identical; added the
      intentional-lexical-containment note.
- [x] Tests: behavior-preserving cases + a `Path.resolve` not-called guard + `..`-within-root +
      root-escape + the `RelativeToRootCrossPlatformTests` (POSIX + PureWindowsPath).
- [x] `run_tests.py` (final run) + `wave_validate` (clean).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Single, tightly-scoped edit in `link_validators.py` + tests; gated by the existing docs-lint link tests and the new behavior/no-resolve tests. |

## Serialization Points

- `check_markdown_links` is called by the full lint's link loop and the incremental per-file dispatch —
  the containment semantics must stay behavior-preserving (existing link tests are the gate).

## Affected Architecture Docs

`N/A` — a localized performance/robustness fix in one validator; no boundary/flow/contract change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The fix — remove the per-link realpath syscalls that cause the field timeout. |
| AC-2 | required | Behavior preservation — link checking must still be correct. |
| AC-3 | required | Prove the syscall-light, linear behavior that fixes the blowup. |
| AC-4 | required | Suite + docs gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-01 | Root-caused the field >30s docs-lint timeout to `check_markdown_links`' per-link `Path.resolve()` (O(links) realpath syscalls); invisible here (small/link-light docs, fast APFS ~36 µs/link) but ~100× slower per syscall on Windows/WSL2/network → tens of seconds on a link-dense doc. Probe: `abspath+lexists` is ~67× faster (297.7 ms → 4.5 ms for 8,000 links), same results. Folded into the open `1p9bm` wave (6th change) per operator. | `1p9c6` `--timings`; link-count timing probe; `link_validators.py:79`. |
| 2026-07-01 | Implemented under `framework_edit_allowed`. On the operator's "support Windows/macOS/Linux/WSL2" directive, a cross-platform audit of the wave's docs-lint changes found a SECOND Windows bug: `relative_to_root` returned `str(WindowsPath)` = backslashes, so every `rel.startswith("docs/…/")` comparison (incl. the `docs/reports/` + `docs/waves/00000 ` link-check skips) silently failed on Windows — letting large historical/report docs get link-checked, compounding this very timeout, and printing `\` paths against the keep-`/` directive. Fixed centrally: `relative_to_root` → `.as_posix()` (no-op on POSIX). Link fix uses `os.path.abspath`/`os.sep`/`os.path.lexists` (portable; `os.sep` boundary guard avoids the sibling-prefix false positive). Tests: 15 link + `RelativeToRootCrossPlatformTests` (POSIX + `PureWindowsPath`) green; `Path.resolve` proven uncalled. | `helpers.relative_to_root`; `link_validators.py`; `RelativeToRootCrossPlatformTests`. |
| 2026-07-01 | Pre-close multi-agent review flagged `test_windows_path_normalizes_to_forward_slashes` as a **vacuous** regression guard — it hand-rolled `PureWindowsPath(...).as_posix()` and never called `relative_to_root`, so a `str()` revert of the fix went undetected (reviewer reproduced). Fixed: the test now drives the REAL `relative_to_root` with `PureWindowsPath` inputs; verified it passes on correct code and FAILS on a `str()` revert. Test-only, no production change. | pre-close review checkpoint; `RelativeToRootCrossPlatformTests`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-01 | Fix the cost at its source — drop per-link `Path.resolve()` for `os.path.normpath` containment + one `lexists` — rather than gate by file size. | The cost axis is link count × per-syscall latency, not bytes; a size gate would miss small-but-link-dense docs and, being a correctness gate, would silently skip validating a doc. The resolve() removal fixes the real cost with no correctness loss (~67× locally, more on slow FS). | Byte-size skip gate like secrets/indexing (rejected — wrong axis + validation hole); advisory-timeout only (already `1p9bf`, a band-aid); parallelize link checking (heavier, and unnecessary once the per-link syscalls are gone). |
| 2026-07-01 | Lexical (normpath) root-containment instead of realpath. | We check the *declared* link path stays in-repo; we do not want realpath to follow a symlink out of the repo and stat an arbitrary external path. Lexical containment is both faster and safer for a linter. | Keep realpath containment (rejected — the syscall cost is the bug; realpath's symlink-following is not a property lint needs). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Dropping `resolve()` changes which links are considered broken/escaping (e.g. symlinked paths). | Behavior-preserving tests over broken/resolvable/root-escape/skip cases; the containment is on the declared path (documented intentional semantics); `lexists` still detects a present target (including a symlink) so a valid link is not falsely flagged. |
| A `..`-heavy relative link normalizes above the root. | `os.path.normpath` collapses `..`; the containment check rejects anything not under the normalized root exactly as the `relative_to` guard did — covered by a root-escape test. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
