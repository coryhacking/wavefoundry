# Synthetic status ordering review

Owner: Engineering
Status: active
Last verified: 2026-09-21

Independent reviewer: code-reviewer and qa-reviewer share one reviewer context, independent of the implementer. Narrow scope: `make_declared_wave` status ordering and its input/producer-order controls. No claim of separate lane independence from each other.

## Finding

`fixture-status-producer-order`: MCP source inspection found the only synthetic Status rewrite before Prepare, readiness run and approval producers. An executed temporary-fixture probe wrapped the real Prepare producer and requested `implementing` plus admitted change, readiness receipt/run and approval. Prepare observed `implementing`; the required producer-backed sequence should retain `planned` until every producer completes. The central status enum also accepted legacy `ready`.

Same-root census: one status rewrite and one accepted-status set in the helper; the existing producer-order test used default `planned` and therefore could not catch this defect. The existing synthetic-status test covered only creation, without readiness producers.

Finding recorded through typed review events, dry-run before create. Only code and QA approvals require rechecking. No production changes, whole-suite execution or source mutations by this reviewer.

## Mutation table

| Probe | Expected | Observed |
| --- | --- | --- |
| Real Prepare wrapper, implementing + ready/run/approval | Prerequisite producer sees planned | Saw implementing, reproducing the defect |

Repair replay and final fingerprint verification are recorded below.

## Cycle 3 reverification

Frozen packet: `cdc9ed9135af6cc1b508a349f858cca75810a0e1db9d00924f743c76447f2c61`. Independently recomputed every packet path's `git hash-object` before and after mutation replay; all matched. Budget: eight minutes; targeted tests per mutant, broader runs only for survivors. No survivors.

MCP readback confirms the single rewrite now follows all producers, the legacy `ready` enum value is absent, and the regression test observes `planned` at admission, Prepare, readiness run and approval before asserting final `implementing`.

Five focused tests passed in 0.492 seconds without skips: producer-order/stub restoration, invalid inputs, status-only rewrite, final readiness oracle, and the actual docs-lint implementing/typed-readiness caller. The last exercises the named sibling shape. All six earlier guard-deletion controls were independently replayed and killed with assertion failures and zero errors/skips.

| Additional mutant | Targeted guard | Result |
| --- | --- | --- |
| Move synthetic rewrite back before Prepare | Producer-order test | Killed: one assertion failure, zero errors/skips |
| Restore legacy ready enum value | Invalid-input test | Killed: two assertion failures, zero errors/skips |

Replay: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests python3 -B 'docs/waves/1yd24 fixture-fidelity/status-order-mutation-probe.py'`. Earlier controls use `repair-mutation-probe.py` with the same environment.

Code and QA verdict: pass for this bounded repair, with both lanes using the same independent review context. No source edits were made by the reviewer. Prior unaffected delivery evidence remains in force; full-suite receipt refresh is coordinator-owned and not claimed by this report. No AC scope changes or new findings.
