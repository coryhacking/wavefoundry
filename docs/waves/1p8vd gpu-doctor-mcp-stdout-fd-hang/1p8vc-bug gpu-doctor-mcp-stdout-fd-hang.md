# wave_gpu_doctor hangs on first cold call — fd-level stdout isolation for the ORT probe

Change ID: `1p8vc-bug gpu-doctor-mcp-stdout-fd-hang`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-29
Wave: `1p8vd gpu-doctor-mcp-stdout-fd-hang` (requires `framework_edit_allowed` at implementation)

## Rationale

On native Windows (1.9.6), the `wave_gpu_doctor` MCP tool hangs and never returns when invoked as the **first** action after restarting the MCP host; invoked later in the same session it works. Root cause (mapped, cited):

`wave_gpu_doctor_response` (`server_impl.py:16028-16043`) guards the probe with `contextlib.redirect_stdout(sys.stderr)` (`:16036`), which only swaps the **Python-level `sys.stdout`** object and **cannot** intercept writes to OS **file descriptor 1**. The probe chain — `provider_policy.diagnostic_report` (`provider_policy.py:347`) → lazy `import onnxruntime` (`:361`) → `setup_index._probe_embedding_provider` (`setup_index.py:705`) → `TextEmbedding(..., providers=["DmlExecutionProvider", ...])` → `ort.InferenceSession` (`onnx_model.py:113`) — on the **cold first call** loads onnxruntime's C extension for the first time and enumerates DirectML/DXGI GPU adapters, writing native diagnostics **directly to fd 1**, which *is* the MCP JSON-RPC stdout pipe. Those non-JSON bytes break the protocol framing → the client hangs (or the server's next stdout write blocks on a full pipe). Warm calls reuse the already-initialized DLL/DML → no fd-1 write → the tool returns.

Secondary latent risk (not currently triggered): fastembed's `ParallelWorkerPool` (`parallel_processor.py:105`, `multiprocessing.get_context("spawn")`) — if an in-server embedding call ever passed `parallel != None`, each spawned worker would re-load ORT and write its own cold-load diagnostics to the inherited fd 1 (the MCP pipe). The probe currently uses `parallel=None` (serial), so the pool never starts — this change locks that in.

## Requirements

1. **fd-level stdout isolation helper.** Add a reusable context manager to `cli_stdio.py` that redirects OS **fd 1** to stderr's fd (fallback: `os.devnull`) for the duration of the block and restores it after (with flush), catching native C-extension writes that `contextlib.redirect_stdout` cannot. It must be a safe no-op when `sys.stdout` has no real `fileno()` (e.g. a `StringIO` under test). Pure stdlib; cross-platform (`os.dup`/`os.dup2` work on Windows).
2. **Apply it to the gpu-doctor probe.** Wrap the `diagnostic_report(...)` call in `wave_gpu_doctor_response` with the new fd-level CM, keeping the existing Python-level `redirect_stdout(sys.stderr)` (belt-and-suspenders: Python writes → stderr; native fd-1 writes → isolated). The JSON-RPC response is written by the framework AFTER the handler returns, outside the CM, so fd 1 is restored before the response goes out.
3. **Lock the in-server probe to serial fastembed.** Ensure the in-server probe path never triggers the spawn-based `ParallelWorkerPool` (whose workers would re-load ORT against the inherited MCP fd 1): keep the probe's `embed()` calls serial (`parallel=None`) and add a regression assertion so a future change can't silently enable the pool in-process.
4. **No content or trust change.** The gpu-doctor report fields are unchanged; verification stays ON (no `verify=False`/`CERT_NONE`); no behavior change on hosts where the cold-load writes nothing.

## Scope

**Problem statement:** the MCP JSON-RPC stdout channel is corrupted by native onnxruntime/DirectML fd-1 writes during the cold ORT probe, hanging `wave_gpu_doctor` on first use; the Python-level stdout redirect can't prevent it.

**In scope:**

- `cli_stdio.py`: the reusable fd-level stdout-isolation context manager.
- `server_impl.py`: wrap the `wave_gpu_doctor_response` probe with it.
- `setup_index.py` / probe path: lock serial fastembed (no `ParallelWorkerPool` in-server) + assertion.
- `test_*`: mechanism + application + serial-probe coverage.

**Out of scope:**

- Caching the probe result across calls (perf, separate concern).
- Changing the embedding model, provider-selection logic, or the report content.
- Reworking fastembed (third-party) — the hardening keeps the pool from starting in-process rather than editing fastembed.
- Other MCP tools (the helper is reusable; adopting it elsewhere is follow-on if another in-process ORT-loading tool is found).

## Acceptance Criteria

