# Embedded archive and index-guard ownership on native Windows

Change ID: `20qrr-bug embedded-archive-ownership-on-windows`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-15
Wave: `20qrv windows-review-follow-ups`

## Rationale

The embedded archive cleanup assumes descriptor-relative deletion, which native Windows does not provide. Index-guard retention and persisted archive identities also need explicit capability/error handling and consistent cross-run validation. These are source-grounded portability concerns; native Windows, reboot and WSL2 qualification remain pending.

Readiness corrected the alleged `os.link(..., follow_symlinks=False)` failure: CPython 3.13's Windows branch calls CreateHardLinkW; lack of linkat alone does not establish that argument raises NotImplementedError on Windows. A capability-failure oracle tests graceful refusal, not that platform claim. Scratch controls demonstrate that a precheck followed by `os.replace` can overwrite a competing destination and is not a valid exclusive-publication fallback.

## Requirements

1. Preserve POSIX descriptor-anchored cleanup. On hosts lacking the necessary operations, use the existing bounded by-path fallback pattern: validate every parent and final entry without following links/name-surrogate reparse points, verify containment and ownership, revalidate immediately before unlink, and retain on unknown identity, unsafe parent, permission or I/O failure. Disclose the residual same-user pathname race; do not call it descriptor-equivalent safety.
2. Distinguish capability fallback from ownership refusal. A successful proved cleanup returns True; genuine retained cleanup includes a truthful reason. No unconditional deletion to make cleanup succeed.
3. Publish index-guard packs with atomic no-clobber hard-link creation where supported. Never use `os.replace` over an occupied or raced destination, and never adopt it by name. When safe publication is unavailable (OSError or unsupported-operation error), preserve recovery and return the existing controlled restart/refusal guidance with reason; remove only the owned temporary. No new fallback publication primitive.
4. Separate durable cross-run identity from fresh same-open deletion identity. Inventory all embedded proof consumers (`retain`, `validate_retained`, `cleanup`) and index-guard consumers (`_validate_index_guard_handoff`, `_guard_file_identity`, `_retain_index_guard_pack`, `validate_index_guard_durable_pack`, `validate_index_guard_terminal_cleanup`, `finalize_index_guard_terminal_cleanup`). Persisted root/file comparisons may ignore legacy device fields while retaining canonical root/locator, inode, size/time and content hash as applicable; old proofs remain readable. Missing/zero/unusable identifying fields remain unproven, not wildcard matches. Never remove device checks globally from fresh descriptor/path comparisons.
5. Terminal unlink derives its expected identity from freshly validated current filesystem metadata, not a legacy persisted proof slice. Re-prove ownership and hash before cleanup; wrong root/token/locator/hash/inode/size/mtime remains refused. Cover retained validation, resume and terminal cleanup together with changed-device oracles.
6. Tests simulate capability and identity differences; they do not prove a real Windows or WSL2 reboot succeeds. Name native cleanup, interrupted-retain/resume and reboot probes for operator qualification. On volumes without safe no-clobber publication, controlled refusal is the supported outcome.

## Scope

In scope: embedded_model_bundle.py owned archive lifecycle; the named upgrade_extensions.py retained handoff/root/file/terminal consumers; upgrade_wavefoundry.py cleanup reporting only as needed; focused tests and native-windows-support.md. No pack-format, byte-ceiling, generic identity-helper weakening or retired-graph cleanup change (20ppj owns the latter).

## Acceptance Criteria

- [x] AC-1: Capability-limited cleanup removes a matching owned archive and returns True; changed final identity, unsafe parent/reparse entry, unproven identity and injected I/O errors preserve it with a truthful reason. Successful cleanup emits no retained message.
- [x] AC-2: No-clobber guard publication preserves occupied and raced destinations byte-for-byte; unsupported link/OSError paths produce controlled guidance without traceback, preserve recovery and remove only owned temporaries. No `os.replace` publication fallback exists.
- [x] AC-3: Legacy proofs carrying a different device field pass durable comparison only when all remaining ownership and hash checks match, through both embedded and index-guard resume and terminal-cleanup consumers. Wrong root/token/locator/hash/inode/size/mtime and unusable identity fail. Fresh deletion identity still includes the current device as applicable.
- [x] AC-4: Existing POSIX descriptor cleanup/link tests pass unchanged, including identity replacement controls.
- [x] AC-5: Focused tests and docs pass; no attributable regression. Native Windows/WSL2 results are explicitly unverified, with named operator probes.

## Tasks

