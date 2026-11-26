# State plainly that `response_keys` must not rename a key the parameter echo already renames

Spec ID: `24etg-doc response-keys-echo-rename-guidance`
Spec Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-26
Wave: 24eth waveforge-1p53-follow-ups

## Rationale

Waveforge reported, on v1.53.0, that a declared `response_keys` entry for a key that an echoed, renamed parameter already renames is refused by the declaration check. They agree the refusal is correct; they found it only through a failing test while serving an override as a `_spec` alias.

The rule is enforced in `_response_key_problems` (`.wavefoundry/framework/scripts/mcp_tool_extensions.py:744-748`), whose error already explains the cause ("is a renamed parameter, whose echoed key 'rename' already renames"). The contract documents it only as one clause in a single long sentence of refusal conditions in `docs/architecture/contracts/mcp-tool-surface.md` (around line 610: "renames a single-segment path that is a parameter `rename` already renames"). There is no separate extension-authoring guide; that contract section is where distributions read the alias rules. (executed: search and read.)

## Product Intent

A distribution author declaring an alias with both `rename` and `response_keys` learns from the contract, before writing a test, that a renamed parameter's top-level echo is already renamed and must not be repeated in `response_keys`. Before: the rule is a clause inside a long refusal list. After: a short sentence with an example sits beside the `response_keys` description. AC-1 tests the delivered guidance; whether authors stop hitting the refusal can only be observed in later distribution reports.

## Requirements

1. In the `response_keys` paragraph of `docs/architecture/contracts/mcp-tool-surface.md`, at the end of the sentence that begins "The echo renames and `response_keys` apply in one walk" (ending "...single-segment paths form that one pass"), add one or two sentences stating that a renamed parameter's echoed top-level key is already renamed by `rename`, so it must not be a `response_keys` path. Example: with `{"rename": {"spec_id": "change_id"}}`, `response_keys` paths use canonical names, so it must not declare the path `"change_id"`, which `rename` already answers as `spec_id`.
2. The existing refusal clause stays in the refusal list unchanged.
3. No code, test or seed changes.

## Scope

**Problem statement:** a correct refusal is hard to anticipate from the contract.

**In scope:**

- One addition to `docs/architecture/contracts/mcp-tool-surface.md`.

**Out of scope:**

- Changing the declaration check or its message.
- A new extension-authoring guide.

## Acceptance Criteria

- [x] AC-1: The contract's `response_keys` paragraph contains the new sentence and example before the refusal list, and the example is accurate: the declaration it names as refused is refused by `mcp_tool_extensions.validate_declaration` with the `is a renamed parameter` problem, checked by running that declaration once.
- [x] AC-2: The refusal clause is unchanged and the document validates.

## Tasks

- [x] Add the sentence and example.
- [x] Run the example declaration once against the validator and record the observed problem in the Progress Log.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| doc | implementer | — | AC-1, AC-2 |

## Serialization Points

- `docs/architecture/contracts/mcp-tool-surface.md`

## Affected Architecture Docs

`docs/architecture/contracts/mcp-tool-surface.md` only; wording, no behaviour change.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The guidance and its accuracy are the change. |
| AC-2 | required | The normative list must not drift. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-26 | Planned from the Waveforge v1.53.0 report, finding 5. | Reads cited in Rationale. |
| 2026-11-26 | Readiness notes applied: insertion point named by sentence, example wording clarified. Example check: `_response_key_problems` with `rename={'spec_id': 'change_id'}` and path `change_id` returns the `is a renamed parameter` problem. | Docs-contract F5; red-team probe. |
| 2026-11-26 | Readback: Explain the echo rule beside response_keys in the tool contract and exercise the exact spec_id example against validate_declaration. The refusal list stays authoritative. | ACs in this spec. |
| 2026-11-26 | The real validate_declaration call accepted the spec_id parameter mapping alone and refused a response_keys path of change_id with “is a renamed parameter”. Full docs lint passed. | Delivery verification. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-26 | Add a sentence and example beside the `response_keys` description in the contract. Planner default; the operator asked for a single wave covering the DO items. | The reported case: the author would have read the rule where `response_keys` is introduced. Guidance only; it advises, and the existing refusal still controls. | (B) Improve the error message: it already names the cause. (C) Write an extension-authoring guide: a new document for one rule. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The example could drift from the validator. | AC-1 runs it once against the validator. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
