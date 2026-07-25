# Prove a concurrency regression can fail before trusting it

Owner: Engineering
Status: active
Last verified: 2026-07-25

Memory ID: `1th3w-mem prove-a-concurrency-regression-can-fail-before-trusting-it`
Kind: `successful_pattern`
Confidence: 0.9
Created: 2026-07-25
Updated: 2026-07-25
Source exploration cost: 270323
Source event: `finding:1tis8:concurrency-regression-vacuous-and-wrong-path`
Validation: promote
Validated by: agent
Action delta: Before claiming a concurrency or crash-safety test protects a repair, run it under two mutations — inject a worker exception and reintroduce the defect — and confirm it fails both times; propagate worker failures through futures, drive the real exposed path, and assert on a value that actually differs between the healthy and broken states.
Validation rationale: Verified against the terminal cycle-2 chain and the executed falsification harness: the original guard passed under the reviewer's worker-crash injection, exercised hermetic run() instead of the MCP-exposed run_curated, and asserted a lookup that file_commit_times short-circuits to {} regardless of corruption. The rebuilt guard fails under both mutations (A PASS / B FAIL propagating RuntimeError / C FAIL on the unrelated-path assertion). Rewritten from the drafted instance summary because the durable lesson is the falsify-your-guard discipline, which generalizes past this test; kept as successful_pattern since it prescribes a repeatable method rather than recording a one-off failure.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

A concurrency test is worthless until you have watched it fail. Three ways they silently cannot: threading.Thread swallows worker exceptions so join() returns normally after a crash (use ThreadPoolExecutor and call future.result(), which re-raises); the test drives a convenient entry point rather than the one where the defect occurs (drive the real exposed path, stubbing only what blocks it, and assert it reached real work rather than an early return); and an assertion whose value is constant regardless of the defect (file_commit_times short-circuits an empty path list to {} before touching the store, so asserting {} there was true either way — probe a path seeded OUTSIDE the frozen subset so healthy and corrupted answers differ). Force overlap with threading.Barrier rather than hoping for it, and demonstrate non-vacuity by mutation: the test must FAIL when a worker raises and when the defect is reintroduced.

## Evidence

- `concurrency-regression-vacuous-and-wrong-path`
- `test_curated_pass_never_rebinds_the_shared_commit_times_global`
- `1tgws-enh memory-eval-shippable-mcp-tool`
- `1tis8`

## Targets

- `.wavefoundry/framework/scripts/tests/test_memory_eval.py`
