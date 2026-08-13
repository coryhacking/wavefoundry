# Rendered Review-Protocol Loss Is Ungated

Change ID: `1v4mt-bug rendered-review-protocol-loss-is-ungated`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-12
Wave: 1v4mw silent-failure-surfacing

## Rationale

Two marker families carry rendered content. Only one is gated.

The framework already states the correct disposition for the `wavefoundry:review-policy` family in
`core_validators.py`: a single or malformed marker pair is a FAILURE, and while the reconciler may
warn and skip, a gate must not. The `wave:executable-review-evidence` family, rendered into every
reviewer role doc, gets only the warn-and-skip half: `_upsert_review_protocol_region` returns `None`
on malformed markers and `render_agent_surfaces` prints a stderr warning and continues. Confirmed
against the tree: `core_validators.py` matches only `review-policy` carriers and no validator under
`wave_lint_lib/` covers the second family.

Field-observed consequence (downstream repo, 1.13.0 through 1.16.1): a broken begin marker in four
role docs left them half-paired through a **full upgrade cycle**, silently receiving no
review-protocol updates, while `docs-lint: ok` and the docs gate PASSED every run. The only signal
was one stderr line among roughly 90 gardener lines, absent from `data.summary`, with
`failed_phase: null`.

This is worse than a wrong output. It is the verification machinery reporting success while the
content it exists to maintain silently stops updating, so nothing downstream can detect the loss.

## Requirements

1. A malformed or half-paired `wave:executable-review-evidence` marker region fails the docs gate,
   with the same disposition the `wavefoundry:review-policy` family already has.
2. The failure names the file and the specific marker condition, so the repair is obvious.
3. Renderer warnings reach the structured upgrade summary rather than stderr alone.
4. A healthy repository is unaffected: no new failure fires on well-formed markers.

## Scope

**Problem statement:** the second rendered-content marker family has no gate, so silent loss of
review-protocol content passes a green docs gate.

**In scope:**

- Extending the existing marker disposition logic to the `wave:executable-review-evidence` family.
- A `renderer_warnings` field in the upgrade summary, beside the existing `reconciliation` and
  `host_permission_flags` lists.

**Out of scope:**

- Changing the disposition of the `wavefoundry:review-policy` family, which is already correct.
- Auto-repairing malformed markers. Report and fail; do not rewrite operator content.
- Any other renderer warning class beyond the marker family named here.

## Acceptance Criteria

- [x] AC-1: A half-paired or malformed `wave:executable-review-evidence` region fails the docs gate, asserted with the exact shapes the field report hit (end marker present, begin missing).
- [x] AC-2: The failure message names the file and the marker condition.
- [x] AC-3: A well-formed repository still passes, asserted so the new check cannot fire on healthy content.
- [x] AC-4: Renderer warnings appear in the structured upgrade summary as `renderer_warnings`, and an upgrade that emits one no longer reports success with the warning only on stderr.
- [x] AC-5: The gate reuses the existing disposition logic rather than a second implementation of it, so the two families cannot drift apart again.

## Tasks

- [x] Reproduce first: a fixture with a half-paired region must fail the new gate and pass the old one.
- [x] Extend the existing carrier disposition to the second family; do not fork the logic.
- [x] Add `renderer_warnings` to the summary contract beside its sibling lists.
- [x] Census every marker family the renderers emit, so a third family is not left ungated. Use a reference-level instrument AND an identifier search, per the seed 209 census rule, and record which closed which part.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| reproduce | implementer | — | Half-paired fixture; must fail after and pass before. |
| gate | implementer | reproduce | Reuse the existing disposition; AC-5 forbids a second implementation. |
| summary | implementer | — | `renderer_warnings` beside `reconciliation` / `host_permission_flags`. |
| family-census | implementer | — | Are there other ungated families? Two instruments required. |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wave_lint_lib/core_validators.py`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`

## Affected Architecture Docs

`N/A` for a new ADR: this restores an already-stated principle to a second carrier rather than
deciding anything new. `docs/specs/mcp-tool-surface.md` should be checked for any claim about what a
passing docs gate guarantees, since that claim is currently too strong.

