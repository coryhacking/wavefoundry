# Tensorwell Memory Reranking

Change ID: `20l7y-enh tensorwell-memory-reranking`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-13
Wave: `20lul tensorwell-memory-reranking`

## Rationale

The optional Tensorwell integration serves normal embeddings and search reranking, but memory retrieval still constructs a separate CPU INT8 reranker inside MCP. The operator requests that memory search also use the qualified Tensorwell reranker so the MCP process does not need that extra local model while the service is available. This is a separately tracked follow-up because memory retrieval's absolute raw-logit cutoff requires its own qualification beyond normal search ranking.

## Requirements

1. `WaveIndex._get_memory_reranker` selects the existing qualified Tensorwell adapter before inspecting or constructing a local reranker. Successful service selection must not construct a local ONNX session, even if the local failure cache is set.
2. Preserve explicit reranker-disable and Tensorwell/provider opt-out controls. If service selection is unavailable, preserve the existing cached CPU INT8 fallback for machines without Tensorwell; do not change that fallback's provider or singleton behavior.
3. Preserve memory search's raw-logit cutoff `>= -4`, pre-gate candidate cap, summary input, order, no-refill behavior, provenance and recovery semantics. A selected service operation failure must use existing honest lexical recovery, never silently construct a local reranker or publish partial service scores.
4. Qualify the service against the frozen memory-retrieval corpus and its independent relevance labels, separately from the existing FP32 normal-search oracle. Compare against the existing CPU INT8 singleton reference, report cutoff disagreements and relevant-item retention, and require no regression in the fixture's established quality criteria. The fixed reference is wave 1yad2’s `qualification-inputs.json.gz` and `summary5-integration-preflight.json.gz`: 24 cases (16 answerable, eight no-match), 120 frozen candidate pairs and unchanged existing labels. Require no loss of useful query support, no new no-match returns, no loss of recall@3/10 or MRR, and no lower independently judged direct-support precision than the current CPU reference. Preserve historical adjacent-context labels; independently review any newly admitted candidate for direct support. This wave makes no timing claim or latency comparison. Do not tune a threshold, invent equality across precisions, or relabel examples to force qualification; a failed quality criterion requires revisiting this plan before adoption.
5. Keep native model tests opt-in and bounded, using an already-running qualified service and cached reference files only. Ordinary suite tests remain hermetic. Update memory routing documentation to distinguish search relevance from approval validation.

## Scope

**In scope:** memory reranker selection; integration/fallback/recovery regression tests; bounded native memory qualification oracle; affected architecture and operator contract docs.

**Out of scope:** service installation or lifecycle changes, Tensorwell source edits, model pin/identity or cutoff changes, live memory/index publication, broad retrieval redesign, benchmarks, unloading models loaded earlier, closing or committing either wave.

## Acceptance Criteria

- [x] AC-1: A memory search using a qualified Tensorwell pair obtains raw scores through that adapter without constructing a local reranker; registered-path or production-handler tests trap local construction and verify actual score consumption.
- [x] AC-2: Disabled reranking, Tensorwell opt-out, absent/incompatible service and existing local-cache/failure cases preserve their documented fallback or disabled behavior in isolated controls.
- [x] AC-3: Boundary scores below, equal to and above -4 preserve the memory gate's cap, ordering and no-refill contract. A service failure yields existing degraded retrieval with no local reranker retry or partial service-score publication.
- [x] AC-4: The bounded native qualification reports the frozen corpus/profile/reference identities, cutoff differences and independently labeled relevance outcomes, meets the existing quality criteria, and distinguishes numerical parity from retrieval quality. The oracle rejects deliberately degraded scores.
- [x] AC-5: The change's tests pass and modified docs validate; documentation describes Tensorwell memory retrieval, local fallback conditions and qualification limits accurately.

## Tasks

