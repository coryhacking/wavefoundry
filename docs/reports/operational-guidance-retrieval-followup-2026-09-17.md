# Operational guidance retrieval: bounded follow-up

Owner: Engineering
Status: active
Last verified: 2026-09-17

## Decision

There is a small, concrete documentation-retrieval opportunity worth a bounded follow-up: a second search over operational guidance can recover missing actionable facts. This does not justify replacing general search, automatically excluding history, or continuing broad ranking-parameter tuning.

The previous [quality evaluation](semantic-search-quality-evaluation-2026-09-17.md) parked implementation because preferred-source counts were not enough. This follow-up tests required facts instead. It supplies one reproducible improvement, with explicit limits and a counterexample to making the scope universal.

## Test

Before retrieval, declare eight present-day operational questions with two required facts each, three history questions with two facts each, and two absent-fact controls. Some topics were already observed; the close-wave and history questions are repeated controls. This is coordinator-authored, unblinded development evidence, not an independent holdout or a release gate.

Compare three top-five result sets using the same CPU model and unchanged text representation:

- **Broad:** existing docs search with 30 dense candidates.
- **Guidance:** 30 dense candidates filtered before the limit to operational docs: prompts, references, architecture, specs, contributing docs, top-level agent roles, AGENTS.md and the framework README. This path scope is not proof that every passage is current.
- **Union:** combine and deduplicate both candidate pools, then rerank up to 60 candidates into five results using the existing model. No source bonus, threshold or file-diversity cap.

All previous `docs/reports/semantic-search-*` evaluation artifacts were excluded before candidate limits, using a 27-row census and bounded overfetch. The completed epoch stayed at generation 1548. All public broad/scoped calls were successful, reranked and without fallback. No runtime source, configuration, index contents or model was changed.

## Required-fact coverage

Judgments are based on the actual returned passages, not their filenames. A complete case means both declared facts are supported within the five passages; it does not mean an agent-generated answer was independently scored.

| Measure | Broad | Guidance | Union |
| --- | ---: | ---: | ---: |
| Complete operational cases | 6/8 | 7/8 | 7/8 |
| Required operational facts present | 13/16 | 15/16 | 14/16 |
| Complete history cases | 3/3 | 2/3 | 3/3 |

All six complete operational baseline cases remained complete. The new complete case asks how to rebuild the graph without regenerating embeddings: broad search discusses graph/map rebuilding without the needed command; guidance search retrieves `index_build(content='graph', mode='rebuild')` and the explicit no-semantic-embedding statement from AGENTS.md.

For wave closure, the guidance search adds explicit current-request operator authorization but still misses the complete AC/task checkbox rule. The case remains incomplete. Merging the pools back into one model-ranked top five loses that authorization passage again. A useful second search is not necessarily improved by flattening it into the same ranking bottleneck.

Commit authorization, lock-file interpretation, post-pull setup, memory authority, test-file inclusion and Python 3.11 compatibility retain their declared facts. Historical material in broad results sometimes already answered these questions correctly; it was not marked wrong merely for being historical.

## Controls and limits

The guidance-only history regression is the LanceDB-to-SQLite rationale: selected passages retain qualification and migration details but omit the explicit consolidation rationale. Broad and union retain it. The original memory-fusion decision and first protected-upgrade restart explanation remain supported in all three modes. This is evidence against applying the guidance restriction to every query.

Neither absent-fact question gains a supported hosted price or an always-correct-search setting. Local-only architecture can help correct a hosted-service premise, while adjacent search settings are not a guarantee. The test does not qualify automated abstention or answer verification.

The scope is tailored to this repository's documentation conventions. It has not been exposed through a public tool, generalized to arbitrary repository layouts, or paired with an automatic intent classifier. The baseline is a controlled-corpus public-handler call; the union is an experimental candidate-stage comparison. CPU-only execution and the small unblinded sample do not justify a production default.

## Worth pursuing, without forcing it

The narrow next step is an **agent-directed operational-guidance follow-up when a required action or rule is missing**, retaining broad/history search. For known workflow names, use existing exact prompt lookup and targeted reads before adding a new search feature. Preserve separately sourced evidence long enough for the agent to judge the missing fact; do not assume another global rerank will retain it.

A fresh-process call to the existing `wf_get_prompt_response(root, shortcut="Close wave")` returned status `ok` and the complete prompt, including its hard checkbox gate: every AC/task must be `[x]` or `[~]`, with the stated out-of-scope exemption. This post-hoc follow-up resolves the missing checkbox fact without a new retrieval feature. Combined with the authorization passage already found in AGENTS.md, the existing tools supply both declared closure facts. It was not included in the three-way search scores above.

The immediate recommendation is to exercise this existing follow-up workflow on future real questions, not open a search-engine implementation wave. A change should earn implementation by recovering additional actionable facts on new independent questions without losing useful baseline evidence or required history. This one extra complete case warrants investigating that small workflow/tooling gap; it does not justify a broader semantic-search rewrite or a release blocker. General code retrieval remains unchanged and its earlier mechanism misses remain unresolved.

The raw candidate capture and scratch driver were archived during the [evidence cleanup](retrieval-evaluation-evidence-retention.md) and remain recoverable from its recorded Git snapshot. The declared test, required-fact results, history regression, exact-prompt follow-up and limitations are preserved above. The original bundle omitted unselected passage bodies and the full database; it was auditable development evidence, not a turnkey frozen benchmark.
