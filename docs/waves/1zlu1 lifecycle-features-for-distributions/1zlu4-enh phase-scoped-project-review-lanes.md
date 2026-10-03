# Phase-Scoped Project Review Lanes

Change ID: `1zlu4-enh phase-scoped-project-review-lanes`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-02
Wave: 1zlu1 lifecycle-features-for-distributions

## Rationale

`docs/workflow-config.json` `required_review_lanes` names project lanes that every wave must pass, and today they apply at BOTH readiness (Prepare) and delivery (Review and Close): every reader unions the list into the wave's roster without regard to phase. A downstream distribution (Waveforge) needs lanes that only make sense at one phase; the typical case is a release or compliance lane that can only judge delivered code, which today blocks readiness on a review it cannot yet perform, so operators either drop the lane or record a hollow readiness approval. The project already has a typed, strict, per-phase config block, `phase_gates` (ADR `1yb53`, `normalize_phase_gates` in `review_policy.py`), with `prepare` and `close` phases that currently carry only `required_sensors`.

The project lane list is also read by six separate union sites and a second loader in `review_evidence.py`, so a phase rule added piecemeal would drift. And `_read_project_required_review_lanes` silently treats a non-list `required_review_lanes` (a string, an object) as no lanes, so a typo removes every project-required review without a word.

The operator decided (2026-10-02): extend `phase_gates` with `required_lanes`; `required_review_lanes` keeps meaning both phases; older frameworks refuse the new field; one helper serves every union site; the wave record keeps `Required review lanes` as the readiness roster and gains an optional `Required delivery lanes` line; a non-list `required_review_lanes` becomes a config error.

Brief: consumers are distributions and projects with phase-specific review lanes; success is that a lane can be required at exactly one phase, every lifecycle reader agrees on which, and a malformed lane config is reported instead of ignored.

## Product Intent

A project can declare "this lane reviews delivery only" (or readiness only) in config. Projects that do not use the new field see no change in behaviour or in their review-policy digest. Spec: `docs/specs/mcp-tool-surface.md` (Prepare, Review and Close lane behaviour); config reference: `docs/architecture/cross-cutting-concerns.md` and ADR `1yb53`.

## Requirements

