# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-03

wave-id: `1p9qh java-csharp-enterprise-accuracy`
Title: Java / C# Enterprise Accuracy

## Objective

Make the graph see the structures enterprise Java and C# codebases are organized around: inheritance. When this wave closes, `extends`/`implements` edges exist for both languages (today no inheritance relation exists at all), calls to supertype-defined methods and `super.` calls resolve, interface calls contribute implementations to impact analysis, and two confirmed Java import defects (wildcard truncation, spurious `external::static` edges) are fixed.

## Changes

Change ID: `1p9q9-bug java-import-wildcard-static-fixes`
Change Status: `planned`

Change ID: `1p9qa-enh inheritance-edges-java-csharp`
Change Status: `planned`

Change ID: `1p9qb-enh java-receiver-annotation-accuracy`
Change Status: `planned`

## Wave Summary

The Java/C# tier of the graph-accuracy investigation (2026-07-03): `1p9q9` fixes wildcard/static import handling (bug), `1p9qa` adds the inheritance model (`extends`/`implements` relations, single-definer inherited-method resolution, dispatch-aware impact) for Java + C#, `1p9qb` closes the `this.field` receiver gap, fixes the annotation-type kind misclassification, and rekeys same-package disambiguation on parsed `package` declarations. Kotlin deferred by explicit decision; every binding change carries calibration and the wave carries an adversarial faithfulness review.

## Journal Watchpoints

- Sequencing inside the wave: `1p9q9` (import facts) lands first; `1p9qa` supertype resolution and `1p9qb` disambiguation rekeying both consume import behavior. `1p9qa` ws3 and `1p9qb` ws1 touch disjoint branches of `_resolve_java_receiver_type` — coordinate merge order.
- Single coordinated `GRAPH_BUILDER_VERSION` bump across all three changes at integration.
- All three changes alter binding behavior: the consolidated adversarial faithfulness review lane at implementation review is required (standing security-control-faithfulness rule).
- `docs/specs/mcp-tool-surface.md` relation vocabulary is touched here (`1p9qa`) and potentially by wave `1p9qi` (`writes` relation decision) and wave `1p9q3` (report metadata) — one integration owner for that doc when multiple waves are in flight.
- Follow-up candidates deliberately not in scope: Kotlin inheritance (cheap once the model lands), deep chained receivers, `throws` edges (no consumer). Blocking: none external; C# fixtures enter the multi-language pack — coordinate fixture conventions with wave `1p9q8` if both are open near-simultaneously.

## Participants

- code-reviewer — all three changes touch `.wavefoundry/framework/scripts/*.py`
- qa-reviewer — required (bug fix `1p9q9` per `review_policies.require_qa_reviewer_for_bug_fixes`) and all change docs carry AC priority tables
- architecture-reviewer — graph-model contract change (`extends`/`implements` relation vocabulary) and resolver module seams
- performance-reviewer — resolver hot-path additions (supertype walk in the per-call resolution path)
- red-team, reality-checker — council seats (prepare phase); consolidated adversarial faithfulness lane re-runs at implementation review

## Review Checkpoints

- Prepare wave — readiness verdict (2026-07-03): READY. Council ran at standard primer depth. Red-team's strongest challenge — a single wrong supertype edge is an error *amplifier*: the inherited-method walk converts one mis-resolved `extends` target into many wrong call binds, a different risk class than one-off wrong binds — was accepted and resolved by amendment: `1p9qa` Requirement 4 now mandates bind provenance (each inherited bind records the supertype hop it resolved through), making the amplification auditable in calibration and targeted by the adversarial lane. Architecture seat confirmed the relation-vocabulary addition is the right model tier (edges, not resolution-time-only walking) and flagged the three-way `docs/specs/mcp-tool-surface.md` coordination (with waves 1p9q3 and 1p9qi) — recorded as a watchpoint. QA seat confirmed the bug change `1p9q9` carries both flip-direction tests and the no-`external::static` whole-payload assertion; reality seat confirmed grammar fields (`superclass`/`super_interfaces`/`base_list`) exist as claimed and that the C# first-base convention is inert for unresolved bases. Performance seat: the supertype walk runs only on failed direct lookups, bounded depth — acceptable; measured in calibration. Strongest alternative (resolution-time supertype walking without persisted edges) recorded and declined — the edges themselves are the durable navigation/impact value. AC priorities recorded on all three change docs. Product-owner acknowledgment: not applicable (framework-internal accuracy work).
- Security seat (rotating): no trust boundary is crossed — all three changes operate on repo-local source through existing parse paths with no new input surfaces, no user-supplied patterns, and bounded traversal (depth-capped supertype walk). Graph edges feed review-support impact analysis, so the amplification challenge above is an integrity concern; the provenance amendment plus the mandatory adversarial faithfulness lane at implementation review cover it. No security findings.
- **Prepare-phase Wave Council [prepare-council] — 2026-07-03: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: a wrong supertype edge amplifies through the inherited-method walk into many wrong call binds — resolved by the 1p9qa bind-provenance amendment making amplification auditable; strongest-alternative: resolution-time supertype walking without persisted inheritance edges — declined, the edges are the durable navigation and impact value)

## Review Evidence

- wave-council-readiness: approved 2026-07-03 — prepare council synthesis verdict READY after the 1p9qa bind-provenance amendment; no unresolved blocking findings
- operator-signoff: pending operator confirmation at closure

## Dependencies

- No external wave dependencies. Synergy note: wave `1p9qi` (`1p9qg` entity mapping) builds on `1p9qa`'s annotation-argument groundwork indirectly; neither blocks the other.
