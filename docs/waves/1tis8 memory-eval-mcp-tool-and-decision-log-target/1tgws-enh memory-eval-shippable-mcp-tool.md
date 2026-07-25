# Memory retrieval eval as a shippable MCP measurement tool

Change ID: `1tgws-enh memory-eval-shippable-mcp-tool`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-24
Wave: `1tis8 memory-eval-mcp-tool-and-decision-log-target`

## Rationale

The memory retrieval eval (`run_memory_eval.py`) currently conflates two different things in one file under `.wavefoundry/framework/scripts/tests/eval/`:

1. **Hermetic invariant checks** (fixture corpus, recall/MRR, the 11 policy invariants) — a genuine test, pinned by `test_memory_eval.py` and run in the suite.
2. **A curated live-corpus measurement** (`run_curated(root)`, `--curated-root`) that runs the real semantic index over an actual project's memory corpus and returns aggregate quality metrics. Its whole purpose is to measure *any* project's retrieval quality over time, exactly as `wf_context_efficiency_eval` measures CE.

The measurement half is stranded by its location. `build_pack.py` `EXCLUDED_REL_PATHS` includes `scripts/tests`, so `scripts/tests/eval/run_memory_eval.py` is not packaged and never reaches a target repository; it is also excluded from the semantic index and has no MCP entry point. As built, the cross-project capability can only ever run against this repo's corpus, from a raw shell invocation, by whoever has the framework checked out. That is why every verification cycle drops to Bash for it: in a target project the script does not exist, and even here there is no typed tool to call. For a framework that dogfoods its own MCP surface, the single most common measurement action bypasses that surface entirely.

This change separates the two concerns: keep the invariant *test* where it is, and promote the corpus *measurement* to a shippable, MCP-exposed capability.

## Requirements

1. **Relocate the eval engine to shippable framework source.** Move the reusable eval logic (corpus loading, lexical/semantic ranking, RRF, metrics, adoption gate, `run`, `run_curated`) out of `.wavefoundry/framework/scripts/tests/eval/` into a normal framework module under `.wavefoundry/framework/scripts/` that `build_pack.py` includes. Fixture data that is purely test scaffolding may stay under `tests/`; the engine that a target project needs must ship.
2. **Expose the curated measurement as an MCP tool.** Add a tool (working name `wf_memory_eval`) that measures the **configured** repository — like every other tool in the surface, and per the allowed-roots safety rule, it takes no caller-supplied target directory (revised during implementation; recorded in the Decision Log). It returns the structured aggregate report `run_curated` produces: metrics, kind/status counts, content fingerprint, and adoption-gate result. It is a read-only measurement (no product mutation, no index writes), a peer of `wf_context_efficiency_eval`. Aggregate-only privacy is preserved: no record bodies, summaries, or identifiers in the response.
3. **Keep the hermetic invariants a test.** `test_memory_eval.py` continues to run the invariant checks by importing the relocated engine; the fixture-based `run()` path and its fingerprint stay test-owned. No invariant coverage is lost or moved into the shipped tool.
4. **Register the tool across the surface.** Wire it into the MCP tool census/`public_contract`, the tool-surface spec, and any docs-constants lint the way other tools are, so the tool list stays consistent and the rename/registration lints pass.
5. **Degrade honestly off-repo.** In a target project without a built semantic index or with a sparse corpus, the tool returns an explicit unavailable/partial report (mirroring the existing `curated pass unavailable` reason) rather than failing or fabricating metrics.

## Scope

**Problem statement:** the corpus-measurement half of the memory eval is a cross-project capability mis-filed as test infrastructure, so it neither ships nor is callable through MCP.

**In scope (edited under `framework_edit_allowed`):**

- Relocate the eval engine to a packaged framework module; update `test_memory_eval.py` and `run_memory_eval.py` (or its replacement CLI entry, if retained) to import it.
- New `wf_memory_eval` MCP tool wrapping the curated pass with a structured, aggregate-only envelope.
- Tool registration: census/`public_contract`, `docs/specs/mcp-tool-surface.md`, docs-constants lint, and `build_pack` inclusion.
- Reference/architecture doc updates (`docs/references/memory-retrieval-eval.md`, testing-architecture) describing the test-vs-capability split.

**Out of scope:**

