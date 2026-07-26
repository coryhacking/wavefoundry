# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-25
review-evidence-source: events.jsonl

wave-id: `1tj0l cwd-independent-host-surface-launchers`
Title: Cwd Independent Host Surface Launchers

## Objective

Make every supported native or opt-in host launcher reach its Python entrypoint after a host changes
into a repository subdirectory, without embedding machine paths or inventing unsupported host
configuration. Record delegated hosts explicitly. At the same time, move Codex MCP registration into
the renderer that owns host connection wiring.

## Changes

Change ID: `1tjjj-bug reconcile-agent-and-platform-surface-ownership`
Change Status: `planned`

Change ID: `1tjjk-bug cwd-independent-hook-launcher-commands`
Change Status: `planned`

Change ID: `1tjjl-bug cwd-independent-mcp-server-stanzas`
Change Status: `planned`

## Wave Summary

The wave first reconciles Codex renderer ownership, then introduces host-specific launcher adapters
for hook commands and MCP argument vectors. Hook coverage includes native Claude, Copilot, Cursor,
Windsurf, and Codex surfaces; an explicit opt-in Junie CLI surface; and honest delegated coverage for
Air and Warp. The supported contract is repository-root or descendant cwd plus verified host anchors;
unrelated cwd without an anchor fails clearly rather than guessing a project. Native Windows, WSL2,
macOS, and Linux are equal delivery gates, with WSL2 verified independently from Linux.

## Watchpoints

- Blocking sequence: `1tjjj` ownership, then `1tjjk` host hook adapters, then `1tjjl` MCP consumers.
- Prefer each host's native root/cwd/argv fields; do not introduce one shared inline resolver or a
  user-home launcher merely to make unlike host schemas look uniform.
- Codex is native but trust-gated; Junie is an explicit EAP CLI opt-in; Air and Warp are delegated
  hosts and must not receive invented native hook files.
- First-class platform support requires real native Windows, WSL2, macOS, and Linux execution. A
  patched platform value or ordinary Linux runner cannot stand in for WSL2.
- All distributed launchers, hook bodies, and host configs are Git-tracked and platform-neutral: one
  canonical artifact per host, with official OS overrides inside that artifact rather than separate
  per-platform files or a user-home locator.
- Do not equate parsed-command subprocess success with an MCP client's acceptance of its config.
- Keep `.air/mcp.json` in the committed runtime-entry census without adding an unsupported Air renderer.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| air-mcp-config-omitted-from-surface-census | do_now | yes | pending | wave-council-readiness |
| codex-platform-only-criterion-conflicts-with-orchestrator | do_now | yes | pending | wave-council-readiness |
| hook-root-contract-is-contradictory | do_now | yes | pending | wave-council-readiness |
| host-config-tests-do-not-validate-host-consumption | do_now | yes | pending | wave-council-readiness |
| mcp-launcher-lacks-project-identity | do_now | yes | pending | wave-council-readiness |

*Machine review evidence — 15 records; 5 runs; 5 findings; current: do_now 5, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | pending | no current executed approval | record approval evidence for wave-council-readiness |
| wave-council-delivery | pending | no current executed approval | record approval evidence for wave-council-delivery |
| operator-signoff | withheld | blocking findings: mcp-launcher-lacks-project-identity, hook-root-contract-is-contradictory, host-config-tests-do-not-validate-host-consumption, air-mcp-config-omitted-from-surface-census, codex-platform-only-criterion-conflicts-with-orchestrator; unresolved lanes: code-reviewer | record independent reverification for code-reviewer, then re-approve operator-signoff |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 1 | 981 |
| **Total** | **1** | **981** |

<!-- wave:context-efficiency-state {"generation":1,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"plan":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":981,"estimated_tokens_saved":981,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17,"response_debit":119,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1117}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":1,"content_source_credit":0,"derived_artifact_credit":0,"direct_net":981,"estimated_tokens_saved":981,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":17,"response_debit":119,"source_credit_count":0,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1117},"wave_id":"1tj0l cwd-independent-host-surface-launchers"} -->
<!-- wave:context-efficiency end -->

<!-- wave:exploration-avoided begin -->
<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":0,"estimated_exploration_avoided":0,"surfaced_events":0} -->
<!-- wave:exploration-avoided end -->
