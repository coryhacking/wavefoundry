# Index Reload File Stat Signature

Change ID: `12kgy-enh index-reload-file-stat-signature`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

WaveIndex reloads its cached semantic layers by comparing the on-disk `built_at` string in `meta.json` against the last loaded value. That is weaker than the underlying indexer's own cache behavior and can miss same-second rebuild transitions. The reload guard should track the actual `meta.json` file signature instead of only the human-readable timestamp.

## Requirements

1. Index reload detection should compare the on-disk `meta.json` file signature, not just the `built_at` string.
2. The signature should use file metadata that changes reliably on rebuild, such as mtime plus size.
3. Existing `built_at` metadata should remain in `meta.json` for human-readable reporting.
4. Reload behavior should remain correct for both project and framework index layers.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`

**Out of scope:**

- Changing index file formats
- Changing chunking or traversal behavior
- Changing dashboard rendering or wave lifecycle behavior

## Acceptance Criteria

- WaveIndex reloads when `meta.json` mtime or size changes for either index layer.
- WaveIndex does not require a process restart to pick up a rebuilt index.
- The existing `built_at` value remains available for display and diagnostics.
- Regression tests cover both project and framework layer reload detection.

## Tasks

- Replace built_at-only reload tracking with a file-stat signature helper
- Keep `built_at` in meta for reporting, but not as the sole reload key
- Add tests for project and framework layer reloads driven by file stat changes

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Reload detection must track real file changes |
| AC-2 | required | Rebuilt indexes should be visible without restarting MCP |
| AC-3 | required | Human-readable built_at remains useful for diagnostics |
| AC-4 | required | Both project and framework layers must reload consistently |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| File-stat resolution differs across platforms | Use mtime plus size rather than built_at text alone |
| Reload becomes too eager | Only compare the meta signature, not every payload file |
| Tests overfit to a specific filesystem timing behavior | Exercise synthetic metadata writes rather than sleeps |
