# Independent security and architecture review — 1ymzq

Owner: Engineering
Status: active
Last verified: 2026-09-22

Verdict: approved in security and architecture scope, with R2 / final baseline completion reserved to the coordinator and QA. No blocking security or architecture finding. This is not a wave closure authorization or a claim that the unchecked index AC-5 is complete.

Reviewer context: fresh independent worker `/root/split3_security_primer`, not an implementation worker. Security, architecture and adversarial-primer perspectives below share this context and are correlated; they must not be counted as independent seats. Budget: 12 minutes; targeted mutation tests, no whole-file mutant escalation because no mutant survived.

Reviewed fingerprint: v2 `/private/tmp/1ymzq-delivery-fingerprint-v2.json`, SHA256 `7d69750f1514d43c92f20b5b68749688b2776ccb5862b5bacd4c66d249808577`. V1 moved under review in six documentation paths and is superseded. Independently reconstructed the old hashes by changing only `Last verified` from 2026-09-22 to 2026-09-21; all six matched v1 exactly. Code remained unchanged. Final v2 comparison found zero changed paths.

Integrity declarations: fresh_context=true; independent=true; implementation_participant=false; code_tree_stable=true; v1_tree_moved_under_review=true; v2_tree_stable=true; repository_edits_by_reviewer=false; source_mutations_restored=true (all mutations were temporary in-memory substitutions or disposable test scratch); claimed_all_required_ACs_complete=false.

## Full adversarial primer (sent before lane conclusions)

Strongest challenge: behavior-preserving extraction can weaken containment by adding resolution or swallowing errors, while re-exports hide stale identities and inert monkeypatch seams after reload. AST parity alone does not establish the boundary.

Best alternative: caller-owned IO and failure policy plus a pure already-resolved comparison; protect indexer._is_relative_to unchanged; retain public wrappers and invocation-time shared-helper lookup. Keeping all comparison implementations local is feasible but abandons the approved consolidation without improving the now-tested failure contract.

Questions issued to council seats: exact renderer/indirect-TechDocs error contracts; missing targets, symlink escapes, root aliases, loops and strict-mode tests at callers; real reload across primitive and six handlers; CE source-guard-before-publication-lock and named patch seams; upgrade old-tree module absence and recovery; index ownership/re-export identities and distinct R2 identity; explicit plan clarification without silent AC narrowing.

## Investigation and execution

Read project orientation, map, architecture hub, handoff, Guru guidance, security/architecture role instructions, review-wave prompt and all five admitted plans. MCP-first assessment used code_ask, code_outline, code_definition and targeted code_read for the primitive, renderer, server boundary and actual structural/reload tests. Shell AST/test discovery and in-memory source substitution filled the exact mutation-census gap; they did not replace semantic orientation. No per-area AGENTS.md was found under .wavefoundry.

Fresh command: tool-venv Python, `-B -m unittest test_path_containment test_handler_modules.HandlerStructureTests test_handler_modules.HandlerReloadTests` from scripts/tests: **27 tests passed** in 16.927s. This includes on-disk symlinks, strict/missing/root aliases, Windows pure-path comparisons, original wrapper fault matrix, retained policy pins, thirty-site census, modified-scratch primitive reload and nine handler reload cases (including all six new families) reaching registered public tools.

Additional isolated targets: TechdocsAuditDegradeTests.test_docs_dir_escaping_the_root_is_refused_before_any_read and test_the_walk_never_descends_outside_the_root: **2 passed**. Three SourceGuardTests for real monitor/build exclusion, unknown acquisition preserving pending work, publication contention releasing source guard: **3 passed**. RuntimeLockCutoverMigrationTests.test_cutover_module_absence_uses_installed_modern_stop: **1 passed**. Initial standalone upgrade invocation omitted scripts PYTHONPATH and failed import before any test; rerun with `PYTHONPATH=..` passed. This was harness setup, not product failure.

The entire current indexer.py equals HEAD byte-for-byte (git show versus filesystem), establishing preservation of both helper and callers, not merely the local comparator expression.

## Mutation table

All 19 controls detected; no NOT CAUGHT result. Scripts/data: `/private/tmp/1ymzq-security-probe.py`, `/private/tmp/1ymzq-security-mutants.json`, `/private/tmp/1ymzq-architecture-mutants.py`, `/private/tmp/1ymzq-architecture-mutants.json`.

