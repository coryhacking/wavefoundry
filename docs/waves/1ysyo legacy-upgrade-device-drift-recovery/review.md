# Device-drift recovery guidance review

Owner: Engineering
Status: active
Last verified: 2026-09-22

## Scope and allocation

Operator replaced the proposed automated package recovery with guidance only before readiness or implementation. Coordinator owns authored edits; fresh independent contexts review the plan and delivery. Available default model retained for small documentation review tasks; actual runtime effort/model identity not independently observed.

## Historical seam evidence

Read tag `v1.25.0` (da3b259e8e9ef9da3f7b2cc4696c5a08c7c4762f): `sqlite_storage_migration.read_receipt` compares the complete stored `root_identity`; `upgrade_wavefoundry.main` calls `restore_checkpoint` before loading incoming extensions. Current `storage_identity.compare_identity` compares available inode after caller path validation and separately reports device drift.

Executed a disposable Python probe with the exact `read_receipt` function AST from that tag, its supporting current module globals, and `ReceiptTests.prepare()` producer-built state. Changed only the live device reported by `_identity`. Historical reader raised `storage_receipt_identity_mismatch`; current reader returned the same receipt. Receipt and upgrade checkpoint bytes remained unchanged. This is a comparison-boundary probe, not a whole old-installation upgrade and not proof of the tester's source revision. No target or repository recovery file was changed. Four existing identity/receipt tests also passed in the preceding investigation.

## Readiness primer

Fresh red-team context `/root/recovery_primer`, standard depth, guidance-only review: no blocking contradiction. Strongest challenge: apparent device drift cannot authorize arbitrary incoming-module copying or prove original-volume identity. Best alternative: maintainer handoff by default until exact source/target repair is reviewed. Specialist questions: distinguish wrong identity, pending recovery and unknown provenance; require reviewed diff, backup/recovery steps and scoped approval adjacent to repair. Prior automation review was interrupted and discarded.

## Delivery evidence

Authored guidance is byte-identical between seed 160 and the local upgrade prompt. Both existing storage-reconciliation lists now explicitly name older-reader diagnosis, operator-assisted repair, stop conditions and preservation. Renderer-owned marker contents are unchanged. Only these two carriers and CHANGELOG.md change outside the wave folder. fingerprint.json captures these three files before review; no target repair is being performed or qualified by this wave.

Executed text checks verify carrier parity, propagation and protected marker preservation. Negative text controls replace scoped approval and the pending-checkpoint stop sentence, respectively; both fail the checks. These are non-vacuous documentation checks, not proof of runtime or downstream agent behavior.

Manual decision walkthrough against the authored numbered steps:

| Case | Outcome | Governing step |
| --- | --- | --- |
| Verified strict older reader, completed receipt, same path and available inode, changed device, exact reviewed repair available | Present precise diff/backups/recovery for scoped approval, stop hosts, apply only approved repair, rerun original CLI | 1–4 |
| Same evidence but no qualified repair | Stop with collected source/package/error evidence for maintainer help | 3 |
| Matching version label but unknown loaded reader/source | No diagnosis from label alone; collect source evidence, stop if unverified | 1–2 |
| Changed path or inode, malformed identity, missing inode evidence, uncertain ownership | Stop; do not authorize benign-drift repair | 2 |
| Pending migration or upgrade/setup checkpoint | Preserve state; existing continuation or maintainer assistance | 2 |
| Temptation to edit device values, delete checkpoint or rebuild index | Explicitly prohibited as ways to force acceptance | final paragraph |
| Old prompt lacks the clause | Read selected package seed without applying it; reconcile authored prompt during upgrade editing | final paragraph plus storage-reconciliation list |

The zero-inode runtime fallback is not removed: this manual diagnosis deliberately declines to call missing-inode evidence proven device-only continuity. Existing identity semantics remain unchanged.


## Final validation

Canonical `python3 -B .wavefoundry/framework/scripts/run_tests.py` completed: 9,550 tests across 123 files, 13 intentional skips, OK in 294.936 seconds. Receipt timestamp: 2026-09-23T06:35:40.899112+00:00; inputs hash: `10c6515a83ac58220155560ed4ccf1ab4cba36e5aa275ee3b50bb9a38c4368ca`. QA and docs-contract delivery approval came from one fresh independent context (delivery-review.md), with no blocking findings. No executable code changed.
