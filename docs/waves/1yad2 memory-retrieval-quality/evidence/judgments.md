# Independent memory qualification judgments

Owner: Engineering
Status: active
Last verified: 2026-09-16

Reviewer: independent QA worker `/root/memory_holdout`, separate from ranker implementation and tuning. No retrieval rankings, similarity scores, reranker scores or experimental results were executed to select these holdout labels. An unqueried MCP memory inventory was used to confirm the public contract; the canonical read-only loader then supplied the full corpus because MCP search caps inventory responses at 20. This bulk filesystem gapfill made no index or memory mutations.

## Frozen inputs

- `qualification-corpus.json` file SHA-256: `d4817379a9c3ef18aca0e152dfb10805630035e9386770b50c89ada0b943d7cd`.
- Canonical corpus content SHA-256: `239b664ee4e03ea35d53a4bcd3967b39da1fd25bf64107a5dc4dd5c5866a7ddd` (sorted compact UTF-8 JSON of records, archive_register and source_manifest).
- `qualification-queries.json` file SHA-256: `00720e2025b35e7cddcbf09d6799174d6f766beb2c371681eb094b468b94f69c`.
- Corpus: 218 parsed bodies (119 active, 54 rejected, 32 superseded, 13 archived) plus 13 compact archive-register entries. Full source text and per-file hashes are retained. Paths are repository-relative.
- Development: 20 original exploratory cases retained as `development_cases`, with their original `type`, `query`, and `expected` fields. These are explicitly not independent labels.
- Holdout: 24 newly authored cases under `cases`, 16 answerable and eight no-match. These use `relevant_ids`, `irrelevant_ids`, and `unjudged_ids`. Five additional `policy_cases` are lifecycle contract controls, not interchangeable with the 24 relevance cases.

## Judgment method

The reviewer examined every active record's summary, inspected action and validation fields for selected lessons, inspected historical and archive variants, and retained the complete parsed records and source markdown for replay. Queries were written as situations or requested facts, not copied record summaries. Labels describe useful answers to the specific question; topical similarity alone is insufficient. Each query carries its rationale. All previously used exploratory query fixtures were checked to avoid exact query reuse; related repository concepts necessarily recur.

Positive cases intentionally leave non-labelled records **unjudged**, rather than claiming an exhaustive relevance census. Recall therefore measures retrieval of the explicitly judged relevant set. Unjudged returns must be reported separately and must not inflate irrelevant-hit counts. Eight no-match cases ask for specific facts absent from the full active corpus; every active record is judged irrelevant to supplying that requested fact, even if it offers adjacent process advice. These controls are local-corpus answerability judgments, not claims that the requested systems or values cannot exist elsewhere.

Cases exercise broad phrasing, exact identifiers, duplicated/overlapping guidance, parsed authority declarations, and historical archive lifecycle. Policy controls explicitly separate full archived bodies from compact register rows and preserve supersession links. The historical allowance-table pair is a real old/current difference, not an invented contradiction. Do not infer supersession from timestamps or apply a historical answer as current policy.

## Limits and scoring discipline

The reviewer authored and judged these cases independently from the tuner, but this is one reviewer and a small, repository-specific sample. It is not a blinded multi-human benchmark. Development cases carry earlier investigator labels. Positive labels are incomplete, and the policy controls are intentionally excluded from pooled quality averages. Report exact numerators alongside scores; one changed hit is not a universal retrieval improvement.

Freeze candidate parameters and normalization populations before the first holdout execution. Do not modify these labels after seeing rankings or use repeated holdout scores for tuning. If a factual label defect is found, retain the original result, document an independently reviewed correction and new fingerprint, and treat subsequent scoring as a new evaluation rather than silently replacing this one. Readiness policy must decide minimum improvement before scoring. No production adoption approval is conveyed by this judgment artifact.
