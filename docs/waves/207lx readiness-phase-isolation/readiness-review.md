# Readiness review — phase isolation

Owner: Engineering
Status: active
Last verified: 2026-10-08

## Briefing and allocation

Wave: `207lx readiness-phase-isolation`

Reviewed change: `206oh-bug readiness-delivery-phase-isolation`.
Phase: readiness. Current receipt: `review-policy-3ee7280c80ff0820a2dc`.

The initial primer and first QA/code pass assessed receipt `review-policy-e1ec831d75e946069b0e`. Before any approval write, the coordinator added the direct diagnostic verification consumers `test_lifecycle_golden.py` and `fixtures/lifecycle-gate-golden.json`, including declared diagnostic deltas and overwrite protection, to Requirement 5 and serialization scope. The current receipt publishes that bounded addition. Initial QA/code verdicts require focused consumer reassessment; all actual approval writes must bind the current receipt.

This review assesses whether the admitted plan can be implemented correctly on the current tree. It does not attest that the proposed behavior already exists. The packet is the admitted change document, its five required ACs, the current phase evaluator and direct lifecycle consumers, and the executable review protocol. No implementation, activation, closure, commit, push, ledger rewrite or semantic plan mutation is part of this review.

The authority boundary is between approval of an implementation plan and approval of completed delivery. Source scope is the canonical relation and projection in `review_evidence.py`, their readiness and delivery consumers in `lifecycle_gates.py` and `lifecycle_gate_support.py`, the affected tests named in the change, and the review contract in `docs/specs/mcp-tool-surface.md` and `docs/contributing/review-and-evals.md`. The existing council aliases, sealed finding origins, actor/independence checks and operator closure authority must remain intact.

The coordinator uses the available inherited model and effort; runtime identity is not independently observable. Work is bounded to one isolated primer, five fresh required-lane assessments, the configured fixed reality-checker seat, a distinct rotating best-alternative seat, and council synthesis. Reviewer contexts run sequentially when the public wave needs the remaining host slot. Fixed configured seats are architecture, security, QA and reality-checker; docs-contract is the distinct rotating seat. Code review is an additional required lane. Reviewers receive the shared primer but not other seats' conclusions before independent assessment.

## Red-team primer

The primer ran in an isolated fresh context, `/root/phase_readiness/primer`, without implementation or lifecycle writes. Depth was enhanced standard: five stances and three questions by explicit coordinator direction. Applied stances: adversarial, constructive, simplicity, first-principles and analogical.

Strongest challenge: isolate the finding-to-approval relation before both unresolved withholding and terminal-repair chronology. Exempting only open delivery findings would permit a later delivery repair to stale an approved readiness plan. Preserve per-key mixed/default phase selection rather than applying a projection-wide readiness flag.

Best alternative: make the selected central design concrete as one per-key relation. Determine the effective approval phase, canonicalize the key, exclude canonically delivery-origin findings only from readiness, and preserve unknown-origin, readiness-origin, delivery and operator behavior. Derive affected keys once and reuse structured facts for chronology, status, guided actions and gate diagnostics. This is a refinement of the accepted design; no stronger competing design was demonstrated.

Every seat must answer these questions:

1. Can one canonical ledger prove readiness stays approved before and after terminal repair of a delivery finding, while delivery stays withheld until its affected approval follows the repair?
2. Do explicit readiness/delivery, mixed/default, custom, council-alias and operator rows preserve their phase and authority rules, including conservative unknown-origin handling?
3. Can public gates and guided actions distinguish absent, invalid/stale and finding-withheld approvals through structured facts, without demanding delivery repair before implementing its approved plan?

The primer found no demonstrated plan blocker. Current evidence anchors: `review_evidence._finding_affects_signoff`, `_finding_origin_phases`, `review_authority_projection`, `_council_approval_phase`, `_approval_rows`, `ReviewAuthority.signoff_current`, `lifecycle_gates.review_lanes_gate` and `_evaluate_shared_delivery_state`. The plan's `prepare_review_lanes_gate` name does not resolve; the actual equivalent is `review_lanes_gate(review_phase='prepare')`. This is a locating note, not a semantic amendment.

## Independent assessments

All five required lanes approve readiness on the current receipt. They assess plan implementability and falsifiability, not completion of the unchecked ACs. No typed finding was warranted under the readiness finding bar.

| Lane or seat | Fresh nonimplementation context | Verdict and evidence |
| --- | --- | --- |
| Code and QA; QA fixed seat | `207lx-qa-code-fresh-20261009-a` | Both approve. These are two remits in one disclosed context, not two isolated reviewers. Current evaluator, fixture producers, gates, golden and direct server consumers were read. Own registered wrong-actor controls rejected. An unchanged golden-oracle probe matched baseline, detected injected bad outcome, refused update-only overwrite and preserved fixture bytes. |
| Architecture fixed seat | `readiness207lx-architecture-seat-20261008-v1` | Approve; no severity. Central relation preserves evaluator/facade ownership, direction and one authority. Updated golden consumers were assessed. Own exact-actor dry-run rejected. |
| Security fixed seat | `security-readiness-207lx-20261008-independent` | Approve with notes; no finding or severity. Sealed origins, unknown handling, receipt/actor/independence, operator authority and direct advisory/admission consumers were checked. Local trusted-actor assumptions are unchanged; no exploit chain was invented. Own exact-actor dry-run rejected. |
| Reality-checker fixed seat | `/root/phase_readiness/reality_seat` | Approve; no severity. Static known-bad control refuted an already-phase-aware relation and confirmed both chronology branches depend on it. Future paired-ledger behavior remains planned. |
| Docs-contract rotating seat | `207lx-docs-rotating-fresh-20261008-a` | Lane and seat approve; no severity. Contract and direct-consumer scope cover truthful remedies. Own invalid-actor preview rejected; complete correct-actor preview validated and bound the current receipt. |

