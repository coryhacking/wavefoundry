# Rename wf_review_evidence to wf_review_event and complete the repair-chain guidance

Change ID: `1tis9-enh repair-chain-recipe-and-review-evidence-errors`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-24
Wave: `1tis8 memory-eval-mcp-tool-and-decision-log-target`

## Rationale

The tool named `wf_review_evidence` does not do what its name says. It *inspects and appends typed review events* — `event="list"`, `event="finding"`, `event="run"`, `event="approval"` — and an executable Evidence Record is only one of several record types it produces (it also writes review-run and finding-synthesis records, and it reads the whole ledger). The "evidence" name mislabels the abstraction and actively contributes to the discoverability friction below: an agent reaching for the tool does not think "I am recording a review event," so the event taxonomy reads as incidental rather than central. Renaming it to `wf_review_event` makes the name match the abstraction. Broad distribution has not happened, so this is a clean rename with **no public alias**.

The same public usability defect has a documentation half. Driving a repair chain — recording a `repair_start`, then a fresh independent `reverification` to clear a blocking lane — currently costs several dead-end calls to rediscover the mechanics, because the guidance and the tool's error messages do not lead to the correct sequence:

- The **lane-clearing recipe** an agent follows appears in *two* places with the same omission: seed 209 ("Lane-clearing recipe (state-derived)") **and the registered tool docstring**. Both jump straight to "submit ONE reverification per lane" and never mention the `repair_start` prerequisite, so following either leads to the tool rejecting the reverification with "no preceding repair_start." The plan must fix **both** copies; updating only the seed leaves the docstring wrong.
- Nothing states that `repair_start` and `reverification` are `event="finding"` calls (carrying `run_kind`), not `event="run"`. The natural guess — `event="run"` for a "run kind" — produces the misleading "empty lightweight run requires run_kind readiness/initial_delivery and cycle 0," which does not hint that these are finding events.
- The recipe's actor model must be correct. A repair chain is **not** one actor discovering, repairing, and reverifying: the **implementer** records the `repair_start` before mutating, and the **blocking reviewer lane** performs the *fresh, independent* `reverification` (`fresh_context=true`, `independent=true`, acting as that lane). The recipe must make that split explicit, because a single actor "reverifying its own repair" would violate the independence the lane clearance depends on.

Field placement is **not** wholly undocumented: the current docstring already assigns the core judgment facts to `judgment` and the executed-observation fields to `evidence`. The real remaining gaps are (a) the error messages do not name which object a missing field belongs to, (b) the tool-surface spec does not state the split, and (c) the docstring's statement of it is not easy to scan. Sharpen those, do not re-document from scratch.

None of this changes the state machine, run kinds, or evidence schema — the validation is correct. The cost is a misleading tool name plus guidance and errors that do not lead to the right call, paid by every agent (here and in every downstream project) that authors review events by hand.

## Requirements

