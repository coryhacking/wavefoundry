# Focused readiness refresh — specialist lanes

Owner: Engineering
Status: active
Last verified: 2026-10-08

Wave: `204mk pack-profile-qualification`

Change reviewed: `204hj-bug reload-probe-profile-portability`. Receipt: `review-policy-9ba428eda25af71e4792`. Context: `204mk-readiness-refresh-lanes-20261008`. Roles: code-reviewer, qa-reviewer, and docs-contract-reviewer rotating alternative seat in one fresh context. These dimensions are not independent corroborating reviewers. Runtime model identity is not exposed.

Verdict: approve code and QA **readiness** for this completed packet's document-only refresh; docs-contract seat supports PASS. No findings in my lane: current fixture source retains both original behavioral oracles, current bounded reload execution rejects stale lifecycle state, and the completed packet explicitly bounds the packaging exception to local testing. No typed approval or lifecycle state was written by this reviewer.

## Independent read and primer response

Pre-primer read: the completed change distinguishes a local pack exception from strict skip parity and release qualification, while its two fixture contracts remain testable without changing production behavior. This assessment was stated to the chair before reading the refresh primer; historical reports were context, not accepted proof of current execution.

Primer effect: confirmed — its warning about promotion into release qualification matches the current Decision Log's explicit limit, and sharpened the need to retain the inferred status of the second-profile skip attribution.

Strongest challenge: completed checkboxes do not prove strict release qualification. Change Progress Log and Decision Log explicitly preserve the 19-extra-declared-skip exception and identify second-profile overlap as inferred. I support preserving those qualifications verbatim in the refreshed result and handoff.

Question 1: yes. Fixture AC completion, coordinator-recorded passing full suites, and strict release qualification are distinct claims. The first is supported by current assertions and historical executed delivery controls; the second is attributed to the recorded serial logs; the third remains unproved. This readiness review supplies no new release qualification.

Question 2: yes for the document-only refresh. Independently rechecked source hashes match both delivery reports, and current source still takes the stock digest before its first render, uses `base_declaration`, and asserts zero writes, unchanged digest, and the manifest condition. The primer's newly executed positive/stale-stock pair directly supports that contract but is attributed evidence, not my own execution. My separate current reload baseline and lifecycle-only mutant below refresh the other oracle. Neither pair substitutes for the historical full profile matrix.

Strongest alternative: defer all packaging until scratch-profile history/index prerequisites and the blanket named-profile guard are qualified. That would be better for an artifact intended to support a strict release claim, because it closes the documented coverage gap. It is not stronger for the authorized local test pack: the operator explicitly accepted the disclosed exception, and further fixture edits would not restore missing scratch prerequisites. Keep qualification follow-up separate and carry the limits with the artifact. No additional implementation change is recommended by this focused refresh.

## Current source and executable evidence

MCP `code_read` and `code_keyword` were discovered in `ALL_TOOLS`, confirmed callable and called successfully before source assessment. Targeted current reads inspected `_RELOAD_PROBE`, `LifecycleIdReloadTests.test_reload_refreshes_lifecycle_id`, and `DefaultRenderIdentityTests.test_render_of_this_repository_writes_nothing`. Keyword graph expansion was truncated and is not a census. MCP reports changed setup inputs; no setup or index recovery was attempted and no semantic freshness claim is needed for direct current-file reads.

Independent reference: the independently read change Requirements 1–5 and AC-1–4. The load-bearing reload property is exact preservation of initial choices plus a previously absent kind after real reload, with validators binding the fresh module. Current source appends to original extras, selects an absent candidate, requires exactly one declaration rewrite, executes `perform_mcp_reload`, and compares the exact kind set and module binding. Failure of either final boolean falsifies the claim.

Selected cells (one parameterized mechanism within the standard budget): shipped reload success; successful reload with only lifecycle eviction omitted. Commands executed in fresh Python processes:

```text
PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests python3 -B -m unittest test_distribution_seams.LifecycleIdReloadTests
python3 -B /tmp/wf204mk_qa_controls.py reload-mutant
```

Expected and observed: baseline ran one original owner test in 1.983 seconds, OK, zero skips. The scratch mutant ran one original owner test in 1.847 seconds and failed its final equality, with zero errors/skips: reload status was `ok`, `new_kind` was `probe0`, absent beforehand, `kind_choices_fresh` was false, and `validators_bind_fresh` was true. The harness exit zero means it detected the expected test failure. This is failure at the intended freshness assertion, not setup refusal.

The existing temporary control was inspected before execution. Reproduction after it expires: copy scripts excluding bytecode; delete precisely the single `            "lifecycle_id",` member from copied `wf_server/server_impl.py`; patch only the original test module's `SCRIPTS` to this copy; run its original owning test. The test makes its own nested copy and calls the real thin runner reload. An observer print before the existing reload-status assertion reports preconditions without changing final output assertions. Require one test, one expected assertion failure, zero errors/skips, and inspect the failure as above. No repository source mutation occurred.

Source Git blob hashes before and after execution match historical delivery evidence:

| Source | Blob |
| --- | --- |
| `test_distribution_seams.py` | `c81059293654443b6a9c98759e4dc4735874fe18` |
| `test_vocabulary_prompt_names.py` | `2ee364b4cb5e4e47bfb2f768eac3aee33314454a` |
| `CHANGELOG.md` | `604748186bdb903ecba78c2cf6105a73cb17c303` |

## Judgment facts and limits

For code and QA readiness approval: `fresh_context: true`, `independent: true`; reviewer did not implement the repair and bases its current judgment on the independently read requirements, current source and executed control. The same context ID applies to both roles, with the actor set to the appropriate specialist lane when recorded. Existing evidence was read as the requested refresh packet; this does not claim an independently designed replacement oracle.

For the selected executed checks, `test_ran_without_unintended_skip: true`, `public_path_reached: true`, `boundary_values_realistic: true`, `assertions_non_vacuous: true`, `known_bad_detected: true`; `known_bad_detection_method: focused-mutation`. Public boundary: original owner subprocess through real `perform_mcp_reload` on copied scripts. Proposition: the unchanged reload owner still succeeds normally and rejects a successful reload retaining stale lifecycle choices. Counterexample: baseline fails/skips or the lifecycle-only mutant passes. Execution status: executed. Probe class: local_safe; authorization: authorized delegated review; safe_boundary: false; unexecuted_remainder_prohibited: false; universal_claim: false.

Limits: no full suite, profile matrix, archive validation, native platform execution or release qualification repeated. Historical owner/profile evidence is attributed, not re-executed by this lane. The control reuses an inspected prior harness and the original test/environment; independence comes from the requirements and actual current observations, not separate implementation of the mechanism. Minimal temporary target readiness notices did not bypass the real reload or its final assertion. No source edits, change edits, ledger writes, commit or closure action occurred. Candidate finding set is empty.
