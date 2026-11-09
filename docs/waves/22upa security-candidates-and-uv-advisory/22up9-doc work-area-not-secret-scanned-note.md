# Note That the Work Area Is Not Secret-Scanned

Change ID: `22up9-doc work-area-not-secret-scanned-note`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-08
Wave: 22upa security-candidates-and-uv-advisory

## Rationale

Waveforge's review of v1.40.0, item 3.

- `wave_lint_lib/secrets_validators` excludes the runtime directories `work`, `locks`, `cache`, `index`, `logs` and `dist` from secret scanning (`_SCAN_RUNTIME_DIRS`).
- Seed 180's **Disposable work** section and seed 209 tell agents to keep review receipts, probe captures and reports in `.wavefoundry/work/<wave-id>/`.
- No seed says that area is not scanned, so an agent that pastes a credential there gets no warning.

The exclusion is intended. The guidance is missing.

## Product Intent

Agents told to use the work area also learn that it is not secret-scanned and must not hold credentials. Scanner behaviour is unchanged.

## Requirements

1. Seed 180's **Disposable work** section gains one sentence:
   - the work area is gitignored and not secret-scanned;
   - do not copy credentials or other secret values into it;
   - redact them, as the safe-execution rule already requires.
2. Seed 209's work-area bullet points to that sentence rather than repeating it.

## Scope

**In scope:** seeds 180 and 209.

**Out of scope:** changing the scanner exclusions.

## Platform Behavior

Prose only; no platform difference.

## Acceptance Criteria

- [x] AC-1: Seed 180's Disposable work section states that the work area is not secret-scanned and must not hold credentials. Seed 209's work-area bullet references it.
- [x] AC-2: The seeds and the documents this change edits validate with `wf_validate_docs`.

## Tasks

- [x] Edit seeds 180 and 209 under `seed_edit_allowed`.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| seeds | implementer | none | two sentences |

## Serialization Points

- `.wavefoundry/framework/seeds/180-implement-change.prompt.md`, `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`

## Affected Architecture Docs

N/A: guidance only.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The change |
| AC-2 | required | Docs stay valid |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-11-08 | Planned from Waveforge item 3. | operator answer |
| 2026-11-08 | Implemented under `seed_edit_allowed` (opened and closed). Seed 180 **Disposable work** first paragraph gains: "The work area is gitignored and not secret-scanned, so never copy credentials or other secret values into it; redact them, as the safe-execution rule requires." Seed 209's work-area bullet already points to seed 180's **Disposable work** ("(seed 180’s **Disposable work**)"), so requirement 2 needed no edit. No rendered copy holds the sentence. Full `wf_validate_docs` passes. | seed diff, docs-lint |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-11-08 | Note in seed 180, pointer in 209 | Seed 180 owns the work-area rule | Repeat in seeds 190 and 209 |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| None material | |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
