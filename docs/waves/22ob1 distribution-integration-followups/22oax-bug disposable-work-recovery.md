# Recover provable work snapshots and repository identity

Change ID: `22oax-bug disposable-work-recovery`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-11-05
Wave: 22ob1 distribution-integration-followups

## Rationale

Two wave_work failures were reproduced in temporary roots. Failing unlink after snapshot publication leaves two hard links; reads refuse snapshot_file_unproven and republication reports snapshot_exists. Reaching the same repository by a differently cased alias, or renaming the root without changing its inode, makes ownership unproven. Both fail safely but lose focused-review reuse or cleanup. Native Windows safe-work support was not executed; its capability guard and reported limitations require explicit documentation.

## Product Intent

Contributors should retain focused-review evidence and clean owned disposable work after recoverable local interruptions or path changes, without accepting foreign work or following links outside the owned area. AC-1 and AC-2 test recovery and refusal together. This maintains the vision's dependable handoffs; work areas remain disposable rather than authority records.

## Requirements

1. Recover a published snapshot whose only extra link is a provably same-inode, regular, non-symlink publisher temporary file in the verified receipts directory. Preserve immutable publication, receipt/content validation and full-review fallback when proof is incomplete. Account for an active concurrent publisher.
2. Keep reads nonmutating. Prefer proof of the permitted internal link or an explicitly owned, serialized repair over opportunistic deletion during reads. Unknown, external or excess links remain unproven.
3. Establish repository ownership from verified directory identity rather than path spelling alone. Case aliases must refer to the actual same directory; never case-fold arbitrary paths. Root moves/renames require a persisted identity or explicit safe rebinding, not merely removing the repository-string comparison.
4. Preserve legacy owner records without silently trusting previously unproven identity. Define compatible migration or an actionable refusal/rebind path. Moving only a work directory into a different repository must not transfer ownership. Preserve reboot-safe continuity: persisted device IDs are diagnostic history, never stable ownership keys or equality requirements across runs, including any new repository identity. Retain strict descriptor/identity checks taken within a single operation to detect substitution.
5. State the actual Windows limitation in the changelog and work-area contract: unsupported descriptor-safe operations yield unavailable work/snapshots and full-review fallback. Do not promise native Windows support from POSIX or simulated tests.

## Scope

In scope: wave_work.py, its tests and work-area documentation. Out of scope: weaker general filesystem containment, deleting arbitrary stale files, adopting another repository's work, changing review authority or implementing a separate Windows filesystem backend.

## Acceptance Criteria

- [x] AC-1: Interrupted post-link cleanup no longer permanently loses a valid snapshot; ordinary publication, concurrent publication and immutable collision behavior remain correct, while unproved links still refuse.
- [x] AC-2: The same repository is recognized through a case alias and supported root rename/move using verified identity. A device-ID change alone across runs does not invalidate owned work, cleanup or snapshot reuse; changed directory identity still refuses. A foreign repository, copied/replaced work area, symlink/redirection and unprovable legacy identity do not gain ownership.
- [x] AC-3: Published documentation and unsupported-capability responses agree about unavailable work, full-review fallback and preservation. Platform evidence distinguishes native runs from simulations.

## Tasks

- [x] Reproduce both failures and choose the smallest proof-preserving recovery.
- [x] Implement snapshot and ownership handling with interruption and negative controls.
- [x] Update the contract, compatibility notes and platform limits.

## Agent Execution Graph

Serialize changes in wave_work.py. Architecture/security review examines proof boundaries; QA checks recovery and refusals.

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wave_work.py`
- `.wavefoundry/framework/scripts/tests/test_wave_work.py`
- `docs/specs/mcp-tool-surface.md`
- `docs/contributing/build-and-verification.md`
- `docs/architecture/threat-model.md`

CHANGELOG.md receives recovery and native Windows scope notes.

## Affected Architecture Docs

Update the work-area/review contract in docs/specs/mcp-tool-surface.md, the verification guidance in docs/contributing/build-and-verification.md and the ownership/continuity boundary in docs/architecture/threat-model.md.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Restores snapshot reuse without weaker integrity. |
| AC-2 | required | Fixes ownership without cross-repository adoption. |
| AC-3 | required | Makes platform limits and safe fallback explicit. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-05 | Recover only from positive ownership and link proof. | The reproduced states are distinguishable from arbitrary files; the proof must include concurrency and legacy records. | Always force full review retains the defect; dropping link/path checks permits unsafe reuse. |

## Risks

The current owner schema stores the work-directory identity, not a persistent root identity. Root-move recovery therefore needs a deliberate compatibility design. If old identity cannot be established, preserve the work and explain the safe continuation.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-05 | Implemented positive construction-link reuse and schema2 root/work continuity with legacy-safe preservation.66 development controls pass;3 guard mutants detect bypassed link/root proof or persisted-device equality. Same-filesystem rename/case alias verified locally; native Windows/cross-volume remain unqualified. | delivery-evidence.json; named production tests and guard mutants; full canonical qualification and independent delivery review pending. |
| 2026-11-05 | Readback: recover only proven internal snapshot links and same-repository continuity; preserve foreign/link/substitution refusals and read-only behavior. AC-1–3; no persisted device-ID equality across runs. Implementer owns wave_work.py and its tests; coordinator integrates published contracts/threat model. Legacy uncertainty retains work and a safe remedy. | Current receipt review-policy-9f3ca64efa19fe8cfee4; Implement wave activation succeeded. |
| 2026-11-05 | Planned; both motivating POSIX cases reproduced, Windows behavior not qualified. | Production wave_work in temporary fixtures; link-count and directory-identity checks. |
| 2026-11-05 | Made existing reboot-safe continuity explicit for current and proposed ownership checks; device IDs must not become persistent identity requirements. | Operator constraint; wave_work._read_owner and storage_identity.compare_identity. Pure-helper probe accepts device-only drift and refuses changed inode. |
| 2026-11-05 | Final delivery passed: canonical suite 12,369 tests / 217 files / 12 reported skips; full docs validation and independent required lanes plus Council approve. Four supporting test-fixture repairs were independently verified in cycle 1; no product repair or scope change was needed. | delivery-evidence.json and typed events.jsonl; current receipt 92ad0645. Wave remains open for operator signoff. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
