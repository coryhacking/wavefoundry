# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-19

wave-id: `12rbc mcp-impl-hot-reload`
Title: MCP Impl Hot Reload

## Objective

Split `server.py` into a thin runner (`server.py`) and a hot-swappable implementation module (`server_impl.py`) so the `wave_upgrade` flow can reload MCP tool logic without restarting the server.

## Changes

Change ID: `12rb9-enh mcp-impl-hot-reload`
Change Status: `admitted`

Completed At: 2026-05-19

## Wave Summary

**12rb9** delivers MCP implementation hot reload via `server_impl.py` and `wave_mcp_reload`. Agent-prompt harness work is in wave **`12rnv agent-prompt-harness`** — not in this wave.

## Participants

| Lane | Phase | Notes |
| ---- | ----- | ----- |
| `code-reviewer` | implementation + delivery | Framework scripts (`server.py`, `server_impl.py`, `upgrade_wavefoundry.py`) |
| `qa-reviewer` | delivery | AC priority table on change doc; full `run_tests.py` |
| `architecture-reviewer` | delivery | MCP module split; `ImplHandler` boundary |
| `security-reviewer` | delivery | New `wave_mcp_reload` tool; reload closes index/cache |
| `performance-reviewer` | delivery (rotating council seat) | Index/cache lifecycle on reload |
| `reality-checker` | readiness + delivery | Assumptions on reload semantics |
| `council-moderator` | readiness + delivery | Council synthesis |
| `product-owner` | readiness | N/A — internal framework tooling |

## Journal Watchpoints

- **Watchpoint:** `framework_edit_allowed` gate required for all edits to `server.py` and `server_impl.py` — open before editing, close immediately after.
- **Watchpoint:** `server.py` must remain the sole entry point after the split — `.mcp.json` and all launch paths must be unchanged.
- **Watchpoint:** LanceDB double-open: `ImplHandler.close()` must complete before `build_handler()` is called during hot reload.

## Review checkpoints

### Prepare wave — readiness verdict (2026-05-19)

**Verdict:** Ready for implementation.

- Admitted change `12rb9-enh mcp-impl-hot-reload` is wave-owned under `docs/waves/12rbc mcp-impl-hot-reload/` with complete Rationale, Requirements, Scope, ACs, tasks, and AC priority.
- Required delivery lanes selected (see Participants).
- `product-owner: N/A — internal framework tooling; no external UX or API contract change beyond existing MCP surface.`
- **Wave Council readiness:** fixed seats + rotating `performance-reviewer`; signoff recorded below.
- **Risks accepted for implementation:** new tools in upgraded sessions still require client reconnect (documented in change Decision Log).

### Wave Council — readiness synthesis (2026-05-19)

**Seat roster:** architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, performance-reviewer (rotating), council-moderator.

**Agreement:** Scope is bounded to server split + hot reload + upgrade hook; no transport or `.mcp.json` changes. Serialization point (`server_impl` before stub rewrite) is correct. AC-6 (close before reopen) is the critical runtime invariant.

**Material disagreements:** None.

**Council verdict:** Approved for implementation.

### Pre-implementation review — Wave Council (2026-05-18)

**Phase:** readiness (code-grounded pass before first edit)  
**Briefing packet:** `12rb9-enh` change doc, `wave.md`, `server.py` `build_server` (lines 8928+), `WaveIndex` / `McpRepoCache`, `_script_cache`, `wave_upgrade_response` subprocess pattern, `upgrade_wavefoundry.py` cleanup summary.

**Seat roster (fixed):** `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker`, `red-team`  
**Rotating seat:** `performance-reviewer` (index/cache lifecycle on reload)

