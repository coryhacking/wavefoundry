# Secrets Full-Scan Baseline at Install and Upgrade

Change ID: `1p450-enh secrets-full-scan-baseline-at-install-upgrade`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-08
Wave: 1p44n framework-1p6-hardening

## Rationale

The secrets gate has no guaranteed full-repo baseline at install or upgrade, so secrets in files that never change stay invisible. The docs-lint hook path is incremental: `cli.py:87` calls `check_hardcoded_secrets(root, scan_all=args.scan_all)`, and `--scan-all` defaults to `False` (`cli.py:44-48`). Downstream, `get_scan_files` (`secrets_validators.py:168-174`) returns `_get_changed_files` whenever `scan_all` is false, so only wave-touched files are classified. No install/upgrade seed wires a full baseline — a grep of seeds 011/012/160 finds no `scan_all`/`--mode full` step. The practical symptom is dribbling findings (1 → 9 → 11 across runs) as new files happen to be touched; a secret in an untouched file is never surfaced until that file changes.

There is one nuance to preserve, not paper over: `run_secrets_scan.py` already full-scans on its FIRST run (empty `scan_state` → `rules_hash` mismatch → `scan_all=True` at `run_secrets_scan.py:126-128`), so the MCP subprocess path is not a pure dribble. But the `cli.py`/docs-lint hook path remains incremental, and nothing in install/upgrade GUARANTEES a baseline pass that classifies every tracked file up front. This change adds that explicit baseline so the whole backlog lands in one triage pass. It pairs with 1p44z, which materializes the scan policy first so the baseline classifies against the intended ruleset.

## Requirements

1. A full-repo secrets baseline scan runs exactly once during install, after the scan policy is written, classifying every tracked file into `docs/scan-findings.json`.
2. A full-repo secrets baseline scan runs exactly once during upgrade, in the post-extract/preflight phase, against the upgraded ruleset.
3. The install baseline step lives in seed-012, ordered AFTER step 2.3a (which writes the policy), so the baseline runs against the materialized policy.
4. The upgrade baseline step lives in seed-160, in the post-extract/preflight phase, before normal incremental operation resumes.
5. The baseline is invoked via a full-scan entrypoint — `wave_scan_secrets(mode='full')` or `run_secrets_scan.py --mode full` — not the incremental `cli.py`/docs-lint path.
6. The seed text documents the `run_secrets_scan.py` first-run full-scan nuance (`run_secrets_scan.py:126-128`) so future maintainers understand the baseline is belt-and-suspenders, not redundant: the MCP subprocess path full-scans on first run, but the docs-lint hook path does not, and a guaranteed baseline must not depend on incidental first-run state.
7. The baseline produces a single consolidated set of findings for one triage pass rather than dribbling findings across later waves.

## Scope

**Problem statement:** Install and upgrade never run a guaranteed full-repo secrets scan, so the docs-lint incremental path leaves secrets in untouched files unclassified and findings surface piecemeal over many waves instead of in one up-front triage.

**In scope:**

- A seed-012 step that runs a full-scan secrets baseline at install, ordered after the policy-write step (2.3a).
- A seed-160 step that runs a full-scan secrets baseline at upgrade, in the post-extract/preflight phase.
- Wiring the baseline through a full-scan entrypoint (`wave_scan_secrets(mode='full')` or `run_secrets_scan.py --mode full`) that classifies all tracked files into `docs/scan-findings.json`.
- A note in the relevant seed(s) capturing the `run_secrets_scan.py` first-run full-scan nuance.

**Out of scope:**

- Changing the default of `--scan-all` on the `cli.py`/docs-lint incremental path (that path stays incremental by design).
- Authoring or changing scan rules / the policy itself (owned by 1p44z and the scan-rules work).
- Auto-remediation of discovered secrets; this change only guarantees classification into findings.
- Re-baselining on every run or any per-wave scheduling beyond the single install/upgrade trigger.

## Acceptance Criteria

- [ ] AC-1: Seed-012 contains an explicit step, ordered after step 2.3a (policy write), that runs a full-repo secrets scan via a full-scan entrypoint (`wave_scan_secrets(mode='full')` or `run_secrets_scan.py --mode full`).
- [ ] AC-2: Seed-160 contains an explicit full-repo secrets baseline step in the post-extract/preflight phase, before incremental operation resumes.
- [ ] AC-3: After running the install baseline against a repo containing a secret in an otherwise untouched file, that file's finding appears in `docs/scan-findings.json` (proving full-scan, not changed-files-only, behavior).
- [ ] AC-4: The baseline uses the full-scan path (`scan_all=True` / `--mode full`), verified by it classifying files with no git changes — distinct from the incremental `cli.py:87` / `get_scan_files` (`secrets_validators.py:168-174`) default.
- [ ] AC-5: The seed text documents the `run_secrets_scan.py:126-128` first-run full-scan nuance and explains why the explicit baseline is still required (docs-lint hook path stays incremental; baseline must not depend on incidental first-run state).
- [ ] AC-6 (regression/test): A test invokes the full-scan baseline over a fixture repo containing a planted secret in an unchanged file and asserts the finding is written to the findings output; it also asserts the incremental path would have missed it (changed-files-only returns empty for that file).
- [ ] AC-7 (MCP wrapper-layer): A wrapper-layer test asserts `wave_scan_secrets(mode='full')` resolves to the full-scan code path (`scan_all=True`) and returns/writes findings for all tracked files, distinct from the default incremental mode.

