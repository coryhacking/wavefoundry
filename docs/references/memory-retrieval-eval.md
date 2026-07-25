# Memory-retrieval evaluation and fusion gate

Owner: Engineering
Status: active
Last verified: 2026-07-25

## Purpose

Any memory-ranking change must be measured, not assumed. The harness combines a
repeatable hermetic gate with an optional bounded live-corpus observation. It
scores the shipped search path, an evaluation-only in-process BM25 + semantic
RRF candidate, and lexical-only/semantic-only controls. The candidate is wired
into product code only after the explicit adoption gate passes.

## Where it lives

The eval is two distinct things, and they live in two places on purpose:

| | Hermetic invariant pass | Curated corpus measurement |
| --- | --- | --- |
| What | Fixture corpus, recall@k / MRR, 11 policy invariants | This repository's real memory records, aggregate metrics |
| Kind | A **test** | A shipped **capability** |
| Entry | `tests/test_memory_eval.py` (or the CLI `--json`) | **`wf_memory_eval`** MCP tool, or the CLI `--curated-root` |
| Ships? | No — fixture is test scaffolding | Yes — the engine packages with the framework |

- Engine: `.wavefoundry/framework/scripts/memory_eval.py` — shippable framework
  source (wave 1tgws). Builds the corpus in a throwaway repo, runs the shipped
  path and evaluation candidate, and reports recall@k / MRR, per-case invariant
  results, controls, fixture fingerprint, and adoption decision. Run it with
  `python3 -B .wavefoundry/framework/scripts/memory_eval.py --json`.
- Fixtures: `.wavefoundry/framework/scripts/tests/eval/memory_golden.json` — a
  synthetic memory corpus, deterministic per-target histories, and
  `(query | target) -> expected record id(s)` cases. Test scaffolding: it is
  **not** packaged, so `run()` raises a clear `FileNotFoundError` in a target
  repository. The shipped measurement (`run_curated`) does not need it.
- Test gate: `.wavefoundry/framework/scripts/tests/test_memory_eval.py` pins
  every invariant, deterministic RRF, aggregate privacy, reproducibility, and
  the registered 1,000-record lexical budget.
- Curated observation (agents): call **`wf_memory_eval`**. It runs the curated
  pass over the configured repository and returns the aggregate report in a
  structured envelope; when the semantic backend or corpus is unavailable it
  returns `available: false` with a `curated_pass_unavailable` diagnostic
  rather than failing. CLI fallback: add `--curated-root <repo>`. The sample is selected and
  fingerprinted before any candidate is scored. Output contains sample size,
  aggregate kind/status counts, metrics, and fingerprint only — never memory
  bodies, summaries, or record ids.

## Categories and invariants

The golden set covers 11 categories:

| Category | Invariant |
| --- | --- |
| `exact_target` | target lookup returns matching records, higher-trust first |
| `paraphrase` | a semantic hit cannot demote a higher-trust record |
| `no_index` | text containment plus policy order remains deterministic |
| `decay` | an old time-sensitive record ranks below a fresh comparable one |
| `supersession` | superseded history is absent from default surfacing |
| `archive_pointer` | normal targeted search returns the compact pointer |
| `archive_history` | history opt-in resolves the archived body |
| `old_authoritative` | tactical recency cannot cross the protected family boundary |
| `new_low_confidence` | recency cannot cross a base-confidence band |
| `adaptive_cadence` | comparable tactical records use cadence-derived half-lives |
| `fragile_reverification` | churn keeps fragile records visible and requests re-verification |

The fixture histories are injected into the same batched `file_commit_times`
seam used by the product path. Adaptive results are therefore hermetic without
adding per-record store work.

## Adoption gate and recorded result

Default-on fusion requires all of the following against the same frozen
fixtures/sample: every candidate policy invariant passes; hermetic recall@3
does not regress; curated MRR strictly improves; curated recall@3 does not
regress; lexical-only and semantic-only controls are present. A tie, unavailable
curated pass, or any regression leaves product search unchanged.

The 2026-07-24 implementation run recorded:

- Hermetic fingerprint:
  `72ead29288cabe762afd9f4e91b96e5aba9f2e66a22e42f25c5f2e8c4d23f4a4`.
- Shipped baseline: recall@3 `1.0000`, MRR `1.0000`; candidate: recall@3
  `1.0000`, MRR `0.8485`; lexical-only: `1.0000` / `0.8485`;
  semantic-only: `0.8636` / `0.9242`.
- All 11 shipped and candidate policy invariants passed.
- Frozen curated sample: cap/size `12/12`, fingerprint
  `9355a41fc118506a2e5d84eea2539e99a840cc87a2f9388fa408ebc9c23fe395`;
  surfaced corpus counts were 37 total (36 active, 1 candidate), with kind
  counts `{decision: 3, dependency_gotcha: 2, environment_gotcha: 7,
  failed_attempt: 13, fragile_file: 3, review_finding: 1,
  successful_pattern: 8}`.
- The curated semantic pass was unavailable to the standalone interpreter
  (`lancedb` unavailable), which is itself a gate failure. Fusion was not
  adopted; the shipped semantic tie-break remains and no dormant product flag
  or branch was added.

The selected adaptive constants are documented beside
`memory_records.ADAPTIVE_*`: 7-day tactical reference cadence; 5–40 commit
clamps; 6× time-sensitive cadence with 30–365 day clamps. Candidate reference
intervals 3.5 and 14 days were rejected as respectively too eager and too
permissive. See the code/docs golden-query eval for the sibling ranking gate.
