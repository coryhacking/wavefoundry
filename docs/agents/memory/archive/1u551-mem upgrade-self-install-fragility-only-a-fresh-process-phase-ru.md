# Upgrade self-install fragility: only a fresh-process phase runs the NEW code

Owner: Engineering
Status: archived
Last verified: 2026-07-31

Memory ID: `1u551-mem upgrade-self-install-fragility-only-a-fresh-process-phase-ru`
Superseded by: `1u8q3-mem upgrade-runner-phase-playbook`
Kind: `fragile_file`
Confidence: 0.85
Created: 2026-07-31
Updated: 2026-08-02
Source exploration cost: 777948
Source event: `repeated-repairs:1u2b0:upgrade_wavefoundry.py`
Validation: promote
Validated by: agent
Action delta: When adding upgrade behavior that must take effect on the upgrade that INSTALLS it, put the new-code call in the --cleanup phase (lock-gated) as well as --update-index, carry any operator-consent value across the process boundary in the upgrade lock rather than a module global, and rerun PermissionsRenderBackstopTests + PermissionsConsentCrossesTheProcessBoundaryTests + PermissionsRenderConsentTests together.
Validation rationale: The draft carries only a repair count and "re-verify with the full suite", which is true of every file. The four 1u2b0 repairs share one mechanism worth recording: the old-code window. The in-process orchestrator that runs Phase 1 was imported BEFORE extraction, so a feature installed by that upgrade cannot render from it; the fix had to move to a phase that runs in a fresh process. Verified in the current tree: _ensure_rendered_permissions_backstop is defined at upgrade_wavefoundry.py:1650 with a docstring naming both sites, and it now has two call sites (:3671 under --update-index, :3742 lock-gated immediately before phase_cleanup) versus the one guarded site the finding walked. The two consent repairs are the same boundary seen from the data side: _bounded_upgrade_summary flattened a dict delta to None at 3106 chars on the write tier, and _print_operator_summary runs in the cleanup process where the module global is gone, so the delta now rides the upgrade lock (:2743, :2868) and the unmanaged count is disclosed (:1639-1645). Overlaps the active 1u0dl-mem (six 1tz6l repairs on phase-transition state seams) — same file, adjacent but distinct mechanism, so recorded as supplements with the process-boundary axis named explicitly.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

Archived: 2026-08-02
Archive reason: Superseded by a verified consolidated file playbook after retention review.
Archive path: `docs/agents/memory/archive/1u551-mem upgrade-self-install-fragility-only-a-fresh-process-phase-ru.md`
## Summary

All four upgrade_wavefoundry.py repairs in wave 1u2b0 sit on the old-code window. The in-process orchestrator that runs Phase 1 was imported before extraction replaced the tree, so its module body is the OLD code and can never execute a step the upgrade is itself installing: the permissions backstop originally had a single call site guarded by --update-index, which an ordinary `wf upgrade` never runs, so the feature would first appear a full upgrade cycle later. The reliable default-path site is --cleanup, the one phase every documented path reaches in a fresh process (CLI `upgrade-wavefoundry --cleanup` and the `--cleanup` subprocess MCP wf_upgrade spawns); it is lock-gated so nothing mutates a committed operator file outside an upgrade, and placed BEFORE phase_cleanup so the recorded delta survives for the consent line and the lock removal. The same boundary produced the two consent repairs: a module global (_PERMISSIONS_DELTA) is empty in the cleanup process, so consent facts must ride the upgrade lock; and the bounded summary treats a dict as one scalar under the 2,000-char cap, so the write-tier delta (3,106 chars) silently became None while the read tier survived with ~440 chars of headroom. Fourth repair, same family: when the merge deliberately leaves already-present rules unmanaged, the count must be disclosed or the operator sees only "Permissions: unchanged".

## Evidence

- `permissions-backstop-unreachable-on-default-upgrade-path`
- `permissions-consent-delta-dropped-on-write-tier`
- `preexisting-rules-never-adopted-defeats-motivating-case`
- `stale-single-channel-contract-in-rendered-prompt`
- `1u2b0`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py:1650-1688 (helper docstring naming both sites)`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py:3671, :3727-3742 (two call sites)`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py:6512, :6765, :6829`

## Targets

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
