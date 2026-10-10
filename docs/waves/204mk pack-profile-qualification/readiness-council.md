# Readiness Council — Pack Profile Qualification

Owner: Engineering
Status: active
Last verified: 2026-10-08

This report preserves the independently requested council evidence for the amended readiness packet. Typed events remain the machine authority; this report does not ready, open, close or approve delivery of the wave.

## Packet and verdict

- Wave: `204mk pack-profile-qualification`; change: `204hj-bug reload-probe-profile-portability`.
- Phase: readiness; current receipt: `review-policy-e4e7635de4c9660a60f8`.
- Verdict: **PASS — admissible for implementation**, with the existing required code/QA approvals; repaired behavior and packaging qualification remain unverified delivery work.
- Primer tier: standard. Production trust boundaries touched: none; two test-fixture assumptions are repaired without changing runtime contracts.
- Actual current roster: isolated `red-team` adversarial primer, then fresh isolated `docs-contract-reviewer`, also serving the configured rotating alternative seat. The earlier reload-only receipt selected architecture; that context was interrupted before a verdict when the amended receipt replaced its roster. No architecture approval or unrun fixed seats are claimed.
- Chair context: `/root/pack_readiness`; approval context ID: `204mk-readiness-council-chair-20261008-1`. Fresh independent review context; no implementation or repair edits by the chair or seats. Requested workhorse/high allocation was used; actual runtime model identity is unavailable.
- Budget: bounded existing baseline/feasibility controls, no full suites. Supplemental primer completed the initial council on the amended packet before any council approval; no readiness repair cycle was performed.

## Primer and seat synthesis

Red-team applied adversarial, constructive and simplicity stances. Strongest challenge: isolation must preserve both oracles. A lifecycle-only eviction mutant must reach successful real reload and then fail kind freshness; stale copied stock bytes must fail on the first renderer pass. Setup failures, profile skips and pre-rendering cannot stand in for those controls.

The two primer questions ask whether reload retains existing extras, selects a valid initially absent kind and proves fresh validator binding under a lifecycle-only mutant; and whether identity isolates the renderer's actual declaration module while preserving first-render zero writes, whole-tree digest, manifest assertions and stale-byte detection.

Docs-contract pre-primer read: the admitted plan preserves both behavioral contracts while correcting distinct empty-vocabulary and absent-extension fixture assumptions, implementable through existing declaration isolation without production changes. Primer effect: confirmed; it sharpened the negative-control failure locations without changing that independent assessment. The seat explicitly answered both questions: reload cells remain required delivery work; its executed identity controls demonstrate feasibility. **No findings in my lane**: the plan aligns with additive vocabulary, validator import-time binding and renderer call-time declarations.

First synthesis weighed the sole Phase 2 output as Seat 1 before restoring its identity; role anonymization is trivial with one configured seat. Red primer and seat share the identity concern by design; treat it as one semantic signal, with separately executed controls rather than independent discovery of two defects. No split or high-severity disagreement required a challenge round. Aggregate: `seat_agreement: unanimous` among the configured Phase 2 seats; `max_severity: none`.

Strongest alternative: reuse `declaration_support.base_declaration()` around the real stock renderer, preserving its first invocation and original assertions. The existing helper restores loaded declaration-module copies and avoids introducing another isolation mechanism. For reload, preserve the active profile and replace only the scratch extra-kind assignment; choose a valid absent kind and remove only lifecycle eviction for the negative control. Resetting vocabulary loses profile coverage; pre-rendering loses first-render drift detection. These are implementation notes within the admitted plan, not additional scope or plan defects.

## Executed readiness evidence

| Reviewer | Current-tree check | Expected versus observed |
| --- | --- | --- |
| Chair | `PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests python3 -B -m unittest test_distribution_seams.LifecycleIdReloadTests` | Real shipped reload succeeds: 1 test, 3.804s, OK, no skips. |
| Chair | In-memory AST feasibility control over current `vocabulary_profile.py`, using legal extras `("spike", "opsx")` | Reject empty-only replacement; preserve extras and select absent `probe1`. Observed empty-only patch rejected, initial extras unchanged, extended tuple `("spike", "opsx", "probe1")`. |
| Chair | Same focused unittest command targeting `test_vocabulary_prompt_names.DefaultRenderIdentityTests` | Existing shipped first-render oracle succeeds: 1 test, 0.367s, OK, no skips. |
| Red-team | Real copied-script shipped reload and canonical `apply_profile(..., load_profile("second"))` baseline | Shipped test succeeds (1 test, 2.892s); second extras `["decision"]` fail the existing `assert text.count(old) == 1` before reload. This is the admitted existing defect. |
| Red-team | Existing identity method: stock empty declaration; exact extension value from canonical `declared.json`; stock plus stale copied skill | Stock succeeds; declared extension correctly creates its prompt and three host skills; stale copied `.codex/skills/wf-plan-change/SKILL.md` causes first-render `written == []` failure. Each cell ran once without skips. Controlled declaration values, not a full declared-profile suite. |
| Docs-contract | Existing identity method under canonical `base_declaration()`, then stale copied stock skill before the first digest | Stock passes once without skips/errors; stale bytes fail `written == []`, naming exactly the rewritten stock skill. No pre-render. |

