# Readiness phase isolation — implementation evidence

Owner: Engineering
Status: draft
Last verified: 2026-10-08

The canonical finding relation receives each approval's effective phase. A sealed delivery origin is irrelevant to readiness currency in every selected lane, including custom lanes and council aliases; delivery and operator authority retain their existing finding and repair chronology rules. The ledger is neither filtered nor rewritten. Structured approval facts now distinguish absence, invalid evidence, stale receipts, withholding and approval, with the canonical reason and next action. Direct Prepare, admission and delivery presentations consume those facts. Legacy prose diagnostics remain unchanged.

The generic real-producer scratch reproduction initially withheld five specialist/custom readiness lanes while approving council readiness. After the fix, every readiness lane is approved, implementation admission succeeds, all paired delivery lanes remain withheld, and ledger bytes are unchanged. Logs: `/tmp/wf-207lx-phase-baseline.log` and `/tmp/wf-207lx-phase-fixed.log`.

Shipped regression coverage includes the real-producer admission/delivery pair, readiness-origin withholding through review/admission/advisory consumers, sealed versus mutable origin, unknown-origin compatibility, canonical/legacy aliases, default mixed selection, terminal repair chronology, receipt currency, reviewer identity, independence and operator authority. Terminal chronology uses projection records; the new public producer case proves unresolved-finding admission and closure behavior. It does not claim a new complete producer repair-chain test.

- Review-evidence and phase owners: 221 tests, no skips, 11.078s (`/tmp/wf-207lx-owned-tests.log`), followed by the additional readiness-origin consumer control: phase owner 32 tests, no skips, 9.495s (`/tmp/wf-207lx-phase-consumers.log`). An in-memory mutation restoring council-only exemption fails the expected readiness assertion.
- Lifecycle golden and readiness convergence: 15 tests, no skips, 6.050s (`/tmp/wf-207lx-golden-controls.log`). Golden regeneration used the existing explicit helper with both required flags; the comparison ignores ambient regeneration flags and the overwrite-refusal control remains intact. Declared authority fields are checked before removing them for comparison with the historical extraction oracle; codes, outcomes and unrelated fields remain pinned.
- Lifecycle gates and server lifecycle consumers: 642 tests, two existing skips, 105.834s (`/tmp/wf-207lx-consumer-qualified.log`). These are direct focused unittest checks, not a framework receipt. The first diagnostic runner attempt was red before consumer expectations were updated and also noticed concurrent source edits; it is not qualification evidence.
- Full documentation validation passes; `git diff --check` passes. The hand-authored MCP contract states the phase and diagnostic behavior. The generated review-and-evals carrier already expresses same-phase review and was preserved.

Full canonical qualification and independent delivery approval remain pending the separately authorized graph-community repair and the remaining C5 link-container repair. The standing framework receipt is stale. No wave is closed, committed or pushed by this checkpoint.