| Mechanism | Mutation | Target and observation |
| --- | --- | --- |
| Resolved containment decision | Always accept candidate | ContainedPathTests.test_directory_link_escape_with_missing_tail: 1 failure |
| Pure no-IO comparison | Resolve root and candidate again | WrapperContractTests.test_renderer_and_techdocs_resolution_matrix: 4 errors from deliberate extra-resolution bomb |
| Renderer root failure boundary | Swallow root OSError into None | Same wrapper matrix: 2 failures |
| Indirect TechDocs root failure boundary | Swallow root OSError into None | Same wrapper matrix: 1 failure |
| CE handler layering | Add local sibling import; separately eager server import | Complete-partition / locations-import tests respectively: 1 failure each |
| Docs handler layering | Same two independent mutations | Same targets: 1 failure each |
| Dashboard handler layering | Same two independent mutations | Same targets: 1 failure each |
| Edit-gate handler layering | Same two independent mutations | Same targets: 1 failure each |
| Upgrade handler layering | Same two independent mutations | Same targets: 1 failure each |
| Index handler layering | Same two independent mutations | Same targets: 1 failure each |
| Background PID identity | Copy _BACKGROUND_BUILD_PIDS in root instead of alias | Complete-partition identity test: 1 failure |
| Freshness cache identity | Copy _FRESHNESS_CACHE instead of alias | Complete-partition identity test: 1 failure |
| Dashboard PID identity | Copy _DASHBOARD_CHILD_PIDS instead of alias | Complete-partition identity test: 1 failure |

Mutants that injected imports were applied to the exact source read used by structural tests; they test guard sensitivity rather than pretending to execute a cyclic import. Behavioral containment mutations were applied to live callables. Real reload positives separately executed modified scratch modules through public registration.

## Judgments

Security: existing local-operator/same-user authority assumptions remain. No newly evidenced less-trusted actor or privilege delta, no credible exploit chain. Confinement is preserved at server_impl.py:3868 and renderer:1652; shared primitive path_containment.py:7 performs no filesystem operation. The wrapper fault matrix specifically exercises the indirect TechDocs delegation and distinguishes root OSError propagation from RuntimeError-to-None. Missing write targets remain supported. Regex/re.escape and symbol-trigger boundaries were not changed in this extraction; no broader regex audit is claimed.

Architecture: six domain owners, composition-root registrations and per-call shared helper lookup match the documented layering. All moved objects retain identity and the new family roster is structurally complete; stayers remain in the root. Real reload receives modified handlers. The CE source-guard lock sequence and upgrade module-absence fallback have fresh executed evidence. Docs accurately say upgrade inversion changes edge direction rather than eliminating server loading. Index persistence/monitor policy remains with original owners. The pure comparison's resolved-absolute/no-`..` precondition is intentional; every admitted adoption retains its original resolution/stronger policy. This is not a race-free open primitive and does not claim one.

Current-plan clarifications / readiness judgment: APPROVED for the clarified current packet associated with parent-reported receipt `94b63f24a5c63152fa15`. Independently read 53 index definitions / 12 objects / 13 direct-response members and the explicit two optimize-contract mock-owner exceptions with assertions unchanged. These clarify actual ownership and preserve test meaning, without changing substrate behavior or diluting containment AC-2. Pure-comparison repair and indexer exclusion are explicit approved contracts. R2 remains a new baseline under moved evaluator identity, never a comparable R0/R1 after measure. Parent must verify typed receipt identity/currentness before authoring readiness authority; this lane supplies substantive approval, not independent inspection of that receipt's JSON.

Required in-scope AC support: containment AC1–4; CE/index/thin-wrapper/upgrade ownership and reload AC1–3; CE interlock AC4; upgrade compatibility AC4. Overall test completeness and R2 are delegated to other lanes, not inferred from checked boxes.

Limitations: no Windows filesystem execution (PureWindowsPath is only comparison evidence); no race-free filesystem claim; no full suite rerun; no independent mutation of unchanged CE lock primitives or upgrade fallback; no R2 run. Public reload, fault-injection, on-disk symlinks, indirect TechDocs no-external-read tests and 19 controls form bounded evidence, not exhaustive dynamic call-graph proof. No new actionable finding or backlog item.

Exact executable approval integrity object (bounded evidence described above):
```json
{"test_ran_without_unintended_skip":true,"public_path_reached":true,"boundary_values_realistic":true,"assertions_non_vacuous":true,"known_bad_detected":true,"known_bad_detection_method":"focused-mutation"}
```
