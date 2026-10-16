# Repair upgrade recovery and PATH diagnostic edge cases

Change ID: `20tzr-bug upgrade-recovery-and-path-diagnostic-edge-cases`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-15
Wave: `20tzs upgrade-recovery-edge-case-follow-ups`

## Rationale

Four bounded defects remain after the rerun and portability batch: legacy temporary-pack paths do not survive macOS lexical aliases, selected archive/recovery guards reject non-surrogate reparse metadata, a post-publication read error can leave a guard-pack slot without recorded ownership, and ordinary PATH misses crowd genuine uv refusal reasons out of the bounded diagnostic. Repair these in one follow-up change without reopening or revising the original waves.

Current source anchors are `_cleanup_verified_pack` in `upgrade_wavefoundry.py`; `retain` and `_retained_path` in `embedded_model_bundle.py`; `_guard_owned_path`, `_retain_index_guard_pack`, and `enforce_index_guard_handoff` in `upgrade_extensions.py`; and `_trusted_path_uv` in `setup_index.py`. Source inspection also found the same raw reparse-attribute check in `_preserve_original_manifest`, reached by `pre_extract`; it belongs to the small recovery-path census rather than a repository-wide reparse rewrite.

Two executed disposable controls confirm the legacy-parent and diagnostic failures: a real mkstemp legacy proof has a lexical `/var` parent and is retained, while the equivalent canonical-parent control cleans up; five ordinary empty PATH directories fill all diagnostic slots before a repository-controlled uv entry is refused. No installed target or repository source was modified. Post-publication behavior and remaining reparse sites were verified from source, not claimed as executed reproductions in this planning pass.

## Requirements

1. **Legacy temporary parent:** accept a valid prior-release path/identity-only proof whose existing parent canonically equals the current configured temporary directory, including macOS `/var` versus `/private/var`. Canonicalize the parent used by the subsequent descriptor walk, not merely the comparison. Validate the original proof/path binding first, never resolve through the final file, and preserve fresh identity, no-follow, basename, replacement, unrelated-parent and legacy-absence refusals. Recorded-parent proofs and cross-session behavior remain unchanged.
2. **Recovery-path reparse classification:** use the existing name-surrogate contract at combined-archive source/parent/final checks and guard-pack source/recovery checks, including the manifest-preservation path when reached by the same pre-extract flow. Valid non-surrogate tags pass link classification; symlinks, known or unknown surrogate tags, and unclassified reparse metadata still refuse. Retain regular-file, containment, size, link-count, identity and hash guards. Preserve the stdlib/old-runner boundary: do not assume the older process can import a newly added sibling API. Reuse the canonical helper where available; any necessary old-runner-compatible copy must join the existing exact parity control.
3. **Failure after exclusive publication:** hold the creation descriptor through exclusive hard-link publication, private-name removal and read-back. Compare the target's read-back identity with the fresh held descriptor even on success; matching bytes alone do not confer ownership. Capture current proof metadata after private unlink changes link count/ctime. On a post-publication error, attempt fresh identity-checked rollback of only this invocation's file. If rollback is refused but the private name is gone and the same exclusively owned regular inode is positively proven, bind its expected hash and root/token/version through the existing checkpoint format, persist that checkpoint and report validation unavailable with the ordinary continuation. A later normal retry must validate fresh identity and hash before executing archive code. Never bind a replacement or a hash mismatch, adopt an occupied filename, overwrite a slot, or unlink a competitor. If proof is unavailable, a private hardlink remains, or checkpoint persistence and rollback both fail, stop with an explicit manual-recovery error, preserve the original package/checkpoint and make no automatic-resumability claim. Do not add a receipt, journal or sidecar. A transient read-back error alone must not strand an unowned slot or silently become generic capability fallback.
4. **Useful bounded uv diagnostic:** ordinary PATH directories with no candidate do not consume the five refusal slots. Report actual trust/safety refusals, including a repository-controlled entry appearing after several ordinary misses. Preserve escaping, length/count bounds, lookup order, executable selection, empty/relative entry refusal, unknown-target CWD conservatism and existing bootstrap guidance. Never execute candidates during discovery.
5. **Preservation:** do not change long-path WinError 3 classification, generation-based declaration caching, the existing predicate semantics/parity, hook digest invalidation, or unreadable-directory lock-scan policy. Timing investigation, thresholds, receipt exceptions and native qualification remain outside this change.

