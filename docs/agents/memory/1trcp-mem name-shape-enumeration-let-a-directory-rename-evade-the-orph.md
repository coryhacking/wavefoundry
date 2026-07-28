# Name-shape enumeration let a directory rename evade the orphan-ledger guard

Owner: Engineering
Status: active
Last verified: 2026-07-27

Memory ID: `1trcp-mem name-shape-enumeration-let-a-directory-rename-evade-the-orph`
Kind: `failed_attempt`
Confidence: 0.85
Created: 2026-07-27
Updated: 2026-07-27
Source exploration cost: 1158805
Source event: `finding:1to78:DF1-orphan-guard-dir-rename-evasion`
Validation: promote
Validated by: agent
Action delta: When adding a guard or exclusion scoped to docs/waves, define its scope by content role (a non-empty events.jsonl in a direct child directory), not by folder-name shape, and check that lifecycle resolution paths use the same predicate; mismatched wave-shape predicates can be played against each other.
Validation rationale: The generated summary described the reverification rather than the lesson. The durable signal is the defect class: the orphan guard enumerated by the id-shape regex while _resolve_wave_md_matches globbed any */wave.md, so one directory rename made a surviving non-empty ledger invisible to lint while the wave stayed operable; three seats executed the evasion and the repair moved enumeration to the content role. The name-vs-content predicate asymmetry survives in the indexer exclusion (named follow-up), so the rule stays actionable.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Wave 1to78 shipped the orphan-ledger docs-lint guard enumerating docs/waves children through the id-shape regex while _resolve_wave_md_matches resolved any */wave.md, so renaming a wave directory (underscore separator, seven-character prefix, or uppercase) with its declaration stripped left a surviving non-empty ledger undetected while the wave stayed fully operable; executed by three delivery seats. Repair: enumerate every direct child directory holding a non-empty events.jsonl regardless of name shape. The lesson: scope docs/waves guards by content role, never folder-name shape, and keep guard and resolution predicates aligned. Follow-up closed 2026-07-27: the indexer exclusion is content-driven too, and the surviving name-shape test is is_id_shaped_wave_dir_name, a lint message hint that decides nothing. All three predicates (lifecycle lookup, orphan lint, retrieval exclusion) now resolve by content or position rather than folder spelling.

## Evidence

- `DF1-orphan-guard-dir-rename-evasion`
- `ev-df1-orphan-guard-dir-rename-evasion-3`
- `1to78`

## Targets

- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/server_impl.py`
