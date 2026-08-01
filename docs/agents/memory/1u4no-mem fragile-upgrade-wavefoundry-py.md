# Fragile: upgrade_wavefoundry.py

Owner: Engineering
Status: superseded
Last verified: 2026-07-31

Memory ID: `1u4no-mem fragile-upgrade-wavefoundry-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 777948
Source event: `repeated-repairs:1u2b0:upgrade_wavefoundry.py`
Validation: rewrite
Validated by: agent
Action delta: When adding upgrade behavior that must take effect on the upgrade that INSTALLS it, put the new-code call in the --cleanup phase (lock-gated) as well as --update-index, carry any operator-consent value across the process boundary in the upgrade lock rather than a module global, and rerun PermissionsRenderBackstopTests + PermissionsConsentCrossesTheProcessBoundaryTests + PermissionsRenderConsentTests together.
Validation rationale: The draft carries only a repair count and "re-verify with the full suite", which is true of every file. The four 1u2b0 repairs share one mechanism worth recording: the old-code window. The in-process orchestrator that runs Phase 1 was imported BEFORE extraction, so a feature installed by that upgrade cannot render from it; the fix had to move to a phase that runs in a fresh process. Verified in the current tree: _ensure_rendered_permissions_backstop is defined at upgrade_wavefoundry.py:1650 with a docstring naming both sites, and it now has two call sites (:3671 under --update-index, :3742 lock-gated immediately before phase_cleanup) versus the one guarded site the finding walked. The two consent repairs are the same boundary seen from the data side: _bounded_upgrade_summary flattened a dict delta to None at 3106 chars on the write tier, and _print_operator_summary runs in the cleanup process where the module global is gone, so the delta now rides the upgrade lock (:2743, :2868) and the unmanaged count is disclosed (:1639-1645). Overlaps the active 1u0dl-mem (six 1tz6l repairs on phase-transition state seams) — same file, adjacent but distinct mechanism, so recorded as supplements with the process-boundary axis named explicitly.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1u551-mem upgrade-self-install-fragility-only-a-fresh-process-phase-ru`
## Summary

upgrade_wavefoundry.py required 4 separate repairs during wave 1u2b0; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `permissions-consent-delta-dropped-on-write-tier`
- `preexisting-rules-never-adopted-defeats-motivating-case`
- `stale-single-channel-contract-in-rendered-prompt`
- `permissions-backstop-unreachable-on-default-upgrade-path`
- `1u2b0`

## Targets

- `upgrade_wavefoundry.py`
