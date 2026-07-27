# Fragile: probe_1to7k_reverify.py

Owner: Engineering
Status: rejected
Last verified: 2026-07-27

Memory ID: `1tntn-mem fragile-probe-1to7k-reverify-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-27
Updated: 2026-07-27
Source exploration cost: 736040
Source event: `repeated-repairs:1to7k:probe_1to7k_reverify.py`
Validation: reject
Validated by: agent
Action delta: No durable action from this candidate as drafted: its target is a reviewer scratchpad probe script absent from the tree, so nothing an editor could consult before touching real code. The genuine fragile signal (review_evidence.py independence-check precedence and server_impl.py focus-reporting seams, three operator-caught edge interleavings in one wave) is carried by the 1to7k ledger chains and the change docs' Progress Logs; a correctly-targeted fragile_file record can be authored from those sources.
Validation rationale: Fifth consecutive occurrence of the verification-command misattribution pattern: the drafter extracted probe_1to7k_reverify.py from command_or_fixture strings. That file is the code-reviewer's session-scratchpad probe, not a repository file (verified absent from the tree), so the candidate cannot be promoted and a rewrite is blocked by the target-currency check. The underlying signal is real but belongs to .wavefoundry/framework/scripts/review_evidence.py and server_impl.py, where all three cycle-2 repairs landed; evidence followed to the three finding chains in the 1to7k ledger.
Evidence verified: true
Current target verified: false
Canonical overlap: none
## Summary

probe_1to7k_reverify.py required 3 separate repairs during wave 1to7k; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `same-actor-same-context-nonfresh-reverification-accepted`
- `open-wave-fallback-stage-mismatch-suppressed`
- `sealed-close-focus-clear-failure-is-silent`
- `1to7k`

## Targets

- `probe_1to7k_reverify.py`
