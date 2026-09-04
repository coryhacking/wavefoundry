# Remove the Secrets Scanner's Super-Linear Cost Without Changing What It Detects

Change ID: `1x4ok-enh secrets-scan-cost-bounds`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-04
Wave: `1x4ol index-build-cost-and-scanner-bounds`

## Rationale

A full secrets scan of this repository takes 198.5 seconds, and one file
accounts for 173.6 of them.

The distribution is not a size curve. `server_impl.py` is the largest file at
1.65 MB and scans in 2.6 seconds. The expensive file is smaller, at 1.15 MB, and
takes 66 times longer. Two more artifacts cost about 12 seconds each. Everything
else is fast.

It is not rule volume either. The keyword prefilter works: 24 of 280 rules
activate on the slow file, the same count as the artifact that scans in 11
seconds and one fewer than the file that scans in 2.6.

The cause is backtracking, and it is visible in the pattern text. Two related
shapes sit at the head of 131 of the 280 rules. Eleven open with two nested
bounded lazy quantifiers over the same character class:

```
[\w.-]{0,50}?(?i:[\w.-]{0,50}?(?:secret|access|key|token) ...
```

Two `{0,50}?` spans over the same class give a backtracking engine on the order
of 2,600 split points to try at each starting position, restarted at every
position in the line. The other 120 open with a single span, `(?i)[\w.-]{0,50}?`,
which has one split point per position but is still restarted at every one;
`generic-api-key` is of this kind. A first census reported all 131 as the nested
shape; that was wrong, and the split matters because the collapse below reaches
only the eleven. On the slow file, 23 rules are active: 6 nested, 6 single-span,
11 neither. Under Go's RE2, which these patterns were written for,
that is linear. `scan-rules.toml` says so in its own header: the ruleset is
Gitleaks-schema and `_re2_to_re()` translates it at load. Python's `re`
backtracks, so the same pattern is quadratic per position.

The slow file is the worst input for that shape. Its lines are fully qualified
Python test identifiers, which are `[\w.-]` characters end to end:

```
"test_upgrade_wavefoundry.PublicUpgradeReviewProtocolIntegrationTests.test_surface_phase_reconciles_stale_carrie...
```

**The fix does not change what the rules detect, and that is provable rather
than hoped.** Two adjacent lazy spans over one class, `X{0,50}?X{0,50}?`, accept
exactly the same strings as `X{0,100}?`. That is a statement about regular
languages, not an approximation. Verified before this plan was written:

| Check | Result |
| --- | --- |
| Random strings, original vs collapsed, two patterns | 0 mismatches in 100,000 |
| Real `aws-secret-access-key` true positives, spans and captured groups | 5 of 5 identical |
| Pathological line, `aws-secret-access-key` | 5.58 ms to 0.20 ms |

The transformation belongs in the engine, not in the ruleset. The header of
`scan-rules.toml` is explicit: patterns stay in RE2 schema and are never
hand-ported, and a construct the shim cannot handle means extending the shim.
A load-time rewrite survives the next upstream refresh; editing the eleven
patterns by hand does not, and would leave the 120 single-span rules untouched
anyway.

**Operator decision, 2026-09-04: no time bound.** An earlier draft of this
change added a per-file time limit as insurance. The operator declined it,
because a limit is the one piece that can reduce coverage. This change lands
only the transformations that cannot alter detection, measures the result, and
leaves any further step to a later decision made on that measurement.

## Requirements

1. The engine SHALL collapse the redundant nested prefix at pattern load, in
   the same shim that already translates RE2 constructs, and SHALL NOT edit
   `scan-rules.toml` to do so. The rewrite SHALL be restricted to the exact
   literal nested shape the eleven rules share, so it cannot act on a pattern it
   was not proven against. The 120 single-span rules are out of the collapse's
   reach by construction and are addressed, if at all, by Requirement 6.
2. The rewrite SHALL be proven language-preserving by differential testing:
   every affected rule's original and rewritten pattern SHALL produce identical
   match sets, spans, and captured groups over a random corpus, over a frozen
   true-positive fixture per affected rule family, and over the real
   repository. A single divergence fails the change.
