# Bound Secrets-Scan Regex Cost and Make a Runaway Pattern Visible

Change ID: `1x4ok-enh secrets-scan-cost-bounds`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-04
Wave: 1x4ol index-build-cost-and-scanner-bounds

## Rationale

A full secrets scan of this repository takes 198.5 seconds, and one file
accounts for 173.6 of them.

The distribution is not a size curve. `server_impl.py` is the largest file at
1.65 MB and scans in 2.6 seconds. The expensive file is smaller, at 1.15 MB, and
takes 66 times longer. Two more artifacts cost about 12 seconds each. Everything
else is fast.

It is not rule volume either. The keyword prefilter works: 24 of 280 rules
activate on the slow file, which is the same count as the artifact that scans in
11 seconds and one fewer than the file that scans in 2.6.

The cause is backtracking, and it is visible in the pattern text. The Gitleaks
generic family all open with two nested bounded lazy quantifiers over the same
character class:

```
[\w.-]{0,50}?(?i:[\w.-]{0,50}?(?:secret|access|key|token) ...
```

Two `{0,50}?` spans over overlapping classes give the engine on the order of
2,600 split points to try at each starting position, restarted at every position
in the line. Under Go's RE2, which is what these patterns were written for, that
is linear. `scan-rules.toml` says so in its own header: the ruleset is
Gitleaks-schema and `_re2_to_re()` translates it at load. Python's `re` is a
backtracking engine, so the same pattern is quadratic per position.

The slow file is the worst input for that shape. Its lines are fully qualified
Python test identifiers, which are `[\w.-]` characters end to end:

```
"test_upgrade_wavefoundry.PublicUpgradeReviewProtocolIntegrationTests.test_surface_phase_reconciles_stale_carrie...
```

Measured on the longest such line, `generic-api-key` alone costs 0.66 ms against
effectively zero on an ordinary JSON line. Across 8,412 lines that is about 5.5
seconds for one rule, and thirteen more active rules share the prefix shape.

Nothing bounds this today. There is a `MAX_FILE_BYTES` guard and a
`MAX_LINE_BYTES` guard, both sized in bytes, and neither one bounds TIME. Python
cannot interrupt a running match, so a single pattern meeting the wrong content
stalls the build with no diagnostic and no ceiling.

The exposure is structural rather than incidental. The ruleset is refreshed from
upstream, upstream targets an engine with a complexity guarantee this one does
not have, and the trigger is machine-generated evidence that records identifiers
-- exactly what this repository commits under `docs/waves/**/evidence/`. The next
refresh can introduce another one.

## Requirements

1. The scanner SHALL bound the time any single file may consume, record a skip
   with a stated reason when the bound is exceeded, and continue the scan rather
   than aborting it.
2. A file skipped for exceeding the time bound SHALL be reported through the
   existing scan-skip channel with its path and the bound it hit, so a skipped
   file is never indistinguishable from a clean one.
3. A skipped file SHALL NOT be recorded in the per-file skip cache as
   successfully scanned, so the next run retries it rather than inheriting an
   unearned pass.
4. The generic-family prefix SHALL be bounded so that identifier-dense content
   no longer drives super-linear cost, without narrowing what the rules detect.
   Detection parity SHALL be proven against a fixture of true positives for each
   modified rule, not asserted.
5. The scan SHALL expose a per-file cost measurement sufficient to identify the
   next runaway pattern by rule id, so the next occurrence is diagnosed from a
   report rather than from a bespoke investigation.
6. Where a rule cannot be made linear without weakening detection, the change
   SHALL record that explicitly and rely on the time bound rather than silently
   leaving the cost in place.

## Scope

**Problem statement:** RE2 patterns running on a backtracking engine can consume
unbounded time on identifier-dense content, with no ceiling and no diagnostic.

**In scope:**

- A per-file time bound in `wave_lint_lib/secrets_validators.py`, its skip
  record, and its interaction with the per-file scan cache.
- The generic-family prefix shape and any sibling rule sharing it.
- Per-file, per-rule cost reporting sufficient to name a runaway pattern.
- A regression fixture built from the identifier-dense content that exposed this.

**Out of scope:**

- Replacing the regex engine with an RE2 binding. Recorded as the alternative
  that would remove the whole class, and deliberately not taken in this change.
- The `full` flag scoping on graph rebuilds (`1x4oj`).
- The findings ledger format, the close-time secrets gate, and any change to
  which files are eligible for scanning.

## Acceptance Criteria

- [ ] AC-1: A file whose scan exceeds the time bound is skipped with a recorded
      reason naming the bound, the scan continues, and the run completes.
- [ ] AC-2: A time-bound skip is reported through the scan-skip channel with its
      path, and is absent from the successfully-scanned set.
- [ ] AC-3: A time-bound skip does not populate the per-file scan cache, proven
      by a second run that scans the same file again rather than skipping it.
- [ ] AC-4: For every rule whose pattern this change edits, a fixture of true
      positives still matches and a fixture of known false positives still does
      not, both asserted before and after the edit.
- [ ] AC-5: The identifier-dense fixture that costs 173.6 seconds today scans
      inside the declared bound, and the whole-repository full scan drops below
      a stated ceiling recorded with its measurement date.
