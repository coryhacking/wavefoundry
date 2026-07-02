# Windows line-endings and path normalization: latent CRLF and cosmetic path issues

Change ID: `1p9hm-enh windows-line-endings-and-paths`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-07-02
Wave: 1p9hn windows-portability-round-2

## Rationale

The Windows audit identified four low-severity clusters with no immediate crash or corruption impact but which create latent failure risk or inconsistent behavior on Windows:

**L-2 — Missing target-repo `.gitattributes` propagation:** Wave 1p7pn added a `.gitattributes` to the Wavefoundry self-host repo pinning `bin/wf` to LF. This was never propagated to target repos on install/upgrade. A target repo committing the rendered `bin/wf` (LF shebang) will have it rewritten to CRLF on a teammate's Windows clone with `core.autocrlf=true`, producing `#!/usr/bin/env bash\r` — unresolvable by MSYS2/WSL2 `sh`.

**L-3 — `_sha256_file` hashes raw bytes; CRLF rewrite changes the digest:** Both `secrets_validators.py:520` and `build_scan_allowlist.py:35` hash via `hashlib.sha256(path.read_bytes())`. Non-`.py` framework files (`*.md`, `*.json`, `*.html`, `*.js`) without explicit `eol` attributes check out as CRLF on `core.autocrlf=true`, so the file digest differs from the LF digest baked into the shipped allowlist. Latent today (header-only allowlist, 0 live entries) but will silently break when the first non-`.py` framework false-positive is allowlisted.

**L-4a — Backslash paths in operator-facing output:** Six `str(path.relative_to(root))` sites in `upgrade_extensions.py` (`:203`, `:233`, `:294`, `:421`, `:439`, `:472`) and one in `server_impl.py` (`:8610`, inside `_audit_harness_coherence`) emit Windows backslash paths. The `.replace("\\", "/")` convention used in 37 other `relative_to` sites in `server_impl.py` was missed.

**L-4b — seed-050 Hook Contract describes retired launcher model:** `050-agent-entry-surface-bootstrap.prompt.md:253` (and `:341`, JSON snippets at `:333/335/356/401-402`) documents the three-variant launcher (`<name>`, `<name>.cmd`, `<name>.py`) and nonexistent Windows `.cmd` hook. The renderer now writes only `<name>.py` and uses `python3 "<name>.py"`. Stale content could mislead an agent hand-authoring hooks on Windows.

**L-4c — Convention hook OS-awareness:** `upgrade_wavefoundry.py:844` (`_run_hook`) uses `os.access(X_OK)` (no-op on Windows) and spawns an extensionless file directly, which Windows cannot execute by path. The `OSError` propagates uncaught. Convention hooks are opt-in and dormant by default.

**L-4d — Dashboard `allow_reuse_address` hardening:** `dashboard_server.py:441` inherits `allow_reuse_address=True`. On Windows, `SO_REUSEADDR` permits multiple sockets to bind the same port simultaneously, unlike POSIX. Defense-in-depth only; the port-probe already rejects most collisions.

## Requirements

1. Install/upgrade must idempotently ensure a `.gitattributes` file in the target repo containing entries pinning rendered framework files to their correct line endings: `.wavefoundry/bin/* text eol=lf`, rendered hook dirs `text eol=lf`, `*.py text eol=lf`, `*.cmd text eol=crlf`. If `.gitattributes` already exists, merge the Wavefoundry block without overwriting existing entries.
2. Both `_sha256_file` implementations must normalize `\r\n` → `\n` before hashing so the digest is line-ending-independent.
3. `server_impl.py:8610` and the six `upgrade_extensions.py` sites must use `.replace("\\", "/")` (or `.as_posix()`) for consistency with surrounding code.
4. seed-050 Hook Contract section must be rewritten to reflect the single-`<name>.py` launcher and `python3 "<name>.py"` command (requires `seed_edit_allowed` gate — open before edit, close immediately after).
5. `upgrade_wavefoundry.py:844` `_run_hook` must handle the extensionless-file case on Windows: either skip `<name>` files with no `.py` suffix (with a logged warning), or OS-aware suffix search (prefer `<name>.py` on Windows).
6. `dashboard_server.py:441` must set `allow_reuse_address = False`.

