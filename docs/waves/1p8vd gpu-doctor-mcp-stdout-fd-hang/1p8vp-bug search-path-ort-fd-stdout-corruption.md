# Search-path ORT cold-load corrupts MCP stdout — isolate native fd 1 from the JSON-RPC channel at startup

Change ID: `1p8vp-bug search-path-ort-fd-stdout-corruption`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-29
Wave: `1p8vd gpu-doctor-mcp-stdout-fd-hang` (requires `framework_edit_allowed` at implementation)

## Rationale

The same root cause fixed for `wave_gpu_doctor` (change `1p8vc`) exists on the **semantic-search hot path**, which is more impactful (a search is a common first action after a restart). A sweep of the MCP server found four more in-process onnxruntime/fastembed cold-load sites, all unprotected, each of which can write native diagnostics (DirectML/CUDA adapter enumeration) directly to OS **fd 1** — the MCP JSON-RPC stdout pipe — corrupting the protocol on first use:

- **A** — `_get_embedder` → `TextEmbedding(...)` → `ort.InferenceSession` (`server_impl.py:912`); query embedding for `docs_search` / `code_search` / `code_ask`.
- **B** — `_get_reranker` → `accel_embedder.make_reranker` → `ort.InferenceSession` (`server_impl.py:979` → `accel_embedder.py:503`); reranker.
- **C / C′** — the background prewarm **thread** (`_ensure_model_cached`, `server_impl.py:448` reranker / `:462` embedder), which builds ORT sessions **concurrently** with the MCP loop.

The per-site `cli_stdio.isolated_stdout_fd()` used for gpu-doctor is **not sufficient** here: it calls `os.dup2` on fd 1, which is **process-global**, so it is unsafe in the background thread (C/C′) — it would clobber the main thread's concurrent JSON-RPC writes.

The correct fix is process-wide and thread-safe: at server startup, give the MCP protocol a **private dup** of the real stdout and redirect fd 1 → `os.devnull`, so *every* native fd-1 write (A, B, C, C′, and gpu-doctor) is harmless without per-call wrapping. This is viable because the mcp stdio transport writes via `TextIOWrapper(sys.stdout.buffer, …)` (`mcp/server/stdio.py:49`), captured when `stdio_server()` runs — i.e. **after** `server.py`'s startup stdio setup — so repointing `sys.stdout` before `mcp.run` redirects the protocol to the private dup while fd 1 goes to devnull.

## Requirements

1. **Startup fd-1 isolation in `server.py`.** Before `mcp.run(transport="stdio")` (after `_configure_stdio_for_mcp_transport`), install a one-time isolation: `os.dup` the current stdout fd to a private fd; build a `TextIOWrapper(BufferedWriter(FileIO(private_fd)))` (utf-8, `newline="\n"`, `write_through=True`) and assign it to `sys.stdout`; then `os.dup2(devnull, 1)`. The mcp transport (which reads `sys.stdout.buffer` at `stdio_server()` time) then writes JSON-RPC to the private dup → the host; native libraries writing to fd 1 hit devnull.
2. **Fail-safe.** If any step raises, leave `sys.stdout` and fd 1 untouched (never break the transport) — build the new stream first and only swap once it is ready. Best-effort, like `_configure_stdio_for_mcp_transport`.
3. **Only on the stdio-server run.** It must run only on the real `mcp.run` path, never on `--dry-run` or CLI/non-transport invocations.
4. **stderr unchanged.** fd 2 / `sys.stderr` is untouched — Python logs (`_wf_log`, warnings) still reach the host's stderr.
5. **No per-site changes required.** With fd 1 isolated process-wide, sites A/B/C/C′ need no wrapping; the existing gpu-doctor `isolated_stdout_fd()` wrap (`1p8vc`) stays (harmless, tested) as defense-in-depth.

## Scope

**Problem statement:** in-process ORT cold-loads on the search hot path (and a background prewarm thread) write to fd 1 and corrupt the MCP JSON-RPC channel on first use; the per-site guard can't cover the background thread.

**In scope:**

- `server.py`: the startup fd-1 isolation function + its call before `mcp.run`.
- `test_*`: mechanism coverage (protocol writes reach the private dup; fd 1 is devnull; fail-safe).

**Out of scope:**

- Changing the embedder/reranker/prewarm logic itself (sites A/B/C/C′ are untouched — the isolation makes them safe).
- Reverting the `1p8vc` gpu-doctor per-site wrap (kept as defense-in-depth).
- Suppressing ORT logging via env (unreliable; the fd isolation is the robust fix).

## Acceptance Criteria

