# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-15

wave-id: `1p5s0 static-version-badge`
Title: Static Version Badge

## Objective

The README version badge uses shields.io's dynamic `github/v/release` endpoint, which broke live (`version: Unable to select next GitHub token from pool` — shields' shared GitHub-API token pool exhausted, fleet-wide, unrelated to our repo). Remove that external dependency: make the badge a **static** shields badge and have `build_pack.py --release` stamp its version each release (alongside `VERSION`/manifest). When this wave closes, the badge has no GitHub-API dependency and stays accurate automatically.

## Changes

Change ID: `1p5s1-enh release-stamped-static-version-badge`
Change Status: `implemented`

Completed At: 2026-06-15

## Wave Summary

Wave `1p5s0` (Static Version Badge) delivered one change: Release-stamped static version badge (drop shields GitHub-API dependency). Notable adjustments during implementation: Release-stamped static version badge (drop shields GitHub-API dependency): **Implemented + verified.** README version badge → static `version-1.6.2-purple`; `_stamp_readme_version_badge` + dry-run line wired into release orchestration (before the stamp commit); 4 tests; fork-instructions updated. Operator-directed: added 2 static badges (MCP, hosts). **Full suite 3147 OK**; docs-lint clean.

**Changes delivered:**

- **Release-stamped static version badge (drop shields GitHub-API dependency)** (`1p5s1-enh release-stamped-static-version-badge`) — 2 ACs completed. Key decisions: --------; Static badge stamped by `build_pack --release`
## Journal Watchpoints

- **Preserve the `1p5l4` release-stamp ordering** — the README badge rewrite goes in the same pre-tag stamp step (build → stamp VERSION/manifest/README → `git add -A` commit → tag → push). Don't move it after the tag.
- **Framework-edit gate:** touches `build_pack.py` — open `framework_edit_allowed` before edits, close after. `README.md` is repo root (doc), no seed gate.
- **Stamp the MAJOR.MINOR.PATCH only** (`args.version`, e.g. `1.6.2`), not the `+build` suffix — the badge shows the release version.
- **No release required to fix the live badge** — committing+pushing the static README badge fixes the repo page immediately; the `build_pack` stamp is for keeping future releases correct.

## Review Evidence

- wave-council-readiness: READY — readiness sign-off recorded 2026-06-15. Low-risk tooling/doc change removing an external dependency. Only risk: the `build_pack` README-rewrite regex mangling the file — mitigated by a tight `badge/version-X.Y.Z-purple` pattern + idempotence + no-op-when-absent + a unit test. Live badge fix lands on commit+push (no release needed); the stamp keeps future releases correct. No security/runtime surface. Strongest challenge: regex over-match (mitigated). Strongest alternative: keep the dynamic shields badge — rejected (the external GitHub-API dependency is the bug).
- wave-council-delivery: READY — delivery sign-off recorded 2026-06-15. `1p5s1` implemented: README version badge is static (no GitHub-API dependency); `_stamp_readme_version_badge` rewrites it at release before the stamp commit (preserving the 1p5l4 commit-before-tag ordering); regex is tight + idempotent + no-ops on absent badge/README (4 tests in ReadmeVersionBadgeStampTests, other badges untouched). `--release-dry-run` prints without writing. Operator-directed scope addendum: 2 static badges added (MCP, hosts) — no stamping/dependency. Full suite 3147 OK; docs-lint clean. No security/runtime surface. Closeable on merits.
- operator-signoff: approved — 2026-06-15, operator requested close + commit/push (holding the next release). README version badge is static + auto-stamped; two static badges added (MCP, hosts); full suite 3147 OK, prepare + delivery council PASS.

## Review Checkpoints

- **Delivery-phase Wave Council [delivery-council] — 2026-06-15: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the release-time README rewrite regex could mangle the file or over-match other badges — mitigated by a tight pattern keyed to the version badge only, idempotence, no-op on absent badge/README, and tests asserting MCP/License badges are untouched; the rewrite runs inside the existing pre-tag stamp step so the 1p5l4 commit-before-tag ordering is preserved; strongest-alternative: keep the dynamic shields badge, rejected — the external GitHub-API token-pool dependency is the breakage being removed; the added MCP/hosts badges are static so they carry no new dependency)
- **Prepare-phase Wave Council [prepare-council] — 2026-06-15: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: the `build_pack` README-rewrite regex could mangle the file or over-match — mitigated by a tight `badge/version-X.Y.Z-purple` pattern, idempotence, no-op-when-absent, and a unit test; strongest-alternative: keep the dynamic `github/v/release` shields badge — rejected because the external shields→GitHub-API token-pool dependency is exactly the breakage being removed)

## Dependencies

- No external wave dependencies.