- [x] AC-1: the `cli_stdio` context manager redirects OS fd 1 for the block — a raw `os.write(1, ...)` inside the block does NOT reach the original stdout — and restores fd 1 afterward. (`cli_stdio.isolated_stdout_fd`; `test_diverts_native_fd1_writes_and_restores`)
- [x] AC-2: the CM is a safe no-op when `sys.stdout` has no real `fileno()` (e.g. `StringIO`), raising nothing. (`test_noop_without_real_fileno`; also `test_does_not_leak_file_descriptors`)
- [x] AC-3: `wave_gpu_doctor_response` wraps `diagnostic_report(...)` in the fd-level CM in addition to the Python-level `redirect_stdout`. (`server_impl.py:16036`; `test_probe_wrapped_in_fd_level_stdout_isolation`)
- [x] AC-4: the in-server probe path runs fastembed serially (no `parallel=`) so the spawn `ParallelWorkerPool` never starts in the MCP server process. (`setup_index._probe_embedding_provider` SERIAL-ONLY comment + serial calls; `test_probe_does_not_enable_fastembed_parallelism`)
- [x] AC-5: the gpu-doctor report content is unchanged and no verification-disabling is introduced. (existing `GpuDoctorToolTests` envelope test stays green; no `verify=False`/`CERT_NONE` added)
- [x] AC-6: the full framework suite + docs-lint stay green. (suite 3697 ok; docs-lint ok)
- [~] AC-7 (field validation, Windows-repro-gated): the operator confirms `wave_gpu_doctor` returns on the FIRST cold call after a Windows MCP-host restart. *Not reproducible on macOS — awaits operator validation of a build; the fd-isolation mechanism is locked by unit tests in the meantime.*

## Tasks

- [x] Add the fd-level stdout-isolation context manager to `cli_stdio.py` (dup/dup2 save-redirect-restore, flush, no-op without a real fileno). (`isolated_stdout_fd`; redirects fd 1 → `os.devnull`)
- [x] Wrap `diagnostic_report(...)` in `wave_gpu_doctor_response` with it (keep the Python-level redirect).
- [x] Audit the in-server probe `embed()` calls; ensure serial; add the serial-probe regression assertion. (calls were already serial; locked with a comment + `test_probe_does_not_enable_fastembed_parallelism`)
- [x] Add tests for AC-1/2/3/4. (5 new: 3 in `test_cli_stdio`, 1 in `test_setup_index`, 1 in `test_server_tools`)
- [x] Run the framework suite + docs-lint; confirm green. (suite 3697 ok; docs-lint ok)
- [~] Hand the build to the operator for AC-7 validation. *Pending a build/release.*

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| fd-level stdout CM in `cli_stdio` | implementer | — | `framework_edit_allowed`; the reusable mechanism |
| apply to `wave_gpu_doctor_response` + serial-probe lock | implementer | fd-level CM | `server_impl.py` / probe path |
| tests + suite/docs-lint | qa-reviewer | both | AC-1..6 |

## Serialization Points

- `cli_stdio.py` (helper) is consumed by `server_impl.py` — land the helper before/with the call-site wrap; open `framework_edit_allowed` for the pass.

## Affected Architecture Docs

`N/A` — a stdio-isolation fix confined to the MCP server's gpu-doctor path and a shared stdio helper; no boundary/flow/verification-architecture change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The core mechanism that stops the fd-1 corruption. |
| AC-2 | required | Must not break non-fd test/host contexts. |
| AC-3 | required | The fix only helps if the probe is actually wrapped. |
| AC-4 | important | Closes the adjacent spawn-pool stdio risk. |
| AC-5 | required | No content/trust regression. |
| AC-6 | required | Suite + docs-lint green. |
| AC-7 | important | Real-world confirmation; Windows-repro-gated, post-build. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-29 | Drafted from a confirmed native-Windows 1.9.6 field report; root cause mapped to a Python-vs-fd-level stdout-redirect gap on the cold ORT/DirectML probe. | `server_impl.py:16028,16036`; `provider_policy.py:347,361`; `setup_index.py:705`; `onnx_model.py:113`; field memory `field-feedback-gpu-doctor-mcp-hang`. |
| 2026-06-29 | Implemented. Added `cli_stdio.isolated_stdout_fd()` (fd 1 → devnull, save/restore in finally, flush, no-op without fileno); wrapped the `diagnostic_report` probe in `wave_gpu_doctor_response` with it (alongside the Python-level redirect); locked the probe serial (comment + assertion). AC-1..6 met; AC-7 `[~]` Windows-repro-gated. | `cli_stdio.py`, `server_impl.py:16036`, `setup_index.py` diffs; suite 3697 ok (was 3692); 5 new tests; docs-lint ok. Delivery constraints honored: wraps only the synchronous probe, fd 1 restored before the response, no fd leak (`test_does_not_leak_file_descriptors`). |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-29 | Fix at the fd level (dup2) and keep the Python-level redirect. | `redirect_stdout` cannot intercept native C writes to fd 1; the fd-level redirect catches both layers. | Run the probe in a subprocess with `stdout=PIPE` (heavier; reintroduces Windows-spawn concerns) — kept as a fallback if fd-redirect proves insufficient. |
| 2026-06-29 | Harden by keeping the probe serial rather than editing fastembed. | `ParallelWorkerPool` is third-party; preventing it from starting in-process is the in-control lever. | Patch fastembed (out of scope); ignore (leaves a latent MCP-deadlock path). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| C library buffers fd-1 output and flushes AFTER fd 1 is restored, leaking a few bytes onto the JSON-RPC channel. | Flush around the redirect; ORT writes are prompt/unbuffered in practice; the subprocess-isolation fallback fully removes the risk if AC-7 still shows corruption. |
| dup2 on fd 1 interferes with the MCP transport's own stdout writes. | The probe is synchronous and the response is written after the handler returns (outside the CM); fd 1 is saved and restored within the block. |
| macOS CI cannot reproduce the Windows cold-load fd-1 write. | Unit-test the mechanism (raw `os.write(1)` is isolated by the CM) cross-platform; gate the real cold-call AC-7 on operator validation. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
