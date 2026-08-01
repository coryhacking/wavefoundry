# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-31
review-evidence-source: events.jsonl

review-policy-reprepare-required: false
wave-id: `1u2b0 host-surface-hardening`
Title: Host Surface Hardening

## Objective

Make the Claude Code host surface self-healing and honest: `wf_server_info` gains a runner
staleness signal that can actually fire (the frozen `server_runner_version` constant is replaced by
capture-at-launch identity over the un-reloadable runner set), and wavefoundry permission allow
rules become a roster-derived, provenance-tracked block in the committed `.claude/settings.json`
that self-heals on upgrade without creating any agent-driven permission-escalation channel. Both
address friction observed across three target-repo 1.15.0 field upgrades on 2026-07-31.

## Changes

Change ID: `1u2ay-bug server-runner-version-never-distinguishes-stale-runner`
Change Status: `implemented`

Change ID: `1u2az-enh rendered-mcp-permission-allowlist`
Change Status: `implemented`

## Participants

- Coordinator: implementing agent session (single-implementer wave)
- Write-owning roles: implementer (framework scripts, seeds under gate)
- Requested review lanes: none
- Required review lanes: code-reviewer, qa-reviewer, architecture-reviewer, docs-contract-reviewer, release-reviewer

Completed At: 2026-07-31

## Wave Summary

Wave `1u2b0` (Host Surface Hardening) delivered two changes: server_runner_version Cannot Distinguish a Stale Runner From a Current One and Renderer-Owned MCP Permission Allowlist for Claude Code Surfaces. Notable adjustments during implementation: server_runner_version Cannot Distinguish a Stale Runner From a Current One: Implemented capture-at-launch runner identity (Design Option 1): `server.py` captures `SERVER_RUNNER_FILES` (unresolved launch paths of `server.py` + `venv_bootstrap.py`) and derives `SERVER_RUNNER_VERSION` from `server_impl.compute_runner_identity` (first 12 sha256 hex over both files' bytes in fixed order); `set_server_runner_version` extended with `runner_files`; `version_payload` reports `server_runner_version` (launch), `runner_disk_identity`, tri-state `runner_stale`, and `runner_stale_detail` + a `runner_stale` diagnostic on stale; frozen `server_impl` alias removed; `server_identity` now always emits the version block so a standalone impl reports explicit nulls; server_runner_version Cannot Distinguish a Stale Runner From a Current One: Docs companions: `wf_server_info` Tool Detail entry added to `docs/specs/mcp-tool-surface.md` (Framework Operations) with tri-state semantics; seed-160 restart-exception paragraph now names both runner files and the `runner_stale` check (edited under `seed_edit_allowed` gate, closed immediately after); rendered `docs/prompts/upgrade-wavefoundry.prompt.md` reconciled (step 5 tool list + step 6 reload wording); docs-lint ok via `wf_validate_docs`; server_runner_version Cannot Distinguish a Stale Runner From a Current One: Delivery-review docs repair pass (docs P3s + finding F10): the `wf_server_info` spec entry now states the REAL path-resolution guarantee instead of a flat symlink-swap-detection claim (only `server.py`'s launch path is stored unresolved; the `venv_bootstrap` path comes back directory-resolved through the resolved `sys.path` entry, so a swap that leaves either recorded path unreadable degrades `runner_stale` to `null`, not `true`, and after an upgrade `null` carries the same action as `true`), and documents the `"unavailable"` launch sentinel a torn mid-upgrade tree injects so a reader can explain an observed value. Front-matter `Status` aligned to `implemented` (it read `active` against `Change Status: implemented`). CHANGELOG `[1.15.0]` **Fixed** bullet added for the tri-state runner-staleness field.

**Changes delivered:**

- **server_runner_version Cannot Distinguish a Stale Runner From a Current One** (`1u2ay-bug server-runner-version-never-distinguishes-stale-runner`) — 5 ACs completed. Key decisions: Filed from field observation; Hash the un-reloadable runner SET, tri-state staleness, null-safe reads
- **Renderer-Owned MCP Permission Allowlist for Claude Code Surfaces** (`1u2az-enh rendered-mcp-permission-allowlist`) — 5 ACs completed. Key decisions: Derive from a new roster module; tier writes as operator-gated opt-in; Permissions rendering only on the upgrade/install path; agent-reachable renders never touch permissions
## Watchpoints

- Blocking guard: permissions rendering must stay unreachable from `wf_sync_surfaces` (pinned by
  test), and the mutating tier must stay behind the operator knob. Delivery review scoped the
  broader claim: the boundary is **operator-approved plus host-enforced, not structural
  agent-unreachability**. `wf_upgrade` is an agent-callable tool whose first phase renders, bounded
  to the read tier because the write tier needs the knob and `wf_upgrade` is itself write-tier; the
  renderer switch reachable through the `wf` dispatcher is an accepted residual outside the threat
  model; and the knob's home is operator territory by host enforcement plus prompt policy, since the
  framework's own guard there (`framework_edit_allowed`) is agent-openable. The council P1 stands as
  the tested `wf_sync_surfaces` negative plus a default-off switch; every shipped surface must state
  the residuals rather than claim more.
- Watchpoint: ownership of rendered allow rules is provenance-tracked, never inferred from the
  `mcp__wavefoundry__` name prefix; operator-authored wavefoundry-named rules must survive renders.
