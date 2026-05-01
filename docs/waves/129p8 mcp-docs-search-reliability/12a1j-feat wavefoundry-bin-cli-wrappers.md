# Wavefoundry `bin/` CLI wrappers + MCP-primary routing

Change ID: `12a1j-feat wavefoundry-bin-cli-wrappers`
Wave: `129p8 mcp-docs-search-reliability`

Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-04-30

## Core intent

1. **Framework-owned executables**  
   Ship docs (and future) **CLI entrypoints** under **`.wavefoundry/bin/`** so the repo root is not the authority for framework tooling. Wrappers may be shell, shebang Python, or **future native binaries**—`bin/` is the stable contract directory.

2. **MCP remains the primary agent surface**  
   Agent-facing guidance continues to prefer **`wave_validate`**, **`wave_garden`**, and related MCP tools. **`.wavefoundry/bin/*`** is for **hooks, CI, emergency shell**, and operators who are not using MCP—not the default instruction path for agents.

3. **Compatibility (policy choice)**  
   Wavefoundry self-host chose **(B)**: **no repo-root** `./docs-lint` / `./docs-gardener` shims — hooks, CI, and docs reference **`.wavefoundry/bin/docs-lint`** and **`.wavefoundry/bin/docs-gardener`** only. Target repositories may still use optional root forwarders during migration; seeds describe **bin/** as canonical.

## Rationale

Previously, **`docs-lint`**-style entrypoints often lived at the **repository root** as thin wrappers around **`.wavefoundry/framework/scripts/docs_lint.py`** and **`docs_gardener.py`**, which blurred ownership. Hooks and Python call sites used **`REPO_ROOT / "docs-lint"`**, coupling behavior to a project-local-looking path.

Moving canonical launchers to **`.wavefoundry/bin/`**:

- Makes **ownership and packaging** obvious (install/upgrade can manage `bin/` as a set).
- Leaves room for **non-Python** tools next to the same wrappers without another migration.
- Aligns with the stated direction: **MCP for agents**, **wrappers for non-MCP execution contexts**.

This plan is **orthogonal** to **`12a17-feat multi-host-mcp-registration`** (MCP JSON registration per host) but may **touch the same files** (`render_platform_surfaces.py`); **serialize** or single-owner those edits.

## Deeper reach: canonical seeds (bootstrap, not just this repo)

Framework seeds on **every target repository** that runs **Init / Upgrade / mechanical enforcement / migration** must converge on **`.wavefoundry/bin/docs-lint`** / **`.wavefoundry/bin/docs-gardener`** (and MCP-first agent guidance), not repo-root `./docs-lint` as the only contract. Hook tables and install seeds (**`050`**, **`010`**, **`080`**, **`160`**, **`250`**, **`040`**, **`170` / `190`**, **`002`**, **`008`**, **`220`**, …) carry that wording.

Implications:

- **Implementation is incomplete** without updating **canonical seeds** under **`.wavefoundry/framework/seeds/`** so new repos get **`.wavefoundry/bin/`** and **upgrade/migration checklists** reference the **bin/** contract (optional legacy root shims called out only where still supported).
- **`render_platform_surfaces.py`** is the **runtime** that materializes hooks from seed-shaped contracts; seeds and renderer must **move together** or freshly installed repos drift.
- **Self-hosted `docs/`** may mirror seed wording after **refresh**; still treat **seeds as source of truth** for framework behavior.
- All seed edits require **`seed_edit_allowed`** per project policy; schedule a **single guarded window** for the seed sweep to avoid partial bootstrap states.

## Requirements

1. **Create `.wavefoundry/bin/`** (directory layout documented in `AGENTS.md` and framework README). Add **`docs-lint`** and **`docs-gardener`** (or namespaced `wavefoundry-docs-lint` only if avoiding PATH collisions—default keep short names inside `bin/`).

2. **Wrapper behavior**  
   Each launcher must resolve **project root** reliably (repo containing `docs/workflow-config.json` or equivalent existing discovery) and `exec` the current Python backends under `.wavefoundry/framework/scripts/` with the **same argv semantics** as today’s root scripts.

3. **Update all in-repo callers** that reference `REPO_ROOT / "docs-lint"` or `REPO_ROOT / "docs-gardener"` to use **`.wavefoundry/bin/...`** (or a shared helper constant), including:

   - `render_platform_surfaces.py` (framework plan gate / embedded strings).
   - `.cursor/hooks/*.py`, `.github/hooks/*.py`, generated hook **sources** inside `render_platform_surfaces.py` (so **re-render** produces correct paths).
   - Any other `grep` hits under `.wavefoundry/framework/scripts/` and `docs/`.

4. **Root shims (compatibility)**  
   **Policy (B) for this repository:** repo-root `docs-lint` / `docs-gardener` are **not** shipped; all callers use **`.wavefoundry/bin/...`**. Other targets may keep temporary root forwarders per their own upgrade notes.

5. **Documentation**  
   - **`docs/architecture/data-and-control-flow.md`**: update the “wrapper calls `docs_lint.py`” diagram to show **`.wavefoundry/bin/docs-lint` → `docs_lint.py`**.  
   - **`AGENTS.md`**, **`docs/contributing/build-and-verification.md`**, **`docs/prompts/*`**: state **MCP-first** for agents; document **`.wavefoundry/bin/`** as canonical CLI for hooks/CI; root shims status per policy.  
   - Align with **`1297t-feat mcp-change-creation-coverage`** intent (MCP first, CLI fallback labeled)—this change **relocates** fallback paths, not removes MCP.

6. **Canonical seeds (required)**  
   Update **all** seed-owned bootstrap / upgrade / enforcement / migration text that names **`./docs-lint`**, **`./docs-gardener`**, or “root wrappers” so it matches **bin/** as canonical (and optional legacy root shims only where a target still carries them).

   - **Create / reconcile** steps must install or point to **`.wavefoundry/bin/`**.
   - **Init / upgrade gates** must require a passing docs gate: **MCP `wave_validate` succeeds** when agents use MCP, **or** **`.wavefoundry/bin/docs-lint` exit 0** for CLI-only verification — wording must be unambiguous.
   - **MCP-first**: where seeds give **agent execution** steps, prefer **`wave_validate` / `wave_garden`** with **`.wavefoundry/bin/...`** as labeled hook/CLI fallback (align with **`1297t`** where already planned).
   - Inventory at minimum: **`010`**, **`040`**, **`050`**, **`080`**, **`160`**, **`170`**, **`190`**, **`220`**, **`250`**, **`002`**, **`008`** (re-grep during implementation for stragglers).

7. **Packaging / install artifacts**  
   Ensure **`Package Wavefoundry`**, **`build_pack.py`**, or unpack docs include **`.wavefoundry/bin/`** when the pack is expected to be self-sufficient on a virgin tree.

8. **Tests**  
   Add or extend tests so hook render output (or a fixture) expects **`.wavefoundry/bin/docs-lint`**; run **`run_tests.py`** and **`.wavefoundry/bin/docs-lint`**.

## Scope

**In scope:**

- New **`.wavefoundry/bin/`** launchers; caller updates; docs and architecture updates; hook **generator** changes in `render_platform_surfaces.py` (no repo-root shims in self-host).
- **Canonical seed updates** and any **regenerated self-hosted `docs/`** surfaces that must stay aligned with seeds after **Refresh wavefoundry** (or equivalent).

**Out of scope:**

- Rewriting **`docs_lint.py` / `docs_gardener.py`** logic beyond path/bootstrap fixes required for the move.
- Making hooks invoke MCP instead of subprocess (explicitly deferred—large separate effort).
- Rewriting unrelated seed content beyond paths, gates, and MCP-vs-CLI routing touched by this contract.

## Acceptance Criteria

- [x] **`.wavefoundry/bin/docs-lint`** and **`.wavefoundry/bin/docs-gardener`** exist and behave equivalently to pre-change root wrappers (same exit codes for representative runs).
- [x] **Grep-clean** for stale `REPO_ROOT / "docs-lint"` patterns **or** documented exceptions (legacy targets only).
- [x] **Regenerated** Cursor / Copilot / Windsurf hook entrypoints (via `render_platform_surfaces`) reference **`.wavefoundry/bin/`** (or repo-relative path that resolves from hook `cwd`).
- [x] **`AGENTS.md`** and **`build-and-verification.md`** describe **MCP-primary** and **bin/** CLI for non-MCP contexts.
- [x] **Seeds:** every identified seed in §Deeper reach is updated under **`seed_edit_allowed`**; grep over **`.wavefoundry/framework/seeds/`** shows **bin/** as the primary CLI contract for new work.
- [x] **`python3 .wavefoundry/framework/scripts/run_tests.py`** and **`.wavefoundry/bin/docs-lint`** pass.
- [x] **`.wavefoundry/bin/docs-lint`** passes after `docs/` edits (post-edit hook contract).

## Tasks

1. Inventory: `rg` for `docs-lint`, `docs-gardener`, `docs_lint.py` references in hooks, scripts, and docs.
2. Add **`.wavefoundry/bin/`** scripts (portable bash; consider **`.cmd`** siblings only if Windows hook story requires—defer if YAGNI).
3. Update **Python** string callers and **hook generator** templates in `render_platform_surfaces.py`; run **`render_platform_surfaces`** on Wavefoundry and commit regenerated hooks if tracked.
4. Remove repo-root shims in self-host (policy B); ensure **`.wavefoundry/bin/`** is the only required CLI path here.
5. Docs + architecture diagram + `framework/README.md` “root wrappers” wording.
6. **Seed sweep (guarded):** enable **`seed_edit_allowed`**, apply the §Requirements seed list, run **`docs-lint`** / **`render_platform_surfaces`** / tests as needed, then **restore** the guard file per policy.
7. **Self-hosted docs refresh** if required so **`docs/prompts/`** and peers do not contradict seeds after the seed pass (may be part of normal refresh workflow rather than this PR—record which).
8. Verify **Package Wavefoundry** / **`build_pack`** include **`.wavefoundry/bin/`** in the shipped tree and document unpack expectations.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| bin scripts + caller migration | implementer | — | Touch `render_platform_surfaces.py` |
| hook regen + tests | implementer | scripts land | |
| seeds + docs | implementer | bin path + hook templates frozen | **`seed_edit_allowed`** window; MCP-first + `bin/` contract |

## Serialization Points

- **`render_platform_surfaces.py`**: coordinate with **`12a17-feat multi-host-mcp-registration`** and any open **`12a0c-debt framework-script-code-quality`** work.
- **Seeds before wide `docs/` churn:** land seed + renderer agreement first so **Refresh** and target **Init** do not publish contradictory wrapper guidance.

## Affected Architecture Docs

- **`docs/architecture/data-and-control-flow.md`** — required update for wrapper path.
- **`docs/architecture/current-state.md`** — optional one-line if it lists operator scripts.

## Relationship to other plans

- **`1297t-feat mcp-change-creation-coverage`**: agent instructions MCP-first; **this change relocates CLI fallback** to **`.wavefoundry/bin/`**; cross-linked in plan environment note.
- **`12a17-feat multi-host-mcp-registration`**: same render module; **serialize**.

## AC Priority

(Populate at Prepare wave.)

## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-04-30 | Plan authored | Initial draft under `docs/plans/` |
| 2026-04-30 | Expanded scope: **canonical seeds** drive bootstrap/upgrade/migration; deeper blast radius than self-host hooks only | Plan body |
| 2026-04-30 | Admitted to wave `129p8 mcp-docs-search-reliability`; change doc under wave folder | `wave.md` Changes |
| 2026-04-30 | Implementation complete: `.wavefoundry/bin/` launchers created; repo-root shims removed (policy B); hooks and verification use `bin/`; seed sweep; docs and prompts updated; `render_platform_surfaces.py` emits bin launchers; tests and docs-lint clean | All ACs checked |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-04-30 | Canonical launchers under **`.wavefoundry/bin/`** | Clear ownership; room for non-Python binaries | Flat `.wavefoundry/` root |
| 2026-04-30 | **Policy B** for Wavefoundry self-host: **no** repo-root `./docs-lint` / `./docs-gardener`; **bin/** only | Clear ownership; matches hooks and CI | Optional root forwarders only in legacy target repos during migration |

## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Hook `cwd` assumes repo root | Use repo-relative path `.wavefoundry/bin/docs-lint` from `REPO_ROOT`; test hook render fixtures |
| Windows hook `.cmd` paths | Confirm Cursor/Copilot cmd launchers; add `.cmd` shims in `bin/` if required |
| Drift vs packaged framework zip | Packaging checklist includes `bin/` |
| **Target repos** stuck mid-upgrade if only half the seed set ships | Ship seeds + pack together; document “upgrade framework then re-run render” in **`160`** |
| **Partial seed edit** (guard left on, or only some seeds updated) | Single **`seed_edit_allowed`** session + grep checklist |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
