# Lifecycle gates in server_impl.py require a public-entry census

Owner: Engineering
Status: archived
Last verified: 2026-07-28

Memory ID: `1tuyw-mem lifecycle-gates-in-server-impl-py-require-a-public-entry-cen`
Superseded by: `1u8q1-mem server-impl-file-playbook`
Kind: `fragile_file`
Confidence: 0.95
Created: 2026-07-28
Updated: 2026-08-02
Source exploration cost: 3365185
Source event: `repeated-repairs:1tsyx:server_impl.py`
Validation: promote
Validated by: agent
Action delta: When changing lifecycle gates in server_impl.py, enumerate every public lifecycle entry and verify declared-wave and legacy-wave behavior independently before trusting a green suite.
Validation rationale: Five 1tsyx repair chains touched distinct lifecycle decisions in server_impl.py; the durable risk is cross-surface gate drift, but the generated basename target was ambiguous.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

Archived: 2026-08-02
Archive reason: Superseded by a verified consolidated file playbook after retention review.
Archive path: `docs/agents/memory/archive/1tuyw-mem lifecycle-gates-in-server-impl-py-require-a-public-entry-cen.md`
## Summary

Repeated 1tsyx repairs showed that lifecycle authority and diagnostic changes in server_impl.py can leave sibling Prepare, Implement, Review, or Close paths inconsistent. Enumerate the public entry points, test declared and legacy waves separately, and mutation-check each claimed failure branch.

## Evidence

- `ac7-stale-readiness-fix-is-mock-shadowed`
- `legacy-prose-activation-branches-unpinned`
- `council-seat-alignment-degated-on-declared-waves-undocumented`
- `ac4a-ac6-and-ac7-coverage-claims-overstated`
- `agents-md-still-documents-retired-prepare-contract`
- `1tsyx`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
