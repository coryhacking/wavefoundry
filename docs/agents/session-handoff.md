# Session Handoff

Owner: Engineering
Status: active
Last verified: 2026-07-31

## Current State (2026-07-31)

- **Wave 1tz6l release-upgrade-hardening remains OPEN (implementing).** Change `1u0cc-bug
  upgrade-extract-leaks-bundle-runner-files` was late-admitted on operator direction and is now
  `implemented`: Phase 0b extraction in `upgrade_wavefoundry.py` is allowlist-filtered
  (`_extract_feature_members`, mirrors `upgrade_bundle` layout constants, pin-tested), 8 regression
  tests added, ordering-guard test re-anchored, seed-160/seed-010/install-block scoped-extraction
  companions landed (seed gate opened and closed), prompt surface and dashboard reference
  reconciled. Full suite green: 6572 tests across 61 files. Verified end-to-end against the real
  `wavefoundry-1.15.0.pfwu.zip` (6 members withheld; collision sentinels untouched).
- **1tz6l close gate is NOT clear.** The close dry-run reports every delivery lane withheld
  (code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer),
  wave-council-delivery and operator signoff missing, with ~20 blocking finding chains in
  `events.jsonl`. Either repairs were made without re-recording lane approvals, or the chains are
  genuinely open. The delivery review for 1u0cc folds into that close-out.
- **Local test build 1.15.0+pfwu** exists at `~/.wavefoundry/dist/wavefoundry-1.15.0.pfwu.zip`
  (only 1.15.0 pack in dist; the stale pfsd zip was deleted). Field upgrades ran on solaris (now
  1.15.0+pfwu) and aceiss/teton (1.15.0+pfsd). Root installer debris in both was already cleaned;
  rollback snapshots (`framework.rollback-bridge-*`) and their `BRIDGE-ROLLBACK.json` remain by
  design. Operator directive: do NOT clean other repositories from this session.
- **Nothing is committed.** The framework-tree hold stands at 1.15.0+pfwu; the working tree carries
  the pre-existing 1tz6l delivery plus this session's 1u0cc fix.

## Next Steps

1. Delivery review lanes for 1u0cc (code-reviewer, qa-reviewer, release-reviewer per policy roster)
   as part of the 1tz6l close-out.
2. Resolve the 1tz6l ledger state (re-record lane approvals or work the open chains), then operator
   decides on close.
3. Rebuild the pack after 1u0cc lands so the shipped zip carries the extraction fix (the pfwu zip
   predates it); changelog entry for 1u0cc still needed in the 1.15.0 section.

## Current Session

**Active wave:** *(none)*
