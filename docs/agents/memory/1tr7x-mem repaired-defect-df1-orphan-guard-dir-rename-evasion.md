# Repaired defect DF1-orphan-guard-dir-rename-evasion

Owner: Engineering
Status: superseded
Last verified: 2026-07-27

Memory ID: `1tr7x-mem repaired-defect-df1-orphan-guard-dir-rename-evasion`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-27
Updated: 2026-07-27
Source exploration cost: 1158805
Source event: `finding:1to78:DF1-orphan-guard-dir-rename-evasion`
Validation: rewrite
Validated by: agent
Action delta: When adding a guard or exclusion scoped to docs/waves, define its scope by content role (a non-empty events.jsonl in a direct child directory), not by folder-name shape, and check that lifecycle resolution paths use the same predicate; mismatched wave-shape predicates can be played against each other.
Validation rationale: The generated summary described the reverification rather than the lesson. The durable signal is the defect class: the orphan guard enumerated by the id-shape regex while _resolve_wave_md_matches globbed any */wave.md, so one directory rename made a surviving non-empty ledger invisible to lint while the wave stayed operable; three seats executed the evasion and the repair moved enumeration to the content role. The name-vs-content predicate asymmetry survives in the indexer exclusion (named follow-up), so the rule stays actionable.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1trcp-mem name-shape-enumeration-let-a-directory-rename-evade-the-orph`
## Summary

Real defect fixed in wave 1to78: Repair verified complete by execution in a fresh independent context distinct from the repairer; the carriers' boundary statement and mechanism wording now both match the shipped guard.

## Evidence

- `DF1-orphan-guard-dir-rename-evasion`
- `ev-df1-orphan-guard-dir-rename-evasion-3`
- `1to78`

## Targets

- `test_docs_lint.py`
- `wave_validators.py`
