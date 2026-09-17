# Record The Human Operator On Review Events

Change ID: `1y9su-enh review-event-operator-identity`
Change Status: `complete`
Owner: Engineering
Status: planned
Last verified: 2026-09-17
Wave: `1y9sv review-event-operator-identity`

## Rationale

**Brief.** Goal: review events written to `events.jsonl` (approval, finding, review run) record an available contributor handle beside the role already recorded as `actor`, for reference. This is best-effort attribution from local configuration or an explicit selection, not verified human identity. Audience: teams sharing a target repository; this repository first. Approach: a committed contributors map keyed by git email resolves the handle at write time; an optional explicit handle overrides; the handle is shown in the wave record's review-status text. Constraints: local-only; no email written into the ledger; existing ledgers stay valid; the review-policy receipt chain is untouched; the smallest change that records the fact. Success: a readiness approval recorded on this repository carries `operator.handle` and the review-status table names that handle.

Motivation. `verification_context` carries `actor` (a role such as `wave-council`), `context_id`, `fresh_context`, and `independent`. Nothing names the person, so on a shared repository "who approved this" has no answer inside the framework. A field report (Peng Qian's AIDLC write-up, September 2026) stamped git user and email on every audit entry; the operator here chose a handle with a separate contributors map so no email lands in committed docs. This is a reference field, not a gate: nothing blocks on it.

Verification against the tree (2026-09-17, symbol anchors): `_VERIFICATION_CONTEXT_REQUIRED` in `review_evidence.py` is a closed set and `_require_fields` rejects unknown keys, so the new field must be declared optional or every write fails. `executable_evidence` records require the context; `review_run` records carry it optionally; `review_policy_receipt` and finding-synthesis records do not carry it and are out of scope. `policy_input_digest` in `review_policy.py` hashes config blocks and change-doc bytes only, so a new ledger field does not lapse receipts. No helper reads `git config user.email` anywhere in the scripts; `commit_provenance._git` is the catch-and-return-`None` pattern for git calls. `operator-signoff` at close is a typed approval event checked by `ReviewAuthority.operator_signoff_present`, so it gains the handle for free. The review-status table is rendered by `review_status_human_table` from `review_authority_projection`.

## Requirements

1. A committed `docs/contributors.json` mapping handle to `{"name": "<full name>", "emails": ["<email>", ...]}`. No schema version, no lint rule. Only an absent file resolves as `no_contributors_file`. An unreadable file or invalid JSON/shape returns a distinct explanatory reason; no separate validation service or lint rule is added.
2. A new stdlib-only module `.wavefoundry/framework/scripts/operator_identity.py` exposes `resolve_operator(root, explicit_handle=None)` returning `(operator | None, reason)`, where `operator` is `{"handle": <handle>, "source": "explicit" | "git_email"}` and `reason` is a short human-readable string used only when `operator` is `None`. Order: if an explicit handle is supplied, use it only when present in the valid map; an unknown explicit handle returns unresolved without falling back to another person. With no explicit handle, `git -C <root> config user.email` is read with a catch-and-`None` call in the style of `commit_provenance._git` and matched case-insensitively after stripping whitespace. A missing or malformed map, an unmapped email, an unset email, or an explicit handle absent from the map all return `None` with a reason. An email matching more than one distinct handle returns unresolved with an ambiguity reason; never select by map order. Repeated emails under the same handle are not ambiguous. The function never raises for environmental causes. Read once per new write attempt using a bounded, read-only git call; no network lookup, cache, or persistent identity state.
3. `wf_review_event` gains one optional string parameter `operator_handle`. For `approval`, `finding`, and `run` events the server calls `resolve_operator` and passes the result through `build_identified_review_event` into `build_compact_review_event` as an optional `operator` argument on both functions; the compact builder adds `"operator"` to all four context literals (run, approval, finding evidence, and generated convergence checkpoint) when the value is not `None`. When no operator resolves the record is written without the field and, unless the reason is that the map file is absent, the response carries one warning diagnostic `operator_identity_unresolved` with the reason and the fix. Repositories without the map see no change. The resolved operator and `operator_handle` are excluded from the semantic event payload that feeds `review_event_request_digest`, so the request digest and replay behavior are unchanged by the identity. A replay returns the original stored bundle and its original attribution, without appending, filling in a previously absent handle, or replacing it with the current caller's handle. Replays need no new identity lookup.
4. `review_evidence.py` accepts `operator` as an optional `verification_context` key whose value is an object with exactly `handle` and `source`, validated with the same unknown-field strictness as the parent. Both validator call sites that pass an empty optional set for the context today (`_validate_run_shape` and `_validate_evidence_shape`) reference one new `_VERIFICATION_CONTEXT_OPTIONAL` constant. Existing ledgers validate unchanged. Dry-run shows the field as `create` would write it; identical retries still replay.
5. The review-status table's `Why` text for a current executed approval (the literal `current executed approval follows every affected repair` in `review_authority_projection`) becomes `current executed approval by <handle> follows every affected repair` when the handle is present and is unchanged otherwise. The handle is operator attribution, not evidence that the named human performed or personally approved an agent review; document that distinction. No other projection changes; `wf_review_event(event="list", verbose=true)` already returns full records.
6. `operator_identity` is added to the `sys.modules` eviction set near the top of `server_impl.py` (the block commented "Evict lifecycle-validation modules so tool handlers always pick up the current code on disk after a wf_reload_mcp", which names `review_evidence`, `review_policy`, `lifecycle_lock`, and siblings).
7. `docs/specs/mcp-tool-surface.md` documents the parameter, the field, and the diagnostic in the `wf_review_event` entry. Seed `209-agent-harness-core` gains one row for the optional `operator` field in its verification-context table, edited under the seed gate, and the rendered role docs are regenerated.
8. This repository adds `docs/contributors.json` with the operator's entry.
9. The `wf_review_event` input schema gains exactly `operator_handle`. If the golden tool-surface fixture from `1y0do` exists, it is regenerated as a named task; otherwise a one-line schema assertion in this change's test pins the parameter.

## Scope

**Problem statement:** Review events record a role and a context id but no person.

**In scope:**

- The contributors map and this repository's entry.
- The resolver, the tool parameter, the optional ledger field, the review-status text in `wave.md`, the eviction entry, and the spec and seed rows. The document uses the identity already stored on the review; it does not perform another lookup or add document-wide identity machinery.

**Out of scope:**

- A docs-lint rule for the contributors map; a malformed map degrades to "no identity" with a diagnostic at write time.
- Recording a person on receipts, finding-synthesis records, session handoff, memory records, or Progress Log rows.
- Enforcing that repairer and reverifier handles differ, or any gate keyed on the handle.
- Any GitHub or network lookup.

## Acceptance Criteria

- [x] AC-1: With a map entry matching the fixture's `git config user.email`, `wf_review_event(mode="create")` for an approval, a finding, and a run each writes `verification_context.operator` with that handle and `source: git_email`; `mode="dry_run"` returns the same field without writing. A finding sequence that generates a convergence checkpoint carries the same operator on that checkpoint; all newly constructed contexts in the bundle retain attribution.
- [x] AC-2: With the map present and an unmapped email, and separately with `user.email` unset, the record is written without `operator` and the response carries `operator_identity_unresolved` with a reason; with no map file the event writes with no diagnostic and no field. An unreadable or malformed map, a failed git lookup, and an email shared by two distinct handles each leave the event writable without identity and produce one explanatory warning. Duplicate emails within one handle still resolve.
- [x] AC-3: `operator_handle` naming a mapped handle writes `source: explicit`; an unmapped explicit handle writes the event without the field and reports `operator_identity_unresolved`.
- [x] AC-8: For approval, finding, and run events, identity does not change `request_digest`. A public-path create attributed to A followed by the identical request under B replays the original bundle, retains A, and leaves ledger bytes unchanged; the same holds when the original event had no handle and a retry can resolve one. The returned records show the retained attribution, not the retry caller.
- [x] AC-4: Every existing `events.jsonl` under `docs/waves/` in this repository validates unchanged through `read_review_event_ledger`, and a record whose `operator` object carries an extra key is rejected with the parent's unknown-fields error shape.
- [x] AC-5: After an approval carrying a handle, the review-status `Why` cell reads `current executed approval by <handle> follows every affected repair`; without a handle the cell is byte-identical to today's text.
- [x] AC-6: The review-policy receipt id for a readied fixture wave is identical before and after recording an approval with the handle, and after `wf_reload_mcp` a modified `operator_identity.py` is served.
- [x] AC-7: The `wf_review_event` schema gains exactly `operator_handle` (optional string) and no other tool schema changes; the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Write `operator_identity.py` and unit tests covering each `source` value, including missing/invalid/unreadable maps, an ambiguous email, repeated emails within one handle, and a git call that fails.
- [x] Add `_VERIFICATION_CONTEXT_OPTIONAL` and reference it from `_validate_run_shape` and `_validate_evidence_shape`; thread the optional `operator` argument through `build_identified_review_event` and `build_compact_review_event`, covering all four context literals; tests.
- [x] Add `operator_handle` to `wf_review_event`, call the resolver, pass the result to the builder outside the digest payload, emit the diagnostic; add the AC-8 public-path replay tests.
- [x] Update the approval `Why` text in `review_authority_projection`, rendered by the existing `review_status_human_table`.
- [x] Add `operator_identity` to the eviction block and extend the reload test.
- [x] Add `docs/contributors.json`.
- [x] Update `docs/specs/mcp-tool-surface.md`; open the seed gate, add the seed-209 row, re-render, close the gate.
- [x] Regenerate the golden fixture or add the schema assertion per Requirement 9.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` last and record the receipt.


## Agent Execution Graph


| Workstream     | Owner       | Depends On   | Notes |
| -------------- | ----------- | ------------ | ----- |
| resolver       | implementer | —            | module and unit tests |
| ledger-tool    | implementer | resolver     | optional key, parameter, diagnostic, Why text, eviction |
| docs-seed      | implementer | ledger-tool  | spec entry, seed row under gate, contributors file |
| verify         | qa          | docs-seed    | AC fixtures, schema pin or golden regen, receipt |


## Serialization Points

- `.wavefoundry/framework/scripts/operator_identity.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`
- `.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md`
- `docs/contributors.json`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

N/A. One optional field on an existing record shape, one small reader, no boundary or flow change; the ledger authority model is unchanged.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The outcome the change exists for |
| AC-2 | required  | Missing identity must never block a review write |
| AC-3 | important | The override is a convenience, not the main path |
| AC-4 | required  | Existing ledgers are the authority and must keep validating |
| AC-5 | required  | The handle is useless if nothing shows it |
| AC-6 | required  | Receipt stability and reload freshness |
| AC-7 | required  | One intentional public-surface change plus standard change-local verification |
| AC-8 | required  | Identity must not turn a replayed retry into a conflicting write |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-09-17 | Change planned after evaluating the AIDLC field report; operator chose handle plus contributors map over name and email in the ledger | this document; `docs/agents/session-handoff.md` |
| 2026-09-17 | Operator direction: keep it as simple as possible, reference only. Dropped the docs-lint validator, the schema version, the list-projection and human-table changes, the hard error on unknown explicit handle, and the architecture-doc updates | this document |
| 2026-09-17 | Prepare council repairs: named the two validator call sites and the one shared optional-set constant; named `build_compact_review_event` and its three context literals as the insertion point; excluded the identity from the request-digest payload and added AC-8; collapsed the `source` enum to `explicit` and `git_email` with a free-text reason for unresolved cases. Refuted: the red-team claim that no reload eviction block exists at the top of `server_impl.py`; the block commented "Evict lifecycle-validation modules" is there and Requirement 6 now quotes it | council seat outputs; `review_evidence.py` `_VERIFICATION_CONTEXT_REQUIRED` call sites; `server_impl.py` eviction block |

| 2026-09-17 | Operator requested simple best-effort attribution. Resolved plan-review items: thread identity through the identified builder and all four contexts; distinguish absent from broken maps; refuse ambiguous attribution without refusing the event; retain original attribution on replay and verify through the public path. Documents reuse the ledger projection; no additional identity infrastructure or authority checks | Requirements 1–5, AC-1/2/8, Scope and Tasks; current builder and handler inspection |
| 2026-09-17 | Readback / Thought: implement AC1–8 with one best-effort local lookup, optional ledger context and existing document projection. Preserve digests, replay attribution and role authority. Sequence: resolver + ledger on disjoint worker paths, server integration/spec/seed here, focused public checks, full suite. No document-wide authoring system | successful Prepare and activation; independent readiness approvals |
| 2026-09-17 | Observe: resolver 9 tests and ledger 160 tests passed; public integration 7 tests and receipt-stability fixture passed. All 140 existing ledgers parse unchanged; before/after comparison of 90 tool schemas shows exactly optional operator_handle. Agent renderer ran with no changed surfaces (existing role pointers already reference seed209). AC1–6/8 verified; AC7 and full-suite task remain pending | test_operator_identity; test_review_evidence.OperatorReviewEvidenceTests; test_review_operator_integration; TypedExclusiveGateDerivationTests.test_operator_attribution_keeps_prepared_policy_receipt_current |
| 2026-09-17 | Guard evidence: 13 in-memory ledger mutations caught (optional allowance, forwarding, nested validation and four context omissions); 6 resolver mutations caught (blank handle, explicit fallthrough, ambiguous selection, Git redirection, timeout, propagated decode failure). Initial public replay fixture reused a finding id and correctly hit lifecycle refusal; fixture corrected to distinct ids, all pass | worker mutation probes; named tests in owned suites; no source mutants persisted |
| 2026-09-17 | Reflect / repair: full suite exposed required stdin isolation and Windows console suppression on Git lookup, plus exact schema/advisory inventories and a contiguous reload census. Added isolation kwargs and tests, updated only the admitted inventories, moved eviction entry to preserve unrelated census. Thirteen focused checks pass. Many initial suite failures came from CommandLineTools Python3.9 shadowing venv Python3.13 in child commands; corrected PATH and reran full suite | /private/tmp/1y9sv-repair-tests.log; /private/tmp/1y9sv-full-tests-final.log; existing guard test names |
| 2026-09-17 | Host-access full suite: 9147 tests, only unrelated setup fixture failed because installed uv changed its expected pip command. Dashboard native checks and timing-sensitive TechDocs test passed outside sandbox. Setup fixture passes with an isolated Python3.13/Git PATH without uv; final full run uses that environment. No unrelated tests or production paths changed to obtain a pass | /private/tmp/1y9sv-host-tests.log; test_setup_index.SetupIndexTests.test_install_deps_invokes_pip_via_venv_python |
| 2026-09-17 | Implementation verification complete: 9147 tests across 97 files, 17 skips, result ok; receipt input hash independently recomputed and matches 416da29caabc905cd8ecfa498133132b45467858290977f72fecceb2ae4a529a. Host access with isolated Python3.13/Git PATH; no native Windows/Linux execution claimed. All ACs/tasks complete; delivery review and operator closure remain pending | .wavefoundry/framework/test-cache.json; /private/tmp/1y9sv-qualified-tests.log |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-09-17 | Contributor handle resolved from a committed map keyed by git email, with an optional explicit override | Operator decision. Keeps email out of committed ledgers, gives a stable short identity, needs no per-machine setup beyond the git email people already have | (a) Write `git config user.name` and `user.email` inline, as the AIDLC field report does: zero setup, but copies email into every committed ledger. (b) A `git config wavefoundry.handle` key: no lookup, but per-machine setup and silent typos. (c) GitHub username via `gh`: network, against the local-only principle |
| 2026-09-17 | Unresolved identity never refuses an event; warn for configuration problems, remain silent when the map is absent | The field is for reference. A refusal would turn a convenience into a gate and block reviewers on fresh clones | Refuse on unknown explicit handle: catches typos, but adds an error path to a reference field |
| 2026-09-17 | No docs-lint rule for the map | A malformed map already degrades to "no identity" with a diagnostic at the one place it is read; a second validator is duplication | Lint the map: earlier feedback, more code |
| 2026-09-17 | Handle lives in `verification_context.operator`, not top-level | It qualifies the claim the context already makes and reuses the existing closed-object validation | Top-level `operator`: a second identity surface beside `event_identity.actor` |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A contributor's git email differs between machines | The map allows several emails per handle; the diagnostic names the fix |
| The new optional parameter changes the golden tool surface | Requirement 9 names the regeneration or pins the schema |
| Someone passes another person's handle explicitly | `source: explicit` is recorded so a reader can tell it from a git-derived handle; this is a reference field, not a gate |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
