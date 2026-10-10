# Pack-profile fixture QA delivery

Owner: Engineering
Status: active
Last verified: 2026-10-08

Independent lane: `qa-reviewer`; context `pack_qa_delivery-204mk-20261008`. This explicitly requested artifact records the bounded test-oracle review for change `204hj-bug reload-probe-profile-portability`; it does not record wave state or replace typed review events. No source, changelog, wave record or ledger was edited by this lane.

Assessment: approve the repaired fixtures within the selected scope. No blocking defect found. Canonical and full packaging-profile qualification remain coordinator gates; the focused runner explicitly reports that it writes no delivery receipt. This report does not claim those suites, packaging or release qualification succeeded.

## Frozen tree

The briefing and final `git hash-object` values match:

| Path | Working-tree blob |
| --- | --- |
| `.wavefoundry/framework/scripts/tests/test_distribution_seams.py` | `c81059293654443b6a9c98759e4dc4735874fe18` |
| `.wavefoundry/framework/scripts/tests/test_vocabulary_prompt_names.py` | `2ee364b4cb5e4e47bfb2f768eac3aee33314454a` |
| `CHANGELOG.md` | `604748186bdb903ecba78c2cf6105a73cb17c303` |

MCP `code_read` and `code_keyword` were discovered in `ALL_TOOLS`, called successfully, and used for the current owner assertions, eviction block, declaration support, change ACs and seed-209 evidence protocol. No missing-tools fallback was needed. Git diff supplied the exact two-file repair. Read-only repository orientation and review history were context, not approval evidence.

## Independent reference and selected cells

The independently read change requirements and AC-1–4 require preservation of the initial kind set, successful real reload, detection when `lifecycle_id` stays stale, and first-render stock-surface identity despite ambient extension declarations. These are the reference; the implementation's explanation is not the oracle.

Selected cells: default/second/declared reload; default/declared stock first render; successful reload with only lifecycle eviction disabled; stock first render with stale copied skill; valid extra `probe0` causing candidate selection of `probe1`. The expected kind-set invariant is `after == before union {new_kind}`, with `new_kind` absent before. Expected stock render is no written paths and identical whole-tree digest on the first invocation. Common-mode limitation: the original owner tests and fixtures still share their normal environment, so the mutation controls show these specific assertions are discriminating, not universal profile compatibility.

## Executed owner runs

Run serially in order, with host permission for existing local socket/process fixtures:

```text
python3 .wavefoundry/framework/scripts/run_tests.py --file test_distribution_seams.py --file test_vocabulary_prompt_names.py
python3 .wavefoundry/framework/scripts/run_tests.py --profile second --file test_distribution_seams.py --file test_vocabulary_prompt_names.py
python3 .wavefoundry/framework/scripts/run_tests.py --profile declared --file test_distribution_seams.py --file test_vocabulary_prompt_names.py
```

| Profile | Distribution seams | Prompt names | Runner total | Skips | Result |
| --- | --- | --- | --- | --- | --- |
| default | 36 tests, 6.797 s | 36 tests, 24.352 s | 72 tests, 24.355 s | 0 | OK |
| second | 36 tests, 7.615 s | 31 tests, 24.220 s | 67 tests, 24.223 s | 4 | OK |
| declared | 36 tests, 8.127 s | 36 tests, 26.096 s | 72 tests, 26.097 s | 0 | OK |

The second profile's skips are the existing default-profile-only guards; notably `DefaultRenderIdentityTests` already carries `default_profile_only`, which was not added by this repair. AC-4 selects default and declared cells, both executed with zero skips. The reload owner executed under all three profiles; none of the selected checks skipped unintentionally. Reported test counts above preserve the runner's output rather than reconstructing its counting conventions. Profile logs: `/tmp/wf204mk-qa-second.log`, `/tmp/wf204mk-qa-declared.log` (temporary convenience copies; named test anchors and this report are the durable evidence).

## Mutation and adjacent-control table

Sweep rule: targeted original owner test per mutant; whole-file sweeps only for survivors. Both mutants were killed, so no mutant whole-file sweep was required. All mutation/injection writes were scratch-only.

