# Close Change

Owner: Engineering
Status: active
Last verified: 2026-10-06

Shortcut: **`Close change`**

## Purpose

Close ONE admitted change inside an open wave with `wf_close_change`: mark it
`complete` and activate the dependents it unblocks. It works the same way
whether the wave has one change or many, and it never closes the wave.
**Close wave** remains the only wave close.

## When to run

Run Close change only after **Review wave** has cleared the change. A completed
change cannot be reopened, and `wf_close_change` records no review evidence, so
closing a change does not satisfy or replace any review lane. Close change is
optional: `wf_close_wave` accepts a change left `implemented`, so use it when a
change must be `complete` inside the open wave, for example to activate a
dependent change.

## Gates

`wf_close_change` reports every failing gate, in `dry_run` and `create`:

1. The wave is OPEN (`active` or `implementing`).
2. The change is admitted to that wave (pass the FULL change id).
3. Its change doc exists and is readable.
4. Its status is closable (`ready`, `active`, `review` or `implemented`) and
   agrees between the wave record and the change doc.
5. It has no silent `[ ]` AC or task; every item is `[x]` or `[~]` with a
   rationale.
6. Every dependency on its wave-record `Depends On:` line is done (terminal or
   `implemented`).

## Steps

1. Confirm Review wave has cleared the change.
2. Run `wf_close_change(wave_id, change_id)`; `dry_run` is the default and
   writes nothing. Fix every reported gate.
3. Run `wf_close_change(wave_id, change_id, mode='create')`. It writes
   `complete` into the change doc and the wave record, and moves each
   `planned` or `blocked` dependent whose dependencies are now all done to
   `ready`.
4. Close the wave later with **Close wave**, which stays operator-owned.

## Guardrails

- Never use Close change to close a wave; **Close wave** is the only wave close.
- It writes no review evidence or ledger event and does not move the
  review-policy receipt.
- A completed change cannot be reopened, so never run it before Review wave
  has cleared the change.