3. The scan SHALL measure per-file and per-rule cost and expose it in the scan
   summary, sufficient to name the most expensive rule for a given file, so the
   next runaway pattern is diagnosed from a report rather than an
   investigation.
4. The whole-repository full scan SHALL be measured before and after on the
   same machine and both figures recorded with their dates in
   `docs/architecture/performance-budget.md`. This is a measurement, not a
   gate: the operator's direction is to land the transformations and decide
   the next step from the result.
5. The change SHALL NOT add a time bound, a byte bound, a line bound, or any
   other condition under which a file goes unscanned. Every file scanned
   before this change SHALL be scanned after it.
6. Per-line keyword gating is a CANDIDATE, not a requirement. It is
   language-preserving only for a rule whose keyword list covers its mandatory
   alternation, which holds for `generic-api-key` (keywords equal the
   alternation; 2.65 s to 0.21 s on the slow file, identical matches) but is
   not a property of the ruleset in general. It SHALL be considered only after
   the collapse is measured, and only for rules where the covering property is
   proven per rule.

## Scope

**Problem statement:** RE2 patterns running on a backtracking engine consume
super-linear time on identifier-dense content.

**In scope:**

- A load-time rewrite in the RE2-to-Python shim collapsing the exact redundant
  prefix shape.
- A differential test harness asserting language equivalence for every affected
  rule.
- Per-file, per-rule cost reporting in the scan summary.
- A regression fixture built from the identifier-dense content that exposed
  this, sized to demonstrate the growth rather than reproduce 173 seconds.
- Before and after measurement of the full scan.

**Out of scope:**

- Any time bound or new skip condition. Operator-declined.
- Making the pre-existing byte and binary guard skips visible to the close
  gate. Raised by the readiness council; it is real and it predates this wave,
  but it is a security-visibility change rather than a performance one, and
  with no new skip route being added here its premise for inclusion is gone.
  Parked as its own plan so it survives this wave's close.
- Replacing the regex engine with an RE2 binding. The alternative that removes
  the class outright; recorded, not taken.
- The `full` flag scoping on graph rebuilds (`1x4oj`).
- Editing any pattern in `scan-rules.toml`.

## Acceptance Criteria

- [x] AC-1: The shim rewrites the exact nested-prefix shape at load and leaves
      every other pattern byte-identical, asserted by round-tripping the full
      ruleset and diffing.
- [x] AC-2: For every affected rule, original and rewritten patterns produce
      identical match sets, spans, and captured groups over a random corpus, a
      frozen true-positive fixture, and the real repository. Zero divergences.
- [x] AC-3: The identifier-dense regression fixture scans measurably faster
      after the rewrite, with the growth curve recorded before and after.
- [x] AC-4: The scan summary names the most expensive rule for a given file,
      verified by pointing it at the regression fixture and asserting it names
      a rule of the affected shape before the rewrite.
- [x] AC-5: The set of files scanned is identical before and after, asserted
      over the real repository, and no new skip reason exists in the scanner.
- [x] AC-6: Deleting the rewrite makes a named performance assertion fail;
      corrupting the rewrite to alter the language makes the differential test
      fail. Both recorded as mutations before review.
- [x] AC-7: `docs/architecture/performance-budget.md` records the full-scan
      figure before and after with dates, and the `scan-rules.toml` header
      records the RE2-to-Python complexity gap and what a future refresh must
      re-check.
- [x] AC-8: This change's own suites and every test it adds pass, the documents
      it authors or edits validate, and no failure elsewhere is attributable to
      it.

## Tasks

- [x] Freeze the identifier-dense regression fixture and its current cost.
- [x] Freeze a true-positive fixture for each affected rule family, BEFORE any
      engine edit.
- [x] Add the load-time rewrite to the shim, restricted to the exact shape.
- [x] Add the differential harness and run it over random, fixture, and
      repository corpora.
- [x] Add per-file, per-rule cost reporting to the scan summary.
- [x] Record both mutations.
- [x] Measure the full scan before and after; update the budget and the
      scan-rules header.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| detection-baseline | implementer | — | Fixtures frozen BEFORE any engine edit. |