| Mutant or control | Actual original assertion | Expected | Observed | Verdict |
| --- | --- | --- | --- | --- |
| Delete only the single `"lifecycle_id",` member from copied `wf_server/server_impl.py` eviction set | `LifecycleIdReloadTests.test_reload_refreshes_lifecycle_id`, JSON `assertEqual` | Child reload succeeds, owner rejects stale choices | `reload_status="ok"`, `new_kind="probe0"`, `new_absent_before=true`; `kind_choices_fresh=false`, `validators_bind_fresh=true`; original equality fails. One test, one failure, zero errors/skips | killed for intended reason |
| Append stale bytes to the copied `.codex/skills/wf-guru/SKILL.md` during fixture copy, before its first render | `DefaultRenderIdentityTests.test_render_of_this_repository_writes_nothing`, `assertEqual(written, [])` | First-render write violates identity | Renderer returns exactly `[".codex/skills/wf-guru/SKILL.md"]`, whole-tree digest changes; original zero-write assertion fails. One test, one failure, zero errors/skips | killed for intended reason |
| Valid scratch extra-kind declaration `("probe0",)` with unchanged production eviction | Same original reload test | Select absent `probe1`, retain existing `probe0` | `reload_status="ok"`, `original_extras=["probe0"]`, `new_kind="probe1"`, `new_absent_before=true`; both freshness and binding values true. One test, zero failures/errors/skips | adjacent collision control passes |

Reproduction: import the original owner in a fresh Python process with scripts and tests on `sys.path`; copy scripts with bytecode excluded; patch only owner `SCRIPTS` to this copy. For the eviction mutant, delete precisely `            "lifecycle_id",` from copied `wf_server/server_impl.py` (one occurrence). Run `LifecycleIdReloadTests('test_reload_refreshes_lifecycle_id')` using `unittest.TextTestRunner`; its own method performs the nested copy, real thin runner `perform_mcp_reload` and original assertions. An observer print inserted immediately before the existing successful-reload assertion records status/preconditions, leaving the final JSON and owner assertions unchanged. For collision, replace only the copied one-line `EXTRA_CHANGE_KINDS` declaration with `("probe0",)` and run the same method and observer.

For stale-skill, run the unchanged original `DefaultRenderIdentityTests` method while wrapping its `shutil.copytree`: after copying the source repository `.codex`, append `\nStale QA fixture bytes.\n` to the destination's existing `skills/wf-guru/SKILL.md`. Wrap the real `render_agent_surfaces` only to record its returned paths and pre/post digest; do not pre-render, replace results or replace assertions. The original first-render assertion must fail naming that skill. The scratch harness and captured output are `/tmp/wf204mk_qa_controls.py`, `/tmp/wf204mk-qa-reload-mutant.log`, `/tmp/wf204mk-qa-stale-skill.log`, `/tmp/wf204mk-qa-collision.log`; the algorithm and assertion anchors above retain reproducibility after temporary artifacts expire.

## Approval judgment facts for coordinator

```json
{
  "claim_id": "approval:qa-reviewer",
  "claim_kind": "approval",
  "required_for_approval": true,
  "phase": "delivery",
  "proposition": "The two repaired fixtures execute their selected profile cells and reject the selected stale-lifecycle and stale-stock-surface controls through their original owner assertions.",
  "counterexample_or_failure_condition": "A selected positive cell fails or skips unintentionally, reload loses an initial kind, lifecycle eviction mutant passes, or stale copied stock skill passes its first-render identity assertion.",
  "execution_status": "executed",
  "public_path": "run_tests.py focused owner subprocesses; thin runner perform_mcp_reload; real render_agent_surfaces on copied repository stock surfaces",
  "command_or_fixture": "The three serial owner commands and targeted scratch controls recorded in this report",
  "expected": "Selected positives succeed; only removing lifecycle eviction yields successful reload with stale kind set rejected; stale skill yields first-render write rejected; probe0 collision selects probe1 and preserves probe0.",
  "observed": "Default and declared: 72 tests, zero skips; second: 67 reported tests, four existing guard skips outside selected AC4 cells. Reload mutant fails original freshness equality despite status ok; stale skill fails original written==[] assertion; collision original assertion succeeds.",
  "artifact_or_test_id": "docs/waves/204mk pack-profile-qualification/qa-delivery.md; LifecycleIdReloadTests.test_reload_refreshes_lifecycle_id; DefaultRenderIdentityTests.test_render_of_this_repository_writes_nothing",
  "adjacent_controls": ["serial default/second/declared owners", "probe0-present valid extra-kind collision"],
  "test_ran_without_unintended_skip": true,
  "public_path_reached": true,
  "boundary_values_realistic": true,
  "assertions_non_vacuous": true,
  "known_bad_detected": true,
  "known_bad_detection_method": "focused-mutation",
  "limitations": "Bounded fixture approval only. Full canonical and packaging-profile suites, framework receipt and pack creation remain pending coordinator gates; focused run_tests reports are not full delivery receipts. Second stock identity cell is intentionally excluded by its pre-existing default-only guard and is outside AC4. No exhaustive custom-profile or platform qualification.",
  "safety_and_authorization": "Authorized independent QA with host permission for existing local fixtures. Mutations confined to temporary scripts/surface copies; no production source or lifecycle state modified.",
  "probe_class": "local_safe",
  "authorization_status": "authorized",
  "safe_boundary": false,
  "unexecuted_remainder_prohibited": false,
  "universal_claim": false,
  "verification_context": {
    "actor": "qa-reviewer",
    "context_id": "pack_qa_delivery-204mk-20261008",
    "fresh_context": true,
    "independent": true
  }
}
```

