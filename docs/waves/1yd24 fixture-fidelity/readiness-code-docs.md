# Fixture-fidelity readiness: code and docs contract

Owner: Engineering
Status: active
Last verified: 2026-09-20

## Verdicts and independence

Code-reviewer: approved for the test-helper plan. Docs-contract-reviewer: needs-revision for finding `fixture-propagation-contract`. These are two role assessments in one independent reviewer context, `1yd24-readiness-code-docs`, not two independent votes. No implementation or repair was authored by this reviewer. This is the first full readiness assessment; remaining work follows the bounded repair/focused-verification protocol.

## Blocking finding: fixture-propagation-contract

The admitted `1yd96-doc fixture-fidelity-harness-rule.md` Requirement 4 and required AC-3 promise regeneration that carries the seed's same text to project surfaces. That promise is false on the current renderer. `render_agent_surfaces._carrier_protocol_block` emits static common guidance referring to seed 209. `_initial_review_carrier_text` copies seed 239 only for a missing QA carrier; `reconcile_review_protocol_surfaces` preserves existing project-authored bodies. A seed-only edit plus regeneration therefore does not put the new wording into an existing QA role or into the seed-209 common carrier. The required AC cannot pass as written without unplanned propagation work or weakening its asserted property.

Bounded fix: preserve the guidance-only scope. Specify authoritative seed-209 pointer coverage, seed-239 copying for newly created QA roles, and an explicit hand-edited synchronization of this repository's project-owned QA guidance. Rewrite AC-3 and the render task to verify those distinct consumer contracts and preservation of existing unrelated project prose; do not claim automatic replacement or identical seed text in every existing carrier. No renderer expansion is necessary for that narrower, truthful contract.

Source/blocking/recheck lanes: docs-contract-reviewer and qa-reviewer (QA independently confirmed the same defect to the coordinator). Classification: real, admitted, required-AC correctness defect introduced by this plan; no attacker or authority gain; material verification impact. The supported renderer is reachable and the wrong propagation expectation is not prevented by existing parity checks.

## Executed bounded probes

1. Producer sequence feasibility. In disposable roots, call the canonical wave creator, change creator and admission producer; Prepare ready with scoped lint/garden/post-write/index stubs; optionally record the readiness run; record the council approval; then call final Prepare ready. Complete sequence returned `ok` with no blocking diagnostic. Omitting the readiness run returned `error` and `review_evidence_invalid`: “marked wave requires a `readiness` Review Run Record at this lifecycle phase”. The approval producer itself accepted the missing-run fixture, proving why the independent final-Prepare assertion matters. Initial Prepare published one receipt; its only blocking diagnostic was missing council approval, while AC-priority and lane-approval advisories remained nonblocking.
2. Renderer propagation. Add distinct sentinel text to copied seeds 209 and 239 in a disposable root, preserving an existing QA body. Execute the public `reconcile_review_protocol_surfaces`. Existing QA retained its body and did not acquire the 239 sentinel; the common review-and-evals carrier did not acquire the 209 sentinel. Remove only the disposable QA file and rerender: the newly created QA carrier acquired the 239 sentinel. This positive control disproves a broken seed or inaccessible renderer as an explanation.
3. Token feasibility. Python `tokenize` finds the declaration string despite a helper call elsewhere in the same sample file, retains a component-input declaration as a classifiable string, and does not claim a computed concatenation is a literal declaration. Current scan found 50 matching Python string tokens across nine files, including named `test_review_evidence.py` and `test_server_tools_lifecycle.py` corpus controls. This is a token inventory, not a fresh classification of every occurrence or a claim about the future guard implementation.

## Reproduction

Temporary scripts created for the probes:

- `/tmp/1yd24-producer-feasibility.py`
- `/tmp/1yd24-render-feasibility.py`
- `/tmp/1yd24-token-feasibility.py`

Run with `/Users/coryhacking/.wavefoundry/venv/bin/python -B`, setting `PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests`. The lifecycle script output is also at `/tmp/1yd24-producer-feasibility.out`. Durable source anchors are the canonical producer entry points and the renderer functions named above; this report records the observed controls if temporary files are later removed.

## Integrity and limits

All selected probes ran without unintended skips, reached the named public response/renderer/parser boundaries, used real producer outputs and concrete temporary files, and made non-vacuous assertions. Known-bad detection: omitted readiness run failed the final public Prepare oracle for the exact missing-run reason; renderer sentinel controls refuted the plan's same-text propagation claim. Method: readiness-safe-control.

No implementation behavior not yet written is claimed as executed. This is feasibility and current-tree evidence, not delivery acceptance. No network, repository source edit, real repository lifecycle mutation, or whole-suite run was performed. Diagnostic/setup subprocesses were scoped stubs; runtime lifecycle ordering was real. The literal guard's computed-string blind spot is explicit, and its exact annotation mechanics remain an implementation choice. MCP exact keyword/read tools grounded source retrieval; shell execution performed bounded probes. No semantic-index completeness claim is made.

## Primer response

A broad accepted-error whitelist would defeat the helper; Requirement 3 correctly requires step-local diagnostics and refuses swallowed approval/run failures. The final-Prepare positive and omitted-run controls are feasible and distinguish the intended path. AC-3 already prevents filewide helper exemptions and distinguishes component inputs from malformed fixtures. The small strict producer orchestrator with independent final-Prepare oracle is the appropriate bounded design; the only required plan repair is the propagation contract above.

## Focused verification after the bounded repair

Current packet: `review-policy-6a0c094179627d203926`, digest `b6c600f43d043f44f1a91f2ed6900b8da02aed5d163a0047a82c3b8c7842d186`. Reviewer context: `1yd24-focused-code-docs`; actor did not author the repair. The code and docs assessments share this context and are not independent votes.

Docs-contract-reviewer: approved; clear this lane for `fixture-propagation-contract`, leaving QA to clear its own lane. Code-reviewer: approved after reviewing repair effects. No remaining or replacement blocker was discovered in the focused packet.

Repaired Requirement 4, scope, AC-3 and task in `1yd96` now describe the real three-way transport: common canonical-seed pointer, fresh QA seed copy, and preservation of existing project-owned prose with explicit self-hosted synchronization. This removes the impossible same-text regeneration claim without introducing renderer behavior or weakening the five-field evidence contract. The sibling `1yd25` clarification scopes post-write/index stubs and explicitly includes separately tokenized f-string literal segments, retaining a bounded literal-only claim and an independent final-Prepare oracle.

Exact replay and adjacent controls: executed `/tmp/1yd24-render-focused.py` through `reconcile_review_protocol_surfaces`, retaining the original sentinel controls. Existing QA did not silently acquire the new seed text; fresh QA did. Common carriers contained the canonical seed209 reference and not the sentinel body. A manually synchronized project-owned QA sentence survived another render. Executed `/tmp/1yd24-producer-feasibility.py` again: complete canonical sequence returned final Prepare `ok` without blocking diagnostics, while omission of the readiness run returned `review_evidence_invalid` for the exact missing readiness Review Run Record. No unimplemented helper or new seed text is claimed as delivered.

All five integrity facts remain true for these readiness checks: no unintended skips, named public boundary reached, realistic concrete inputs, non-vacuous assertions, and known-bad detection. Method: readiness-safe-control. The original false propagation assumption is still rejected by the renderer negative control; the new contract agrees with both that negative control and fresh-role/pointer/manual-sync positive controls. Limits remain local temporary roots and scoped subsystem stubs; no additional whole-document review or delivery suite was run. Typed lane clearance and current-receipt approvals are coordinator-owned and were not written by this reviewer.
