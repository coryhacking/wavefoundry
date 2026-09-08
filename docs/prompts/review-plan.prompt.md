# Review Plan

Owner: Engineering
Status: active
Last verified: 2026-09-08

Shortcut: **`Review plan`** | Aliases: **`Interrogate this plan`**, **`Stress-test this plan`**

## Purpose

Optional stress-test of a consolidated change doc, or the current wave record when no change is specified, before or after admission and before implementation. Walks every unresolved decision branch in Requirements, Acceptance Criteria, and Scope.

**Compare the draft with its brief:**

At the start of this optional review, compare drafted Requirements, Acceptance Criteria, and Scope against the brief in Rationale, the operator's request, and relevant established context. When no change is specified, use the corresponding current-wave planning content. Consider what is strong, vague, missing, removable, or less useful to the consumer; report only meaningful observations and feed unresolved discrepancies into the existing decision-branch walk.

Read Rationale as reference for the brief, without reopening the whole section or resolved Decision Log entries. New ideas remain proposals, not authorized scope. This comparison adds no document, gate, or signoff; preserve the existing stop condition and one-question-at-a-time flow.

## Behavior

Given a change doc as context, or the current wave record when no change is specified:
1. Walk every unresolved decision branch one question at a time.
2. Provide a recommended answer and cite the supporting project resource (source code, specs, architecture docs, references, agent docs).
3. Self-answer without operator input when derivable from repository evidence.
4. Return `Self-Answered Questions`, `Operator Questions` or a batch `Question List`, and the `Stop Condition`.
5. Stop when all branches in Requirements, Acceptance Criteria, and Scope are resolved.

Support `--batch` mode for a full question list rather than interactive back-and-forth.

## When to Use

- Before or after admitting a complex or high-risk change, but before implementation
- When multiple valid approaches exist and the tradeoffs need surfacing
- When the change doc's acceptance criteria feel underspecified

## This Is Not a Gate

**Review plan** is an optional stress-testing tool, not a required lifecycle step. Use it before or after plan admission, at the operator's discretion, before implementation begins.

It records no typed signoff and satisfies no prepare or delivery gate. **Review wave** / `wf-review-wave` is the distinct workflow for the open wave's required implementation-review lanes and typed evidence.

See `.wavefoundry/framework/seeds/175-review-plan.prompt.md` for the full plan-review contract.