- Changing the eval's metrics, adoption-gate math, or the fusion decision (1sufn stays evaluation-only and rejected).
- Any change to shipped `memory_search`/`memory_brief` behavior.
- A CLI-only story: if a shell entry is retained for CI, it wraps the same relocated engine; the MCP tool is the primary surface.

## Acceptance Criteria

- [x] AC-1: the eval engine lives in a `build_pack`-included framework module and appears in a freshly built pack; `test_memory_eval.py` passes by importing it.
- [x] AC-2: `wf_memory_eval` runs the curated pass and returns the aggregate report (metrics, counts, fingerprint, adoption gate) with no record bodies/ids; it is registered in the tool census and tool-surface spec. — **design deviation:** the tool takes NO target-directory argument. No other tool accepts one, and the allowed-roots safety rule forbids operating outside the configured root; it measures the configured repository. Recorded in the Decision Log.
- [x] AC-3: the hermetic invariant coverage is unchanged (same invariants, same fixture fingerprint) and remains test-owned.
- [x] AC-4: off-repo degradation returns an explicit unavailable/partial report rather than an error.
- [x] AC-5: docs gate, tool-registration/docs-constants lints, and the full framework suite are green; the reference docs describe the test-vs-capability split.

## Tasks

- [x] Relocate the eval engine; repoint `test_memory_eval.py` and the CLI entry.
- [x] Add and register the `wf_memory_eval` MCP tool (census, spec, docs-constants, build_pack inclusion).
- [x] Reference/architecture doc updates; docs gate; full suite; pack-inclusion probe confirms the engine is present and the fixture is not.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| relocate | implementer | — | Engine out of tests/eval into shippable source; imports repointed |
| tool | implementer | relocate | wf_memory_eval wrapper + registration |
| verify | qa-reviewer | relocate, tool | Pack-inclusion check, invariant parity, off-repo degradation |

## Serialization Points

- The tool wrapper depends on the relocated engine module path; land the relocation before wiring the tool.

## Affected Architecture Docs

