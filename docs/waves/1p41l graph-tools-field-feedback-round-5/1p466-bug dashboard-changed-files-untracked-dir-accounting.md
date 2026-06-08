# Dashboard Miscounts Changed Files And Added Lines For Untracked Directories

Change ID: `1p466-bug dashboard-changed-files-untracked-dir-accounting`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-08
Wave: 1p41l graph-tools-field-feedback-round-5

## Rationale

The dashboard's git "Files" tile and its "Changed files" dialog disagree, and the tile's added-line total over-counts — both from the same cause: **inconsistent handling of fully-untracked directories.**

`git status --porcelain` (default `-unormal`) **collapses** a directory that is entirely untracked into a single `?? dir/` entry rather than listing the files inside it. The three dashboard git readouts each treat that differently:

1. **Tile file count** — `dashboard_lib.py:1254-1255`: `files_changed = len(git status --porcelain lines)`. Counts each collapsed `?? dir/` as **1 file**.
2. **Tile added-line total** — `dashboard_lib.py:1266-1278`: adds untracked lines via `git ls-files --others --exclude-standard`, which **expands** untracked directories into their individual files — so the tile's `+` total **includes** every line of every file inside those untracked dirs.
3. **Changed-files dialog** — `list_git_changed_files` (`:847`, rendered by `FilesDialog`): iterates `git status --porcelain` and **skips trailing-slash directory entries** (`:852` `if rel.endswith("/"): continue`) — so the files inside untracked dirs are **omitted entirely** from the list (and from its per-file line counts).

Measured on the current working tree (2026-06-08): tile **64 files**, dialog **58 files**; the 6-file gap is six fully-untracked **wave directories** (`docs/waves/1p3rm…`, `1p3rq…`, `1p41l…`, `1p44n…`, `1p458…`, `1p45n…`) containing **41 files / 4,956 added lines**. The tile counts those 4,956 lines (via `ls-files`) but the dialog lists none of those 41 files. Removed-line totals are unaffected (untracked files are pure additions; both `-` figures come from the tracked `git diff HEAD`).

Note the internal inconsistency too: within the tile, the **file count** (porcelain, collapsed) and the **line count** (`ls-files`, expanded) already use different untracked enumerations. The fix unifies on individual-file enumeration everywhere.

## Requirements