- Watchpoint: the runner identity covers `server.py` AND `venv_bootstrap.py`; comparison reads are
  tri-state and never raise (`wf_server_info` is used mid-upgrade).
- Watchpoint: `reconcile_scan.py` is a fragile file (two 1tz6l channel-boundary repairs); rerun its
  near-miss controls with the channel split.
- Sequencing: security-control faithfulness review applies before close (permission-posture and
  detection-adjacent changes).

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-31: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: as first drafted, the allowlist feature was itself an agent-driven permission-escalation channel — an agent could flip a tier knob and call wf_sync_surfaces to self-grant allow rules for operator-consent tools, inverting the repo's own agents-never-self-edit-allow-rules doctrine — resolved structurally in-plan by gating permissions rendering to the upgrade/install path, placing the mutating-tier knob in operator-owned space, and pinning the agent-path negative with a test; strongest-alternative: expose the roster-derived allowlist as an operator-applied artifact instead of rendering into the committed file — retained in the Decision Log as the documented fallback if Prepare finds tier-1 consent insufficient, with rendering kept as default because self-heal-on-upgrade is the point and the consent tradeoff is mitigated by the explicit upgrade diff line. Both seats verified claims code-grounded: the frozen runner constant, reload mechanics, and test pins for 1u2ay (hash-at-launch confirmed feasible; runner set extended to venv_bootstrap.py; readOnlyHint disproven as tier datum; the cited GRAPH_BUILDER_VERSION guard-test prior art disproven); the renderer/scan/host-permission contracts for 1u2az (managed-region framing replaced by provenance set-merge; rename attribution corrected to 1.14.0; docs companions consolidated into scope: seed-050, seed-160, mcp-tool-surface.md:858, platform-mapping.md).)

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| ac3-overclaims-agent-reachable-render-paths | do_now | no | completed | architecture-reviewer, qa-reviewer, code-reviewer, release-reviewer, wave-council-delivery |
| changelog-bullets-missing | do_now | no | completed | release-reviewer, docs-contract-reviewer, wave-council-delivery |
| first-render-delay-undisclosed | do_now | no | completed | release-reviewer, docs-contract-reviewer, wave-council-delivery |
| knob-operator-space-is-host-guarantee-not-framework | do_now | no | completed | architecture-reviewer, wave-council-delivery |
| permissions-backstop-unreachable-on-default-upgrade-path | do_now | no | completed | release-reviewer, wave-council-delivery |
| permissions-consent-delta-dropped-on-write-tier | do_now | no | completed | release-reviewer, wave-council-delivery |
| preexisting-rules-never-adopted-defeats-motivating-case | do_now | no | completed | architecture-reviewer, wave-council-delivery |
| provenance-channel-misroutes-non-allow-hits | do_now | no | completed | qa-reviewer, code-reviewer, architecture-reviewer, release-reviewer, wave-council-delivery |
| provenance-span-matches-any-allow-array | do_now | no | completed | qa-reviewer, wave-council-delivery |
| renderer-docstring-retains-structural-overclaim | do_now | no | completed | docs-contract-reviewer, wave-council-delivery |
| runner-identity-helper-guards-only-typeerror | do_now | no | completed | code-reviewer, wave-council-delivery |
| runner-setter-kwarg-crashes-torn-tree | do_now | no | completed | code-reviewer, release-reviewer, wave-council-delivery |
| seed-050-documents-nonworking-drop-procedure | do_now | no | completed | — |
| stale-single-channel-contract-in-rendered-prompt | do_now | no | completed | — |

*Machine review evidence — 228 records; 64 runs; 14 findings; current: do_now 14, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| code-reviewer | approved | current executed approval follows every affected repair | none |
| qa-reviewer | approved | current executed approval follows every affected repair | none |
| architecture-reviewer | approved | current executed approval follows every affected repair | none |
| docs-contract-reviewer | approved | current executed approval follows every affected repair | none |
| release-reviewer | approved | current executed approval follows every affected repair | none |
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
| plan | 47 | 1,990,051 |
| implement | 29 | 1,066,012 |
| review | 213 | 6,925,129 |
| **Total** | **289** | **9,981,192** |

<!-- wave:context-efficiency-state {"generation":304,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":29,"content_source_credit":1103850,"derived_artifact_credit":143,"direct_net":1066012,"estimated_tokens_saved":1066012,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2089,"response_debit":37323,"source_credit_count":22,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1431},"plan":{"calls":47,"content_source_credit":2091235,"derived_artifact_credit":1703,"direct_net":1990051,"estimated_tokens_saved":1990051,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":6223,"response_debit":100029,"source_credit_count":103,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":3365},"review":{"calls":213,"content_source_credit":7592323,"derived_artifact_credit":4243,"direct_net":6925129,"estimated_tokens_saved":6925129,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":131807,"response_debit":540976,"source_credit_count":204,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1346}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":289,"content_source_credit":10787408,"derived_artifact_credit":6089,"direct_net":9981192,"estimated_tokens_saved":9981192,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":140119,"response_debit":678328,"source_credit_count":329,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":6142},"wave_id":"1u2b0 host-surface-hardening"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 25 | 0 | 11 | 10266184 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":11,"estimated_exploration_avoided":10266184,"surfaced_events":25} -->
<!-- wave:exploration-avoided end -->