## Scope

**Problem statement:** A cluster of low-severity Windows issues: latent CRLF hash breakage, missing `.gitattributes` propagation to target repos, cosmetic backslash paths in output, a stale seed doc describing retired hook launchers, extensionless hook OS-awareness, and a defense-in-depth socket hardening.

**In scope:**

- Target-repo `.gitattributes` creation/merge on install and upgrade (L-2)
- `_sha256_file` CRLF normalization at both sites (L-3)
- Backslash path normalization at `server_impl.py:8610` and `upgrade_extensions.py` ×6 (L-4a)
- seed-050 Hook Contract rewrite under `seed_edit_allowed` gate (L-4b)
- `_run_hook` extensionless-file OS-awareness (L-4c)
- `dashboard_server.py:441` `allow_reuse_address = False` (L-4d)

**Out of scope:**

- The `.gitattributes` in the Wavefoundry self-host repo itself (already correct from 1p7pn)
- Changing what files are shipped in the framework distribution (separate packaging concern)

## Acceptance Criteria

- [x] AC-1: `render_platform_surfaces` creates/merges a `.gitattributes` in the target repo, non-destructively (marker-delimited block, operator lines preserved verbatim). **Scope decision:** the propagated block is NARROW (framework-rendered paths only — `.wavefoundry/bin/*`, rendered hook dirs, `.wavefoundry/bin/*.cmd`), NOT the self-host's broad `* text=auto`/`*.py eol=lf`/global `*.cmd`, which would overreach into a target repo's own sources. `RenderGitattributesBlockTests` (5 tests).
- [x] AC-2: Both `_sha256_file` implementations normalize CRLF before hashing; `TestSha256FileCrlfNormalization` confirms CRLF and LF variants hash identically AND the two copies agree
- [x] AC-3: `server_impl.py:8610` and all six `upgrade_extensions.py` relative-path sites use forward slashes (`.replace("\\", "/")`)
- [x] AC-4: seed-050 Hook Contract rewritten to `<name>.py`-only launcher + `python3 "<name>.py"` command; all four JSON snippets updated; retired-trampoline note added (under `seed_edit_allowed` gate, closed immediately after)
- [x] AC-5: `_run_hook` is OS-aware — on Windows it prefers `<name>.py` (via interpreter) or `<name>.cmd`/`.bat`, and logs+skips a bare extensionless hook instead of raising `OSError`; POSIX path unchanged (`RunHookTests` still green)
- [x] AC-6: `dashboard_server._QuietThreadingHTTPServer` sets `allow_reuse_address = os.name != "nt"` — **OS-scoped during delivery review**: disabled only on Windows (where SO_REUSEADDR permits duplicate LIVE binds), kept enabled on POSIX where SO_REUSEADDR only allows beneficial TIME_WAIT rebind (and `choose_port` prefers the last-recorded port, so a blanket `False` would fail a quick restart). Blanket `False` would have been a POSIX regression.

## Tasks

- [x] Add `.gitattributes` creation/merge step (`render_gitattributes_block`) to `render_platform_surfaces` + wire into `main()` (L-2)
- [x] Normalize `\r\n` → `\n` in both `_sha256_file` implementations (L-3)
- [x] Add `.replace("\\", "/")` to `server_impl.py:8610` (L-4a)
- [x] Add `.replace("\\", "/")` to `upgrade_extensions.py` at `:203`, `:233`, `:294`, `:421`, `:439`, `:472` (L-4a)
- [x] Open `seed_edit_allowed` gate; rewrite seed-050 Hook Contract; close gate immediately after (L-4b)
- [x] Fix `_run_hook` extensionless-hook handling at `upgrade_wavefoundry.py` (L-4c)
- [x] Set `allow_reuse_address = False` in `dashboard_server.py` (L-4d)

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| gitattributes | implementer | — | L-2: add to install/render flow |
| sha256-crlf | implementer | — | L-3: normalize in both _sha256_file sites |
| path-normalization | implementer | — | L-4a: cosmetic .replace fixes |
| seed-050-rewrite | implementer | — | L-4b: requires seed_edit_allowed gate |
| hook-os-aware | implementer | — | L-4c: _run_hook extensionless handling |
| dashboard-reuse | implementer | — | L-4d: allow_reuse_address=False |

