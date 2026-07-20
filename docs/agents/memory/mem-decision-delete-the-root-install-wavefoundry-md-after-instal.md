# Decision: Delete the root `install-wavefoundry.md` after install/upgr…

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-delete-the-root-install-wavefoundry-md-after-instal`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1rxyi-bug cleanup-root-install-bootstrap-file:06157fca6ab23243`
Validation: reject
Validated by: agent
Action delta: None; follow the current install and upgrade cleanup contracts and their executable tests.
Validation rationale: The bootstrap-file cleanup rule is already a canonical lifecycle behavior, so a separate memory would duplicate rather than supplement the operating contract.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1rycd): Delete the root `install-wavefoundry.md` after install/upgrade rather than move it into `.wavefoundry/`.. Rationale: Transient single-use bootstrap file; canonical instructions live in `docs/prompts/install-wavefoundry.prompt.md`; a `.wavefoundry/` copy would go stale and be re-dropped each upgrade..

## Evidence

- `1rxyi-bug cleanup-root-install-bootstrap-file`
- `1rycd`

## Targets

- `test_build_pack.py`
