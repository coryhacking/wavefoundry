# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-26
review-evidence-source: events.jsonl

wave-id: `1tj0l cwd-independent-host-surface-launchers`
Title: Cwd Independent Host Surface Launchers

## Objective

Make every supported native or opt-in host launcher use the project identity selected by its owning
host configuration, without embedding machine paths, switching to a nested installation, or inventing
unsupported host capabilities. Move Codex MCP registration into the renderer that owns host wiring,
repair the phantom MCP `kwargs` contract, and install the same-readiness review/repair loop needed to
verify these plan repairs before implementation.

## Changes

Change ID: `1tjjj-bug reconcile-agent-and-platform-surface-ownership`
Change Status: `implemented`

Change ID: `1tjjk-bug cwd-independent-hook-launcher-commands`
Change Status: `implemented`

Change ID: `1tjjl-bug cwd-independent-mcp-server-stanzas`
Change Status: `implemented`

Change ID: `1tmaz-bug kwargs-published-as-required-mcp-parameter`
Change Status: `implemented`

Change ID: `1tmb0-bug review-loop-has-no-readiness-clearing-path`
Change Status: `implemented`

Completed At: 2026-07-26

## Wave Summary

Wave `1tj0l` (Cwd Independent Host Surface Launchers) delivered 5 changes: Reconcile Agent And Platform Surface Ownership, Cwd Independent Hook Launcher Commands, Cwd Independent Mcp Server Stanzas, Kwargs Published As Required Mcp Parameter, and Readiness Findings Need A Same-Phase Clearing Path. Notable adjustments during implementation: Reconcile Agent And Platform Surface Ownership: Pre-implementation review revisions: cohesive helper-family move and bounded `--platform codex` semantics added; Reconcile Agent And Platform Surface Ownership: **Mechanism replaced.** The `detect_platforms` design was falsified by execution: in a Guru-absent repo nothing under `.codex/` is created, so detection never fires and the defect survives; in a Guru-present repo the entrypoint loop precedes the agent renderer, so registration would land one render late. Rewritten to render unconditionally from the common section. Marker-map split, provenance/byte-identity conflict, and seed/doc scope added.; Cwd Independent Hook Launcher Commands: Pre-implementation review revisions: bootstrap execution boundary, descendant-cwd contract, verified host-signal matrix, and nested-project ownership added.

**Changes delivered:**

- **Reconcile Agent And Platform Surface Ownership** (`1tjjj-bug reconcile-agent-and-platform-surface-ownership`) — 10 ACs completed. Key decisions: Move Codex MCP registration to the platform renderer rather than removing the Guru gate; **Supersedes the routing half of the row above.** Render Codex MCP config unconditionally from the platform renderer's common section, NOT through `detect_platforms` and the per-platform dispatch.
- **Cwd Independent Hook Launcher Commands** (`1tjjk-bug cwd-independent-hook-launcher-commands`) — 12 ACs completed. Key decisions: Use per-host adapters instead of one `python3 -c` resolver; Render Codex hooks in `.codex/hooks.json`, separate from `.codex/config.toml`
- **Cwd Independent Mcp Server Stanzas** (`1tjjl-bug cwd-independent-mcp-server-stanzas`) — 9 ACs completed. Key decisions: Treat the MCP exposure as latent rather than a confirmed outage; Share root-selection semantics, not one serialized resolver, between hooks and MCP stanzas
- **Kwargs Published As Required Mcp Parameter** (`1tmaz-bug kwargs-published-as-required-mcp-parameter`) — 9 ACs completed. Key decisions: Correct the published schema at registration rather than removing `**kwargs` from every tool signature.; Set `extra="forbid"` alongside the default, rather than accepting the permissiveness the fix would otherwise introduce.
- **Readiness Findings Need A Same-Phase Clearing Path** (`1tmb0-bug review-loop-has-no-readiness-clearing-path`) — 7 ACs completed. Key decisions: Permit existing repair kinds to terminalize readiness-born findings before implementation.; Current unresolved finding heads withhold approval even when an approval record is newer; terminal repairs stale only approvals that predate the repair.
## Watchpoints

- Blocking sequence: `1tmb0` review-loop grammar, `1tjjj` ownership, `1tjjk` host hook adapters, then
  `1tjjl` MCP consumers; `1tmaz` is serialized independently around the shared registry surface.
- Prefer each host's native owner-root/cwd/argv fields; do not introduce one shared inline resolver,
  nearest-installation walk, or user-home launcher merely to make unlike host schemas look uniform.
