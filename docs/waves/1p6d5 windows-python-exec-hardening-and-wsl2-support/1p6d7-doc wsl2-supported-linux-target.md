# Bless WSL2 as a first-class supported Linux target

Change ID: `1p6d7-doc wsl2-supported-linux-target`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-18
Wave: `1p6d5 windows-python-exec-hardening-and-wsl2-support`

## Rationale

Operators are running Wavefoundry under **Windows WSL2 today**, but the project's docs never state which platforms are supported, and the recent native-Windows scoping work made the (correct) point that **WSL2 is Linux** — under WSL2 the framework runs the POSIX path (`os.name == 'posix'`, `bin/python`, `fcntl`, `os.kill`, shebangs) exactly like native Linux. So WSL2 is already functionally supported; what's missing is making it **explicit and validated** so WSL2 users (and evaluators) know it's a blessed target, know the couple of WSL2-specific gotchas, and aren't confused by the in-flight native-Windows discussion.

This is a documentation + validation change: there is **no framework code to add** for WSL2 (it is Linux; the Area-2 native-Windows guards in `1p6d6` are irrelevant to it). The deliverable is an accurate platform-support statement, a WSL2 smoke checklist, and the known gotchas.

## Requirements

1. **Platform-support statement.** Add a clear, single source of truth for supported platforms: **macOS (Apple Silicon + Intel), Linux (x86_64/arm64), and Windows via WSL2** — all first-class; **native Windows (Terminal/PowerShell/cmd): not yet supported, planned** (point at `docs/references/native-windows-support.md`). Surface it where evaluators look: the `README` and `docs/references/project-overview.md` (and the install prompt/docs if they imply a platform).
2. **WSL2 = the Linux path (explicit).** State that WSL2 runs the identical POSIX code path as native Linux — no separate install, no special flags — so everything that works on Linux works under WSL2 (MCP server, semantic + graph index build, dashboard, secrets scan, docs-lint, the `code_*`/`wave_*` tools, GPU via CUDA passthrough when present; CoreML is macOS-only so WSL2 embeds on CPU or CUDA).
3. **WSL2 gotchas (the few that matter).** Document: (a) keep the repo on the **Linux filesystem** (`~/...`), NOT a Windows drive mount (`/mnt/c/...`) — DrvFs cross-OS I/O is dramatically slower and will make index builds and file-watch crawl; (b) the tool venv lives at `~/.wavefoundry/venv` inside the WSL2 distro (not the Windows `%USERPROFILE%`); (c) optional NVIDIA CUDA works via WSL2 GPU passthrough (`nvidia_gpu_present` detects it); CoreML/DirectML do not apply.
4. **WSL2 smoke checklist.** A short, reproducible validation list a WSL2 user (or we, on a WSL2 box) can run to confirm the blessed-target claim: install/setup, `wave_index_health` ready, an MCP `code_ask`/`docs_search`, a `wave-gate` open/close, dashboard start/stop, a secrets scan, `docs-lint`. (Mirrors the downstream-test runbook shape; lives outside any indexed-contamination trap.)
5. **Honest validation status.** Record that the Linux path is exercised continuously (the framework is POSIX and dev/CI runs on macOS/Linux), and mark whether an actual WSL2 run has been performed — if not yet, the smoke checklist is the open validation item (a real WSL2 user can close it).
6. Generic and vendor-neutral; docs-lint clean; no framework code change (assert WSL2 support rests on the existing Linux path, not new code).

## Scope

**Problem statement:** WSL2 users are real but unacknowledged; the project has no platform-support statement, so WSL2's (already-working) status is implicit and its gotchas undocumented.

**In scope:** a platform-support statement (`README` + `project-overview.md`), the WSL2-is-Linux explanation, the WSL2 gotchas, a WSL2 smoke checklist, and the validation-status note. Docs only.

**Out of scope:**

- Native-Windows support and the launcher/Area-1 work (explicitly *not yet supported* — this change says so).
- The Area-2 python-exec guards (`1p6d6`) — irrelevant to WSL2.
- Any WSL2-specific *code* (a `/mnt/`-drive perf warning, etc.) — documented as a gotcha, not engineered (revisit only if WSL2 users hit it).

## Acceptance Criteria