- [ ] AC-6: A per-file cost report names the most expensive rule for a given
      file, verified by pointing it at the known-slow fixture and asserting it
      identifies a generic-family rule.
- [ ] AC-7: Deleting the time bound makes a named test fail, and deleting the
      prefix fix makes a named performance assertion fail, both recorded as
      mutations before review.
- [ ] AC-8: `docs/architecture/performance-budget.md` and the scan-rules header
      record the time bound, the RE2-to-Python complexity gap, and what a future
      ruleset refresh must re-check.
- [ ] AC-9: This change's own suites and every test it adds pass, the documents
      it authors or edits validate, and no failure elsewhere is attributable to
      it.

## Tasks

- [ ] Freeze the identifier-dense regression fixture and its current cost.
- [ ] Add the per-file time bound, its skip record, and its cache interaction.
- [ ] Add the per-file per-rule cost report.
- [ ] Build true-positive and false-positive fixtures for every generic-family
      rule this change will touch, and record their verdicts BEFORE editing.
- [ ] Bound the generic-family prefix; re-run both fixtures for parity.
- [ ] Record both mutations.
- [ ] Measure the full scan before and after; update the budget and the
      scan-rules header.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| bound-and-report | implementer | — | Time bound, skip record, cost report. |
| detection-baseline | implementer | — | Fixtures frozen BEFORE any pattern edit. |
| prefix-fix | implementer | bound-and-report, detection-baseline | Parity is judged against the frozen baseline. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py`
- `.wavefoundry/framework/scripts/scan_secrets.py`
- `.wavefoundry/framework/scan-rules.toml`
- `.wavefoundry/framework/scripts/tests/test_secrets_validators.py`
- `docs/architecture/performance-budget.md`

## Affected Architecture Docs

`docs/architecture/performance-budget.md` records the time bound and the full
scan's ceiling. `docs/architecture/testing-architecture.md` gains the
detection-parity rule for any future pattern edit: a rule's behaviour is judged
against fixtures frozen before the edit, never against the edited pattern's own
output.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The bound is the durable protection; the pattern fix is one instance. |
| AC-2 | required | A silent skip in a security scanner is worse than a slow one. |
| AC-3 | required | A cached unearned pass would make the skip permanent. |
| AC-4 | required | A performance fix to a detection rule must not quietly cost detection. |
| AC-5 | required | The measured outcome the change exists to produce. |
| AC-6 | important | Turns the next occurrence into a report rather than an investigation. |
| AC-7 | required | Both guards must fail when deleted. |
| AC-8 | important | The next ruleset refresh needs to know what to re-check. |
| AC-9 | required | Standard delivery gate. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-04 | Localised to one file by measurement, not inference. | Per-file scan cost: 173.62 s for a 1.15 MB evidence artifact, 13.67 s and 11.22 s for two others, 2.63 s for the 1.65 MB `server_impl.py`, 0.04 s for a 0.92 MB test module. |
| 2026-09-04 | Ruled out size and rule volume as the cause. | The slow file activates 24 of 280 rules; the 11 s artifact activates 24 and `server_impl.py` 25. Larger files scan faster. |
| 2026-09-04 | Mechanism confirmed against the pattern text and timed on a real line. | The generic family opens with two nested `[\w.-]{0,50}?` spans; `generic-api-key` costs 0.66 ms on the file's longest line (245 chars of dotted underscore-heavy test identifiers) against effectively zero on an ordinary JSON line. Fourteen active rules share the shape. |
| 2026-09-04 | Confirmed nothing bounds the cost today. | `MAX_FILE_BYTES` and `MAX_LINE_BYTES` are byte guards; no time bound exists anywhere in the scanner, and Python cannot interrupt a running match. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-04 | Land the time bound first and treat the prefix fix as one instance of the class. | The ruleset is refreshed from upstream and upstream targets an engine with a complexity guarantee this one lacks, so the next refresh can reintroduce the problem. A bound survives that; a pattern fix does not. | **Fix only the pattern:** leaves the class open at the next refresh. **Exclude the expensive artifacts from scanning:** narrows coverage over committed files to hide a cost. **Swap in an RE2 binding:** removes the class outright and is the right long-term answer, but it is a dependency and engine change far larger than this wave, so it is recorded here rather than taken. |
| 2026-09-04 | Freeze detection fixtures before editing any pattern. | A pattern edit judged against its own post-edit output proves nothing about what stopped matching. | **Judge parity on the repository's own findings:** the ledger holds zero findings, so it would pass vacuously. |


## Risks


| Risk | Mitigation |
| --- | --- |
| The prefix fix silently narrows detection. | AC-4 freezes true-positive and false-positive fixtures per edited rule BEFORE the edit and asserts both sides after. |
| The time bound hides a genuinely slow but legitimate scan, so a file quietly stops being covered. | AC-2 reports every time-bound skip by path through the existing skip channel, and AC-3 keeps it out of the cache so the next run retries it. |
| The bound is tuned to this repository's content and trips on a normal file elsewhere. | The bound is set from the measured distribution, where the slowest legitimate file is 2.6 s against a 173.6 s outlier, so there is roughly two orders of magnitude of headroom to place it in. |
| Fixture content that reproduces the blowup is itself expensive to run in CI. | The regression fixture is sized to demonstrate super-linear growth, not to reproduce the full 173.6 s. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
