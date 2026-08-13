# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-08-13
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1v7a3 mcp-stanza-without-inline-exec`
Title: Mcp Stanza Without Inline Exec

## Objective

Stop shipping a code-execution surface in a Git-tracked config. The Claude MCP registration is the only rendered stanza that carries an inline Python program instead of naming the server file, an enterprise deployment's security tooling flags it, and the exposure it was introduced to close was documented as latent and never reproduced.

## Changes

Change ID: `1v7a2-bug claude-mcp-stanza-embeds-inline-python-exec`
Change Status: `implemented`

## Participants

- Coordinator: Engineering
- Write-owning roles: implementer (renderer, rendered config), qa (stanza shape and root-resolution assertions)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer

Completed At: 2026-08-13

## Wave Summary

Wave `1v7a3` (Mcp Stanza Without Inline Exec) delivered one change: Claude MCP Stanza Embeds Inline Python Exec. Notable adjustments during implementation: Claude MCP Stanza Embeds Inline Python Exec: Reverted `render_claude_mcp_json` to the repo-relative path and re-rendered this repository's `.mcp.json`. AC-5 verified on the real artifact: the existing inline stanza was REPLACED, not merged alongside, and a foreign `my-other-server` entry in the same file survives untouched.; Claude MCP Stanza Embeds Inline Python Exec: **The suite proved the exposure was not purely hypothetical, which the plan understated.** `1tjjl-bug` shipped an EXECUTED test, `test_claude_mcp_stanza_runs_owner_server_from_nested_cwd`, that spawned the stanza from a nested cwd and asserted success. The revert breaks it by design. It was NOT deleted: it is replaced by two tests that pin the new contract honestly, one asserting the supported repository-root launch works, and one asserting a nested cwd fails LOUDLY with a missing file. The second matters more than the first: it proves the failure happens before the server starts, so `_discover_root` never runs and the dangerous outcome (starting successfully against the WRONG repository) is impossible. A future change that made the nested path start successfully would now be caught.; Claude MCP Stanza Embeds Inline Python Exec: Discharged the council's docs obligation. One seed described the retired shape: `seeds/011-install-wavefoundry-phase-1.prompt.md` told installers to expect a stanza that "resolves `server.py` from Claude's `CLAUDE_PROJECT_DIR`". Corrected under the `seed_edit_allowed` gate to describe a path argument, to state that no `--root` or project anchor belongs in the stanza, and to name hooks as the separate case that does need the variable. `AGENTS.md`'s copy-ready entry is for instruction-only hosts where an operator types an absolute path by hand; it is a different contract and out of scope.

**Changes delivered:**

- **Claude MCP Stanza Embeds Inline Python Exec** (`1v7a2-bug claude-mcp-stanza-embeds-inline-python-exec`) — 6 ACs completed. Key decisions: Revert the Claude stanza to the repo-relative path, re-accepting the cwd-dependence that `1tjjl-bug` closed.; Leave hook launchers alone.
## Watchpoints

- **Watchpoint:** hooks are NOT in scope and must not be touched. They need `CLAUDE_PROJECT_DIR`, `1tjjk-bug` proved that with a REPRODUCED failure, and this wave's whole argument is that the MCP case differs because its motivating exposure was only latent. Weakening hooks here would invert the reasoning.
- **Watchpoint:** no machine-absolute path. `1tjjl-bug` Requirement 2 still binds: every distributed MCP registration is Git-tracked and must stay portable. An absolute path would be a worse regression than the inline program.
- **Watchpoint:** do not add a `cwd` field to the Claude stanza as a way to keep cwd independence without inline code. `1tjjk-bug`'s Decision Log records the framework getting burned assuming Claude host-substitution behaviour without an executed probe. If cwd independence is wanted back, it needs a probe and its own change.
- **This wave re-accepts a known tradeoff deliberately.** The cwd-dependence `1tjjl-bug` closed comes back for Claude. It is stated in the change doc's Risks rather than hidden, it fails loudly at startup rather than mis-rooting, and Antigravity and Codex already carry it.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| hook-launchers-still-carry-inline-exec | do_now | no | completed | — |

*Machine review state — 1 findings; current: do_now 1, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-08-13: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: this wave REVERSES a decision the framework made deliberately eleven waves ago, so the bar is not "the operator asked" but "the original reasoning does not survive contact with the new evidence"; it does not: `1tjjl-bug` states in its own Rationale that the exposure it closed was latent and never reproduced, while the cost it introduced is active, reported from a real enterprise deployment, and lands in a Git-tracked file, so an unobserved risk was being paid for with a shipped code-execution surface; strongest-alternative: keep the inline form and pursue a security exception downstream, rejected because that imposes a recurring per-consumer cost to preserve a guarantee three of the five rendered hosts never had)

Seat evidence:

- **red-team** — verified code-grounded, and the operator's premise holds in a stronger form than stated. `server_impl._discover_root` ranks candidates explicitly and puts **the script's own install location at priority 2, above every environment variable**: `server_impl.py` always sits at `<root>/.wavefoundry/framework/scripts/`, so `parents[3]` is the served repository, and `CLAUDE_PROJECT_DIR` is only priority 3. Its docstring states the consequence outright: "Authoritative for the MCP server and independent of the host's cwd, so the committed config needs no `--root .`". The inline wrapper therefore never supplied the root; it only helped the interpreter locate `server.py`. Confirmed Claude is the sole outlier by reading all five rendered configs: Cursor pins a native `cwd`, Junie is config-relative by host contract, and Antigravity and Codex ship the same bare relative path this change restores. Confirmed the revert's residual risk fails LOUDLY rather than silently: if a client ever spawns from another cwd the interpreter cannot open the file, so `_discover_root` never runs and no mis-rooting is possible. One caution recorded rather than raised as a finding: four test assertions reference `CLAUDE_PROJECT_DIR` and two of them are HOOK launcher assertions at `test_render_platform_surfaces.py` lines 232 and 245; those must survive untouched, and AC-4 exists to enforce that.
- **docs-contract-reviewer** — no blocking finding, one delivery obligation. The renderer's own docstring currently explains the inline launcher ("Claude supplies `CLAUDE_PROJECT_DIR` ... so the inline launcher resolves that project's server"), and `AGENTS.md` carries an MCP registration table plus a copy-ready stdio entry for instruction-only hosts. Both describe launcher shape, so both must be checked at delivery rather than left asserting a shape the code no longer emits; the change doc's task list already carries that. Recorded because the sibling wave `1v4mw` shipped a gate for exactly this failure class, and it would be poor form to leave rendered documentation drifting in the same session that hardened it.

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 7 | 2,118 |
| implement | 5 | 0 |
| review | 14 | 29,817 |
| **Total** | **26** | **31,935** |

<!-- wave:context-efficiency-state {"generation":26,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":5,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":-263,"estimated_tokens_saved":0,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":35,"response_debit":228,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":0},"plan":{"calls":7,"content_source_credit":5467,"derived_artifact_credit":1227,"direct_net":2118,"estimated_tokens_saved":2118,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":936,"response_debit":7146,"source_credit_count":4,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3506},"review":{"calls":14,"content_source_credit":58999,"derived_artifact_credit":1076,"direct_net":29817,"estimated_tokens_saved":29817,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":8737,"response_debit":22867,"source_credit_count":16,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":26,"content_source_credit":64466,"derived_artifact_credit":2303,"direct_net":31672,"estimated_tokens_saved":31935,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":9708,"response_debit":30241,"source_credit_count":20,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":4852},"wave_id":"1v7a3 mcp-stanza-without-inline-exec"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
