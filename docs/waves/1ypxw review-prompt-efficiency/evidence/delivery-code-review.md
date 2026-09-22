# Independent delivery code review

Owner: Engineering
Status: active
Last verified: 2026-09-22

Date: 2026-09-22
Role: code-reviewer
Context: /root/ypxw_delivery_code (fresh delivery context; no implementation/readiness participation)
Final verdict: APPROVE for the code and test scope after C-1 and C-2 repair verification. The original blocking finding is preserved below as history. Retrieval after-measurement remains pending and is outside this approval.

## Scope and independent reference

Reviewed the wave objective and three admitted requirements, the five changed runtime scripts against `/tmp/1ypxw-before` (not HEAD), producer-backed lifecycle tests and consumers, and the renderer contract. MCP `wf_get_change`, `code_outline` and targeted `code_read` established owners and contracts; shell diff/AST comparison was used for exact prewave comparison and executable controls. The independent references were the prewave digest implementation, unchanged receipt semantic fields/identity function, the append-only per-lane readiness requirement, public response contracts and the handler digest fixture. Seed and authored prose received scope inspection rather than a complete sentence-by-sentence audit; the docs lane owns that audit.

All 45 entries in `delivery-tree.json` matched before and after review. `tree_moved_under_review`: false.

## Blocking finding C-1: required handler descriptions invalidate standing exact-source fixture

`test_mcp_tool_registry.HandlerDigestTests.test_every_handler_matches_its_pre_change_digest` fails. Independently reproduced with:

`PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests python3 -B -m unittest test_mcp_tool_registry.HandlerDigestTests`

Two tests run; one failure, zero errors/skips. Exactly two handlers differ from the standing fixture: `wf_review_wave` and `wf_review_event`. Independently comparing each wrapper AST against the prewave snapshot after removing only its leading docstring proves all other wrapper structure is unchanged. The new description is required by 1yoy2 AC-2, so reverting it would violate the plan. This is an omitted fixture migration, not a runtime behavior regression.

Recommended repair: update only those two exact-source hashes, preserving every other handler entry and the promised tool-surface and two lifecycle goldens. Preserve the digest implementation and its known-bad docstring mutation test. Record the narrow fixture migration; this satisfies existing AC-2 without changing its requirements. Do not suppress descriptions from all handler digests.

Changed hashes:

- wf_review_wave: `f14f8d5fcab7e3908465ecce17238599020ec16237e7d3f27a2e8d0098f94e49` → `5967b107fe0d341985f83b50382f34fb858352a3f8f7abc089143f9af5575d25`
- wf_review_event: `67b6dc6c6d4c2aea5c213c3f8a2dffa5409770e48122dfe1db9c8e9caf8fab11` → `761597d6e6614797f8899d991b0ab28715977e9a094f52c6693d36654da8c963`

Finding facts for coordinator synthesis: validation_status=real; scope_relation=admitted; introduced_or_worsened_by_wave=true; contract_relevance=required_ac (AC-5); supported_reachability=true; attacker_reachability=false; authority_domain=none; authority_delta=none; observable_impact=material; containment=detect_only; fix_risk=lower; repair_scope_bounded=true; repair_safety=safe; benefit_vs_fix_risk=greater; source_lanes=[code-reviewer]; approval_recheck_lanes=[code-reviewer,qa-reviewer]. No claim of user-facing execution failure; observable failure is the required full-suite verification gate. Enum spellings verified against the current schema.

## Executed evidence

