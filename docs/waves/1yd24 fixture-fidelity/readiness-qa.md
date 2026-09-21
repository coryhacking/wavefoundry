# Fixture fidelity readiness QA

Owner: Engineering
Status: active
Last verified: 2026-09-20

## First full review

Verdict: **blocked on `fixture-propagation-contract`**, corroborating the code/docs lane's single finding. The helper, anti-vacuity oracle and bounded literal census are feasible on the current tree. No implementation or typed approval was performed by this reviewer.

Reviewed plan Git-object hashes: `1yd25` = `e430c71f47fe9bdc208488b471b9ba2676c6e0e3`; `1yd96` = `0a9aca51035214c4b01435cd61e44d868bec3abb`. Reviewer context: `/root/readiness_qa_delivery`, new fixture-fidelity task, actor `qa-reviewer`. This reviewer did not author either plan or implement a repair.

## Adversarial primer

Mode: `council-adversarial-primer`, standard depth. Adversarial stance: the helper can move false confidence into a broad accepted-error whitelist or swallowed producer refusal. Constructive stance: assert each producer result and independently assert the final readiness outcome. Simplicity stance: retain intentional component/negative fixtures rather than replacing their subjects with lifecycle setup. These are the three selected standard-tier stances.

Strongest initial challenge: a canonical-looking fixture can still stop before the span its test names. Best alternative: the proposed small orchestration helper, narrowly scoped lint/garden stubs, strict unexpected-refusal assertions and an independent end-state oracle. The cost is explicit caller setup and per-site migration review; the benefit is that a green fixture demonstrates reachability.

Primer questions supplied before specialist assessment:

1. Does omission of the readiness run fail final Prepare for the expected reason, while the complete producer sequence reaches readiness without blocking diagnostics?
2. Can a site-specific token guard reject an unannotated declaration in a helper-using file while retaining valid parser/projection inputs and avoiding a computed-string coverage claim?

The propagation assumption became the strongest concrete challenge after source validation and the third probe: existing project-authored QA prose is deliberately preserved by the renderer.

## Executed readiness probes

Finite budget: three parameterized probes, completed without additional exploratory probes. Command:

```bash
PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests /Users/coryhacking/.wavefoundry/venv/bin/python -B /tmp/1yd24-qa-readiness-probes.py
```

Scratch script and log: `/tmp/1yd24-qa-readiness-probes.py`, `/tmp/1yd24-qa-readiness-probes.log`. The observations below persist the evidence if those temporary files are removed. Probes used disposable repositories and no network, credentials or project lifecycle mutation.

### Producer sequence and anti-vacuity

Executed current `wf_create_wave_response`, canonical change creation, `wf_add_change_response`, `wf_prepare_wave_response`, and `wf_review_event_response` in lifecycle order. Lint/garden, post-write lint and background indexing were explicitly stubbed within a scoped context. The independently read reference was `1yd25` AC-2's observable final-readiness contract, rather than the author's preflight result.

- Complete case: initial Prepare published one receipt; readiness run and council approval succeeded; final `mode="ready"` returned `status="ok"`, no blocking diagnostics; `validate_external_review_evidence(...).ok` was true.
- Omitted-run control: approval itself still returned `ok` and standalone evidence validation remained true, but final Prepare returned `error`, code `review_evidence_invalid`, message `marked wave requires a readiness Review Run Record at this lifecycle phase` (the message quotes readiness in backticks).

This directly answers primer question 1. Merely asserting that the ledger parses or that approval was appended would be vacuous for readiness. The specified final Prepare oracle distinguishes the known-bad state.

### Literal census and retained subjects

Independently enumerated raw literal occurrences and Python lexical tokens over `scripts/tests/**/*.py`. Both instruments reconcile to **51 occurrences across 10 files** when formatted-string literal tokens are included. A synthetic file containing both a helper call and a separate handwritten declaration still yields that declaration site, answering the bypass portion of primer question 2.

