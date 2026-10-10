# Independent code and QA readiness

Owner: Engineering
Status: active
Last verified: 2026-10-08

Wave: `204mk pack-profile-qualification`
Change: `204hj-bug reload-probe-profile-portability`
Review phase: readiness
Reviewer context: `204mk-independent-pack-lane-readiness-20261008`
Review-policy receipt: `review-policy-e4e7635de4c9660a60f8`

Code-reviewer verdict: approve readiness. QA-reviewer verdict: approve readiness. No new blocking finding. These verdicts approve feasibility and the verification plan; they do not satisfy delivery evidence for any AC.

The reviewer authored neither the plan nor implementation and formed these judgments from the current source and independent execution. Both lanes used the same independent reviewer context; they are two review dimensions, not two independently corroborating reviewers. The requested workhorse/high routing was supplied by the coordinator; actual runtime model identity is not exposed.

## Current-tree evidence

MCP `code_read`, `code_keyword`, and `code_outline` were discovered and callable before source retrieval. The codebase map and root `AGENTS.md` were consulted; the map identifies no per-area `AGENTS.md` for these test/server areas. Reviewed role documents: `docs/agents/code-reviewer.md`, `docs/agents/qa-reviewer.md`; evidence contract: seed `209-agent-harness-core.prompt.md`, Executable Review Evidence Protocol.

- `test_distribution_seams._RELOAD_PROBE` requires a literal empty `EXTRA_CHANGE_KINDS` assignment, replaces it with only `spike`, calls real `runner.perform_mcp_reload()`, and reports both fresh kind availability and validator-to-module identity. `LifecycleIdReloadTests.test_reload_refreshes_lifecycle_id` checks the subprocess return code and exact two-boolean result.
- `tests/fixtures/profiles/second.json` declares `decision`. `record_layout_support.apply_profile` preserves the assignment prefix, converts JSON lists to the editable constant's tuple type, validates imported values in a fresh process, and refuses the canonical scripts tree. Therefore the literal-empty match is an invalid setup assumption for the second profile; replacing existing extras wholesale would also violate AC-1.
- `server.perform_mcp_reload` clears lazy script state, evicts `wave_lint_lib`, and actually reloads `server_impl`. `wf_server.server_impl`'s lifecycle-validation eviction block includes both `vocabulary_profile` and `lifecycle_id`. Preserving this path and the fresh validator binding tests the intended stale-module seam.
- `vocabulary_profile.change_kind_errors` defines a valid extra as a unique lower-case ASCII token of 2–16 characters, excluding core and reserved tokens. Selecting a valid candidate absent from initial `KIND_CHOICES` makes the before/after oracle feasible even when a distribution already declares `spike`.
- `test_vocabulary_prompt_names.DefaultRenderIdentityTests` copies this repository's stock surfaces, then imports the active renderer and requires its first render to return no writes and preserve `_tree_digest`. `render_agent_surfaces.declared_skills` reads the active `EXTENSION_SKILLS` at call time; `render_skills` correctly creates missing declared prompts and skills. The declared asset defines `dist-review`, so mixing its renderer declaration with stock fixture bytes is inconsistent.
- `record_layout_support.SHIPPED_DECLARATION` is intentionally separate from default vocabulary/layout marker constants: declarations do not cause `default_profile_only` to skip. `declaration_support.base_declaration` is existing test-only isolation for stock-surface tests; it patches all loaded declaration module copies and restores them afterward. Applying it around the identity fixture is feasible without changing the renderer, skipping the test, or pre-rendering its inputs.

## Executed readiness control

Two parameterized fixtures were selected within the standard 1–3 probe budget. The reload fixture covers existing default baseline, existing second-profile setup failure, and existing declared-profile reload baseline. A Python driver extracted the unchanged `_RELOAD_PROBE` using `ast.literal_eval`, copied the entire scripts tree to temporary directories without bytecode, applied each profile through the real `record_layout_support.apply_profile`, and launched `[sys.executable, '-B', '-c', probe]` with that copied scripts directory as `cwd` and `PYTHONPATH`. No probe touched canonical source.

| Profile | Initially declared extras | Process result | Observed boundary |
| --- | --- | --- | --- |
| Shipped default | `[]` | exit 0 | Real reload returned both `kind_choices_fresh: true` and `validators_bind_fresh: true` |
| Second | `["decision"]` | exit 1 | `assert text.count(old) == 1` failed in probe line 17, before the reload call |
| Declared | `[]` | exit 0 | Real reload returned both `kind_choices_fresh: true` and `validators_bind_fresh: true` |

