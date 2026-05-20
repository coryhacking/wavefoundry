# Prompt surface manifest version bump for packaging

Change ID: `12rqn-enh prompt-surface-manifest-version-bump`
Change Status: `implemented`
Owner: Engineering

Status: implemented
Last verified: 2026-05-20
Wave: `12rnv agent-prompt-harness`

## Rationale

Packaging the current framework revision stamped a new canonical pack version and refreshed the generated prompt-surface manifest. That update needs to remain wave-tracked so the active wave reflects the repository state after packaging.

## Requirements

1. Update the canonical framework version to the newly packaged revision.
2. Refresh `docs/prompts/prompt-surface-manifest.json` so the recorded framework revision matches the stamped pack.
3. Keep the generated prompt surface and manifest metadata aligned for subsequent upgrade and packaging checks.

## Scope

- `/.wavefoundry/framework/VERSION`
- `docs/prompts/prompt-surface-manifest.json`
- `/.wavefoundry/framework/MANIFEST`

## Acceptance Criteria

- AC-1: The stamped framework version is recorded as `2026-05-20c`.
- AC-2: `docs/prompts/prompt-surface-manifest.json` records the same framework revision.
- AC-3: The wave record includes this packaging revision update as an implemented change.

## Tasks

- [x] Confirm the packaged revision.
- [x] Update the manifest metadata to the stamped revision.
- [x] Add the revision bump to the active wave.

## Progress Log

- 2026-05-20: Pack build completed successfully and stamped `2026-05-20c`.
- 2026-05-20: Version, manifest, and wave record aligned to `2026-05-20c`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|-----------|-------|------------|-------|
| packaging-version-bump | implementer | — | Keep `VERSION`, `MANIFEST`, and prompt-surface manifest aligned |

## Serialization Points

- The packaged revision must be stamped before the wave record is updated so the tracked metadata matches the artifact.

## Affected Architecture Docs

N/A — packaging metadata alignment only.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | The stamped revision is the source of truth for packaging |
| AC-2 | required | Manifest and framework revision must match or the next package build fails |
| AC-3 | required | The wave record must track the packaged state |
