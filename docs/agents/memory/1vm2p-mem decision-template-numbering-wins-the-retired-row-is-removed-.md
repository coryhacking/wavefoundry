# Decision: Template numbering wins; the retired row is removed and the…

Owner: Engineering
Status: superseded
Last verified: 2026-08-17

Memory ID: `1vm2p-mem decision-template-numbering-wins-the-retired-row-is-removed-`
Kind: `decision`
Confidence: 0.6
Created: 2026-08-17
Updated: 2026-08-17
Source exploration cost: 3068146
Source event: `decision-log:1viyt-bug install-log-and-install-seed-reference-drift:be0718480e9dc9dd`
Validation: rewrite
Validated by: agent
Action delta: Never renumber existing install-log template rows (retire a row by removing it and leaving the gap; insert with decimal extension); keep seed-012 headings mirrored to the template's numbered rows with lettered sub-steps, and let the parity and step-mention tests hold both.
Validation rationale: Verified against install/install-log-format.md line 32 ("Existing row numbers are never renumbered"), install_log_lib._ROW_RE and first_unchecked_row (gaps tolerated), the shipped template (rows 2.1..2.11, 2.13..2.15, gap at 2.12), and test_install_log_lib.FreshInstallContractParityTests (seed-ref resolution, one-to-one numbered headings, step-mention resolution). The readiness primer caught the original plan trying to renumber contiguously; the rule and the tests that enforce it are the durable part. Draft target test_install_log_lib.py is one of three; the format contract file and the template are the primary targets.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1vn8p-mem install-log-rows-are-never-renumbered-seed-012-mirrors-the-t`
## Summary

Decision (wave 1viyu): Template numbering wins; the retired row is removed and the gap kept (no renumber, per `install-log-format.md` line 32); seed-012 headings are renumbered to the template with lettered sub-steps for row-less steps; parity and path-resolution tests hold the references.. Rationale: The template is the live state machine operators copy, and `wf_audit_install` returns its row numbers; the shipped row-format contract forbids renumbering existing rows because it invalidates in-progress logs, and the parser tolerates gaps; a test is the only thing that has kept a reference honest in this pack..

## Evidence

- `1viyt-bug install-log-and-install-seed-reference-drift`
- `1viyu`

## Targets

- `test_install_log_lib.py`
