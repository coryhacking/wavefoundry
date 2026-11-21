# Close Spec

Owner: Engineering
Status: active
Last verified: 2026-11-21

Shortcut: **`Close spec`** | Alias: **`Close change`**

## Purpose

Close ONE admitted change inside an open wave with `wf_close_change`: mark it
`complete` and activate the dependents it unblocks. It works the same way
whether the wave has one change or many, and it never closes the wave.
**Close wave** remains the only wave close.

## When to run

Run Close spec only after **Review wave** has cleared the change. A completed
change cannot be reopened, and `wf_close_change` records no review evidence, so
closing a change does not satisfy or replace any review lane. Close spec is
optional: `wf_close_wave` accepts a change left `implemented`, so use it when a
change must be `complete` inside the open wave, for example to activate a
dependent change.

## Gates

First, before any gate and with nothing written, `wf_close_change` refuses
a wave record it cannot read unambiguously (`wave_record_ambiguous`): an id
in more than one record, a record with more than one status line (fenced or
not, readable or not), or a fenced example id line that starts a record.
Move fenced examples out of the record lines and retry.

`wf_close_change` reports every failing gate, in `dry_run` and `create`:

1. The wave is OPEN (`active` or `implementing`).
2. The change is admitted to that wave (pass the FULL change id).
3. Its spec exists and is readable.
4. Its status is closable (`ready`, `active`, `review` or `implemented`) and
   agrees between the wave record and the spec.
5. It has no silent `[ ]` AC or task; every item is `[x]` or `[~]` with a
   rationale.
6. Every dependency on its wave-record `Depends On:` line is done (terminal or
   `implemented`).

## Steps

1. Confirm Review wave has cleared the change.
2. Run `wf_close_change(wave_id, change_id)`; `dry_run` is the default and
   writes nothing. Fix every reported gate.
3. Run `wf_close_change(wave_id, change_id, mode='create')`. It writes
   `complete` into the spec and the wave record, and moves each
   `planned` or `blocked` dependent whose dependencies are now all done to
   `ready`.
4. After a successful close, count all admitted specs. If the selected spec
   is the sole member, you may offer **Close wave**. Wait for the operator's
   explicit approval before running it. With multiple admitted specs, leave
   the wave open even if the selected spec was its last unfinished member.
   **Close wave** handles all eligible members under its usual review and
   closure rules.

## Guardrails

- Never use Close spec to close a wave; **Close wave** is the only wave close.
- It writes no review evidence or ledger event and does not move the
  review-policy receipt.
- A completed change cannot be reopened, so never run it before Review wave
  has cleared the change.
