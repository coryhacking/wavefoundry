# fragile-memory-minting-seam-hidden-indirection

Owner: Engineering
Status: archived
Last verified: 2026-07-23

Memory ID: `1tf7m-mem fragile-memory-minting-seam-hidden-indirection`
Superseded by: `1u8q1-mem server-impl-file-playbook`
Kind: `fragile_file`
Confidence: 0.85
Created: 2026-07-23
Updated: 2026-08-02
Source exploration cost: 85585
Source event: `repeated-repairs:1tg55:run_tests.py`
Validation: promote
Validated by: agent
Action delta: When adding a parameter or supersession-linked behavior to _memory_add_response_locked, forward it at the lock-acquisition self-re-entry and handle the memory_validate rewrite path explicitly (it passes no supersedes; supersession is applied to the old record afterwards).
Validation rationale: The drafted candidate misattributed the fragile target to run_tests.py (the verification command) for the fourth consecutive wave. Both 1tg55 repairs landed at the memory minting seam: the self-re-entry silently dropped the new _source_exploration_cost parameter, and the rewrite path never passes supersedes so lineage-keyed behavior cannot see it. Both were live-caught by the inheritance test matrix before landing.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

Archived: 2026-08-02
Archive reason: Superseded by a verified consolidated file playbook after retention review.
Archive path: `docs/agents/memory/archive/1tf7m-mem fragile-memory-minting-seam-hidden-indirection.md`
## Summary

_memory_add_response_locked in server_impl.py carries two indirections that silently bypass new behavior: the lock-acquisition SELF-RE-ENTRY re-invokes the function and must forward every new keyword (wave 1tg55's _source_exploration_cost was dropped there, live-caught by the explicit-cost regression), and the memory_validate REWRITE path mints through this seam WITHOUT passing supersedes (supersession is applied to the old record afterwards), so supersession-keyed logic never fires for rewrites (live-caught by the rewrite-inheritance regression). When changing this seam, update the re-entry forwarding in the same edit and give the rewrite path its own explicit handling and test.

## Evidence

- `zero-cost-key-omission-breaks-draft-consumers`
- `rewrite-inheritance-not-visible-at-mint-seam`
- `1tg55`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
