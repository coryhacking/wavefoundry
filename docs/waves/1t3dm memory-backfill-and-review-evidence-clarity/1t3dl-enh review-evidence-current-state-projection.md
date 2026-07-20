# Review Evidence Current-State Projection

Change ID: `1t3dl-enh review-evidence-current-state-projection`
Change Status: `complete`
Owner: framework
Status: complete
Last verified: 2026-07-19
Wave: `1t3dm memory-backfill-and-review-evidence-clarity`

## Rationale

The external `events.jsonl` ledger correctly preserves every approval,
invalidation, repair, and reverification event. Its Markdown projection does
not: every finding currently appends another
`wave-council-delivery: withdrawn — <finding> requires affected-lane
re-verification` line to `## Review Evidence`. Reverification appends the same
withdrawal again, so a contentious wave can accumulate dozens of repetitive
lines while the operator still cannot see, at a glance, why an approval is
currently withheld or which lane must act next.

History belongs in `events.jsonl`; `wave.md` should communicate current state.
This change replaces append-only approval-state prose with a deterministic,
marker-owned current-state projection. A withheld lane names the current
blocking findings, required reviewer lanes, and next action. Human-authored
readiness decisions, historical deviations, verification notes, and council
narrative remain readable and are never collapsed into machine bookkeeping.

## Requirements

1. **Single historical authority.** `events.jsonl` remains the append-only
   authority for every approval, withdrawal/invalidation, finding, repair,
   reverification, and convergence event. The Markdown projection contains no
   second event history.
2. **One current row per signoff key.** Add one canonical
   `<!-- wave:review-status begin/end -->` block under `## Review Evidence`.
   Row identity is the canonical `signoff_key`, not its actor lane: for example,
   `wave-council-readiness` and `wave-council-delivery` are separate rows even
   though both are recorded by the `wave-council` actor. Render exactly one
   current row for each required specialist/council/operator signoff with
   `Signoff`, `State`, `Why`, and `Next action` columns; a friendly lane label
   may be secondary display text only.
3. **Actionable withheld reasons.** A `withheld` state must name the current
   blocking finding IDs, their unresolved `blocking_required_lanes`, and the
   operation needed to move forward. “Withheld” or “withdrawn” without a
   derived reason is invalid. Multiple findings are grouped once, not repeated
   as separate signoff lines.
4. **Current-state derivation.** Approval state is derived from the latest
   applicable approval evidence plus current finding heads and per-lane
   staleness rules. A later unaffected repair cannot withhold a lane; a later
   valid approval clears the displayed reason without deleting history.
5. **Replace, never append.** Finding, repair, reverification, and approval
   writes through `wave_record_review_evidence`, plus mutating prepare/close
   modes, rebuild the owned status block through the existing ledger-first,
   recoverable write protocol.
   They must stop appending approval-state lines to human-authored Markdown.
   Upgrade adoption/compaction acquires the same cross-process review-event
   writer lock as event append; it cannot race a concurrent review mutation.
   Every mutating path acquires that lock before reading, then re-reads
   `events.jsonl`, adoption state, and `wave.md`, derives current state, and
   writes in canonical ledger → adoption proof → projection order. A failure
   after ledger/adoption commit returns the existing `adoption_pending` or
   `projection_stale` partial-success state and converges on retry; it never
   overwrites from a pre-lock Markdown snapshot.
   `wave_review`, prepare dry-run, and close dry-run remain observational:
   they derive and report the same current state without writing the ledger,
   adoption proof, or projection.
6. **Narrative preservation.** Keep human-authored prepare councils, delivery
   council narratives, verification summaries, retrospective-repair notes,
   and explicit historical deviations such as
   `pre-implementation-review: missed`. Projection refresh must be
   byte-preserving outside its owned marker.
7. **Gate authority.** For an adopted external-ledger wave, review/close gates
   read typed ledger-derived current approval state, not arbitrary historical
   prose ordering. There is no dual-authority fallback. Upgrade must complete
   the existing one-way adoption for any active/readied legacy wave before its
   next lifecycle mutation.
   Eligibility is explicit:
   - external adopted ledger → regenerate from external events;
   - previously adopted typed-inline ledger → externalize losslessly, then
     regenerate;
   - non-adopted active/readied prose-only wave → block mutation with an exact
     typed-evidence/adoption recovery command;
   - non-adopted closed wave → report only, never fabricate or mutate.
