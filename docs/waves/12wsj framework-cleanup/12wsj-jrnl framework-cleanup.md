# Journal — Framework Cleanup

Owner: Engineering
Status: active
Last verified: 2026-05-25

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-05-25

## Operating Identity

- Role: wave-coordinator — coordinating the two framework-cleanup changes: suppress empty gardener reports and remove pre-v1.0.0 legacy compatibility code.
- Responsibilities include: gate enforcement for seed edits, sequencing the test suite run only after both Scripts and Tests workstreams complete, and ensuring the docs gate passes before closure.

## Salience Triggers

- **High:** Legacy-compat removal (`12wsd`) touches closed wave records or the `Last verified:` date field — those are explicitly out of scope; stop and re-scope.
- **High:** `seed_edit_allowed` gate not opened before editing any seed file for `12vrb` — open before editing, close immediately after.
- **Medium:** Test suite run attempted before both Scripts and Tests workstreams are complete — sequence matters to avoid chasing a moving target.

## Distillation

- **Two independent workstreams:** `12vrb` (suppress empty gardener reports) and `12wsd` (remove legacy compat) are independent and can run in parallel.
- **`12wsd` test sequencing:** run `run_tests.py` only after the Scripts workstream (build_pack.py, check_version.py, upgrade_wavefoundry.py) and the Tests workstream are both done.
- **Docs gate always required:** both changes require `wave_validate` and `wave_garden` to pass before closure is requested.

## Active Signals

wave-id: `12wsj framework-cleanup`

- Created 2026-05-25: two planned changes admitted — `12vrb-enh suppress-empty-gardener-reports` and `12wsd-debt remove-pre-v1-legacy-compat`.

## Promotion Evidence

- Stable artifact: `docs/waves/12wsj framework-cleanup/wave.md`
- No lessons promoted yet; promote at wave closure to `docs/references/project-context-memory.md` if new patterns emerge.

## Retirement And Supersession

- None yet.

## Governance

- No secrets, credentials, or PII in journals.
- Seed edits require the `seed_edit_allowed` gate; framework script edits require `framework_edit_allowed`.
