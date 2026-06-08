# Epoch Randomized Offset

Change ID: `1p3rr-enh epoch-randomized-offset`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-06
Wave: `1p3rq epoch-randomized-offset`

## Rationale

The current install instruction sets `epoch_utc` to the project's first git commit date (fallback: today minus 4 years). This makes the epoch trivially guessable: an observer who knows roughly when a project started can enumerate nearby dates and decode the ID scheme. Introducing a randomized offset of -365 to +180 days around a 5-year base makes the epoch unpredictable without materially changing the ID density or sort behavior. The asymmetric range (more past than future) ensures the epoch is always meaningfully before project inception while keeping it varied enough to resist enumeration.

## Requirements

1. The epoch calculation in seed-011 (Phase 1, Step 1.1) is updated to: `epoch = (inception_date - 5 years) + random_offset`, where `random_offset` is drawn uniformly from `[-365, +180]` days (inclusive).
2. `inception_date` is determined by the following priority order:
   1. First git commit date: `git log --reverse --format="%aI" | head -1` (non-empty output).
   2. If no git history: oldest file mtime in the project directory (excluding `.git/`), obtained via:
      ```
      python3 -c "
      import datetime
      from pathlib import Path
      mtimes = [p.stat().st_mtime for p in Path('.').rglob('*')
                if p.is_file() and '.git' not in p.parts]
      if mtimes:
          print(datetime.date.fromtimestamp(min(mtimes)).isoformat())
      else:
          print(datetime.date.today().isoformat())
      "
      ```
   3. If no git history and no files: `today`.
3. The installing agent generates `random_offset` using: `python3 -c "import random; print(random.randint(-365, 180))"`. The result is a signed integer number of days; a negative value pushes the epoch further into the past. The agent must write the computed epoch to `docs/workflow-config.json` immediately after generating the offset and must not re-run the formula — the epoch is a one-time decision.
4. The computed epoch is rounded to the nearest calendar date (no time component) and written as `YYYY-MM-DDT00:00:00Z`.
5. The seed documents the resulting range explicitly: the epoch will fall between `inception_date - 6 years` and `inception_date - approximately 4 years 6 months`.
6. The upgrade seed (seed-160) is updated to note that the fallback epoch for projects missing `epoch_utc` remains `2020-02-02T02:02:00Z` (unchanged); the randomized offset applies only at install time, not during upgrade backfill.

## Scope

**Problem statement:** The epoch is deterministic from the project start date, making lifecycle IDs decodable to approximate project age by an observer who can guess the epoch. A randomized offset breaks this correlation without changing the ID format or sort properties.

**In scope:**

- seed-011 (`011-install-wavefoundry-phase-1.prompt.md`) — Step 1.1 epoch calculation updated to randomized formula
- seed-160 (`160-upgrade-wavefoundry.prompt.md`) — note that upgrade backfill epoch is unaffected by this change

**Out of scope:**

- `lifecycle_id.py` — no code change; the epoch value is set at install time by an agent, not computed at runtime
- Existing projects — epoch is never overwritten once set (existing rule unchanged)
- Upgrade backfill default (`2020-02-02T02:02:00Z`) — unchanged

## Acceptance Criteria

- [x] AC-1: seed-011 Step 1.1 specifies the formula `(inception_date - 5 years) + random_offset` where `random_offset ∈ [-365, +180]` days.
- [x] AC-2: seed-011 specifies the exact Python one-liner for generating the offset: `python3 -c "import random; print(random.randint(-365, 180))"`.
- [x] AC-3: seed-011 documents the resulting epoch range: `inception_date - 6 years` to `inception_date - approximately 4 years 6 months`.
- [x] AC-4: seed-011 specifies the three-tier inception_date fallback: (1) first git commit, (2) oldest file mtime via the Python one-liner excluding `.git/`, (3) today if no files exist.
- [x] AC-5: seed-011 specifies that the computed epoch is written as `YYYY-MM-DDT00:00:00Z` (date only, no sub-day precision).
- [x] AC-6: seed-160 notes that upgrade backfill epoch (`2020-02-02T02:02:00Z`) is unaffected by the randomized offset; backfill never applies the random formula.
- [x] AC-7: seed-011 explicitly instructs the agent to write the epoch immediately after generating the offset and not re-run the formula (one-time decision).
- [x] AC-8: Lint passes after both seed edits.

## Tasks

- [x] Open seed edit gate (`wave_gate_open(gate="seed_edit_allowed")`)
- [x] Update seed-011 Step 1.1 with randomized epoch formula, Python one-liner, and range documentation
- [x] Update seed-160 upgrade backfill note to clarify randomized offset is install-only
- [x] Close seed edit gate (`wave_gate_close(gate="seed_edit_allowed")`)
- [x] Run docs-lint and confirm clean

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| seed-011 Step 1.1 update | software-engineer | — | Single insertion; open/close gate wraps both seed edits |
| seed-160 backfill note | software-engineer | seed-011 update | Edit in same gate session |

## Serialization Points

- Seed edit gate must remain open across both seed edits and be closed only after both are complete.

## Affected Architecture Docs

N/A — seed-level instruction change only. No code, schema, or runtime behavior change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Core formula |
| AC-2 | required | Implementer needs exact command |
| AC-3 | required | Range documentation prevents misapplication |
| AC-4 | required | Fallback case must be specified |
| AC-5 | required | Date-only precision is the existing convention |
| AC-6 | required | Prevents upgrade from inadvertently applying random offset |
| AC-7 | required | One-time decision constraint must be verifiable at close |
| AC-8 | required | Lint gate |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| | | |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-06 | Range [-365, +180] asymmetric | Biases toward further past (harder to guess) while allowing modest future offset; pure negative range would always give IDs starting further back than needed | Symmetric ±365 — rejected: could push epoch as close as 4 years before inception, too easy to guess; always negative — rejected: predictably pushes epoch back, enumerable |
| 2026-06-06 | Base of 5 years before inception | Puts IDs in the `1xxxx` prefix range for projects started in the last decade; 4-year base produced `0xxxx` prefixes | 4 years — was the prior default; insufficient for `1xxxx` start |
| 2026-06-06 | Upgrade backfill epoch unchanged | Randomizing backfill would silently change issued IDs for existing projects | Apply random to backfill — rejected: breaks ascending order for existing IDs |
| 2026-06-06 | Three-tier inception_date fallback (git → oldest mtime → today) | Projects without git history may have files years older than today; using today would produce a wrong epoch for migrated or pre-git codebases; oldest mtime is the best available signal | today-only fallback — rejected: wrong for pre-git projects with existing files; parent folder mtime — rejected: unreliable, changes on every file add/remove |
| 2026-06-06 | Python one-liner for mtime (not shell stat) | `stat` flags differ between macOS (`-f '%m'`) and Linux (`-c '%Y'`); Python `Path.stat().st_mtime` is cross-platform | Shell stat — rejected: platform-specific flags |

## Risks

| Risk | Mitigation |
|---|---|
| Installing agent re-runs the formula and gets a different offset on retry | Seed instructs agent to write epoch immediately and not re-derive it; epoch is treated as a one-time decision |
| Offset pushes epoch after project's first commit (if inception_date is very recent) | Maximum future offset is +180 days from 5-year base = still ~4.5 years before inception for any project; not a practical risk |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