8. **Upgrade compaction.** Upgrade regenerates the current-state block for every
   adopted ledger-backed wave and removes only machine-generated repetitive
   approval-state lines proven equivalent to ledger events. Human prose and
   historical events remain untouched. Non-adopted closed history is reported,
   not guessed or rewritten. A withdrawal-looking human line with no exact
   ledger equivalence is preserved. Ambiguous/malformed/duplicate marker state
   fails closed without rewriting.
9. **Consumer parity.** Dashboard, MCP resources, `wave_review`, `wave_close`,
   docs lint, and rendered summaries consume the same derived current state and
   display the same reason/next action.
10. **Bounded output.** Projection size grows with the number of current lanes
    and current blocking findings, not event count or review-cycle count.
    Finding IDs may be capped only with an explicit “+N more” count and a
    pointer to `events.jsonl`.

## Scope

**Problem statement:** `wave.md` duplicates ledger history as repetitive
withdrawal lines and obscures the reason a current approval is withheld.

**In scope:**

- A typed current approval-state derivation and compact Markdown table.
- Removal of `_append_review_evidence_state_line` behavior for ledger-backed
  finding/approval events in favor of serialized, recoverable projection
  rebuild.
- Exact reason and next-action synthesis from current finding heads,
  `blocking_required_lanes`, affected approvals, and approval chronology.
- Review/close parser and validator migration to typed ledger-derived state.
- One-way upgrade cleanup of machine-generated duplicate state lines for
  adopted ledgers, preserving human narrative.
- Dashboard/resource/tool/doc parity and adversarial tests using the real
  repetitive `1sxj7` pattern.

**Out of scope:**

- Deleting, compacting, or rewriting `events.jsonl` history.
- Summarizing every historical transition in `wave.md`.
- Changing finding actionability, approval-staleness, signoff ownership, or
  executable-evidence requirements.
- Fabricating adoption/evidence for non-adopted historical waves.
- General Markdown cleanup outside the owned projection and proven generated
  approval-state lines.

## Acceptance Criteria

- [x] AC-1: A ledger containing repeated finding, repair, and reverification
  cycles renders one row per canonical signoff key and no repeated generated
  `wave-council-delivery: withdrawn` lines. (required)
- [x] AC-2: Every withheld row names current blocking finding IDs, unresolved
  reviewer lanes, and an exact next action; a reasonless withheld state fails
  validation. (required)
- [x] AC-3: Approving after all required reverifications changes the one current
  row to approved while all earlier withdrawal/repair events remain unchanged
  in `events.jsonl`. (required)
- [x] AC-4: An unaffected later repair leaves the lane approved, while an
   affected repair with a required lane makes it withheld; fixtures cover
  specialist, distinct readiness/delivery council keys sharing one actor, and
  operator final-gate semantics. (required)
- [x] AC-5: Projection refresh is byte-preserving outside the owned marker,
  including prepare councils, explicit historical misses, verification notes,
  project-authored review prose, and a human-authored withdrawal-looking line
  lacking ledger equivalence. Duplicate, unbalanced, or malformed projection
  markers fail closed. (required)
- [x] AC-6: `wave_review`, `wave_close`, dashboard parsing, MCP resources, and
  docs lint return the same current state/reason from one ledger fixture.
  Finding, repair, reverification, and approval writes plus mutating
  prepare/close paths each rebuild through the shared helper; `wave_review`,
  prepare dry-run, and close dry-run are fixture-proven non-writing. (required)
- [x] AC-7: Upgrade converts an adopted `1sxj7`-shaped wave from dozens of
  generated withdrawal lines to the compact block, is idempotent, and leaves
  `events.jsonl` plus human narrative byte-identical. A real two-process race
  with an event append proves compaction shares the review lock, and a no-Git
  target behaves identically. (required)
- [x] AC-8: Active/readied legacy waves complete one-way ledger adoption before
  lifecycle mutation when a lossless typed-inline source exists. Prose-only
  active/readied waves block with the exact evidence/adoption recovery command;
  adopted waves never fall back to prose authority, and non-adopted closed
  waves are reported without mutation. (required)