All five integrity booleans are affirmed only for the selected executed checks. The reviewer did not implement either repair. No approval of the pending canonical full-suite gate is implied. No finding is invented solely because a broader run remains pending.

## Bounded packaging skip audit

This later audit is separate from the fixture approval above. Coordinator-reported canonical full qualification was 11,894 tests / 174 files / 20 skips; serial second qualification was 11,886 / 174 / 53 skips. The earlier declared run reported 39 skips but also failed and is not qualification; a serial declared rerun was still active during this audit. These full-suite facts are attributed to coordinator logs, not rerun by this lane.

`run_tests._run_file` derives skip telemetry from the final unittest summary and binds it to the final test-count block; it does not aggregate arbitrary nested runner telemetry. `_profile_run_in` copies tracked/untracked non-ignored files and creates a new one-commit Git repository, without source Git history or the ignored local index. The active declared copy had no `.wavefoundry/index`, `v1.14.0`, `v1.22.0` or version-1 reader commit; canonical has `index.sqlite` and the historical tags.

The declared skip delta of 19 is attributable to these source-level branches:

| Cause | Tests affected | Count | Evidence status |
| --- | --- | --- | --- |
| Missing historical Git objects | `ReviewPolicyReconcilerTests.test_real_v114_carrier_family_reconciles_and_retries_byte_stably`; `test_real_v114_carriers_render_policy_and_pass_production_validator` | 2 | Source branch and missing-copy/present-canonical tag verified |
| Missing historical Git objects | `StorageUpgradeProcessResumeTests.test_old_main_pause_then_fresh_installed_main_relocated_pack_and_retry`; `SchemaEightKindTests.test_version_one_code_refuses_a_version_two_receipt_and_creates_nothing` | 2 | Executed in the existing declared copy: both skipped with exact historical-tag/commit reasons, not missing dependency reasons; 2 tests / 2 skips / 2.346 s |
| Missing ignored published SQLite graph | `EvidencePartitionResponseTests` (8 methods); `EvidenceNodesStayQueryableTests` (5 methods); `EvidencePairDocumentationTests.test_the_pair_list_matches_what_the_report_actually_emits` | 14 | Enumerated source methods, real graph-presence guards and absent-copy/present-canonical index verified; individual full-run skip records were not retained by the runner |
| Blanket named-profile guard | `IsChangeIdTests.test_accepts_every_admitted_id_in_this_repository` | 1 | `@unittest.skipUnless(_same_profile_run(), ...)`; `_same_profile_run` is exactly `not os.environ.get("WAVEFOUNDRY_TEST_PROFILE")`, so declared skips even with unchanged vocabulary |
| **Total** | | **19** | Source attribution matches observed delta; not a new 19-test execution |

The ANN report explanation was ruled out: `docs/reports/ann-reference-post-1wsc8.json` existed in both canonical and active declared copy. Seven live graph checks in `test_graph_quality_eval` read the retired `.wavefoundry/index/graph/project-graph.json`, absent in both trees; they cannot explain the additional delta. Do not count their skips again.

Second has a further 14 skips beyond this copy-related delta (`53 - 20 - 19`). Static enumeration found 15 real `default_profile_only` sites across nine owners; its runtime predicate checks vocabulary/layout differences, and class guards count as one unittest setup skip rather than their suppressed methods. This supports profile-guard attribution, but exact net-14 overlap with canonical pre-existing skip reasons remains **inferred**, because the full-run per-test skip details were not retained. It is not evidence that every one of the second profile's 53 skips satisfies the packaging prompt's rule.

Qualification limit: the declared run's strict no-extra-skip criterion is not met by these known copy/history/profile guards, and the second rule that extra skips be `default_profile_only` is not satisfied by these 19 paths. No fixture skip was added in this repair. Do not claim strict release qualification or silently waive these differences. Any explicitly permitted local-pack exception must be operator-owned and recorded separately from QA fixture approval. No source was changed and no additional full suite was run in this audit.