## AC Priority


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect. |
| AC-2 | required | A gate that fails without naming the cause repeats the diagnosis cost this report describes. |
| AC-3 | required | A false positive here would block every upgrade. |
| AC-4 | required | The field signal was invisible precisely because it was stderr-only. |
| AC-5 | required | Two implementations of one disposition is how the families diverged in the first place. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-12 | Filed from downstream upgrade feedback spanning 1.13.0 to 1.16.1. Both halves verified against the tree before planning: `core_validators.py` matches only `review-policy` carriers, and no validator under `wave_lint_lib/` references `executable-review-evidence`. | Field report; `core_validators.py`; `render_agent_surfaces.py` `_upsert_review_protocol_region` warn-and-continue. |
| 2026-08-12 | Reproduced first. A half-paired region (end present, begin removed: the exact field shape) passed before and fails after. Disposition factored into `_check_marker_family_parity`; both families now call it, and the review-policy family's four pinned dispositions still pass unchanged. Registered on the full and incremental docs-lint paths. | `test_protocol_family_half_paired_markers_fail`; `test_protocol_family_registered_on_full_and_incremental_paths`; red state before the fix was `ImportError: cannot import name 'check_review_protocol_carrier_parity'`. |
| 2026-08-12 | AC-3 measured against the live corpus, not a fixture alone: 21 rendered carriers present in this repository, zero failures. | `check_review_protocol_carrier_parity(repo_root)` returned `[]` over `docs/agents/**`, `docs/prompts/**`, `docs/contributing/review-and-evals.md`, `.claude/agents/guru.md`, `.codex/skills/auto-guru/SKILL.md`; pinned by `test_protocol_family_live_corpus_passes` with a probe assertion against vacuity. |
| 2026-08-12 | Marker-family census run with two instruments, per the seed-209 rule. **Instrument A** (`code_pattern` on the constant-definition shape `^[A-Z_]*MARKER[A-Z_]*=`) returned 61 hits and closed the "constants named `*MARKER*`" part of the universe. **Instrument B** (`code_keyword` on the marker literals `<!-- wave:`, `<!-- wavefoundry:`, `# wave:`, `<!-- waveframework:`) returned 98 hits and closed the part A was blind to: it found `review_policy_reconcile.MANAGED_BEGIN`/`MANAGED_END` (`wavefoundry:review-lifecycle`), whose constant names contain no `MARKER` token and which A therefore could not see. Neither instrument alone was sufficient. | `code_pattern` 61 matches; `code_keyword` 98 matches; disposition of each family then read directly. |
| 2026-08-12 | **Regression caught by the suite and repaired.** The first implementation of the summary scan imported `wave_lint_lib.core_validators` from `upgrade_wavefoundry.py` to share the gate's logic. That broke the upgrade feature-pack protocol: `upgrade_protocol._validate_imports` walks the WHOLE tree (function-scoped imports included) and admits only top-level pack modules, and `wave_lint_lib` is a package, so the bridge bundle could no longer validate. Four tests failed in `test_upgrade_protocol.py`. Repaired by deriving the finding from `render_agent_surfaces.review_protocol_carriers_skipped_by_render`, an admitted module, rather than by disguising the import behind `importlib` — the guard exists so the bridge bundle runs standalone, and routing around it would have traded a visible failure for exactly the class of silent breakage this wave is about. Both paths still bottom out in one disposition: `_upsert_review_protocol_region` returning `None`. | `test_upgrade_protocol` 4 failures then 31/31 OK; `UpgradeProtocolError: mandatory module upgrade_wavefoundry.py has unavailable import wave_lint_lib`; `upgrade_protocol.py:96-115`. |
| 2026-08-12 | Discharged the readiness council's delivery-time obligation (docs-contract-reviewer): locate and correct any documentation claiming a passing docs gate guarantees rendered-content integrity. **Audited and found nothing to correct.** The only spec entry is `docs/specs/mcp-tool-surface.md:969`, which says `wf_validate_docs` "runs docs validation and returns structured pass/fail diagnostics" and makes no integrity claim; `docs/RELIABILITY.md:71` names it only as a recovery step. Every other hit for "carrier parity" sits in wave records and plans, which are historical and correctly describe the state at their time. Reported rather than silently dropped, since the obligation was recorded as blocking-at-delivery. | `code_keyword` over `docs/**` for "carrier parity", "docs gate guarantees", "rendered region differs"; `docs/specs/mcp-tool-surface.md:969-972`; `docs/RELIABILITY.md:71-72`. |
| 2026-08-12 | Delivery review found three defects in this change, all repaired in session. (1) The refactor replaced `REVIEW_POLICY_SURFACE_BLOCKS.get(...)` with a membership test plus indexing, which silently changed the pre-existing disposition for a registry row whose block VALUE is `None`: the old code skipped it, the new code would have handed `None` to the upsert helper. Restored via a walrus on `.get(...) is not None`. (2) The changelog described the new gate as firing only on broken markers, understating it: adopting the shared rule also brings the drift half, so a hand-edited region now fails too. Corrected, including why that case is largely self-correcting during an upgrade. (3) The Decision Log claimed the warning is emitted on a failed phase and outside the major/minor gate, and no test asserted it. Added, with a polarity assertion that the reconciliation prose IS still suppressed on that path, so the test cannot pass merely because everything prints. | `core_validators.check_review_policy_carrier_parity` entries comprehension; `CHANGELOG.md` 1.16.2; `test_warning_still_emitted_on_a_failed_phase`. |
| 2026-08-12 | Retrieval caveat recorded for future review work: `code_keyword` returned hits for newly added lines in `tests/` while missing the same session's new symbols in `upgrade_wavefoundry.py`, `accel_embedder.py`, and `render_agent_surfaces.py` (`_run_renderer_warning_scan`, `_probe_failure_detail`, `review_protocol_carriers_skipped_by_render` all absent). A direct cross-check found all of them. Index freshness, not absence: MCP-first retrieval is right, but a claim of ABSENCE from a single instrument is not sound against a tree edited in the same session. This is the seed-209 rule applying to the review phase, not just the census. | `code_keyword` 19 hits vs direct check; all three symbols present at `upgrade_wavefoundry.py:3264`, `accel_embedder.py:96`, `render_agent_surfaces.py:1164`. |
| 2026-08-12 | Census result: eleven marker families, and only ONE other shares the silent-skip disposition. `wave:auto-guru` / `wave:root-bridge` append rather than skip; `wavefoundry:review-lifecycle`, `wave:context-efficiency-carrier`, `wave:review-status` and `wave:finding-synthesis` **raise** `ValueError`; `wave:context-efficiency` returns validation errors; `wave:codex-mcp` re-appends. The one remaining silent skip is `gen_codebase_map._refresh_repo_index_modules`, which returns `False` on a half-paired region in `docs/repo-index.md`. Left ungated deliberately: out of this change's declared scope, and self-healing because the enclosing generator rewrites the file wholesale whenever structural content changes. Recorded as a follow-up rather than silently absorbed. | `render_agent_surfaces.upsert_marked_region`; `review_policy_reconcile._managed_region`; `context_efficiency.replace_carrier_block`; `review_evidence` status/synthesis upserts; `gen_codebase_map.py:1795-1797`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-12 | Extend the existing disposition to the second family rather than write a new validator for it. | The correct behaviour is already implemented and documented for the first family; a parallel implementation is what allows the two to drift, which is the root cause here. | A dedicated validator for the second family (rejected: duplicates the rule). Auto-repair of malformed markers (rejected: rewrites operator content to satisfy a gate, and hides the fact that a marker was broken). |
| 2026-08-12 | Derive `renderer_warnings` by re-scanning the tree at summary time rather than capturing the renderer subprocess's stderr. | The renderer runs as a subprocess and the condition is a property of the tree, so a read-only rescan reports it with no cross-process plumbing. It also shares the docs-gate validator, so the summary and the gate cannot disagree about what is malformed. Same shape as `_run_reconciliation_scan`, which already re-derives its three channels this way. | Parse the child's stderr (rejected: couples the summary to log formatting and needs capture plumbing the render phase does not have). A module-global warning carrier like `_PERMISSIONS_DELTA` (rejected: that exists to cross a process boundary the delta cannot be recomputed across; this finding can simply be recomputed). |
| 2026-08-12 | Emit `renderer_warnings` outside the `not failed_phase` guard and outside the major/minor gate that wraps the reconciliation prose. | A malformed marker pair is exactly what a half-finished render leaves behind, and the field case arrived on ordinary upgrades. Suppressing the line on a failed phase or a patch upgrade would withhold the finding in the runs most likely to produce it. | Reuse the existing reconciliation prose block (rejected: inherits both gates). |
| 2026-08-12 | Leave `gen_codebase_map._refresh_repo_index_modules` ungated despite the census finding it shares the silent-skip disposition. | Out of the declared scope, and materially different in consequence: the enclosing generator rewrites `docs/repo-index.md` wholesale on any structural change, so the region self-heals, whereas a role doc's protocol region only ever updates through the skipped path. | Gate it in this change (rejected: silent scope expansion). Say nothing (rejected: the census exists precisely so a third family is not left undocumented). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A new blocking gate could fire on repositories whose markers are already broken, turning a silent problem into a blocked upgrade. | That is the intended behaviour, and it is why AC-2 requires the message to name the file and condition. Worth calling out in the changelog as an operator-visible change. |
| The census could miss a third marker family, leaving the same gap elsewhere. | The census task mandates two instruments with differing blind spots and requires recording which closed which part of the claim. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
