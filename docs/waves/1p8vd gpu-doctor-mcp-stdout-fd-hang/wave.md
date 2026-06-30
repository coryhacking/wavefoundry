# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-29

wave-id: `1p8vd gpu-doctor-mcp-stdout-fd-hang`
Title: Gpu Doctor Mcp Stdout Fd Hang

## Objective

Stop `wave_gpu_doctor` hanging on its first cold call after a Windows MCP-host restart. The cold onnxruntime/DirectML probe writes native diagnostics to OS fd 1 — the MCP JSON-RPC stdout pipe — which the Python-level `redirect_stdout` cannot catch. Add an fd-level stdout-isolation context manager around the probe (and lock the probe to serial fastembed so its spawn pool can't re-introduce the same corruption from workers).

## Changes

Change ID: `1p8vc-bug gpu-doctor-mcp-stdout-fd-hang`
Change Status: `implemented`

Change ID: `1p8vj-bug gitignore-runtime-block-not-enforced`
Change Status: `implemented`

Change ID: `1p8vp-bug search-path-ort-fd-stdout-corruption`
Change Status: `implemented`

Change ID: `1p8vq-debt drop-legacy-exc-secret-scan-ids`
Change Status: `implemented`

Completed At: 2026-06-29

## Wave Summary

Wave `1p8vd` (Gpu Doctor Mcp Stdout Fd Hang) delivered 4 changes: wave_gpu_doctor hangs on first cold call — fd-level stdout isolation for the ORT probe, Programmatic .gitignore reconcile — enforce the Wavefoundry runtime ignore block on install + upgrade, Search-path ORT cold-load corrupts MCP stdout — isolate native fd 1 from the JSON-RPC channel at startup, and Drop the legacy `exc-###` secret-scan ID backward-compat. Notable adjustments during implementation: wave_gpu_doctor hangs on first cold call — fd-level stdout isolation for the ORT probe: Implemented. Added `cli_stdio.isolated_stdout_fd()` (fd 1 → devnull, save/restore in finally, flush, no-op without fileno); wrapped the `diagnostic_report` probe in `wave_gpu_doctor_response` with it (alongside the Python-level redirect); locked the probe serial (comment + assertion). AC-1..6 met; AC-7 `[~]` Windows-repro-gated.; Programmatic .gitignore reconcile — enforce the Wavefoundry runtime ignore block on install + upgrade: Drafted from a field report (Windows-test repo missing index/log `.gitignore` entries across multiple upgrades). Root cause: `.gitignore` block is agent-prose-only (seed-050/160) with no programmatic writer; `render_aiignore` is the established idempotent-writer pattern to mirror. Added to wave `1p8vd` per operator direction.; Programmatic .gitignore reconcile — enforce the Wavefoundry runtime ignore block on install + upgrade: Implemented. Added `render_gitignore_block` (sentinel-delimited managed block; folds loose canonical entries; preserves operator content) + wired into `main()` (unconditional, runs every render/setup/upgrade); reconciled seed-050 + seed-160 prose to name it the authoritative writer. Dogfooded on this repo.

**Changes delivered:**

- **wave_gpu_doctor hangs on first cold call — fd-level stdout isolation for the ORT probe** (`1p8vc-bug gpu-doctor-mcp-stdout-fd-hang`) — 6 ACs completed. Key decisions: Fix at the fd level (dup2) and keep the Python-level redirect.; Harden by keeping the probe serial rather than editing fastembed.
- **Programmatic .gitignore reconcile — enforce the Wavefoundry runtime ignore block on install + upgrade** (`1p8vj-bug gitignore-runtime-block-not-enforced`) — 7 ACs completed. Key decisions: Programmatic writer in the renderer (runs on install + upgrade), not a reconcile-scan suggestion.; Sentinel-delimited managed block (mirror `render_aiignore`).
- **Search-path ORT cold-load corrupts MCP stdout — isolate native fd 1 from the JSON-RPC channel at startup** (`1p8vp-bug search-path-ort-fd-stdout-corruption`) — 5 ACs completed. Key decisions: Process-wide startup fd-1 isolation (private protocol dup + fd 1 → devnull), not per-site wraps.
- **Drop the legacy `exc-###` secret-scan ID backward-compat** (`1p8vq-debt drop-legacy-exc-secret-scan-ids`) — 5 ACs completed. Key decisions: Delete the `exc-###` migration shim entirely (no deprecation window).
## Journal Watchpoints

- Guard requirement: implementation needs `framework_edit_allowed` open (`cli_stdio.py` + `server_impl.py` + probe path); close immediately after.
- Sequencing: land the `cli_stdio` fd-level CM before/with the `server_impl` call-site wrap (helper → consumer).
- Watchpoint: the response must be written AFTER fd 1 is restored — wrap only the probe, never the framework's JSON-RPC write; flush around the dup2.
- Blocking for full closure: AC-7 (first-cold-call on a Windows MCP restart) is repro-gated — cannot be verified on macOS; mark `[~]` until the operator confirms a build.
- `1p8vj` guard: the `.gitignore` reconcile touches `render_platform_surfaces.py` (`framework_edit_allowed`) AND `seed-050`/`seed-160` prose (`seed_edit_allowed`) — open both for that pass, close immediately after. Mirror `render_aiignore`'s managed-block pattern so operator `.gitignore` entries are never clobbered.
- Re-review: the wave-council-delivery signoff must be re-run to cover BOTH changes before close (the original delivery review predated `1p8vj`).

## Review Evidence

- wave-council-readiness: approved 2026-06-29 — cited-root-cause bug change; localized to `cli_stdio.py` + `server_impl.py` + the probe path; 7 ACs (4 unit-assertable cross-platform, 1 suite/lint, 1 faithfulness, 1 Windows-repro-gated `[~]`); fd-level fix with a documented subprocess-isolation fallback; the mechanism is testable even though the cold-load repro is not. No dependencies.
- wave-council-delivery: approved 2026-06-29 — PASS, no issues (covers BOTH changes). **`1p8vc`** (gpu-doctor): `isolated_stdout_fd` saves/restores fd 1 and closes both fds in `finally` (no leak — `test_does_not_leak_file_descriptors`, 50 iterations); only the synchronous probe is wrapped and `return _response(...)` is outside the block, so fd 1 is restored before the JSON-RPC response (resolves the prepare-phase dup2-vs-transport challenge); no fail-open; serial-probe lock closes the spawn-pool risk; AC-7 `[~]` Windows-repro-gated. **`1p8vj`** (gitignore): `render_gitignore_block` writes a sentinel-managed block, idempotent, preserves operator content (5 passing tests), wired unconditionally into `main()` (self-heals on every render/upgrade), seed-050/160 reconciled to the programmatic owner; dogfooded on this repo (`git check-ignore` confirms); the legacy-orphan-comment migration artifact is documented + bounded to prior-hand-seeded repos (target missing-block repos get a clean append). Suite 3702 green; docs-lint ok.
- wave-council-delivery (re-run for `1p8vp` + `1p8vq`): approved 2026-06-29 — PASS, no issues (now covers all 4 changes). **`1p8vp`** (search-path fd-1): `_isolate_native_stdout_from_protocol` gives the protocol a private dup + points fd 1 at devnull; 3 tests prove protocol→dup / native→devnull / fail-safe / stdio-only; build-then-swap + best-effort fallback + verified `sys.stdout.buffer` write-path; broad blast-radius bounded; AC-6 `[~]` Windows-repro-gated. **`1p8vq`** (drop `exc-###`): migration shim + `legacy_id` + docs/seed/3 test classes removed; the **gate/detection logic is untouched** (security-reviewer) so an `exc-###` ledger still blocks/reminds (new AC-2 test) and is not rewritten; twins byte-identical; historical `1p8nw` archive preserved. Suite 3696 green; docs-lint + byte-parity ok.
- operator-signoff: pending operator confirmation at closure

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-29: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, code-reviewer; rotating-seat: code-reviewer; strongest-challenge: dup2 is on the same fd 1 the MCP transport owns — a JSON-RPC frame written during the redirect window would be misdirected; bounded because per-request handling is synchronous and the gpu-doctor probe runs to completion with no frame in flight, so the impl must wrap ONLY the synchronous probe and restore fd 1 before returning; strongest-alternative: run the probe in a subprocess with stdout=PIPE — heavier, kept as the documented fallback if the fd-redirect proves insufficient. Delivery constraints: flush sys.stdout before dup2, close duped fds in `finally`, no-op when stdout has no real fileno.)

