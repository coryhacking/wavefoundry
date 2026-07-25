# memory-propose decision-log path extracts harness and prose tokens as targets

Change ID: `1tis7-bug memory-propose-decision-log-harness-target`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-24
Wave: `1tis8 memory-eval-mcp-tool-and-decision-log-target`

## Rationale

Wave `1tgkx` fixed the harness-token misattribution on `memory_supply.draft_candidates`'s **repaired-finding path (B)**: it filters `run_tests.py` and the configured `test_runner` entry out of targets extracted from finding evidence. But `draft_candidates` has a **second target-extraction path (A)** — Decision Log rows — that was explicitly left out of 1tgkx's scope and is unfiltered.

This was proven live at 1tbt5's close. `memory_propose(1tbt5)` drafted a `decision` candidate from the `1tgkx` Decision Log whose targets were `["run_tests.py", "test_<module>.py"]`. Path A extracts `_code_targets(row["refs"])` directly from the decision/reason prose refs, with no harness filter, so:

- `run_tests.py` (named in the decision prose because the decision is *about* filtering it) became a target — the exact misattribution 1gkx set out to end.
- The literal placeholder `test_<module>.py` (an illustrative token in the prose) became a "target", which is not even a real file.

The decision actually governs `memory_supply.py`'s `draft_candidates`, not the verification harness. The candidate was rejected at close as a duplicate of the active `1tdmn-mem`, but the drafting defect remains: any decision whose rationale mentions the test runner or an illustrative file token will mis-anchor. Path A is inherently noisier than path B because it mines prose refs rather than repaired-surface evidence.

## Requirements

1. **Apply the harness-token exclusion to the decision-log path.** The same test-runner-entry filter used on repaired-finding targets (canonical `run_tests.py` plus the `docs/workflow-config.json` `test_runner` entry, with graceful absence) must also apply to targets extracted from Decision Log rows, so verification-runner tokens never become decision targets.
2. **Drop non-file placeholder tokens.** Illustrative or placeholder tokens containing `<`/`>` (e.g. `test_<module>.py`) must not be admitted as targets from prose refs. *(Revised during implementation: an additional "does not resolve to a tracked file" screen was implemented, proved net-negative, and withdrawn — decision docs legitimately name paths absent at drafting time. See AC-2 and the Decision Log.)*
3. **Preserve genuine decision targets.** A decision whose prose legitimately references the real module it governs still drafts with that module as the target; the conservative rule stands — if no qualifying target survives, draft the candidate with no target only where the schema allows, or draft nothing, consistent with the existing path behavior.
4. **Regression corpus from a real decision doc.** Tests replay a decision-log row shaped like the `1tgkx` case (prose naming `run_tests.py` and a `test_<module>.py` placeholder alongside the real governed module) and assert the harness/placeholder tokens are excluded while the real module survives.
5. **Reconcile the decision memory.** Confirm the existing active `1tdmn-mem` (or its lineage) still expresses the exclusion rule now that it covers both paths; update its action delta if it implies path B only.

## Scope

**Problem statement:** `draft_candidates`' Decision Log path extracts verification-runner and non-file placeholder tokens as targets, re-introducing the harness misattribution 1tgkx closed only for the repaired-finding path.

**In scope:**

- The Decision Log target extraction in `.wavefoundry/framework/scripts/memory_supply.py` (`draft_candidates` path A / `_decision_log_rows` consumer).
- Reuse of the existing `_test_runner_entry_names` filter and a non-file-token guard.
- Regression tests in `test_memory_records.py` derived from a real decision-log shape.
- Reconciling `1tdmn-mem`.

**Out of scope:**

- The repaired-finding path (already fixed by 1tgkx).
- Retrieval/ranking and the eval (companion change `1tgws`).
- Rewriting historical rejected/superseded records (the 1tbt5 `1tidv-mem` reject stands as history).

## Acceptance Criteria

- [x] AC-1: a decision-log row naming `run_tests.py` (or the configured `test_runner`) plus a `test_<module>.py` placeholder alongside the real governed module drafts a candidate whose targets exclude the runner and the placeholder and include the real module.
- [~] AC-2: no non-file placeholder token (containing `<`/`>` or not resolving to a tracked path) is admitted as a target from prose refs. — **narrowed during implementation:** the angle-bracket placeholder half is met and enforced for every caller in `_code_targets`. The "not resolving to a tracked path" half is **intentionally not implemented**: an existence check against the repo dropped legitimate targets and broke 12 existing tests (decision docs and fixtures name paths that do not exist at drafting time, e.g. a module the decision introduces or a path recorded before a rename). The placeholder and runner screens fully cover the observed defect; an existence guard is net-negative. Recorded in the Decision Log.
- [x] AC-3: a decision-log row that legitimately names only its governed module still drafts with that module as target (no over-filtering).
- [x] AC-4: `1tdmn-mem` reflects the both-paths exclusion rule; docs gate and full framework suite green.

