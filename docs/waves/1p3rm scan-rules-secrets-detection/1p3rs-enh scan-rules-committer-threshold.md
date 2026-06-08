# Scan Rules Committer Threshold

Change ID: `1p3rs-enh scan-rules-committer-threshold`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-06
Wave: `1p3rm scan-rules-secrets-detection`

## Rationale

The framework default `false_positive_confirmations_required = 2` is appropriate for small multi-person teams but blocks solo projects (only one reviewer available) and is too permissive for large teams (two reviewers may represent a small fraction of contributors). At install and upgrade time the git history is available and provides a direct signal: the count of unique committer emails in the last 24 months approximates the size of the team actively engaged with the codebase. Using recent history rather than all-time avoids inflating the threshold for projects with decades of historical contributors but a small current maintainer set. Computing the project-level threshold from this signal and writing it to `docs/scan-rules.toml` during install/upgrade eliminates the need for every project operator to understand and manually set the policy.

## Requirements

1. During install (seed-012 step 2.3), after creating the `docs/` structure and before closing out Phase 2:
   - Count unique committer emails in the last 24 months:
     ```bash
     git log --format="%ae" --since="2 years ago" | sort -u | wc -l
     ```
     If the command fails (no git repository, no commits, or no git installed), treat the count as 0. If the command succeeds but returns 0 (no commits in the last 24 months), fall back to all-time history:
     ```bash
     git log --format="%ae" | sort -u | wc -l
     ```
     If the all-time fallback also returns 0 or fails, treat the count as 0.
   - Map count to threshold:
     - 0–1 committers → `false_positive_confirmations_required = 1`
     - 2–6 committers → `false_positive_confirmations_required = 2`
     - 7+ committers → `false_positive_confirmations_required = 3`
   - Check whether `docs/scan-rules.toml` already contains `false_positive_confirmations_required`. If it does, skip — never overwrite an operator-set value.
   - If absent: create `docs/scan-rules.toml` with the computed value and a header comment explaining the auto-detection and how to override.
   - Log the detected count and chosen threshold in the install step output so the operator can verify or override.

2. During upgrade (seed-160 step 8 normalization list):
   - Apply the same detection and write logic: count unique committer emails in the last 24 months (with all-time fallback if count is 0), map to threshold, write to `docs/scan-rules.toml` only if `false_positive_confirmations_required` is not already present in the file.
   - If `docs/scan-rules.toml` exists but lacks `false_positive_confirmations_required`, add the `[policy]` section with the computed value without disturbing existing content.
   - If `docs/scan-rules.toml` does not exist, create it with the computed value.

3. The created/updated `docs/scan-rules.toml` uses this template:

   ```toml
   # wavefoundry project scan rules
   # false_positive_confirmations_required: auto-detected from git committer count (last 24 months) at install.
   # Override this value if your team size has changed, then delete this comment.
   # Add project-specific [[rules]] entries below to extend the framework default ruleset.

   [policy]
   false_positive_confirmations_required = N
   ```

4. The created file must be valid TOML parseable by `load_merged_ruleset` in `wave_lint_lib/secrets_validators.py`.

5. The step never overwrites an operator-set `false_positive_confirmations_required`. Once set (by this step or manually), the value is sticky across upgrades.

## Scope

**Problem statement:** The `false_positive_confirmations_required` policy has a fixed framework default (2) that is wrong for solo projects and under-strict for large teams. Projects must manually discover and override this value, which most operators won't do.

**In scope:**

- seed-012 — new install step for committer-threshold detection and `docs/scan-rules.toml` creation
- seed-160 — upgrade normalization entry for backfilling `docs/scan-rules.toml`

**Out of scope:**

- Automatic re-detection on future git history changes (threshold is set once at install/upgrade)
- Integration with `wave_install_audit` artifact verification (scan-rules.toml is not a required-artifact row in the install log)
- Changing the framework default in `.wavefoundry/scan-rules.toml` — that stays at 2

## Acceptance Criteria

- [x] AC-1: Install step detects unique committer count via `git log --format="%ae" --since="2 years ago" | sort -u | wc -l` with all-time fallback when count is 0, and maps to threshold (0–1→1, 2–6→2, 7+→3).
- [x] AC-2: Count of 0 (no git history, empty repo, or no commits in window after fallback) maps to threshold 1.
- [x] AC-3: Install step creates `docs/scan-rules.toml` with the computed `false_positive_confirmations_required` when the file does not contain the key.
- [x] AC-4: Install step skips write if `false_positive_confirmations_required` is already set in `docs/scan-rules.toml`.
- [x] AC-5: Upgrade step (seed-160) backfills `docs/scan-rules.toml` using the same detection logic (24-month window + all-time fallback); does not overwrite an existing value.
- [x] AC-6: Created `docs/scan-rules.toml` is valid TOML that `load_merged_ruleset` can parse without error.
- [x] AC-7: Install step logs the detected committer count and chosen threshold in its output.

## Tasks

- [x] Open seed edit gate (`wave_gate_open(gate="seed_edit_allowed")`)
- [x] Add committer-threshold detection step to seed-012 (after step 2.3, before 2.4)
- [x] Add committer-threshold backfill entry to seed-160 step 8 normalization list
- [x] Close seed edit gate (`wave_gate_close(gate="seed_edit_allowed")`)

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| seed-012 + seed-160 | software-engineer | `1p3rn` complete (scan-rules.toml schema stable) | Both edits in one seed gate session |

## Serialization Points

- Seed edit gate must be open for the duration of seed-012 and seed-160 edits and closed immediately after.

## Affected Architecture Docs

N/A — seed-level instructions only. No schema, infrastructure, or framework script change.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Core detection logic with time-bounded window and all-time fallback |
| AC-2 | required | No-history case is the solo-project path |
| AC-3 | required | File creation is the deliverable |
| AC-4 | required | Must not overwrite operator decision |
| AC-5 | required | Upgrade parity with install |
| AC-6 | required | Invalid TOML breaks secrets scanning |
| AC-7 | important | Operator needs to verify auto-detected value |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| | | |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-06 | Map 0–1→1, 2–6→2, 7+→3 | Solo projects (0–1 committer) need only one reviewer; pair-and-up (2–6) need two; large teams (7+) need three. Original 0–2 bucket conflated solo with pair — a two-person team can still provide meaningful dual review. | 0–2→1 (original) — rejected: pair projects deserve two reviewers; linear scaling — rejected; threshold 2 always — rejected |
| 2026-06-06 | 24-month time window for committer count, with all-time fallback | Recent history approximates the active maintainer set; all-time history inflates count for long-lived projects with past contributors no longer involved. 24 months captures annual release cadence. Fallback ensures projects with no recent activity (dormant repos) still get a threshold rather than defaulting to 1 incorrectly. | All-time always — rejected: decades of history inflates threshold for small current teams; 12 months — rejected: misses annual contributors; per-commit weighting — rejected: adds complexity without proportional benefit |
| 2026-06-06 | Never overwrite existing value | Threshold is an operator judgment call after first set; auto-detection at upgrade would be surprising and potentially destructive | Re-detect on every upgrade — rejected: destroys operator overrides |
| 2026-06-06 | Seed-012 (Phase 2) not Phase 1 | Phase 1 has no MCP and may not have full docs structure yet; Phase 2 is after the docs root is established | Phase 1 — rejected: docs/ not yet created |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
