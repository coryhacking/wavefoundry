# Agent Body — Finalize Feature

Owner: Engineering
Status: active
Last verified: 2026-06-03

## Context

You are running **Finalize feature** on Wavefoundry (single-change closure).

## Steps

Same closure requirements as **Close wave** (see `docs/prompts/close-wave.prompt.md`). The wave contains one change; all seven closure items still apply.

## Wavefoundry Specifics

- Framework tests must pass if scripts were changed
- Docs gate must pass
- Guard-overrides must be reset if seeds were edited
- When `wave_review.enabled` is true, both council signoffs must be present in `## Review Evidence`
