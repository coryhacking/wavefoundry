# Trusted `uv` lookup refuses every PATH entry under the working directory

Change ID: `20qxn-bug uv-trust-refuses-cwd-ancestor-paths`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-15
Wave: `20tpo posix-review-follow-ups`

## Rationale

`_trusted_path_uv` in `setup_index.py` (waves `1zv87` and `1zv84`) replaced `shutil.which` so that a `uv` planted in the repository or reached through `.` cannot run. It refuses two folders: the target root and the current working directory, and it skips any PATH entry or candidate that lies under either. The working-directory refusal over-reaches:

- The standalone installer and pipx put `uv` in `~/.local/bin`; cargo puts it in `~/.cargo/bin`. A `wf setup --root <repo>` run from the home directory, or a repository cloned directly under it, refuses the only `uv` on the machine.
- Hosts that start the MCP server with `/` as the working directory, as can occur with host launch configurations on macOS, make every PATH entry a descendant of the refused folder, so no PATH `uv` is ever trusted. The startup dependency installer then reports no `uv` instead of installing in the background.
- The same range removed the plain-pip fallback, so setup exits 2 with "uv could not be found or installed" on a machine where it is installed and on PATH.

Homebrew's `/opt/homebrew/bin` and `/usr/local/bin` are not under a typical working directory, which is why the author's machine does not show it. `_controller` in `tensorwell_client.py` carries the same working-directory exclusion; there the cost is losing Tensorwell silently.

## Requirements

1. The trust rule refuses the target root and relative or empty PATH entries. The working directory is refused only when it lies inside the target root, which is the case the original guard meant (a shell sitting in the repository with `.` or a repo-relative entry on PATH). A working directory that is an ancestor of the repository, or unrelated to it, refuses nothing by itself.
2. A candidate that resolves through a symlink into the target root is still refused.
3. `_controller` in `tensorwell_client.py` adopts the same rule.
4. The refusal message when no `uv` is trusted names a bounded number of skipped entries with control characters escaped, and why, so an operator can see that `~/.local/bin` was skipped rather than absent.
5. Windows, macOS, Linux and WSL2 behaviour: the rule is platform-neutral. Windows keeps the `uv.exe`-only requirement from the original guard (a separate change in wave `20qrv` considers `.cmd` shims). macOS hosts started at `/` and Linux shells at `$HOME` now find the installer-default `uv`.

## Scope

**Problem statement:** a working-directory exclusion meant for `.` refuses the installer's default `uv` location.

**In scope:**

- `_path_inside`, `_trusted_path_uv` and the refusal message in `.wavefoundry/framework/scripts/setup_index.py`
- `_controller` in `.wavefoundry/framework/scripts/tensorwell_client.py`
- Tests covering a home-directory working directory, a `/` working directory, a working directory inside the root, and a symlinked candidate into the root

**Out of scope:**

- Restoring the plain-pip fallback
- The hash-pinned bootstrap

## Acceptance Criteria

- [x] AC-1: With PATH containing `<home>/.local/bin/uv` and the working directory set to `<home>` or `/`, `_trusted_path_uv(root)` returns that candidate when the root is elsewhere.
- [x] AC-2: With the working directory inside the root and a PATH entry under it, or a candidate symlinked into the root, the lookup refuses as today.
- [x] AC-3: `_controller` passes the equivalent of AC-1 and AC-2 for `tensorwell`.
- [x] AC-4: The no-`uv` refusal gives bounded, escaped skipped-entry diagnostics and reasons.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add failing tests for AC-1 to AC-3.
- [x] Narrow the working-directory refusal to "inside the root" in both lookups; add the skipped-entry report.
- [x] Update the setup guidance sentence that describes where `uv` is looked for.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Lookup rule and tests | Implementer | Readiness | Single write owner |
| Delivery review | QA, security | Lookup rule and tests | Security: the planted-binary refusal must not weaken |

