# Waveforge Merge Prep Delivery Review

Owner: Engineering
Status: active
Last verified: 2026-09-21

## Review context and scope

Context: `1ym4h-independent-delivery-20260921`. One reviewer context independently reviewed both implementations and later covered the code, QA and docs-contract lanes after the host rejected further agent creation at its thread limit. These are three lane judgments from one shared review context, not three independent reviews. The reviewer implemented neither change, edited no production/test files, and formed the assessment from current code, admitted requirements and executed checks. Requested model/effort: host default; actual runtime identity unknown. Readiness currency bookkeeping is separately recorded in [readiness review](readiness-review.md#currency-reconciliation).

Reviewed scoped diffs: dashboard library/script and affected existing tests; new terminology tests; marker module, chunker, codenav handlers, renderer, server reload imports, compatibility source membership and new/changed tests; the two dashboard references and this wave's two CHANGELOG bullets. Unrelated generated docs and prior-wave CHANGELOG bullets are excluded. MCP-first searches/outlines/live reads supplied discovery and source verification; Git diff supplied exact edit comparison. No semantic-search answer was treated as proof. No source-retrieval Gapfill was needed.

Budget: one bounded review pass, three probe groups (dashboard contract/rendering, marker consumers/census, runtime compatibility/reload), with focused in-memory or temporary-copy mutations. No production mutations, external calls, new full critique, ledger edits, commits or closure. The coordinator owns the full framework suite.

## Docs-contract verdict

**Approved for the scoped contract.** The adapter reference correctly states Wavefoundry tier keys, singular labels, default/invalid normalization, the sorted ignored-key payload, lowercase/title casing, append-s plural limitation, display-only scope and the required downstream key remap. The overlapping valid `wave` key remains explicitly ambiguous; the pill does not promise tier-correctness. The install/upgrade reference removes dashboard-block seeding/backfill claims. Seed searches and the source diff show no new dashboard materializer. The review-policy carrier region was extracted from HEAD and the working file and compared byte-for-byte: identical.

The marker module docstring names the merge-time constant edit; the CHANGELOG explicitly defers the version bump and warns that consumer indexes can retain old output until affected files change or a full rebuild runs. The source diff leaves CHUNKER_VERSION unchanged. Downstream merge invalidation and Waveforge's own dashboard consumer remain unverified by design.

Executed doc verification: independent temp-root reader fixtures produced defaults for absent/non-object terminology, retained Sprint/story, dropped invalid values in sorted order, and produced `feature,set` diagnostics for the unremapped fork map. A separate Node slice produced default Waves, lowercase sprint, capitalized Storys and default reset; the actual advisory rendered one sorted pill and no node for empty/absent input. The checked-in real snapshot/render suite passed after source settled. Full `wf_validate_docs` passed with no errors or warnings before this artifact; the final artifact also passed `wf_validate_docs` with no errors or warnings.

Preexisting/outside-scope observation: adapter reference auto-index rows still describe behavior removed from `read_dashboard_config`; older endpoint metadata and sibling-runtime prose were not re-audited. These are not introduced or worsened by this wave and were not used to widen the approved scope or create a backlog.

## Code-review verdict

**Approved for the changed implementation.** The module constant has no framework imports; consumer patterns are read at call time and the stripper retains its exact newline/space boundary. Named and bare ends, annotated begins and Waveforge recognition match the explicit requirements. Runtime source membership and reload purge/import coverage preserve the existing guard and restart semantics. Dashboard normalization accepts JSON-shaped inputs, fills defaults and leaves other settings alone; payload fields are explicit. Dynamic lifecycle flow and selected-dialog lookup avoid stale labels after register changes. The full scoped JS diff preserves routing/CSS/variant identifiers and explanatory body prose; labels are routed through the helper. `docs/repo-profile.json` supplies no additional code patterns (`insufficient_history`). No seed or packaging behavior changed.

Independent reference: the admitted Requirements, read before testing, specify output labels and exact marker boundaries independently of implementation. The strongest metamorphic checks are default -> custom -> default rendering, accepted source -> same-stat byte replacement refusal -> fresh-process adoption, and namespace removal breaking three consumer oracles. These establish the named properties; they do not prove arbitrary browser interaction or every consumer repository.

## QA verdict and AC evidence

**Approved.** Scoped behavior checks and the independently verified current green full-suite receipt support AC-5 integration.

| Change / AC | Evidence |
| --- | --- |
| Terminology AC-1 | Real snapshot register tests and Node rendered default/custom/default slices; default list pinned independently of current rendered output. |
| Terminology AC-2 | Real invalid/fork-map normalization and snapshot checks; rendered one/empty/absent pill; bounded structural Dashboard hero wiring assertion as explicitly permitted. |
| Terminology AC-3 | Exact literal allowlist plus stale-entry check; planted Prepare Wave reports exactly one extra hit; identifier controls remain excluded. |
| Terminology AC-4 | Two references inspected against source, carrier compared to HEAD, and full docs validation passed. |
| Marker AC-1 | Shared module/three call-time consumers inspected; no-private-alternation census and planted-literal polarity both executed. |
| Marker AC-2 | Real chunk_file, code_read_response and section stripper; removing Waveforge from shared patterns defeats all three site assertions. |
| Marker AC-3 | Named/bare end and annotated-only/authored-content tests; four named legacy tests passed unmodified; stripper anchoring control retained. |
| Marker AC-4 | Same-stat namespace source replacement child process passes unchanged, refuses replacement with index_runtime_stale:marker_namespaces and adopts in a fresh process; import-derived purge and real MCP reload both passed. |
| Both AC-5 | Changed suites pass in this review; coordinator full run completed successfully and the reviewer independently checked the green receipt against the current source hash. |

Independent executions: `test_dashboard_terminology.py` 6/6 (after dashboard settled); `test_marker_namespaces.py` 8/8; `test_index_compatibility.py -k marker_namespace` 1/1; `test_lifecycle_gates_structure.py` selected purge-census and real-reload tests 2/2; `test_server_tools_retrieval.py -k marker_regions` 3/3; `test_chunker.py -k marker_region_only` 2/2 with `PYTHONPATH=.wavefoundry/framework/scripts`. No selected test skipped. An initial guessed reload filename discovered zero tests and was replaced with the actual discovered file; an initial chunker invocation failed import without PYTHONPATH and was rerun correctly. Neither failed invocation is counted as passing evidence. Real reload emitted existing duplicate-resource warnings but completed its fresh-module assertions.

## Focused mutation evidence

| Mechanism | Safe mutation / negative control | Detection |
| --- | --- | --- |
| Label register | Ignore supplied labels in a temporary JS copy | Rendered custom-register assertion fails. |
| Append-s plural | Remove plural suffix in temporary JS copy | Rendered labels assertion fails. |
| Advisory presence | Unconditionally return null in temporary JS copy | Actual pill render assertion fails. |
| Advisory absence | Remove empty-list guard in temporary JS copy | Empty-list null assertion fails. |
| Ignored-key payload | Patch reader result to suppress diagnostics | Real collect_dashboard_snapshot oracle fails for fork map. |
| Namespace membership | Builder omits Waveforge, patches shared module attributes | All three real consumer oracles fail as expected. |
| Named region end | Restore bare-only end regex in memory | Named-end following-prose assertion fails. |
| Annotated region begin | Restore strict unannotated begin regex in memory | Annotated-only zero-content assertion fails. |
| Namespace census | Plant duplicated namespace alternation in temp tree | Census reports one hit; repeated same name is not a hit. |
| Label census | Append Prepare Wave literal in memory | Exactly one extra literal reported. |
| Runtime source guard | Same-size replacement with original timestamps in child-process fixture | Unchanged accepted; replacement rejected for exact marker_namespaces component; fresh process accepts. |
| Reload purge | Remove marker_namespaces purge entry from source string | Import-derived missing-entry set is exactly marker_namespaces. |

Mutations were executed by this reviewer, not merely accepted from implementer reports. No mutation survived these selected assertions. No browser-wide test, downstream integration, alternate platform process test or exhaustive UI transition matrix was run. No concurrent-writer protocol was added; selected state cells were snapshot label change/reset, source replacement/restart and module reload.

## Evidence facts for typed approval

Proposition: the changed dashboard/marker behavior matches the scoped admitted contracts, and the reference/CHANGELOG edits describe its limits accurately. Failure condition: a scoped output, carrier, source guard, reload or documented boundary contradicts its promised behavior. Faithful boundaries: real read_dashboard_config/collect_dashboard_snapshot, shipped Node component slices, chunk_file, code_read_response, strip_legacy_auto_guru_section, ensure_runtime_current child process and perform_mcp_reload. Whole Dashboard rendering is deliberately outside scope; only its permitted advisory wiring assertion is structural.

Artifact/test anchors: this review; DashboardTerminologyTests; MarkerNamespaceTests; ProcessBarrierTests.test_marker_namespace_source_unchanged_passes_and_replacement_is_stale; LifecycleGateStructureTests.test_reload_purge_covers_direct_sibling_imports and test_reload_refreshes_imported_siblings_and_source_guard_callable; CodeReadEnrichmentTests marker tests; SymbolessCodeFileSummaryTests marker-only tests.

Integrity for these executed checks: test_ran_without_unintended_skip=true; public_path_reached=true at the named faithful boundaries; boundary_values_realistic=true; assertions_non_vacuous=true; known_bad_detected=true. Method: focused mutations and real same-stat source-replacement refusal as detailed above. execution_status=executed; probe_class=local_safe; authorization_status=authorized; safe_boundary=false; unexecuted_remainder_prohibited=false; universal_claim=false. Verification context is fresh relative to implementation and independent of implementers, but shared across these three lane judgments; it is not three fresh contexts. No whole-repository safety claim is made.


## Final integration verification

The coordinator's framework run completed with 9,468 tests across 119 files, exit 0, in 325.576 seconds; it reported 21 skips. This reviewer independently read `.wavefoundry/framework/test-cache.json` and recomputed `run_tests._hash_inputs()`: both equal `8e2ce791dce8b17aa48677b5eb28f3e13ebad722eac6674f6985a40952f482da`. Receipt result is `ok`, test_count is 9468, durations cover 119 files, and ran_at is `2026-09-21T19:10:31.635134+00:00`. This supports final QA approval for both AC-5s. The full run's skip reasons were not independently verified here; the selected wave-specific probes above ran without skips. The reviewer did not rerun the whole framework suite or claim to have produced the coordinator's receipt.

## Closure reconciliation

Operator authorized closure and commit on 2026-09-21. All ten scoped ACs and all tasks are met, with no intentionally unmet items. Code, QA and docs-contract approvals are recorded; no delivery Council was selected. The current framework receipt is proven. Memory proposal yielded no candidates; the retrospective lessons (retain source coverage for extracted constants and test the hook-free advisory directly) are already captured by the code/tests and change decisions.

Wave-folder cleanup retained all six wave-owned files: canonical wave/change/ledger records plus unique readiness and delivery reports. Review paths are ledger-cited, so they remain stable. No disposable scratch or redundant copy required deletion. Evidence index: [readiness](readiness-review.md), this delivery report and `events.jsonl`.

The downstream version bump/invalidation check and terminology-key remap remain assigned to the Waveforge merge, not delivered here. The single shared independent reviewer context remains an explicit review limitation. Closure writes final statuses, chronology and an idle handoff through the canonical tool.
