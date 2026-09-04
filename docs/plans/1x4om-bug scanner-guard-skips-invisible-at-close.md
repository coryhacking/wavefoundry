# A File the Secrets Scanner Skips Is Invisible to the Close Gate

Change ID: `1x4om-bug scanner-guard-skips-invisible-at-close`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-04
Wave: TBD

## Rationale

Raised by the security seat of wave `1x4ol`'s readiness council on 2026-09-04
and deliberately kept out of that wave's scope once the operator declined the
time bound that would have added a new route to it. This record exists so the
disclosed, unfixed gap survives that wave's close instead of evaporating with
the session.

The scanner already skips files it will not read: anything over
`MAX_FILE_BYTES`, any line over `MAX_LINE_BYTES`, and any file whose first 8 KB
holds a NUL byte. Each skip is surfaced two ways, a stderr line from
`_record_scan_skip` and an entry in `_SCANNER_SKIPS`, which is an in-process
list reset at the start of every `check_hardcoded_secrets` run. `scan-state.json`
persists a `files_skipped` COUNT with no paths.

The close-time gate, `_check_secrets_gate`, reasons only over entries in
`docs/scan-findings.json`. A file that was never scanned produces no entry, so
a skipped file passes close with no signal. This is not theoretical: the
current build log shows `Wavefoundry_Executive_Presentation.pptx` skipped by
the binary guard, and that skip reached close silently.

The gate is fail-closed on findings it can see and blind to files it was never
shown. A secret in a skipped file is invisible by construction.

## Requirements

1. A guard skip SHALL leave a durable record naming the path and the reason,
   persisted alongside the scan state rather than only emitted to stderr.
2. `wf_close_wave` SHALL surface every guard skip recorded since the last
   full scan, so a file that was never scanned is visible at the gate that
   already stops on unresolved findings.
3. Surfacing SHALL be advisory, not blocking, unless the operator classifies a
   skip as requiring review. A binary asset skipped for a NUL byte is the
   common case and must not halt every close.
4. The record SHALL be cleared for a path only when that path is subsequently
   scanned or removed, never by a run that skipped it again.

## Scope

**Problem statement:** The close gate cannot see files the scanner declined to
read, so a skipped file carrying a secret passes silently.

**In scope:**

- A persisted skip record beside `scan-state.json`.
- Close-time surfacing of recorded skips as an advisory.
- Tests for each existing guard reaching the record and the gate.

**Out of scope:**

- Any change to which files are eligible for scanning or to the guards
  themselves.
- Any time bound. Operator-declined in wave `1x4ol`.

## Acceptance Criteria

- [ ] AC-1: Each existing guard skip (file too large, line too long, binary)
      is persisted with path and reason, asserted per guard.
- [ ] AC-2: A `wf_close_wave` dry run on a tree with a recorded skip surfaces
      that path and reason in its response, and a tree with none surfaces
      nothing.
- [ ] AC-3: A recorded skip is cleared when the path is later scanned or
      removed, and is NOT cleared by a later run that skips it again.
- [ ] AC-4: Deleting the persistence makes a named test fail, recorded as a
      mutation before review.
- [ ] AC-5: This change's own suites and every test it adds pass, the documents
      it authors or edits validate, and no failure elsewhere is attributable to
      it.

## Tasks

- [ ] Persist guard skips with path and reason beside the scan state.
- [ ] Surface recorded skips in the close-wave response as an advisory.
- [ ] Add per-guard tests and the clear-on-scan test.
- [ ] Record the mutation.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| persist | implementer | — | Record beside scan-state.json. |
| surface | implementer | persist | Advisory in the close response. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py`
- `.wavefoundry/framework/scripts/scan_secrets.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_secrets_validators.py`

## Affected Architecture Docs

N/A beyond the secrets-gate description in `docs/specs/mcp-tool-surface.md`,
which gains the advisory. No boundary or flow change.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The record is the whole change. |
| AC-2 | required | Visibility at the gate is the point; visibility in a log is what exists today. |
| AC-3 | required | Without it a skip is either permanent or silently forgotten. |
| AC-4 | required | A guard that survives its own deletion is not landed. |
| AC-5 | required | Standard delivery gate. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-04 | Disclosed by the `1x4ol` readiness council and parked. | `_check_secrets_gate` loads only `docs/scan-findings.json`; `_record_scan_skip` writes stderr and a per-run list; `scan-state.json` keys are counts only; the current build log shows a `.pptx` binary-guard skip that reached close with no signal. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-04 | Park rather than fold into `1x4ol`. | The finding's premise for inclusion was that `1x4ol` would add a third skip route. The operator declined that route, so `1x4ol` adds nothing to this gap, and a security-visibility change does not belong in a wave scoped to build cost. | **Fold in anyway:** widens a performance wave with a gate change. **Drop it:** the gap is real and live today. |


## Risks


| Risk | Mitigation |
| --- | --- |
| The advisory is ignored like the stderr line is today. | It rides the close response, which is the surface the operator already reads before closing. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