- **Prepare-phase review addendum [prepare-council] — 2026-06-29: PASS (`1p8vj`, added mid-wave per operator direction)** (seats: red-team, code-reviewer; strongest-challenge: the managed-block rewrite could clobber operator `.gitignore` entries — mitigated by mirroring `render_aiignore`'s sentinel-delimited replace-only-managed-region pattern (AC-3); strongest-alternative: add `.gitignore` to the report-only `reconcile_scan` — rejected because the agent-prose backfill already failed silently across multiple upgrades, so a writer that self-heals is required, not another suggestion.)

- **Prepare-phase review addendum [prepare-council] — 2026-06-29: PASS (`1p8vp` + `1p8vq`, added mid-wave per operator direction)** (seats: red-team, code-reviewer, security-reviewer). **`1p8vp`** strongest-challenge: mis-wiring the protocol stdout = total I/O failure (broad blast radius) — mitigated by build-the-new-stream-then-swap, a best-effort fallback that leaves the original intact, the verified fact that mcp reads `sys.stdout.buffer` (`mcp/server/stdio.py:49`) after `server.py` startup, and a cross-platform mechanism test; subprocess-inherits-devnull is non-issue (server spawns set stdout explicitly). strongest-alternative: per-site `isolated_stdout_fd` for A/B + subprocess-ize the prewarm thread — rejected as more surface and can't cleanly cover the thread. **`1p8vq`** strongest-challenge (security lens): removing migration could strand `exc-###` ledgers — refuted: the gate keys on `status` not id shape and `_find_exception` matches by file/line/hash, so old ledgers stay readable + gate-correct; only the cosmetic id-rewrite stops; ~1-day exposure window; detection/gate logic itself is untouched.

## Dependencies

- No external wave dependencies.
