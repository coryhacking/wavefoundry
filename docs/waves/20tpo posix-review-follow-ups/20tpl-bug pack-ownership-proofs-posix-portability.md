# Pack ownership proofs survive reboots, sessions and link-less filesystems

Change ID: `20tpl-bug pack-ownership-proofs-posix-portability`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-15
Wave: `20tpo posix-review-follow-ups`

## Rationale

Verified-pack cleanup in `upgrade_wavefoundry.py` persists device numbers in `_pack_entry_identity` and requires the pack parent to equal the current process's temporary directory in `_cleanup_verified_pack`. The exact-source scratch control retained an otherwise valid pack after changing that directory. Device drift is an injected portability case; native reboot and filesystem qualification remains outstanding.

Readiness found duplicate scope: **20qrv / 20qrr already owns every index-guard durable-pack and embedded-archive identity consumer, terminal cleanup, and no-clobber publication.** This change owns only the residual verified-pack lifecycle. It introduces no publication fallback and does not edit the readied wave.

## Requirements

1. Only verified-pack cross-run comparisons treat `st_dev` as historical evidence. Keep older five-field proofs readable; require usable inode, size, mtime and ctime plus the existing ownership checks; this temporary-pack consumer has no stored content hash, so do not add another archive hash pass. Device drift alone may be reported without refusal; missing or unusable identity remains a controlled refusal. Fresh within-process identity comparisons retain device and inode.
2. Locate a staged verified pack from its recorded location across session changes, but never treat the path alone as deletion authority. Validate the recorded ownership proof and its owned parent, no-follow ancestry and fresh descriptor-anchored file identity before unlink. Refuse replaced/linked parents or files. Preserve the established owned-location restrictions; do not adopt arbitrary paths from old locks.
3. Absence completes cleanup only for a validated owned location. An unprovable legacy parent or malformed proof retains the pack and yields bounded recovery guidance; it is not silently accepted as absent. Do not inspect or delete unrelated paths.
4. Diagnostics identify the recorded parent kind and safe repository-relative or temp-relative basename, with control characters escaped and no absolute-root disclosure.
5. Implement after 20qrv's pack-proof changes, reconcile its consumer contract without rewriting it, and preserve its no-clobber publication/refusal policy. No `os.replace` publication fallback is admitted here.

## Scope

**Problem statement:** verified-pack cleanup incorrectly depends on the current session's temp directory and durable device number.

**In scope:** `_pack_entry_identity`, `_cleanup_verified_pack`, their proof producer and `phase_cleanup` diagnostics in `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`; focused verified-pack tests and upgrade guidance.

**Out of scope:** all index-guard durable-pack/embedded-archive identities, publication and terminal cleanup owned by 20qrr; new storage identity abstractions; weakening replacement, containment or content checks.

## Acceptance Criteria

- [x] AC-1: Verified-pack cleanup accepts injected device drift with otherwise valid ownership and usable identity; changed inode, size, timestamps, or unusable identity refuses; there is no new content-hashing contract. Old five-field proofs remain readable without granting new ownership.
- [x] AC-2: A changed current temp directory does not prevent cleanup of a proven owned staged pack. Replaced/linked parent or file, forged recorded path and unprovable legacy ownership retain/refuse; validated absence is idempotent.
- [x] AC-3: The implementation leaves all guard-pack identity/publication work with 20qrr and preserves its no-clobber refusal, with a cross-wave consumer regression check.
- [x] AC-4: Retention diagnostics provide bounded, escaped, path-safe recovery information without disclosing an absolute root.
- [x] AC-5: Existing replacement/truncation controls still pass; fresh identity changes between validation and unlink refuse.
- [x] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add failing verified-pack controls for device drift, changed session, ownership/parent substitution, unusable identity, legacy proof, absence and stale descriptor identity.
- [x] After 20qrv, repair verified-pack proof comparison and cleanup only; retain existing ownership gates without a new content hash pass.
- [x] Add safe diagnostics and update the upgrade guidance about retained owned packs.
- [x] Run targeted consumer and adversarial controls before delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Verified-pack proof and cleanup | Implementer | Readiness and 20qrv implementation | Single write owner; guard-pack policy belongs to 20qrr |
| Delivery review | QA, security, release | Verified-pack repair | Confirm ownership and no-clobber contracts remain intact |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py` and its tests: serialize after 20qrv and coordinate with 20ppj.
- Upgrade seed guidance: same write owner.
- No duplicate edits to `upgrade_extensions.py` guard-pack policy.

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` if it names the five-field identity; otherwise N/A. The storage-identity decision record already states the device rule.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Durable proof portability without weaker ownership |
| AC-2 | required | Session-independent safe cleanup |
| AC-3 | required | One owner for guard-pack policy |
| AC-4 | important | Actionable bounded diagnostics |
| AC-5 | required | Preserve fresh replacement protection |
| AC-6 | required | Delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned from the POSIX review of commits 2026-10-01 to 2026-10-15 | Confirmed at HEAD |
| 2026-10-15 | Implementation note on requirement 2's "existing content hash": the verified-pack proof today records only `path` and the identity tuple (`_stage_pack_for_consumption` writes `{"path", "identity"}`), so no existing hash applies to this consumer. Do not add a new hash pass over the pack before deleting the framework's own temporary; fresh descriptor-anchored identity inside the validated owned parent is the deletion gate. Operator rule: favor reduced work while maintaining quality. | Cross-wave plan review; no requirement or AC changed |

