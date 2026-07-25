# Repaired defect concurrency-regression-vacuous-and-wrong-path

Owner: Engineering
Status: superseded
Last verified: 2026-07-25

Memory ID: `1tiyt-mem repaired-defect-concurrency-regression-vacuous-and-wrong-pat`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-25
Updated: 2026-07-25
Source exploration cost: 270323
Source event: `finding:1tis8:concurrency-regression-vacuous-and-wrong-path`
Validation: rewrite
Validated by: agent
Action delta: Before claiming a concurrency or crash-safety test protects a repair, run it under two mutations — inject a worker exception and reintroduce the defect — and confirm it fails both times; propagate worker failures through futures, drive the real exposed path, and assert on a value that actually differs between the healthy and broken states.
Validation rationale: Verified against the terminal cycle-2 chain and the executed falsification harness: the original guard passed under the reviewer's worker-crash injection, exercised hermetic run() instead of the MCP-exposed run_curated, and asserted a lookup that file_commit_times short-circuits to {} regardless of corruption. The rebuilt guard fails under both mutations (A PASS / B FAIL propagating RuntimeError / C FAIL on the unrelated-path assertion). Rewritten from the drafted instance summary because the durable lesson is the falsify-your-guard discipline, which generalizes past this test; kept as successful_pattern since it prescribes a repeatable method rather than recording a one-off failure.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1th3w-mem prove-a-concurrency-regression-can-fail-before-trusting-it`
## Summary

Real defect fixed in wave 1tis8: All three reported weaknesses are closed and each closure is demonstrated by a mutation that makes the test fail. The guard now fails for exactly the reasons it exists to catch, so it protects the underlying repair rather than merely accom…

## Evidence

- `concurrency-regression-vacuous-and-wrong-path`
- `ev-concurrency-regression-vacuous-and-wrong-path-3`
- `1tis8`

## Targets

- `.wavefoundry/framework/scripts/tests/test_memory_eval.py`