## Tasks

- [ ] Confirm the full-scan entrypoint contract: `wave_scan_secrets(mode='full')` and/or `run_secrets_scan.py --mode full` both set `scan_all=True` and write to `docs/scan-findings.json`.
- [ ] Add the install baseline step to seed-012 immediately after step 2.3a (policy write), invoking the full-scan entrypoint.
- [ ] Add the upgrade baseline step to seed-160 in the post-extract/preflight phase, invoking the full-scan entrypoint.
- [ ] Add the `run_secrets_scan.py:126-128` first-run full-scan nuance note to the relevant seed step(s).
- [ ] Add the regression test (AC-6): fixture repo with a planted secret in an unchanged file; assert baseline writes the finding and incremental path would miss it.
- [ ] Add the MCP wrapper-layer test (AC-7): assert `wave_scan_secrets(mode='full')` maps to `scan_all=True` and covers all tracked files.
- [ ] Coordinate edits to seeds 012 and 160 with 1p44z / 1p453 / 1p455 (shared files); ensure ordering: policy materialized (1p44z) before baseline (this change).
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and the docs gate; confirm clean.

## Agent Execution Graph


| Workstream            | Owner       | Depends On            | Notes                                                                 |
| --------------------- | ----------- | --------------------- | --------------------------------------------------------------------- |
| entrypoint-contract   | Engineering | —                     | Verify full-scan entrypoint sets `scan_all=True` and writes findings  |
| install-baseline-012  | Engineering | entrypoint-contract   | Seed-012 step after 2.3a; serialize with 1p44z policy-write ordering  |
| upgrade-baseline-160  | Engineering | entrypoint-contract   | Seed-160 post-extract/preflight step                                  |
| nuance-note           | Engineering | install-baseline-012  | Document `run_secrets_scan.py:126-128` first-run full-scan caveat     |
| tests                 | Engineering | install-baseline-012  | Regression (AC-6) + MCP wrapper-layer (AC-7)                          |


## Serialization Points

- `.wavefoundry/framework/seeds/012-install-wavefoundry-phase-2.prompt.md` — shared with 1p44z / 1p453 / 1p455; the install baseline step must land after the 1p44z policy-write (2.3a) edits.
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md` — shared with 1p44z / 1p453 / 1p455; coordinate insertion point in the post-extract/preflight phase to avoid conflicting edits.

## Affected Architecture Docs

N/A — this change adds install/upgrade seed steps and tests that invoke an existing full-scan entrypoint; it introduces no new module boundary, control/data-flow path, or verification-architecture change.

## AC Priority


| AC   | Priority   | Rationale                                                                                          |
| ---- | ---------- | ------------------------------------------------------------------------------------------------- |
| AC-1 | required   | Install baseline step is the core deliverable; without it secrets in untouched files stay hidden  |
| AC-2 | required   | Upgrade baseline step is the second core deliverable so existing installs gain a baseline         |
| AC-3 | required   | Proves full-scan behavior end-to-end (untouched-file finding lands in findings)                   |
| AC-4 | important  | Confirms the baseline uses the full-scan path, not the incremental default                        |
| AC-5 | important  | Documents the first-run nuance so the baseline is not later deleted as redundant                  |
| AC-6 | required   | Regression test guards against silent regression to changed-files-only behavior                   |
| AC-7 | important  | MCP wrapper-layer coverage ensures `mode='full'` routes to `scan_all=True`                         |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date       | Decision                                                                                  | Reason                                                                                                         | Alternatives                                                                                      |
| ---------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| 2026-06-08 | Add an explicit `scan_all=True` baseline at both install (seed-012, after 2.3a) and upgrade (seed-160, preflight) rather than changing the docs-lint default. | Keeps the per-edit hook fast/incremental while guaranteeing a one-time full classification of every tracked file; pairs with 1p44z policy materialization. | Flip `--scan-all` default to True (rejected: slows every docs-lint run); rely on `run_secrets_scan.py` first-run full-scan only (rejected: docs-lint hook path stays incremental, baseline not guaranteed). |
| 2026-06-08 | Document the `run_secrets_scan.py:126-128` first-run full-scan nuance in the seed step.    | Prevents a future maintainer from deleting the explicit baseline as "redundant" without realizing the hook path is still incremental and first-run state is incidental. | Leave undocumented (rejected: invites accidental removal).                                         |


## Risks


| Risk                                                                                          | Mitigation                                                                                                      |
| --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Baseline runs before the policy is materialized, classifying against the wrong ruleset.       | Order the seed-012 step after 2.3a and gate on 1p44z; verify policy presence before invoking the baseline.     |
| Concurrent edits to seeds 012/160 with 1p44z/1p453/1p455 cause merge conflicts.               | Treat both seeds as serialization points; coordinate insertion points and land after 1p44z policy-write edits. |
| Full baseline surfaces a large backlog that stalls install/upgrade.                           | Baseline classifies into `docs/scan-findings.json` for one triage pass; it reports, it does not block on count.|


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
