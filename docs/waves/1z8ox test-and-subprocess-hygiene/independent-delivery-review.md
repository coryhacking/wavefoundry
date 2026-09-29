# Independent delivery review: 1z8ox

Owner: Engineering
Status: active
Last verified: 2026-09-29

Date: 2026-09-29
Verdict: not ready to close.

## Blocking: executable fallback violates two standing censuses

`run_tests._wave_record_matcher`, run_tests.py:324, introduces `return "docs/waves/", "wave.md"`. Both RecordLayoutCensusTests.test_census_has_no_unrouted_sites and VocabularyCensusTests.test_census_has_no_unrouted_sites fail on that exact line. Each failure was independently reproduced with a five-test module run; the respective planted-literal polarity controls passed. Fix the fallback under the record-layout/vocabulary contracts, then rerun verification. Do not merely suppress these tests.

Both required verification ACs remain unchecked: 1z8ov AC-4 and 1z8ow AC-6. Their change statuses say complete, which does not establish verification. The existing 9,917-test green receipt is stale against the current framework hash.

## Nonblocking census gap

The new runner-binding census omits subprocess.check_output, check_call and call from _RUNNER_ATTRS (test_tree_kill_routing.py:205). An ordinary assignment `runner = subprocess.check_output` followed by a timed runner call escapes both censuses. The independent reviewer planted it in a temporary scripts mirror: all 29 routing tests still passed. No current production assignment using the missing APIs was found. This is a future regression-detection gap, not evidence of a live leaked process. Suggested follow-up: include those attributes and a combined alias/API control. It is distinct from the already documented import-alias, module-alias and default-argument limitations.

## Verification performed

- Root focused canonical run: 143 tests passed, zero skips (repo guard 29, runner cache 97, secret-prefix tests 17).
- Independent reviewer: 71 tests passed (routing and subprocess 57; git sanitation/drift checks 14).
- Full canonical run: 9,961 tests, 140 files, 16 skips, 287.858 seconds; failed dashboard_server, record_layout_census and vocabulary_census. No new green receipt.
- Full run also reported that the separate 1zbrr change document changed during execution. The guard named it; this review did not write that file during the run. Actor/source of the change was not established.
- Dashboard failures included process inspection returning None. A paired read-only call to dashboard_cmdline_pids confirmed inspection unavailable inside the sandbox and available outside. An elevated focused rerun was refused because another test invocation already held the lock. This diagnoses an environmental contribution, not a passing dashboard test or proof that every dashboard failure is environmental.
- Initial wf_review_wave full docs validation passed; full-suite test_docs_lint passed 1,115 tests.

## Discriminating controls

| Control | Result |
| --- | --- |
| Disable repository-change detection | All three selected real-worker regressions fail |
| Signal a reaped child's process group unconditionally | Reaped-ID safety test fails |
| Poll before signalling an exited child's group | Real descendant survives; regression fails; fixture cleans it up |
| Plant direct timed check_output | Census detects it |
| Plant alias of subprocess.run | Binding census detects it |
| Plant alias of subprocess.check_output | Survives both censuses and all 29 routing tests |

Source changes were examined against admitted requirements and prior caller behavior, not only delivery prose. Review supports preserved output/error handling, runtime helper resolution with the old-runner fallback, sanitized git environment, and the distinction between unreaped and reaped child IDs. Native Windows was not executed; Windows branch coverage is stub-based.

## Scope and evidence integrity

No production edits, implementation, closure or commit were performed. Mutants and probes used temporary trees/modules. Relevant source fingerprints stayed identical during the independent review. The independent review manifest is /tmp/hygiene-review-fingerprint.json (SHA-256 74c7b7b9607396942c24b0ed27de07bf457e2fa50810ed5e672da8caa5f0e9ec). Root guard-source hashes were also unchanged before and after focused verification.

This report is outside the checkout to avoid invalidating the other session's running suite. A typed DEL-F4 finding was successfully previewed but not appended; review-ledger approvals therefore do not yet reflect this newly reproduced failure. Persist this report and record the finding when that run is finished. Do not close based only on the earlier approvals.