Driver control assertions required default/declared exit 0 and second exit nonzero at the identified setup line; all completed without skips. Raw observations: `/tmp/wf204mk-lane-readiness-baseline.json`. This table is the durable observation summary.

After the coordinator amended Requirement 5 and AC-4, the second parameterized fixture exercised the existing `DefaultRenderIdentityTests.test_render_of_this_repository_writes_nothing` against a temporary declared-profile scripts tree with copied seeds/install templates. Its `REPO_ROOT` was directed to this repository solely as the stock input source; the test itself copied inputs to a fresh temporary target. Each selected run executed one test with zero skips and zero errors. No preparatory render was performed.

| Identity fixture cell | Observed result |
| --- | --- |
| Existing ambient declared profile | One assertion failure: first render wrote `docs/prompts/dist-review.prompt.md` and `.codex`, `.claude`, `.agents` `skills/dist-review/SKILL.md` |
| Existing test inside `base_declaration()` | Passed the untouched first-render zero-write, whole-tree digest, and manifest assertions |
| Same isolation with deliberately stale copied skill | One assertion failure: first render reported `.codex/skills/wf-guru/SKILL.md` after the copy hook appended stale bytes before the initial digest |

Raw observations: `/tmp/wf204mk-lane-readiness-identity.json`. This is readiness feasibility of the existing helper and oracle, not execution of a landed repair. The negative cell exercises actual `render_agent_surfaces` and the existing assertion; it would fail if the stock bytes require reconciliation. The declared ambient control independently confirms that extra writes are correct renderer behavior and that adding a profile skip would hide a mismatched fixture.

Independent references are the actual second-profile asset and the current vocabulary grammar, plus independently executed original defect reproduction. The promised property is preservation of all initial declared kinds while adding one previously unavailable valid kind, with real reload and fresh module binding. The readiness known-bad control refutes the assumption that the empty declaration is profile-independent. It does not demonstrate the future repaired test's broken-refresh detection.

## AC verification plan

| AC | Readiness assessment | Required delivery falsifier |
| --- | --- | --- |
| AC-1 | Feasible; real producer-built profile inputs reproduce the defect and baseline reload runs | Owning test fails if any original kind is lost, candidate is present before reload, candidate remains absent afterward, or validator binds a stale module; execute default, second and declared profiles |
| AC-2 | Feasible; current production eviction block provides a precise scratch-only mutation seam | Disable `lifecycle_id` refresh in the copied implementation tree; the repaired owning regression must fail its fresh-kind or binding assertion after reaching real reload, not an earlier fixture/setup assertion |
| AC-3 | Scope is bounded to test infrastructure and evidence | Diff must preserve production reload and vocabulary contracts, add no profile skip, and distinguish focused results from full-suite and packaging qualification |
| AC-4 | Feasible and directly demonstrated with existing declaration isolation and untouched owning test | Owning test passes default/declared without a preparatory render; stale copied stock bytes make its original zero-write or digest assertion fail |

The implementation must retain exact result checking, preserve existing extras, match the supported assignment formatting with an exactly-one guard, and choose an absent valid candidate. A fixed candidate such as `spike` remains insufficient for arbitrary valid profiles. The negative control must identify its mutated path and actual failure; setup refusal is not reload failure evidence.

## Integrity and limitations

For this readiness review, `test_ran_without_unintended_skip`, `public_path_reached`, `boundary_values_realistic`, `assertions_non_vacuous`, and `known_bad_detected` are all true. Method: `readiness-safe-control / pre-fix reproductions plus stale copied-surface control`. The selected review checks executed; default/declared reached actual reload; second reached and falsified the named setup premise with producer-built realistic inputs; the driver assertions distinguished the expected outcomes. The additional identity fixture reached the real renderer and detected both the ambient declaration mismatch and deliberate stale stock bytes while preserving the original first-render oracle.

No full suite, landed repaired implementation, disabled-refresh mutant, package build, native platform run, commit, or closure was performed. Delivery ACs remain unverified. Default/declared scratch reload runs emitted existing duplicate-resource and setup-readiness notices for their deliberately minimal target repositories; those notices did not bypass reload assertions. MCP reported changed setup inputs; no setup/rebuild was initiated and no semantic-index freshness claim is used. Direct current-file MCP reads and fresh-process probe execution establish this bounded evidence. The profile helper, declaration-isolation helper, and renderer/server paths are shared substrates, so this review does not prove correctness of their full contracts.

Typed approvals are supplied to the coordinator for recording with `approval_phase: readiness`, exact lane actors/signoff keys, `fresh_context: true`, and `independent: true`; the coordinator remains the typed ledger's writing hand.
