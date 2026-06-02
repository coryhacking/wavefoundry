# Workflow-Config Emits code_navigation_hints Block

Change ID: `1p2th-enh workflow-config-emits-code-navigation-hints-block`
Change Status: `implemented`
Owner: Engineering
Status: in-progress
Last verified: 2026-06-02
Wave: 1p2q3 field-feedback-round-4

## Rationale

Teton field validation against 1.3.6+p2t6 confirms that seed-211 documents the `code_navigation_hints.guard_tokens` schema clearly, including the default-fallback behavior when absent. But no example exists in:

- `docs/workflow-config.json` — the file the schema actually applies to. Teton's repo has no `code_navigation_hints` key at all.
- seed-100 / seed-040 — the seeds that produce / maintain `docs/workflow-config.json` at project init time.
- The package-wavefoundry workflow doc.

So an operator reading guru's question-type recipes and wanting to tune the guard tokens has to navigate from the recipe back to seed-211, read the schema, construct a JSON block from scratch, and decide where to put it. A one-line example in the workflow-config skeleton at init would close the loop.

The fix is trivial and entirely additive — emit the default-tokens block as part of the seed-100-produced workflow-config skeleton. Operators see the schema in context, can tune it in place when they want non-default guard tokens, and `wave_garden` / `wave_validate` continue to ignore unknown keys (so no validation churn).

## Approach

Add a `code_navigation_hints` block with the language-default `guard_tokens` array to seed-100's workflow-config skeleton. The block is purely declarative — the resolver already falls back to these defaults when absent, so the block makes the operator-tunable surface visible without changing behavior.

Block content:

```json
"code_navigation_hints": {
  "guard_tokens": ["return", "throw", "raise", "guard", "assert"]
}
```

This is what the resolver consults today (when `code_navigation_hints` is present in `workflow-config.json`); operators can edit the array to add codebase-specific guard patterns (e.g. `["return", "throw", "raise", "guard", "assert", "panic!", "expect"]` for a Rust-heavy codebase) without re-reading the schema docs.

The seed update lands at project init; existing repos pick it up via the next `setup-wavefoundry` run (which is idempotent — only adds keys that don't exist, doesn't overwrite custom tuning).

## Requirements

1. seed-100 (the install workflow seed that produces the initial `docs/workflow-config.json`) emits a `code_navigation_hints` block with the documented default `guard_tokens` array.
2. The block lives at the top level of `workflow-config.json` (sibling to `lifecycle_id_policy`, `indexing`, etc.), matching the schema documented in seed-211.
3. Existing repos with a populated `workflow-config.json` are not modified by this change — the seed update only affects new initializations.
4. Operators tuning `guard_tokens` after init see the same behavior they get today: the resolver consults the value when present, falls back to the language defaults when absent.
5. Regression test: a fresh seed-100 run against a clean fixture produces a `workflow-config.json` containing the `code_navigation_hints.guard_tokens` array.
6. All existing 2,200 framework tests pass without modification.

## Scope

**Problem statement:** `code_navigation_hints.guard_tokens` is documented in seed-211 but absent from the workflow-config skeleton seed-100 emits at init, so operators tuning it have to construct the block from scratch.

**In scope:**

- `.wavefoundry/framework/seeds/100-install.prompt.md` (or wherever seed-100's workflow-config skeleton lives) — emit the `code_navigation_hints` block
- `.wavefoundry/framework/scripts/tests/test_setup_wavefoundry.py` — verify the block appears in fresh init output

**Out of scope:**

- Backfilling existing `workflow-config.json` files in upgraded repos. The block is purely an operator-facing convenience; no behavior change either way.
- Adding `code_navigation_hints` validation to `wave_garden` / `wave_validate`. Defaults work fine when absent; validating the shape adds churn without value.

## Acceptance Criteria

- [x] AC-1: seed-100's workflow-config skeleton includes a `code_navigation_hints` block at the top level.
- [x] AC-2: The block's `guard_tokens` value matches the language-default array documented in seed-211: `["return", "throw", "raise", "guard", "assert"]`.
- [x] AC-3: Existing repos with a populated `workflow-config.json` are not modified by this change.
- [x] AC-4: Regression test: fresh init against a clean fixture produces a `workflow-config.json` with the block present.
- [x] AC-5: All existing 2,200 framework tests pass without modification.

## Tasks

- [x] Open `seed_edit_allowed` gate
- [x] Locate the workflow-config skeleton in seed-100 (or the install machinery that consumes it)
- [x] Add the `code_navigation_hints` block to the skeleton
- [x] Add regression test in `test_setup_wavefoundry.py`
- [x] Run framework tests
- [x] Close seed gate; mark change `implemented`

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| seed-100-update | Engineering | — | Single seed edit |
| regression-test | Engineering | seed-100-update | One test |

## Serialization Points

- N/A — single-seed change with no integration gates.

## Affected Architecture Docs

N/A — surface seed addition; no architectural boundary, flow, or verification change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The block must land in the skeleton |
| AC-2 | required | Values must match the documented default to avoid divergence between seed-211 and seed-100 |
| AC-3 | required | Existing repos must not be perturbed |
| AC-4 | required | Regression coverage on the fresh-init path |
| AC-5 | required | No baseline regression |

## Related Work

- Follow-on to [[1p2qb]] (which documented the schema in seed-211 but did not propagate to seed-100). Closes the gap surfaced by Teton field validation.
