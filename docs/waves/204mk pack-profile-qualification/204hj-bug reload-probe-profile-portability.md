# Make packaging qualification fixtures profile-independent

Change ID: `204hj-bug reload-probe-profile-portability`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-08
Wave: 204mk pack-profile-qualification

## Rationale

The operator requested a fresh 1.29.0 local test pack. Its second-profile qualification reproduced a failure in LifecycleIdReloadTests before the real reload: the probe assumes EXTRA_CHANGE_KINDS is an empty tuple. Repair this test fixture while preserving meaningful reload regression coverage, then resume packaging. The operator explicitly chose a new repair wave over waiving the failed packaging check.

## Requirements

1. Make the lifecycle reload probe work with the active vocabulary profile's extra change kinds and declaration formatting. Preserve existing kinds while adding a valid test kind absent from the initial choices.
2. Continue exercising the real thin runner reload in an isolated copied scripts tree. Verify the new kind becomes available and the reimported validator binds the fresh lifecycle_id module.
3. Keep an observable before/after distinction and prove a broken reload is detected; do not skip the probe under non-default profiles or weaken its result assertions.
4. Record focused default, second and declared profile results and any full-suite qualification failures separately from this fixture's assertions. Update the current changelog and return to the requested local pack after the packaging checks pass.

5. Isolate the stock-surface first-render identity fixture from distribution extension declarations. Preserve its original first-render zero-write and whole-tree byte-identity assertions; do not pre-render the tree to hide drift or add a profile skip.

## Scope

**Problem statement:** A hardcoded empty declaration prevents the second-profile reload regression from reaching the behavior it intends to test.

**In scope:** `_RELOAD_PROBE` and its owning test in `test_distribution_seams.py`; `DefaultRenderIdentityTests` in `test_vocabulary_prompt_names.py`; directly needed test support if inspection justifies it; change/wave evidence and the 1.29.0 changelog.

**Out of scope:** Production reload behavior, vocabulary contracts, hook work, uv pin changes, timeouts or concurrency policy changes, release publication, commits and wave closure.

## Acceptance Criteria

- [x] AC-1: The reload test reaches and passes its real reload assertions with the shipped, second and declared profiles, preserving existing declared kinds; evidence is the owning test's executed output in each profile.
- [x] AC-2: The same regression fails when lifecycle_id refresh is deliberately disabled, showing a new kind is absent before reload and present only after correct reload; evidence names the mutated path and failing assertion.
- [x] AC-3: The repair stays within test infrastructure and records accurate qualification and release-note evidence without changing runtime reload behavior or adding profile skips.

- [x] AC-4: The stock-surface identity test passes under default and declared profiles with its first-render zero-write and tree-digest assertions intact, and detects deliberately stale copied surface bytes.

## Tasks

