# Agent Body — Init Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-05-04

## Context

You are running **Init Wavefoundry** (seed-010) on the Wavefoundry repository. This is the self-hosting mode: `.wavefoundry/framework/` is the canonical framework directory.

## Key Precedences

- When `docs/` local policy conflicts with `.wavefoundry/framework/seeds/` on generic framework behavior, the seed source wins.
- When Wavefoundry-specific policy under `docs/` conflicts with generic defaults, the local policy governs.

## Git Commits Policy

Agents must not run `git commit` unless the operator explicitly instructs them in the current request. Default: hand off diff + suggested message for operator to commit.

## Self-Hosting Paths

All framework paths are direct:

| Path | Content |
|------|---------|
| `.wavefoundry/framework/scripts/` | Framework tooling scripts |
| `.wavefoundry/framework/seeds/` | Canonical seed prompts |
| `.wavefoundry/framework/VERSION` | Current framework version |

## Epoch

`lifecycle_id_policy.epoch_utc: "2022-04-28T00:00:00Z"` — UTC midnight 4 years before init date; no prior git history. See `docs/workflow-config.json`.