- 173 tests passed, zero skips, in 18.148 seconds: `test_review_policy`, `test_review_evidence.EphemeralArtifactTokensTests`, `test_server_tools_lifecycle.WaveCouncilPolicyTests`, `test_lifecycle_golden` under the same PYTHONPATH command. These reach real lifecycle producers and response entry points; expensive lint is patched in narrowly focused response tests.
- Forty distinct canonical change bodies produce identical digest bytes from the extracted prewave `policy_input_digest` function and current function. `receipt_semantic_fields` and `derive_receipt_id` are AST-identical to prewave. This establishes compatibility without using the new metadata implementation as its own oracle.
- Every snapshotted `*golden*.json` remains byte-identical. This statement does not include `register-surface-handler-digests.json`, whose fixture stayed unchanged but no longer matches its producer.
- Latest readiness uses existing `_approval_rows(..., approval_phase='readiness')`, independently keyed by claim; historical rows remain intact. Delivery advice is phase-separated. Public response tests prove warnings persist through partial reapproval and disappear only after all lanes reapprove.
- Ephemeral classification is lexical and advisory. Producer tests assert create still appends records and dry run does not, cover both findings and approvals, mixed durable paths, bare test identifiers, scratchpad and root boundaries. It does not establish filesystem durability or existence, and does not claim to do so.

## Independent known-bad controls

Reproduce with `python3 -B 'docs/waves/1ypxw review-prompt-efficiency/evidence/delivery-code-controls.py'` from repository root. Mutations affect in-memory module bindings only, restored after each test; source stays untouched.

| Mutant | Detection | Result |
| --- | --- | --- |
| Scan historical readiness approvals forever | `test_repeated_receipt_advice_tracks_latest_approval_per_lane`, final all-reapproved assertion | Killed; assertion failure, no error/skip |
| Use globally latest approval rather than latest per lane | Same test, partially reapproved assertion | Killed; assertion failure, no error/skip |
| Remove scratchpad classifier | `test_ephemeral_evidence_advises_on_preview_and_write`, scratchpad fixture | Killed; assertion failure, no error/skip |

No survivors, so no full-file escalation was necessary. Budget: eight minutes; did not rerun whole framework suite, retrieve benchmark, perform native MCP reload or exhaustively mutate every branch. Coordinator is running canonical full-suite validation separately; no claim of green receipt is made here.

Integrity assertions for this review: test_ran_without_unintended_skip=true; public_path_reached=true (response producer paths, not transport); boundary_values_realistic=true; assertions_non_vacuous=true; known_bad_detected=true. Method: three independently constructed in-memory mutants killed by producer-path assertions, plus exact-source wrapper mismatch reproduced independently. These assertions support review evidence, not approval while C-1 remains open.


## Final integration review

Rechecked the final 48-path `delivery-tree-final.json` manifest before and after this pass: no mismatches. Compared all changes since the original review fingerprint: only the handler-digest fixture and two test-contract repairs changed; no runtime source changed after this lane's review. C-1's fresh independent `C1-reverification.md` confirms only two handler hashes plus explanatory provenance changed, all other 87 entries and digest algorithm remain intact, and 27 real registry/reload tests pass. C-2's fresh `C2-reverification.md` confirms the sixth QA condition and obsolete census allowlist entry were narrowly reconciled, retaining all original five conditions and census controls; eight tests and four independent mutants verify the repair.

Independently reran `test_mcp_tool_registry.HandlerDigestTests`, `test_fixture_fidelity_guidance`, and `test_record_layout_census`: ten tests pass in 0.628 seconds, zero skips/errors/failures. Independently recomputed `run_tests._hash_inputs()` and matched the standing `test-cache.json`: `result=ok`, 9,533 tests, hash `c7ad178ba2f8223f4ca113aa9970edfabba9cac9e2cb0f1bcd25d834afb8792e`. This validates the receipt's framework currency; the full run was coordinator-executed, not rerun by this lane.

Code-lane approval is now supported. Final integrity fields are all true: `test_ran_without_unintended_skip`, `public_path_reached`, `boundary_values_realistic`, `assertions_non_vacuous`, `known_bad_detected`. Detection method: original three independent in-memory mutants failed their specific producer-path assertions; final ten-test pass retains the one-word handler docstring known-bad and census polarity controls, and fresh finding-scoped reverification reports substantiate both repairs. Retrieval after-measurement and final docs/closure gates remain coordinator responsibilities; this report does not claim those pending results or authorize closure.