- [x] Complete independent readiness and record typed approvals.
- [x] Repair the reload and stock-surface fixtures and verify positive and negative paths.
- [x] Run the canonical suite and serial packaging profiles; investigate any remaining failures.
- [x] Complete independent delivery review, docs validation and packaging handoff.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Readiness | Independent council and reviewers | Plan | Standard primer; separate review contexts |
| Implementation | Coordinator implementer | Readiness | One test owner; serialized writes |
| Delivery | Independent code and QA reviewers | Verification | Executed public reload and negative control |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_distribution_seams.py`
- `.wavefoundry/framework/scripts/tests/test_vocabulary_prompt_names.py`

The coordinator owns source and changelog writes. Reviewers read only and return evidence. Full canonical suite runs with all repository writes frozen; full profile suites run serially after the initial concurrent qualification finishes.

## Affected Architecture Docs

N/A: test-fixture repair preserves the existing runtime reload contract and verification seam; no architecture or production interface changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Restores profile qualification without deleting its behavioral coverage |
| AC-2 | required | Prevents a portable but vacuous reload test |
| AC-3 | required | Keeps the repair and release claims bounded |
| AC-4 | required | Keeps the stock-surface drift oracle independent of added distribution skills |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-08 | Second-profile full run and focused reproduction fail at `assert text.count(old) == 1`; the default cached suite matches 11,894 tests. Concurrent full profiles also hit docs-lint's 600-second timeout; serial reruns will distinguish load from defects. | /tmp/wf-129-pack-seams.log; /tmp/wf-129-pack-second.log; /tmp/wf-129-pack-declared.log |

| 2026-10-08 | Declared-profile identity fixture copies stock surfaces but uses the added dist-review declaration; real renderer correctly writes its prompt and three skills. Scope adds this fixture isolation while retaining first-render drift detection. | /tmp/wf-129-pack-declared.log; DefaultRenderIdentityTests |

| 2026-10-08 | Readback: preserve active reload kinds and select an absent test kind; retain real reload and exact fresh-choice/binding assertions. Reuse base_declaration for copied stock surfaces, retaining first-render zero-write/digest checks. Only two test files change; runtime is unchanged. Current typed readiness complete; framework gate open. | AC-1–4; readiness-council.md; lane-readiness.md |

| 2026-10-08 | AC-1–4 verified: default/declared owner runs72 tests0skips, second67 reported4 existing guards. Real lifecycle-only eviction mutant fails freshness after successful reload; stale copied skill fails first-render zero-write; probe0 collision selects probe1 and preserves extras. Independent code review16 valid-format cases and14 killed controls. Runtime untouched; current changelog records bounded claims. Full-suite gates pending. | code-delivery.md; qa-delivery.md; typed code/QA delivery approvals |

| 2026-10-08 | Full canonical run passed11,894 tests/174 files/20 skips in472.467s; serial second passed11,886/174/53 skips in574.900s; serial declared passed11,894/174/39 skips in534.518s. Initial concurrent timing/timeout failures did not recur. Strict packaging skip parity is not established: declared has19 extra skips (4 historical Git,14 local graph,1 blanket named-profile guard); second further14 are consistent with default-only guards, exact overlap inferred. Local-pack exception requested; no archive built yet. | /tmp/wf-204mk-canonical.log; /tmp/wf-204mk-second.log; /tmp/wf-204mk-declared.log; qa-delivery.md skip audit |

| 2026-10-08 | Built local test pack1.29.0+pvbx under the approved skip-parity exception. ZIP CRC passes; embedded VERSION and manifest revision agree; packed changelog equals root; renamed lifecycle seed present and old name absent; executable bridge present. SHA-2561b3b5149481b29f84ebe6d6b4ad19785bcdf5af1d113b71f285dc5c4e6be178e. | /Users/coryhacking/.wavefoundry/dist/wavefoundry-1.29.0.pvbx.zip; /tmp/wf-204mk-pack.log |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-08 | Preserve the active profile and modify only the scratch declaration for a new kind. | Exercises the real distribution environment while restoring setup portability. | Reset to shipped defaults: loses profile coverage. Skip second-profile test: hides the regression. Change production reload: unsupported by the observed setup failure. |

| 2026-10-08 | Isolate the stock renderer fixture from extension declarations. | Its subject is the shipped first-render identity, not added distribution surfaces. | Pre-render: could hide drift. Add a declared-profile skip: reduces coverage. Change renderer: its extra writes are correct. |

| 2026-10-08 | Operator approved building the local 1.29.0 test pack with the 19 extra declared-profile skips disclosed. | All three full suites pass; this is a local-testing exception to strict profile skip parity, not release qualification. | Fixing the scratch-profile qualification gap remains separate work. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A portable fixture can pass without exercising reload | Verify the precondition and fresh module binding; execute a broken-reload control |
| Test kind collides with a distribution kind | Select a valid kind absent from initial KIND_CHOICES |
| Concurrent full suites hit resource timeouts | Re-run full packaging profiles serially without changing timeouts |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state. Return to the local 1.29.0 pack after repair and validation; closure and commits require operator instruction.
