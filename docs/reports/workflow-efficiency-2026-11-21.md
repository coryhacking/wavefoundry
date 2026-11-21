# Where Wavefoundry can shorten delivery

Owner: Engineering
Status: active
Last verified: 2026-11-21

**Run the inexpensive contract checks before the full suite, give each distinct defect one repair, and reuse the resulting qualification.** These changes address work we repeated today. The independent checks on upgrade recovery, permissions and shared workspace ownership found defects worth their cost.

## What we reviewed

The November 21 release work spans five waves and 15 specs. The first two waves closed today and include work begun earlier. Counts below cover each wave’s history. A finding is one distinct ledger ID. A ledger row is neither a review round nor an agent invocation.

| Wave | Specs | Findings | What the review taught us |
| --- | ---: | ---: | --- |
| [23z45, field correctness](<../waves/23z45 field-feedback-correctness/wave.md>) | 4 | 10 | The Windows branch needed an explicit limit on what a simulated run establishes. |
| [23z46, installation and upgrades](<../waves/23z46 install-and-upgrade-friction/wave.md>) | 4 | 22 | Testing old runners exposed cases where an upgrade promise was unachievable. Run those fixtures before settling the acceptance criteria. |
| [23zbf, setup and permissions](<../waves/23zbf upgrade-setup-and-permission-follow-ups/wave.md>) | 5 | 10 | The proposed permission tier depended on what the mark tools actually enforced. Review found closed-record, deferral and checklist defects. A delivery probe also caught concurrent writes. |
| [23zbg, planning and review guidance](<../waves/23zbg review-and-planning-guidance/wave.md>) | 1 | 4 | Three finding IDs described the same missing seed marker. The fourth concerned the authority and scope of a classification ruling and deserved its own repair. |
| [23xo7, awaiting closure](<../waves/23xo7 awaiting-closure/wave.md>) | 1 | 5 | Every delivery finding concerned a test or contract check. The registered two-wave tests established that closing A preserves B’s work on refusal, success and retry. |

## Change what we do on the next wave

1. **Run focused contract checks before final review and qualification.** For 23xo7 the first full run took 831 seconds and failed in five files. The repaired run took 754 seconds and passed the same 13,193 tests. Three concerned an outdated fixture-call count, a mock whose positive path the test never exercised, and an obsolete vocabulary exemption for a deleted comment. One exposed a vocabulary reader the checker could not recognize. One test depended on the old spelling of a refresh call. The implementer can run the affected lifecycle, vocabulary, fixture and handler checks together and repair them before freezing the candidate. That first run cost 13 minutes 51 seconds. This is the upper bound on the saving for this case, before paying for the focused checks. A full run still qualifies the finished tree.
2. **Give reviewers one shared regression example and distinct questions.** For a permission change, start with the real write and the records it must preserve. For an upgrade, exercise an older installed runner with a live document, a closed record and a recovery case. For named closure, use a paused delivery and a different active owner. QA checks outcomes, architecture checks ownership across scopes, and security checks authority where applicable. Each reviewer can add an independent counterexample. One person can collect the same baseline output for everyone.
3. **Group findings by cause before assigning repairs.** On 23zbg one missing marker generated three finding histories. Reviewers can independently report what they observed, then the coordinator can attach their lanes to one finding when the failing input, required fix and expected outcome coincide. Keep separate IDs when those differ. Reverify the affected lanes from the existing review recommendation. Reserve another full council for the policy or a genuine change in the review boundary.
4. **Match the evaluation to the claim.** In 23zbg the prior and revised instructions both passed all six comparison scenarios. That result supports preserving behavior on those scenarios. It cannot establish better downstream performance. Stop that comparison once it stops distinguishing the versions. To measure improvement, use a sanitized case that produced the original mistake or observe whether it recurs in the next downstream use. Keep a distribution-specific rehearsal for renames and aliases, where the default repository cannot supply that evidence.

## Where our coordination added work

I started the first full run on 23xo7 while delivery reviewers were still checking the same files. Once they found a defect and the tree changed, that run could only diagnose problems. Five late findings then produced 15 successive finding records across discovery, repair and verification. The fixes needed testing. Earlier focused checks could have kept them in the ordinary implementation loop. For the next wave, the implementer should finish the affected checks and hand off one result. One coordinator should monitor the full run and share its receipt. Reviewers can use the time for independent behavior probes without polling the same suite.

The request to work on multiple waves also illustrates where simplicity pays. Reusing the existing paused status avoided another lifecycle transition. A guidance-only change, however, would have left the tool recommending Resume for completed work and allowed Close A to clear B’s session state. The registered two-wave check established exactly which code needed to change. Scope similar requests by identifying the smallest observable operator outcome before commissioning cross-cutting changes.

## Small framework changes worth considering

- **Route changed files to the existing fast checks.** Start with the few files that account for today’s misses. Offer one focused test invocation when a change touches lifecycle readers, served handlers or their fixtures. Print which contract selected each test. Pilot this as advice alongside the current full-suite gate and measure how often a later full run still finds something the focused run missed.
- **Make the compatibility fallback explain itself.** The release inventory classifies 188 workers, while this checkout discovers 253. Both alternate profiles ran all 253. The renamed run took 823 seconds and the distribution-tool run took 767 seconds. All three release profiles passed on the same framework tree, and the release gate reused the executed default report. The inventory explicitly exempts only one inexpensive worker. Refreshing its counts alone buys little. First report the fallback reason, then examine the slowest tests for genuinely profile-independent inputs. Demonstrate skip parity and detection of a broken renamed profile against the full reference matrix before reducing coverage. [Qualification selector](../../.wavefoundry/framework/scripts/tests/record_layout_support.py)
- **Benchmark scheduling before changing it.** Replaying the 253 measured worker durations from the green run with six workers gives approximately 754 seconds in alphabetical order and 609 seconds with longest first. This calculation holds each duration constant and excludes contention changes. Earlier controlled runs measured alphabetical scheduling faster. The existing scheduling experiment can test today’s much larger suite on the same machine and frozen tree. A scheduler change would still run every test. [Runner scheduling and prior measurements](../architecture/testing-architecture.md)

## How to tell whether this helps

For the next three comparable waves, record time to a green full run, the number of full attempts on distinct trees, unique root causes, and first discoveries by the full suite or an independent reviewer. Keep the existing gates during the trial. Run the release matrix once on the final framework revision and reuse the exact default report. The framework’s estimated context savings do not measure reviewer cost or wall time, so they cannot establish that the process got faster.