1. **Config.** `normalize_phase_gates` accepts an optional `required_lanes` list in `phase_gates.prepare` and `phase_gates.close`, validated as strictly as `required_sensors`: a list, each entry a non-empty string, no duplicates within the phase, errors named `phase_gates.<phase>.required_lanes[...]`. A phase block may carry `required_lanes`, `required_sensors`, or both. Unknown keys and phases stay errors. An older framework, which treats `required_lanes` as an unknown field, refuses the config (fail closed, already true and pinned today by a case in `test_phase_gates.py` that this change updates).
2. **Meaning.** `phase_gates.prepare.required_lanes` are required at readiness only; `phase_gates.close.required_lanes` are required at delivery only (Review and Close); `required_review_lanes` remains required at both. Risk-triggered lanes (from `select_required_review_lanes` path scoring) and requested lanes (the wave's `Requested review lanes`) apply to both phases, as today.
3. **One helper.** A single pure function, `project_lanes_for_phase(config, phase)` with `phase` in `{"prepare", "close"}`, in `review_policy.py` beside `normalize_phase_gates`, takes an already-loaded config mapping and returns `required_review_lanes` followed by that phase's `required_lanes`, order-preserving and de-duplicated. It reads no file. `lifecycle_gate_support.py` keeps a root-reading wrapper beside `_read_project_required_review_lanes` that loads `_read_workflow_config(root)` and calls the pure helper; the gate sites below call the wrapper. `review_evidence.required_review_status_keys` calls the pure helper directly on the config it already holds, so the `config_override` that `review_policy_upgrade.py` passes is honoured instead of being bypassed by a second file read. Both modules already import from `review_policy`. Unifying the two loaders changes `review_evidence`'s handling of non-string entries: it applies `str(value).strip()` to every list entry today (so `5` becomes lane `"5"`), while the shared helper keeps `_read_project_required_review_lanes`' rule of dropping entries that are not non-empty strings; the census in AC-6 records whether any config relies on the old coercion. Every project-lane union routes through the helper, chosen by phase:
   - `_prepare_policy_state` (readiness roster: `prepare`; delivery roster: `close`);
   - `_prepare_lane_review_state` (`prepare`);
   - `_guided_review_signoff_keys` (`prepare` for `approval_phase == "readiness"`, otherwise `close`);
   - `wf_review_wave_response` (`prepare` for the prepare phase, `close` for implementation);
   - `_evaluate_shared_delivery_state` in `lifecycle_gates.py` (`close`);
   - `_audit_harness_coverage` (the union of both phases, since it reports configured coverage, not a gate);
   - `review_evidence.required_review_status_keys`, the second config loader (the union of both phases' lanes plus both wave-record lines, so the signoff projection lists every lane that will be required at some phase).
   The wave-record roster has its own readers, and each must read the roster for its phase, or a lane required only at readiness stays required at Review and Close. Readers found on 2026-10-02 and the roster each reads after this change:
   - `lifecycle_gates.py` near line 276, `_evaluate_shared_delivery_state`: the delivery roster (Requirement 5 reader);
   - `wf_server/server_impl.py` near line 11322, `wf_review_wave_response`: by phase (readiness roster for the prepare phase, delivery roster for implementation);
   - `wf_server/server_impl.py` near line 9821, `_guided_review_signoff_keys`: by `approval_phase` (readiness roster for `readiness`, otherwise delivery);
   - `wf_server/server_impl.py` near line 10689, `_prepare_lane_review_state`: the readiness roster;
   - `lifecycle_gate_support.py` near line 786, `_review_policy_receipt_diagnostics`: both rosters, for the staleness check (Requirement 6);
   - `review_evidence.py` near line 1908, the `Required review lanes` regex parser in `required_review_status_keys`: both lines (Requirement 5).
   A census at implementation is recorded, with the predicate: every read of `"required_review_lanes"`, call of `_read_project_required_review_lanes` or of the new wrapper, call of `_extract_required_review_lanes`, and every regex or string match on `Required review lanes` or `Required delivery lanes`, in `.wavefoundry/framework/scripts/` (tests excluded). Each hit is listed with the roster it reads; any site not listed above is routed or given a recorded reason.
4. **Config error for a non-list.** `_read_project_required_review_lanes` no longer returns `[]` for a present, non-list `required_review_lanes`; the value is reported as a config error by the same channels as `phase_gates` errors: docs-lint (`check_workflow_config` path in `core_validators.py`, `docs/workflow-config.json: required_review_lanes must be a list`) and `_prepare_policy_state` (`PolicyInputError("config", ...)`, so Prepare, Review and Close surface it as today's config errors do). Readers never treat it as an empty list: for a present non-list value, the pure helper and `_read_project_required_review_lanes` raise a typed config error (a `ValueError` subclass defined in `review_policy.py`, carrying the lint message), never return a sentinel or `[]`. Gate callers convert it to `PolicyInputError("config", ...)` or the existing config-error diagnostic; `_audit_harness_coverage` catches it and reports the config error in its result with no lane coverage counted, so `wf_audit` never crashes on it; `required_review_status_keys` catches it and keeps the lanes it can still read (the wave-record lines), as it already does for a malformed `wave_review` policy, since lint reports the error separately. This is a deliberate behaviour change. An absent key is still an empty list; entries that are not non-empty strings stay dropped (unchanged, and listed as a follow-up rather than changed here).
5. **Wave record.** `- Required review lanes:` stays the readiness roster, written by `_replace_required_review_lanes` as today. Prepare writes `- Required delivery lanes: <lanes>` directly after it only when the delivery roster differs from the readiness roster, and removes the line when they become equal. An absent line means "same as readiness". A new reader beside `_extract_required_review_lanes` returns the delivery roster (the line when present, otherwise the readiness roster); the regex for the readiness line does not match the delivery line (verified: it is anchored on `Required review lanes`). The second wave-text parser in `required_review_status_keys` reads both lines.
6. **Staleness.** The roster check in `_review_policy_receipt_diagnostics` compares the readiness line with the current readiness selection and the delivery roster (line or fallback) with the current delivery selection; a mismatch in either is `review_policy_receipt_stale`.
7. **Readiness display.** A lane required at delivery only is reported at Prepare as applying at delivery (in the Prepare response, for example `data.delivery_only_lanes`, and visibly in the delivery line), and is not gated at readiness.
8. **Digest.** `REVIEW_POLICY_EVALUATOR_VERSION` stays 7. `policy_input_snapshot` keeps receiving the base `required_review_lanes` list as `project_lanes`; `phase_gates` already enters the payload whole when present, so a config that adds `required_lanes` moves its digest and a config without `phase_gates` produces a byte-identical payload. `canonical_review_policy_body` is not edited.
9. **Docs.** `docs/architecture/cross-cutting-concerns.md` (the `phase_gates` config paragraph and example), `docs/architecture/current-state.md` (its lifecycle gate paragraph), ADR `1yb53` (a dated note that `required_lanes` joined the block in wave `1zlu1`), seed `007-review-system-overview.md` (where it documents `required_review_lanes`; seed edit behind `seed_edit_allowed`), `docs/references/wavefoundry-overview.md` (its config example), `docs/specs/mcp-tool-surface.md` (Prepare, Review and Close lane behaviour and the new Prepare field), and a CHANGELOG entry (`### Added` for phase lanes, `### Changed` for the non-list config error). The docs census also covers framework carrier prose that states when required lanes apply, including `review_policy_reconcile.py` near lines 87-88 ("Required review lanes from readiness participate during **Review wave** ..."), which is reworded if a readiness-only lane makes it inaccurate.

## Scope

**Problem statement:** project review lanes cannot be scoped to one phase, the rule lives in seven places, and a malformed lane list is silently ignored.

**In scope:**

- `normalize_phase_gates`, the new helper, every site in Requirement 3, the wave-record delivery line writer and reader, the staleness comparison, the Prepare display, the non-list error.
- Tests: config validation, each phase's gating (a delivery-only lane does not block Prepare and does block Review and Close; a readiness-only lane the reverse), the delivery line written, removed and read, staleness per line, digest identity for configs without `phase_gates`, the non-list error at lint and Prepare, and the updated `test_phase_gates.py` case.
- Docs listed in Requirement 9.

**Out of scope:**

- Phase-scoping risk-triggered or requested lanes.
- A `review` phase in `phase_gates` (Review and Close share the delivery roster).
- Changing `REVIEW_POLICY_EVALUATOR_VERSION` or the canonicalizer.
- Dropping non-string list entries loudly (follow-up).
- Migrating existing configs (none in this repository or its fixtures use a non-list value).

## Acceptance Criteria

- [x] AC-1: `normalize_phase_gates` accepts `required_lanes` in `prepare` and `close` and rejects a non-list, an empty or non-string entry and a duplicate, each with a path-named error; the existing unknown-field and unknown-phase errors still fire; docs-lint reports the same errors.
- [x] AC-2: With `phase_gates.close.required_lanes = ["release-review"]`, Prepare readies a wave without a `release-review` approval, writes `- Required delivery lanes:` including `release-review`, and reports the lane as applying at delivery; Review and Close then refuse until `release-review` is approved. With `phase_gates.prepare.required_lanes`, the reverse holds. Against the current code the first fixture fails (the config is refused).
- [x] AC-3: Each site in Requirement 3 derives its lanes from the pure `review_policy.project_lanes_for_phase`: a test patches that pure helper (so both the root-reading wrapper and the direct `review_evidence` call see the patch) to return a sentinel lane per phase and observes it at every site (Prepare roster, Prepare lane state, guided signoff order for both phases, Review for both phases, the shared delivery gate, harness coverage, the signoff projection); `required_review_status_keys` called with a `config_override` uses the override's lanes, not the file's; each wave-record roster reader listed in Requirement 3 reads its stated roster (a readiness-only lane is absent from the Review and Close rosters); the census is recorded.
- [x] AC-4: When both rosters are equal no delivery line is written, and an existing delivery line is removed when they become equal; a hand-edited delivery line that differs from the current delivery selection yields `review_policy_receipt_stale`, as does a stale readiness line; deleting the `Required delivery lanes` line while a delivery-only lane is configured also yields `review_policy_receipt_stale` (the fallback roster, the readiness line, lacks the delivery-only lane).
- [x] AC-5: For a config without `phase_gates`, the review-policy digest and receipt are byte-identical before and after this change (computed on a fixture wave with the existing snapshot function), and `REVIEW_POLICY_EVALUATOR_VERSION` is 7.
- [x] AC-6: A string or object `required_review_lanes` is reported by docs-lint and refused at Prepare as a config error, and no reader treats it as an empty roster (the helper and `_read_project_required_review_lanes` raise the typed config error); `wf_audit` still returns, with the config error reported in harness coverage; an absent key still means no project lanes. A non-string list entry is dropped by the signoff projection as by the gates (the changed `review_evidence` behaviour). The census of existing configs (this repository's `docs/workflow-config.json`, the install defaults and test fixtures) is recorded.
- [x] AC-7: The docs in Requirement 9 (including `docs/architecture/current-state.md` and the `review_policy_reconcile.py` carrier prose) describe the field, its phases, the delivery line and the config error.
- [x] AC-8: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Run the Requirement 3 site census (project-lane reads and wave-record roster readers) and the Requirement 4 config census; record both.
- [x] Write failing tests for AC-1 through AC-6 (including updating the `test_phase_gates.py` case that pins `required_lanes` as unknown).
- [x] Extend `normalize_phase_gates`; add the pure `project_lanes_for_phase(config, phase)` in `review_policy.py` and the root-reading wrapper in `lifecycle_gate_support.py`; make the non-list value a typed error.
- [x] Route every project-lane site through the helper and every wave-record roster reader to its phase's roster; route `required_review_status_keys` through the pure helper on its own config.
- [x] Add the delivery line writer and reader, the staleness comparison and the Prepare display.
- [x] Update the docs (including `docs/architecture/current-state.md` and the `review_policy_reconcile.py` carrier prose), the seed (under `seed_edit_allowed`) and the CHANGELOG.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| phase-lanes-config | implementer | none | `review_policy.py`, `lifecycle_gate_support.py`, `core_validators.py` |
| phase-lanes-sites | implementer | phase-lanes-config | `wf_server/server_impl.py`, `lifecycle_gates.py`, `review_evidence.py` |
| phase-lanes-docs | implementer | phase-lanes-sites | docs, seed 007, CHANGELOG |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/lifecycle_gate_support.py`
- `.wavefoundry/framework/scripts/lifecycle_gates.py`
- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/review_policy_reconcile.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/core_validators.py`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_phase_gates.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/seeds/007-review-system-overview.md`
- `docs/architecture/cross-cutting-concerns.md`
- `docs/architecture/current-state.md`
- `docs/architecture/decisions/1yb53-adr config-declared-phase-gates.md`
- `docs/references/wavefoundry-overview.md`
- `docs/specs/mcp-tool-surface.md`

- The CHANGELOG at the repository root is edited too.

## Affected Architecture Docs

`docs/architecture/cross-cutting-concerns.md` (typed project policy: `phase_gates` gains `required_lanes`), `docs/architecture/current-state.md` (its lifecycle gate paragraph says optional `phase_gates` add required sensors; it gains lanes), and ADR `1yb53` (dated note). No new boundary: the config stays typed data read by the existing support module.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Strict config validation is the fail-closed contract. |
| AC-2 | required | The feature. |
| AC-3 | required | One rule, every reader. |
| AC-4 | required | The wave record and the staleness check must agree. |
| AC-5 | required | No receipt rotation for configs that do not use the field. |
| AC-6 | important | The deliberate behaviour change and its census. |
| AC-7 | important | Discoverability. |
| AC-8 | required | Standard verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-03 | Delivery-review repairs. F2: `wf_review_wave_response` computes its own roster only for the prepare phase; the implementation phase's `required_review_lanes_empty` advisory now reads `shared["required_lanes"]`, the roster the delivery gate enforces; `test_review_status_fails_when_executable_approval_is_missing` no longer patches the two server-level readers the implementation phase stopped calling. New test `test_delivery_only_roster_is_not_reported_empty_at_review` (no base lanes, `phase_gates.close.required_lanes = ["release-review"]`): Prepare writes `Required delivery lanes: release-review` and implementation-phase review reports no `required_review_lanes_empty` (prepare-phase review still does). F4b: spec, CHANGELOG and cross-cutting-concerns now say Implement, Review and Close report `required_review_lanes_invalid` and Prepare refuses through the policy-state config error. Nit: `normalize_phase_gates` strips a lane before the duplicate check; case `[" x", "x"]` added. | Failing-first and mutations: the new L9 (R3, implementation advisory read from the readiness roster) killed by the new F2 test; R9 (strip after the duplicate check) killed by `test_required_lanes_validation`; full suite 10,878 OK (34 skipped), `--profile second` 10,875 OK, `--profile declared` 10,878 OK, in a fresh scratch copy |
| 2026-10-03 | Implemented. `review_policy`: `normalize_phase_gates` accepts and validates `required_lanes`; `project_required_review_lanes`, `project_lanes_for_phase(config, phase)` and `ProjectLanesConfigError`. `lifecycle_gate_support`: `_read_project_required_review_lanes` raises for a non-list; wrapper `_project_lanes_for_phase`; `_extract_required_delivery_lanes`/`_extract_required_lanes_for_phase`; `_prepare_policy_state` returns `delivery_lanes` and `delivery_only_lanes` (digest still takes the base list); `_review_policy_receipt_diagnostics` checks both rosters. Site census (predicate as planned): `_prepare_policy_state` (readiness and delivery), `_prepare_lane_review_state` (prepare), `_guided_review_signoff_keys` (by approval phase), `wf_review_wave_response` (by phase; implementation-phase lanes come from the shared delivery gate), `_evaluate_shared_delivery_state` (close), `_audit_harness_coverage` (union), `required_review_status_keys` (union plus both lines, through the pure helper on its own config), `_review_policy_receipt_diagnostics` (both rosters), `_replace_required_review_lanes` (writer, gains the delivery line), `wf_server/server_impl.py` scaffold line in `create_wave` (writer, `none`, unchanged), `lifecycle_gates.py` message text (not a reader); `_wave_review_policy_diagnostics` also reads the base list to report the config error. Config census: no `required_review_lanes` that is not a list in `docs/workflow-config.json`, `.wavefoundry/framework/install/*.json` or the tests tree, and no config relied on the old `str()` coercion. Docs: cross-cutting-concerns, current-state, ADR 1yb53 note, seed 007, wavefoundry-overview, spec, CHANGELOG, `review_policy_reconcile.py` replacement text reworded. Deviations: Review and Close report the non-list error as the new blocking code `required_review_lanes_invalid` (from `_wave_review_policy_diagnostics`), Prepare refuses through the policy-state config error; the pure helper is called through the `review_policy` module so one patch reaches every site; the lifecycle golden gains `delivery_only_lanes` and `review_policy.delivery_lanes`/`delivery_only_lanes` (equal to readiness on its fixtures), declared in `test_only_declared_observability_additions_since_extraction_golden`; `test_review_status_fails_when_executable_approval_is_missing` patches the new server-level readers. A config that adds phase lanes after a wave was created leaves its review-status projection stale until the next typed event, as adding a base lane already does. | `tests/test_phase_gates.py` `PhaseLaneTests` (9 tests) plus the updated non-list case; failing-first: 10 failures and 3 errors on the pre-change tree; mutations L1-L8 and L9b killed; L9 (implementation phase forced to the readiness roster in `wf_review_wave_response`) survived because that phase's lanes come from the shared delivery gate, pinned by L3; full suite and both profiles green (counts in 1zlu2) |
| 2026-10-02 | Planned from the operator's decisions. Verified against the tree: `normalize_phase_gates` accepts only `required_sensors` (any other key is `phase_gates.<phase>.<key>: unknown field`), and `test_phase_gates.py` pins `{'close': {'required_lanes': [...]}}` as an error today; `policy_input_snapshot` adds `phase_gates` to the payload only when truthy and keeps `project_required_review_lanes` separate; `REVIEW_POLICY_EVALUATOR_VERSION = 7`. Union sites found: `_prepare_policy_state`, `_prepare_lane_review_state`, `_guided_review_signoff_keys`, `wf_review_wave_response`, `_evaluate_shared_delivery_state`, `_audit_harness_coverage`, and the second loader `required_review_status_keys` (which reads `docs/workflow-config.json` itself and parses the Participants roster with its own regex). The roster check is in `_review_policy_receipt_diagnostics`. Config census, predicate: any `required_review_lanes` value in `docs/workflow-config.json`, `.wavefoundry/framework/install/*.json` and the tests tree that is not a list literal: none (this repository's config does not set the key; every test fixture passes a list). `docs/workflow-config.json` does not set `phase_gates`, so this repository's digests do not move. | Code reads and grep, 2026-10-02 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-02 | Extend `phase_gates` with `required_lanes`; `required_review_lanes` keeps meaning both phases | Operator decision: reuses the typed, strict per-phase block, and older frameworks refuse it (fail closed) | New top-level keys `required_readiness_lanes`/`required_delivery_lanes` (rejected: older frameworks would silently ignore them); per-lane phase objects inside `required_review_lanes` (rejected: changes an existing key's type) |
| 2026-10-02 | One helper, `project_lanes_for_phase`, for every union site including the second loader | Operator decision: seven independent unions would drift | Patch each site inline |
| 2026-10-02 | Keep `Required review lanes` as the readiness roster; add `Required delivery lanes` only when it differs | Operator decision: existing wave records and parsers stay valid; most waves never gain the line | Always write both lines (rejected: churns every wave record) |
| 2026-10-02 | Keep `REVIEW_POLICY_EVALUATOR_VERSION` at 7 | Operator decision: `phase_gates` already enters the digest only when present, so configs not using the field do not rotate | Bump to 8 (rejected: lapses every readiness approval in every open wave for no behavioural change) |
| 2026-10-02 | Risk-triggered and requested lanes apply to both phases | Operator decision | Phase-scope them (rejected: no input names a phase for them) |
| 2026-10-02 | A non-list `required_review_lanes` becomes a config error | Operator decision, recorded as a deliberate behaviour change: silently dropping every project lane on a typo is a fail-open | Keep the silent `[]` |
| 2026-10-02 | The signoff projection and harness coverage use the union of both phases | They describe what will be required at some phase; neither is a gate | Phase-specific projection (rejected: the projection is one table) |
| 2026-10-02 | Readiness amendments: the helper is the pure `review_policy.project_lanes_for_phase(config, phase)` beside `normalize_phase_gates`, with a root-reading wrapper in `lifecycle_gate_support.py`; `required_review_status_keys` calls the pure helper so `review_policy_upgrade.py`'s `config_override` is honoured; AC-3 patches the pure helper; unifying the loaders changes `review_evidence`'s `str()` coercion of non-string entries to the gates' drop rule (B3); every `_extract_required_review_lanes` caller and the `review_evidence` regex parser are enumerated with the roster each reads and the census predicate widened to them, so a readiness-only lane does not stay required at Review and Close (B4); AC-4 adds the deleted-delivery-line case, and a non-list value raises a typed config error (no sentinel) that `_audit_harness_coverage` catches so `wf_audit` does not crash (N7, raise chosen at readiness because a sentinel can be mistaken for an empty roster, the fail-open this change removes); `review_policy_reconcile.py` carrier prose joins the docs census (N10); `docs/architecture/current-state.md` added to tasks and ACs (N11) | Readiness review findings, 2026-10-02. Operator decisions above are unchanged | Keep the helper root-reading in `lifecycle_gate_support.py` (rejected: bypasses `config_override`); a sentinel return for a non-list value (rejected: callers could read it as no lanes) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A union site is missed and gates the wrong phase | Requirement 3 census with a stated predicate; AC-3 sentinel test at every site |
| A project with a malformed `required_review_lanes` is newly blocked at Prepare | Intended; lint names the key and the fix; census found no such config here |
| Open waves in a distribution that adopts the field see their receipts go stale | Expected: adopting a `phase_gates` change moves the digest, as adding a sensor does today; documented in the CHANGELOG |
| `1zlu2` and `1zlu0` touch neighbouring lifecycle code | Different functions; serialize `server_impl.py` edits within the wave |
| Platform behaviour | Config and record parsing only; identical on Windows, macOS, Linux and WSL2 (the wave record line parsers already tolerate CRLF through `splitlines`) |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
