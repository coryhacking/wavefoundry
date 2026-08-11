# Review Authority Silently Downgrades On An Unreadable Wave Record

Change ID: `1v1de-bug review-authority-downgrades-on-unreadable-wave-record`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-11
Wave: 1v1di authority-receipt-and-dashboard-hardening

## Rationale

`resolve_review_authority` is the single review-authority facade (`1to78`): every gate surface derives signoff currency from its result. Executed against today's tree: its wave-record read wraps only `OSError` and substitutes `wave_text = ""` on failure, so a permission-unreadable `wave.md` parses as an empty document, `parse_review_evidence_source` finds no declaration, and the wave is classified `typed=False`: **legacy prose authority with empty text**. Every prose signoff then reads as absent, so gates report missing approvals instead of an unreadable record, and the events ledger sitting beside the unreadable record is never consulted. The decode cause is worse in a different way: `UnicodeDecodeError` is not an `OSError`, so it raises out of the facade uncaught.

This is a review-authority downgrade, the exact fail-open class `1tomw` eliminated and `1to78` centralized the facade to prevent. Wave `1uzwh` bounded the exposure: every tool entry now gates on the wave-record seam before reaching the facade, so the reachable windows are post-gate races and direct library consumers. The `1uzwh` delivery-council synthesis (the `wave-council-delivery` ledger record, carry-forward list: "review_evidence authority fail-open shapes") records it as the carried-forward residue of that wave; this change retires it. The sibling read in `validate_external_review_evidence` already fails closed for both causes but renders `{exc}` verbatim, embedding the absolute path in `authority_errors` prose (the same leak idiom repaired at the ledger-read site during `1uzwh` delivery).

## Requirements

1. **An unreadable wave record is never classified as legacy authority.** `resolve_review_authority` catches `(OSError, UnicodeError)` at its wave-record read and returns a structured unreadable-authority result: distinguishable from both `typed=False` (legacy) and a healthy typed result, carrying the cause path-free. The shape follows `validate_external_review_evidence`'s existing `authority_errors` fail-closed pattern rather than inventing a third convention.
2. **Consumers fail closed on the new result.** The census enumerates every `resolve_review_authority` consumer by OBJECT FLOW, not call sites alone (a readiness-council correction): the six `1to78` gate surfaces plus every helper the returned `ReviewAuthority` flows into. The named fail-open hazard is `_required_wave_council_signoffs`' close carve-out predicate, `current_policy_receipt(authority.records) is None and not authority.ledger_errors` (the `1upba` Requirement 9 shape): an unreadable-authority result that presents with empty `ledger_errors` reads as "never prepared under policy" and DROPS the readiness key from the close roster, which is more permissive than today's downgrade. The result shape must therefore satisfy that predicate safely (typed-with-errors), and the census verifies each consumer, recording which are reachable without a prior seam gate.
3. **The `validate_external_review_evidence` message goes path-free.** Its unreadable-record branch renders the file name plus `strerror` (or the exception type when `strerror` is absent), the same idiom its ledger-read sibling gained at `1uzwh` delivery. `authority_errors` semantics are otherwise unchanged.
4. **No behavior change for readable records**, legacy and declared both: the existing `review_evidence` corpus of validity states is unchanged, per the executed derive-states protocol from `1v0lz` (real ledger corpus, old code from a clean extract vs new working tree, zero state diffs).

## Scope

**Problem statement:** the one function every review gate trusts to classify authority silently reclassifies an unreadable declared wave as legacy prose with empty text on the permission cause, and crashes on the decode cause.

**In scope:** the wave-record read and result shape in `resolve_review_authority`; the consumer census and any consumer that needs the distinguishable handling; the `validate_external_review_evidence` message; red-first tests for both causes.

**Out of scope:** the events-ledger read paths (already fail-closed with path-free messages after `1uzwh` delivery); the wave-record seam in `server_impl.py` (`1v0lw`, shipped); any change to how readable records classify.

## Acceptance Criteria

- [x] AC-1: A permission-unreadable `wave.md` at `resolve_review_authority` yields the structured unreadable-authority result, reproduced **red-first**: today it returns `typed=False` with empty `wave_text` (the silent legacy downgrade), asserted on the result shape before and after.
- [x] AC-2: An undecodable `wave.md` yields the same structured result, reproduced **red-first**: today `UnicodeDecodeError` raises out of the facade.
- [x] AC-3: The `validate_external_review_evidence` unreadable message names the file and the cause and carries no absolute filesystem path, red-first with a reach guard (the fixture must demonstrably hit the unreadable branch before the leak assertion counts).
- [x] AC-4: The object-flow consumer census (Requirement 2) is recorded in this document, and each consumer reachable without a prior seam gate has a test pinning its fail-closed outcome, including a test that an unreadable wave record does NOT drop `wave-council-readiness` from the close roster via the `_required_wave_council_signoffs` carve-out predicate.
- [x] AC-5: Readable-record classification is unchanged across the real ledger corpus (executed derive-states comparison, zero state diffs) and the existing `review_evidence` suite.
- [x] AC-6: The full framework suite and docs-lint pass.