## Tasks

- [x] Apply `_test_runner_entry_names` + a non-file-token guard to the Decision Log target extraction.
- [x] Producer-derived regression tests (harness/placeholder excluded, real module preserved).
- [x] Reconcile `1tdmn-mem`; docs gate; full suite.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| extraction | implementer | — | Path A filter + non-file-token guard in draft_candidates |
| regression | qa-reviewer | extraction | Real decision-log shape, both directions |

## Serialization Points

- None; single-module change with its tests. Independent of companion change `1tgws`.

## Affected Architecture Docs

N/A — confined to `memory_supply.py`'s drafter and its tests; no boundary, flow, or verification-architecture change. `docs/agents/memory/README.md` gets a note only if the rule becomes operator-visible.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect being fixed: harness/placeholder tokens must not become decision targets. |
| AC-2 | required | The non-file-token guard is half the fix; the literal placeholder must not become a target. |
| AC-3 | important | Preventing over-filtering keeps genuine decision targets intact. |
| AC-4 | required | Reconciling the decision memory and the standard gates. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-25 | Implemented. `_code_targets` now rejects angle-bracket placeholders for every caller; new `_prose_targets` applies the `_test_runner_entry_names` filter to the Decision Log path. LIVE-VERIFIED against the real producer: `memory_propose(1tbt5)` — the exact call that drafted `Fragile:`-style targets `run_tests.py` and `test_<module>.py` — now drafts no mis-targeted decision. Three producer-derived tests; memory_records 178 OK. | `memory_supply.py` `_code_targets`/`_prose_targets`; `test_memory_records.py` MemoryProposeTests; live `memory_propose(1tbt5)` post-reload |
| 2026-07-25 | SCOPE NARROWED (live-caught): the planned "not resolving to a tracked path" guard was implemented, then withdrawn. An existence check dropped legitimate targets and failed 12 existing tests (fixtures and real decision docs name paths absent at drafting time). The placeholder + runner screens fully fix the observed defect; the existence guard was net-negative. AC-2 marked `[~]` with rationale. | Failing run: 7 failures + 5 errors incl. `src/kept.py` dropped; green after withdrawal (178 OK) |
| 2026-07-24 | Drafted from the live 1tbt5-close reproduction: `memory_propose(1tbt5)` drafted a decision candidate targeting `run_tests.py` and `test_<module>.py` via the unfiltered Decision Log path. 1tgkx fixed only the repaired-finding path. | 1tbt5 close `memory_propose` output; `memory_supply.py` `draft_candidates` path A; rejected candidate `1tidv-mem`; active `1tdmn-mem` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-24 | Extend the harness-token exclusion to the decision-log path and reject non-file placeholder tokens. | Path A mines prose refs, so it re-introduces the exact misattribution 1tgkx closed for path B; the same filter plus a real-file guard is the minimal fix. | Rework how decision targets are derived (e.g. prefer the change doc's In-scope targets over prose refs) — deferred as larger than the observed defect. |
| 2026-07-25 | Do NOT screen prose targets by on-disk existence; keep the angle-bracket placeholder and runner-entry screens only. | Implementation proved the existence check net-negative: decision docs legitimately name paths absent at drafting time (a module the decision introduces, a pre-rename path), so it dropped genuine targets and broke 12 tests. The two remaining screens fully cover the observed defect. | Existence check on refs containing a directory separator (tried, withdrawn — still dropped fixture and real targets); repo-walk basename resolution (rejected — cost and fragility exceed the benefit). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A decision that genuinely governs the test runner would draft nothing | Same conservative tradeoff accepted for path B: a suppressed true signal costs less than a minted false one; the corpus test pins the accepted behavior. |
| Over-eager non-file guard drops a real but oddly-named path | REALIZED during implementation for the on-disk-existence half, which was withdrawn. The shipped guard keys only on angle-bracket placeholders and runner-entry basenames, never on general naming or resolvability; `test_decision_prose_keeps_the_governed_module` pins a real module through. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