1. **Rename `wf_review_evidence` → `wf_review_event`, clean, no alias.** Every live surface adopts the new name; no backward-compatible alias is registered. The census in Scope is exhaustive for live surfaces. State machine, event kinds, judgment/evidence schema, and accepted inputs are unchanged — only the tool name.
2. **Telemetry attribution follows the rename.** The tool-name-keyed context-efficiency extractor maps in `server_impl.py` (`_STATE_SOURCE_EXTRACTORS`, `_ARTIFACT_EXTRACTORS`, `_COST_FOCUS_EXTRACTORS`) key on `wf_review_event` so new invocations attribute correctly; the explicit-wave telemetry-attribution and repeat-list-neutrality tests are updated to the new name and stay green.
3. **Upgrade reconciliation.** The upgrade tool-rename map (`upgrade_wavefoundry.py`) carries a `wf_review_evidence → wf_review_event` entry so existing projects' rendered surfaces and configs reconcile on upgrade; build/upgrade tests and a fresh-process (reload) tool-list verification confirm the tool registers under the new name and the old name is absent from the live tool list.
4. **Complete the lane-clearing recipe in BOTH seed 209 and the registered tool docstring.** Both must state: when the finding's repair cycle is not yet open, record a `repair_start` first; `repair_start` and `reverification` are `event="finding"` calls carrying `run_kind` (not `event="run"`); and the actor split — the **implementer** records `repair_start` before mutation, the **blocking reviewer lane** performs the fresh independent `reverification`. The existing per-lane, re-list-first, auto-minted-`lane_reassessment` guidance is preserved.
5. **Self-correcting sequence errors.** When `event="run"` is submitted with a `run_kind` other than `readiness`/`initial_delivery`, the error states these are recorded as finding events (`event="finding"` with the `run_kind`). When a `reverification` has no preceding `repair_start`, the error names the corrective call (`event="finding"`, `run_kind="repair_start"`, `cycle>=1`, same `finding_id`).
6. **Sharpen field-placement guidance (do not re-document).** Preserve the existing docstring assignment (core facts → `judgment`, executed observations → `evidence`); add the missing signals: the "requires <field>" errors name whether the field belongs in `judgment` or `evidence` where practical, the tool-surface spec states the split, and the docstring presents it scannably.
7. **Historical records retain the old name.** Closed wave records under `docs/waves/`, existing telemetry rows (SQLite and published `wave:context-efficiency-state` JSON), and prior CHANGELOG release entries keep `wf_review_evidence` as point-in-time history and are not rewritten. A new CHANGELOG entry documents the rename.
8. **Semantic, not verbatim.** Requirements 4–6 are about guidance *content* (event type, prerequisite, actor split, field home), not exact strings; tests assert the corrective concept, not brittle literals.

## Scope

**Problem statement:** the tool's name mislabels the typed-event abstraction, and the repair-chain guidance (in both the seed and the docstring) plus the tool's errors do not lead an agent to the right sequence, event type, actor split, or field placement.

**In scope — rename census (live surfaces; edited under `framework_edit_allowed`, seed under `seed_edit_allowed`):**

- **MCP registration + public contract + census + recovery hints** — `server_impl.py` (tool registration/`@mcp.tool`, `public_contract`, tool census, `next_tools`/`recovery_tools`/`recovery_usage` strings).
- **Telemetry extractor maps** — `server_impl.py` `_STATE_SOURCE_EXTRACTORS`, `_ARTIFACT_EXTRACTORS`, `_COST_FOCUS_EXTRACTORS` keys, and their tests (`test_context_efficiency.py`, `test_server_context_efficiency.py`) including explicit-wave attribution and repeat-list neutrality.
- **Tool builder + docstring** — `review_evidence.py` (error messages; the lane-clearing recipe embedded in the registered description).
- **Renderer mappings** — `render_platform_surfaces.py`.
- **Upgrade + build** — `upgrade_wavefoundry.py` (rename map), `test_upgrade_wavefoundry.py`, `test_build_pack.py`, and a fresh-process/reload tool-list check (`test_server_tools.py`).
- **Seeds + docs + inventory** — `seeds/209-agent-harness-core.prompt.md`, `AGENTS.md` (tool inventory), `docs/specs/mcp-tool-surface.md`, `docs/architecture/data-and-control-flow.md`, `docs/architecture/domain-map.md`, `docs/references/context-efficiency.md`, `docs/contributing/review-and-evals.md`, and any live rendered prompt surface (regenerate via the renderer; do not hand-edit renders).
- **Repo memory** — `docs/agents/memory/` records that cite the tool as a *current* action surface are updated; records citing it as history are left as history.

**Out of scope:**

- Any change to the review-event state machine, run kinds, judgment/evidence schema, or accepted inputs.
- The `event="list"` inspection surface behavior (already sufficient and the correct first step).
- A composite repair-chain authoring helper (a conditional future follow-up recorded in the Decision Log, only if manual sequencing still recurs after this change).
- Historical wave records, prior telemetry rows, and past CHANGELOG entries (retain the old name).

## Acceptance Criteria

