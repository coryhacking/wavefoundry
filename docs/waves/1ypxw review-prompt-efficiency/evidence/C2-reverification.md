# C-2 independent repair reverification

Owner: Engineering
Status: active
Last verified: 2026-09-22

Context: `/root/ypxw_c2_reverify`; fresh independent focused delivery QA context. This reviewer did not implement the change or either repair. Scope is C-2 only; this is not a whole-wave approval.

Verdict: repair verified. Original finding judgment remains unchanged: real, admitted, introduced or worsened by this wave, required-AC relevance, supported reachability, no attacker reachability, integrity authority, low authority delta, material impact, preventive containment. The original failures were valid; the narrow repairs now discharge them.

Compared both repaired test files with `/tmp/1ypxw-before` after MCP source reads. The guidance test changes only its numbering expectation from 12345 to 123456 and adds explicit assertions for conditional measured-delta applicability and the sixth controlled-comparison heading. The census removes only the obsolete renderer ALLOWLIST entry and adds a retirement comment to the unchanged historical SITES row. Neither census predicate, exclusion set, stale-entry guard nor polarity test was weakened. Independently extracted all five original numbered seed-239 conditions and compared their text byte for byte: all five match the before-wave snapshot.

Command, from repository root:

```sh
PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests /Users/coryhacking/.wavefoundry/venv/bin/python -B -m unittest test_fixture_fidelity_guidance test_record_layout_census -v
```

Actual: eight tests passed in 0.279 seconds, zero errors, failures or skips. This includes the real public renderer in disposable roots and the real census against both the repository and an injected literal-join fixture. Expected: the six-condition guidance passes while preserving the first five; only live allowlist sites remain; injected unrouted joins remain detectable. Actual matches expected.

Four independent process-local negative controls were killed, each by exactly one assertion failure with zero errors/skips:

1. Patched `Path.read_text` only for the QA seed to remove its `6. ` line; the repaired guidance test failed its numbering assertion.
2. Patched that seed read to replace `the sixth when claiming a measured delta` with `all six conditions`; the repaired test failed its conditional-applicability assertion.
3. Patched the census function to return no hits; `test_census_polarity_reports_a_literal_join` failed because the expected `tiny.py` lines 3 and 5 were absent.
4. Patched `_allowed` to return true for every hit; the same polarity test failed its assertion that injected hits are not allowlisted.

These controls used `unittest.mock.patch` in a separate Python process and changed no repository source. The real scanner's fixture includes excluded test/resolver files and actual literal join/prefix shapes. Hashes from `evidence/delivery-tree-final.json` matched all 48 paths before and after verification, with zero mismatches. The manifest itself was read unchanged. No ledger writes or lifecycle mutations were performed.

## Integrity facts

```json
{
  "finding_id": "C-2",
  "repair_completed": true,
  "fresh_context": true,
  "independent": true,
  "context_id": "/root/ypxw_c2_reverify",
  "integrity_checks": {
    "test_ran_without_unintended_skip": true,
    "public_path_reached": true,
    "boundary_values_realistic": true,
    "assertions_non_vacuous": true,
    "known_bad_detected": true,
    "known_bad_detection_method": "focused-mutation"
  }
}
```

Limits: this focused verification does not claim a full-suite result or approval of unrelated wave changes. The coordinator is running the canonical full suite separately. Guidance availability tests do not establish future agent adherence.
