# upgrade_wavefoundry.py passes --root to render_platform_surfaces.py, which only accepts --repo-root

Change ID: `12r8f-bug upgrade-script-root-arg-mismatch`
Change Status: `implemented`
Owner: wave-coordinator
Status: active
Last verified: 2026-05-19
Wave: 12r09 automated-upgrade

## Rationale

`upgrade_wavefoundry.py` Phase 1 calls `render_platform_surfaces.py` with `--root`, but that script only registers `--repo-root` in its `argparse` setup. The mismatch causes an immediate exit-code-2 failure on every upgrade run in pack `2026-05-19c`, blocking the entire upgrade workflow before any rendering, pruning, or indexing can occur.

A secondary latent bug exists in Phase 3 (docs-gate fallback path): the same upgrade script passes `--root` to `docs_gardener.py` and `docs_lint.py` when the bin launchers are absent, but neither of those scripts registers `--root`. They rely on CWD, which `subprocess.run` already sets correctly via `cwd=str(root)`.

## Requirements

1. `phase_surface_rendering()` must call `render_platform_surfaces.py` with `--repo-root`, not `--root`.
2. The Phase 3 fallback path must not pass `--root` to `docs_gardener.py` or `docs_lint.py`, since neither script registers that argument; CWD (already set) is sufficient.

## Scope

**Problem statement:** Argument name mismatch between caller and callee — shipped in the same pack with no runtime guard.

**In scope:**

- `upgrade_wavefoundry.py` line 725: `--root` → `--repo-root` for `render_platform_surfaces.py`
- `upgrade_wavefoundry.py` line 774: remove `"--root", str(root)` from the docs-gate fallback `cmd` (both `docs_gardener.py` and `docs_lint.py` use CWD; passing `--root` would trigger "unrecognized arguments" if the fallback path ever runs)

**Out of scope:**

- `setup_index.py` at lines 798/808: correctly accepts `--root` — no change needed
- `upgrade_wavefoundry.py` `main()` at line 898: this is the upgrade script's own `--root` CLI arg — correct as-is
- `render_platform_surfaces.py` argparse: `--repo-root` is the correct canonical name — no alias needed

## Acceptance Criteria

- AC-1: Running `python3 upgrade_wavefoundry.py --root <repo>` completes Phase 1 without "unrecognized arguments" error.
- AC-2: `phase_surface_rendering()` subprocess call uses `--repo-root`.
- AC-3: `phase_docs_gate()` fallback subprocess call does not pass `--root` or any unrecognized argument to `docs_gardener.py` / `docs_lint.py`.
- AC-4: Framework tests pass.

## Tasks

- [x] Fix line 725: `"--root"` → `"--repo-root"` in `phase_surface_rendering()` subprocess call
- [ ] Fix line 774: remove `"--root", str(root)` from `phase_docs_gate()` fallback `cmd`
- [ ] Run framework tests

## Agent Execution Graph

| Workstream   | Owner            | Depends On | Notes |
| ------------ | ---------------- | ---------- | ----- |
| script-fix   | wave-coordinator | —          | lines 725 and 774 in upgrade_wavefoundry.py |
| test-verify  | wave-coordinator | script-fix | run_tests.py |

## Serialization Points

- Both edits are in the same file; apply sequentially.

## Affected Architecture Docs

N/A — single-script bug fix with no boundary or flow impact.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | This is the blocker — upgrade must complete Phase 1 |
| AC-2 | required  | Direct implementation of AC-1 |
| AC-3 | required  | Latent crash in fallback path; same root cause |
| AC-4 | required  | Standard gate for all framework script changes |

## Progress Log

| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-05-19 | Line 725 fixed by operator: `--root` → `--repo-root` | Confirmed in upgrade_wavefoundry.py |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-19 | Fix caller (upgrade script), not callee (renderer) | `--repo-root` is already consistent with the renderer's convention; adding an alias would spread the inconsistency | Add `--root` alias to render_platform_surfaces.py |
| 2026-05-19 | Remove `--root` from docs-gate fallback, not add the arg to those scripts | Both scripts correctly use CWD; no arg needed | Add `--root` to docs_gardener.py and docs_lint.py |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Other upgrade script subprocess calls may also use wrong arg names | Audited all `--root` calls in upgrade_wavefoundry.py: setup_index.py (✓ correct), docs-gate fallback (latent bug — fixed here), main() argparse (own arg — correct) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