## Scope

**Problem statement:** existing recovery/lookup paths mishandle aliases, reparse metadata, partial publication and diagnostic budgeting at four specific boundaries.

**In scope:** the four implementation modules named above, existing contained-file helpers only if required for those call sites, focused existing regression modules, changelog and narrowly affected support guidance.

**Out of scope:** reopening original waves; new ownership authorities, broad cleanup/refactor machinery, new persistent evidence artifacts, inference/model behavior, hook or scan redesign, timing policy, and native OneDrive/Windows/reboot qualification claims.

## Acceptance Criteria

- [x] AC-1: A faithful prior-release legacy proof under a macOS-style temporary-parent alias cleans up its owned file and lets terminal cleanup progress. Equivalent parent spellings work; unrelated parents, final links, replacements and unproven legacy absence remain refused. Verify both the direct helper and its terminal cleanup consumer with disposable fixtures.
- [x] AC-2: The admitted archive/recovery call sites accept valid non-surrogate metadata while refusing surrogate and unclassified metadata. Existing containment/hash/identity failures still refuse; the existing parity control covers any necessary compatibility copy. Exercise source selection, retained resume/cleanup and the old-runner pre-extract path with explicit simulated-platform limitations.
- [x] AC-3: An injected post-publication read-back error rolls back the owned slot, or, when rollback is refused but exclusive ownership and checkpoint persistence remain provable, retains a checkpoint-bound slot that a normal retry validates and completes. Verify held-descriptor identity on successful read-back too. Exercise rollback success/refusal, retry, private-unlink failure, competing/replaced targets, hash mismatch, unavailable proof and checkpoint-write failure. Compound proof/rollback/persistence failures stop explicitly with original package/checkpoint preserved and no automatic-resumability claim. No foreign entry is overwritten/unlinked, no occupied name grants ownership, and no error path claims verification success without proof.
- [x] AC-4: Five ordinary missing-candidate PATH entries followed by a repository-controlled uv produce a visible bounded repository-refusal reason. Valid external uv selection and existing trust/refusal/escaping/bootstrap controls retain their outcomes without executing a candidate.
- [x] AC-5: The preserved policies in Requirement 5 retain their current behavior; existing relevant compatibility, predicate-parity and ownership tests pass without loosening assertions or adding exemptions.
- [x] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change. Full-suite receipt and release qualification remain separate existing gates, with timing limitations reported honestly.

## Tasks

- [x] Trace the small archive/recovery call-site set, current helper availability and old-runner boundaries; confirm the selected held-descriptor rollback/existing-checkpoint route and its explicit compound-failure boundary before code edits.
- [x] Repair legacy-parent normalization and add direct/terminal-consumer alias and refusal controls.
- [x] Apply the shared reparse classification to admitted recovery sites and extend existing parity/compatibility controls as needed.
- [x] Repair post-publication failure handling, identity-checked rollback and existing-checkpoint retry; add failure/replacement/no-clobber controls.
- [x] Keep ordinary PATH misses out of the refusal budget and add the late-repository-entry regression.
- [x] Update the changelog and affected existing support guidance; run targeted preservation checks and required independent delivery review.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Readiness | Coordinator and required reviewers | Plan admission | Verify exact recovery route and old-runner imports before edits |
| Bounded repairs | One implementer | Readiness | Serialize upgrade_extensions.py and shared ownership helpers |
| Delivery | Code, QA, security, architecture, release and docs reviewers | Repairs | Current-source and registered-path controls; no native or timing claims |