- Codex and Junie have MCP surfaces but no verified native hook contract in this wave; Air and Warp
  are delegated hosts. None may receive an invented native hook file.
- Platform evidence is tiered honestly: executed where a runner exists (macOS). Native Windows, WSL2,
  and Linux remain `not_executed`; their owner is the release operator and their mechanism is the next
  **Package Wavefoundry** downstream verification pass: install the built archive in each real target
  environment, execute the host/platform matrix from root, descendant cwd, and a path containing
  spaces (plus both WSL2 checkout locations), and record the results in the package/downstream report
  before claiming those platforms passed. A patched platform value, a container, or an ordinary Linux
  runner may never be recorded as a pass, and never stands in for WSL2. A *failed* cell blocks delivery.
- Native-Windows runtime evidence is deferred, so the Windows code path is validated instead by an
  independent reviewer with no implementation context (`1tjjk` AC-15). That is code validation, not
  execution, and is never counted as a platform pass.
- All distributed launchers, hook bodies, and host configs are Git-tracked and platform-neutral: one
  canonical artifact per host, with official OS overrides inside that artifact rather than separate
  per-platform files or a user-home locator.
- Do not equate parsed-command subprocess success with an MCP client's acceptance of its config.
- **Seeds are in scope and ship to every target repository.** `seeds/011:52` is an install-time
  acceptance gate for an artifact `1tjjl` stops emitting; `seeds/050` hardcodes the broken hook literal
  four times and carries the host capability matrix that `1tjjk` reconciles while preserving Codex and
  Junie as instruction-only for hooks. Seed edits need
  `seed_edit_allowed`, opened and closed around each seed task. Seed `050` is owned **wholly** by
  `1tjjk` (it contains no MCP registration statement); seed `160` is touched by **three** changes
  (`:386` by `1tjjj`, `:472-477` by `1tjjl`, `:478` by `1tjjk`), so sequence those three rather than
  running them concurrently. `install-log.template.md` is outside `seeds/` and needs
  `framework_edit_allowed` instead.
- Correctness must never depend on `detect_platforms`. Codex MCP registration renders unconditionally
  from the platform renderer's common section; detection is discoverability only, and `1tjjj` AC-6 is
  the standing proof that removing it does not break the fix.
- `1tmaz`'s fix point is `fn_metadata.arg_model`, not the published schema dict. Dispatch validates
  the model; correcting only `tool.parameters` was falsified by execution. Compatibility accepts only
  legacy `kwargs: {}`; populated nested payloads must reach the typed unknown-argument envelope.
- The manual MCP entry for instruction-only hosts stays absolute by design. Do not "reconcile" it with
  the repo-relative rendered form; they answer different questions and the split is recorded.
- Keep `.air/mcp.json` in the committed runtime-entry census without adding an unsupported Air renderer.

## Implementation Checkpoint

The five changes are implemented. The launcher design remains intentionally host-specific and small:
verified configuration-owner signals are used where they exist, and hosts without one retain an
explicit root-only or delegated contract. No shared root locator, user-home launcher, Codex hook
surface, or Junie native-hook surface was added. Install and upgrade tests exercise fresh non-Git
targets and one-pass replacement of stale generated host configurations.

The readiness-loop implementation fixes the misleading approval state without retroactive approval.
The eleven readiness findings now have terminal independent reverification in `events.jsonl`. A fresh
delivery council subsequently found four additional contract/diagnostic defects; their repairs and
independent reverification are recorded in the same append-only ledger.

Final implementation verification: the canonical runner completed **6,242 tests across 59 files,
all green**; docs lint and `git diff --check` are clean. Fresh install, one-pass upgrade, non-Git,
nested-project, public-render, MCP hot-reload, and closed-ledger compatibility paths are included.

## Finding Synthesis

