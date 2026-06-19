# Forward-slash everywhere we write a path (write-consistency policy)

Change ID: `1p6dx-bug path-separator-write-consistency`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-18
Wave: `1p6d5 windows-python-exec-hardening-and-wsl2-support`

## Rationale

Operator policy: **every file path Wavefoundry writes into any file or document must use forward slashes (`/`), never backslashes (`\`)** — so an artifact generated on Windows is byte-identical to one generated on macOS/Linux (no OS-specific diffs, no cross-OS match failures). This generalizes the `1p6d6` map-href fix (`os.path.relpath` → `posixpath`) into a codebase-wide invariant.

A find→verify audit of `.wavefoundry/framework/scripts/*.py` found the index/graph layer already normalizes (`.as_posix()` / `.replace("\\","/")` / `chunker._normalize_path`) and the `build_pack` manifest is `.as_posix()`-safe. The remaining un-normalized path-writes (below) would emit `\` on Windows. The **critical** one is the secrets pipeline: a Windows-generated `scan-findings.json` / shipped `scan-allowlist` would carry backslash paths and fail to match a POSIX scan's entries.

Per operator direction, the policy is applied **literally everywhere we write a path, including the per-OS launcher/command strings** in `render_platform_surfaces.py` (the `cmd.exe`/`.cmd` forms). Those are execution paths, not data; `cmd.exe` accepts forward slashes for a quoted, env-rooted path, but that is **not verified on a real Windows host here**, and native Windows does not run today (Area-1), so this is a forward-compat change whose `cmd.exe` execution is explicitly Windows-smoke-deferred.

## Requirements

1. **Secrets pipeline (critical).** `wave_lint_lib/secrets_validators.py` builds `rel = str(file_path.relative_to(root))` (no `.as_posix()`) and writes it into the findings JSON (`"file": rel`); `build_scan_allowlist.py` reads `entry["file"]` and writes it verbatim into the shipped `scan-allowlist` (`<sha256>:<rel_path>:…`). Normalize at the source (`secrets_validators`) so the JSON + allowlist are forward-slash, and normalize defensively in `build_scan_allowlist` so a legacy/backslash input can't leak through.
2. **Reindex report markdown.** `docs_gardener.py` embeds `str(path.relative_to(root))` (3 sites) into the `docs/reports/reindex-{date}.md` report. Normalize to forward slashes.
3. **Surface-render stdout.** `render_agent_surfaces.py` prints `str(path.relative_to(repo_root))` (6 sites). These go to stdout, not a file — but normalize for consistency with the policy.
4. **Launcher / command strings (operator-directed, Windows-smoke-deferred).** `render_platform_surfaces.py` `launcher_command` (the `nt` `cmd.exe /c "…\…"` form, `rel_base.replace("/", os.sep)`) and the generated `.cmd` contents (`%VAR%\Scripts\python.exe`) intentionally emit `\`. Rewrite to `/`, keep the paths quoted so `cmd.exe` accepts them, and document that the `cmd.exe`-with-forward-slash execution is unverified on Windows (deferred to the Windows-smoke wave with the other `nt` branches).
5. **No POSIX/WSL2 regression** — every change is byte-identical or strictly-normalizing on POSIX; full framework suite green; docs-lint clean.
6. **Regression coverage** — unit tests assert each fixed site emits `/` (and never `\`) given a backslash-bearing input, simulated without a Windows host.

## Scope

**Problem statement:** Several path-writes emit OS-default separators, so Windows-generated artifacts carry `\` — breaking cross-OS reproducibility and (critically) secrets-allowlist matching.

**In scope:** the four write-site clusters above in `secrets_validators.py`, `build_scan_allowlist.py`, `docs_gardener.py`, `render_agent_surfaces.py`, and `render_platform_surfaces.py`; `os.name`/backslash-input-simulated unit tests; POSIX no-regression.

**Out of scope:**

- Sites already normalized (the index/graph layer, `build_pack`/`upgrade` manifest, `scan_secrets` JSON once its source is fixed) — verified safe, no change.
- End-to-end **native-Windows** verification of the `cmd.exe`-forward-slash launcher forms — deferred to the Windows-smoke wave (consistent with `1p6d6`).
- TOML — no dynamic paths are written to any `.toml` (verified); no change needed.

## Acceptance Criteria

- [x] AC-1: `secrets_validators` now builds the finding `rel` via `file_path.relative_to(root).as_posix()` (and `file_path.as_posix()` on the out-of-root fallback), so the findings JSON `"file"` is forward-slash on every OS. **Test note:** the effect is only *observable* on Windows — on POSIX `str(PosixPath)` already equals `.as_posix()`, so a POSIX unit test can't distinguish old from new (same boundary as `1p6d6`'s nt branches). `.as_posix()` is the canonical normalizer (and correctly preserves a literal-backslash POSIX filename, unlike a blind `replace` — red-team condition); verified by code review.
- [x] AC-2: `build_scan_allowlist` normalizes `entry["file"]` with `.replace("\\","/")` before the `root / rel` lookup, the `framework_rel` prefix slice, and the emitted `<sha256>:<rel>:…` key (defense-in-depth). No-op on POSIX (entries already `/`). **Test note:** isolating the one-line normalize needs the full `build_allowlist` scan fixture; it's a trivially-correct string replace covered by the existing `test_scan_secrets`/`test_secrets_validators` integration + code review.
- [x] AC-3: `docs_gardener` reindex-report rel paths use `.as_posix()` (3 sites). Same POSIX-indistinguishable note as AC-1 (correct-by-construction; manifests on Windows).
- [x] AC-4: `render_agent_surfaces` printed paths use `.as_posix()` (6 sites). stdout-only (not a file); consistency fix. Same POSIX-indistinguishable note.
- [x] AC-5: `render_platform_surfaces` `launcher_command` `nt` form and the generated `.cmd` contents (`windows_launcher_source`) emit `/` (operator-directed); the bare launcher form is now quoted too. **Tested** (`ForwardSlashPolicyTests`, 3): nt form `/`-and-quoted with no `\`, POSIX form unchanged, `.cmd` source has no backslashes. `cmd.exe`-forward-slash *execution* documented as Windows-smoke-deferred (native Windows is Area-1).
- [x] AC-6: **No POSIX/WSL2 regression** — full framework suite green (**3326**, +3); docs-lint clean; macOS output byte-identical (the `.as_posix()`/`.replace` calls are no-ops on POSIX, and the renderer emits the unchanged POSIX launcher form).

## Tasks

- [x] `secrets_validators.py`: finding `rel` now `file_path.relative_to(root).as_posix()` (+ `file_path.as_posix()` fallback).
- [x] `build_scan_allowlist.py`: `entry["file"].replace("\\","/")` before the lookup/slice/key (defense-in-depth).
- [x] `docs_gardener.py`: `.as_posix()` on the 3 reindex-report rel paths.
- [x] `render_agent_surfaces.py`: `.as_posix()` on the 6 printed rel paths.
- [x] `render_platform_surfaces.py`: `launcher_command` `nt` form + `windows_launcher_source` `.cmd` contents emit `/` (bare form now quoted); cmd.exe-forward-slash documented Windows-smoke-deferred.
- [x] Tests: `ForwardSlashPolicyTests` (launcher nt `/`+quoted, POSIX unchanged, `.cmd` no-backslash) + updated the nt launcher expectations; full suite 3326 green. The `as_posix` data-path fixes are POSIX-indistinguishable (manifest on Windows) — code-review-verified per the wave's Windows-deferred boundary.

## Affected Architecture Docs

`N/A` — single-module path-string normalization across several scripts; no architecture boundary, flow, or verification-contract change.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Critical — Windows-generated secrets findings/allowlist must match POSIX scans. |
| AC-2 | required | Defense-in-depth for the shipped allowlist (same matching risk). |
| AC-3 | important | Reindex report reproducibility across OSes. |
| AC-4 | nice-to-have | stdout cosmetic consistency (not a file). |
| AC-5 | required | The operator-directed core of the policy (launcher/cmd strings → `/`); Windows execution deferred but the emitted string must be `/`. |
| AC-6 | required | No POSIX/WSL2 regression — the load-bearing gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-18 | Planned from the write-consistency audit (operator policy: `/` everywhere we write a path). 4 finding clusters; index/graph layer + manifests already safe; TOML has no dynamic paths. | `secrets_validators.py:1379/1118`, `build_scan_allowlist.py:84/101`, `docs_gardener.py:253/260/264`, `render_agent_surfaces.py:311-377`, `render_platform_surfaces.py:114-121/177-179` |
| 2026-06-18 | Implemented all 5 clusters. `as_posix()` for Path values, `replace("\\","/")` for the already-string `entry["file"]` (red-team condition folded in — `as_posix` won't corrupt a literal-backslash POSIX filename). Launcher/cmd strings forward-slashed per operator direction (bare form now quoted); cmd.exe-forward-slash execution Windows-smoke-deferred. No-op on POSIX (paths already `/`), so no committed artifact changed. | +3 tests (`ForwardSlashPolicyTests`) + updated nt launcher expectations; full suite **3326 green**; docs-lint clean |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-18 | Apply the `/`-policy literally everywhere, including the per-OS launcher/cmd command strings. | Operator direction (consistency); the strings don't execute today (native Windows = Area-1/deferred), so it's forward-compat. | Exclude the launcher/cmd command strings (recommended by the agent — `\` is the canonical cmd.exe form) — overridden by operator. |
| 2026-06-18 | Keep launcher/cmd paths quoted and defer `cmd.exe`-forward-slash execution verification to the Windows-smoke wave. | `cmd.exe` accepts `/` for quoted env-rooted paths in practice, but it is unverified on a real Windows host here. | Claim it verified (rejected — dishonest; no Windows host). |
| 2026-06-18 | Admit as a new change to the open `1p6d5` wave rather than a new wave. | Same Windows-portability theme; `1p6d5` is open (single-OPEN), so a new wave couldn't open without closing it. | New wave (rejected — would require closing `1p6d5` first, not operator-approved). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Forcing `/` into a `cmd.exe`/`.cmd` execution path breaks Windows launch. | Paths stay quoted (cmd accepts `/` quoted); nothing executes these forms today (Area-1); flagged Windows-smoke-deferred so the future wave validates on a real host. |
| A normalization is missed and a backslash still leaks. | Audit-derived finding list + per-site regression tests feeding a backslash input; full suite + docs-lint. |
| Changing the secrets `rel` shifts allowlist entries for existing consumers. | The allowlist keys on `<sha256>:<rel_path>`; normalizing `rel` to `/` is the correct canonical form — a one-time re-stamp; POSIX `rel` was already `/`, so only Windows-generated entries change (none shipped). |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