- [x] AC-1: a case-insensitive census finds `wf_review_evidence` on no live surface (code, seeds, live docs, tool inventory, renderer, tests); only historical wave records, prior telemetry rows, and past CHANGELOG entries retain it. The tool registers as `wf_review_event` and a fresh-process/reload tool list shows the new name and not the old.
- [x] AC-2: the tool-name-keyed extractor maps use `wf_review_event`; the explicit-wave attribution and repeat-list-neutrality tests pass under the new name (new invocations credit `wf_review_event`).
- [x] AC-3: the upgrade rename map carries `wf_review_evidence → wf_review_event`; build/upgrade tests and the reload tool-list verification are green.
- [x] AC-4: the lane-clearing recipe in **both** seed 209 and the registered tool docstring names the `repair_start` prerequisite, the `event="finding"` event type, and the implementer-records-repair_start / blocking-lane-performs-independent-reverification actor split; the render is regenerated, not hand-edited.
- [x] AC-5: submitting `event="run"` with a non-readiness/initial_delivery `run_kind` returns an error pointing to the finding-event form; submitting a `reverification` with no preceding `repair_start` returns an error naming the corrective call (semantic tests, not verbatim).
- [x] AC-6: the field-placement split is preserved in the docstring and additionally stated in the tool-surface spec and the "requires <field>" errors name the field's home where practical.
- [x] AC-7: historical wave records, prior telemetry rows, and prior CHANGELOG entries are unchanged; a new CHANGELOG entry documents the rename.
- [x] AC-8: docs gate, tool-registration/docs-constants lints, and the full framework suite are green.

## Tasks

- [x] Rename across the live census (registration/contract/census/hints, extractor keys, builder/docstring, renderer, upgrade map, seeds, docs, inventory, tests); add a new CHANGELOG entry.
- [x] Complete the lane-clearing recipe in both seed 209 and the tool docstring (repair_start prerequisite, event type, actor split); regenerate the rendered surface.
- [x] Self-correcting sequence errors + sharpened field-placement guidance (errors, spec, scannable docstring).
- [x] Telemetry-attribution and repeat-list-neutrality tests under the new name; upgrade/build tests; fresh-process reload tool-list verification; case-insensitive rename-gate census; docs gate; full suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| rename | implementer | — | Live census incl. extractor keys, renderer, upgrade map, docs, inventory (framework_edit_allowed) |
| recipe | implementer | — | Seed 209 + tool docstring recipe (seed_edit_allowed); render regen |
| errors | implementer | rename | Self-correcting sequence errors + field-home guidance |
| verify | qa-reviewer | rename, recipe, errors | Rename-gate census, telemetry attribution, reload tool-list, semantic error tests |

## Serialization Points

