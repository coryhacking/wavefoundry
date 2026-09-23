# Guide recovery from an older upgrade reader after device drift

Change ID: `1ysyn-bug legacy-upgrade-device-drift-recovery`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-22
Wave: 1ysyo

## Rationale

An upgrade to 1.26.0+pru0 reportedly needed edits to stored device numbers after a Mac reboot. The incoming 1.26 reader already accepts matching paths and available inodes without restamping records, but the installed runner reads the migration receipt before loading incoming hooks. An older reader can block the upgrade containing its own repair. The exact tester source revision remains unverified. The operator chose guidance instead of new automation because few installations are affected. Provide accurate diagnosis and a bounded operator-assisted repair procedure, not a new package mode or generic bypass.

## Requirements

1. Describe the older-reader bootstrap failure separately from the fixed 1.26 comparison contract. A mismatch diagnostic alone does not prove benign device drift: inspect installed version/source, the selected package identity, the failing reader, and recorded versus live path and available inode before diagnosing. Inode/path mismatch, malformed records, ambiguous ownership or incomplete migration/checkpoint state stop this procedure and require the existing recovery path or maintainer help.
2. Preserve receipts, checkpoints, index databases and staging/rollback artifacts. Never recommend changing stored device numbers, deleting records, clearing locks/checkpoints, restamping, rebuilding the index, or swapping packages to force acceptance. Mention the existing path-plus-available-inode replacement-volume/reused-inode limitation without changing that contract.
3. For a confirmed older-reader defect, guide a build-specific installed-code repair: stop affected hosts, obtain a reviewed exact source/target repair from the maintainer, present its precise files/diff and backup/recovery steps for operator approval, and apply only that approved repair. A previously successful two-module repair is historical evidence, not a universal recipe; do not copy arbitrary incoming modules into arbitrary old builds. Keep the exact selected archive, rerun the original ordinary CLI command in a fresh process, follow its normal gates, and fully restart hosts when instructed. An unavailable verified repair means stop and provide version/hash/error evidence for assistance, not improvise.
4. Add the same guidance to seed 160 and the self-hosted upgrade prompt outside generated markers. Ensure the existing storage-guidance reconciliation instruction explicitly covers this clause for already-seeded targets. Changelog describes guidance only. Explain that the incoming seed can be inspected directly when the old installed prompt lacks the section; rendering alone does not populate authored guidance.

## Scope

**In scope:** seed 160, local upgrade prompt, changelog and durable verification evidence.

**Out of scope:** new CLI flags, package/bootstrap code, runtime patches, automatic repair, receipt edits, changing identity semantics, index rebuild, target-repository changes, memory rewrites, release/package creation, commit or closure.

## Acceptance Criteria

- [x] AC-1: Seed and local guidance distinguish the installed-reader failure from incoming 1.26 behavior and require evidence separating benign device drift from an actual identity/recovery mismatch. Verify against current and historical source and a decision-case walkthrough.
- [x] AC-2: The procedure preserves recovery evidence, requires a verified build-specific repair and scoped operator approval before installed-code mutation, and stops rather than improvising when repair or identity is uncertain. Wrong-path/inode, malformed and pending-recovery walkthroughs cannot reach repair authorization.
- [x] AC-3: The two authored carriers agree and the propagation instruction reaches already-seeded targets; changelog claims no automation. Diff verification confirms no executable code, renderer blocks or identity contract changed.

## Tasks

- [x] Verify the historical source seam and current no-restamping behavior; record evidence limitations.
- [x] Author diagnosis and operator-assisted recovery guidance in seed 160 and local carrier, plus explicit propagation and changelog.
- [x] Verify positive/negative guidance walkthroughs and carrier parity; run required gates and independent review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Guidance | coordinator acting implementer | readiness | One writing hand; no executable changes |
| Review | independent QA and docs-contract reviewers | draft | Check reachable diagnosis, safety boundaries and propagation |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`

CHANGELOG.md is also authored. Renderer-owned marker blocks, unrelated project prose and all executable files are protected. Review lanes are read-only; coordinator owns edits.

## Affected Architecture Docs

N/A: existing recovery and identity behavior is unchanged; the upgrade prompt documents an exceptional operator-assisted procedure, not a new runtime path.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Accurate diagnosis is the reason for the follow-up |
| AC-2 | required | Preserve evidence and avoid converting a rare issue into unsafe generic advice |
| AC-3 | required | Guidance must reach consumers without claiming nonexistent automation |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-22 | Current and packaged identity modules match; four existing focused tests pass, including device-drift record preservation. Tester pre-upgrade version is unknown. | sqlite_storage_migration.py:532; upgrade_wavefoundry.py:4790 |
| 2026-09-22 | Operator narrowed the follow-up to guidance because few users are affected. Removed all proposed package mode, staging, transaction-entry and runtime changes before readiness or source edits. | Operator: provide guidance instead of making it automatic |
| 2026-09-22 | Readback: add diagnosis and reviewed operator-assisted repair guidance only (AC-1–3). Before: mismatch may prompt receipt edits; after: collect identity/source evidence, stop uncertain cases, obtain exact reviewed repair and scoped approval. Only seed 160, local upgrade prompt and changelog change. | Current readiness approvals; review.md |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-22 | Ship diagnosis and reviewed operator-assisted repair guidance only | Operator-selected scope is proportionate to rare affected installations; no extra execution or recovery machinery | Automatic staged runner rejected for this wave: expands filesystem/execution surface. Blanket two-module copy rejected: compatibility varies. Receipt rewrite rejected: destroys historical evidence and conflicts with no-restamping policy. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Agents treat every mismatch as benign drift | Require path/inode and reader evidence; uncertain and pending states stop |
| Historical repair becomes a generic recipe | Exact build-specific compatibility review and operator approval; otherwise maintainer handoff |
| Old local prompt lacks new guidance | Read selected package seed directly and reconcile authored carrier during upgrade |

## Session Handoff

Guidance-only implementation complete after Prepare and independent readiness review. QA and docs-contract delivery approvals recorded from one fresh independent context. All 9,550 framework tests pass across 123 files, with 13 intentional skips. No executable source edits, automatic repair or target repair. Closure and commit await operator instruction.