- [x] AC-9: Projection output is bounded by current lanes/findings; a many-cycle
  fixture proves constant output once current heads are unchanged. (important)
- [x] AC-10: Full framework suite, server/review-evidence/dashboard/upgrade
  focused suites, docs lint, and execution from a built then installed/upgraded
  package pass—not merely source-string presence. (required)
  **Status:** the final exact-tree run passed 5,972/5,972 across 56 isolated
  files. Review evidence 89, dashboard/browser 182, upgrade 332, package 97,
  and MCP upgrade/status 25 pass, including executable installed/upgraded
  targets. An earlier load-sensitive p95 failure passed 3/3 in isolation and
  did not recur.

## Tasks

- [x] Implement typed current approval-state derivation from ledger heads and
  approval evidence.
- [x] Render the marker-owned `Signoff | State | Why | Next action` block.
- [x] Replace per-event Markdown appends with serialized ledger-first projection
  rebuild.
- [x] Route review/close/dashboard/resources/lint to the same current-state
  helper and remove prose-order authority for adopted waves.
- [x] Implement one-way adopted-wave upgrade compaction and legacy-active
  adoption handling.
- [x] Add real `1sxj7` repetition, per-lane staleness, approval recovery,
  narrative-preservation, malformed-marker, all-mutation-path,
  two-process-compaction, no-Git adoption, idempotency, and bounded-size
  fixtures.
- [x] Add crash-injection after ledger and adoption writes plus concurrent
  event-versus-prepare/review/close controls that prove locked re-read and
  partial-commit recovery.
- [x] Update review-evidence, lifecycle, dashboard, upgrade, and tool-surface
  documentation and canonical prompt carriers.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| state-derivation | implementer | — | Approval chronology + current finding heads |
| markdown-projection | implementer | state-derivation | Compact block, narrative preservation |
| gate-consumers | implementer | state-derivation | Review/close/lint/resources/dashboard |
| upgrade-migration | implementer | markdown-projection, gate-consumers | One-way adopted-wave cleanup |
| verification-docs | qa-reviewer + docs-contract-reviewer | all | Real repetition fixture and carrier parity |

## Serialization Points

- `review_evidence.py` owns typed derivation and projection rendering;
  `server_impl.py` must stop appending state lines in the same change that gates
  switch to ledger authority.
- Every lifecycle mutator acquires `review_event_write_lock` before its first
  authoritative read and re-reads ledger/adoption/Markdown inside the lock.
- Dashboard, lint, resource, review, and close consumers must migrate together
  so no surface reports a different current approval reason.
- Upgrade cleanup must call the same projection helper; it must not implement a
  second Markdown parser or state derivation, and it must acquire the canonical
  review-event writer lock before reading ledger and rewriting Markdown.

## Affected Architecture Docs

- `docs/architecture/data-and-control-flow.md` — event authority versus current
  Markdown projection and consumer flow.
- `docs/architecture/testing-architecture.md` — authority parity,
  narrative-preservation, upgrade, and bounded-output fixtures.
- `docs/specs/mcp-tool-surface.md` — review/evidence response and recovery
  semantics.
- Review/close/upgrade canonical seeds and rendered prompt carriers where they
  currently describe signoff lines.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The repeated-line defect is the core operator problem |
