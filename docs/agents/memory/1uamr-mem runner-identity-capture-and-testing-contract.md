# Runner identity capture and testing contract

Owner: Engineering
Status: active
Last verified: 2026-08-02

Memory ID: `1uamr-mem runner-identity-capture-and-testing-contract`
Kind: `decision`
Confidence: 0.6
Created: 2026-08-02
Updated: 2026-08-02
Supersedes: `1u4hd-mem test-launch-captured-runner-identity-by-injection-not-by-a-f`

## Summary

Keep runner identity hashing in exactly one implementation site, server_impl.compute_runner_identity. server.py captures the runner version and runner-file set once at launch through a compatibility-safe fallback, while wf_server_info recomputes the same paths at query time. Test launch-captured state by injecting compute_runner_identity over temporary runner-file copies and mutating them; reserve fresh-process probes for tool-registration changes.

## Evidence

- `consolidated from 1u4hd-mem test-launch-captured-runner-identity-by-injection-not-by-a-f`
- `consolidated from 1u55k-mem runner-identity-hashing-has-exactly-one-implementation-site-`

## Targets

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
