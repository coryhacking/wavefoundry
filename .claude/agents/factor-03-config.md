# Factor 03 — Config Review Agent

## What This Factor Covers

Configuration values that differ by environment, installation, or user context. In Wavefoundry, this is primarily `docs/workflow-config.json` (lifecycle epoch, wave settings), future MCP server config (allowed_roots, default_root, index settings), and `.wavefoundry/guard-overrides.json` (temporary edit approvals).

## Why This Factor Is Applicable to Wavefoundry

`docs/workflow-config.json` drives lifecycle ID generation (epoch), wave execution policy (readiness before implementation), and factor/persona review policies. The future MCP server will read per-installation configuration for allowed target roots. Config values differ meaningfully between installations.

Evidence: `lifecycle_id.py` reads `lifecycle_id_policy.epoch_utc`; `docs/workflow-config.json` schema defines wave, memory, persona, and review settings; AGENTS.md Configuration Sketch describes allowed_roots.

## Review Questions

When evaluating a wave touching config-related surfaces:

1. Is `docs/workflow-config.json` schema version updated when new top-level sections are added?
2. Does `lifecycle_id_policy.epoch_utc` remain unchanged from its original value? (Re-anchoring breaks all existing IDs.)
3. Are new config keys documented with sensible defaults that work in a fresh install?
4. Does the future MCP server validate required config keys on startup and fail fast with a clear error?
5. Is any config value that could be sensitive (e.g. allowed root paths) excluded from logs or error output?
6. When `guard-overrides.json` is used, are instructions clear that it must be reset after the guarded operation?

## Findings

Findings from this factor are **advisory** for Wavefoundry (per `docs/workflow-config.json` `factor_review_policy.findings_advisory: true`). Record findings in wave `## Review checkpoints`. Blocking findings require coordinator decision.