## Tasks

- [x] Red-first tests: both causes at the facade; the leak assertion with reach guard.
- [x] Structured unreadable-authority result; consumer census recorded; consumers verified or fixed.
- [x] Path-free message at `validate_external_review_evidence`.
- [x] Derive-states corpus comparison; full suite; docs-lint.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| red-tests | implementer | — | Both causes, facade-level |
| facade | implementer | red-tests | Result shape per the existing authority_errors pattern |
| census | implementer | facade | Consumers verified; reachability recorded |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`

## Affected Architecture Docs

`N/A` with rationale: the review-authority flow in `docs/architecture/data-and-control-flow.md` already describes fail-closed authority handling; this change makes one classifier conform to the documented contract rather than moving any boundary.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect: a review-authority downgrade on the routine failure cause. |
| AC-2 | required | The crash half of the same defect. |
| AC-3 | required | The `1uu9z` leak class must not survive in authority prose. |
| AC-4 | required | The facade serves every gate; an unverified consumer is the next silent downgrade. |
| AC-5 | required | The classifier is verified territory; this change must not move any readable-record outcome. |
| AC-6 | required | Standard gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-11 | Planned from wave `1uzwh`'s carried-forward findings (delivery-council synthesis carry-forward list). Premises executed before authoring: the facade's read wraps `OSError` only and substitutes empty text (source read at `resolve_review_authority`'s wave-record read); `parse_review_evidence_source("")` yields `typed=False`; `validate_external_review_evidence` catches both causes but renders `{exc}` verbatim (source read at its unreadable branch) | executed source reads and the 1uzwh ledger synthesis, 2026-08-11 |
| 2026-08-11 | Readiness council (red-team and docs-contract seats): both facade premises re-executed independently (both causes probed; the decode escape and empty-text downgrade confirmed; the leak confirmed with the note that the decode message carries neither path nor filename). Council correction folded pre-receipt: the consumer census re-scoped from call sites to OBJECT FLOW, because the one consumer where a wrong result shape is fail-OPEN is not a call site: the close carve-out predicate in `_required_wave_council_signoffs` would drop the readiness key from the close roster if the unreadable result presented with empty `ledger_errors`. Requirement 2 and AC-4 now name the predicate and the safe shape | seat reports, executed probes P1-P3 and the six-site call sweep, 2026-08-11 |
| 2026-08-11 | Object-flow consumer census (AC-4), recorded before the first code edit. Production `resolve_review_authority` call sites, each passing pre-read seam text (`wave_text=`), so the facade's internal wave-record read is defense-in-depth today, reachable only through direct library consumers and post-gate races: `server_impl.py` 2666 inside `_required_wave_council_signoffs` (fed by 15443 guided-phase signoff roster, 16454 prepare, 16813 `_evaluate_shared_delivery_state`, 17424 implement gate 1), 16453 prepare authority, 16807 `_evaluate_shared_delivery_state`, 16982 shared review/prepare responder, 17422 implement gate 1, 17475 implement gate 2. The returned `ReviewAuthority` flows into `signoff_current`, `signoff_recorded`, `operator_signoff_present`, `evidence_present`, `any_signoff_evidence`, and `max_severity` (all fail closed on the typed-with-errors shape: empty `records` derive pending/absent/none), plus direct field reads of `records` and `ledger_errors` in the close carve-out predicate. Dispositions: (a) close carve-out predicate (`server_impl.py` ~2696): the typed-with-errors shape keeps `wave-council-readiness` on the close roster because `ledger_errors` is nonempty; pinned by a dedicated test. (b) `_wave_uses_external_review_evidence` (~15145): returns False (legacy) on a failed seam read; deliberate 1v0lw behavior since callers gate on their own record read first; recorded, not changed. (c) `_required_wave_council_signoffs` targeted-delivery branch (~2639) discards `read_review_event_ledger` errors; behind the 1v0lw seam gates at every tool entry; recorded, not changed. (d) an unreadable LEGACY wave reclassifies from silent legacy-empty to typed-with-errors (its declaration is unknowable); gate outcomes are identical (every approval reads absent either way); only the remediation nuance changes, naming an unreadable record instead of missing approvals. Also folded under AC-3's spirit as a census item: `_review_authority_path_error` renders `{exc}` verbatim and leaks the absolute path for a permission-broken wave DIRECTORY through both the ledger and validation paths; repaired with the same strerror idiom | executed call-site sweep (`code_keyword` on `resolve_review_authority`) and source windows at `server_impl.py` 2600-2720, 15130-15170, 16430-16470, 16795-16825, 16970-16990, 17405-17485, 2026-08-11 |
| 2026-08-11 | Red-first evidence, all four defects executed before any production edit (probe script plus the new tests run against the unmodified tree): permission cause at the facade returned `typed=False`, `wave_text=''`, `ledger_errors=()` (the silent legacy downgrade, AC-1 red); decode cause raised `UnicodeDecodeError` out of the facade (AC-2 red, also red through `_required_wave_council_signoffs`); `validate_external_review_evidence` rendered the absolute path on the permission cause and no filename on the decode cause (AC-3 red); `_review_authority_path_error` leaked the absolute path for a permission-broken wave directory AND a symlink-loop parent through both the ledger-read and validation paths (census leak red, four subTest cases); the close roster dropped `wave-council-readiness` to `['wave-council-delivery']` on a permission-unreadable record (AC-4 red, the named fail-open). Fix landed in `review_evidence.py` only: shared `_unreadable_wave_record_error` helper (file name plus strerror-or-type-name), facade catch `(OSError, UnicodeError)` returning `ReviewAuthority(typed=True, wave_text='', records=(), ledger_errors=(message,))`, the same message at the validator's unreadable branch, and the path-free strerror idiom (failing member name plus cause) at `_review_authority_path_error`; no `server_impl.py` consumer change needed, matching the census expectation. All new tests green after the fix | probe output and red runs recorded in-session 2026-08-11; tests `tests.test_review_evidence.ReviewAuthorityFacadeTests` (4 new tests) and `tests.test_server_tools.WaveCouncilPolicyTests.test_an_unreadable_wave_record_does_not_drop_the_readiness_key` (both causes) |
| 2026-08-11 | AC-5 corpus comparison executed THROUGH the facade per wave (not the 1v0lz ledger-only derive-states, which is vacuous for the facade): for every `docs/waves/*/wave.md` the script resolves `resolve_review_authority(root, wave_dir)` with the facade doing its own record read, and derives typed flag, `ledger_errors`, record count, `evidence_present`, `any_signoff_evidence`, `operator_signoff_present`, `max_severity`, and per-key `signoff_current`/`signoff_recorded` for both approval phases plus the prose prepare section across five canonical keys. Before side: byte-copy of the pre-edit working-tree scripts (taken before the first edit, since HEAD predates the uncommitted 1uzwi/1uzwh deliveries; the copy isolates exactly this change). Result: 215 waves (75 typed, 140 legacy), 6880 derived state fields, zero diffs, output byte-identical. File-scope verification: `tests.test_review_evidence` 156 tests OK, `tests.test_dashboard_server` 189 tests OK (1 environment skip), `tests.test_server_tools` 1680 tests OK in a single module run (338.9s); the wave-level suite row below carries the full-suite tally | `derive_authority_states.py` with `states_before.json`/`states_after.json` in session scratch, `diff -q` byte-identical, 2026-08-11 |
| 2026-08-11 | AC gate evidence (coordinator, shared across the wave's three docs): full framework suite via `run_tests.py` reports 7129 tests across 62 files, OK, rc=0 captured unpiped; `wf_validate_docs` passed with zero warnings after the readiness seat-evidence rows were recorded. Independently re-executed by the delivery docs-contract seat: same 7129/62 OK rc=0 and "docs-lint: ok" | run_tests.py 2026-08-11 rc=0; wf_validate_docs 2026-08-11; docs-contract seat rerun 2026-08-11 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-11 | Reuse the existing `authority_errors` fail-closed shape rather than a new result type | One authority, one failure convention; `validate_external_review_evidence` already models it and consumers already understand it | New enum or exception type (rejected: a third convention in the same file is drift fuel) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A consumer treats the new unreadable result as legacy by falling through a `typed` check | The census (AC-4) enumerates consumers and pins the reachable ones; the result shape must make the naive `if not authority.typed` branch safe, not just documented |
| Changing the facade shape breaks the six gate surfaces | AC-5's corpus comparison plus the full suite; the `1to78` residue census test constrains consumers to the facade already |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
