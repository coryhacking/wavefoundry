# Platform Surface Rendering Rewrites Unchanged Files On Every Setup

Change ID: `1zuq4-bug render-rewrites-unchanged-surfaces`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-04
Wave: 1zuq3 setup-rerun-output

## Rationale

Field report (1.29.0+puha target): every `wf setup` printed `build_index: repairing 1 drifted file(s): .gitattributes`, re-indexed it (0 chunks) and repeated on the next run. The file holds only the Wavefoundry line-ending block, and its modification time matched the last setup.

Cause, in `render_platform_surfaces.write_text`: it computes whether the bytes changed (for the sync manifest) but writes the file unconditionally, so every setup, upgrade and `wf render-surfaces` gives every rendered platform surface a new modification time with identical bytes. The indexer then re-processes `.gitattributes` (a docs-eligible file that yields no chunks) every build. Reproduced here: a zero-chunk `.gitattributes` with its mtime touched between builds is "repaired" on every build and is quiet when untouched. The same rewrites change the launch surfaces `setup_readiness.assessment_signature` watches, which can make a check running during setup report `inputs_changed`. `render_agent_surfaces.write_text` already skips byte-identical writes (wave 1t72b).

## Requirements

1. `render_platform_surfaces.write_text` does not write when the on-disk bytes equal the content; it still records the manifest entry as today (`changed` False) and still applies the executable bit when `executable=True` (an unchanged launcher whose mode lost its exec bit is repaired).
2. When the bytes differ or the file is unreadable, behavior is unchanged (write with `newline=""`).
3. No other renderer changes; `render_agent_surfaces.write_text` already has this rule.
4. CHANGELOG gets a bullet under `## [1.29.0]` `### Fixed`.

## Scope

**Problem statement:** byte-identical rewrites churn modification times on every render.

**In scope:**

- `render_platform_surfaces.write_text`; tests; CHANGELOG.

**Out of scope:**

- The indexer labelling a changed zero-chunk file "drifted" (the label is misleading but the work is correct and runs only when the file changes); recorded as a follow-up.

## Acceptance Criteria

- [x] AC-1: Rendering a surface twice leaves its modification time (`st_mtime_ns`) unchanged on the second render, and the manifest records it as unchanged.
- [x] AC-2: Changed content is written, and an unchanged executable launcher whose exec bit was removed gets it back (POSIX).
- [x] AC-3: `render_gitattributes_block` run twice leaves `.gitattributes` untouched on the second run.
- [x] AC-4: Restoring the unconditional write fails the tests (scratch copy).
- [x] AC-5: CHANGELOG describes the fix; docs validate.

## Tasks

- [x] Skip byte-identical writes in `write_text`, keeping the exec-bit repair
- [x] Add tests for mtime stability, changed content, exec-bit repair and `.gitattributes`
- [x] Show the mutant fails in a scratch copy
- [x] CHANGELOG bullet

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                         |
| ---------- | ----------- | ---------- | ----------------------------- |
| render     | implementer | —          | render_platform_surfaces only |


## Serialization Points

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`, `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`

## Affected Architecture Docs

N/A: write behavior of one helper; matches the agent-surface renderer's existing rule.

## Platform Behavior

Windows, macOS, Linux and WSL2: the comparison is byte-exact and the write keeps `newline=""`, so a file rendered on any host compares equal on the next render. The exec-bit repair is POSIX-only in effect (Windows ignores the mode bits, as today).

## AC Priority


| AC   | Priority | Rationale                                  |
| ---- | -------- | ------------------------------------------ |
| AC-1 | required | the root cause                              |
| AC-2 | required | no lost writes or exec bits                 |
| AC-3 | required | the field-reported file                     |
| AC-4 | required | the pins must catch a revert                |
| AC-5 | required | release notes                               |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-04 | Implemented: `write_text` returns early on identical bytes after recording the manifest entry, still applying the exec bit. Tests: second `.gitattributes` render keeps its mtime; identical write skipped, exec bit repaired, changed content written | `test_render_platform_surfaces` OK; scratch mutants A-B killed |
| 2026-10-04 | Planned from the 1.29.0+puha field report; reproduced with a touched zero-chunk `.gitattributes` | scratch `garepro2`: repairs on each touched build, quiet untouched; `render_platform_surfaces.write_text` writes unconditionally |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-04 | Fix the rewrite, not the indexer's handling of zero-chunk files | the rewrite is the cause and also touches files readiness watches; once mtimes are stable the indexer converges (reproduced) | exclude `.gitattributes` from docs indexing (hides one symptom, keeps the churn) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A caller relied on the rewrite to refresh a file's mode or mtime | the exec bit is still applied; no caller reads surface mtimes as a signal (readiness treats them as inputs) |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