| rewrite-and-prove | implementer | detection-baseline | Equivalence judged against the frozen baseline. |
| cost-report | implementer | — | Independent; diagnostic only. |
| measure | implementer | rewrite-and-prove, cost-report | Before/after on the same machine. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py`
- `.wavefoundry/framework/scripts/scan_secrets.py`
- `.wavefoundry/framework/scripts/tests/test_secrets_validators.py`
- `docs/architecture/performance-budget.md`

## Affected Architecture Docs

`docs/architecture/performance-budget.md` records the full-scan figures.
`docs/architecture/testing-architecture.md` gains the differential-equivalence
rule for any future engine or pattern edit: a rewrite is judged by identical
match sets against frozen inputs, never by the rewritten pattern's own output.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The rewrite must be surgical; a shim that touches patterns it was not proven against is a detection change. |
| AC-2 | required | The whole claim is that detection is unchanged. This is the proof. |
| AC-3 | required | The measured outcome the change exists to produce. |
| AC-4 | important | Turns the next occurrence into a report rather than an investigation. |
| AC-5 | required | Operator direction: no file goes unscanned that was scanned before. |
| AC-6 | required | Both the speed and the equivalence must fail when their mechanism is removed. |
| AC-7 | important | The next ruleset refresh needs to know what to re-check. |
| AC-8 | required | Standard delivery gate. |


## Progress Log


| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-04 | Localised to one file by measurement, not inference. | Per-file scan cost: 173.62 s for a 1.15 MB evidence artifact, 13.67 s and 11.22 s for two others, 2.63 s for the 1.65 MB `server_impl.py`, 0.04 s for a 0.92 MB test module. |
| 2026-09-04 | Ruled out size and rule volume as the cause. | The slow file activates 24 of 280 rules; the 11 s artifact activates 24 and `server_impl.py` 25. Larger files scan faster. |
| 2026-09-04 | Mechanism confirmed against the pattern text and timed on a real line. | Eleven of 280 rules open with two nested `[\w.-]{0,50}?` spans and 120 more with a single `(?i)[\w.-]{0,50}?` span (a first census conflated the two as 131); on the file's longest line (245 chars of dotted underscore-heavy test identifiers) the real `aws-secret-access-key` pattern costs 5.58 ms against effectively zero on an ordinary JSON line. |
| 2026-09-04 | Proved the collapse is language-preserving before proposing it. | 0 mismatches over 100,000 random strings across two patterns; 5 of 5 real true positives keep identical spans and captured groups on `aws-secret-access-key`, including a 95-character identifier prefix at the edge of the old two-span coverage; 5.58 ms to 0.20 ms on the pathological line. |
| 2026-09-04 | Found the single-span variant the collapse does not reach, and its own safe lever. | `generic-api-key` opens with one `(?i)[\w.-]{0,50}?` span, so no collapse applies. Its keyword list equals its mandatory alternation, so per-line keyword gating is a theorem for it: 8,412 lines examined to 521, 2.65 s to 0.21 s, identical matches. Recorded as a candidate, not a requirement, because the covering property must be proven per rule. |
| 2026-09-04 | **Census corrected before any engine edit: 11 nested, 120 single-span, not 131 nested.** | The freeze script's exact-literal match found 11 rules carrying the two-span prefix; the earlier figure had OR'd in the single-span `(?i)[\w.-]{0,50}?` head. Re-derived: 11 nested (`aws-secret-access-key`, `cisco-meraki-api-key`, `cohere-api-token`, `okta-access-token`, five `polymarket-*`, `privateai-api-token`, `sumologic-access-id`), 120 single-span, 131 union, zero overlap. On the slow file 23 rules are active: 6 nested, 6 single-span, 11 other. Consequence: the collapse removes the worst per-line cost (5.58 ms) from six active rules; the six single-span rules (about 0.66 ms per line) remain, and Requirement 6's per-line gate is the only verified language-preserving lever for them. The plan, wave record, architecture note, and ruleset header were corrected in the same pass; the readiness approval evidence in the ledger is immutable and carries the old figure, so this row is the correction of record. |
| 2026-09-04 | **Growth curve recorded; the collapse removes a constant factor, not the exponent.** | Doubling an identifier run from 100 to 200 `[\w.-]` characters costs the nested form x3.1 and the collapsed form x3.2 on `aws-secret-access-key`: the same curve, roughly n * min(n, 100), because `search()` still restarts at every position. What the collapse removes is the ~2,600-way split factor at each position, which is why the absolute per-line cost drops by more than 5x (5.58 ms to 0.20 ms on the pathological line) while the shape of the curve is unchanged. A test asserting a flatter curve was wrong and was deleted rather than fitted; the absolute-cost assertion stands. |
| 2026-09-04 | **Baseline frozen BEFORE the engine edit, on the unmodified engine.** | `freeze_detection_baseline.py`, seed 20260904: every match of the eleven nested-shape rules over 20,000 seeded random lines (944 matches), the 15-entry hand-authored fixture (20 matches; the fixture itself agreed with the unmodified engine on all 15 expectations first), and every scannable file in the repository, line by line, honouring the production byte and binary guards (2,372 files, 5 matches). Digest `3a3ea871…`. The eleven rules alone took 343.6 s serially over the repository, which is the cost this change removes. Installed as `tests/fixtures/secrets_prefix_collapse_baseline.json`. |
| 2026-09-04 | **Landed: `collapse_redundant_prefix` in the load-time shim, applied to every pattern before compile.** | Exact-literal substitution of `[\w.-]{0,50}?(?i:[\w.-]{0,50}?` with `(?i:[\w.-]{0,100}?`; idempotent; every other pattern byte-identical on a full-ruleset round trip. It runs unconditionally, unlike `_re2_to_re`, because the nested shape compiles fine and the failure path would never see it. `scan-rules.toml` untouched apart from its header note. |
| 2026-09-04 | **Equivalence proven differentially, zero divergences.** | `test_secrets_prefix_collapse.py`: the random corpus reproduced from its seed, the frozen positives, and the five recorded repository matches all reproduce at identical spans with identical captured groups under the collapsed patterns; the fixture's 15 expectations still hold for every rule. |
| 2026-09-04 | **Cost report landed without changing the public scan contract.** | A first cut returned a 4-tuple from `scan_file_raw` and broke 23 callers in `test_secrets_validators.py` (`ValueError: too many values to unpack`). Reworked: `scan_file_raw` keeps its documented 3-tuple and appends the file's costliest rule to `_SCANNER_COSTS` in-process; the spawn-worker wrapper reads that back and returns it as a 4th element; the parent aggregates worker rows and skips serial ones, so nothing double-counts. `update_secrets_scan` prints the top five as `secrets scan cost — <ms> <file> (rule <id>, <n> rules timed)` and persists them as `most_expensive` in `scan-state.json`. All 146 existing scanner tests pass. |
| 2026-09-04 | **Full scan measured before and after, same machine, isolated, 8 workers.** | Before: 198.8 s over 2,373 files (serial control: 369.1 s, so the pool bought 1.85x because one file pinned one worker). After: 18.2 s over 2,377 files. Zero findings both sides. Graph rebuild command, after `1x4oj` alone: 52 s against 203 s. Recorded in `docs/architecture/performance-budget.md`. |
| 2026-09-04 | **AC-5 asserted, not assumed.** | `NothingNewIsSkippedTests`: a serial full scan of every eligible repository file records only the three pre-existing guard reasons (`file too large`, `binary file`, `binary file (extension)`), every file is either guard-skipped or produced a cost row, and a source-level check confirms no new `_record_scan_skip` reason exists. The mark was placed before this test existed and is honest only because of it; recorded so the sequence is visible. |
| 2026-09-04 | **Fixtures carry secret-shaped strings on purpose; the hazard is pinned rather than allowlisted.** | The frozen baseline and the positives fixture contain a documented AWS example key and random high-entropy captures. Allowlisting them for the scanner would narrow the scan set, which this wave forbids, so they stay scannable and `FixturesYieldNoFindingsTests` asserts that scanning them records no finding and leaves `docs/scan-findings.json` byte-identical (true today: the after-fix full scan covered them, zero findings, ledger unchanged). The baseline is excluded from the INDEX via `.aiignore`, the same treatment every machine-generated report family gets, which has no bearing on scan coverage. |
| 2026-09-04 | **Landing rule: both mutations recorded before review, engine restored byte-identical.** | Mutant A, `collapse_redundant_prefix` made a no-op: fails exactly `test_round_trip_over_the_whole_ruleset_changes_only_the_shape` and `test_the_collapsed_pattern_is_an_order_of_magnitude_cheaper_on_dense_input` (14 tests, 194.6 s, because the disabled collapse restores the slow path). Mutant B, `_COLLAPSED_PREFIX` changed to `{0,90}?` so the language narrows: fails `test_frozen_positives_match_identically` (the 95-character-prefix positive stops matching), `test_the_declared_shape_is_the_one_the_rules_actually_carry`, and the round-trip test (3 failures). The differential harness is therefore sighted in both directions: it detects a rewrite that stops working and a rewrite that changes what is detected. Engine restored and confirmed byte-identical against the pre-mutation copy. |
| 2026-09-04 | **Operator decision: no time bound.** | The earlier draft's per-file limit and its close-gate visibility work were removed. The visibility gap for the pre-existing byte and binary guards is real and predates this wave; parked as its own plan. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-04 | Rewrite in the engine shim at load, never in the ruleset data. | `scan-rules.toml`'s own header forbids hand-porting patterns and directs unsupported constructs to the shim. A load-time rewrite survives the next upstream refresh; 131 hand edits do not. | **Edit the eleven patterns by hand:** lost on refresh, and a review burden with no equivalence proof. **Swap in an RE2 binding:** removes the class outright and is the right long-term answer, but it is a dependency and engine change far larger than this wave. |
| 2026-09-04 | Prove equivalence differentially, not by fixture alone. | A fixture depends on imagining the right cases. A differential test over random input, frozen positives, and the real repository asserts the property the change claims. | **Fixture parity only:** proves the cases someone thought of. |
| 2026-09-04 | No time bound. Operator decision. | A limit is the one piece that can reduce coverage. The direction is to land the transformations that cannot, measure, and decide the next step on the result. | **Report-only timer with a hang-breaker in minutes:** offered; declined for now, revisitable on the measurement. |
| 2026-09-04 | **Operator decision at close: performance is fine at this point; the per-line keyword gate is not pursued.** | The measured result, 18.2 s for the isolated full scan and 52 s for the graph rebuild command, is accepted as the standing figure. The remaining per-line cost sits in the 120 single-span rules; the gate that would address them is language-preserving for 98 of those by mechanical proof and would need a per-rule proof for the other 22. It stays a recorded candidate, decidable later from the cost report the scan now prints, and is not admitted to any wave. | **Land the gate for the 98 proven rules now:** more speed the operator has said is not needed, in exchange for a third engine change in one wave. |
| 2026-09-04 | Per-line keyword gating stays a candidate. | It is language-preserving only where keywords cover the mandatory alternation, which is per-rule, not a ruleset property. Decide after the collapse is measured. | **Apply to every keyword-bearing rule:** narrows detection for any rule whose regex can match a line lacking its keyword. |


## Risks


| Risk | Mitigation |
| --- | --- |
| The shim rewrite acts on a pattern it was not proven against and changes its language. | AC-1 restricts the rewrite to the exact literal shape and asserts every other pattern is byte-identical after load. |
| The collapse is language-preserving in theory but a real rule has a construct that interacts with it. | AC-2 runs the differential over every affected rule, not a sample, including frozen true positives per family. |
| The measured saving is smaller than expected because another shape dominates after the collapse. | AC-4's cost report names the most expensive rule per file, so the next shape is identified from the report. This is the "see where we are" the operator asked for. |
| Fixture content that reproduces the blowup is expensive to run in CI. | The regression fixture is sized to demonstrate super-linear growth, not to reproduce the full 173.6 s. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
