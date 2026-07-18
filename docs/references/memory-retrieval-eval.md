# Memory-retrieval evaluation baseline

Owner: Engineering
Status: active
Last verified: 2026-07-18

## Purpose

Any change to how the agent-memory layer ranks records must be measured, not
assumed. This is the memory-specific analog of the code/docs golden-query recall
eval: a hermetic golden set + runner that scores the current `wave_memory_search`
/ `wave_memory_brief` paths and asserts the policy invariants, so a future
ranking change (the deferred lexical+semantic fusion) has a recorded baseline to
beat and a guard against regressing the invariants.

## Where it lives

- Fixtures: `.wavefoundry/framework/scripts/tests/eval/memory_golden.json` — a
  synthetic memory corpus plus `(query | target) -> expected record id(s)` cases.
- Runner: `.wavefoundry/framework/scripts/tests/eval/run_memory_eval.py` — builds
  the corpus in a throwaway repo, runs the shipped search/brief paths, reports
  recall@k / MRR and per-case invariant pass/fail. Run it standalone with
  `python run_memory_eval.py` (add `--json` for the machine report).
- Test gate: `.wavefoundry/framework/scripts/tests/test_memory_eval.py` runs the
  harness in the suite and asserts every invariant holds and the recorded
  baseline is intact.

## Categories and invariants

The golden set covers five categories, each with an explicit policy invariant:

| Category | Invariant |
| --- | --- |
| `exact_target` | a target lookup returns the matching records, higher-trust first |
| `paraphrase` | a semantic hit never demotes a higher-trust record below a lower-trust one (the 1svuj fix) |
| `no_index` | with no semantic index, the text-containment fallback + policy order still returns the right records |
| `decay` | of two records of equal base confidence, the time-decayed one ranks below the fresh one |
| `supersession` | a superseded record is excluded from default surfacing |

## Recorded baseline

Over the paraphrase case, the runner records three configurations at recall@1:

| Configuration | recall@1 | Meaning |
| --- | ---: | --- |
| `baseline` (shipped: policy-primary + semantic tie-break) | 1.00 | the high-trust record stays on top |
| `semantic_only` (pure semantic order, the pre-1svuj behavior) | 0.00 | text relevance demotes the high-trust record |
| `lexical_only` (no index, strict text containment) | 0.00 | strict containment misses the paraphrase |

This is the baseline the deferred fusion change must beat. A fusion that improves
paraphrase recall must do so **without** dropping any policy invariant below
`baseline`.

## Measurement-only

The harness never changes ranking: it calls the shipped `wave_memory_search` /
`wave_memory_brief` paths and `_memory_ranked` unchanged. It is deterministic and
hermetic — it builds its own corpus and uses a fixed stub for the semantic index,
so it never depends on the live (empty) corpus. See the code/docs golden-query
eval for the sibling policy that gates code/docs retrieval changes.