- [x] Add capability/no-clobber, unsafe-parent and current-identity regressions before code changes.
- [x] Implement bounded fallback cleanup and controlled no-clobber publication refusal.
- [x] Census and reconcile every named durable identity consumer, keeping backward-readable proof and fresh deletion checks separate.
- [x] Run focused POSIX and synthetic platform controls; document three native operator probes without claiming they ran.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Embedded bundle | Implementer | Readiness | Single write owner |
| Index guard | Implementer | Readiness | Same owner; separate file |
| Delivery review | QA, security, required reviewers | Both | Read-only; security-faithfulness on the ownership checks |

## Serialization Points

- `.wavefoundry/framework/scripts/embedded_model_bundle.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

N/A. Both lifecycles keep their published contract; only the Windows branches gain an implementation. `docs/references/native-windows-support.md` should gain one paragraph on where the retained archive lives and that it is removed at cleanup.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Disk leak on every Windows upgrade |
| AC-2 | required | Traceback instead of operator guidance |
| AC-3 | required | Resume after reboot |
| AC-4 | required | POSIX path must not weaken |
| AC-5 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned from Windows source review; no native execution claimed | Current source |
| 2026-10-15 | QRV-RD1/RD2 corrected Windows link premise, exclusive publication and durable/fresh identity contracts. | Bounded readiness repair; owning requirements and ACs |
| 2026-10-15 | Reconciliation note: this change gives the embedded archive a bounded by-path cleanup on hosts without descriptor-anchored deletion, while `20og5` (wave `20ppj`) retains the retired graph folder permanently on the same hosts. The asymmetry is deliberate: the archive can reach the pack byte ceiling; the graph folder is a few bounded files under a prior descriptor-only decision. | Cross-wave plan review; no requirement or AC changed |

| 2026-10-15 | Implementer readback: embedded cleanup currently assumes descriptor deletion; durable embedded and guard proofs compare cross-run device fields, and guard link publication has no controlled capability refusal. Preserve fresh device checks and POSIX descriptor anchoring, add bounded no-follow path cleanup only where unsupported, compare durable identities without legacy device equality, and derive terminal unlink identity freshly after hash validation. Verify failing synthetic controls before repairs, existing POSIX controls and named guard mutants; native probes remain unrun. | Requirements 1–6 and AC-1–5 read before code edits; owns embedded and named guard consumers only |

| 2026-10-15 | Implemented strict durable/fresh ownership separation across embedded retain/validate/cleanup and all named guard consumers. Durable comparisons ignore only legacy device equality and require usable positive identity fields; fresh reads/deletion preserve device checks. Embedded cleanup uses existing contained-file descriptor unlink or its bounded no-follow path fallback and reports a path-free retention reason; coordinator updated cleanup reporting. Guard publication uses only exclusive hard-link creation, retains occupied/raced slots, and turns unsupported/OSError publication failures into controlled guidance. Terminal cleanup revalidates ownership/hash and derives unlink identity from freshly opened metadata; terminal bindings remain validated after deliberate archive absence. | New portability suite 12 tests green; existing index-guard 45 tests passed in the combined 97-test run; upgrade protocol rerun 44 green after preserving existing source-link OSError; model bundle 29 green in a 40-test run with then-11 portability tests |
| 2026-10-15 | Six named in-memory guard mutants were detected: embedded durable-device equality, fresh-device omission, fallback final-identity omission, terminal persisted-device unlink, unhandled link capability, and omitted terminal live-file validation. Existing POSIX occupied/raced/no-clobber and descriptor replacement controls passed unchanged. Native cleanup, interrupted retain/resume and reboot continuity probes are documented by the coordinator; Windows/WSL2/reboot execution remains unverified and by-path cleanup retains the disclosed same-user race. | /private/tmp/qrr-ownership-mutants.py; git diff --check clean; batch-wide full-suite/docs gate left to coordinator |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Preserve no-clobber creation; controlled refusal when unavailable | A precheck plus replace can destroy a competing file | New publication abstraction and replacement fallback rejected |
| 2026-10-15 | Separate durable identity comparison from freshly proved cleanup identity across all consumers | Device changes must not weaken current ownership checks or leave terminal cleanup inconsistent | Global device-field removal rejected |

## Risks

| Risk | Mitigation |
| --- | --- |
| By-path cleanup has a residual same-user race | Check parent chain, containment and current ownership; retain on uncertainty; document weaker fallback guarantee |
| Synthetic controls differ from native behavior | Native Windows, WSL2 and reboot probes remain release qualification obligations |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