Reproducible chair AST control: parse current vocabulary source with `ast.parse`; replace its shipped empty declaration in memory with `("spike", "opsx")`; assert the original exact empty declaration is absent; locate `EXTRA_CHANGE_KINDS`'s `AnnAssign`, read its tuple with `ast.literal_eval`, select the first absent token from `("spike", "probe1", "probe2")`, and assert both original extras remain in the extended tuple. This rejects the known-bad empty-only portability claim, not an unimplemented reload repair.

Identity controls invoke `DefaultRenderIdentityTests.test_render_of_this_repository_writes_nothing` on its temporary copied tree. The stale control appends text to the copied `.codex/skills/wf-plan-change/SKILL.md` immediately before the original first `_tree_digest`, then runs the unchanged renderer and assertions. Declaration controls surround that call with the test helper or the exact declaration-module value. No repository source was mutated.

Selected state cells: shipped real reload success; nonempty-profile setup refusal; stock first-render identity; legitimate declared-skill creation; stale-stock first-render refusal. Future repaired reload/profile/mutant cells are unverified, not skipped readiness checks.

Integrity attestation for the chair's readiness judgment: `test_ran_without_unintended_skip`, `public_path_reached`, `boundary_values_realistic`, `assertions_non_vacuous`, and `known_bad_detected` are true. The real copied-tree runner and renderer were reached; the AST control deliberately refuted the empty-only portability claim. `known_bad_detection_method`: readiness-safe-control, supported by the empty-only refutation and seats' stale-byte controls. Initial chair invocation without the scripts PYTHONPATH failed import before the selected check; the corrected invocation above completed and is the cited evidence.

## Grounding and limits

Resolvable source anchors: `_RELOAD_PROBE` and `LifecycleIdReloadTests.test_reload_refreshes_lifecycle_id` in `test_distribution_seams.py`; `DefaultRenderIdentityTests.test_render_of_this_repository_writes_nothing` and `_tree_digest` in `test_vocabulary_prompt_names.py`; `perform_mcp_reload` in `server.py`; lifecycle eviction block in `wf_server/server_impl.py`; `lifecycle_id.KIND_CHOICES`; `declared_skills` in `render_agent_surfaces.py`; `base_declaration` in `declaration_support.py`; `SHIPPED_DECLARATION` and its vocabulary/declaration separation in `record_layout_support.py`.

Gapfill: the chair's first ALL_TOOLS discovery exposed no Wavefoundry retrieval tools, so initial bounded local reads were used. A later discovery exposed callable `code_read` and `code_keyword`; the chair switched to MCP. Both seats used callable MCP. An unsupported initial keyword argument attempt was corrected to `query`/`glob`. A broad keyword response was truncated and was not used to claim a closed census. MCP reported `setup_inputs_changed`; no setup recovery was attempted. Live targeted source reads grounded the review.

The chair's probes approve current-plan feasibility and existing failure attribution. No repaired code, lifecycle-only mutant, full qualification matrix, release artifact, external platform qualification or whole-repository green result is claimed. Probes were local and authorized, used temporary or in-memory state and required no network, credentials, commits or closure.

## Frozen packet

Current packet git object hashes matched at the amended briefing and final chair recheck, before recording council approval:

| Path | Working-tree git object hash |
| --- | --- |
| `.wavefoundry/framework/scripts/tests/test_distribution_seams.py` | `4093b79332b4fb92dcd29e48d64284fe055f7781` |
| `.wavefoundry/framework/scripts/tests/test_vocabulary_prompt_names.py` | `94f84a7cfcb76fee6ff25e78328ce19affc5990a` |
| `CHANGELOG.md` | `ebecee94fc4e6a60f6b9dbc433cbb39c3dd438af` |
| `docs/waves/204mk pack-profile-qualification/wave.md` | `05f9aaa12e9164971f2e37050f5c68a5006e257d` |
| `docs/waves/204mk pack-profile-qualification/204hj-bug reload-probe-profile-portability.md` | `5d0a6bfc4161f6fc8bdafa4c1dddb112a84d6c28` |

## Finding synthesis and falsification

Sealed readiness candidate set: empty. No Finding Synthesis rows are required; the coordinator records or retains the empty readiness Review Run and records the current council approval through `wf_review_event`. No existing fixture failure is misclassified as a new plan defect.

| Finding | Disposition | Rationale | Red-team |
| --- | --- | --- | --- |
| None | — | No candidate meets the readiness finding bar. | Held: empty set supported; no new finding. Canonical helper preference is an implementation note. |

### Falsification Check

Working verdict: PASS for implementation readiness. The strongest argument against it is that portable fixture setup could silently weaken either oracle. The plan expressly requires nonvacuous before/after checks and precise negative controls; independent current renderer controls demonstrate stock isolation still catches stale bytes, and current runner baselines ground the reload seam. That supports feasibility without pretending the future repair is verified. Delivery must still execute the required positive and negative cells before approval.
