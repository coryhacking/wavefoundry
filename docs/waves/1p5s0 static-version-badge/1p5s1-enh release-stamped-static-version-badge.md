# Release-stamped static version badge (drop shields GitHub-API dependency)

Change ID: `1p5s1-enh release-stamped-static-version-badge`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Wave: `1p5s0 static-version-badge`
Last verified: 2026-06-15

## Rationale

The README version badge uses shields.io's dynamic `github/v/release/<owner>/<repo>` endpoint, which calls the GitHub API from shields' shared, rate-limited token pool. When that pool is exhausted the badge renders an error (`version: Unable to select next GitHub token from pool`) — confirmed live, fleet-wide on shields, unrelated to our repo. GitHub's own data is correct (`releases/latest` = the shipped version), so the badge breaks purely on an external dependency we don't control.

Fix: make the badge **static** and **stamp it at release**. A `https://img.shields.io/badge/version-<X.Y.Z>-purple` static badge makes no GitHub API call (no token pool, no outage), and `build_pack.py --release` rewrites the version in `README.md` each release — same place it already stamps `VERSION`/manifest — so it stays accurate without any runtime dependency.

## Requirements

1. `README.md`'s version badge is a **static** shields badge (`/badge/version-<X.Y.Z>-purple`), wrapping the same Releases link. Initialized to the current shipped version (`1.6.2`).
2. `build_pack.py --release` **rewrites** the badge's version to the release `version` (MAJOR.MINOR.PATCH, not the build suffix) as part of the release stamp, so it's committed in the same stamp commit and the badge always matches the latest release. `--release-dry-run` reports it without writing. Idempotent; never raises.
3. The README **fork-instructions** are updated: the badge image is now fork-stable (a generic static badge, no per-repo API URL) and its version is auto-stamped by `build_pack --release`; only the badge's **link target** + the Releases download link still need fork-redirecting.
4. No behavior change to the rest of `--release` (build → stamp → commit → tag → push → gh release).

## Scope

**In scope:**

- `README.md`: static badge (line ~3) + fork-instructions wording (lines ~320, ~324).
- `build_pack.py`: a `README.md` version-badge rewrite in the release stamp step; `--release-dry-run` line.
- `test_build_pack.py`: the rewrite updates the version + is idempotent + no-ops cleanly when the badge is absent.

**Out of scope:**

- The Python / License badges (static already; unaffected).
- The `.wavefoundry/framework/README.md` (no version badge).
- Cutting a release for this — the badge fix takes effect on the repo page on commit+push; `build_pack` stamping is for keeping future releases correct.

## Acceptance Criteria

- [x] AC-1: `README.md` carries a static `img.shields.io/badge/version-1.6.2-purple` badge (no `github/v/release`), linking to the Releases page; rendering has no GitHub-API / shields-token-pool dependency.
- [x] AC-2: `build_pack._stamp_readme_version_badge` rewrites the badge version to the release version (`ReadmeVersionBadgeStampTests`: rewrites `1.0.0`→`1.6.3`, idempotent, no-op when badge/README absent, leaves other badges untouched); wired into `_run_release_orchestration` before the stamp commit; `--release-dry-run` prints it without writing. **Full suite 3147 OK**; docs-lint clean.

**Scope addendum (operator-directed):** two additional **static** badges added to `README.md` (no stamping/dependency) — `MCP · local server` (→ modelcontextprotocol.io) and a supported-hosts badge (`Claude Code · Cursor · Codex · Junie`). No official MCP/harness badge standard exists; dynamic registry badges (Smithery/Glama/mcp.so) were rejected as they'd reintroduce the external dependency this wave removes and conflict with the local/no-account ethos.

## Tasks

- [x] `README.md`: static version badge (value `1.6.2`); fork-instructions updated; + 2 static badges (MCP, hosts).
- [x] `build_pack.py`: `_stamp_readme_version_badge` (regex rewrite of `badge/version-X.Y.Z-purple`) called before the stamp commit; dry-run line added.
- [x] `test_build_pack.py`: `ReadmeVersionBadgeStampTests` (rewrite / idempotent / no-badge / no-README; other-badges-untouched).
- [x] Full suite 3147 OK + docs-lint clean.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| badge-stamp| Engineering | —          | README static badge + build_pack stamp + tests |


## Serialization Points

- `build_pack.py` release stamp ordering (commit-before-tag, wave 1p5l4) must be preserved — the README stamp goes in the same pre-tag stamp step.

## Affected Architecture Docs

`N/A` — README presentation + release-tooling change; no runtime/contract behavior change.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Removing the shields GitHub-API dependency is the whole point. |
| AC-2 | required | Auto-stamping keeps the static badge correct without manual edits each release. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-15 | Confirmed the live badge renders `version: Unable to select next GitHub token from pool` (shields token-pool exhaustion — external, fleet-wide); GitHub `releases/latest` = v1.6.2 (correct). Fix: static badge + `build_pack --release` stamp. | `README.md:3`, `build_pack.py` |
| 2026-06-15 | **Implemented + verified.** README version badge → static `version-1.6.2-purple`; `_stamp_readme_version_badge` + dry-run line wired into release orchestration (before the stamp commit); 4 tests; fork-instructions updated. Operator-directed: added 2 static badges (MCP, hosts). **Full suite 3147 OK**; docs-lint clean. | `README.md`, `build_pack.py`, `test_build_pack.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-15 | Static badge stamped by `build_pack --release` | No GitHub-API call → immune to shields token-pool / outages; release-stamped → always accurate; trivial + no new infra. | Keep dynamic shields badge (rejected — the external dependency is the bug); self-hosted shields or a GitHub-Actions-updated badge (rejected — new infra for a one-line value) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| `build_pack` rewrite regex misses / mangles the badge | Tight regex on `badge/version-<semver>-purple`; idempotent; no-op + return False when absent; unit-tested |
| Badge value drifts if someone forgets to release | `build_pack --release` stamps it automatically every release; the committed value is the last shipped version |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
