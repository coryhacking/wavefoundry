# Agent Body — Finalize Feature

Owner: Engineering
Status: active
Last verified: 2026-07-31

## Context

You are running **Finalize feature** on Wavefoundry (single-change closure).

## Steps

Same closure requirements as **Close wave** (see `docs/prompts/close-wave.prompt.md`). The wave contains one change; all seven closure items still apply.

## Wavefoundry Specifics

- Framework tests must pass if scripts were changed
- Docs gate must pass
- Guard-overrides must be reset if seeds were edited
- When review is enabled, readiness Council must be present and delivery Council must be present only when selected by the current Prepare receipt in `## Review Evidence`
