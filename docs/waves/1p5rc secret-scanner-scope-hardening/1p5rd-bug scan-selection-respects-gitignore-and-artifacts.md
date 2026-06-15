# Secret scan reads files outside scope (gitignored artifacts, versioned binaries)

Change ID: `1p5rd-bug scan-selection-respects-gitignore-and-artifacts`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-15
Wave: `1p5rc secret-scanner-scope-hardening`

## Rationale

Field report root-cause (follow-on to `1p5qp`/091yo): a downstream project's **gitignored** `.wavefoundry/index/` LanceDB segments were being read by the secrets scan (the ~54s spin). Investigation pinned the cause:

- File selection (`wave_lint_lib/secrets_validators.py`) is git-based and respects `.gitignore`: `_get_changed_files` and the primary path of `_get_all_files` use `git ls-files` + `git ls-files --others --exclude-standard`. In a normal git repo, gitignored `.wavefoundry/index/` is **excluded**.
- But `_get_all_files` has a **fallback** (`:144–150`): when `git ls-files` returns non-zero (not a git repo, git unavailable, or the scan `root` isn't the worktree root) it walks `root.rglob("*")` excluding only `.git/` — it does **not** consult `.gitignore`. That fallback is the only path that sweeps gitignored files into the scan, and it's what hit the reporter (their target wasn't a usable git worktree at scan time).
- The framework scan `[allowlist].paths` does **not** cover `.wavefoundry/index/` (or `.wavefoundry/cache|logs|dist/`, or the `wavefoundry-*.zip` pack), so once selected, nothing excludes them at scan time.
- Separately, the `1p5qp` extension fast-skip keys on `Path.suffix`, so a **versioned** shared object (`libfoo.so.13`) has suffix `.13` and slips past both the skip and the `$`-anchored `.so` allowlist entry.

`1p5qp` made the *symptom* cheap (binary extensions skipped before read), but the underlying scope gaps remain: gitignored files in a non-git context are still scanned, framework runtime artifacts aren't allowlisted, and versioned `.so.N` libs aren't skipped.

## Requirements

1. **Framework runtime artifacts are never scanned, in any project, git or not.** Add to the framework `[allowlist].paths` (matched in `scan_file_raw` before any read): `.wavefoundry/index/`, `.wavefoundry/cache/`, `.wavefoundry/logs/`, `.wavefoundry/dist/`, and the pack glob `wavefoundry-*.zip`. Do NOT exclude `.wavefoundry/framework/` (that's shipped source, intentionally scannable).
2. **The `rglob` fallback honors `.gitignore` when possible.** When `git ls-files` fails, filter the walked candidates through `git check-ignore` (best-effort, batched): if it's actually a git worktree (e.g. `ls-files` glitched), gitignored paths are dropped; if it's truly non-git, `check-ignore` errors and the walk is kept as-is (the allowlist + extension skip still exclude framework artifacts). Still exclude `.git/`. Never raise.
3. **Versioned shared objects are skipped.** The binary-extension fast-skip recognizes multi-component suffixes like `.so.13` / `.dylib.1` (treat a `.so`/`.dylib`/`.dll` component anywhere in the suffix chain as binary), so versioned libs don't reach the per-file read.
4. **No regression to real detection:** source/config files are still scanned; a real secret in a tracked source file is still flagged; the git-based selection path is unchanged.

## Scope

**In scope:**

- `.wavefoundry/framework/scan-rules.toml` (`[allowlist].paths` additions).
- `wave_lint_lib/secrets_validators.py`: `_get_all_files` rglob fallback → `git check-ignore` filter; `_BINARY_SKIP_EXTENSIONS` / the skip check → versioned-suffix aware.
- Tests (`test_secrets_validators.py`): gitignored-artifact exclusion via allowlist; rglob fallback drops gitignored paths when check-ignore works and keeps them when non-git; `.so.13` skipped; source still scanned.

**Out of scope:**

- Resolving the scan `root` to the git worktree root (a deeper selection change) — the allowlist + check-ignore filter already neutralize the reported impact; revisit only if field evidence shows the wrong-root case dominates.
- The config-aligned file cap (`indexing.max_file_bytes`) — separate perf-knob enhancement, deferred.
- Reworking `.gitignore` parsing in pure Python (rejected — `git check-ignore` is the correct oracle).

## Acceptance Criteria

- [x] AC-1: framework runtime artifacts are excluded from the scan. The shipped `scan-rules.toml` `[allowlist].paths` now match `.wavefoundry/{index,cache,logs,dist}/**` + `wavefoundry-*.zip` (and NOT `.wavefoundry/framework/` source) — asserted against the real ruleset in `test_runtime_artifacts_allowlisted_framework_source_not`. End-to-end (`test_artifact_with_secret_not_flagged_source_is`): in a non-git tree, a `.wavefoundry/index/*.lance` with a secret string is skipped while a `.py` with the same string is flagged.
- [x] AC-2: `_filter_gitignored` drops `.gitignore`d paths when `git check-ignore` works and keeps the walk (no crash) when the dir is truly non-git (`test_filter_gitignored_drops_in_repo_keeps_when_non_git`); the `rglob` fallback wires it in and still excludes `.git/`. Versioned shared objects (`.so.13`/`.dylib.1`) are skipped, while `foo.so.txt`/dotted source still scan (`test_is_binary_path_versioned_shared_objects`). **Full suite 3143 OK**; docs-lint clean.

## Tasks

- [x] `scan-rules.toml` `[allowlist].paths`: added `(?:^|/)\.wavefoundry/(?:index|cache|logs|dist)(?:/.*)?$` + `(?:^|/)wavefoundry-[0-9][^/]*\.zip$` (anchored; verified they don't match `.wavefoundry/framework/`).
- [x] `_get_all_files` fallback → `_filter_gitignored` (batched `git check-ignore --stdin`; returncode 0/1 → filter, else keep; never raises).
- [x] `_is_binary_path` versioned-suffix skip (`.so.N`/`.dylib.N`/`.dll.N` via `Path.suffixes`, numeric trailing only); `scan_file_raw` uses it.
- [x] Tests (4 in `ScannerScopeHardeningTests`: real-ruleset allowlist, versioned `_is_binary_path`, check-ignore both ways, end-to-end artifact-not-flagged) + full suite 3143 OK + docs-lint.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| scope-fix  | Engineering | —          | allowlist + fallback + suffix skip in one file pair |


## Serialization Points

- `scan-rules.toml` + `secrets_validators.py` change together; no other in-flight change touches them.

## Affected Architecture Docs

`N/A` — scanner file-selection/allowlist scope fix; no contract/behavior change to detection of in-scope source secrets. `scan-findings-format.md` describes the ledger, not selection.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The reported bug — framework runtime artifacts must never be scanned, in any project. |
| AC-2 | required | Close the root selection gap (gitignore-blind fallback) + the versioned-binary miss without regressing source detection. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-15 | Scoped: root cause of the 091yo spin is the `rglob` fallback (`secrets_validators.py:144-150`) being `.gitignore`-blind + `.wavefoundry/index/` not allowlisted. Fix = framework allowlist additions (sure fix, applies in `scan_file_raw` regardless of selection) + `check-ignore` filter on the fallback + versioned-`.so.N` skip. | `secrets_validators.py:144`, `scan-rules.toml` |
| 2026-06-15 | **Implemented + verified.** `scan-rules.toml` allowlist additions; `_filter_gitignored` wired into the `rglob` fallback; `_is_binary_path` (versioned-suffix aware) replaces the bare `suffix in set` check. 4 new tests; **full suite 3143 OK**; docs-lint clean. The fix is layered: the allowlist (applied before any read) fixes the reported `.wavefoundry/index/` scan even in pure-non-git; `check-ignore` is the bonus for the glitched-repo case. | `secrets_validators.py`, `scan-rules.toml`, `test_secrets_validators.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-15 | Fix via framework allowlist + `git check-ignore` fallback filter, not a pure-Python `.gitignore` parser | The allowlist is the surest, context-independent exclusion (runs before any read); `check-ignore` is git's own authoritative oracle for the general gitignore case. | Reimplement `.gitignore` matching in Python (rejected — complex, error-prone); resolve worktree root (deferred — bigger change, not needed to neutralize impact) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Allowlist pattern accidentally excludes `.wavefoundry/framework/` (shipped source) | Anchor the patterns to the specific runtime subdirs (`index`/`cache`/`logs`/`dist`); test that `framework/` paths still scan |
| `git check-ignore` adds latency on the fallback | One batched `--stdin` call; only on the (already-slow) fallback; never on the git-tracked happy path |
| Versioned-suffix logic over-skips a real source file with a dotted name | Match only when a known binary component (`.so`/`.dylib`/`.dll`) appears in the suffix chain; test a `.py`-style dotted name still scans |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
