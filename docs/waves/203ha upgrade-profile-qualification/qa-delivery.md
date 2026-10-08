# QA qualification — 203ha

Owner: Engineering
Status: active
Last verified: 2026-10-08

Verdict: approved for QA delivery. AC-1 through AC-4 have verification evidence. Delivery review was started by the coordinator before this final judgment.

Reviewed source: `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`. Start and end `git hash-object`: `f89d39d7dd3bea415852c8d8f7b7a802bc110925`. No source edits were made by this reviewer. The coordinator may update documentation outside this frozen source boundary.

## Evidence

Independent QA worker read the admitted ACs, QA role, review workflow, source diff, and relevant test ranges through confirmed callable MCP `code_outline` and `code_read`. The independent reference is the admitted promise: invalid replacement names cannot reach phase 2c; historical prompt bytes survive migration exactly; active-profile carriers exist before indexing, preserve project extensions, and remain stable on repeated rendering.

Executed `/tmp/wf-qa203ha.py`, creating a private framework copy and applying the canonical `record_layout_support.apply_profile` producer with the checked-in `prompt-names` profile. The copy reported `docs/prompts/plan-task.prompt.md` and `docs/prompts/review-batch.prompt.md`. Five selected tests passed with zero skips in 1.907 seconds; log: `/tmp/wf-qa203ha.log`. These are diagnostic checks, not a canonical release receipt.

| AC | Own executable evidence |
| --- | --- |
| AC-1 | Both invalid-profile tests passed, including alternate Batch assignments with single and double quotes. Assertions retain exception identity/cause checks and downstream nonexecution. |
| AC-2 | Installing-upgrade rename test passed under prompt-names, asserting exact original CRLF bytes, exact profile-specific manifest rows, new skills, and removed historical artifacts. |
| AC-3 | Surface-phase integration passed with actual renderer subprocesses, exact project prefix/suffix preservation, a second rendering with byte equality, and profile-specific carriers. The unchanged unwired integration negative reached `main` and detected absent carriers at the index boundary. Separate real-render probe without a manifest produced the expected migration-skipped NOTICE and did not create `review-batch.prompt.md`. |
| AC-4 | Independently read both complete owner/profile logs: each 681 tests, two existing skips, zero failures/errors. Read quiet canonical log: 11,885 tests across 173 files, 20 existing skips, 431.917 seconds, OK. Read final handoff coverage table, qualification evidence and explicit adoption limits. Independently verified receipt result and current framework hash match. |

## Mutation and negative-control table

| Control | Expected | Observed |
| --- | --- | --- |
| Omit post-extraction profile refresh | Invalid-profile assertion fails | Detected: `RuntimeError not raised`. |
| Invoke downstream guard before profile rejection | Nonexecution assertion fails | Detected: unexpected `enforce_index_guard_handoff` call. |
| Append corrupt bytes to migrated plan prompt | Exact byte assertion fails | Detected: expected CRLF bytes differed by appended `corrupted` text. |
| Inject unwired surface phase in full upgrade | Index-boundary carrier assertion detects missing carrier | Test passed by catching the expected `known-bad upgrade` assertion at `phase_index_update`; zero skips. |
| Omit prompt manifest from otherwise canonical staged seeds | Profile prompt migration refuses materialization | Renderer NOTICE names absent manifest; renamed review carrier absent. Surface phase itself returns normally. |

The first three mutations were independently executed in the QA prompt-names copy using the coordinator-authored `/tmp/wf-profile-repair-controls.py` after inspecting its mutation and assertion logic. That script requires exactly one intended failure, no errors, and no skips per mutant. This establishes independent execution, not independently authored mutation logic. The last two controls were executed in the QA probe. No survivor required an owner-file sweep.

## Integrity and limitations

The selected checks executed without skips or swallowed setup failures. Positive checks used the real surface renderer through the production upgrade phase; the unwired control exercised public `main` with deliberately mocked surrounding upgrade phases and injected missing rendering. Python resolution/healing was mocked to keep probes local. Historical input bytes are independent of generated destination names; profile destination/label expectations share the production vocabulary resolver, so these checks establish integration portability and preservation, not independent correctness of that resolver.

The initial missing-manifest probe incorrectly expected `SystemExit(2)` and failed its own oracle. Inspection of the actual renderer NOTICE established the intended nonfatal refusal; the corrected probe verifies absent profile carrier and passed. This is a probe correction, not a repository defect or source repair.

The test-only diff confines new empty manifests to the two positive integration fixtures. No production guard was changed. This worker did not repeat the full second-profile owner, full prompt-names owner, full canonical suite, native Windows qualification, packaging, or downstream Waveforge execution. Source fingerprint remained unchanged. The initial bounded review used targeted tests per mutant; final delivery judgment is recorded below.


## Final delivery judgment

Context ID: `qa-203ha-delivery-20261008-1913`. Reviewer actor: `/root/qa_qualification`; role: `qa-reviewer`. This reviewer did not implement or repair source. Its independently executed scratch probes and mutation execution precede this final evidence reconciliation; code remained frozen throughout. `independent: true`. This was a separately spawned review context, not an implementer self-review; finalization continues that same reviewer context and does not claim a new context reset.

After coordinator delivery-review start, independently read `/tmp/wf-second-repaired.log`, `/tmp/wf-prompt-names-repaired.log`, `/tmp/wf-203ha-canonical-quiet.log`, the canonical receipt, and `waveforge-handoff.md`. The receipt records `result: ok`, 11,885 tests, `ran_at: 2026-10-08T19:13:12.019056+00:00`, and `inputs_hash: dde11ab2ef7918216ee07fa1ab0244033acfd6bc8f590157818322a084e17c2f`.

A read-only call to the canonical `_hash_inputs()` recomputed that exact hash and asserted equality with the receipt. No suite was rerun by this worker. The final source fingerprint remains `f89d39d7dd3bea415852c8d8f7b7a802bc110925`. The earlier guard-rejected attempt is not used as delivery evidence.

The handoff names all R1–R9 and A1–A3 entries, distinguishes prior pushed work from this uncommitted qualification repair, and accurately limits profile diagnostics to the owner file and shipped full-suite execution. Historical coverage claims are supported by linked prior wave records; this bounded QA review does not independently re-prove every earlier request. No deferred AC or new skip is introduced by this repair. All required rows have direct or inspected canonical verification evidence; no blocking QA finding remains.
