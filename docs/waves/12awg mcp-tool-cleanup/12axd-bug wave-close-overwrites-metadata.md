# wave_close Overwrites Metadata on Close Summary and Session Handoff

Change ID: `12axd-bug wave-close-overwrites-metadata`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-01
Wave: `12awg mcp-tool-cleanup`

## Rationale

`wave_close` generates two files on every close: the wave close summary (`docs/waves/<wave>/archive/close-summary-<date>.md`) and an update to the session handoff (`docs/agents/session-handoff.md`). Both writes are currently destructive:

1. **Close summary** — the scaffold template omits required metadata fields (`Owner`, `Status`, `Last verified`), so the freshly written file fails docs-lint immediately after close. This was hit twice during the `12ahv` wave: once when `12ahv` was first closed, and again when `wave_close` regenerated the file after `12awg` was opened.

2. **Session handoff** — `wave_close` rewrites the entire file from a template, discarding whatever content the agent had written there during the session. This is the wrong behavior: session-handoff is a living document maintained across the session; `wave_close` should only update the wave reference (clearing "Active wave"), not wipe the file.

These are two distinct bugs with two distinct fixes.

## Requirements

1. **Close summary template fix:** The close summary scaffold always includes `Owner`, `Status: closed`, and `Last verified: <date>` filled in with values known at close time (`Owner` from the wave record, `Last verified` from today's date). The file must pass docs-lint immediately after `wave_close` writes it, with no manual patching required.

2. **Session handoff targeted update:** `wave_close` does not rewrite `docs/agents/session-handoff.md` from a template. Instead it reads the existing file and makes a targeted update: clearing the "Active wave" field (or setting it to `*(none)*`) and updating `Last verified`. All other content is preserved as-is. If the file does not exist, a minimal valid scaffold is written (as today).

3. **`wave_pause` consistency:** `wave_pause` also updates the session handoff. Apply the same targeted-update behavior there: only update the wave reference and `Last verified`, preserve all other content.

4. Tests cover: close summary has required metadata after `wave_close`; session handoff content outside the wave reference is preserved after `wave_close`; session handoff content is preserved after `wave_pause`.

## Scope

**Problem statement:** `wave_close` stomps both the close summary (missing metadata) and the session handoff (full rewrite discards agent-written content).

**In scope:**

- Fix close summary template in `wave_close_response` to include `Owner`, `Status`, `Last verified`
- Change session handoff write in `wave_close_response` from full rewrite to targeted update
- Apply same targeted-update to `wave_pause_response` for consistency
- Tests for all three behaviors

**Out of scope:**

- Changing the content or structure of the close summary beyond adding the missing metadata fields
- Merging or diffing arbitrary content in the close summary (it's always a fresh artifact)
- Templating or formatting the session handoff content — `wave_set_handoff` semantics (write as-is) are unchanged

## Acceptance Criteria

- AC-1: After `wave_close`, the close summary at `docs/waves/<wave>/archive/close-summary-<date>.md` includes `Owner`, `Status: closed`, and `Last verified: <date>` and passes docs-lint without manual patching.
- AC-2: After `wave_close`, content in `docs/agents/session-handoff.md` outside the "Active wave" line is unchanged.
- AC-3: After `wave_close`, the session handoff "Active wave" field reflects the closed state (cleared or set to `*(none)*`).
- AC-4: After `wave_pause`, content in `docs/agents/session-handoff.md` outside the "Active wave" line is unchanged.
- AC-5: If `docs/agents/session-handoff.md` does not exist at close/pause time, a minimal valid scaffold is written (existing behavior preserved).
- AC-6: `python3 .wavefoundry/framework/scripts/run_tests.py` passes.
- AC-7: `.wavefoundry/bin/docs-lint` is clean.

## Tasks

- In `wave_close_response`: update the close summary scaffold string to include `Owner: <wave owner>`, `Status: closed`, `Last verified: <today>`.
- In `wave_close_response`: replace the session handoff full-write with a targeted-update helper that reads the existing file, updates only the "Active wave" field and `Last verified`, and writes back.
- In `wave_pause_response`: apply the same targeted-update helper to the session handoff write.
- Extract the targeted-update logic as a shared `_update_handoff_wave_ref(root, wave_id_or_none)` helper used by both close and pause.
- Add tests: close summary metadata present; handoff content preserved through close; handoff content preserved through pause; missing handoff creates scaffold.
- Run tests and docs-lint.

## Agent Execution Graph

| Workstream      | Owner       | Depends On | Notes |
| --------------- | ----------- | ---------- | ----- |
| close-summary   | implementer | —          | Template fix only; no merge logic needed |
| handoff-update  | implementer | —          | `_update_handoff_wave_ref` helper + wire into close and pause |
| tests           | implementer | close-summary, handoff-update | Cover all ACs |

## Serialization Points

- `close-summary` and `handoff-update` workstreams are independent and can land in either order.

## Affected Architecture Docs

- N/A — this is a bug fix to internal write behavior with no new domain boundaries or interfaces.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority       | Rationale |
| ---- | -------------- | --------- |
| AC-1 | required       | Close summary must pass lint immediately after close; this is a repeated manual-fix burden |
| AC-2 | required       | Session handoff content preservation is the core of the bug fix |
| AC-3 | required       | Active wave cleared at close is basic correctness |
| AC-4 | required       | wave_pause has the same write pattern; must be fixed for consistency |
| AC-5 | required       | Missing handoff fallback prevents a regression from the existing behavior |
| AC-6 | required       | Tests are the verification gate |
| AC-7 | required       | docs-lint is the docs verification gate |

## Progress Log

| Date       | Update         | Evidence |
| ---------- | -------------- | -------- |
| 2026-05-01 | Bug identified. Hit twice during `12ahv` close and once more when `12awg` was opened. Distinct root causes: template missing metadata (close summary); full rewrite discards content (session handoff). | `wave_prepare` lint failures on close-summary and session-handoff after `wave_close` |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-01 | Fix close summary with complete template (option 1), fix session handoff with targeted update (option 2) | Close summary is always a fresh artifact — no existing content to preserve, template fix is sufficient. Session handoff is a living document — a full rewrite discards agent-written state, so a targeted update is required. | Option 1 for both (rejected: would still wipe session handoff content); option 2 for both (rejected: merge logic on a fresh artifact is unnecessary complexity) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Targeted handoff update fails to find the "Active wave" field in unusual handoff formats | Fall back to writing the minimal scaffold if the pattern is not found; log a diagnostic |
| Close summary `Owner` field not present in wave record | Default to `Engineering` (same as all existing waves); document the fallback |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
