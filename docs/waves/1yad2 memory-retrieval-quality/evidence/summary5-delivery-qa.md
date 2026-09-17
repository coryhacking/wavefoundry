# Summary5 independent delivery QA — initial frozen round

Owner: Engineering
Status: active
Last verified: 2026-09-17

Verdict: **needs repair; no delivery approval**. Independently reviewed the admitted acceptance criteria and current source. The stale-source recovery contract fails for ordinary same-path memory edits. Historical prototype metrics do not establish actual production delivery qualification.

## Frozen scope and budget

All 12 source/test/doc git-blob hashes from `/private/tmp/wf-summary5-freeze.json` matched before and after this round. Exact fingerprint, executable scratch probes, raw mutation output, and typed finding facts are retained in [the evidence bundle](summary5-delivery-qa.json.gz). Budget: 15 minutes, three grouped risk probes; targeted tests per mutant, whole-file runs only for survivors. No survivor required a whole-file run. No source, test, label, parameter, or lifecycle state was edited.

## Finding: stale source does not trigger recovery

AC-4 and search-architecture.md promise unavailable/lexical-policy recovery for stale semantic state. The public `memory_search_response` loads current memory text, but `_ensure_loaded` checks completed epoch/generation and compatibility; `dense_path_scores` checks path coverage only. Editing a memory at its existing path without rebuilding leaves the old vector eligible. The real public response reports `hybrid_rrf`, `model_relevance`, and `fallback_reason: null` after the source SHA-256 changes.

The reproduction uses a real on-disk rendered memory, actual source edit, real loader, and real SQL dense helper. Completed epoch/open-layer producer uses a stable token; distance/model kernels are deterministic. This is a faithful reachable boundary control, not native model quality evidence. Expected: unavailable screening and explicit lexical recovery. Observed: healthy screening using stale candidates. Disposition: **do_now**, bounded source-freshness repair plus producer-faithful regression coverage. Existing stale coverage only raises an injected loader exception and misses this state.

## Executed checks

- Nine qualification tests passed, zero skips: filters before retrieval, archive identity/history recovery, exact threshold, cap/order, malformed/nonfinite scores, missing/incomplete/code-only/model failure, CPU isolation and title fallback.
- Five ordering/brief tests passed, zero skips.
- One SQL grouping/coverage/read-only test passed, zero skips.
- Independent same-index sequence passed: healthy screened result → nonfinite-model lexical recovery → healthy screened empty → healthy screened result. Queryless listing, brief and path advisory did not call the candidate path.
- Source-staleness probe exposed the blocking gap above.

The first test invocation selected Apple's old Python after PATH adjustment and failed importing `tomllib`; that run is not evidence. Repeated with explicit `/opt/homebrew/bin/python3` and CommandLineTools git. An initial scratch brief call supplied unsupported `index`; corrected to its real signature before successful execution. Neither harness error is counted as a passing check.

## Mutation table

| Mechanism | Safe in-memory mutation | Detection |
| --- | --- | --- |
| Raw-logit boundary | Loosen threshold from -4 to -5 | Named five-summary test fails exact IDs; no errors/skips |
| Nonfinite model rejection | Delete finite guard | Named failure test fails unavailable metadata for NaN and rejects unchecked infinity hit |
| Candidate admission | Admit every checked candidate regardless of score | Named five-summary test fails exact IDs |
| RRF output order | Reverse selected candidates | Named five-summary test fails exact order |
| Source freshness | Reachable changed source with unchanged completed epoch | NOT CAUGHT by existing stale test; independent public-path probe exposes contract failure |

## AC evidence and limits

AC-1/2 retain historical frozen comparisons; this round verified bounded current mechanics but did not re-author labels. AC-3 has passing targeted filter/history controls. AC-4 is blocked by source freshness. AC-5/6 actual public-path benchmark and parity/latency audit remain **unverified**, intentionally held while this correctness defect is resolved; no historical prototype result is substituted. AC-7 metadata/support-unverified semantics match inspected code except the stale-state promise. AC-8 targeted tests pass, but canonical full suite and final document validation remain coordinator work after repair. Native Windows/Linux/Intel, actual CPU model timing, full evaluator privacy regression and the entire neighboring code/docs retrieval suite were not executed in this finite round.

Evidence integrity: executed probes reached the public response, had zero unintended skips, realistic boundary values, non-vacuous assertions and known-bad detection. The bundle contains all five integrity booleans and method plus full finding facts. Reviewer did not implement or repair this code; fresh-context and independent declarations apply to this initial round. Subsequent repair requires fresh independent reverification. No approval is supplied.