| Seat | Verdict | Key finding |
| ---- | ------- | ----------- |
| `architecture-reviewer` | **approved-with-notes** | Split boundary is sound (`server.py` transport + registrations, `server_impl.py` logic). **Note:** AC-3 should trigger reload **in-process** from `wave_upgrade_response` after a successful `cleanup` subprocess — not an MCP stdio client inside `upgrade_wavefoundry.py` (subprocess has no attachment to the live server). `server.py` must **re-export** symbols tests import today (`WaveIndex`, `*_response`, helpers) or AC-4 “tests pass without modification” will fail. |
| `security-reviewer` | **approved-with-notes** | `wave_mcp_reload` is a **mutating** tool (reloads code + drops caches). Register with `_MUTATING_TOOL`, not read-only. No new trust boundary if reload only loads framework scripts under configured root and does not accept arbitrary paths. Document that reload does not add new tools to an existing session (accepted limitation). |
| `qa-reviewer` | **needs-revision** (resolved in change doc this pass) | AC-2/AC-6 need **behavioral** tests, not only registered-tool set membership. Require: (1) post-reload smoke call proves new code path; (2) reload after index open does not double-open LanceDB; (3) `wave_upgrade(phase=cleanup)` path invokes reload when server is live. Update Tasks before implement. |
| `reality-checker` | **approved-with-notes** | **Assumption:** `ImplHandler.close()` exists — **false today**; must be implemented. **Assumption:** `_script_cache` clears on reload — **not in change doc**; stale `_load_script` modules would otherwise survive reload. **Assumption:** ~10K-line extract is mechanical — **partially false**; 61 tool stubs must delegate without closing over `index`/`cache`. |
| `red-team` | **approved-with-notes** | Failure modes: reload mid-request (serialize via tool handler lock); reload while background model download running (`_start_background_model_downloads`); partial reload after `importlib.reload` exception leaves server in broken state — return `ok: false` and keep old handler until success. |
| `performance-reviewer` | **approved (advisory)** | Reload is rare (upgrade only). Cost is full handler rebuild + cache cold start; acceptable. Clear `_script_cache` and invalidate `McpRepoCache` on reload to avoid stale indexer modules. |

**Material disagreements:** `qa-reviewer` initially blocked on missing behavioral AC tests vs prior readiness “approved.” **Resolved:** change doc updated with explicit test tasks and AC-3 integration correction; council does not require re-Prepare.

**Council verdict:** **Approved for implementation** with mandatory pre-edit doc alignment (done in `12rb9` Tasks / Requirements / Decision Log).

### Wave Council — delivery review (2026-05-20)

**Phase:** delivery  
**Seat roster (fixed):** architecture-reviewer, security-reviewer, qa-reviewer, reality-checker  
**Rotating seat:** performance-reviewer

| Seat | Verdict | Key finding |
| ---- | ------- | ----------- |
| `code-reviewer` | **approved-with-notes** | `_handler_lock` declared but never used (dead code, advisory). `perform_mcp_reload` captures `old` before lock (acceptable given stdio single-threading). All resource closures correctly use `get_handler().root` after NameError fixes. `wave_mcp_reload` registered `_MUTATING_TOOL`. ✓ |
| `security-reviewer` | **approved** | No path injection; `_MUTATING_TOOL` correct; `_ensure_no_extra_args` guard present; `_reload_lock` prevents concurrent reload. ✓ |
| `qa-reviewer` | **needs-revision** | AC-3 behavioral test missing: no test verifies `wave_upgrade(phase="cleanup", mode="apply")` invokes `perform_mcp_reload`. AC-6 behavioral test missing: no test verifies `ImplHandler.close()` nulls Lance handles before `build_handler`. Both required by pre-implementation council action item 4. All other ACs have coverage. |
| `architecture-reviewer` | **approved-with-notes** | Split boundary sound; `ImplHandler` dispatch path correct; stubs don't close over `index`/`cache`. Advisory: `_orig_server_identity` monkey-patch pattern is subtle on reload (re-executes correctly, but worth a comment). ✓ |
| `reality-checker` | **approved** | All three previously-false assumptions now true: `ImplHandler.close()` exists; `_script_cache.clear()` on reload; AC-3 wired in-process from `wave_upgrade_response`. Graceful degradation when `server` not in `sys.modules`. ✓ |
| `performance-reviewer` | **approved** | `_script_cache.clear()` prevents stale modules; Lance handles nulled on close; background downloads stopped; no double-open. ✓ |

