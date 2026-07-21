# Sync Surfaces Reports a Structured Written-File Manifest

Change ID: `1t729-enh sync-surfaces-written-manifest`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

`wf_sync_surfaces` renders host configs and native wrappers but its response
exposes no usable file list: `run_sync_surfaces` greps stdout for lines
containing "wrote"/"rendered" into `files_written` — prose lines, not paths.
That fragility blocked the 1t15a artifact credit (deferred by recorded
decision: "response exposes no file list") and leaves operators unable to see
what a sync actually touched. A structured manifest closes both gaps: the
response becomes reviewable, and the renderer's real work earns the same
deterministic avoided-writing credit as the other artifact tools.

## Requirements

1. `render_platform_surfaces` emits a machine-readable manifest of the files it
   wrote (repo-relative paths), through a structured channel — not by parsing
   free-text log lines. Log output stays human-readable.
2. `run_sync_surfaces` returns the manifest as `written` (list of
   repo-relative paths) alongside the existing `passed`/`output`; the fragile
   `files_written` prose-line grep is retired (breaking-shape note recorded —
   the field was never a path list).
3. `wf_sync_surfaces_response` exposes `written` in its data on successful
   `mode='run'`; dry-run continues to expose no file list.
4. `wf_sync_surfaces` joins `_ARTIFACT_EXTRACTORS` through the shared
   written-paths extractor, closing the 1t15a deferral: credit follows the
   per-artifact floor and stable replay-identity contracts already in place.
5. An unchanged re-render (nothing written) credits nothing.

## Scope

**Problem statement:** the renderer's output is only human prose, so the
response cannot enumerate written files and the tool cannot take artifact
credit.

**In scope:**

- Manifest emission in `render_platform_surfaces`
- `run_sync_surfaces` / `wf_sync_surfaces_response` shape
- The artifact-extractor registration and its tests

**Out of scope:**

- Changing what the renderer writes or the platform surface set
- Crediting dry-run or failed runs (error responses credit nothing, per the
  established observational contract)

## Acceptance Criteria

- [x] AC-1: A `mode='run'` sync whose renderer wrote files returns their
      repo-relative paths under `data.written`, verified by test with the real
      renderer manifest channel (canonical producer, not a hand-modeled shape).
- [x] AC-2: `wf_sync_surfaces` credits the written files as derived artifacts
      (per-artifact floor, replay dedup), verified by wrapper test.
- [x] AC-3: A no-op re-render and a dry-run credit nothing, verified by test.
- [x] AC-4: Full framework test suite passes (6,036 tests across 56 files, OK, 2026-07-20).

## Tasks

- [x] Manifest channel in `render_platform_surfaces`
- [x] `run_sync_surfaces` returns `written`; response exposes it
- [x] Artifact-extractor registration + tests
- [x] Run full framework test suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| renderer   | Engineering | —          | Manifest emission |
| surface    | Engineering | renderer   | Response shape + extractor |


## Serialization Points

- `server_impl.py` extractor table is shared with 1t72a; sequence their edits.

## Affected Architecture Docs

`docs/references/context-efficiency.md` (artifact-credit tool census gains
wf_sync_surfaces). `N/A` otherwise.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The structured manifest is the point of the change |
| AC-2 | required | Closes the recorded 1t15a deferral |
| AC-3 | required | The never-overstate bright line |
| AC-4 | required | Suite-green delivery gate |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-20 | Manifest channel, response shape, and artifact credit landed; hermetic tests green | ManifestChannelTests; test_sync_surfaces_credits_written_manifest_files |
| 2026-07-20 | LIVE-CAUGHT at the post-reload double-probe: the four tier-3 agent surfaces reported as written on every byte-identical re-render — the Guru-less hermetic fixture had let render_agent_surfaces early-return (incomplete-fixture blind spot). Repaired with net-change semantics (pre-render snapshot, verdict after the closing reconcile pass, reconcile return no longer re-adds candidates); fixture strengthened to a Guru-enabled repo that reproduces the find hermetically | `ev-agent-surfaces-report-unchanged-files-as-written*`; strengthened ManifestChannelTests |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-20 | Manifest records only NEW-OR-CHANGED content (byte comparison inside the write chokepoint); writes still always happen | "Written" for credit purposes means avoided writing of real new content; a byte-identical rewrite avoided nothing. Also makes the no-op re-render manifest empty (AC-3) without changing renderer side effects | Record every write (rejected: overstates on idempotent re-renders); skip identical writes entirely (rejected: mtime-behavior scope creep) |
| 2026-07-20 | `render_agent_surfaces`' changed-only return value merges into the manifest rather than instrumenting its writers | It already reports exactly the changed-path semantics the manifest needs | Instrument its four direct write sites (rejected: duplicate mechanism for identical data) |
| 2026-07-20 | Tier-3 agent surfaces use NET-change semantics: pre-render bytes vs post-closing-reconcile bytes, with the reconcile pass's return filtered against decided candidates | The render intentionally rewrites templates then reconciles them every pass, so write-time comparison oscillates and the reconcile's honest per-pass 'updated' return overstates net change | Make the reconciler idempotent against templates (rejected: changes the materialize-then-reconcile design this wave does not own); report every write (rejected: untruthful manifest) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Manifest channel drifts from what the renderer actually writes | Emit the manifest from the same code path that performs each write, never from a parallel list |
| Fixture-echo (the 1t3ek defect class) | AC-1 mandates the canonical renderer as the test producer; `server_impl.py` carries an active fragile-file advisory for exactly this area |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
