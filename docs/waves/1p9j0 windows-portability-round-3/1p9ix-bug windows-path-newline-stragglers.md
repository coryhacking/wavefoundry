# Fix Windows newline/path stragglers in agent-surface render and gitignore secrets filter

Change ID: `1p9ix-bug windows-path-newline-stragglers`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-03
Wave: TBD

## Rationale

Two one-line Windows-portability stragglers escaped the 1p9hm "windows-line-endings-and-paths" theme (round-2 missed both). Each is the exact sibling of a fix the theme already landed elsewhere, so the correct construct to copy is already in-tree.

**F14 — agent-surface renders get CRLF on Windows.** `render_agent_surfaces.write_text` at `.wavefoundry/framework/scripts/render_agent_surfaces.py:295-297` writes with `path.write_text(content, encoding="utf-8")` and **no** `newline=""`:

```python
def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")   # :297 — missing newline=""
```

The sibling `render_platform_surfaces.write_text` at `.wavefoundry/framework/scripts/render_platform_surfaces.py:69-78` was already fixed in wave 1p7tz to open with `newline=""`, with an inline comment explaining that the default `newline=None` translates every embedded `"\n"` → `os.linesep` on native Windows. Because the agent-surface helper still uses the default, a render/upgrade run on native Windows writes the four fresh agent surfaces it produces — `.cursor/rules/auto-guru.mdc`, `.claude/agents/guru.md`, `.codex/skills/auto-guru/SKILL.md`, `.codex/config.toml` (written via this helper at lines 310, 315, 319, 323) — with CRLF line endings instead of LF. That yields a spurious full-file line-ending diff on re-render and non-byte-identical output across hosts.

**F18 — gitignore membership never matches on Windows.** `_filter_gitignored` at `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py:147-177` builds its relpath list at line 160 with `str(p.relative_to(root))`:

```python
rels.append(str(p.relative_to(root)))   # :160 — backslash-separated on Windows
```

On Windows `str(PurePath)` yields backslash-separated paths (`sub\file.py`), but `git check-ignore --stdin` emits forward-slash paths on stdout. The membership test at line 177 (`[p for p, rel in zip(paths, rels) if rel not in ignored]`) therefore never matches on Windows, so gitignored files are **not** dropped from the `rglob` fallback path in `_get_all_files` (line 193). The secrets scan then walks excluded/generated artifacts, risking false-positive findings. The `.as_posix()` normalization is the same construct already used throughout the render path (e.g. `render_agent_surfaces.py:311,316,320,324`).

## Requirements

1. `render_agent_surfaces.write_text` must write byte-identical LF output on every host, matching `render_platform_surfaces.write_text` — no `os.linesep` translation of embedded `"\n"` on native Windows.
2. `_filter_gitignored` must compare relative paths against `git check-ignore` output using forward-slash (posix) separators so gitignored files are correctly dropped from the `rglob` fallback on Windows.
3. Both changes are isolated one-liners; no signature, contract, or call-site changes.
4. Tests must assert LF-only output for the rendered agent surfaces and posix-path gitignore filtering, so a regression to the default newline / backslash behavior fails on any host.

## Scope

**Problem statement:** Two Windows-portability one-liners were missed by the 1p9hm theme: the agent-surface render helper omits `newline=""` (F14), so the four rendered agent surfaces gain CRLF on native Windows; and the secrets-scan gitignore filter compares OS-separator relpaths against git's forward-slash output (F18), so gitignored files are never dropped on Windows. Both have an in-tree sibling that already does it correctly.

**In scope:**

- Change `render_agent_surfaces.write_text` (`.wavefoundry/framework/scripts/render_agent_surfaces.py:295-297`) to open with `path.open("w", encoding="utf-8", newline="")`, matching `render_platform_surfaces.write_text`.
- Change the relpath append in `_filter_gitignored` (`.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py:160`) from `str(p.relative_to(root))` to `p.relative_to(root).as_posix()`.
- Add/extend unit tests asserting (a) LF-only bytes in the four rendered agent surfaces and (b) that a gitignored file is filtered out when relpaths are normalized to posix.

**Out of scope:**

- The other in-place file patchers in `render_agent_surfaces.py` that use `path.write_text(..., encoding="utf-8")` on already-authored files (`patch_root_bridge` ~:290, the tier-2 CLAUDE.md marker upsert ~:357, `cursor_ctx` ~:376, thin-pointer patchers). These modify existing operator-authored files with their own on-disk line endings and are not named by F14; do not touch them in this change.
- Any change to how the four surface source strings are authored, to git-attributes, or to the render pipeline's structure.
- Any change to secrets-scan detection logic, the `git ls-files` primary path, or the allowlist/binary-skip filters.

