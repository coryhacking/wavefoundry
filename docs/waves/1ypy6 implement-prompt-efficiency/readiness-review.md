# Implement Prompt Efficiency Readiness Review

Owner: Engineering
Status: active
Last verified: 2026-09-21

Phase: readiness. Context: `implement-prompt-efficiency-readiness-20260921`. This reviews the three plans, not delivered behavior; nothing is implemented.

## Council

Seats ran in separate fresh contexts against the admitted change docs and wave record: `red-team` (fixed) and `docs-contract-reviewer` (rotating, bound to the receipt). The code-reviewer, qa-reviewer and architecture-reviewer readiness lanes ran in the same round, fresh and independent. Every seat verified plan claims against the tree (server_impl.py, review_evidence.py, the lint library, the seeds, the renderer, the test modules and eight recent ledgers) rather than the plans' prose.

Strongest challenge (all five, independently): the first draft's independence predicate, "a fresh-declared row whose context appeared on any earlier row", would have refused the second lane approval of every council round, every currency refresh after a receipt rotation, and a lane reverifying its own finding, and would have failed this wave's own close. The shape that motivated it (one reviewer context filing findings, then reverifying and approving) is the same shape two closed waves used under the readiness rule and is not decidable without a trust assumption.

Strongest alternative (architecture): scope the audit to any earlier `repair_start` context, which is decidable and keeps every shipped shape legal, and make the finding-then-approve shape visible in the ledger list view instead of refusing it. Adopted. Red-team's focused pass then checked the narrowed guard against eight ledgers: nine `repair_start` contexts, zero rows the new check would have flagged, so it is a contradiction guard whose only known-bad is its fixture; the plan says so.

## Findings and repair

Blocking in the first round, all repaired in one rewrite pass:

- Tools: the predicate above; the dependency parsers had no producer (the execution-graph table names workstreams; `## Dependencies` is free prose), while the lint-validated `Depends On:` line inside a change's block of the wave record already exists and the tool never read it; the advisory for out-of-wave ids must attach to the success envelope because the gate branch errors on any diagnostic; the new code must join `INDEPENDENCE_DIAGNOSTIC_CODES`; both close call sites named; the correct architecture doc is `data-and-control-flow.md`, not `cross-cutting-concerns.md`.
- Seeds: the retired-journal blocks are project prose in six role docs written by the seed 210 migration, not renderer output, and `memory-archive.md` is a machine-regenerated register that would destroy them, so the local move went to the documentation change and only the seed 210 and 160 wording stayed; `code_patterns` has no producer, so its pin is static; "immediately preceding" also lives in seed 050 and five local surfaces; seed 100 carries no checkbox copy; seed 209 gains the writing-hand, `recommended_fix` and code-enumeration sentences and seed 180 the docs-gate sentence, so seed 160's carrier clause reaches existing targets.
- Surfaces: three passages the first draft called restatements are pinned carrier content (host-neutral paragraph, ten readback clauses, memory briefing) and stay; the two pointer literals are pinned; there is no context-efficiency carrier on the file; size is measured, not pinned.

## Focused verification

Five fresh verifiers, one per lane, checked the rewritten packet against the tree. Every original block resolved. Their remaining items were bounded plan-text corrections, all folded before this record was written: the `fresh_context=false` twin applies to the reverification row only because the builder already rejects such approvals upstream; the wave-record `Depends On:` line resolves by exact id, matching lint, with prefix tolerance only on the legacy change-doc form; `wf_add_change` writes no dependency line, so fixtures author it after admission; the lifecycle golden captures the delivery-review and close envelopes, so nothing unconditional joins them; the residue-census pin must be a test-local token tuple with a count-bounded allowance for the history document, because the production `RETIRED_LIFECYCLE_TOKENS` tuple ships to every target; the history document needs `Role:` and `Category:` metadata; seed 160 notes go outside the byte-pinned briefing-loop block; seed 110, not 170, owns the wave-record dependency grammar; seed 209's numbered lane-clearing steps keep their semantics when the verbs change; the local surface keeps builder-lane and delegation pointers because seed 100 requires them; the delivery advisory is a new surface, not a match of an existing one.

Known-bad detection in this round: every blocking item was detected by a seat or lane reading the tree, not the plan; the readiness rule of one full review, one bounded repair and one focused verification was followed, and the focused round's findings were plan-text corrections rather than build-changing defects, so approvals were recorded without a further round. Verdict: approved; no readiness blockers remain.

Requested lane settings: host default model and effort for all seats and lanes. Observed runtime identity: unknown.

Limits: no implementation; no test executed this round; ledger censuses are scripted reads of the eight most recent `events.jsonl` files; the new independence guard has no historical positive, which the bug change records.

## Operator contract review (2026-09-22)

After readiness, the operator's own session ran independent architecture and security reviews of the readied packet and returned four contract revisions and two wording fixes, all folded before re-readying: exact ids everywhere the wave-record dependency line is mentioned, with prefix tolerance confined to the legacy change-doc form; the measurement sentence narrowed so the intended change is distinguished from uncontrolled differences, each run must be stable within itself, and other differences qualify rather than forbid a conclusion; propagation made explicit as a per-sentence table of destination and mechanism, since `wf render-surfaces` does not copy seed prose into existing prompts, with authored reconciliation of Wavefoundry's surfaces assigned to the cleanup change; the retained-context audit judges only currently authoritative rows at close, with supersession, ordering and receipt-rotation regressions; census hits classified as update or intentionally retained; legacy prose-verdict and review-disabled readiness behavior preserved; and the efficiency claim stated as entry cost and duplication, backed by a with-and-without-MCP walkthrough. No design element changed; the three changes and their order stand. Approvals re-recorded on the rotated receipt as a scope-bounded currency refresh citing the operator's review.

## Focused confirmation (2026-09-22)

One fresh reviewer context (`/root/efficiency_readiness_verify`) verified the revised dependency, measurement, propagation and supersession contracts against the tree and approved. It covered code, QA, architecture and documentation perspectives as one correlated context, not four independent lanes. The remaining task wording was aligned to the permitted not-propagated option: renderer constants remain unchanged; canonical seeds and authored upgrade reconciliation own the broader guidance. No source tests were claimed. Existing current readiness approvals were consumed by prepare and activation. Coordinator and reviewer used inherited host settings for cross-cutting contract reasoning; runtime model identity was not exposed. An additional inventory worker could not be spawned because the host thread limit was reached, so implementation investigation proceeds locally.