- [x] AC-1: after the startup isolation, a write to `sys.stdout.buffer` (what the mcp transport uses) reaches the **private dup** (the original stdout target), while a raw `os.write` to the isolated fd (native lib) does **not** reach it. (`test_protocol_writes_reach_private_dup_native_writes_dropped`)
- [x] AC-2: the isolated fd points at `os.devnull` after isolation (native writes dropped); `sys.stderr` is unchanged. (same test asserts `sys.stderr` untouched + native bytes absent)
- [x] AC-3: fail-safe — when `sys.stdout` has no real `fileno()`, `sys.stdout` is left intact (no exception escapes). (`test_fail_safe_no_real_fileno_leaves_stdout_intact`)
- [x] AC-4: the isolation runs only on the stdio-server path (after `_configure_stdio`, before `mcp.run`), not on `--dry-run`. (`server.py` main; `test_isolation_runs_on_stdio_path_before_mcp_run`)
- [x] AC-5: the full framework suite + docs-lint stay green. (suite 3696 ok; docs-lint ok)
- [~] AC-6 (field validation, Windows-repro-gated): the operator confirms the first `code_search` / `code_ask` / `docs_search` after a Windows MCP restart returns cleanly (no hang/garbled channel). *Not reproducible on macOS — awaits operator validation of a build; the isolation mechanism is locked by unit tests.*

## Tasks

- [x] Add the startup fd-1 isolation function to `server.py` (`_isolate_native_stdout_from_protocol`: dup → private buffered stdout → `sys.stdout` swap → `dup2(devnull, fd)`; build-then-swap; best-effort).
- [x] Call it after `_configure_stdio_for_mcp_transport()` and before `mcp.run(transport="stdio")` (the transport-only path; dry-run returns earlier).
- [x] Add tests for AC-1/2/3/4. (3 in `test_server_stdout_isolation.py`)
- [x] Run the framework suite + docs-lint; confirm green. (suite 3696 ok; docs-lint ok)
- [~] Hand the build to the operator for AC-6 validation. *Pending a build/release.*

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| startup fd-1 isolation in `server.py` | implementer | — | `framework_edit_allowed`; the process-wide fix |
| tests + suite/docs-lint | qa-reviewer | isolation | AC-1..5 |

## Serialization Points

- Single code surface (`server.py` runner). Open `framework_edit_allowed` for the pass.

## Affected Architecture Docs

`N/A` — a startup stdio-isolation step in the MCP runner; no boundary/flow/verification-architecture change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Protocol must reach the host; native writes must not. |
| AC-2 | required | fd 1 → devnull (the actual protection); stderr intact. |
| AC-3 | required | Must never break the transport on failure. |
| AC-4 | required | Must not perturb dry-run / CLI paths. |
| AC-5 | required | Suite + docs-lint green. |
| AC-6 | important | Real Windows confirmation; repro-gated, post-build. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-29 | Drafted from a server-wide sweep (4 in-process ORT cold-load sites on the search hot path: `_get_embedder`, `_get_reranker`, background prewarm thread embedder+reranker). The per-site guard can't cover the background thread (process-global `dup2`). mcp writes via `sys.stdout.buffer` (`mcp/server/stdio.py:49`), captured after `server.py` startup → a startup repoint + fd-1→devnull is the robust fix. | `server_impl.py:912,979,448,462`; `accel_embedder.py:503`; `server.py:395-397`; `mcp/server/stdio.py:47-49`. |
| 2026-06-29 | Implemented `_isolate_native_stdout_from_protocol()` in `server.py` (private dup of stdout for the protocol + fd 1 → devnull; build-then-swap, best-effort) and wired it after `_configure_stdio`, before `mcp.run`. Covers A/B/C/C′ + gpu-doctor process-wide and thread-safely; the `1p8vc` per-site wrap stays as defense-in-depth. AC-1..5 met; AC-6 `[~]` Windows-repro-gated. | `server.py` diff; 3 `test_server_stdout_isolation` tests (protocol→private dup, native→devnull, fail-safe, stdio-only); suite 3696 ok; docs-lint ok. |
| 2026-06-29 | **Live macOS smoke test** (partial AC-6): after a `/mcp` reconnect that loaded the patched `server.py`, the first `code_search` + `docs_search` (cold-loading the embedder + reranker, firing the prewarm thread) returned clean reranked JSON-RPC responses — the startup fd-1 isolation does NOT break the transport or the cold ORT load (refutes the "broad blast radius" challenge on macOS). The Windows-DirectML fd-1 noise-drop remains operator-gated. | macOS reconnect; `code_search`/`docs_search` `reranked: true`, top score 1.0. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-29 | Process-wide startup fd-1 isolation (private protocol dup + fd 1 → devnull), not per-site wraps. | Covers A/B/C/C′ + gpu-doctor in one place; the per-site `dup2` is process-global → unsafe in the background thread. mcp uses `sys.stdout.buffer` (verified) so repointing before `mcp.run` is sound. | Per-site `isolated_stdout_fd` for A/B + subprocess-ize the prewarm thread for C/C′ (more code, more surface); suppress ORT logging via env (unreliable). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Mis-wiring the protocol stdout breaks ALL server I/O (high blast radius). | Build the new stream first; swap only when ready; best-effort fallback leaves the original intact; verified mcp reads `sys.stdout.buffer`; unit-test that protocol writes reach the dup. |
| A subprocess inherits fd 1 = devnull and loses output. | Server spawns route stdout explicitly (`isolated_run`/`isolated_popen` capture or DEVNULL); none rely on inheriting the server's fd 1. |
| macOS can't reproduce the Windows/CUDA native fd-1 writes. | Unit-test the isolation mechanism cross-platform; gate AC-6 on operator validation. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