## Acceptance Criteria

- [x] AC-1: `render_agent_surfaces.write_text` opens the target with `path.open("w", encoding="utf-8", newline="")` and writes `content` verbatim (no `path.write_text` default-newline call remains in that helper). — `render_agent_surfaces.py:295-304` now uses `with path.open("w", encoding="utf-8", newline="") as handle: handle.write(content)`; no `path.write_text` remains in the helper.
- [x] AC-2: A test renders the agent surfaces (or calls `write_text` with content containing `"\n"`) and asserts the written bytes contain no `\r\n` (LF-only), so the assertion holds on any host regardless of `os.linesep`. — `AgentSurfaceNewlineTests.test_rendered_agent_surfaces_are_lf_only` asserts no `\r\n` bytes in the four generated surfaces; `test_write_text_uses_newline_empty_and_writes_verbatim` captures the `newline=""` kwarg (durable non-Windows proof) + LF-only bytes.
- [x] AC-3: `_filter_gitignored` builds its relpath list with `p.relative_to(root).as_posix()` (forward-slash separators) at the line that previously used `str(...)`. — `secrets_validators.py:160` now `rels.append(p.relative_to(root).as_posix())`.
- [x] AC-4: A test drives `_filter_gitignored` (or the `_get_all_files` rglob fallback) with a gitignored path and asserts it is dropped when git emits forward-slash paths, verifying the membership test matches on posix-normalized relpaths. — `test_filter_gitignored_matches_posix_relpaths_on_windows_seps` simulates a native-Windows path (`PureWindowsPath`) so the nested gitignored path is dropped only when relpaths are posix-normalized; fails on any host on a revert.
- [x] AC-5: `python3 .wavefoundry/framework/scripts/run_tests.py` passes with the new/updated tests; no unrelated test regresses. — Deferred to the coordinator's central verification pass (AEG ws-3); the full suite is not run per-implementer (shared working tree). Targeted new tests pass (3/3): `AgentSurfaceNewlineTests` + `test_filter_gitignored_matches_posix_relpaths_on_windows_seps`.

## Tasks

