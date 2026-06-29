# WSL2 Smoke Checklist — confirm Wavefoundry on Windows/WSL2

Owner: Engineering
Status: active
Last verified: 2026-06-28

## Purpose

A short, reproducible runbook to confirm that Wavefoundry works end to end under **Windows WSL2**. WSL2 is Linux, so this exercises the identical POSIX path as native Linux — the goal is to *validate the blessed-target claim*, not to test Windows-specific code (there is none for WSL2). Run it inside a WSL2 distro (Ubuntu, etc.); it is procedural — a list of commands and the result each should produce.

This is a validation runbook, not authoritative reference content. See `docs/references/project-overview.md` → **Supported Platforms** for the platform statement and WSL2 gotchas.

## Preconditions

- [ ] Running **inside** a WSL2 distro (`uname -r` contains `microsoft` / `WSL2`), not Git-Bash or PowerShell.
- [ ] Repo checked out on the **Linux filesystem** (`~/...`), **not** `/mnt/c/...` (DrvFs is slow — index builds will crawl).
- [ ] `python3 --version` reports **3.11+**.

## Checklist

1. **Setup / venv + index build**
   - Run: `python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root .`
   - Expect: dependency check passes (or prints the isolated tool-venv install command), then the docs/seed index builds. The tool venv is created at `~/.wavefoundry/venv` **inside the distro**.
   - [ ] Setup completes without a platform error.
   - **GPU capability:** run `wf gpu-doctor` (or `wf setup --check-gpu`, or the `wave_gpu_doctor` MCP tool — all the same report) to print the embedding-provider / GPU diagnostic — confirm `nvidia GPU` detection, the provider it would select (CUDA vs CPU), and that no CUDA 12/13 ABI-gap is reported. Safe to run anytime.
   - [ ] `wf setup --check-gpu` reports the expected provider (CUDA on an NVIDIA WSL2 box, else CPU).

2. **Index health**
   - Tool: `wave_index_health()` (MCP), or CLI equivalent.
   - Expect: the project docs layer reports **ready** (present, non-zero counts, builder version stamped).
   - [ ] `index_health` shows the docs layer ready.

3. **MCP retrieval**
   - Tool: `docs_search("install flow")` and `code_ask("how does the wave gate work")`.
   - Expect: non-empty citations resolving to real files; `code_ask` returns citations + a confidence value.
   - [ ] Both return results with file-resolving citations.

4. **Wave gate open/close** (POSIX `fcntl` locking path)
   - Run: `wf gate open seed_edit_allowed` then `wf gate close seed_edit_allowed` (or the `wave_gate_open`/`wave_gate_close` MCP tools).
   - Expect: gate opens, status reflects enabled, then closes cleanly — no lock error.
   - [ ] Gate opens and closes without error.

5. **Dashboard start/stop** (POSIX detach via `start_new_session`)
   - Run: `wave_dashboard_start()` then `wave_dashboard_stop()` (MCP), or the `wf dashboard` dispatcher subcommand.
   - Expect: dashboard binds a loopback port and reports running; stop terminates it cleanly with no orphan (PID reconciliation via `os.kill`/cmdline on POSIX).
   - [ ] Dashboard starts, is reachable on loopback, and stops with no orphan.

6. **Secrets scan** (runs on Linux/WSL2 — not macOS-gated)
   - Tool: `wave_scan_secrets()` (MCP) or `run_secrets_scan.py`.
   - Expect: the scan executes and returns findings/clean (it is **not** a no-op off macOS — only the perf-core-count helper is macOS-specific).
   - [ ] Secrets scan runs and returns a result.

7. **Docs lint**
   - Run: `wf docs-lint` (or `wave_validate()` via MCP).
   - Expect: lint runs and reports clean (or real findings) — no platform/launcher error.
   - [ ] `wf docs-lint` runs to completion.

## Recording results

When a WSL2 user (or a WSL2 box) runs this, record the date, distro/version, Python version, and any deviations below. Until then, the open validation item is item 1–7 executed on a real WSL2 host; the Linux/POSIX path that WSL2 shares is exercised continuously by dev/CI on macOS/Linux.

| Date | Distro / WSL version | Python | Result | Notes |
| --- | --- | --- | --- | --- |
| _(pending)_ | | | | First real-WSL2 run not yet recorded. |