- [x] Establish the frozen memory oracle inputs, baseline criteria and current routing controls.
- [x] Route memory reranking through Tensorwell first and add hermetic production-path regression controls.
- [x] Add and execute bounded native memory qualification with cached CPU INT8 reference and the running service.
- [x] Update docs, perform focused independent delivery review and final framework qualification.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Discovery and native feasibility | implementer | — | Read-only; no source edits or live memory mutation |
| Readiness | council-chair and independent seats | discovery | Failure-first plan review |
| Source and tests | implementer | readiness | Coordinator-owned serial writes |
| Delivery | independent required reviewers | implementation | Frozen source, bounded controls |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/test_memory_records.py`
- `.wavefoundry/framework/scripts/tests/test_tensorwell_integration.py`
- `.wavefoundry/framework/scripts/tests/oracle/tensorwell_memory_parity.py`
- `.wavefoundry/framework/README.md`
- `docs/architecture/embedding-model.md`
- `docs/architecture/search-architecture.md`
- `docs/architecture/testing-architecture.md`
- `docs/specs/mcp-tool-surface.md`
- `docs/references/memory-retrieval-eval.md`

CHANGELOG.md records the behavior. Historical qualification artifacts are read-only inputs. No source edits before readiness; no code changes during independent delivery review or final qualification.

## Affected Architecture Docs

`docs/architecture/embedding-model.md`, `docs/architecture/search-architecture.md` and `docs/architecture/testing-architecture.md`: selection, failure boundary and memory-specific evidence. `docs/specs/mcp-tool-surface.md`, `docs/references/memory-retrieval-eval.md` and the framework README retain the operator contract.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Operator's requested memory reduction and service reuse |
| AC-2 | required | Preserve optional-service deployment and explicit controls |
| AC-3 | required | Retain trustworthy memory relevance and failure semantics |
| AC-4 | required | Absolute relevance thresholds need distinct numerical/quality qualification |
| AC-5 | required | Reproducible behavior and truthful documentation |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-13 | Thought: inspect memory-specific score qualification before changing selection; normal-search parity is insufficient for an absolute cutoff. | `_get_memory_reranker`, `_memory_query_records`; existing frozen memory qualification corpus |
| 2026-10-13 | Discovery: the separate model is for memory retrieval relevance, not approval publication; native comparison is read-only and bounded. | MCP targeted source reads and independent discovery |

| 2026-10-13 | Observe: qualified service fixture still constructs the CPU model; the baseline must fail the intended no-local-model outcome. Native feasibility compared 120 frozen pairs: one newly admitted labeled-relevant item, no useful-support losses, all eight negative cases empty; max absolute CPU/CoreML logit delta 0.825978279. | Actual `_get_memory_reranker` constructor trap: service qualified, returned service false, local constructor calls 1; bounded native diagnostic in temporary storage |

| 2026-10-13 | Readback: memory retrieval will select the qualified Tensorwell adapter before any local cache or constructor; explicit disable and absent-service CPU fallback remain. The combined integration control covers embeddings, normal reranking and memory reranking without local session creation. Existing cached fallback sessions are not evicted by this narrowly scoped change. Before: qualified service plus memory search constructs CPU model; after: memory scores arrive through the same service adapter. | AC-1 through AC-5; `WaveIndex._get_memory_reranker`, Tensorwell integration and memory regression tests, native oracle and named docs |

| 2026-10-13 | Implemented service-first memory selection and truthful retrieval docs. Three new hermetic production-handler tests fail the old getter; all four routing controls pass the repair. Integration module: 13 tests; memory qualification class: 11 tests; docs lint clean. Combined constructor traps cover embedding and both rerankers, including old local cache/failure state; late malformed service batch gives lexical recovery with no partial scores or local retry. | `test_tensorwell_integration.IntegrationTests`; `test_memory_records.MemoryQueryQualificationTests` |
| 2026-10-13 | Native qualification PASS: 24 cases/120 pairs, useful cases 15 to 16, recall@3/10 .84375 to .90625, MRR .833333 to .895833, direct-support precision 15/21 to 16/22, all eight negatives remain empty. One cutoff flip (-4.178757 to -3.698660) independently judged direct support; no original blind label changed. Max absolute logit delta .825978; no numerical-equivalence, timing or RSS claim. Child exited successfully. | `tests/oracle/tensorwell_memory_parity.py`; input/reference/profile digests emitted by the repeatable oracle; native output held only in temporary storage |
| 2026-10-13 | Gapfill: used bounded filesystem reads for prose-only documentation updates and Git blob hashes for the review packet; implementation navigation and consumer validation used MCP code reads. Hardened fixture constructors/offline environment after an initial baseline test reached a refused download attempt; interrupted/reaped that child and reran isolated controls cleanly. | Current getter and consumer source; focused controls above |

| 2026-10-13 | Delivery found two fixture issues: canonical runner disable environment bypassed existing CPU controls, and intentional tool-description text changed its frozen digest. Recorded D1/D2 repair start before one fixture-only batch. Explicitly enabled mocked CPU fallback/service absence in the two old controls and updated only the supporting golden handler digest. No production semantics or admission changed. | `test_memory_records.MemoryQueryQualificationTests`; `test_mcp_tool_registry.HandlerDigestTests`; supporting `tests/fixtures/register-surface-handler-digests.json` |

| 2026-10-13 | Final qualification passed: 12,504 tests across 187 files, 12 existing skips, 763.799 seconds with six workers. Fresh independent code and QA cleared D1/D2; required performance control and its memory-selection negative control passed. Full docs validation passed. | Canonical `run_tests.py` green receipt; typed delivery evidence and durable regression tests |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-13 | Reuse the qualified adapter first, preserving CPU fallback and the unchanged relevance gate; qualify memory separately. | Smallest change that removes duplicate inference while preserving optional deployment and measurable quality. | Keeping CPU always misses the request; removing all fallback makes Tensorwell mandatory; blindly reusing normal-search parity does not verify the absolute cutoff. |
| 2026-10-13 | Separate follow-up wave from 20nju. | The original wave is fully reviewed; absolute memory relevance qualification was explicitly outside it and deserves a bounded separate review. | Reopening the completed implementation would broaden its original acceptance packet. |

## Risks

| Risk | Mitigation |
| --- | --- |
| FP16 service and INT8 reference disagree near the cutoff | Native labeled-corpus qualification with disagreement reporting; no automatic cutoff changes |
| Tests accidentally contact the live service or load a model | Patch selection explicitly; constructor traps and isolated fixtures |
| Selected service failure silently changes provider | Exercise production recovery and assert no local construction |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
