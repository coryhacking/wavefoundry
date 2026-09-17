# Memory-retrieval evaluation and fusion gate

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Purpose

Memory-ranking changes require independent evidence. The ordinary `wf_memory_eval`
call is a bounded **self-summary diagnostic**, not release qualification: it uses
up to 12 sampled records to report policy and retrieval observations. Its report
explicitly returns `qualifying: false` and `adoption_gate.adopt: false`. A healthy
sampled pass cannot select a replacement ranking. Unavailable measurements remain
unavailable; lexical recovery is not counted as semantic success.

Qualification is a separate, explicitly generated local evaluation with a frozen
full corpus, independently authored disjoint holdout labels, fixed parameters,
policy controls and end-to-end CPU timings. Detailed artifacts may contain
queries and memory identities; they never enter ordinary MCP evaluation output.

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
| `archive_register_entry` | normal targeted search returns the compact register entry |
| `archive_history` | history opt-in resolves the archived body |
| `old_authoritative` | tactical recency cannot cross the protected family boundary |
| `new_low_confidence` | recency cannot cross a base-confidence band |
| `adaptive_cadence` | comparable tactical records use cadence-derived half-lives |
| `fragile_reverification` | churn keeps fragile records visible and requests re-verification |

The fixture histories are injected into the same batched `file_commit_times`
seam used by the product path. Adaptive results are therefore hermetic without
adding per-record store work.

## Original qualification gate and result

Wave `1yad2` compares the public production path with memory-scoped RRF and
75/25 min-max score fusion, plus bounded weighted-RRF, lexical-injection and
single-channel controls. Memory filtering precedes the experimental semantic
limit, and chunk distances group by path before returning at most 20 identities.
Both channels cap at 20, the union at 40 and results at 20. Compact archive
entries remain separate lexical identities. SQL/BM25 work still scales with
eligible chunks/records; bounded output is not a constant-time claim.

The predeclared gate requires no Recall@3/10 or MRR regression, no additional
empty answerable response or nonempty no-match response, a material gain of
five percentage points Recall@3 or 20% warm p95, and candidate warm p95 <=500 ms
and no worse than production over at least 100 calls. Raw per-record relevance
checks are evaluated separately; scores are neither probabilities nor authority.
Missing infrastructure, incomplete coverage or failed required relevance checks
invalidates qualification and retains the public lexical recovery path.

The independent 24-query holdout (16 answerable, eight no-match) selected
**non-adoption**. Plain RRF improved Recall@3 from 0.75 to 1.0 and warm p95 from
690.8 to 137.1 ms, but false-positive queries rose from two to eight. Qualified
variants eliminated those false positives but introduced one empty answerable
response. Production ordering, `memory_brief` and read-tool advisories therefore
remain unchanged. No new dependency, schema or model was introduced.

See [qualification report](../waves/1yad2%20memory-retrieval-quality/evidence/qualification-report.md)
for complete outcomes, immutable input fingerprints, local reproduction,
platform limits and cold/warm distributions. `memory_eval.py` exposes reusable
manifest, metric and gate helpers; it does not automatically discover or adopt
local qualification files. The older 11-invariant hermetic suite remains useful
policy coverage, not a substitute for the independent holdout.

## Historical gate and 2026-07-24 result

The following records the earlier gate, superseded for new ranking decisions
by the qualification contract above.

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

## Selected production integration (wave 1yad2)

The original frozen comparison above remains a non-adoption result. Subsequent
independent experiments selected memory-scoped RRF with summary-only relevance
checks over its first five records, using the unchanged raw cutoff -4. The
operator approved implementing this candidate and explicitly accepted an empty
response replacing a baseline response with no useful evidence. This acceptance
revision is disclosed after observation; it is not retroactively attributed to
the original gate. Paired loss of useful answers, no-match false positives,
Recall@3/10, MRR, pooled direct-support precision and latency remain measured.

An independent 24-query integration preflight found useful memories for 15/16
answerable queries versus 12/16 by the original labels, with no nonempty response
on eight conceptual no-match queries in either system. A separate blind judge
classified every returned record: direct-support precision was 15/21 versus
11/16, with six and five adjacent-context returns respectively. CPU warm p95 was
200 ms versus 694 ms over 100 calls. These are prototype/pre-integration results;
production-path parity and delivery evidence must establish that the shipped
implementation follows the same design. This small local sample establishes no
universal threshold, perfect precision or native-platform guarantee.

The query path preserves eligibility and provenance, bounds each channel at 20,
uses equal-weight RRF k=60, and checks at most five summaries (title fallback).
Each finite raw score >= -4 independently admits its record. Results preserve
RRF order; no unchecked tail refills rejected candidates. No-query listings,
briefings and advisories retain existing policy ordering. Failure uses explicit
lexical-policy recovery, and archive history remains available without embedding
archived bodies. Model checks are local CPU work with existing model artifacts.

Relevance-screened records are evidence for the calling agent to evaluate, as
with semantic, lexical and graph search. A score is neither verified answer
support nor instruction authority; inspect the returned status, confidence,
provenance and content. Agent validation in these experiments is independent
review, not a new per-search agent service. The four earlier weak tails and six
latest adjacent records are retained as limitations rather than reclassified as
correct by topical similarity.

See [follow-up experiment](../waves/1yad2%20memory-retrieval-quality/evidence/relevance-followup.md)
and [integration preflight](../waves/1yad2%20memory-retrieval-quality/evidence/summary5-integration-preflight.md)
for frozen labels, paired results, blind support judgments and reproducible artifacts.

### Source freshness and runtime recovery

Production checks eligible memory body SHA-256 values against published docs-layer
source hashes within the vector read transaction. Changed or missing provenance
uses explicit lexical-policy recovery until indexing catches up. A failed CPU
model load is cached for the process: check the disable setting and local model/runtime
availability, use `wf setup` if provisioning is needed, then restart MCP. An index
refresh alone does not clear the cached model failure.