- [x] AC-1: A single, accurate platform-support statement exists — a **Supported Platforms** table in `docs/references/project-overview.md` (macOS / Linux / **WSL2 supported**; native Windows **not-yet/planned**, linking the scoping doc) and the matching one-liner at `README.md` (prerequisites). No contradictory platform claims remain.
- [x] AC-2: Both docs state WSL2 runs the identical Linux POSIX path (no separate install) and list the three WSL2 gotchas — Linux-FS-not-`/mnt/c`, venv at `~/.wavefoundry/venv` inside the distro, CUDA-yes/CoreML-DirectML-no.
- [x] AC-3: A reproducible WSL2 smoke checklist is published at `docs/reports/wsl2-smoke-checklist.md` (preconditions → setup/index health → MCP `docs_search`/`code_ask` → wave-gate open/close → dashboard start/stop → secrets scan → docs-lint), framed as a procedural runbook (no fabricated authoritative Q&A → out of the contamination trap).
- [x] AC-4: Validation status recorded honestly in both the overview and the checklist — the Linux/POSIX path is continuously exercised (dev/CI on macOS/Linux); **no real WSL2 run has been recorded yet**, so the smoke checklist (with a pending results row) is the explicit open item a WSL2 user can close.
- [x] AC-5: No framework code change. Statement is consistent with `docs/references/native-windows-support.md`, and that doc's stale **L-2** ("secrets scan is a no-op off macOS") was corrected — the cited lines are the `_physical_perf_core_count` helper, verified live; the scan runs on Linux/WSL2/Windows. docs-lint verified clean.

## Tasks

- [x] Add the platform-support statement to `README` + `docs/references/project-overview.md` (macOS/Linux/WSL2 supported; native Windows planned, link scoping doc).
- [x] Write the WSL2-is-Linux explanation + gotchas (Linux FS, venv location, GPU).
- [x] Publish the WSL2 smoke checklist (`docs/reports/wsl2-smoke-checklist.md`, procedural runbook — out of contamination traps).
- [x] Record validation status; flagged the real-WSL2-run as the open validation item (pending results row).
- [x] docs-lint; corrected the stale L-2 in the native-Windows scoping doc + verified consistency.

## Affected Architecture Docs

`N/A` — documentation/support-statement change; no architecture boundary, flow, or verification impact. References `docs/references/native-windows-support.md`.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The blessing itself — an accurate platform-support statement. |
| AC-2 | required | WSL2-is-Linux + gotchas (the actionable content for WSL2 users). |
| AC-3 | important | A reproducible validation checklist. |
| AC-4 | important | Honest validation status (don't claim more than we've run). |
| AC-5 | required | No code change; consistency with the scoping doc. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-18 | Planned alongside `1p6d6`. Verified WSL2 = Linux (POSIX path) and that secrets scanning runs on Linux/WSL2 (the `sys.platform!='darwin'` gate is only the `_physical_perf_core_count` helper, graceful fallback — not the scan). | `scan_secrets.py:45`/`run_secrets_scan.py:33` (perf helper only); `docs/references/native-windows-support.md` |
| 2026-06-18 | Implemented. Added the Supported Platforms table to `project-overview.md` + the README prereq one-liner; published `docs/reports/wsl2-smoke-checklist.md`; corrected the stale L-2 in the scoping doc (re-verified the cited lines are `_physical_perf_core_count`, def at `scan_secrets.py:40`/`run_secrets_scan.py:32`). No code change; honest validation status (no real WSL2 run recorded yet). | `README.md`, `docs/references/project-overview.md`, `docs/reports/wsl2-smoke-checklist.md`, `docs/references/native-windows-support.md` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-18 | Bless WSL2 via docs + a smoke checklist, with no WSL2-specific code. | WSL2 is Linux; the existing POSIX path already supports it — the gap is an explicit, validated statement, not engineering. | Add WSL2-specific code (rejected — nothing to fix; a `/mnt/` perf warning is a documented gotcha, not engineering). |
| 2026-06-18 | State native Windows as explicitly NOT-yet-supported. | Avoid implying the in-flight native-Windows work is shippable; set correct expectations. | Stay silent on native Windows (rejected — leaves WSL2 vs native-Windows ambiguous for evaluators). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Claiming WSL2 "supported" without a real WSL2 run. | AC-4 records honest validation status; the smoke checklist is the explicit close-out; a real WSL2 user can run it. |
| The support statement drifts from the native-Windows scoping doc. | AC-5 cross-checks consistency; both point at each other. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
