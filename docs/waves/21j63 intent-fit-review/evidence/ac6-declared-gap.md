# AC-6 declared intent gap

Owner: implementer
Status: active
Last verified: 2026-10-24

Written by the coordinator before either AC-6 plan was authored or reviewed. The plans are kept as `.txt` so docs-lint does not read them as wave artifacts: `plan-a-one-command-bootstrap.txt` (expected to show the gap) and `plan-b-one-command-bootstrap.txt` (control).

Subject: a change that gives first-time contributors a one-command local setup on Windows, macOS and Linux.

Declared gap (mis-aimed plan only): no acceptance criterion exercises the setup on native Windows, and none runs it on a clean machine with no prior toolchain. Every AC can pass on a maintainer's already-provisioned macOS or Linux machine while the Product Intent (first-time contributors on all three platforms) is not established.

Pass condition: the qa-reviewer names one or both halves of this gap (Windows not tested; clean or first-time machine not tested) as intent left untested. A generic `does_not` without naming it does not pass. On the control plan, the reviewer raises no intent-coverage finding.