## Serialization Points

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tensorwell_client.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A. The trust boundary stays "nothing the repository controls"; only the proxy for that boundary changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Setup fails on a correct machine |
| AC-2 | required | The original guard must hold |
| AC-3 | important | Same rule, lower impact |
| AC-4 | important | Operator can see why |
| AC-5 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned from the POSIX review of commits 2026-10-01 to 2026-10-15 | Two reviewers converged; confirmed at HEAD |

| 2026-10-15 | Readback: keep target-root, relative/empty PATH and symlink trust refusals; remove unrelated/ancestor cwd exclusion for uv and Tensorwell. Add bounded escaped skipped-entry diagnostics, no installer or selection-policy change. Before HOME or / cwd hides valid outside binaries; after it finds them. | Current-source MCP reads and admitted ACs; material code waits for current readiness binding |

| 2026-10-15 | Implementer Readback: with a known target, exclude only the target root and resolved candidates under it; ancestor/unrelated cwd adds no exclusion. With root=None keep conservative cwd refusal. Relative/empty entries, repository binaries and symlink targets stay refused; add bounded escaped lookup diagnostics without changing bootstrap, Windows shim notice or global policy. | MCP outline/read/keyword confirmed callable; current source includes qru shim notice. Inherited runtime model identity unknown. New tests will reproduce HOME and filesystem-root cwd failures, retain planted-binary/symlink controls in both methods, and run named mutants; only targeted setup tests, no full setup suite or live setup. |

| 2026-10-15 | Implemented known-target-only exclusion in uv and Tensorwell lookups; unknown-target uv keeps conservative cwd exclusion. Relative/empty entries and resolved repository candidates stay refused. Optional skipped diagnostics carry at most five escaped, bounded head/tail labels and reasons, reported by setup refusal and startup no_uv without global caching/reconfiguration. Preserved qru Windows shim notice, uv.exe-only lookup and pinned bootstrap. Updated the exact current setup lookup sentence in build-and-verification guidance. | Initial corrected cwd controls reproduced four failures: HOME and / each hid uv and Tensorwell. Final targeted results: new trusted-executable suite 7, existing UvLookupTrustTests 7, InstallIsolationTests 12, Tensorwell controlled lookup 1, qru shim notice 1; 28 tests / 0 skips green. No full setup suite, installer/model/service call or live setup. AC-1–AC-4/tasks complete; AC-5 final batch gate remains open. |
| 2026-10-15 | Eight named source guard mutants detected without errors/skips. | `uv-home-root-cwd-overreach` and `tensorwell-home-root-cwd-overreach` → `test_home_root_and_unrelated_cwd_find_outside_executables` (2 failures each); `uv-planted-repository-binary-accepted` and `tensorwell-planted-repository-binary-accepted` → `test_absolute_repo_entries_and_relative_or_empty_entries_stay_refused`; `uv-candidate-symlink-adopted` and `tensorwell-candidate-symlink-adopted` → `test_candidate_and_directory_symlinks_into_repo_stay_refused`; `unknown-target-cwd-refusal-removed` → `test_unknown_target_keeps_conservative_cwd_exclusion`; `raw-path-diagnostic-injection` → `test_skipped_diagnostics_are_bounded_escaped_and_explain_refusal` (1 failure each). `/private/tmp/20qxn-guard-mutants.py`; functions compiled in memory, shipped source never replaced. Native Windows/WSL2 qualification remains pending. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Refuse the working directory only when it is inside the root | That is the planted-binary case the guard was written for; an ancestor working directory controls nothing in the repository | (a) Drop the working-directory refusal entirely: loses the `.`-in-root case when PATH holds an absolute repo-relative entry. (b) Allowlist `~/.local/bin` and `~/.cargo/bin`: a growing list that still breaks for `/` working directories. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A repository checked out at `$HOME` itself | Then the working directory is inside the root and the old refusal applies; AC-2 covers it |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
