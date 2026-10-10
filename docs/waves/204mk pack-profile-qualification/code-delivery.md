# Code delivery review

Owner: Engineering
Status: active
Last verified: 2026-10-08

Wave: `204mk pack-profile-qualification`
Change: `204hj-bug reload-probe-profile-portability`
Actor: code-reviewer
Context: `204mk-code-delivery-independent-20261008`

Verdict: approve the narrow test-fixture implementation; no blocking code findings. This is a code-lane result, not a claim that the pending canonical suite or serial packaging qualification has passed. The coordinator owns those gates and AC completion.

## Independent reference and inspection

Reference: the independently read admitted change Requirements 1–5 and AC-1–4, plus the documented extra-kind grammar at `vocabulary_profile.EXTRA_CHANGE_KINDS`. Required properties: preserve existing kinds, select a valid absent kind, compare the exact post-reload choices and fresh validator binding, and preserve the original first-render zero-write/tree-byte identity oracle.

MCP tools were discovered through the actual callable tool inventory before source retrieval. `code_read` read the changed probe, `LifecycleIdReloadTests.test_reload_refreshes_lifecycle_id`, `DefaultRenderIdentityTests.test_render_of_this_repository_writes_nothing`, `declaration_support.base_declaration`, and the profile guard; `code_keyword` located supporting vocabulary/declaration occurrences. The bounded keyword result was truncated and was not used as a closed census. No shell retrieval fallback was necessary.

The diff retains the copied-tree subprocess and real thin-runner reload; `kind_choices_fresh` now compares the exact original set plus the new kind. Candidate selection excludes the initial choices and searches enough candidates to guarantee an absent token. The regex handles the single-line declaration contract without assuming an empty tuple or particular quoting. Existing extras are appended to, rather than replaced. Validator identity still compares its binding to the freshly imported lifecycle module.

The stock identity fixture invokes its original first render inside the existing `base_declaration` context. The pre-render digest, zero-write assertion, post-render digest, and manifest assertion remain intact. There is no preparatory render. The existing default-profile marker is unchanged; no new profile skip was introduced. `base_declaration` restores all patched declaration values in `finally` and resets derived server state on both entry and exit.

## Executed bounded probe

Probe ID: `code-delivery-declaration-format-collision-matrix`.

Boundary: the actual `_RELOAD_PROBE` candidate expression and rewrite regex, followed by Python compilation/execution of the actual `vocabulary_profile.py` module with the rewritten declaration. This exercises the real declaration parser/import validation boundary; it does not independently exercise the MCP reload, which belongs to QA's allocated probes.

The executed `python3 -B` probe parsed the test with `ast`, extracted `_RELOAD_PROBE`, extracted its `new_kind` expression and `re.subn` pattern from the probe AST, and tested four declarations: annotated with double quotes, plain with single quotes, tab-spaced annotation/assignment, and CRLF. Each ran with extras `()`, `('spike',)`, `('probe0', 'probe1', 'spike')`, and `('probe0', 'probe2', 'spike')`. Each transformed full vocabulary source was compiled and executed. Assertions required exactly one substitution, the exact original extras plus the chosen kind, the exact original kind set plus that kind, and the documented valid/absent token property. Adjacent controls included stock empty extras and candidate collisions. A separate collision set containing `probe0`, `probe1`, and `probe2` required `probe3`.

Expected: 16 legitimate parser cases preserve existing extras and add exactly one valid absent kind. Observed: all 16 met the assertions; CRLF compiled successfully; the collision selected `probe3`.

## Mutation table

| Known-bad control | Targeted assertion | Observed |
| --- | --- | --- |
| Replace extras with only the new kind | Exact `CHANGE_KINDS == original_choices union {new_kind}` | Failed as expected for all 12 nonempty-extra format cases |
| Force fixed `probe0` under an initial `probe0/probe1/probe2` collision | Candidate absent from original choices | Failed as expected |
| Inject original exact-empty-declaration prerequisite under declared `spike` | Single exact empty assignment exists | Failed as expected |

Total: 14 expected known-bad failures; no survivor requiring a whole-file sweep. Mutations were in memory, never in repository source. QA owns the separate lifecycle-eviction and stale-copied-skill controls. No owning full files or full suite were duplicated by this lane.

## Approval payload and limits

`fresh_context: true`; `independent: true`. The reviewer did not implement this change and formed this verdict from the current diff, independently read ACs, and its executed probe rather than prior review conclusions.

Integrity for this bounded code-fit claim: `test_ran_without_unintended_skip: true`, `public_path_reached: true` (named real declaration parser boundary), `boundary_values_realistic: true`, `assertions_non_vacuous: true`, `known_bad_detected: true`, `known_bad_detection_method: focused-mutation`.

Proposition: the changed reload-fixture setup preserves configured extras across the tested supported declaration formats and selects a valid absent kind, while the test diff retains the exact reload/binding and first-render drift oracles. Failure condition: any format loses extras, collides with an initial kind, fails real declaration validation, or the diff bypasses/weakened an original oracle. Safety: local in-memory test-only probes within delegated review authorization; no external actions or production source edits.

Limitations: this lane did not execute real MCP reload or the renderer identity test, packaging profile suites, the canonical suite, native Windows, or arbitrary multiline declaration syntax. QA supplies executed real-reload and stale-surface evidence. The format probe shares the implementation expression/regex by design; its independently specified invariants and known-bad controls test their outcome, while actual module validation supplies a separate parser contract. No universal absence/census claim is made. Changelog also contains an adjacent earlier-wave entry; this lane attributes only the fixture-portability release-note claim to the current change.

Reviewed frozen hashes, rechecked after the probes:

- `test_distribution_seams.py`: `c81059293654443b6a9c98759e4dc4735874fe18`
- `test_vocabulary_prompt_names.py`: `2ee364b4cb5e4e47bfb2f768eac3aee33314454a`
- Root `CHANGELOG.md`: `604748186bdb903ecba78c2cf6105a73cb17c303`

No source edits, ledger writes, wave-status edits, full-suite runs, commits, or closure actions were performed.