| 2026-10-15 | Owning Requirements and AC-1 corrected to match the actual path/identity-only verified-pack proof. Preserve existing checks and add validated parent ownership without a redundant archive hash pass. This supersedes the inaccurate reference to an existing content hash; affected readiness is refreshed before cleanup edits. | _stage_pack_for_consumption actual source and prior implementation refinement |

| 2026-10-15 | Implementer preflight after corrected owning requirements and refreshed readiness: current verified cleanup compares durable device fields and current TMPDIR, lacks retained parent proof, and does not compare a freshly opened final file descriptor. Add recorded temporary-parent coordinates/usable identity to new proofs, preserve old five-field proofs only within established current-temp ownership, separate durable comparison from fresh descriptor checks, and bound escaped retention guidance. No new archive hash pass. Original-source scratch reproduction had six failures / zero errors across eight tests; proposed in-memory implementation passed all eight. | Corrected Requirements/AC read; coordinator confirms current seven lanes plus council readiness before source edits |

| 2026-10-15 | Implemented residual verified-pack ownership only after refreshed readiness. New staging proofs retain five-field file identity and add recorded temporary-parent kind/canonical locator/usable identity; producer refuses adopting or deleting a post-validation replacement. Cleanup accepts durable device drift only, keeps legacy present files within the established current canonical temp location, refuses unprovable legacy parent/absence, and anchors no-follow ancestry, final open/stat and unlink with fresh device-inclusive checks. Bounded diagnostics escape parent/archive basenames and disclose no absolute roots; no extra archive hash pass. | New suite 11 green; existing reporting/emitter replacement controls plus qrr portability suite 14 green; two guard terminal TMP/retry consumers plus new suite 13 green; diff-check clean |
| 2026-10-15 | Seven named in-memory guard mutants detected, each by assertion failure with zero test errors: durable-device equality, omitted parent authority, omitted fresh-device check, omitted final identity check, staging replacement adoption, widened legacy scope and unescaped diagnostics. Guard-pack publication/identity code and qrr embedded callback remain unchanged. Coordinator confirmed the guidance paragraph landed in native-windows-support.md, including unchanged normal staging validation/expected-hash checks; batch-wide full-suite/docs gate remains open. | /private/tmp/tpl-verified-pack-mutants.py; native reboot/Windows/WSL2 execution unverified |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Narrow to verified-pack lifecycle; 20qrr owns guard packs | Readiness TPO-RD1 found duplicate scope and contradictory publication policy | Duplicate guard fixes and reserve-then-replace rejected: a competing file can be overwritten |
| 2026-10-15 | Recorded location is a locator, not deletion authority | Cross-session cleanup still requires proven parent/file ownership and fresh identity | Trust path alone rejected |

## Risks

| Risk | Mitigation |
| --- | --- |
| Device drift masks a different file | Usable remaining identity, ownership and fresh descriptor checks remain mandatory; no new archive hash pass |
| Old proof lacks sufficient parent evidence | Retain with controlled recovery; do not infer ownership |
| Cross-wave consumers drift | Implement after 20qrv and test the consumer contract; preserve readied records |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