<!-- wave:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| air-mcp-config-omitted-from-surface-census | do_now | no | completed | wave-council-readiness |
| codex-platform-only-criterion-conflicts-with-orchestrator | do_now | no | completed | wave-council-readiness |
| copilot-windows-override-schema-is-misnamed | do_now | no | completed | wave-council-readiness |
| deferred-platform-owner-mechanism-unnamed | do_now | no | completed | wave-council-delivery |
| descendant-locator-can-switch-project-identity | do_now | no | completed | wave-council-readiness |
| hook-root-contract-is-contradictory | do_now | no | completed | wave-council-readiness |
| host-config-tests-do-not-validate-host-consumption | do_now | no | completed | wave-council-readiness |
| launcher-missing-owner-raw-keyerror | do_now | no | completed | wave-council-delivery |
| legacy-kwargs-payload-remains-silently-accepted | do_now | no | completed | wave-council-readiness |
| live-hook-contract-claims-unsupported-codex-junie | do_now | no | completed | wave-council-delivery |
| mcp-launcher-lacks-project-identity | do_now | no | completed | wave-council-readiness |
| native-windows-c3-contradiction | do_now | no | completed | wave-council-delivery |
| platform-deferral-not-applied-to-tasks-and-aeg | do_now | no | completed | wave-council-readiness |
| platform-evidence-contract-still-contradictory | do_now | no | completed | wave-council-readiness |
| readiness-repairs-have-no-same-phase-terminal-state | do_now | no | completed | wave-council-readiness |

*Machine review evidence — 155 records; 46 runs; 15 findings; current: do_now 15, maybe_later 0, dont_do_later 0, not_issue 0*
<!-- wave:finding-synthesis end -->

## Review Evidence

<!-- wave:review-status begin -->
| Signoff | State | Why | Next action |
| --- | --- | --- | --- |
| wave-council-readiness | approved | current executed approval follows every affected repair | none |
| wave-council-delivery | approved | current executed approval follows every affected repair | none |
| operator-signoff | approved | current executed approval follows every affected repair | none |
<!-- wave:review-status end -->

- operator-signoff: <approved when operator confirms closure>

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-26: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: two of four plans specified a fix mechanism that provably did not produce the fix, both falsified by execution rather than argument, and `1tmaz`'s stated justification described behavior that never fires on the dispatch path; strongest-alternative: render the Codex config unconditionally from the platform renderer's common section rather than via `detect_platforms`, and retarget `1tmaz` at `fn_metadata.arg_model` rather than the published schema dict, both adopted and re-verified by execution)

**Round 1 verdict was FAIL** on the two mechanism falsifications below. Both plans were reworked to
the seats' alternatives, and both seats re-verified by execution across three further rounds. Fifteen
findings were raised and closed; the record of the FAIL and its evidence is retained below rather than
rewritten, because the mechanisms it killed are the ones a future reader is most likely to reinvent.

Seat evidence (round 1, retained):

- **red-team: FAIL.** Executed proofs. `1tjjj`: rendering against a Guru-absent temp repo creates nothing under `.codex/`, so `detect_platforms` (which keys on `.codex/` existing) never returns `codex` and registration is still never written; the relocation does not repair the defect. `1tmaz`: applying the plan's own scoped fix to a live tool object and re-running real dispatch still raises `kwargs | Field required`, because dispatch validates `fn_metadata.arg_model`, not `tool.parameters`. Also blocking: `1tmaz` Requirement 4 / AC-4 / Decision Log describe an `unknown_arguments` envelope that never fires through dispatch (three argument shapes executed). Moderate: `_LEGACY_OWNED_MARKERS` is shared with five markdown surfaces, so the "cohesive unit" move is wrong about the tree; byte-identity conflicts with correcting the generated-by marker; no contingency for a negative Claude anchor probe; `1tjjl` omits `NoPathedLauncherScanTests` from its census. `1tjjk` and `1tjjl` passed this seat's factual standard.
- **docs-contract-reviewer: FAIL.** `1tjjl` AC-7 is unsatisfiable as written and satisfying it literally would regress the contract it protects: there is no renderer output for instruction-only hosts, and the manual absolute form differs from the rendered relative form by design (`docs/references/native-windows-support.md` records the split). Blocking: the seed layer goes stale and no plan names it, including an install-time acceptance gate in `seeds/011` and hardcoded hook literals plus a contradicted host classification in `seeds/050`. Also: ADR `1p7pb-adr` states the launcher mechanism this wave retires; `1tjjk`'s census omits Antigravity; a second copy-ready MCP block exists in the install prompt.

Final round (both seats PASS):