Implementation note: on Python 3.13, checking only `tokenize.STRING` yields 50 sites across nine files and misses the formatted-string declaration in `test_memory_records.py` (`MemoryProposeTests._wave`). Including `tokenize.FSTRING_MIDDLE` restores 51/10. The implementation should honor the existing literal-site promise across supported tokenizer representations. This is a bounded implementation note, not a new data-flow requirement.

The two instruments address different concerns: raw text locates literal spellings including comments, while tokenization identifies the lexical string sites and formatting-token split. Agreement closes this current literal census only. Concatenated/computed values remain outside the advertised static guard and require migration review.

Read current `ReviewPhaseAliasTests` and `ReceiptSemanticCanonicalInputTests` context; reviewed the supplied census only as leads. Parser/projection/index inputs and declaration assertions/removal tokens have different subjects from positive lifecycle setup. Requirements 4–5 explicitly retain these subjects and prevent blanket migration or mislabeling valid component inputs as negative. Annotation adjacency, nonempty reasons and all guard negative controls remain delivery obligations; no not-yet-written guard was claimed to execute.

### Actual renderer propagation

Executed public `render_agent_surfaces` twice in a disposable repository, with independently chosen version sentinels in seeds 239 and 209:

1. Fresh QA carrier received seed-239 version 1.
2. Replaced the seed with version 2 and rendered again: existing QA body retained version 1 and did not receive version 2.
3. The seed-209 consumer had the canonical seed pointer, but not the seed-body sentinel.

Source anchors: `render_agent_surfaces._initial_review_carrier_text`, `_carrier_protocol_block`, `_upsert_review_protocol_region`, and `reconcile_review_protocol_surfaces`. Existing files are read as their original project prose; only the owned protocol block is refreshed. These results refute the current unqualified same-text regeneration promise in `1yd96` AC-3 while preserving the intentional project-ownership boundary.

## Finding facts

Finding: `fixture-propagation-contract` (shared with code/docs lane).

Proposition: editing the two seeds and merely regenerating current surfaces does not refresh existing QA condition-2 prose as promised; seed 209 is transported through a canonical pointer rather than same-text copying.

Failure condition: a target with an existing QA role is rerendered after seed 239 changes and retains the old role body. This was executed, not inferred.

Recommended bounded repair: state the actual transport contract—authoritative seed-209 guidance through the existing pointer, fresh seed-239 QA-role copying, and an explicit self-hosted QA prose sync while preserving existing target-owned prose. Require the corresponding pointer/fresh/existing preservation checks rather than promising unsupported automatic body replacement. This changes no lifecycle behavior, validator, evidence field or tool signature.

Ten load-bearing judgment facts:

```json
{
  "validation_status": "real",
  "scope_relation": "admitted",
  "introduced_or_worsened_by_wave": true,
  "contract_relevance": "required_ac",
  "supported_reachability": true,
  "attacker_reachability": false,
  "authority_domain": "none",
  "authority_delta": "none",
  "observable_impact": "material",
  "containment": "none"
}
```

The impact is a required propagation criterion that cannot be met by the stated seed-only/regeneration operations. This is a correctness/feasibility finding, not a security finding or prose preference. No production renderer modification is required by the proposed narrow repair. Root owns the typed finding and repair workflow; this document does not terminalize it.

## Evidence integrity and limitations

```json
{
  "test_ran_without_unintended_skip": true,
  "public_path_reached": true,
  "boundary_values_realistic": true,
  "assertions_non_vacuous": true,
  "known_bad_detected": true,
  "known_bad_detection_method": "readiness-safe-control: omitted readiness run fails final Prepare; public renderer refutes same-text refresh claim; STRING-only census misses an existing formatted-string site"
}
```

Execution status: `executed`, phase `readiness`, probe class `local_safe`; no product delivery claim. The producer probe reaches production lifecycle response handlers; the propagation probe reaches the public renderer. Future helper implementation, annotation guard, migration fidelity, seed edits, parity and full-suite outcomes remain delivery work.

