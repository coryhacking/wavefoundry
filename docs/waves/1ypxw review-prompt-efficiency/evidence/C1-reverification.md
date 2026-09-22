# C-1 independent focused delivery reverification

Owner: Engineering
Status: active
Last verified: 2026-09-22

Date: 2026-09-22
Actor: code-reviewer
Context: `/root/ypxw_c1_reverify` (fresh independent context; no implementation or prior review participation)
Verdict: repair verified. This is finding-scoped reverification, not a whole-wave approval.

All 46 paths in `delivery-tree-repaired.json` matched their SHA-256 fingerprints before and after this review. No reviewed source moved. MCP code_read established the digest algorithm, assertion and known-bad control; direct snapshot comparison and executable tests verified the repair.

The fixture differs from `/tmp/1ypxw-before` only in its description/provenance and the expected hashes for `wf_review_wave` and `wf_review_event`. The other 87 handler entries, schema and capture metadata remain unchanged. The repaired hashes independently match the current exact-source producer:

- wf_review_wave: `5967b107fe0d341985f83b50382f34fb858352a3f8f7abc089143f9af5575d25`
- wf_review_event: `761597d6e6614797f8899d991b0ab28715977e9a094f52c6693d36654da8c963`

After removing only leading docstrings, all 110 directly nested function ASTs in register_mcp_surface match the prewave snapshot, including both affected wrappers. This verifies unchanged executable wrapper structure; it does not claim descriptions are unchanged. The digest algorithm and test file are byte-identical to prewave. The tool-surface golden and both lifecycle goldens are byte-identical; the additionally checked graph parity golden is also unchanged.

Executed with `PYTHONPATH=.wavefoundry/framework/scripts/tests:.wavefoundry/framework/scripts /Users/coryhacking/.wavefoundry/venv/bin/python -B -m unittest`:

- `test_mcp_tool_registry.HandlerDigestTests`: 2 passed in 0.420 seconds.
- `test_mcp_tool_registry`: 27 passed in 3.382 seconds, including real FastMCP registry and reload subprocess paths.

Neither run had errors, failures or skips. In addition to the retained one-word control in HandlerDigestTests, an independent in-memory mutation inserted the single word MUTANT at the start of the wf_review_wave wrapper docstring. The unchanged digest producer differed from the repaired fixture only for wf_review_wave, while the unmutated producer matched all 89 entries. Known-bad result: killed. No repository source was mutated.

C-1 remains a real, admitted, wave-introduced blocking defect in historical judgment; repair is now complete and independently verified. Preserve its recorded facts: validation_status=real; scope_relation=admitted; introduced_or_worsened_by_wave=true; contract_relevance=required_ac; supported_reachability=true; attacker_reachability=false; authority_domain=none; authority_delta=none; observable_impact=material; containment=detect_only; fix_risk=lower; repair_scope_bounded=true; repair_safety=safe; benefit_vs_fix_risk=greater. The observation that changed is that the required exact-source fixture now matches the intentionally changed descriptions without weakening the oracle.

Integrity: test_ran_without_unintended_skip=true; public_path_reached=true; boundary_values_realistic=true; assertions_non_vacuous=true; known_bad_detected=true. Detection method: current exact-source producer compared against the migrated fixture, independent prewave AST/byte comparisons, real registry/reload tests, and a one-word mutation of the affected wrapper description rejected by the unchanged digest oracle.

Budget: four-minute focused review. No whole-suite, benchmark, broader prose audit, approval, ledger write, closure or commit performed.
