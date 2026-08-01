# reconcile_scan.py fragility is channel boundaries: four repairs across two waves

Owner: Engineering
Status: active
Last verified: 2026-07-31

Memory ID: `1u43m-mem reconcile-scan-py-fragility-is-channel-boundaries-four-repai`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 777948
Source event: `repeated-repairs:1u2b0:reconcile_scan.py`
Validation: promote
Validated by: agent
Action delta: When touching reconcile_scan channel routing, add a near-miss control that varies the LOCATION within .claude/settings.json (hooks command string, foreign array named allow, deny/ask entry) as well as the rule and the file, keep unrecognized shapes degrading to the operator channel, and rerun RendererProvenanceChannelTests + HostPermissionChannelTests together.
Validation rationale: Overlaps the active 1u0yp-mem (same file, same kind, wave 1tz6l); neither draft alone states a mechanism, so this rewrite is deliberately the stronger cross-wave record and 1u0yp should be retired against it (recorded as supplements because the tool reserves the duplicates verdict for canonical-contract collisions). Four repairs across two waves sit on one axis: which CHANNEL a scan hit routes to, with misrouting into the self-healing channel as the dangerous direction because its operator guidance is literally "no edit needed" for a reference nothing will ever rewrite. 1tz6l contributed the rollback-prefix exclusion leak and the host-permission partition; 1u2b0 contributed _is_renderer_provenance_hit gating only on the filename (a retired name inside a hooks command in .claude/settings.json routed as renderer provenance) and _json_array_spans keying on ANY array named allow at any depth (a foreign somePlugin.config.allow hit misrouted the same way). The 1u2b0 review named why the earlier controls stayed vacuous: they varied the rule and the file but never the LOCATION within the file. Verified in the current tree: reconcile_scan.py:219-226 pins both governed regions to exact document positions, _json_key_value_spans (:229-302) is depth- and key-position-aware and degrades to "not governed" on malformed input, provenance_governed_spans (:305-320) requires allow to be a direct member of the top-level permissions object, and tests/test_reconcile_scan.py carries RendererProvenanceChannelTests (:554) alongside HostPermissionChannelTests (:343).
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Every reconcile_scan.py repair in waves 1tz6l and 1u2b0 is a channel-boundary defect: a scan hit routed to the wrong channel. Misrouting toward the self-healing channel is the dangerous direction, because that channel tells the operator "no edit needed" for a stale reference the renderer will never rewrite, producing a permanently unfixed reference nobody is looking at. 1tz6l: a rollback-bridge backup leaked into the live scan (scope boundary), and host-permission files were not partitioned to their own channel. 1u2b0: _is_renderer_provenance_hit gated only on rel == '.claude/settings.json' plus a rule match, so a retired tool name inside a HOOKS COMMAND in that file was classified as renderer provenance; and after that repair, _json_array_spans still keyed on ANY array named allow at any nesting depth, so a foreign somePlugin.config.allow hit misrouted the same way. The delivery review named the control gap explicitly: the existing near-miss tests varied the RULE and the FILE but never the LOCATION within the file, which is how the boundary went vacuous in a new dimension even though the fragile-file protocol was followed. Current code pins the two renderer-governed regions to exact document positions (the top-level provenance array, and the allow array that is a direct member of the TOP-LEVEL permissions object), with a position-tracking scan that consumes string literals whole and degrades every unrecognized or malformed shape to "not governed", i.e. the operator channel, which is the safe direction. This record subsumes the single-wave view in 1u0yp-mem.

## Evidence

- `provenance-channel-misroutes-non-allow-hits`
- `provenance-span-matches-any-allow-array`
- `knob-operator-space-is-host-guarantee-not-framework`
- `stale-single-channel-contract-in-rendered-prompt`
- `rollback-bridge-backup-leaks-into-live-reconciliation-scan`
- `upgrade-reconciliation-misses-live-guidance-and-misroutes-host-rules`
- `1u2b0`
- `1tz6l`
- `.wavefoundry/framework/scripts/reconcile_scan.py:219-320`
- `.wavefoundry/framework/scripts/tests/test_reconcile_scan.py:343 HostPermissionChannelTests, :554 RendererProvenanceChannelTests`
- `subsumes 1u0yp-mem`

## Targets

- `.wavefoundry/framework/scripts/reconcile_scan.py`
- `.wavefoundry/framework/scripts/tests/test_reconcile_scan.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
