# AC Priority Lint No Unknown

Change ID: `12jvb-enh ac-priority-lint-no-unknown`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The dashboard and wave tooling should not allow change docs to drift into an `unknown` AC state. If the AC Priority table is incomplete, malformed, or out of sync with the Acceptance Criteria bullets, docs-lint should fail so the mismatch is caught before the wave is reviewed or closed.

## Requirements

1. Docs-lint must fail when a change doc has Acceptance Criteria bullets that are not covered by the AC Priority table.
2. Docs-lint must fail when an AC Priority row uses an invalid or placeholder priority value.
3. Well-formed change docs with matching AC bullet and AC Priority rows must continue to pass.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- wave documentation updates needed to track the new lint rule

**Out of scope:**

- Dashboard rendering changes
- Wave lifecycle behavior

## Acceptance Criteria

- A change doc with more AC bullets than AC Priority rows fails docs-lint.
- A change doc with malformed AC Priority values fails docs-lint.
- A change doc with matching AC bullets and AC Priority rows still passes docs-lint.
- Regression coverage proves both failure modes and the success path.

## Tasks

- Add a docs-lint validator for AC Priority completeness and value validity
- Add regression tests for missing AC priority coverage and malformed priorities

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Unknown AC states should be caught before review. |
| AC-2 | required | The linter should fail when the table is incomplete. |
| AC-3 | required | The linter should fail when priorities are malformed. |
| AC-4 | required | Valid docs must continue to pass. |