- The error-message and telemetry-test edits touch the same files being renamed; land the rename first within the change, then the error/guidance edits, to avoid churn. Independent of the other 1tis8 changes.

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` (tool rename + field-placement note), `docs/architecture/data-and-control-flow.md` and `docs/architecture/domain-map.md` (tool-name references). No boundary, flow, or state-machine change.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The rename must be complete on live surfaces; a stale reference is a broken tool reference. |
| AC-2 | required | A missed extractor key silently drops telemetry credit for the renamed tool. |
| AC-3 | required | Existing projects must reconcile the name on upgrade, as prior tool renames did. |
| AC-4 | required | The recipe (both copies) is the surface agents follow; its omission is the primary usability cost. |
| AC-5 | required | The two sequence errors are the dead ends an agent hits; they must self-correct. |
| AC-6 | important | Field-home guidance prevents trial-and-error but the split is already partly documented. |
| AC-7 | required | History must not be rewritten; the point-in-time record stands. |
| AC-8 | required | Standard gates. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-25 | Implemented the clean rename: 103 `wf_review_evidence` occurrences renamed across 18 live files, plus 41 `wf_review_evidence_response` occurrences (the `\b` word boundary skipped the `_response` suffix — caught by the residual census, not assumed). Extractor maps (`_STATE_SOURCE_EXTRACTORS`, `_ARTIFACT_EXTRACTORS`, `_COST_FOCUS_EXTRACTORS`) key on the new name; upgrade reconciliation gained `wf_review_evidence -> wf_review_event`. FRESH-PROCESS verification: 83 tools register, `wf_review_event` present, `wf_review_evidence` absent, no alias. Historical wave records, prior telemetry rows, and the 1.14.0 CHANGELOG entry retain the old name; a new 1.15.0 section documents the rename. | Rename census; fresh-subprocess `register_mcp_surface` probe; `render_platform_surfaces.py` rename map |
| 2026-07-25 | Recipe + errors: seed 209 and the registered tool docstring both now carry the `repair_start` prerequisite, the finding-vs-run event type, and the implementer-records / blocking-lane-reverifies actor split. Both sequence errors self-correct semantically; field placement sharpened into a scannable judgment-vs-evidence enumeration (the prior assignment was preserved, not rewritten). | `review_evidence.py` error branches; `server_impl.py` docstring; seed 209 (gate opened and closed immediately); `test_review_evidence.py` 94 OK |
| 2026-07-25 | Final verification. One live-caught failure: the docstring rewrite split the existing semantic anchor `ONE reverification per lane` across a line break, tripping the 1tbw4 discoverability guard. Reflowed the docstring rather than weakening the assertion — the guard was doing its job. Full suite 6,200 tests across 59 files OK; `wf_validate_docs` clean. | `test_server_tools` 1419 OK; final suite log |
| 2026-07-25 | **Gapfill:** the rename itself was executed as a scripted pass over an explicit file list rather than through MCP retrieval — it is bulk-mechanical token replacement across 18 files where the raw residual census IS the verification artifact. Discovery, call-site reads, and the recipe/error edits used `code_keyword`/`code_read`. | Rename script + residual census output |
| 2026-07-24 | Drafted from a live 1tbt5 delivery re-review (repair-chain dead ends) and the operator's rename verdict. Grounded census: a case-insensitive scan finds 160 occurrences across 34 files — 5 framework code files (incl. the three tool-name-keyed extractor maps at `server_impl.py` ~23255/23269/23289), 6 test files, seed 209, six live docs + AGENTS.md, the renderer, and the upgrade map; 15 historical wave records plus telemetry/CHANGELOG lines retain the old name. | `grep -ric wf_review_evidence`; `server_impl.py` extractor maps; seed 209 recipe vs Review Runs section; `review_evidence.py` error branches; 1tbt5 events.jsonl |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-24 | Rename `wf_review_evidence` → `wf_review_event`, clean, no alias, folded into this change. | The tool inspects and appends typed review events; "evidence" is one produced record type. The name mislabels the abstraction and is the same public usability defect as the recipe/error gaps. No broad distribution yet, so no alias is warranted. | Keep the name and fix only docs (rejected: the misleading name is itself the defect); register a compatibility alias (rejected: not distributed; an alias is permanent surface debt). |
| 2026-07-24 | Fix guidance in both the seed AND the tool docstring; sharpen (not re-document) field placement; correct the actor model. | The recipe is duplicated in both surfaces; the docstring already documents the field split; the chain uses a distinct implementer and blocking reviewer lane. | Update only the seed (rejected: leaves the docstring wrong); claim field placement undocumented (rejected: inaccurate). |
| 2026-07-24 | Defer a composite repair-chain authoring helper. | The repair_start→reverification split encodes repair-before-verify chronology the audit ledger depends on; collapse it only if manual sequencing still recurs after the rename/recipe/error fixes. | Build a one-call composite now (rejected: premature; adds a code path to the most integrity-sensitive tool before the cheaper fix is proven insufficient). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| An incomplete rename leaves a dangling `wf_review_evidence` reference on a live surface | Case-insensitive rename-gate census as an AC; fresh-process reload tool-list verification confirms only the new name registers. |
| A missed extractor-map key silently drops telemetry credit for the renamed tool | AC-2 pins the extractor keys and the explicit-wave attribution + repeat-list-neutrality tests under the new name. |
| Historical records or telemetry rows get rewritten by an over-broad rename | AC-7 excludes closed wave records, prior telemetry rows, and past CHANGELOG entries; the census separates live from historical surfaces. |
| Seed and docstring recipes drift apart again | Both are updated in the same change and the render is regenerated from the seed via the canonical renderer. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
