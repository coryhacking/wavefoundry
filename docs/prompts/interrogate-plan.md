# Interrogate This Plan

Owner: Engineering
Status: active
Last verified: 2026-04-28

Shortcut: **`Interrogate this plan`** | Alias: **`Stress-test this plan`**

## Purpose

Optional stress-test of a consolidated change doc before wave admission. Walks every unresolved decision branch in Requirements, Acceptance Criteria, and Scope.

## Behavior

Given a change doc as context:
1. Walk every unresolved decision branch one question at a time.
2. Provide a recommended answer and cite the supporting project resource (source code, specs, architecture docs, references, agent docs).
3. Self-answer without operator input when derivable from repository evidence.
4. Stop when all branches in Requirements, Acceptance Criteria, and Scope are resolved.

Support `--batch` mode for a full question list rather than interactive back-and-forth.

## When to Use

- Before admitting a complex or high-risk change
- When multiple valid approaches exist and the tradeoffs need surfacing
- When the change doc's acceptance criteria feel underspecified

## This Is Not a Gate

**Interrogate this plan** is an optional stress-testing tool, not a required lifecycle step. Use it before or after authoring a change doc but before wave admission.

See `.wavefoundry/framework/seeds/175-interrogate-plan.prompt.md` for the full interrogation contract.
