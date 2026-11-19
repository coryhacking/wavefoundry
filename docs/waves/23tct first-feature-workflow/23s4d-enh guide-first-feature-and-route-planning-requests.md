# Guide a first feature from definition through delivery review

Change ID: `23s4d-enh guide-first-feature-and-route-planning-requests`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-19
Wave: 23tct first-feature-workflow

## Rationale

The README compares artifacts and walks a health endpoint through delivery. Its first-wave example jumps from implementation to reported approvals without showing the operator request for delivery review. The command catalog describes what Plan spec produces. A product owner asking to specify a feature and an engineer asking later to plan its tasks need to recognize two stopping points within that workflow. Ease of transition for actual users remains unmeasured.

## Product Intent

A team can start its next feature in familiar language, hand an agreed definition to engineering, and locate the evidence for delivery. An agent can interpret a request in its conversational context and stop after the work the speaker asked for. AC-1 covers the visible handoff; AC-2 and AC-3 cover agent behavior.

## Requirements

1. Revise the existing README first-feature example. A product owner defines who benefits and what behavior matters; an engineer resumes the same spec to choose an approach and tasks. Identify an unfinished definition as a draft. Introduce a wave where the team groups work for delivery. Show one spec in one wave, admission, Prepare, Implement, an explicit Review wave with one concrete observation against an acceptance criterion, and operator-directed Close. Use the current enhancement kind for the example. Keep the primary walkthrough useful to first-time users of any background.
2. Add a short agent instruction in the command catalog, delivered by seed 100. Route by the requested action, subject, current artifact and user's stopping point. For example, “Specify the health endpoint; leave design for engineering” starts the definition within Plan spec. “Clarify what happens when a dependency times out” while drafting that spec resolves a requirement with the operator, recording the decision when settled. “Plan how to build it and break it into tasks” resumes that spec. Use existing project-configured workflow names. If two plausible readings would lead to materially different actions, ask one focused question before dependent work.
3. Distinguish a question about existing behavior, a request to refine a spec, an optional pre-build challenge (Review plan), a readiness check (Prepare wave), and verification of delivered work (Review wave). An explanation or a task breakdown alone grants no authority to admit, implement or close. Respect explicit requests to use another installed workflow. Keep this guidance in prose; no global word triggers or foreign slash-command registrations.
4. Retain a concise Spec Kit orientation near the existing README comparison. Explain familiar actions in terms of what they accomplish here. Keep the spec, approach and tasks together and show where a person can pause. Avoid expanding this into an artifact migration procedure.

## Scope

One documentation writer owns README.md, the catalog instructions in seed 100 and the self-hosted prompt index. Confirm normal seed reconciliation carries the catalog instruction to existing customized projects. Read Plan spec and its neighboring lifecycle prompts for consistency. Change 23rgx owns outcome-authoring language in seed 170 and the local Plan spec prompt. Either change can be reviewed on its own. This spec leaves skill names, host dispatch code, gates and OpenSpec conversion outside scope.

## Acceptance Criteria

- [x] AC-1: A fresh reader given the revised health-endpoint walkthrough can identify where product can stop, where engineering resumes, how a spec enters a wave, who asks for close, and which step shows evidence for the endpoint behavior. Report any missed handoff.
- [x] AC-2: In a disposable scenario with a definition-only request followed by clarification and a later task-planning request, the agent preserves the stopping point, settles the material ambiguity, and continues the same spec. Inspect outputs and workspace changes for a duplicate spec or premature implementation.
- [x] AC-3: A contrasting request such as “clarify how the endpoint works today” receives an explanation. An ambiguous “review this” with two plausible targets prompts a focused question. A request explicitly naming another installed workflow retains that choice. Check the actual response and side effects.
- [x] AC-4: A new target catalog and a reconciled existing catalog convey the routing guidance using local workflow names; the existing catalog preserves a local customization. The README and self-hosted catalog agree on the stages and full docs validation passes.

## Tasks

- [x] Revise the first-wave example and the existing comparison.
- [x] Add and reconcile the agent guidance in the public prompt index.
- [x] Exercise the walkthrough and routing cases; record the observed limits.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Documentation and seed | Documentation writer | Readiness | One owner for both audiences |
| Walkthrough and routing checks | Reviewer | Draft | Use fresh context for comprehension |

## Serialization Points

- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`, `docs/prompts/index.md`

The writer also owns the first-feature and comparison sections of the root README.

## Affected Architecture Docs

Existing command catalog and lifecycle routes retain their contracts. No architectural change is planned.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The reader can resume work at the right stage. |
| AC-2 | required | Familiar phrasing preserves the user's handoff. |
| AC-3 | required | Ordinary questions and explicit workflow choices keep their meaning. |
| AC-4 | required | Downstream agents receive the same instruction. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-19 | Observe: A fresh reader recovered all five walkthrough handoffs including review of HTTP 200 during dependency failure. In the coached calendar-export exercise only definition, settled answer and engineering planning changed the same draft; the clarification question, current timeout explanation, ambiguous review and explicit editorial review produced empty diffs. After clarifying checklist timing, a two-turn replay again preserved the draft-only stop. Fresh and renamed target catalogs carried the routes, and removing the inserted section restored every byte of the customized catalog. Agent exercises used disposable targets; live human onboarding, a packaged install and cross-host behavior remain unobserved. | Source comparison and disposable independent exercises. |
| 2026-11-19 | Readback: Guide first-feature handoff in README and route ordinary requests in seed 100 and the project catalog. Clarifying a proposed requirement can refine a draft; asking how the system works today calls for an explanation. | Readied scope. |
| 2026-11-19 | Compared the current artifact table, health-endpoint example and prompt catalog. | README sections Coming from Spec Kit or OpenSpec and Your first wave; prompt index Public Commands; seed 100 catalog instruction. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-19 | Use a worked conversation and a short context-sensitive routing instruction. | Readers encounter the handoff in the quickstart; agents encounter it before selecting a workflow. A routing trial can expose overreach. At the next natural onboarding, observe where a Spec Kit user needs coaching. | A README-only change leaves agent routing implicit. Hard aliases for single verbs can turn ordinary questions into writes and compete with installed tools. |

## Risks

| Risk | Mitigation |
| --- | --- |
| An agent treats a partial definition as ready to implement. | Show the draft handoff and the existing readiness boundary in the same example. |
| A successful agent trial is reported as evidence of easy human onboarding. | Record the trial and the first human onboarding observation separately. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