## Serialization Points

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/embedded_model_bundle.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/contained_files.py`
- `.wavefoundry/framework/scripts/tests/test_verified_pack_portability.py`
- `.wavefoundry/framework/scripts/tests/test_archive_ownership_portability.py`
- `.wavefoundry/framework/scripts/tests/test_trusted_executable_lookup.py`
- `.wavefoundry/framework/scripts/tests/test_windows_path_guards.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `docs/references/native-windows-support.md`

The changelog is updated as release narration. No seed, prompt, AGENTS.md or generated hook edits are intended. Reviewers read; the implementer owns the named code/test edits only after readiness. Preserve the existing source receipt and review workflows.

## Affected Architecture Docs

`docs/references/native-windows-support.md`: refine existing archive recovery/retention guidance if changed by the repair. `docs/architecture/cross-cutting-concerns.md`: update only if its current ownership/classification contract needs clarification. No new authority, dependency direction or data format is intended; architecture review must reject an unexplained expansion.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Prior-release interrupted upgrades are the compatibility window being repaired |
| AC-2 | required | A non-surrogate tag must not masquerade as a path redirect |
| AC-3 | required | Prevent silent ownership loss after publication without adopting foreign files |
| AC-4 | required | Bounded diagnostics must retain the refusal they exist to explain |
| AC-5 | required | The rejected claims and approved policies are not defects to change |
| AC-6 | required | Change-local qualification and truthful gate evidence |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Replacement qualification also passed all 11,838 tests / 200 files / 12 existing skips in 744.159s. Its only failure was concurrent authored changes in another session's wave 20tpp; no 20tzs or reviewed source path was flagged. Implementation/review are complete and paused; green receipt remains withheld. Await coordination before any further full run; do not revert or absorb the other session's edits. | /private/tmp/20tzs-final-qualification.log; reviewed source aggregate unchanged; coordination question pending |
| 2026-10-15 | All 11,838 tests / 200 files / 12 existing skips passed in 845.377s. Overall qualification failed solely because the coordinator appended authored Review checkpoints during the run; ledger and generated views independently validate. No source change or test failure caused it. AC-6 change-local tests/docs/no-attributable-failure is met; the mandatory green receipt is still withheld. | /private/tmp/20tzs-full-suite.log; live runner canonical-ledger/generated-view checks; no fabricated receipt |
| 2026-10-15 | Finish the authored review summary and handoff before qualification, then rerun with records settled. Do not change Review checkpoints, standalone handoff or edit gates during that run. This is coordination repair, not another source/review cycle or timing retry. | Existing authoring/qualification discipline; reviewed source remains c0922b039d3f0319ad1bf99ad8cb21c7707f5712dba5225104571d8caebfa352 |
| 2026-10-15 | Independent delivery approved all six required lanes and targeted council with zero findings. Code/QA/security/architecture/release/docs used current contracts and in-memory prior-code or narrowed guard mutants; no mutant survived. | Frozen 11-path aggregate c0922b039d3f0319ad1bf99ad8cb21c7707f5712dba5225104571d8caebfa352; typed delivery approvals; /private/tmp/20tzs-delivery-review-index.json |
| 2026-10-15 | Readback consolidation: pre-edit operator updates described the four intended repairs and preserved proof/compatibility boundaries. For example, read-back failure previously stranded an unowned slot; now it rolls back or persists provable existing-format ownership, with explicit compound failure. This consolidates execution narration, not a new scope or approval. | Requirements 1–5 and the independently reviewed current source; no new review round |
| 2026-10-15 | A noncanonical handoff paragraph edit rotated readiness despite no functional plan change. Chair and original docs context confirmed bookkeeping-only continuity; original approvals were explicitly rebound by reference, without another plan review or suite. Future continuation stays in Progress Log or the standalone handoff. | Current readiness receipt review-policy-03fc3b3d7c6caf9237b7; original independent contexts retained honestly |
| 2026-10-15 | Canonical isolated focused run passed 509 tests across nine modules in 84.086s, with one existing platform skip. In-process invocation is not qualification. All named preservation controls passed, including the exact fresh-identity census. | /private/tmp/20tzs-focused.log; no framework receipt written by focused mode |
| 2026-10-15 | Implemented four repairs. Alias/uv focused modules: 23 tests; archive ownership: 29 tests; Windows metadata parity: 3 tests, all green/no skips in isolated module runs. Five in-memory old-code/incomplete-fix mutants were detected. | Existing regression modules, direct legacy cleanup and terminal consumer, real guard handoff and synthetic Windows API/metadata controls |
| 2026-10-15 | Held-descriptor Windows sharing required a narrow handle-based ReOpenFile adapter before publication, independently checked against Microsoft API/CRT contracts. Exact identity census in test_sqlite_storage_migration.py now lists only the five added fresh comparisons; no wildcard/exemption or historical-device semantics changed. | Seed-180 focused implementation checkpoint; native execution remains unverified; source/spec distinction retained |
| 2026-10-15 | Discarded a combined in-process test invocation as qualification: test modules intentionally replace imported module state. The actual identity census correctly found five new exact comparisons; its explicit inventory was updated under the admitted compatibility task. Canonical per-file isolation is running. | In-process run: 481 tests, 9 failures/19 errors/1 skip, mixed harness interference and census drift; no green claim |
| 2026-10-15 | Current readiness passed all six lanes and targeted council; implementation opened. Write ownership: alias/uv implementer owns those two modules/tests; coordinator owns archive/classification and shared review records. | Receipt review-policy-eb3b8eaf94062a6ab011; no source edit before successful Prepare |
| 2026-10-15 | One bounded readiness repair made Requirement 3 and AC-3 concrete: held-descriptor identity, rollback first, existing checkpoint only when provable, explicit compound failure. All six initial lanes reported one deduplicated finding. | Typed readiness finding 20tzs-readiness-ac3-compound-failure; source and disposable handoff probe |
| 2026-10-15 | Planned one consolidated bug change for the four source-confirmed follow-ups. Two disposable probes reproduce alias retention and refusal-budget crowding; current production code remains unchanged. | Named source anchors and existing regression modules; no copied intake report or permanent probe artifact |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Keep post-publication read-back and use the existing checkpoint only for positively proven retained ownership | Preserves verification and normal retry validation; compound filesystem/persistence impossibility must remain an explicit safe failure | Removing read-back changes a verification guarantee; new recovery sidecars introduce an unnecessary authority |
| 2026-10-15 | Select bounded repairs using existing helpers/proof/checkpoint formats | Covers the actual alias, classification, partial-publication and diagnostic boundaries without a new authority layer | Minimal line substitutions miss the later no-follow walk and post-publication ownership window; a new journal/transaction/cleanup framework adds retained state and complexity beyond these four defects |
| 2026-10-15 | Keep one follow-up wave with one consolidated bug change | These small repairs share upgrade recovery boundaries and can be reviewed/qualified together | Four separate waves add lifecycle overhead; reopening prior waves conflates settled scope and the separate timing receipt hold |
| 2026-10-15 | Preserve the explicitly reviewed policies | Long-path hints, generation invalidation, predicate parity, digest-lapsed hooks and unreadable-directory refusal are intentional contracts | Changing them on speculative review claims would regress approved behavior |

## Risks

| Risk | Mitigation |
| --- | --- |
| Resolving a whole file path legitimizes a final link | Normalize only the authorized legacy parent; keep final no-follow and fresh identity checks |
| New helper import is missing in an older runner | Verify incoming helper provenance or pin an exact compatible rule copy with parity |
| Rollback unlinks a competitor, or a failed read loses ownership | Prove invocation ownership and fresh identity; preserve competing entries and existing checkpoint recovery authority |
| Non-surrogate acceptance weakens other guards | Change classification only; retain regularity, containment, size, links, identity and hashes |
| Tests overclaim native support | Label metadata/error injection and macOS/POSIX controls accurately; native probes remain unverified |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state and the Progress Log above for current execution evidence.