- **red-team: PASS.** Executed the reworked `1tjjj` mechanism (real `main()` in a Guru-absent,
  `.codex`-absent repo under `--platform claude`; common section ran, manifest collected, every
  production entry point reaches it) and the reworked `1tmaz` fix point (arg-model default plus
  `model_rebuild`, across all 83 tools, with the call matrix passing). Three conditions raised and
  applied: `.codex` preflight belongs in the unconditional block, not `_PLATFORM_WRITE_ROOTS`, or the
  change reduces symlink-escape containment coverage for a path it newly writes; AC-5's reload test
  passes vacuously unless routed through `_refresh_mcp_tool_surface` with a negative control; and
  AC-4's "document the unreachable shape" clause would have permitted recording a regression this
  change introduces as pre-existing behavior. Separately executed the `extra="forbid"` safety
  question and the `extra="allow"` alternative, retracting its own earlier hypothesis: the
  alternative reaches the typed envelope for all three shapes but **breaks AC-3**, so `forbid` stands.
- **docs-contract-reviewer: PASS.** Verified every doc, seed, pack template, ADR and enumeration is
  owned by exactly one change with the correct gate. Deleted one phantom target (`1tjjj`'s seed `050`
  share, censused to nothing: `050` is a hook capability matrix with no MCP column). Added the
  normative rule `050:256` behind the literals, `160:478`, and `install-log.template.md:31`, a shipped
  install acceptance artifact that had independently drifted from its seed twin. **Retracted its own
  P3 classification** of `012:139` after re-checking in code, escalating it to a blocking-class
  install gate: it states "Two hooks wired" against three rendered Claude hooks today, and up to six
  host configs after this change.

Determination carried to implementation (red-team, verified by reading `upgrade_wavefoundry.py`): **the old-code window does NOT apply to upgrade Phase 1.** Phase 0b extracts the pack into `root` before Phase 1, and `phase_surface_rendering` spawns `render_platform_surfaces.py` as a subprocess resolved from the just-overwritten scripts directory, so the renderer runs new code. This answers the question `1tjjj` AC-7, `1tjjk` AC-14 and `1tjjl` AC-11 each defer. Hand it to implementation rather than re-deriving it.

## Dependencies

- No external wave depI endencies.

<!-- wave:context-efficiency begin -->
## Context Efficiency

Estimated token savings use phase-unique returned source versions and mapped workflow prompts, minus recorded request and response tokens. Saved model output or avoided tool loops count only through quality-equivalent paired evidence.

| Stage | Tool calls | Estimated token savings |
| --- | ---: | ---: |
| plan | 97 | 2,724,214 |
| implement | 72 | 1,689,703 |
| review | 189 | 4,220,792 |
| **Total** | **358** | **8,634,709** |

<!-- wave:context-efficiency-state {"generation":358,"measurement_status":"healthy","pending":false,"schema_version":1,"stages":{"implement":{"calls":72,"content_source_credit":1812529,"derived_artifact_credit":1207,"direct_net":1689703,"estimated_tokens_saved":1689703,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":2429,"response_debit":123177,"source_credit_count":33,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1573},"plan":{"calls":97,"content_source_credit":2879439,"derived_artifact_credit":2226,"direct_net":2724214,"estimated_tokens_saved":2724214,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":35234,"response_debit":127482,"source_credit_count":85,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":5265},"review":{"calls":189,"content_source_credit":4666637,"derived_artifact_credit":1635,"direct_net":4220792,"estimated_tokens_saved":4220792,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":36100,"response_debit":412592,"source_credit_count":170,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":1212}},"store_instance_id":"f294635fbf24489a9a50af63451b2532","totals":{"calls":358,"content_source_credit":9358605,"derived_artifact_credit":5068,"direct_net":8634709,"estimated_tokens_saved":8634709,"matched_pair_residual":0,"paired_evaluation_count":0,"request_debit":73763,"response_debit":663251,"source_credit_count":288,"source_credit_drop_count":0,"structural_source_credit":0,"workflow_prompt_credit":8050},"wave_id":"1tj0l cwd-independent-host-surface-launchers"} -->
<!-- wave:context-efficiency end -->

## Estimated Exploration Avoided

<!-- wave:exploration-avoided begin -->

This is a bounded estimate from exact-match memory advisories. It is not added to measured Context Efficiency.

| Advisory surfaces | Citations | Records credited | Estimated tokens avoided |
| ---: | ---: | ---: | ---: |
| 2 | 0 | 1 | 1048594 |

estimated: a surfaced (or cited) advisory does not prove a re-exploration was avoided; this is grounded in the measured cost of the original exploration, scaled by a bounded exact-match attribution, and is NEVER summed into the measured Context Efficiency token total.

<!-- wave:exploration-avoided-state {"cited_events":0,"credited_records":1,"estimated_exploration_avoided":1048594,"surfaced_events":2} -->
<!-- wave:exploration-avoided end -->
