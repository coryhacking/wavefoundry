# 1z9df-adr — Process information comes from psutil through one module

Owner: Engineering
Status: accepted
Last verified: 2026-09-29

## Context

The framework asks the operating system about other processes in many places: whether a pid is alive, whether it is a zombie, its command line, its working directory and when it started. Each place does it by hand. There are four pid-liveness implementations (`server_impl._pid_is_running`, `indexer._pid_is_running`, `upgrade_lib._pid_is_running`, `sqlite_storage_migration._host_is_running`), three command-line readers (`indexer._process_cmdline`, `dashboard_lib` dashboard scans, `sqlite_storage_migration.discover_hosts`), one zombie check (`indexer._process_is_zombie`, `ps -o state=`) and one working-directory reader (`sqlite_storage_migration._process_cwds`, `/proc` or `lsof`, nothing on Windows).

On native Windows these spawn `tasklist` (three copies with no timeout) and PowerShell CIM queries, and none of those branches has run on a real Windows host in CI (`docs/references/native-windows-support.md`). Windows is heavily used by enterprise consumers. One `index_build_status` call on Windows can spawn several processes in series, including a PowerShell cold start. The copies also disagree: the MCP server's copy has no zombie check and treats a process it may not signal as dead.

Wave `1za2y` delivery review found that a rootless `wf setup` in another repository can be attributed to this one (CR-L1). Fixing it well needs another process's identity on every platform, and Windows has no standard-library way to read another process's working directory. Wave `1p654` (2026-06-17) had rejected psutil for dashboard reconciliation to keep the tool environment lean for a local-only convenience surface.

This evaluation followed the Evaluate decision workflow: current-state grounding, a red-team comparison of four options, a reality-checker pass on the framing, an operator interview, and a feasibility check against the code.

## Decision

Process information in code that runs inside the tool environment comes from `psutil`, a required and capped dependency like `apsw` and `sqlite-vec`, through one flat module (`process_info.py`); there is no hand-rolled fallback, and a missing or broken install is a clear error that names `wf setup`.

## Consequences

**Positive:**

- On Windows, process queries use `psutil`'s code, which its maintainers test on Windows CI, instead of our untested `tasklist`, PowerShell and CIM branches; the MCP status path no longer spawns processes to answer them.
- Every consumer can read a process's start time (which callers compare with a recorded start to detect pid reuse), zombie state, command line and working directory on Windows, macOS, Linux and WSL2 from one API; the reuse check itself is each caller's comparison and is skipped when a start time cannot be read.
- Liveness has one implementation behind an explicit tri-state result (alive, dead, unknown); each caller states what "unknown" means for it.
- The hand-rolled `tasklist`, `ps` and PowerShell queries in tool-environment code are deleted rather than kept as a second path.

**Negative / tradeoffs:**

- A new compiled dependency. `psutil` publishes abi3 wheels for the mainstream platforms; a platform without a wheel builds from source. Platforms without `sqlite-vec` wheels (musl, Windows ARM64, 32-bit Windows) cannot run the framework today anyway.
- A host where `psutil` is missing or blocked (for example a Windows application-control policy) keeps building (the locks decide) but reports `process_info_unavailable` with the `wf setup` remedy, and its status may show a live build as not running until it is fixed.
- Code that runs before dependencies are installed keeps its own standard-library process queries, so a small amount of hand-rolled code remains outside `process_info`.
- Reverses the `1p654` decision. The reasons have changed: Windows is a primary platform, the process queries now sit on the MCP status path, and a real need (CR-L1) has no standard-library answer on Windows.

**Constraints imposed:**

- `psutil` is declared in both `setup_requirements.REQUIRED_IMPORTS` and `pyproject.toml` with a floor and a cap below the next major version (the `mcp[cli]<2` precedent), and a test pins it in both.
- `process_info.py` is flat in `scripts/`, importable without `psutil`, imports `psutil` inside a loader, and raises a typed `ProcessInfoUnavailable` (naming `wf setup`) when the import fails for any reason or the version is below the floor. The liveness wrappers turn it into "not running", so every build and refresh proceeds to the operating-system locks in `runtime_lock`, which remain the only correctness authority; `index_health`, `index_build_status` and `wf_server_info` report `process_info_unavailable` and recommend running `wf setup`, even when package metadata says `psutil` is installed.
- Code that runs before dependencies are installed or inside an older upgrade runner keeps its standard-library implementation, never imports `psutil`, and imports `process_info` only inside functions that run after `ensure_deps`: `venv_bootstrap`, the setup modules before `ensure_deps`, `upgrade_lib`, `dashboard_lib` (the upgrade runner calls its dashboard scan early), the modules in `upgrade_protocol.MANDATORY_FEATURE_MODULES` (whose import check walks every import, including function-local ones) and `sqlite_storage_migration` (`_host_is_running`, `discover_hosts`, `_process_cwds`). This is a separate context, not a fallback.
- `process_info` returns alive, dead or unknown and never decides policy; callers keep theirs (the storage migration stays fail-closed; build status treats an unverifiable builder as live).
- The standard-library subprocess calls that remain carry timeouts and go through the tree-kill resolver.
- Tests reach `psutil` through the loader seam, so a fake or failing `psutil` can be supplied.
- The macOS performance-core helpers stay as they are: `psutil.cpu_count(logical=False)` counts all physical cores, not performance cores.

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| Keep the hand-rolled code and add timeouts and zombie checks only | Leaves the untested Windows branches, the Windows spawn latency on the status path and the four diverging copies; cannot read a Windows working directory |
| One standard-library module with ctypes on Windows (PEB reads for command line and working directory) | Reimplements what `psutil` already maintains; the Windows parts are exactly what cannot be verified without a Windows CI host. Revisit if a Windows CI host is added and the dependency becomes a problem |
| `psutil` optional, with the hand-rolled code kept as a fallback | Doubles the code and tests for a case `wf setup` fixes, and the fallback would rarely run in the field; required dependencies already fail clearly (operator decision during readiness) |
| `psutil` everywhere, including pre-dependency code | Setup and older upgrade runners run before `psutil` is installed; those modules keep their own standard-library queries |
| Scrape process identity instead of recording it (working-directory lookup for CR-L1) | Kept only as a fallback; the follow-up records pid, start time and root when the build pid is stamped |

## References

- `docs/waves/1p61u graph-layer-map-quality/1p654-bug dashboard-lifecycle-reconciliation.md` (the superseded "not psutil" decision)
- `docs/waves/1zc7l rootless-setup-status-attribution/` (CR-L1)
- `docs/references/native-windows-support.md`
- `docs/architecture/decisions/12tm5-adr python-tool-environment.md`, `docs/architecture/decisions/1p7pb-adr native-windows-distribution-model.md`
- `.wavefoundry/framework/scripts/setup_requirements.py`, `.wavefoundry/framework/scripts/upgrade_protocol.py`
