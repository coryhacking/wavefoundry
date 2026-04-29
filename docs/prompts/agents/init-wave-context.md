# Agent Body — Init Wave Framework

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Context

You are running **Init wave framework** (seed-010) on the Wavefoundry repository. This is the self-hosting mode: `framework/` is the canonical source; `.wavefoundry/framework` is a symlink to `../framework`.

## Key Precedences

- When `docs/` local policy conflicts with `framework/seeds/` on generic framework behavior, the seed source wins.
- When Wavefoundry-specific policy under `docs/` conflicts with generic defaults, the local policy governs.

## Git Commits Policy

Agents must not run `git commit` unless the operator explicitly instructs them in the current request. Default: hand off diff + suggested message for operator to commit.

## Self-Hosting Paths

| Canonical Reference | Actual Path |
|--------------------|-------------|
| `.wavefoundry/framework/scripts/` | `framework/scripts/` (via symlink) |
| `.wavefoundry/framework/seeds/` | `framework/seeds/` (via symlink) |
| `.wavefoundry/framework/VERSION` | `framework/VERSION` (via symlink) |

## Epoch

`lifecycle_id_policy.epoch_utc: "2022-04-28T00:00:00Z"` — UTC midnight 4 years before init date; no prior git history. See `docs/workflow-config.json`.
