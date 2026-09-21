# Model Policy Readiness Review

Owner: Engineering
Status: active
Last verified: 2026-09-17

Phase: readiness. Verdict: approved; no readiness blockers. Context: `model-policy-readiness-20260917`. Receipt: `review-policy-4b88764778aa4446a368`. This reviews the plan, not delivered behavior; implementation remains unauthorized in this session.

## Council

Standard primer ran first in the isolated council context, applying adversarial, constructive and simplicity stances. Its strongest challenge was silent loss of deliberate Sonnet, `inherit`, future values or malformed frontmatter when a template cleanup leaves the real writer destructive. Its questions were: what establishes ownership before removing a setting, and what actual render/upgrade test distinguishes prose cleanup from durable preservation?

The configured seats then ran in separate fresh contexts: `red-team` (`model_policy_readiness/red_seat`) and rotating `docs-contract-reviewer` (`model_policy_readiness/docs_contract`). Both independently approved. Each addressed both primer questions; the fixed seat subsequently weighed the rotating alternative. First synthesis weighed the two outputs as anonymous Seat 1 and Seat 2: both grounded approval in Requirements 2/6 and AC-2/3, with no dissent or blocking finding. Reattached roster: red-team and docs-contract-reviewer. Agreement: unanimous; maximum finding severity: none; no challenge round needed.

The strongest alternative is already the selected design: omit fresh defaults, preserve existing preferences conservatively, and resolve ambiguous ownership in the existing upgrade editing pass. A provenance database, model/provider matrix or role-tier policy adds complexity without establishing historical intent. The accepted tradeoff is that ambiguous old pins persist until explicitly reconciled.

Requirement 3 makes delegation-time selection primary using controls actually exposed by the host; Requirement 4 distinguishes requested settings from observed identity. The seats confirm that inheritance alone cannot prove a task-fit decision. Requested review settings were inherited host defaults under current host constraints, adequate for this bounded independent contract/risk review; actual runtime model and effort were unknown. No selection-quality or savings claim is made.

## Evidence

MCP `code_ask` was available but reported stale indexed evidence. Live `code_read` verified `render_agent_surfaces.CLAUDE_GURU_AGENT`, `render_agent_surfaces.render_agent_surfaces` and its nested `_tier3_write`, plus the call from `render_platform_surfaces.main`. These establish the current Sonnet default, unconditional Guru overwrite and actual surface-render route. Seed 050's Guru example agrees with the current default; seed 180 already contains task-fit guidance. No universal writer census is claimed.

The council executed the real `render_agent_surfaces.py --repo-root <temporary-directory>` CLI with `python3 -B`, three times on a temporary target containing `docs/agents/guru.md` and `.claude/agents/`. The cases were: absent wrapper; an existing wrapper with `model: inherit`, `effort: high` and `x-operator: keep`; and malformed frontmatter missing its closing delimiter with `model: sonnet` and `effort: high`.

Expected current-tree control: fresh generation emits Sonnet; the existing destructive writer loses custom fields. Observed: all three CLI calls returned zero; fresh generation emitted `model: sonnet`; both existing-input cases lost `effort: high`, and the deliberate case also lost `inherit` and `x-operator`. Assertions checked these observations. This refutes the known-bad proposition that changing seed text alone repairs preservation. The initial probe used invalid `--root`; it was corrected to the declared `--repo-root` CLI and all selected cases completed. Nothing was rendered into the repository.

Reproduction: create those three inputs under a temporary root, invoke `python3 -B .wavefoundry/framework/scripts/render_agent_surfaces.py --repo-root <temporary-root>` for each, then inspect `.claude/agents/guru.md`. Artifact/test ID: this report, `temporary-render-preservation-control`.

Integrity checks for this readiness evidence: `test_ran_without_unintended_skip=true`, `public_path_reached=true`, `boundary_values_realistic=true`, `assertions_non_vacuous=true`, `known_bad_detected=true`. Execution status: executed. Known-bad detection method: readiness-safe current-writer control. Actor: `wave-council`; context ID: `model-policy-readiness-20260917`; fresh context: true; independent: true. Probe class: local_safe; authorization: authorized; safe_boundary: false; unexecuted_remainder_prohibited: false; universal_claim: false.

## Delivery Follow-through

Include duplicate keys and missing delimiters alongside deliberate Sonnet, `inherit`, future values and unrelated fields in the planned fixtures. Keep separate controls for reintroducing a fixed default and bypassing preservation. Cover the actual upgrade/surface-render route, repeat-render byte stability and the seed-guided factor-wrapper path. These details refine existing requirements; they add no new scope or gate.

Limits: no implementation, future preservation behavior, upgrade correctness, effective model execution, live model calls or cost optimization was verified. Current-tree probes establish the defect and the plan's feasibility target only. The shared renderer is being edited by another wave; re-read its current symbols before activation. Required delivery lanes remain code-reviewer, qa-reviewer and docs-contract-reviewer. The coordinator owns typed approval and final ready-only transition.

## Lane Round 2026-09-21

Context: `model-policy-readiness-20260921`. Receipt: `review-policy-e1f99da91112f189c44f`. The three required lanes (code-reviewer, qa-reviewer, docs-contract-reviewer) ran in separate fresh contexts, read-only, and verified each plan claim against HEAD (`ead35718`) with live reads rather than the plan's own prose. All three approved; no blocking finding; thirteen nonblocking refinements were folded into the change doc (Rationale, Requirements 2, 5 and 6, Scope, AC-2, AC-3, Tasks, Decision Log, Risks, References). A separate documentation check confirmed the Claude Code frontmatter claims (`model` aliases and `inherit`, `effort` levels, per-invocation override outranks frontmatter, frontmatter outranks the environment default).

Known-bad detection in this round: the plan carried a stale claim that another agent still held the OPEN slot (`1y0gz` closed in `8545c4f9`), and its "ambiguous legacy ownership" framing did not hold for this repository, where git history (`07e9dd17`, `df94140d`) establishes that all five local pins are framework-written. Both were detected by the lanes and corrected. Drift since planning: the renderer changed only in scaffold-path resolution, not in the Guru writer; seed 160 gained unrelated setup and Python runtime sections.

Requested lane settings: host default model and effort for all three lanes, chosen because plan review against code needs judgment and each lane is bounded. Observed runtime identity: unknown; the host does not report it.

Limits: no implementation exists; no tests were run; no mutant was executed; which renderer the installing upgrade subprocess executes remains unverified and is recorded as a Risk.
