# Decision: Retarget wave `1uugg`'s predicate-spelling pin to the extra…

Owner: Engineering
Status: archived
Last verified: 2026-11-10

Memory ID: `1ydvk-mem decision-retarget-wave-1uugg-s-predicate-spelling-pin-to-the`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-18
Updated: 2026-11-25
Source exploration cost: 38262
Source event: `decision-log:1yd98-enh close-sensor-approval-precondition:f6ef29ab12c05d8d`
Validation: promote
Validated by: agent
Action delta: When an extraction deletes the exact string a landed substring pin asserts, retarget that pin to the new single implementation rather than leaving a copy behind to keep the search green. Separate what the pin protects from where it happens to read: wave 1uugg's pin carried two obligations, that the advisory predicate reads in the non-advisory direction and that two workaround symbols stay deleted. The direction half moved with the predicate into lifecycle_gates.py; the two absence checks stayed on server_impl.py, which is what 1uugg was actually protecting. Before repointing any call site, grep the test tree for the literal expression being moved, because a substring pin is invisible to the type checker and to every structural scan.
Validation rationale: Verified against the landed tree during wave 1yd97 delivery. The pinned spelling occurred exactly once, in prepare's closure, because the close envelope named its loop variable differently; repointing that closure to the extracted helper deleted the only occurrence, so the pin would have reddened with no type or structural signal. A code-review lane found this at readiness by reading the test tree rather than the production tree. Both halves of the retarget are exercised by the landed test: the direction assertion now reads lifecycle_gates.py and the two absence assertions still read server_impl.py, and a structural criterion independently asserts exactly one implementation of the predicate exists.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Checked at: 2026-11-25T16:09:21Z
Check note: Item 7 review: encoded elsewhere. The retargeting has shipped and is pinned. tests/test_server_tools_lifecycle.py:11848 test_prepare_advisory_predicate_and_workaround_removal reads the predicate direction from lifecycle_gates and keeps the two workaround-symbol absence checks on server_impl.py; its docstring records this decision. tests/test_lifecycle_gates_structure.py:715 test_blocking_predicat.
Check flags: target_unresolved
Archived: 2026-11-25
Archive reason: Retired in the 244cm item 7 review, encoded in The retargeting has shipped and is pinned. tests/test_server_tools_lifecycle.py:11848 test_prepare_advisory_predicate_and_workaround_removal reads the predicate direction from lifecycle_gates and keeps the two workaround-symbol absence checks on server.
Archive path: `docs/agents/memory/archive/1ydvk-mem decision-retarget-wave-1uugg-s-predicate-spelling-pin-to-the.md`

## Summary

Decision (wave 1yd97): Retarget wave `1uugg`'s predicate-spelling pin to the extracted helper rather than leaving a third inline copy in `server_impl.py` to keep it green. Rationale: The pin's purpose is that the predicate reads in the non-advisory direction and the two workaround symbols stay deleted; both survive retargeting, while leaving a copy to satisfy a substring search would defeat the extraction the pin's own wave motivated.

## Evidence

- `1yd98-enh close-sensor-approval-precondition`
- `1yd97`

## Targets

- `server_impl.py`