**Material disagreements:** `qa-reviewer` blocks on two missing behavioral tests. All other seats approved or advisory-only.

**Resolution:** Wave returns to implementation for the two tests. No code changes; tests only.

**Council verdict: approved — AC-3 and AC-6 behavioral tests added (3 new tests); 1482/1482 green. Ready for operator signoff and close.**

### Wave Council — advisory-fix re-review (2026-05-20)

**Scope:** `perform_mcp_reload` TOCTOU fix + close-warning diagnostics; `server_identity` monkey-patch removed; `register_mcp_surface` blank line; `_handler_lock` and null-check removals. No AC-scope changes.

| Seat | Verdict | Key finding |
| ---- | ------- | ----------- |
| `code-reviewer` | **approved** | `_get_handler()` now inside lock — handler read and reload fully atomic. `close_warnings` propagated on both success and failure paths. `server_identity` single definition; forward refs to `_runner_version`/`version_payload` correct at call time. Advisory: `Callable` import in `server.py` unused. |
| `security-reviewer` | **approved** | `close_warnings` uses `str(exc)` on internal exception — no user-controlled input. Lock fully serializes handler lifecycle. ✓ |
| `qa-reviewer` | **approved-with-advisory** | 1482/1482 green; AC-3 and AC-6 behavioral tests pass. New `close_warnings` path (when `close()` raises) not tested — advisory only, non-blocking graceful-degradation path. |
| `architecture-reviewer` | **approved** | No boundary changes. `old.root` (stdlib `Path`) survives reload correctly. Fallback `_set_handler(old)` on build failure restores a closed handler — acceptable trade-off vs. LanceDB double-open. ✓ |

**Material disagreements:** None.

**Council verdict: approved. All prior advisory items resolved. Ready for operator signoff and close.**

**Action items for implementer:**

1. Open `framework_edit_allowed`; implement `ImplHandler.close()` before `build_handler()`.
2. On reload: `_script_cache.clear()`, `McpRepoCache.invalidate()` or replace instance, tear down `WaveIndex` Lance handles / reranker as needed.
3. Wire AC-3 in `wave_upgrade_response` after successful cleanup subprocess (and update operator summary line in `upgrade_wavefoundry.py`).
4. Add `test_hot_reload_*` (or extend `test_server_tools`) for AC-2 and AC-6.
5. Add `wave_mcp_reload` to `_help_catalog()` `core_tools` and `reload_mcp` workflow (requirement 10 / AC-8).
6. `wave_mcp_reload` and `wave_server_info` return `framework_version`, `server_runner_version`, `server_impl_version`, `impl_matches_disk` (requirement 9 / AC-7).

**Implementation complete (2026-05-20):** Items 1–3, 5–6 done. Item 4 partially done (AC-2 `test_perform_mcp_reload_returns_versions` added). AC-3 and AC-6 behavioral tests still missing — see delivery review below.

## Review Evidence

- wave-council-readiness: approved (moderator: council-moderator; seats aligned on scope, serialization, and AC-6 LanceDB close-before-reload; rotating seat: performance-reviewer)
- wave-council-pre-implementation: approved-with-notes 2026-05-18 (code-grounded pass; fixed seats + performance-reviewer; qa-reviewer test gaps resolved in change doc; AC-3 in-process reload path)
- wave-council-delivery: approved 2026-05-20 (all seats aligned; two missing behavioral tests added and passing — AC-3 cleanup→reload, AC-6 close-before-rebuild; 1482/1482 green)
- wave-council-delivery-repass: approved 2026-05-20 (advisory-fix pass: TOCTOU resolved, close errors surfaced as diagnostics, monkey-patch removed, dead import noted; all seats approved; 1482/1482 green)
- operator-signoff: approved 2026-05-20 (upgrade flow tested end-to-end; `impl_matches_disk` confirmed post-reload; package 2026-05-19h shipped)

## Dependencies

- No external wave dependencies.
- Related (separate wave): `12rnv agent-prompt-harness` for security-review seed generalization after hot reload ships.
