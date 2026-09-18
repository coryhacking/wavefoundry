# Decision: record roots are fork-editable constants in record_paths.py, not configuration

Owner: Engineering
Status: active
Last verified: 2026-09-17

Memory ID: `1ybvy-mem decision-record-roots-are-fork-editable-constants-in-record-`
Kind: `decision`
Confidence: 0.9
Created: 2026-09-17
Updated: 2026-09-17
Source exploration cost: 578663
Source event: `decision-log:1y042-enh record-roots-config-and-resolver:a8e20667877520c3`
Validation: promote
Validated by: agent
Action delta: Do not read record roots from workflow-config; edit the constants in record_paths.py at merge time and keep validation fail-closed there
Validation rationale: The generated candidate captures the SUPERSEDED cycle-1 decision (config-driven roots). The operator redirected the design during delivery review on 2026-09-17: roots are fork-editable module constants (WAVES_ROOT, PLANS_ROOT, NESTED, MAX_DEPTH) in record_paths.py, nothing is read from configuration, and the ADR 1yb8v records why (a runtime-dynamic layout needed input validation, cache invalidation, and lint-corpus following, which produced three review findings). Verified against record_paths.py and the ADR on the current tree.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Decision (wave 1y0gz, operator redirect 2026-09-17): the wave and plan record roots and the nested-discovery settings are module constants in .wavefoundry/framework/scripts/record_paths.py (WAVES_ROOT, PLANS_ROOT, NESTED, MAX_DEPTH); a downstream fork edits them at merge time and nothing is read from docs/workflow-config.json at runtime (a record_layout block or wave_implement.wave_root is inert). Rationale: a runtime-dynamic layout required input validation, cache invalidation on config edits, and every lint and gardener walker following it, which produced three delivery-review findings; constants keep the layout fixed per process. Validation of the constants stays fail-closed (absolute, dotdot, empty, file or dangling-symlink ancestor, escaping symlink, symlink or case alias, equal or nested by inode, typed NESTED and MAX_DEPTH). See ADR 1yb8v.

## Evidence

- `1y042-enh record-roots-config-and-resolver`
- `1y0gz`
- `ev-contract-doc-claims-3`

## Targets

- `.wavefoundry/framework/scripts/record_paths.py`
- `docs/architecture/decisions/1yb8v-adr record-layout-config-over-resolver-protocol.md`
