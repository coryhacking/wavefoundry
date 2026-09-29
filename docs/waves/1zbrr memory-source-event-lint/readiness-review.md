# Memory Source Event Lint — Plan Review

Owner: Engineering
Status: active
Last verified: 2026-09-28

## Verdict and scope

The revised approach is sound. No remaining code/architecture design blocker was found. This is a plan review, not delivery verification or a completed typed readiness gate. The operator requested review without implementation while another wave is in progress. The wave remains planned.

An isolated red-team primer and a separate code/architecture reviewer inspected the plan and current source. The coordinator assessed verification feasibility and synthesized their evidence. Dedicated independent QA/security approvals and formal council approval have not been recorded; additional reviewer allocation failed at the host's agent-thread limit. Do not represent this report as three independent approvals.

## Corrections made during review

1. The actual producer is `memory_supply.draft_candidates`, not `propose_from_wave`. Existing proposal tests are `MemoryProposeTests` in `test_memory_records.py`; `test_memory_supply.py` does not exist. The plan now points to the current owners.
2. AC-1 now promises passage for benign producer output, with AC-2 explicitly retaining protection inside finding IDs and targets. Producer origin does not establish safe content.
3. Requirement 2 now requires match-level classification at validated event-level separator offsets, with every other match still checked. Nested `symbol:` and `community:` target payloads are not automatically exempt.
4. Requirement 5 explicitly includes a same-line structural match plus real assignment, both supported lifecycle-ID widths, nested payload controls, and another forbidden-content pattern.

These are plan clarifications and corrections, not implementation edits.

## Evidence and mechanism

Current source anchors:

- `memory_supply.draft_candidates`: emits decision-log, repeated-repairs and finding source events. Decision events use the admitted change stem and a 16-hex decision hash.
- `memory_supply._code_targets`: accepts `symbol:` and `community:` references before the space check; normal file targets lose their line suffix. It does not certify that target text is free of forbidden content.
- `review_evidence.build_compact_review_event`: finding identifiers are checked for a nonempty string, not a narrow harmless alphabet.
- `wave_lint_lib.constants.JOURNAL_DISALLOWED_PATTERNS`: the assignment pattern matches the structural `secret:` in the reported decision ID. Memory extends these patterns; the shared journal policy must remain unchanged.
- `wave_lint_lib.wave_validators.check_memory_docs`: scans each non-prohibition line for forbidden patterns. This is the intended narrow correction site.
- `MemoryProposeTests` and `MemoryRecordLintTests`: existing producer and lint fixtures provide suitable regression-test owners.

The red-team ran a read-only probe of the live target filter and forbidden patterns. The independent code reviewer additionally ran `check_memory_docs` against temporary records. Observed current behavior:

| Case | Observation | Required result after implementation |
| --- | --- | --- |
| Reported decision ID ending in secret before its hash | Forbidden-content failure on the structural separator | Pass without changing source bytes |
| Benign decision event | Pass | Keep passing |
| Repeated-repairs target containing a nested secret assignment | Target accepted by producer filtering; lint fails | Keep failing |
| Community target containing a password assignment | Target accepted; secret pattern matches | Keep failing |
| Symbol target containing raw-transcript wording | Target accepted; separate forbidden pattern matches | Keep failing |
| Finding event with wave token `token` followed by a secret assignment | Two assignment-pattern matches | Ignore only the validated event separator; retain the payload failure |
| Canonical metadata followed by an assignment outside its closing backtick | Assignment pattern matches | Keep failing; full-line recognition must not accept a prefix |

Probe values were synthetic fixtures. No credentials, downstream repository writes, production-source edits, setup, rebuild or reload were involved. These observations reproduce the existing defect and establish useful negative controls; they do not prove an unimplemented fix.

## Primer and alternatives

The standard-depth primer applied adversarial, constructive and simplicity perspectives. Its strongest challenge was that generated metadata can contain unsafe payloads. Both reviewers supported retaining the narrow classifier rather than changing record identities or skipping whole metadata lines.

The two review questions were how to separate event delimiters from nested payload delimiters, and which independent fixtures discriminate correct classification from removal or overbroadening. The revised requirements answer the first with offset-specific match filtering and the second with real producer fixtures plus separately specified lint outcomes and negative controls. Exact implementation grammar remains grounded in existing producer contracts, not a new general-purpose event parser.

## Falsification check

Working verdict: the plan removes the documented false positive without requiring a broader exemption. The strongest contrary argument is that a canonical event can itself carry forbidden text. The revised plan explicitly requires that text to remain detectable, including a second match on the same line; that resolves the design objection. Delivery must still demonstrate the behavior through discriminating tests.

## Limitations and next step

Indexed retrieval reported unavailable/stale state, so reviewers verified current source through targeted disk reads. No index recovery was attempted during the other wave's work. Prepare dry-run passed lint and gardening but correctly withheld readiness for missing typed signoffs. No full suite was run for this docs-only review.

Before future implementation, finish the independent QA/security and council review, publish the final policy packet and obtain current typed readiness approvals. Do not open this wave or modify framework code under the present review-only instruction.