1. The dashboard must enumerate untracked content as **individual files**, not collapsed directories, wherever it counts or lists changed files — so a fully-untracked directory of N files contributes N files (and their lines), not one collapsed entry (file count) or zero (dialog).
2. The "Files" tile count, the "Changed files" dialog list length, and the underlying changed-file set must agree: tile count == number of rows the dialog would render == (tracked changed files + individual untracked files).
3. The tile's added-line total must equal the sum of the dialog's per-file added lines (both accounting for files inside untracked directories). Removed-line totals must remain unchanged (tracked-diff-only) and consistent.
4. The fix must not regress the existing handling of tracked modified/added/deleted files, renames, binary-file line skipping, or the `since`-date filtering path of `list_git_changed_files`.
5. Files inside untracked directories must render correctly **regardless of filename** — non-ASCII and spaced paths must resolve on disk (so the dialog row's diff is populated, not empty) and their added lines counted. (Achieved via NUL-delimited `-z` parsing; bare `-uall` line-parsing would surface these files with un-decoded octal-escaped paths — a defect the fix would otherwise *introduce* by un-collapsing the directory.)

## Scope

**Problem statement:** `git status --porcelain` collapses fully-untracked directories to one `?? dir/` line; the tile file count counts that as 1, the tile line count expands it via `ls-files` (counting its lines), and the dialog skips it (omitting its files) — so file count, dialog list, and the `+` line total disagree.

**In scope:**

- `dashboard_lib.py`: use **`--untracked-files=all -z`** (NUL-delimited) on the two `git status --porcelain` invocations — the tile file-count source (`:1254`) and `list_git_changed_files` (`:847`) — **and** add `-z` to the tile's `git ls-files --others --exclude-standard` call (`:1267`); parse on `\0` instead of lines. NUL-delimited output emits **raw, unquoted** paths (no C-octal escaping, no surrounding quotes), so untracked directories expand to individual files everywhere AND non-ASCII / spaced filenames resolve on disk. **Why `-z`, not bare `-uall`:** the line-based form quotes + octal-escapes non-ASCII paths (e.g. `?? "…/caf\303\251.txt"`), which `_parse_porcelain_path` (`:822`) does not decode — newly-surfaced non-ASCII untracked files would then render as broken dialog rows with unresolvable paths and empty diffs (their lines silently dropped from *both* totals, so a reconciliation-only AC still passes). `-z` removes that whole class in one move. The trailing-slash dir-skip guards (`:852`, `:1270`) become no-ops for untracked content (they still guard nested-worktree entries).
- Confirm the dialog's per-file line counting covers the newly-listed untracked files (the existing "untracked new files don't appear in numstat — count lines directly" branch, `~:906`).
- Tests in `test_dashboard_server.py`: a fixture repo with an untracked directory of multiple files asserting the three readouts reconcile.

**Out of scope:**

- Changing the line-stat sources for tracked files (`git diff HEAD --shortstat` / `--numstat`) — only untracked enumeration changes.
- Reworking `FilesDialog` rendering, the `limit=500` cap, or the `since`-date semantics.
- Renaming or restructuring the git-collection functions (a DRY refactor into one canonical changed-file helper is a possible follow-up, not this fix).
- **Three PRE-EXISTING tile/dialog inconsistencies surfaced by adversarial verification (confirmed NOT regressions of this change — HEAD behaves identically — so left for a separate follow-up):** (1) `list_git_changed_files` sums `git diff --numstat HEAD` **and** `--cached`, so a staged-then-further-modified file can be double-counted; (2) the dialog counts lines for untracked **binary** files (via `read_text(errors="replace")`) while the tile skips them — divergence on binary untracked files; (3) a **content-changing rename** keys numstat under `{old => new}`, so the dialog drops its `lines_added`. All three predate this fix and concern tracked/binary line-stat sources (explicitly out of scope above); a DRY `_changed_files()` refactor (Option A) is the natural home for fixing them together.

## Acceptance Criteria

- [x] AC-1: With a fully-untracked directory containing multiple files (including a **spaced** and a **non-ASCII** filename), `list_git_changed_files` lists each file individually (N rows), not zero; each listed path **resolves on disk** and its `+`/diff is populated (no broken row / empty diff). *(Asserted in `GitUntrackedDirAccountingTests`: all three untracked files listed, `(root/name).exists()`, `get_file_diff` returns 200 + non-empty.)*
- [x] AC-2: The tile "Files" count (`git.files_changed`) equals the number of individual changed files (tracked changed + individual untracked) and matches the dialog list length **below the dialog's `limit=500` cap** — note the cap as the stated precondition (`-uall` makes exceeding it likelier; either cap the tile count to match the dialog or document the bound) — no over-count from collapsed directories. *(Both readouts now enumerate via the shared `_iter_porcelain_z` + trailing-slash skip; test asserts `files_changed == len(listed)`. Cap documented in the `collect_git_stats` comment.)*
- [x] AC-3: For a fixture with a **known** added-line total, both the dialog's per-file `+` sum AND the tile's `lines_added` equal that known total — an **absolute-correctness** check, not merely `tile == dialog sum` (equality alone can pass while both are equally wrong on a mis-parsed path); `lines_removed` is unchanged and consistent (tracked-diff-only). *(Test asserts untracked sum == 4 (absolute), `lines_added == dialog_sum`, and `lines_added == 5` (untracked 4 + tracked 1). `lines_removed` logic untouched.)*
- [x] AC-4: Tracked modified/added/deleted files, binary-file skipping, and the `since`-date filter path of `list_git_changed_files` are unchanged (regression-guarded). *(150-test dashboard suite green; `test_binary_untracked_file_skipped` updated to `-z` keys so it still exercises the skip; `since` branch logic unchanged — now fed raw `-z` paths that resolve where escaped paths previously could not.)*
- [x] AC-5: A `test_dashboard_server.py` test builds a temp repo with an untracked directory of multiple files (with **known line counts**, a **spaced** and a **non-ASCII** filename) plus a tracked modification **and a tracked rename**; it asserts AC-1..AC-3 (each listed path resolves on disk with a non-empty diff; file count == dialog length; the dialog `+` sum AND `lines_added` equal the known total) and that the tracked rename still parses; `python3 .wavefoundry/framework/scripts/run_tests.py` is green. *(`GitUntrackedDirAccountingTests.test_untracked_dir_files_reconcile_with_known_totals`; `diff.renames=true` pins the pure-rename contribution to 0; rename's new path listed, old path absent.)*

## Tasks

- [x] `dashboard_lib.py:1254` + `:1267` — switch the tile file-count `git status --porcelain` AND the untracked line-count `git ls-files --others --exclude-standard` to **`-z`** (NUL-delimited), splitting on `\0`; count individual untracked files.
- [x] `dashboard_lib.py:847` — switch `list_git_changed_files`'s status call to `git status --porcelain --untracked-files=all -z`, parse on `\0` (raw, unquoted paths — no `_parse_porcelain_path` quote-strip needed for these records); the `:852` trailing-slash skip stays as a harmless guard. Optionally tighten the ` -> ` rename split to fire only on `R`/`C` XY status (newly reachable for untracked paths containing a literal ` -> `).
- [x] Confirm the per-file line-count path (`~:880-910`, including the untracked direct-count branch) populates `+` lines for the newly-listed untracked files; adjust if needed so AC-3 holds.
- [x] Add a `test_dashboard_server.py` test: temp repo with an untracked dir (≥2 files incl. a **spaced** and a **non-ASCII** name, **known** line counts) + a tracked edit + a tracked rename; assert each untracked file is listed with a **resolvable path + non-empty diff**, `files_changed` == dialog length, the dialog `+` sum AND `lines_added` == the known total (absolute), and the rename still parses.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py`; run `.wavefoundry/bin/docs-lint` on this plan.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| untracked-all-enumeration | software-engineer | — | `--untracked-files=all` on both porcelain calls; verify per-file line counting. |
| tests | qa-reviewer | untracked-all-enumeration | Untracked-dir fixture reconciling file count + dialog list + line totals. |


## Serialization Points

- `.wavefoundry/framework/scripts/dashboard_lib.py` — both the tile git-snapshot (`~:1248-1297`) and `list_git_changed_files` (`~:829-910`); single owner, coordinate if other dashboard work is in flight.

## Affected Architecture Docs

N/A — a confined correctness fix to the dashboard's git-change enumeration; no module boundary, data-flow, or verification-surface change. (`git status --untracked-files=all` is a flag change to an existing input command.)

## AC Priority

(Provisional — finalized at Prepare wave.)


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The dialog must list untracked-dir files — the visible omission. |
| AC-2 | required   | File count must match the dialog (the reported tile-vs-dialog defect). |
| AC-3 | required   | The added-line total must reconcile with the dialog (the larger, ~4,956-line divergence). |
| AC-4 | required   | Must not regress tracked/binary/`since` handling. |
| AC-5 | required   | Test coverage + green suite. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-08 | Implemented the `-z` NUL-delimited fix: added `_iter_porcelain_z` (raw-path, rename-origin-consuming iterator) replacing the dead `_parse_porcelain_path`; switched both `git status --porcelain` calls to `--untracked-files=all -z` and the tile `ls-files` call to `-z`; tile file count + dialog list now share the iterator. Updated 3 `GitStatsParsingTests` mocks to the new arg-tuples + NUL values; added `GitUntrackedDirAccountingTests` (real git repo: untracked dir w/ spaced + non-ASCII names + known counts, tracked modify + tracked rename). | `dashboard_lib.py` `_iter_porcelain_z` / `list_git_changed_files` / `collect_git_stats`; `test_dashboard_server.py`; full dashboard module green (150 tests, 1 pre-existing skip). |
| 2026-06-08 | **Adversarial verification caught a self-introduced HIGH bug + fixed it.** A 3-lens verification workflow found that `collect_git_stats`'s `run()` helper `.strip()`s stdout — which corrupts the new NUL-delimited `-z` payloads at the blob boundary (a leading-space XY record like `" M a"` or a leading-space untracked filename), dropping/mis-parsing the first token and re-diverging the tile from the dialog (the exact invariant this fix targets). Added a `run_raw()` (unstripped) reader and routed the two `-z` calls through it; added `GitStatsZStripSafetyTests` (2 real-git regression cases: unstaged-modify of a 1-char file as the first record; leading-space untracked filename) that fail pre-fix and pass post-fix. | `dashboard_lib.py` `collect_git_stats.run_raw`; `test_dashboard_server.py::GitStatsZStripSafetyTests`; full framework suite green (2792 tests, dashboard 152). |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | **Selected:** add `--untracked-files=all` to the two `git status --porcelain` calls (tile count + `list_git_changed_files`). | Minimal, surgical fix that expands untracked directories to individual files everywhere porcelain is used — reconciling the file count, the dialog list, AND (since `ls-files` already expands) the `+` line total in one stroke, with no rename/binary/`since` regression risk. | **(A) Shared canonical `_changed_files()` helper** feeding both count and dialog — cleanest DRY but a larger two-path refactor; reserve as a follow-up. **(C) Switch all untracked enumeration to `git ls-files --others`** — also expands dirs, but the dialog still needs `status` for tracked modified/deleted, so it's a bigger rewrite of `list_git_changed_files` than just adding a flag. |
| 2026-06-08 | **Refined (pre-impl review):** use `--untracked-files=all -z` (NUL-delimited) on the porcelain calls AND `ls-files -z` — not the bare line-based `-uall`. | The grounded review reproduced a real defect the bare flag would introduce: non-ASCII/quoted untracked paths are C-octal-escaped in line output and `_parse_porcelain_path` can't decode them → broken dialog rows + empty diffs, with the lines symmetrically dropped so reconciliation-only ACs still pass. `-z` yields raw unquoted paths, fixing the dialog row + the tile line count at once. | Bare `-uall` line-parse (leaves non-ASCII broken); `-c core.quotePath=false` + C-unescape in the parser (strictly more work than `-z`). |
| 2026-06-08 | **Post-implementation fix (adversarial verification):** read the two `-z` git calls in `collect_git_stats` through a new unstripped `run_raw()` rather than the `.strip()`-ing `run()`. | The shared `run()` strips stdout (correct for scalar reads like `rev-parse`/`shortstat`), but stripping a NUL-delimited blob corrupts its first/last token — a leading-space XY record (`" M a"`) or leading-space filename — re-diverging tile from dialog. `list_git_changed_files` already used a raw reader; `collect_git_stats` now mirrors it for the `-z` calls only. | Drop `.strip()` from `run()` globally (rejected — the scalar callers rely on it); `rstrip("\n")` only (rejected — a filename could legitimately end in a space, and `run_raw` is clearer about intent). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| `--untracked-files=all` is slower on a huge untracked tree (e.g., a big `node_modules` not yet ignored). | Acceptable for the dashboard's snapshot cadence; `--exclude-standard`-respecting `ls-files` is already invoked for line counts, so the cost profile is similar. If it becomes a problem, scope a cap. |
| A repo-local `status.showUntrackedFiles=no` config could otherwise hide untracked files. | Explicit `--untracked-files=all` overrides any configured default, making the behavior deterministic. |
| The dialog's per-file line counting might not populate `+` for the newly-listed untracked files. | AC-3 + the test assert the reconciliation; the existing untracked direct-count branch (`~:906`) is the intended path — verify/extend it. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
