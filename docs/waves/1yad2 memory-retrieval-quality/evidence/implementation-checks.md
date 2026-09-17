# Memory evaluation implementation checks

Owner: Engineering
Status: active
Last verified: 2026-09-16

## Scope and identity

Implementer: `memory_readiness_primer`, previously the readiness primer/moderator. This implementation record is not an independent delivery approval. Source ownership: `memory_eval.py` and `tests/test_memory_eval.py`; the coordinator owns the SQLite helper, live runner, server descriptions and other documentation. No production memory-search ranking was changed.

The implementation adds frozen-input and judgment validation, deterministic bounded fusion controls, aggregate quality accounting, and a fail-closed adoption gate. The existing sampled self-summary diagnostic is explicitly nonqualifying; a semantic query failure yields unavailable evidence rather than a successful empty result or private exception text.

## Executed tests

On macOS ARM64, Python 3.13:

```text
PYTHONPATH=.wavefoundry/framework/scripts:.wavefoundry/framework/scripts/tests /opt/homebrew/bin/python3 -B -m unittest test_memory_eval -q
Ran 25 tests in 4.167s — OK
```

The initial implementation passed 23 tests. Independent QA then found two validation defects; their repairs and one additional regression test produced a 24-test result. A subsequent code-only-index availability check brought the suite to 25 tests. Existing hermetic policy, concurrency and response tests remain included.

Coverage includes bounded distinct candidates; deterministic ties and valid negative cosine; explicit injection eligibility; compact archive entries sharing a path without losing identities; answerable empty results and negative queries kept in separate denominators; judged irrelevant versus unjudged results; unavailable measurement handling; complete-payload hashes; reviewer/split declarations; and adoption rejection on quality, evidence and timing failures.

The SQLite grouping test uses a real temporary database opened read-only and a deterministic injected distance function. Twenty-nine dominant chunks cannot crowd out a second memory, a quoted path matches literally, an unrelated path is excluded, a missing requested path reports incomplete coverage, and the database byte hash is unchanged. This verifies SQL shape and read behavior, not native sqlite-vec arithmetic; native qualification belongs to the coordinator's separate evidence.

The MCP response test drives `wf_memory_eval_response` with a failing semantic query and sentinel private identity, query and path values. The response is unavailable/nonqualifying/adoption-false and contains none of those sentinel values. The model/index inputs are controlled; this does not claim live retrieval quality.

Python 3.11: eight pure qualification-helper tests passed. The two tests importing the runtime/MCP storage dependencies could not run under that interpreter because the existing shared tool venv was built for 3.13 and the bootstrap correctly refused an ABI mismatch. No venv was rebuilt and no guard was bypassed. No native Windows or Linux execution is claimed.

## Independent QA repairs

| Finding | Repair | Expected versus observed |
| --- | --- | --- |
| QA-DEL-1: matching malformed populations could qualify | Require integer query populations, at least 24 total/eight negatives/one positive, exact population sum, and bounded miss/false-positive counts | Independent probe's valid control still adopts; negative, boolean and inconsistent populations reject |
| QA-DEL-2: missing judgments became implicit negatives; malformed corpus crashed | Require explicit typed judgment lists and a nonempty negative judgment; malformed corpus/query structures return invalid reports | Independent probe's genuine frozen manifest remains valid; missing judgments and malformed records reject without exceptions |
| Code-only index credited as available semantic measurement | Require the docs vector layer after loading; healthy test doubles explicitly declare that layer | Test executes the real WaveIndex loader with a valid code-only layer, then the public evaluation response reports unavailable and no metrics |

The independent reproduction was rerun at `/private/tmp/wf_qa_helpers_probe.py`; it reads the frozen artifacts but does not score any holdout query. No frozen corpus, query, or parameter input was modified by these repairs.

## Mutation checks

All mutations were compiled into isolated test-process module dictionaries and restored immediately. No mutated source was written to the repository or loaded into the live MCP host.

| Deliberate mutation | Protecting test | Observed |
| --- | --- | --- |
| Always return adoption true | `test_adoption_rejects_missing_evidence_regressions_and_timing_shortcuts` | One assertion failure, zero errors |
| Suppress no-match false-positive counts | `test_metrics_keep_negatives_empty_answers_and_unjudged_distinct` | One assertion failure, zero errors |
| Remove SQL GROUP BY before LIMIT | `test_scoped_sql_groups_before_limit_and_preserves_database` | One assertion failure, zero errors |
| Remove strict population validation added for QA-DEL-1 | `test_adoption_rejects_missing_evidence_regressions_and_timing_shortcuts` | Seven assertion failures, zero errors |
| Default missing labels to empty lists and remove negative-judgment requirement | `test_manifest_requires_explicit_judgments_and_rejects_malformed_corpus` | Two assertion failures, zero errors |
| Remove the docs-layer availability guard | `test_curated_code_only_index_is_unavailable_not_empty_semantic_success` | One assertion failure, zero errors |

The positive implementation passes the same tests. These controls establish that the tests detect the named defects; they are not a general proof against all malformed inputs or future model regressions.

## Limits

These are implementation checks, not final holdout, performance, policy-adoption or independent delivery results. Fingerprints detect changed inputs; reviewer independence and untouched holdout still require truthful process evidence. CPU/model/scale benchmarks and the adoption verdict belong in the coordinator's qualification report. Production search, memory briefing and advisory ordering remain unchanged unless their separate gates later pass.