| AC-2 | required | Withheld state must explain why and what to do |
| AC-3 | required | Current state must converge without losing history |
| AC-4 | required | Per-lane staleness semantics must remain correct |
| AC-5 | required | Projection ownership cannot erase human evidence |
| AC-6 | required | Every consumer needs one answer |
| AC-7 | required | Existing projects need an upgrade repair |
| AC-8 | required | No dual authority after adoption |
| AC-9 | important | Output must scale with current contention, not history |
| AC-10 | required | Framework and consumer delivery gate |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-19 | Planned from the closed `1sxj7` Review Evidence field report; exact source inspection found each finding event appends another withdrawal line before rebuilding only the separate Finding Synthesis projection. | Attachment; `server_impl.py:12153-12178` |
| 2026-07-19 | Implemented one typed current-state derivation and marker-owned projection for lifecycle gates, resources, dashboard, and docs lint; ledger-first mutations rebuild both projections under the canonical lock. Upgrade externalizes typed inline evidence one way, blocks ambiguous active/readied prose, and reports closed prose-only history without rewriting it. | `review_evidence.py`; `server_impl.py`; `dashboard_lib.py`; `wave_validators.py`; `upgrade_wavefoundry.py` |
| 2026-07-19 | Consumer and recovery verification passed, including per-lane approval chronology, malformed markers, externalization idempotency, partial-commit replay, concurrent typed writes, dashboard current-state output, and stale-projection lint detection. MCP reload now also notifies on callable tool additions/removals, which is required for the two new memory tools to become discoverable after upgrade. | `test_review_evidence.py` (85); `test_dashboard_server.py` (180); `test_docs_lint.py` (819); `WaveMcpReloadTests` (9); `test_upgrade_wavefoundry.py` (313) |
| 2026-07-19 | Delivery repair centralized required status keys, made the projection mandatory for every external-ledger wave, and aligned lifecycle/resource/dashboard/lint/upgrade consumers with one blocking-only head derivation. Current-wave selection now prefers the active wave, resource recovery derives from the ledger without revalidating stale disk, and reload fixtures prove retained resource callbacks resolve current implementation behavior. Extracted package and upgrade artifacts execute the shipped Python and JavaScript paths. | `test_review_evidence.py` (89); `test_dashboard_server.py` (181); `test_docs_lint.py` (828); `test_upgrade_wavefoundry.py` (321); `test_build_pack.py` (97); `test_server_tools.py` (1,391) |
| 2026-07-19 | Final delivery repair closed the old-runner/new-validator gap: an upgrade process holding the pre-upgrade module now loads and executes the newly extracted current-state projector before docs lint, records the completed projection in the upgrade lock, and is idempotent on retry. | `HistoricalMemoryUpgradeExtensionBootstrapTests`; `test_upgrade_wavefoundry.py` (322) |
| 2026-07-19 | Delivery re-review closed the adjacent retry gap. The canonical resume path now treats `review_status_projection` and `docs_gate` as recoverable, regenerates current state on every retry instead of trusting an old lock marker, and then runs lint. | `ResumeAfterGateTests`; exact external-ledger recovery; `test_upgrade_wavefoundry.py` (324) |
| 2026-07-19 | Final architecture/release/QA probes proved every publication and cleanup entry point honors the retained projection/docs failure. The backstop reports projection failure as typed review recovery, and both CLI/MCP direct the caller to the only valid resume phase. | Upgrade 329/329; MCP upgrade/status 25/25; canonical 5,958/5,959 with unrelated p95 fixture 3/3 green in isolation |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-19 | Keep complete history only in `events.jsonl`; render current approval state in `wave.md`. | The external ledger already exists precisely to separate machine history from human-readable current state. | Retain append-only Markdown (rejected: unreadable and duplicative) |
| 2026-07-19 | A withheld state carries reason and next action derived from current heads. | State without causal/action information does not help the operator. | Display only `withheld` (rejected: recreates the reported ambiguity) |
| 2026-07-19 | Preserve project-authored narrative outside one owned marker. | Readiness rationale and historical deviations remain valuable human evidence. | Regenerate all Review Evidence prose (rejected: destroys authorship and context) |
| 2026-07-19 | Key current rows by `signoff_key`, not actor lane. | Readiness and delivery councils share an actor but represent independent approvals. | One row per actor (rejected: collapses distinct gates) |
| 2026-07-19 | Preserve the existing ledger-first partial-commit protocol instead of claiming filesystem atomicity. | Three files cannot be replaced atomically; current typed recovery states already express safe convergence. | All-or-nothing claim (rejected: false); Markdown-first write (rejected: can publish state absent from the ledger) |
| 2026-07-19 | Block prose-only active/readied legacy waves instead of fabricating adoption. | Only typed inline or external events can be externalized losslessly. | Parse arbitrary prose into evidence (rejected: invents authority) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Projection disagrees with gates | One typed derivation consumed by every surface plus parity fixtures |
| Upgrade deletes human notes | Exact generated-line recognition, marker ownership, byte-preservation tests, report-only on ambiguity |
| Many current findings still produce noise | Group by lane/reviewer and cap IDs with an explicit remaining count |
| Legacy prose remains authoritative accidentally | One-way adoption before mutation and no fallback for adopted ledgers |
| Approval semantics change unintentionally | Reuse existing staleness diagnostics; assert old gate matrices unchanged |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