- [x] Read `render_platform_surfaces.write_text` (`.wavefoundry/framework/scripts/render_platform_surfaces.py:69-78`) to mirror the exact `newline=""` construct and intent. — Mirrored the `with path.open("w", encoding="utf-8", newline="") as handle: handle.write(content)` construct and inline rationale.
- [x] Edit `render_agent_surfaces.write_text` (`.wavefoundry/framework/scripts/render_agent_surfaces.py:295-297`) to use `path.open("w", encoding="utf-8", newline="")` and `handle.write(content)`.
- [x] Edit `_filter_gitignored` (`.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py:160`) to append `p.relative_to(root).as_posix()`.
- [x] Add/extend a unit test for the agent-surface render asserting LF-only output (no `\r\n`) in the written bytes. — `AgentSurfaceNewlineTests` in `tests/test_render_agent_surfaces.py`.
- [x] Add/extend a unit test for `_filter_gitignored` asserting a gitignored path is dropped with posix-normalized relpaths. — `test_filter_gitignored_matches_posix_relpaths_on_windows_seps` in `tests/test_secrets_validators.py`.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py`; clean any stray `__pycache__` per Framework Script Hygiene. — Deferred to coordinator central pass (AEG ws-3); per-implementer full-suite runs are skipped in the shared tree. Targeted new tests pass (3/3, `python3 -B`, no bytecode written).
- [x] Update Change Status and AC/task checkboxes in real time as each item completes.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ws-1 render-agent-surfaces-lf | implementer | — | F14: `render_agent_surfaces.py:295-297` → `path.open("w", encoding="utf-8", newline="")`; add LF-only render test. Independent file. |
| ws-2 gitignore-posix-relpath | implementer | — | F18: `secrets_validators.py:160` → `.as_posix()`; add posix-path gitignore filter test. Independent file. |
| ws-3 suite-verify | implementer | ws-1, ws-2 | Run `run_tests.py`, confirm no regressions, clean `__pycache__`. |


## Serialization Points

- None between ws-1 and ws-2 — they touch disjoint files (`render_agent_surfaces.py` vs `wave_lint_lib/secrets_validators.py`) and can proceed in parallel. ws-3 (full-suite verification) is the only join point and runs after both land.

## Affected Architecture Docs

N/A — both edits are one-line corrections confined to a single function each, with no boundary, control-flow, data-flow, or verification-architecture change. The render pipeline and secrets-scan interfaces are unchanged.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| ---- | ---- | ---- |
| AC-1 | required | Core F14 fix; without it the four agent surfaces stay CRLF-on-Windows. |
| AC-2 | required | Regression guard for F14; the bug is host-conditional so an explicit LF assertion is the only durable proof on non-Windows CI. |
| AC-3 | required | Core F18 fix; without it gitignored files are never dropped on Windows. |
| AC-4 | required | Regression guard for F18; proves the membership test matches posix-normalized relpaths. |
| AC-5 | important | Confirms no collateral regression; the two edits are trivially isolated so full-suite failure would indicate an unrelated pre-existing issue. |


## Progress Log


| Date | Update | Evidence |
| ---- | ---- | ---- |
| 2026-07-02 | Scoped from Windows audit `wf_eab9a03d-004` + comparison `wf_33ca6bdb-757`. F14/F18 are the two low-severity one-line stragglers the 1p9hm theme's round-2 missed. Verified both cited sites against the current tree (1p9hn applied): F14 at `render_agent_surfaces.py:297` (helper def `:295`), sibling fix at `render_platform_surfaces.py:69-78` (wave 1p7tz); F18 at `secrets_validators.py:160`, membership test `:177`. | This change doc; `render_agent_surfaces.py:295-297`, `render_platform_surfaces.py:69-78`, `secrets_validators.py:147-177` |
| 2026-07-02 | Implemented both fixes. F14: `render_agent_surfaces.write_text` now opens with `newline=""` and `handle.write(content)` (mirrors the 1p7tz sibling) + inline rationale. F18: `_filter_gitignored` relpath now `p.relative_to(root).as_posix()`. Added `AgentSurfaceNewlineTests` (LF-only render bytes + `newline=""` capture) and `test_filter_gitignored_matches_posix_relpaths_on_windows_seps` (native-Windows path simulated via `PureWindowsPath`). Targeted tests: 3/3 OK. AC-5 full-suite deferred to coordinator central pass (ws-3). | `render_agent_surfaces.py:295-304`, `secrets_validators.py:157-166`, `tests/test_render_agent_surfaces.py`, `tests/test_secrets_validators.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | ---- | ---- | ---- |
| 2026-07-02 | Fix F14 by switching `write_text` to `path.open("w", ..., newline="")` rather than pre-normalizing the source strings. | Mirrors the already-landed sibling `render_platform_surfaces.write_text` (wave 1p7tz) exactly; single source of truth for the "verbatim embedded terminators" pattern. | Normalize each surface string; re-write with `.replace("\r\n","\n")` — rejected as divergent from the sibling and easy to regress. |
| 2026-07-02 | Fix F18 with `.as_posix()` rather than normalizing git's output to OS separators. | Git speaks forward-slash on stdin/stdout by contract; normalizing the local relpaths to posix is the same construct the render path already uses and is stable across hosts. | Split/rejoin git output on `os.sep` — rejected as fragile and backwards (git is the fixed contract). |
| 2026-07-02 | Keep the other in-place `path.write_text(...)` patchers in `render_agent_surfaces.py` out of scope. | F14 names only the `write_text` render helper for freshly generated surfaces; the patchers modify existing operator-authored files whose on-disk line endings should be preserved. | Blanket-apply `newline=""` to every writer — rejected as scope expansion beyond the assigned finding. |


## Risks


| Risk | Mitigation |
| ---- | ---- |
| `newline=""` change alters bytes of an already-authored surface unexpectedly. | The four surfaces are freshly generated from LF source strings, so `newline=""` produces identical bytes on POSIX and corrects only the Windows CRLF regression; AC-2 asserts LF-only bytes. |
| `.as_posix()` changes behavior for paths already forward-slash (POSIX). | On POSIX `str()` and `.as_posix()` are identical, so the change is a no-op there and only corrects Windows; AC-4 asserts filtering works with posix relpaths. |
| Regression escapes because CI is not native Windows. | Tests assert the host-independent invariants directly (no `\r\n` bytes; posix-relpath membership), so they fail on any host if the construct regresses, not only on Windows. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
