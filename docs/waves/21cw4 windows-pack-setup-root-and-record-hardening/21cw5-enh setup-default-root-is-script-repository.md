# Setup Defaults to the Repository That Holds the Script

Change ID: `21cw5-enh setup-default-root-is-script-repository`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-21
Wave: 21cw4 windows-pack-setup-root-and-record-hardening

## Rationale

The `wf` launchers pick the repository from their own location (`.wavefoundry/bin/wf` sets `REPO_ROOT` to `bin/../..` and changes into it), so `wf setup` always targets the repository that holds the framework. Running `setup_wavefoundry.py` directly does not: without `--root`, `_resolve_setup_root` (`.wavefoundry/framework/scripts/setup_wavefoundry.py`) and the `--check` branch of `main` use the current folder, and `setup_index.main` falls back to the current folder on its own. Run from a subfolder or another folder, setup is now refused by change `21ayw`, but the operator still has to work out the right folder. The operator asked that setup default to the repository containing the framework, as the launcher does.

## Product Intent

An operator who runs the setup script directly without `--root` gets the repository that holds the script, wherever they run it from, matching `wf setup`, whose launcher changes into its repository first. Before: the current folder is used, and outside the repository root setup is refused. After: a direct run behaves as if started from the script's repository. Boundaries: `main(argv)` callers (`wf_cli` and the tests) keep using the current folder; an explicit `--root` keeps today's behaviour, including the `21ayw` refusal; no upward search. AC-1 with AC-2 tests whether the intent was established.

## Requirements

1. Only when `setup_wavefoundry.py` runs as `__main__` and the arguments carry no `--root` (either `--root PATH` or `--root=PATH`), the entry changes the working directory to the folder three levels above the script's directory before calling `main`, so every stage that falls back to the current folder (reconciliation, `setup_index`, the render, the setup pid checks in `wf_server/index_handlers.py`) sees that root. The path comes from the `__main__` script's `__file__` made absolute without resolving links, so a linked framework folder still targets the repository that holds the link.
2. `main(argv)` is unchanged: in-process callers (`wf_cli`, whose launcher already changes into the repository, and the tests) keep the current folder.
3. An explicit `--root` is unchanged, and the `21ayw` refusal still applies to the resolved root; its message stays accurate because the current folder is the derived root.
4. A relative `--model-bundle` path (the one path option setup accepts) is made absolute against the operator's folder before the directory change, so it still names the file the operator typed.
5. `--help` text states the default; `--check-gpu` is unchanged.

## Scope

**Problem statement:** a direct run of the setup script targets the current folder rather than the repository the script belongs to.

**In scope:**

- The default in the `__main__` entry block of `setup_wavefoundry.py` and the `--help` text.
- Subprocess tests that run the script directly from another folder, from a subfolder, with a linked framework folder, with an explicit `--root`, and with `--check`.

**Out of scope:**

- `main(argv)` behaviour, `wf_cli.py` and the launchers (already correct).
- Upward search from the current folder (rejected: may pick a different repository when checkouts nest).
- Other entry points that take `--root`.

## Acceptance Criteria

- [x] AC-1: Running the setup script directly as a subprocess without `--root` from a folder outside a scratch repository that holds the scripts targets that repository: it gets past the `21ayw` root check (observed by a stubbed stage or `--check` output naming the repository); on the current code the same run is refused for the current folder.
- [x] AC-2: Running it from a subfolder of the scratch repository targets the repository root, `--check` without `--root` from another folder assesses the scratch repository, and a relative `--model-bundle` given from another folder still names the file in that folder.
- [x] AC-3: With the scratch repository's framework folder reached through a link (skipped with a reason where links cannot be created), the default is the repository that holds the link, not the link's target.
- [x] AC-4: An explicit `--root` (both spellings) still wins and a `--root` without the framework folder is still refused; in-process `main([])` still uses the current folder, so the existing in-process setup tests stay inside their sandboxes.
- [x] AC-5: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] In the `__main__` block, make a relative `--model-bundle` absolute, then change into the script's repository when no `--root` is given; update the `--help` default text.
- [x] Add the subprocess tests for AC-1 to AC-4 using a scratch repository that holds a copy of the scripts.
- [x] CHANGELOG Unreleased entry (Changed).

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                   |
| ---------- | ----------- | ---------- | ----------------------- |
| default    | implementer | none       | `__main__` entry only   |
| tests      | implementer | default    | subprocess, scratch repo |


## Serialization Points

- `.wavefoundry/framework/scripts/setup_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A: the default of one entry point's argument; no boundary, flow or verification seam changes.

## Platform Behavior

The default is computed with path arithmetic on the `__main__` script path, identical on native Windows, macOS, Linux and WSL2. That path is not resolved, so a framework folder linked into the repository (a symlink, or a junction on Windows) still targets the repository that holds it; an imported module's `__file__` would be the link target, which is why only the direct-run entry computes the default. Windows drive letters and separators come from the absolute script path.

## AC Priority


| AC   | Priority | Rationale                     |
| ---- | -------- | ----------------------------- |
| AC-1 | required | the requested default         |
| AC-2 | required | subfolder and check paths     |
| AC-3 | required | linked framework folders      |
| AC-4 | required | explicit root unchanged       |
| AC-5 | required | change-local verification     |


## Progress Log


| Date       | Update  | Evidence                                          |
| ---------- | ------- | ------------------------------------------------- |
| 2026-10-21 | Planned | operator request after the 21ayw setup root check |
| 2026-10-21 | Readiness amendment: default moved from `main` to the `__main__` entry and applied by changing directory, after readiness found the imported module's `__file__` is the link target and 19 in-process tests rely on the current folder. | readiness subagent a93b8f9 (code-reviewer, qa-reviewer, red-team) |
| 2026-10-21 | Readiness amendment round 2: a relative `--model-bundle` is made absolute before the directory change (Requirement 4, AC-2). | readiness recheck red-team editorial |
| 2026-10-21 | Implemented: `_direct_run_default` in `setup_wavefoundry.py` makes a relative `--model-bundle` absolute and returns the script's repository (link path not resolved) when no `--root`/`--root=` is given; only the `__main__` block calls it and changes directory; `--help` states the default. New `tests/test_setup_direct_run_default.py`: 5 unit tests and 4 subprocess tests against a scratch repository holding a copy of the scripts (foreign upgrade lock stops runs at reconciliation before any write). | 9 OK; with the entry change reverted in a scratch copy the three default-root subprocess tests fail and the explicit-root guard passes; setup, reconciliation, readiness, readiness-integration, memory-backfill and wf_cli suites OK |
| 2026-10-21 | Delivery review PASS with editorial notes repaired inline: `_enter_direct_run_root` makes a relative `WAVEFOUNDRY_MODEL_BUNDLE` absolute before the directory change (C1) and turns an underivable or unenterable script repository into a refusal naming `--root` instead of a traceback (C2); the environment test restores the folder in `finally` so Windows can remove its temporary folder (W1). | 11 OK; mutants (parents index, resolve, both model-bundle spellings, `--root=` detection, no directory change, env absolutisation, except removed, IndexError-only) all killed; delivery subagent a2f8836 |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-10-21 | Default only in the `__main__` entry, by changing into the script's repository | Matches the launcher exactly; in-process callers and tests keep the current folder; the imported module's `__file__` is the link target, so `main` must not compute it | Compute in `main` and inject `--root` (readiness: wrong root for linked frameworks via `wf_cli`, and 19 in-process tests would target the real repository); search upward (may pick a nested or outer repository) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A relative path option is read after the directory change | Requirement 4 makes `--model-bundle`, the only path option, absolute first |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
