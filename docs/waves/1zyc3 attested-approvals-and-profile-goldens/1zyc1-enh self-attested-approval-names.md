# Approvals Carry No Person Name

Change ID: `1zyc1-enh self-attested-approval-names`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-06
Wave: 1zyc3 attested-approvals-and-profile-goldens

## Rationale

Downstream request (Waveforge, workflow seams 2026-10-01 #7): approvals should say which person recorded them. Today a review-ledger record carries the lane role (`verification_context.actor`) and, when `docs/contributors.json` resolves one, an operator handle (`verification_context.operator: {handle, source}`, from `operator_identity.resolve_operator`), but never a person's name. Waveforge keeps self-attestation as a process control. The operator chose self-attested names: the name is what the recording person states, with no signing or verification.

## Requirements

1. `wf_review_event` gains an optional `attested_by` input: the name the recording person states for themselves. It is recorded only when explicitly supplied; there is no default from `docs/contributors.json`, git or anywhere else, so every recorded name was stated by the caller.
2. Validation runs at request time, before the replay branch in `wf_review_event_response`, and refuses with a typed diagnostic (nothing written) a name that, after NFC normalization and trimming surrounding spaces, is empty or longer than 100 code points, or contains any Unicode `Cc`, `Cf` or `Cs` (lone surrogate) character (including the bidi controls U+202A-U+202E and U+2066-U+2069, zero-width U+200B-U+200D and U+FEFF), U+0085, U+2028, U+2029, or any of `<`, `>`, a backtick, `|`, `[`, `]` or a backslash (characters that would break or inject into the markdown projection). The stored value is the normalized, trimmed name.
3. The name is passed to `build_identified_review_event` / `build_compact_review_event` as a keyword argument like `operator` (never through the semantic event), so it stays outside the request digest: a replay returns the original attribution, a retry with a different name is not an identity conflict, and when a replay's supplied name differs from the stored one an advisory diagnostic says so. `attested_by` is added to the set of keys `evidence` may not supply, so it cannot enter the digest through `evidence`.
4. It is recorded as an optional `verification_context.attested_by` string on every record the builder writes (run, approval, finding evidence, convergence checkpoint), added to `_VERIFICATION_CONTEXT_OPTIONAL` and validated by the same rules when ledgers are read. Ledgers without the key stay valid and render exactly as today.
5. Projection: the approval row's `why` text reads `... by <name> (<handle>)` when both exist, `... by <name>` with only a name, and `... by <handle>` unchanged with only a handle, so existing projections do not drift. This reaches the `wave.md` table, `wf_review_wave`, `wf_close_wave` status and the dashboard.
6. Approval validity, close gates and readiness are unchanged; `operator_identity.resolve_operator` is unchanged.
7. `docs/specs/mcp-tool-surface.md` (the operator-identity paragraph) states the field is self-attested and unverified, recorded only when supplied, and that names then appear in the committed ledger and `wave.md`. The `wf_review_event` docstring and a CHANGELOG Added bullet under `## [1.29.0]` describe it; the bullet notes that a ledger with the key is read as invalid by framework versions before 1.29.0 (as the `operator` key was for its predecessors).

## Scope

**Problem statement:** approvals cannot be attributed to a person.

**In scope:**

- The input, validation, record field, projection, docs and tests.

**Out of scope:**

- Signed or verified identity.
- Any derived or default name.
- Back-filling names into existing ledgers.

## Acceptance Criteria

- [x] AC-1: An approval recorded with `attested_by="Ada Lovelace"` stores it in `verification_context.attested_by`; the review table shows `by Ada Lovelace (<handle>)` (or `by Ada Lovelace` without a handle); replaying the same event with another name returns the original record with an advisory and no conflict.
- [x] AC-2: Without `attested_by` no name is recorded, the row renders exactly as today, and `resolve_operator` behaves as before.
- [x] AC-3: Each invalid name class in Requirement 2 is refused with a typed diagnostic before any write or replay; `evidence={"attested_by": ...}` is refused; an older ledger without the key still validates and closes.
- [x] AC-4: The pinned `wf_review_event` schema tests and the tool-surface golden include the new input; docs and the CHANGELOG bullet describe it as self-attested and note the older-version read; the change's own tests pass and no failure elsewhere is attributable to this change.

## Tasks

- [x] Input and request-time validation (before replay), evidence-key protection
- [x] Record field via keyword argument, validators, replay advisory
- [x] Projection text
- [x] Docs, golden fixture, pinned schema tests, CHANGELOG
- [x] Tests

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| attested-names | implementer | — | |


## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/tests/test_review_evidence.py`, `.wavefoundry/framework/scripts/tests/test_review_operator_integration.py`, `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`, `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`, `.wavefoundry/framework/scripts/tests/fixtures/tool-surface-golden.json`, `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

N/A: an optional attribution field on an existing record; no boundary, flow or ownership change.

## Platform Behavior

Pure data handling; identical on Windows, macOS, Linux and WSL2 (NFC normalization and the character checks use `unicodedata`). No new subprocess or network use.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | the requested attribution |
| AC-2 | required | no name unless stated; nothing else changes |
| AC-3 | required | safe input and old-ledger compatibility |
| AC-4 | required | contract, docs and release notes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-06 | Implemented: optional `attested_by` on `wf_review_event`, NFC-normalized, trimmed and refused (`invalid_attested_by`) before any write or replay; `attested_by` protected from `evidence`; recorded via a builder keyword argument on run, approval, finding and convergence-checkpoint contexts; validated as stored on read (no re-normalization); advisory `attested_by_replay_mismatch` on replay; approval `why` renders name and handle; spec, docstring, CHANGELOG; shipped golden regenerated | scratch copy: test_review_evidence 183 OK, test_review_operator_integration 13 OK, test_server_tools_retrieval 1044 OK, test_server_tools_lifecycle 612 OK (sanctioned advisory set extended), test_tool_surface_golden OK; mutation probes all caught: read validation dropped (test_stored_name_is_validated_on_read_without_renormalizing fails), name put into the server request digest (replay test fails), name put into the builder digest (digest test fails), request-time refusal disabled (refusal test fails) |
| 2026-10-06 | Gapfill: shell grep/sed used alongside MCP code tools to read long contiguous regions of `review_evidence.py`, `server_impl.py` and the test files for editing | implementer session |
| 2026-10-06 | Readiness review folded in: no default name (B1, B3); request-time validation before replay, with `Cc`/`Cf`, bidi, zero-width, line separators and markdown-breaking characters refused (B2, N4); keyword-argument path and evidence-key protection (N3); handle-only rendering unchanged (N2); pinned schema tests added to serialization (N1); older-version read noted (N5) | readiness review |
| 2026-10-06 | Planned from Waveforge Part 3 #1; operator chose self-attested names | identity map of `review_evidence` and `operator_identity` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-06 | Record a name only when the caller supplies `attested_by`; no default | a derived name (from `docs/contributors.json`) would be presented as self-attested though no one stated it, and would put a name on every agent approval; this narrowly revisits the 1y9su decision (handle, not name, in the ledger) only for names a person chooses to state | default from the contributors map; git `user.name`; signed approvals |
| 2026-10-06 | Delivery review: also refuse lone surrogates (`Cs`), `[`, `]` and a backslash, beyond Requirement 2's minimum set | a lone surrogate passed validation and then raised an untyped encoding error on write; bracket and backslash allow Markdown link syntax in the `wave.md` table and the approval text | escape the name at projection time (more code, two render sites) |
| 2026-10-06 | Keep the name outside the request digest | matches `operator`; replays and retries stay stable | digest it |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A name in a committed ledger is personal data | recorded only when the person states it; the spec says so |
| Markdown or bidi injection through the name | request-time refusal of `Cc`/`Cf`, line separators, `<`, `>`, backtick and pipe |
| A pre-1.29 framework reads a ledger with the key as invalid | stated in the CHANGELOG, as for the `operator` key before it |
| Readers mistake it for verified identity | spec and projection call it self-attested |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
