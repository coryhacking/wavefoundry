# Agent Body — Finalize Feature

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Context

You are running **Finalize feature** on Wavefoundry (single-change closure).

## Steps

Same closure requirements as **Close wave** (see `docs/prompts/close-wave.md`). The wave contains one change; all seven closure items still apply.

## Wavefoundry Specifics

- Framework tests must pass if scripts were changed
- Docs gate must pass
- Guard-overrides must be reset if seeds were edited
