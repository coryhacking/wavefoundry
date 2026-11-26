# Give each upgrade advisory one owner across primary and cleanup

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24f1e-mem give-each-upgrade-advisory-one-owner-across-primary-and-clea`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 256624
Action delta: When adding an upgrade advisory, choose the phase that owns its facts and exercise the installed cleanup handoff. Count primary and cleanup messages separately and check for one terminal summary.
Validation rationale: Checked _run_auto_cleanup and the tests for one terminal result and one cleanup advisory.
Supersedes: `1vjt5-mem cleanup-and-summary-run-from-the-extracted-runner-do-not-hoo`

## Summary

Automatic cleanup prints the primary summary before invoking the installed cleanup child. The child owns the terminal summary. A cleanup-specific advisory added to a pre-cleanup extension hook can print twice on the very upgrade that introduces it.

## Evidence

- `docs/waves/24buu memory-revalidation-upgrade-delivery/24bn9-enh cli-upgrade-runs-cleanup.md`
- `1vgep`
- `test_cli_primary_runs_extracted_cleanup_and_emits_one_terminal_result`
- `test_delivering_upgrade_cleanup_prints_the_advisory_exactly_once`

## Targets

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/tests/test_agent_surface_integrity.py`
