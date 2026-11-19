# Make claims specific, attributable and useful

Change ID: `23ruk-doc concrete-claims-in-general-writing`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-18
Wave: 23r7u envision-opening-retelling

## Rationale

A sentence can be fluent and still give the reader little basis for a decision. For example, “Users want fewer reviews” turns feedback from one operator about separate review documents into a broader claim about the review process. The [unslop skill](https://github.com/backnotprop/pstack/blob/main/skills/unslop/SKILL.md) prompted this review of our shared writing practice.

## Product Intent

Readers of Wavefoundry prose can identify the concrete outcome a claim describes, whose observation supports it, and what remains to decide or do. Apply this to general writing, including specs, architecture, ADRs, plans, waves, prompts, memories, reviews, handoffs, release notes and replies. AC-1 and AC-2 verify the guidance and its application to examples. Field effects require later observation.

## Requirements

1. For a claim about a particular project or change, try substituting another project’s name. If the sentence still fits equally well, identify the specific action, behavior, or beneficiary outcome that matters. Keep useful general instructions and intentionally reusable contracts.
2. **Attribute claims used to make decisions.** Attribute consequential observations to an identifiable source at the scope it supports. For example, “One Tensorwell operator asked for fewer separate review documents.” Use role or source type when confidentiality requires it. Preserve uncertainty when evidence is limited.
3. **Check sentences that end in a promised benefit.** Inspect a sentence that starts with an action and ends by promising a benefit. State the connection the evidence supports. For example, replace “The runner retains a receipt, ensuring reliable delivery” with “The receipt lets the close gate check which framework inputs passed the suite.” Label an intended but unmeasured benefit as such.
4. Remove a closing sentence when it adds only praise, filler or a repeat of the preceding point. Keep conclusions that synthesize evidence for a decision or give a meaningful next action, owner or unresolved question.

## Scope

The canonical owner is `.wavefoundry/framework/docs/writing-guide.md`. Consolidate these checks into the existing editing guidance and use compact examples. Preserve established terminology, constraints and required document formats. This change adds no word blacklist, punctuation policy, skill, prose linter or review gate. The Envision colleague-retelling exercise stays in its review companion.

## Acceptance Criteria

- [x] AC-1: The shared guide gives writers all four editing checks, with their scope and exceptions. A reviewer can use the guide alone on ordinary project prose.
- [x] AC-2: Apply the checks to sample passages from two distinct artifact types outside Envision. Show a generic or unsupported claim made specific, attribution scoped to its evidence, a promised benefit corrected, and a redundant ending removed. A useful cross-project instruction, a consequential uncertainty and an actionable ending survive the edit.

## Tasks

- [x] Integrate the four checks in the shared guide and remove overlapping instruction.
- [x] Exercise the examples and preservation controls, compare the result with the source meaning, and validate the edited docs.

## Serialization Points

- `.wavefoundry/framework/docs/writing-guide.md`

## Affected Architecture Docs

N/A. The change refines editorial guidance within its existing canonical owner.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Makes the checks available to all writing workflows |
| AC-2 | required | Verifies their application and protects meaningful content |

## Decision Log

Extend the existing guide so authors across workflows read one policy. A separate editing skill would depend on invocation. Importing the full style checklist would give punctuation and banned words the same weight as accuracy.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