## Serialization Points

- seed-050 rewrite requires `wave_gate_open(gate="seed_edit_allowed")` before edit and `wave_gate_close` immediately after. No other workstreams depend on it.

## Affected Architecture Docs

N/A — changes are confined to individual function bodies and one seed prompt. No boundary or flow change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | important | Latent: breaks MSYS2/WSL2 on a teammate's Windows clone; no existing mitigation |
| AC-2 | important | Latent: breaks allowlist matching when first non-.py entry is added |
| AC-3 | nice-to-have | Cosmetic; no functional impact |
| AC-4 | important | Stale doc is a regression vector for agents hand-authoring hooks |
| AC-5 | nice-to-have | Opt-in operator feature, dormant by default |
| AC-6 | nice-to-have | Defense-in-depth only |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-02 | Change doc created from 10-dimension Windows audit | audit workflow wf_51bd40fe-082 |
| 2026-07-02 | Implemented all six sub-items (L-2 gitattributes, L-3 sha256 CRLF, L-4a paths, L-4b seed-050, L-4c hook, L-4d socket) | Full suite tests OK; new tests: `RenderGitattributesBlockTests` (5), `TestSha256FileCrlfNormalization` (2); docs-lint clean |
| 2026-07-02 | Delivery review fixes: (a) `_run_hook` `.cmd`/`.bat` branch now launches via `cmd /c` (bare-path `subprocess.run` would raise WinError 193 on Windows); (b) `allow_reuse_address` OS-scoped to avoid a POSIX TIME_WAIT regression | code-reviewer + POSIX-regression lanes; new test `test_convention_hook_windows_dispatches_cmd_via_cmd_shell` |
| 2026-07-02 | Self-host `.gitattributes` reconciliation note (see Decision Log): the unconditional `render_gitattributes_block` will fold the self-host repo's existing hook/bin `eol=lf` pin lines into the managed block on the next render — functionally identical (verified via `git check-attr`: `wf`→lf, `wf.cmd`→crlf, hooks→lf all unchanged) and idempotent, but produces a one-time cosmetic diff | reality-checker lane |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-02 | Batch all L-4 items into this change | All are low-severity, cosmetic, or latent; batching keeps wave size manageable | Separate changes per item (more process overhead for low-risk fixes) |
| 2026-07-02 | Merge .gitattributes rather than overwrite | Safety rule: never overwrite project-local customizations without a diff | Always create fresh (risks destroying operator-custom entries) |
| 2026-07-02 | **Implement `.gitattributes` merge via idempotent marker-delimited block** (mirroring `render_gitignore_block`), NOT a diff+interactive-confirm | The council flagged that an interactive confirmation would hang in the non-interactive render/CI/hook contexts where `render_platform_surfaces` runs. A marker-owned block is inherently non-destructive (operator lines untouched) so there is nothing to prompt on. | diff+abort-on-conflict (breaks non-interactive render) |
| 2026-07-02 | **Narrow the propagated `.gitattributes` block** to framework-rendered paths only (dropped the self-host's broad `* text=auto` / `*.py eol=lf` / global `*.cmd`) | Those broad rules are correct for the self-host repo (it owns its whole tree) but would OVERREACH into a consuming target repo — forcing the operator's own `*.py`/`*.cmd` line endings and, for an appended `* text=auto`, potentially overriding operator binary declarations (last-match precedence). The narrow set fixes the actual L-2 breakage (LF shebang in `.wavefoundry/bin/*`) without touching the target's sources. Deviation from the change doc's literal entry list; safest-default per org security guidance. | Propagate the full broad self-host block (target-repo overreach risk) |

## Risks

| Risk | Mitigation |
| --- | --- |
| `.gitattributes` merge conflicts with operator-custom entries | Show diff and require operator confirmation before writing; abort if conflict |
| CRLF normalization in _sha256_file changes existing allowlist digests | Allowlist is currently header-only with 0 live entries; no stored digests to break |
| seed-050 edit without gate causes framework drift | Gate enforcement is mandatory before edit per CLAUDE.md |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
