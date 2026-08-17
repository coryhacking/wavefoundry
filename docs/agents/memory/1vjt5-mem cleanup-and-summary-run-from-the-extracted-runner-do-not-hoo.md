# Cleanup and summary run from the extracted runner; do not hook them for the delivering upgrade

Owner: Engineering
Status: active
Last verified: 2026-08-16

Memory ID: `1vjt5-mem cleanup-and-summary-run-from-the-extracted-runner-do-not-hoo`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-08-16
Updated: 2026-08-16
Source exploration cost: 256624
Source event: `finding:1vgep:pre-cleanup-hook-duplicates-advisory`
Validation: promote
Validated by: agent
Action delta: Before adding an upgrade_extensions hook to make new behavior act on the delivering upgrade, check WHICH process runs the phase: --update-index and --cleanup (and therefore the operator summary) run from the freshly extracted runner, so summary-time and cleanup-time behavior needs no hook; a zip-loaded hook there prints twice. Only code that runs in the pre-extraction parent needs the hook path. Prove it with a real main(['--cleanup']) driver test counting the output block.
Validation rationale: Wave 1vgep: a review assumed the operator summary was printed by the pre-upgrade runner (class-b transition) and added a version-gated pre_cleanup hook; two independent reverifiers executed the real --cleanup on a from-1.17.0 lock with a zip-carried extension module and counted the advisory block twice. phase_cleanup is emitted only in the standalone --cleanup process, which runs the on-disk (freshly extracted) upgrade_wavefoundry.py (see _new_code_upgrade_backstop docstring). Verified in the current tree: upgrade_extensions.py is byte-identical to HEAD again and tests/test_agent_surface_integrity.py::test_delivering_upgrade_cleanup_prints_the_advisory_exactly_once pins one block from both 1.17.0 and 1.17.1. This supplements 1u8q3-mem (upgrade-runner phase playbook) with the specific hook-vs-runner ownership rule and its falsification method.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

The upgrade operator summary is emitted only by phase_cleanup in the standalone --cleanup process, which every documented path runs from the freshly extracted upgrade_wavefoundry.py; the same holds for --update-index. Behavior placed there already acts on the upgrade that delivers it, so a zip-loaded upgrade_extensions hook added to cover the delivering upgrade duplicates the output (1vgep: the advisory printed twice from 1.17.0). Reserve extension hooks for code that must run in the pre-extraction parent process, and prove single ownership with a real main(['--cleanup']) driver test that counts the block.

## Evidence

- `pre-cleanup-hook-duplicates-advisory`
- `agent-surface-advisory-absent-on-delivering-upgrade`
- `1vgep`
- `1u8q3-mem`

## Targets

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/tests/test_agent_surface_integrity.py`
