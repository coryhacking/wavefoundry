# Reuse Existing Change And Extend ACs Tasks

Change ID: `12kfp-doc reuse-existing-change-and-extend-acs-tasks`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The lifecycle prompts should teach agents to reuse and extend an admitted current-wave change when a follow-up request is still part of that scope. That keeps one change authoritative instead of scattering closely related follow-ups across new IDs.

## Requirements

1. Planning prompts must tell agents to prefer updating an existing admitted change when a follow-up stays within the current wave.
2. Implementation prompts must tell agents to extend the existing change's ACs and tasks instead of opening a new change when the scope still fits.
3. New change IDs should only be created when the remaining work is materially different or needs separate tracking.
4. Rendered prompt surfaces must match the canonical seed wording.

## Scope

**In scope:**

- `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`
- `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`
- `docs/prompts/plan-feature.prompt.md`
- `docs/prompts/implement-feature.prompt.md`
- wave documentation updates needed to track the prompt guidance change

**Out of scope:**

- Product code
- Wave lifecycle semantics
- Prompt taxonomy changes

## Acceptance Criteria

- The planning prompt tells agents to adjust an existing admitted change when appropriate.
- The implementation prompt tells agents to extend ACs and tasks instead of creating a new change for same-wave follow-ups.
- The rendered prompt surfaces match the canonical seeds.
- Docs lint passes after the prompt updates.

## Tasks

- Update canonical planning and implementation seeds with the reuse rule
- Sync rendered planning and implementation prompt docs
- Sync the wave record and verify docs lint

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Planning needs the reuse rule to avoid needless change proliferation. |
| AC-2 | required | Implementation needs the same rule so follow-up work stays attached to the right change. |
| AC-3 | required | Seed and rendered prompt surfaces must stay aligned. |
| AC-4 | required | Docs lint must remain clean after the update. |
