# Focused Readiness Delta

Owner: Engineering
Status: active
Last verified: 2026-09-21

## Finding MODEL-READY-1

The plan's `_tier3_write`-only protection cannot satisfy AC-2. `render_agent_surfaces.render_agent_surfaces` invokes `reconcile_review_protocol_surfaces` before and after that writer. The reconciler accepts an existing Claude Guru wrapper with unclosed frontmatter, appends its protocol region, and reports the path written. Those appended bytes belong to the unclosed frontmatter and violate the promised byte preservation.

Independent current-source inspection used MCP `code_outline` and `code_read`. A local `python3 -B` probe imported the renderer, created a disposable root, wrote `.claude/agents/guru.md` with bytes `---\nname: guru\nmodel: sonnet\n# Missing closing delimiter\n`, and called `reconcile_review_protocol_surfaces(root)`. Assertions established both changed bytes and a returned written-list entry. Observed: `changed=True`, `reported_written=True`. This refutes the existing plan claim; it does not claim future implementation behavior.

Typed finding: `MODEL-READY-1`, required AC, admitted, actionable and blocking; source/blocking lane `code-reviewer`. Affected approvals: code, QA, docs-contract and council readiness. A bounded correction to fulfill the unchanged AC requires focused review, with no full-council boundary trigger.

## Review Allocation And Limits

Context: `model-policy-readiness-delta-20260921`. Requested model/effort: available host defaults, retained because this is a bounded code-grounded readiness judgment. Observed runtime identity: unknown. This context is independent of the repair owner. Subsequent code/QA/docs/council effects review will share this context; their conclusions are correlated and must not be represented as separate independent corroboration. No new broad council is being run. Fresh delivery review requires other contexts.

The probe exercised the existing reconciliation boundary in a temporary root, with public renderer call ordering verified from source. It did not exercise a live host, network, paid model or future implementation. The exact final public render route and negative controls remain delivery obligations.

## Focused Verification

Pending repaired packet publication. Review only the original finding, repair diff, affected AC-2/AC-3 and directly related unchanged contracts. Escalate any remaining blocker at the end of this round; no automatic further repair round.

### Repaired Packet Verdict

Focused verification approves receipt `review-policy-4926d35aeaa2d77e3233`. Reviewed exact original/current plan diff, Requirements 2 and 6, scope, AC-2/AC-3, and unchanged preservation/ownership boundaries. Replayed the malformed baseline and an adjacent valid-frontmatter reconciliation control: malformed bytes changed and were reported, while valid frontmatter remained intact. The original failure is therefore still a meaningful delivery control. The repaired plan now expressly protects the whole render, both reconciler passes, malformed Claude family wrappers, absent/stale protocol regions and Guru-unavailable rendering. No replacement readiness defect found.

- Code: feasible bounded extension of the existing writer/reconciler skip, without mandatory TOML machinery or a new YAML dependency.
- QA: whole-entry, repeated-render, absent/stale-region and Guru-unavailable obligations make the missing guard observable; existing valid overrides remain required controls.
- Docs-contract: byte preservation, warning, successful exit and written-list exclusion retain the existing obligation. Added wording resolves implementation coverage rather than changing acceptance meaning. Model/effort choice, provenance, permissions and ownership obligations remain intact.
- Council effects: focused correction satisfies an unchanged contract. No changed trust boundary, architecture, ownership, cross-component protocol, or readiness semantics requires a new broad council. All four role conclusions share the disclosed independent reviewer context and are correlated.

Falsification check: the strongest objection is that protecting only the template writer still loses bytes through reconciliation, particularly with Guru unavailable. The repaired packet names exactly those paths and requires absent/stale protocol fixtures, so that objection now challenges future implementation rather than the plan. Implementation correctness remains unproved until delivery.
