# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-15

wave-id: `1p5rc secret-scanner-scope-hardening`
Title: Secret Scanner Scope Hardening

## Objective

Fix the root cause behind the `1p5qp`/091yo scanner spin: the secrets scan reads files it should never touch. In a non-git context (or when the scan root isn't the git worktree root), `_get_all_files`'s `rglob` fallback ignores `.gitignore` and sweeps in framework runtime artifacts (`.wavefoundry/index/` LanceDB segments, the pack zip). When this wave closes, framework runtime artifacts are never scanned in any project (allowlisted before any read), the `rglob` fallback honors `.gitignore` via `git check-ignore`, and versioned shared objects (`.so.N`) are skipped — with source-secret detection unchanged.

## Changes

Change ID: `1p5rd-bug scan-selection-respects-gitignore-and-artifacts`
Change Status: `implemented`

Completed At: 2026-06-15

## Wave Summary

Wave `1p5rc` (Secret Scanner Scope Hardening) delivered one change: Secret scan reads files outside scope (gitignored artifacts, versioned binaries). Notable adjustments during implementation: Secret scan reads files outside scope (gitignored artifacts, versioned binaries): Scoped: root cause of the 091yo spin is the `rglob` fallback (`secrets_validators.py:144-150`) being `.gitignore`-blind + `.wavefoundry/index/` not allowlisted. Fix = framework allowlist additions (sure fix, applies in `scan_file_raw` regardless of selection) + `check-ignore` filter on the fallback + versioned-`.so.N` skip.

**Changes delivered:**

- **Secret scan reads files outside scope (gitignored artifacts, versioned binaries)** (`1p5rd-bug scan-selection-respects-gitignore-and-artifacts`) — 2 ACs completed. Key decisions: --------; Fix via framework allowlist + `git check-ignore` fallback filter, not a pure-Python `.gitignore` parser
## Journal Watchpoints

- **Don't over-exclude `.wavefoundry/framework/`** — that's shipped framework source and must stay scannable; the allowlist patterns anchor to the runtime subdirs (`index`/`cache`/`logs`/`dist`) only. Add a test that a `framework/` path still scans.
- **Framework-edit gate:** touches `scan-rules.toml` + `wave_lint_lib/secrets_validators.py` — open `framework_edit_allowed` before edits, close after.
- **`check-ignore` is best-effort:** returncode 0/1 → filter applies; anything else (truly non-git) → keep the walk (the allowlist + extension skip still exclude framework artifacts). Never raise; never block on git absence.
- **Security-faithfulness:** this is a scanner-SCOPE change — confirm it does not narrow detection of in-scope SOURCE secrets (only excludes framework runtime artifacts + gitignored + versioned binaries). A real secret in a tracked source file must still be flagged.

## Review Evidence

- wave-council-readiness: READY — readiness sign-off recorded 2026-06-15. Single low-risk scanner-scope fix. Security-faithfulness: excludes only framework runtime artifacts + git-ignored paths + versioned binaries (no source); the `check-ignore` filter makes the `rglob` fallback consistent with the already-gitignore-respecting git-tracked path (closes an inconsistency, not a new hole); no narrowing of in-scope source-secret detection. The fix does not depend on `check-ignore` — the framework allowlist (applied in `scan_file_raw` before any read) fixes the reported `.wavefoundry/index/` scan even in the pure-non-git case. Strongest challenge: excluding gitignored files could hide a secret — rejected, the git-tracked path already excludes them; this only makes the fallback consistent. Strongest alternative: pure-Python gitignore parser — rejected (`git check-ignore` is the oracle). Required test: `.wavefoundry/framework/` paths still scan.
- wave-council-delivery: READY — delivery sign-off recorded 2026-06-15. `1p5rd` implemented; full suite **3143 OK**; docs-lint clean. **Security-faithfulness PASS:** no source-detection narrowing — allowlist additions match only `.wavefoundry/{index,cache,logs,dist}/` + the pack zip (verified NOT matching `.wavefoundry/framework/` source); `git check-ignore` only drops what git already ignores (makes the `rglob` fallback consistent with the git-tracked path, not a new hole); the versioned-suffix skip catches `.so.N` with numeric-only trailing so `foo.so.txt`/dotted source still scan; a tracked source secret is still flagged (test). `_filter_gitignored` fails **open** in the safe direction (non-git/error → keep the walk), and the allowlist (applied before read, git-independent) fixes the reported `.wavefoundry/index/` scan even with git absent — end-to-end test on a non-git tree confirms. Contained to `scan-rules.toml` + `secrets_validators.py`; 4 new tests in `ScannerScopeHardeningTests`. Closeable on merits.
- operator-signoff: approved — 2026-06-15, operator requested close + a 1.6.2 release. Root-cause scanner-scope fix; full suite 3143 OK, prepare + delivery council PASS, no source-detection narrowing.

## Review Checkpoints

- **Delivery-phase Wave Council [delivery-council] — 2026-06-15: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: a scanner-scope narrowing could hide in-scope source secrets — resolved: exclusions are framework runtime artifacts only (regex verified to not match `.wavefoundry/framework/`), `check-ignore` only mirrors git's own ignore set (the git-tracked path already excludes those, so it closes an inconsistency), and the versioned-suffix skip is numeric-trailing-only (`foo.so.txt` still scans); `_filter_gitignored` fails open (scan-more) so it never causes a miss, and the allowlist is applied before any read independent of git; full suite 3143 OK, docs-lint clean; strongest-alternative: pure-Python gitignore parser, rejected — `git check-ignore` is the authoritative oracle)
- **Prepare-phase Wave Council [prepare-council] — 2026-06-15: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: security-reviewer; strongest-challenge: the change narrows what the scanner reads, so does it narrow detection of in-scope SOURCE secrets? — resolved: it excludes only framework runtime artifacts (`.wavefoundry/index|cache|logs|dist`, pack zip), git-ignored paths, and versioned binaries; `.wavefoundry/framework/` stays scannable; the `check-ignore` filter makes the `rglob` fallback consistent with the git-tracked path that already excludes gitignored files, so it closes an inconsistency rather than opening a hole; fix doesn't depend on check-ignore (allowlist runs before any read); strongest-alternative: pure-Python `.gitignore` parser, rejected because `git check-ignore` is git's authoritative oracle; required test: a `framework/` path still scans and a tracked source secret is still flagged)

## Dependencies

- No external wave dependencies.