`docs/references/memory-retrieval-eval.md` and `docs/architecture/testing-architecture.md` (test-vs-capability split); `docs/specs/mcp-tool-surface.md` (new tool). No boundary or flow change beyond adding a read-only measurement tool.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Without shipping, the capability cannot run off-repo at all. |
| AC-2 | required | The MCP tool is the point of the change: the measurement must be callable through the surface. |
| AC-3 | required | The relocation must not lose or weaken the hermetic invariant coverage. |
| AC-4 | important | Off-repo degradation must be honest, but sparse-corpus behavior is a graceful-fallback detail. |
| AC-5 | required | Standard gates plus the documented test-vs-capability split. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-25 | Implemented. `git mv` relocated the engine to `.wavefoundry/framework/scripts/memory_eval.py` (history preserved); `load_fixture()` now resolves the test-only golden corpus and raises a clear FileNotFoundError when absent. New read-only `wf_memory_eval` tool + `wf_memory_eval_response`. Fingerprint parity held byte-identical (`72ead292…d23f4a4`), metrics and adoption gate unchanged; pack probe confirms engine included / fixture excluded; live reload registered the tool and emitted `tools/list_changed`. | `memory_eval.py`; `server_impl.py` `wf_memory_eval`; `test_memory_eval.py` 12 OK; build_pack 101 OK; pack-inclusion probe |
| 2026-07-25 | SECOND REPAIR (blocking P2 on the GUARD, independent code-reviewer): the concurrency regression added by the first repair could not fail. `threading.Thread` swallows worker exceptions so `join()` returned normally after a crash; the behavioural half exercised hermetic `run()` rather than the MCP-exposed `run_curated()` where the corruption occurred; and its "unrelated lookup" assertion passed an EMPTY path list, which `file_commit_times` short-circuits to `{}` before touching the store — true whether or not the global was corrupted. Rebuilt: drives the real `run_curated` through a stubbed `srv.WaveIndex` with a `threading.Barrier` forcing genuine overlap, runs both calls through `ThreadPoolExecutor` so `future.result()` re-raises worker failures, asserts both reports are `available` with a non-zero sample, and probes a path deliberately seeded OUTSIDE the sampled records' targets so a leftover frozen subset answers `{}`. Structural source pin retained. | `test_curated_pass_never_rebinds_the_shared_commit_times_global`; falsification probes below |
| 2026-07-25 | Non-vacuity PROVEN by falsification rather than asserted: (A) unmodified tree PASS; (B) both workers raise -> FAIL with the injected `RuntimeError` propagated through `future.result()` (the reviewer's exact injection, which the old test survived); (C) a leftover frozen lambda installed -> FAIL on the unrelated-path assertion. The guard now fails for the two reasons it exists to catch. | Falsification harness output (A PASS / B FAIL / C FAIL) |
| 2026-07-25 | REPAIR (blocking P2, independent code-reviewer): `run_curated` rebound the shared `index_state_store.file_commit_times` global and restored it in a `finally`. Safe in the old single-shot CLI process; NOT safe once relocated into the long-lived MCP server — two overlapping `wf_memory_eval` calls restore out of order, leaving one call's frozen-subset lambda installed permanently, and unrelated concurrent `memory_search` readers observe the replacement meanwhile. Fixed by removing the global mutation entirely: `_memory_ranked` gained a `commit_times_override`, threaded through `_policy_order`/`_shipped_baseline_order`/`_candidate_and_controls`. The hermetic `run()` now SEEDS its throwaway store through the canonical `apply_freshness` writer instead of patching, so the fixture corpus is real rather than monkeypatched. A locked tool would have been insufficient: the corruption was visible to unrelated readers. Hermetic fingerprint and all comparison metrics reproduce byte-identically. | `memory_eval.py` `_seed_commit_history`/`run_curated`; `server_impl.py` `_memory_ranked`; `test_eval_never_rebinds_the_shared_commit_times_global` (source pin + two overlapping runs + concurrent watcher) and `test_frozen_histories_reach_ranking_without_global_mutation`; memory_eval 14 OK |
| 2026-07-25 | Post-restart live call proved the capability was genuinely stranded, not merely inconvenient: `wf_memory_eval()` returned `available: true` and produced the first real curated report this repo has ever had (38 records, 12 sampled; baseline recall@3 1.0 / MRR 0.9167; candidate fusion 0.25 / 0.2586, identical to lexical-only). The standalone CLI could not load the semantic backend, so the curated leg was always unavailable; the MCP server can. The result independently CONFIRMS the `1sufn` fusion rejection on real data. | Live `wf_memory_eval` envelope; contrast with the 1tbt5 record of an unavailable curated pass |
| 2026-07-25 | LIVE-CAUGHT by the new test: the diagnostic read `report.get('reason')` but the engine emits `unavailable_reason`, so the unavailable path would have surfaced a generic message instead of the real cause. Fixed and pinned by asserting the diagnostic carries the engine's actual reason. A first pass at the privacy test also substring-matched the serialized envelope and false-tripped on the prose "no surfaced records…"; rewritten to walk keys structurally. | `test_memory_eval_tool_reports_aggregate_only`; failing run before the key fix |
| 2026-07-24 | Drafted from the 1tbt5 close discussion: confirmed `build_pack.py` `EXCLUDED_REL_PATHS` excludes `scripts/tests`, so `run_memory_eval.py` is unpackaged, and `run_curated(root)` is an explicit cross-project live-corpus pass with no MCP entry. | `build_pack.py` EXCLUDED_REL_PATHS; `run_memory_eval.py::run_curated`; `wf_context_efficiency_eval` as the peer tool pattern |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-25 | `wf_memory_eval` takes no target-root argument; it measures the configured repository. | No other tool in the surface accepts a root, and the "never operate outside configured allowed roots" safety rule makes a caller-named directory the wrong shape. Cross-project use comes from the engine SHIPPING, so each project's own server measures its own corpus. | A `root` parameter with an allowed-root check (rejected: invents a resolution path no other tool has and widens the safety surface for no gain). |
| 2026-07-24 | Split the eval into a shipped MCP-exposed measurement plus a test-owned invariant check. | The curated pass is a cross-project capability; the invariants are a test. Conflating them stranded the capability under tests/. | Leave as a Bash script (rejected: never ships, never callable via MCP); make the whole thing an MCP tool including the fixture invariants (rejected: invariants are test scaffolding, not a product measurement). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Relocation breaks the test's import path or the fixture fingerprint | Repoint imports in the same change; assert the hermetic fingerprint is byte-identical before and after. |
| The tool leaks record content, breaking the aggregate-only privacy boundary | Reuse `run_curated`'s aggregate-only report shape; a test asserts no bodies, summaries, or ids in the envelope (mirrors `test_curated_unavailable_report_is_aggregate_only`). |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
