# Install-log rows are never renumbered; seed-012 mirrors the template and tests hold the parity

Owner: Engineering
Status: active
Last verified: 2026-08-17

Memory ID: `1vn8p-mem install-log-rows-are-never-renumbered-seed-012-mirrors-the-t`
Kind: `decision`
Confidence: 0.9
Created: 2026-08-17
Updated: 2026-08-17
Source exploration cost: 3068146
Source event: `decision-log:1viyt-bug install-log-and-install-seed-reference-drift:be0718480e9dc9dd`
Validation: promote
Validated by: agent
Action delta: Never renumber existing install-log template rows (retire a row by removing it and leaving the gap; insert with decimal extension); keep seed-012 headings mirrored to the template's numbered rows with lettered sub-steps, and let the parity and step-mention tests hold both.
Validation rationale: Verified against install/install-log-format.md line 32 ("Existing row numbers are never renumbered"), install_log_lib._ROW_RE and first_unchecked_row (gaps tolerated), the shipped template (rows 2.1..2.11, 2.13..2.15, gap at 2.12), and test_install_log_lib.FreshInstallContractParityTests (seed-ref resolution, one-to-one numbered headings, step-mention resolution). The readiness primer caught the original plan trying to renumber contiguously; the rule and the tests that enforce it are the durable part. Draft target test_install_log_lib.py is one of three; the format contract file and the template are the primary targets.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

install-log-format.md forbids renumbering existing rows because a renumber invalidates in-progress logs, and install_log_lib tolerates gaps (_ROW_RE accepts any N.M; first_unchecked_row walks document order). Wave 1viyu retired the seed-130 row 2.12 by removal (gap kept), renumbered only seed-012's prose headings to the template's numbers with lettered sub-steps (2.4a/2.4b/2.14a) for row-less steps, and pinned it with FreshInstallContractParityTests (every (seed-NNN) resolves; numbered template rows and seed-012 headings are one-to-one; every "step N.M" mention across seeds resolves). A red-team primer rejected the contiguous renumber the plan first proposed. Rule: retire by removal, insert by decimal extension, never renumber; when the state machine and its mirror seed disagree, the template wins and a parsing test holds both.

## Evidence

- `1viyt-bug install-log-and-install-seed-reference-drift`
- `test_install_log_lib.FreshInstallContractParityTests`
- `install/install-log-format.md line 32`

## Targets

- `.wavefoundry/framework/install/install-log-format.md`
- `.wavefoundry/framework/install/install-log.template.md`
- `.wavefoundry/framework/seeds/012-install-wavefoundry-phase-2.prompt.md`
- `.wavefoundry/framework/scripts/tests/test_install_log_lib.py`