Gapfill: an initial MCP keyword call used unsupported parameter names and was rejected without results; corrected `query`/`queries` and `glob` calls succeeded. MCP keyword/read grounded the renderer and lifecycle fixture paths. No stale indexed result was substituted for live source. Targeted shell reads supplied the census/probe execution and enum definitions; no semantic-index recovery was needed. The requested red-team role path was absent at `docs/agents/red-team.md`; the actual role was read at `docs/agents/specialists/red-team.md`.

The first token-census attempt deliberately exposed an unaccounted Python 3.13 token class and was corrected before completing that probe. That failure is retained above as the implementation note, not silently counted as a green control. The preflight notes were leads, not the correctness oracle. No full suite was run for this readiness assessment because no implementation exists yet.

## Focused repair verification

Verdict: **QA readiness approved** for repaired receipt `review-policy-6a0c094179627d203926`, policy digest `b6c600f43d043f44f1a91f2ed6900b8da02aed5d163a0047a82c3b8c7842d186`. The QA contribution to `fixture-propagation-contract` is resolved; root must record this lane's reverification and current-receipt approval through the typed surface. This document does not clear another lane's authority.

Repaired plan Git-object hashes: `1yd25` = `d8a166d98c591edef06f5df2c0a183b10e038184`; `1yd96` = `4eaa35acf6f52fbaa40aacf7cef8316703272789`.

This was the one focused verification pass, restricted to the original propagation finding, repair text, directly affected fixture stubbing/census rules and unchanged renderer ownership contract. No new whole-document sweep or implementation work occurred. The reviewer did not author the repair; root identified its repair context as `1yd24-readiness-plan-repair`, actor `implementer`, cycle 1.

The repaired `1yd96` Requirement 4 and AC-3 now distinguish all four relevant obligations: common carriers retain the seed-209 reference, fresh QA roles receive seed-239 guidance, existing target-owned role prose survives rerender, and this repository's QA guidance receives an explicit local sync. Renderer modification and automatic target prose replacement are expressly excluded. This removes the original impossible transport claim without narrowing away required guidance availability or conflicting with the unchanged ownership rule.

Replayed the same three parameterized probes with the command above; execution completed successfully with no skips. The exact renderer reproduction remains unchanged—fresh 239 copy, preserved existing body, 209 pointer—but now agrees with the repaired requirements rather than contradicting them. The independent version-sentinel counterexample still rejects the old automatic-body-replacement claim, so the verification has a discriminating known-bad control.

Affected adjacent controls were also replayed: complete canonical lifecycle setup reaches final Prepare `ok` with no blocking diagnostics; omitted readiness run causes the specific `review_evidence_invalid` refusal despite successful approval append and valid standalone ledger; literal census again yields 51 sites across 10 files. The repair explicitly covers whole-sequence post-write lint and background-refresh stubs, restoration on failure, and separately tokenized f-string literal segments. These agree with the executed feasibility probe and original narrow static-census boundary. Actual helper restoration tests and annotation enforcement remain delivery obligations, not claims about code that does not yet exist.

No surviving blocker or replacement defect was found within this focused packet. Required delivery checks, independent expected-value oracles, component/negative/producer fixture exceptions, immutable golden preservation and the tests-only helper scope remain intact.

Focused verification context: actor `qa-reviewer`, context ID `1yd24-qa-focused-verification`, `fresh_context=true`, `independent=true`. These declarations mean no implementation/repair context was retained and this reviewer independently replayed the current-tree evidence; the earlier review narrative was not substituted for execution.

```json
{
  "test_ran_without_unintended_skip": true,
  "public_path_reached": true,
  "boundary_values_realistic": true,
  "assertions_non_vacuous": true,
  "known_bad_detected": true,
  "known_bad_detection_method": "readiness-safe-control: replayed public-renderer version-sentinel counterexample to the old replacement promise and omitted-readiness-run final Prepare refusal"
}
```

Approval evidence anchor: this section, `render_agent_surfaces.render_agent_surfaces` / `reconcile_review_protocol_surfaces`, and the three executed probes above. Limitations remain readiness-only: no future helper, seed edits, migrations or delivery full-suite result is represented as implemented or verified.