Initial code/QA judgments were refreshed after the two golden paths and explicit delta/overwrite protection entered the packet. Architecture assessed that refreshed packet during its full pass. Before final synthesis, code/QA and security also read the existing direct consumers `server_impl._prepare_lane_review_state`, `_attach_prepare_readiness_advisories` and `wf_implement_wave_response`, plus `ReadinessSignalTests.test_lane_advice_matches_activation_union_and_current_receipt`. These are current Requirement 1/4/5 consumers, not an added authority mechanism. Reality and docs assessed them in their first passes. Code/QA reaffirmed their current approvals; security's write used its supplemental evidence.

## Council synthesis

The chair compared anonymized seat merits in randomized order before attaching role identities. It weighed authority preservation, both chronology branches, direct-consumer coverage, falsifiable ACs and honest execution limits. No seat supplied a required-lane blocker to dilute. The five configured seats independently reached the same admissibility decision: `seat_agreement=unanimous`, `max_severity=none`. No challenge-round trigger occurred.

The primer was confirmed and extended: all seats required phase selection before both open-head withholding and terminal-repair chronology, and retained per-key default/mixed selection. They did not treat current-file inspection or a guard/oracle probe as proof of future implementation behavior.

The rotating seat's strongest competing approach was separate immutable readiness and delivery views over the unchanged ledger, followed by a shared evaluator. All four fixed seats explicitly weighed that alternative after their independent first passes and reaffirmed. Views preserve history, but mixed/default projections select phase per key, operator approval spans findings, and sealed origin requires linked root/run history. A view needs exceptions or reconstructs the same relation. The accepted central per-key relation gives fewer mechanisms to qualify and one source for chronology, status, guidance and gate remedies. No stronger alternative emerged.

Implementation notes recommended by the council:

- Resolve canonical key and effective phase once before deriving applicability; preserve operator precedence and conservative unknown origin.
- Use one structured reason/remedy source for projection, `review_lanes_gate`, server advice and implementation admission. Preserve diagnostic identifiers, outcomes, advisory-only behavior and null/unavailable observations.
- Preserve golden codes, outcomes, unrelated fields and overwrite refusal; adapt only explicitly declared message and observation deltas. Retain advisory/admission roster agreement and read-only byte invariance.
- Update the two named review contracts with unresolved and terminal-delivery isolation. Check canonical seed 209 and rendered guidance for direct contradictory claims, changing canonical source only when its contract needs correction.

These are implementation notes within existing requirements, not semantic plan amendments or completed AC claims. Delivery must still execute the paired canonical-ledger/public-gate controls, custom/alias/default cases, authority negatives and terminal chronology.

## Authority controls and limitations

The coordinator exercised `wf_review_wave(wave_id='207lx', phase='prepare')`: full docs lint passed and the canonical guided action projection named the five missing required readiness approvals plus council readiness. A deliberate read-only `wf_review_event` approval preview using actor `implementer` for `qa-reviewer` returned `invalid_review_event` and the exact-actor requirement, without writing. This is a readiness-safe known-bad control, not an approval claim about unimplemented behavior.

The chair additionally exercised a complete-integrity current-receipt approval preview with `actor='implementer'` for `council-readiness`. It rejected with `invalid_review_event` and the exact `council-chair` requirement. The three core phase files' byte fingerprints remained unchanged between the initial review and final seat review: `review_evidence.py` SHA-256 `8bb906408fee688f17aecfd24a7bf544a87c6d0ad2f702eefef60556e07acd5a`; `lifecycle_gates.py` `69f5bea2141cbea691bf8c2b153f19e5e6545fe068478d5e28c65521151488a8`; `lifecycle_gate_support.py` `65c9d11276eadefb0b6a5e72ae16400ec94f813006a9f3da1dc6a6f23d3f21c3`.

Live MCP source reads were used rather than accepting indexed summaries. Setup diagnostics earlier reported changed inputs and loaded-code staleness; no setup, model installation or index mutation ran. Fresh local process probes remain necessary for implementation qualification. The public wave was OPEN during early readiness review and is now paused; this review performs no activation. Root's generic scratch reproduction is supplemental evidence and is not claimed as a seat's own execution.

## Verdict

Council readiness verdict: approve the admitted plan on `review-policy-3ee7280c80ff0820a2dc`. Five required lane approvals and typed council readiness are current. `wf_prepare_wave(wave_id='207lx', mode='ready')` returned `status='ok'`, `readied=true`, `transitioned_to_active=false`, clean garden/lint, no repairs and no pending readiness lanes, without rotating the receipt. The wave remains planned and readied. No demonstrated plan blocker, material dissent, waiver or implementation qualification claim. No activation or closure occurred.
