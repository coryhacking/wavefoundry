# Extension Prefix and Inert Config Readiness Review

Owner: Engineering
Status: active
Last verified: 2026-09-25

## Red-team primer (standard depth)

Independent read-only context `pfx_primer`, receipt `review-policy-6400dcdeadc4761e2a97`. No blocking findings.

- **Strongest challenge:** with the prefix rule gone, the only guard against an extension inheriting core-only behavior by name is the served-table same-name refusal. Probes (scratch copy, this repo and an empty root) show all 90 registered tools match `TOOL_TIERS`, and the lifecycle-lock, cost-exempt and cost-extractor sets and the publication registry name no unregistered tool, so nothing is inheritable today. The latent gap: a later core change adding a name to one of those sets without registering it would silently grant it to a fork tool of that name.
- **Best alternative (adopted as 1yxl8 Requirement 5 / AC-4):** refuse new extension tool names that appear in any core name-keyed set; not an opt-in or preflight check, so consistent with the operator decision.
- **Primer questions answered in the plan:** new positive `wf_` fixture instead of converting the overlap fixtures, whose causes change; `core_prefix_tier` expectation updated or dropped; advisory routing for 1yygb through `_route_sensor_findings` with a warnings sink at both `cli.py` sites; `cli.py`, `wave_validators.py`, `server_impl.py` added to serialization points; `wf_help` prefix grouping noted in the spec.
- Verified non-blocking facts: no production code reads `wave_implement.wave_root` or a `record_layout` block; removing the key does not rotate the review-policy receipt.

## Focused verification round 1

Receipt `review-policy-4af60904942a51c8e4cd`. Code, QA and security (context `pfx_code_qa_sec`) approve with no blockers; notes: `_RENAMED_MCP_TOOLS` keys are retired names (known-bad `wf_review_evidence` would otherwise be rewritten by upgrade), extractor maps missing from the set list, registration-only check, fixture expectation updates, cycle-free lint routing keeping `check_workflow_config`'s signature, legacy `wave_execution.wave_root`. Docs-contract (context `pfx_docs`, rotating seat) blocks: DOCS-READY-1 set list needs a deriving rule and is incomplete; DOCS-READY-2 false `wf_help` grouping claim; DOCS-READY-3 1yygb contradicts ADR 1yb8v "no migration hint". Escalated to the operator, who chose one more bounded repair and focused verification by the blocking lane (2026-09-25). Repair applied: 1yxl8 Requirement 4 states the reserved-name rule with a census test and the derived collection list; Requirement 5 corrects `wf_help` and adds allowlist and override-resolution notes; 1yygb amends ADR 1yb8v, keeps the checker signature, warns on the legacy key.
