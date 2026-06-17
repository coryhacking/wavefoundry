# simulate-hooks: include the session-capture (Stop) hook

Change ID: `1p607-enh simulate-hooks-session-capture`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Wave: `1p5x8 large-codebase-map`
Last verified: 2026-06-16

## Rationale

teton field report (1.7.0+p5zy): the rendered `.claude/hooks/simulate-hooks.py` `HOOKS` map only knows `pre-edit` and `post-edit`. The new `Stop` → `session-capture` hook (wave 1p5ti) is rendered into `.claude/settings.json` and wired, but **cannot be dry-run** through the documented simulate path because `claude_simulate_hooks_source()` in `render_platform_surfaces.py` (~line 421) hardcodes the two-hook list. The hook list drifted because the simulate map and the settings renderer are independent sources.

## Requirements

1. **Add `session-capture` to the simulated `HOOKS` map** so the Stop hook is dry-runnable through `simulate-hooks`.
2. **Anti-drift: derive the simulate map from the same source the settings renderer uses** (one hook registry/list consumed by both `render_claude_settings` and `claude_simulate_hooks_source`), so a future rendered hook can't be added to settings without also being simulatable. A test asserts **parity** between the hooks rendered into `.claude/settings.json` and the keys in the simulate `HOOKS` map.
3. Generic; no behavior change beyond the simulate surface.

## Acceptance Criteria

- [x] AC-1: The rendered `simulate-hooks.py` `HOOKS` map includes `session-capture` (→ `.claude/hooks/session-capture.py`); the Stop hook is dry-runnable.
- [x] AC-2: The simulate map and the settings-rendered hooks come from one shared source; a parity test asserts every rendered Claude hook is in the simulate map (drift-proof). Full suite + docs-lint clean.

## Tasks

- [x] Factor the Claude hook list into one source consumed by both `render_claude_settings` and `claude_simulate_hooks_source`; include `session-capture`.
- [x] Add the parity test (rendered settings hooks == simulate map keys).
- [x] Full suite + docs-lint.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The Stop hook must be dry-runnable (the reported bug). |
| AC-2 | required | Deriving from one source prevents the drift that caused this. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | teton field report: simulate-hooks omits `session-capture`; hardcoded list in `claude_simulate_hooks_source` (~421). | `render_platform_surfaces.py` |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
