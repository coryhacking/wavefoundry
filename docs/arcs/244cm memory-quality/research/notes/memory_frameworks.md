# LLM-agent memory frameworks, 2023-2026: architecture, claims, criticism

Owner: Engineering
Status: active
Last verified: 2026-11-23

The body below is copied unchanged from wave 245na's work folder on 2026-11-23 as the evidence base for arc `244cm-arc memory-quality`.

Research date 2026-11-23. Sources were arXiv abstracts and HTML, vendor docs and blogs, and a few secondary posts. Claims are labelled VENDOR (self-reported), PEER (paper, not independently reproduced) or INDEPENDENT. I found no fully independent reproduction of any headline number.

## Memory types (taxonomy)

### Takeaway
There is no single taxonomy. Letta uses placement tiers (in-context core, recall, archival). LangMem uses cognitive types (semantic, episodic, procedural). Zep uses graph tiers (episode, entity/fact, community). Mem0 and A-Mem use one undifferentiated pool of facts or notes. Generative Agents uses a typed stream (observation, reflection, plan).

### Cited Findings
- MemGPT (arXiv Oct 2023): main context has read-only system instructions, a fixed-size read/write working context, and a FIFO message queue with a recursive summary at its front. External context has recall storage (full message history) and archival storage (arbitrary text objects). Data must be explicitly paged into main context. — [MemGPT](https://arxiv.org/html/2310.08560)
- Letta current docs: core memory is in-context read-write blocks (persona, user info); recall is conversation history searched with `conversation_search`; archival is explicitly saved, indexed knowledge. — [Letta agent memory](https://www.letta.com/blog/agent-memory), [Letta docs](https://docs.letta.com/guides/agents/architectures/memgpt)
- LangMem: semantic (facts, preferences), episodic (past experiences stored as examples with context, reasoning and outcome), procedural (system behaviour and instructions, evolved via prompt optimization). Two storage shapes: collections (many records, searched at runtime) and profiles (one document updated in place, user-editable). — [LangMem conceptual guide](https://langchain-ai.github.io/langmem/concepts/conceptual_guide/)
- Zep/Graphiti: episode subgraph (raw messages/text/JSON, lossless), semantic entity subgraph (entities and facts, facts can be hyper-edges), community subgraph (clusters of entities with summaries; label propagation, not Leiden). — [Zep paper](https://arxiv.org/html/2501.13956)
- Generative Agents (2023): memory stream of objects, each with a natural-language description, creation timestamp and last-access timestamp. Types are observations, reflections and plans. — [Generative Agents](https://arxiv.org/html/2304.03442)
- A-Mem (Feb 2025): each note holds raw content, timestamp, LLM-generated keywords, tags and a contextual description, plus a dense embedding of the concatenated text. — [A-Mem](https://arxiv.org/html/2502.12110)
- MemoryOS (Jun 2025): three levels (short-term, mid-term, long-term personal memory); short to mid-term by FIFO on dialogue chains, mid to long-term by "segmented page" organization. — [MemoryOS abstract](https://arxiv.org/abs/2506.06326)
- Cognee (May 2025 paper): modular knowledge-graph construction and retrieval; the paper tunes chunking, graph construction, retrieval and prompting hyperparameters on multi-hop QA (HotPotQA, TwoWikiMultiHop, MuSiQue). — [Cognee abstract](https://arxiv.org/abs/2505.24478)

### Inferences
- Wavefoundry's typed records with evidence refs sit closest to LangMem's semantic/procedural split plus Generative Agents' reflections-with-citations (reflections point to supporting memories). Nothing surveyed has file-target binding; that is Wavefoundry-specific.

### Gaps
- I did not read Cognee's or MemoryOS's code/docs; their internals (Cognee's pipeline, MemoryOS's heat score) are unverified. The MemoryOS abstract does not mention a heat score; I have no source for it.

## Writing (extraction, dedup, contradiction)

### Takeaway
Three patterns: agent self-edits via tools (MemGPT/Letta), LLM extraction followed by an LLM-chosen CRUD op against nearest neighbours (Mem0, Zep, A-Mem), and background reflection or consolidation jobs (LangMem, Letta sleep-time, Generative Agents). Every write costs at least one LLM call; contradiction handling is always LLM judgement, never deterministic.

### Cited Findings
- MemGPT: the LLM emits function calls to save to working or archival storage. A memory-pressure warning fires at a configured token fraction (e.g. 70%); at the flush count (e.g. 100%) a share of messages (e.g. 50%) is evicted and the recursive summary updated; evicted messages stay in recall. `request_heartbeat` lets the model chain calls. — [MemGPT](https://arxiv.org/html/2310.08560)
- Letta sleep-time agents: creating one yields two agents. The primary cannot edit core memory; the sleep-time agent holds the memory-editing tools and can use a different (larger, slower) model. Run frequency is configurable, higher frequency costs more tokens. Docs label it experimental. — [Letta sleep-time blog](https://letta.com/blog/sleep-time-compute), [Letta docs](https://docs.letta.com/guides/agents/architectures/sleeptime/index.md)
- Mem0 extraction: prompt built from a conversation summary, the last m=10 messages and the new message pair; an LLM extracts candidate facts; a separate asynchronous module refreshes the summary. — [Mem0 paper](https://arxiv.org/html/2504.19413v1)
- Mem0 update: for each candidate fact, retrieve top s=10 similar memories by embedding; the LLM (tool-call interface) picks ADD (no equivalent), UPDATE (complementary info), DELETE (contradicts), or NOOP. The paper gives no explicit LLM-calls-per-write figure (one extraction call plus one update call per fact is implied). — [Mem0 paper](https://arxiv.org/html/2504.19413v1)
- Mem0g (graph variant): directed labelled graph in Neo4j; LLM entity extractor and relationship generator (GPT-4o-mini function calling); new nodes matched to existing by embedding similarity above threshold t; an LLM resolver marks obsolete relations invalid rather than deleting them. — [Mem0 paper](https://arxiv.org/html/2504.19413v1)
- Mem0 criticism (anecdotal, secondary): auto-resolution can silently delete a memory you still need; DELETE removes it from `search()` and `get_all()`. A third-party "mem-audit" discussion notes that Mem0's newer additive extraction passes nearby existing memories into the extraction prompt so related facts coexist; its author caveats it as one 24-fact set, one measurement per configuration. — [DEV post](https://dev.to/mukesh_13/mem0-auto-resolves-memory-conflicts-for-you-until-it-silently-deletes-one-you-still-need-4f4m), [mem0 discussion 4787](https://github.com/mem0ai/mem0/discussions/4787)
- Zep ingest: LLM steps for entity extraction (with a reflection pass), entity resolution (1024-d name embedding cosine plus full-text candidates, then an LLM duplicate judge that merges name and summary), fact extraction, fact resolution, temporal extraction, and contradiction checks. No per-ingest call count is given. — [Zep paper](https://arxiv.org/html/2501.13956)
- A-Mem: on a new note, take top-k cosine neighbours; an LLM decides which to link; the LLM also decides whether to rewrite neighbours' contextual descriptions and tags ("evolution"). Ablation (GPT-4o-mini, multi-hop F1): full 27.02; no evolution 21.35; no links and no evolution 9.65. — [A-Mem](https://arxiv.org/html/2502.12110)
- Generative Agents reflection: triggered when summed importance of recent events exceeds 150 (about 2-3 times a day); the model reads the 100 most recent memories, generates 3 questions, retrieves against them, and extracts up to 5 insights citing supporting memories; reflections can cite reflections (trees). Ablation TrueSkill: full 29.89, no reflection 26.88, no reflection or planning 25.64, human crowdworker 22.95, no memory/planning/reflection 21.21. — [Generative Agents](https://arxiv.org/html/2304.03442)
- LangMem: hot-path formation is immediate but adds latency; background formation adds no response latency, supports deeper pattern analysis, but updates are delayed. Over-extraction hurts precision, under-extraction hurts recall; reconcile by delete/invalidate or update/consolidate. The page does not specify a contradiction algorithm. — [LangMem conceptual guide](https://langchain-ai.github.io/langmem/concepts/conceptual_guide/)

### Inferences
- Wavefoundry's agent-validated candidates (propose, then validate) resemble Mem0's two-phase extract-then-decide, but with an explicit validation gate and evidence refs. Mem0's literature shows the main risk is silent DELETE of still-valid facts; Wavefoundry's supersede/archive statuses (non-destructive) match Mem0g's and Zep's choice to invalidate rather than delete.
- Generative Agents' "reflection cites its evidence" is the closest published analogue of evidence refs.

### Gaps
- No source quantifies duplicate or contradiction error rates for any system. No independent audit of Mem0's junk-memory rate was found (a search returned only anecdotes and one small self-described audit).

## Forgetting, decay, invalidation

### Takeaway
Real forgetting is rare. Generative Agents has explicit recency decay; Zep has bi-temporal invalidation (facts are kept but marked invalid); Mem0g marks relations invalid; Mem0 base deletes; MemGPT evicts to recall (nothing is lost but it leaves context). LangMem's docs mention memory "strength" from recency and frequency of use but I found no mechanism description.

### Cited Findings
- Generative Agents recency: exponential decay over game hours since last retrieval, decay factor 0.995. — [Generative Agents](https://arxiv.org/html/2304.03442)
- Zep bi-temporal: timeline T (when events occurred) and T' (when ingested); each fact has t_valid, t_invalid, t'_created, t'_expired. An LLM compares a new edge to semantically related existing edges; on temporal overlap the older edge's t_invalid is set to the newer edge's t_valid; new information takes priority on T'. — [Zep paper](https://arxiv.org/html/2501.13956)
- Mem0g: obsolete relations are marked invalid, not deleted. Mem0 base: DELETE on contradiction. — [Mem0 paper](https://arxiv.org/html/2504.19413v1)
- MemGPT: eviction moves messages to recall and updates a recursive summary; no deletion. — [MemGPT](https://arxiv.org/html/2310.08560)
- LangMem docs say good recall should combine similarity with importance and "strength" (recency and frequency of use). — [LangMem conceptual guide](https://langchain-ai.github.io/langmem/concepts/conceptual_guide/)
- Zep community summaries drift from a full label-propagation run and need periodic refresh (authors' stated limitation). — [Zep paper](https://arxiv.org/html/2501.13956)

### Inferences
- Wavefoundry's decay from age plus target-file git churn is not matched by any surveyed system. It is an external-signal staleness proxy (the world changed under the memory), where the surveyed systems use only usage recency or LLM-detected contradiction. Zep's t_invalid is the closest analogue to supersede, but is set by LLM contradiction detection, not by observable file change.
- A least-recently-reviewed audit has no direct equivalent in the surveyed systems; it is closest to Letta's sleep-time re-organization, done by a human or agent on a schedule rather than a background model.

### Gaps
- I found no published evaluation of whether any decay or invalidation policy improves answer quality (Zep's LongMemEval knowledge-update category slightly declined, see Claims). No source on MemoryOS forgetting.

## Retrieval and score combination

### Takeaway
Pure dense vector search is the base case (Mem0, A-Mem, Generative Agents relevance). Zep is the only surveyed system with a documented hybrid of cosine, BM25 and graph BFS, with RRF/MMR/cross-encoder rerankers. Only Generative Agents publishes an explicit recency-importance-relevance formula.

### Cited Findings
- Generative Agents: score = recency + importance + relevance, each min-max normalised to [0,1], all weights 1. Importance is an LLM-rated integer 1-10 at creation time; relevance is cosine similarity. Top-ranked memories that fit the context window are used. — [Generative Agents](https://arxiv.org/html/2304.03442)
- Zep: search by cosine, BM25 full-text and BFS over graph hops; rerankers RRF, MMR, episode-mentions, node-distance and cross-encoder (most accurate, most expensive). — [Zep paper](https://arxiv.org/html/2501.13956)
- Mem0: vector similarity over dense memory embeddings. Mem0g: entity-centric subgraph expansion from anchor nodes, or semantic triplet ranking above a threshold. — [Mem0 paper](https://arxiv.org/html/2504.19413v1)
- A-Mem: top-k cosine (default k=10, sweep 10-50; gains plateau and can decline; MiniLM-L6-v2 embeddings), plus linked notes in the same "box". — [A-Mem](https://arxiv.org/html/2502.12110)
- Letta filesystem agent: grep, semantic search_files, open, close tools, with tool rules forcing a search first; the agent chooses queries and call count. — [Letta benchmarking blog](https://www.letta.com/blog/benchmarking-ai-agent-memory)
- Generative Agents failure modes: missed relevant memories (election), partial recall, embellishment, 6 of 453 (1.3%) hallucinated awareness. — [Generative Agents](https://arxiv.org/html/2304.03442)

### Inferences
- Wavefoundry's dense plus BM25 RRF plus cross-encoder rerank matches Zep's documented best-quality configuration and exceeds Mem0/A-Mem/Letta defaults. At a corpus of about 170 records, the evidence in Letta's filesystem result (agentic grep plus search beats specialized memory on LoCoMo) suggests retrieval sophistication is unlikely to be the binding constraint; record quality and staleness are.
- Generative Agents' importance is LLM-rated per memory with equal weights; Wavefoundry's confidence plus decay is a similar scalar. Equal-weight, unnormalised-then-min-max combination is the only published recipe; nobody published ablations of the weights.

### Gaps
- No source for how LangMem ranks (beyond the docs sentence), nor Letta archival's exact ranker. No published ablation of recency/importance weights.

## Claims, benchmarks, and criticism

### Takeaway
Every headline number is vendor-run or paper-authors-run, on LoCoMo, DMR, LongMemEval or DialSim. Disputes show the numbers swing 58 to 84 for one product depending on evaluation choices. The strongest independent finding is that LoCoMo itself is flawed and that a full-context baseline beats most memory systems on it.

### Cited Findings
- Mem0 paper LoCoMo J (LLM-as-judge), overall (Table 2): full-context 72.90, Mem0g 68.44, Mem0 66.88, Zep 65.99, LangMem 58.10, OpenAI 52.90, A-Mem 48.38. Headline: 26% relative J gain over OpenAI; 91% lower p95 latency and over 90% token saving versus full context. p95 total latency: Mem0 1.44 s, Mem0g 2.59 s, Zep 2.93 s, A-Mem 4.37 s, LangMem 60.4 s, full context 17.1 s. Retrieved tokens per query: Mem0 ~1.8k, Mem0g ~3.6k, Zep ~3.9k, full context ~26k. Stored memory: Mem0 ~7k, Mem0g ~14k, Zep over 600k tokens. Adversarial category excluded. Mem0g did not beat Mem0 on single-hop or multi-hop. Authors note Zep results varied with retrieval timing after ingestion. — [Mem0 paper](https://arxiv.org/html/2504.19413v1) (VENDOR/PEER)
- Zep paper: DMR 94.8% vs MemGPT 93.4% (gpt-4-turbo), but full conversation already scores 94.4%; with gpt-4o-mini full conversation 98.0% vs Zep 98.2%. LongMemEval_s (~115k tokens): gpt-4o-mini 63.8% vs 55.4% full context; gpt-4o 71.2% vs 60.2%; latency about 3.2 s and 2.6 s vs about 31 s and 29 s; context 1.6k vs 115k tokens. Declines on single-session-assistant (about -9% and -17.7% relative) and knowledge-update (about -3% relative, gpt-4o-mini). Authors could not reproduce MemGPT results with gpt-4o-mini; latency included residential-to-AWS network overhead the baselines did not have. — [Zep paper](https://arxiv.org/html/2501.13956) (VENDOR)
- The Zep/Mem0 dispute: Zep's blog says Mem0 misconfigured Zep (user role on both participants, timestamps appended to messages instead of using created_at, sequential searches) and gives a corrected Zep score of 75.14% +/- 0.17, about 10% above Mem0 Graph; Zep p95 search 0.632 s vs Mem0g 0.657 s. Zep argues LoCoMo contexts (~16-26k tokens) fit in modern windows, the benchmark has no knowledge-update questions, and Mem0's full-context (about 73%) beat its best memory system (about 68%). The page has an internal inconsistency (metadata says 24%, body says 10%). — [Zep blog](https://www.getzep.com/blog/lies-damn-lies-statistics-is-mem0-really-sota-in-agent-memory/) (VENDOR, adversarial)
- Zep's earlier ~84% LoCoMo claim was challenged by a Mem0 co-founder's GitHub issue ("Revisiting Zep's 84% LoCoMo Claim: Corrected Evaluation & 58.44% Accuracy"), alleging the adversarial category was included in the numerator; sources differ on the exact mechanism. This detail is from a search-result summary of secondary sources, not the issue itself. — [search summary via Atlan/others](https://atlan.com/know/zep-vs-mem0/) (secondary; unverified)
- Letta: GPT-4o-mini agent with the conversation as a plain file plus grep/search tools scored 74.0% on LoCoMo vs Mem0's reported top graph variant 68.5%. Letta says Mem0's MemGPT numbers were hard to reproduce and Mem0 did not clarify how they were computed, and argues memory benchmarks mainly test retrieval, not agentic memory. — [Letta blog](https://www.letta.com/blog/benchmarking-ai-agent-memory) (VENDOR, adversarial)
- INDEPENDENT-ish audit (Penfield Labs, April 2026, a vendor of a competing memory product, so treat as interested): 99 score-corrupting errors in LoCoMo's 1,540 questions (6.4%); implied ceiling about 93.6%; the gpt-4o-mini judge accepted 62.81% of intentionally wrong but topical answers (caught specific wrong names/dates about 89% of the time). It also reports that several researchers could not reproduce published LoCoMo results and that LongMemEval-S is a context-window test (Mastra's quoted full-context gpt-4o baseline 60.20% vs 84.23% for its memory system). Scripts published in a locomo-audit repo (not inspected). — [Penfield audit](https://dev.to/penfieldlabs/we-audited-locomo-64-of-the-answer-key-is-wrong-and-the-judge-accepts-up-to-63-of-intentionally-33lg)
- One aggregator notes a single product spanning 58 to 95 on LoCoMo across self-reports and that 2026 self-reports (Zep 94.7%, Mem0 92.5%) use different models and setups and are not comparable (secondary, from search summary). — [braindetox](https://braindetox.kr/en/posts/memory_benchmark_scores_reliability_2026.html)
- MemGPT paper (2023): deep memory retrieval GPT-4 32.1% to 92.5%, GPT-4 Turbo 35.3% to 93.4%, GPT-3.5 38.7% to 66.9%; nested KV: GPT-4 and GPT-4 Turbo fell to 0% by three nesting levels while MemGPT with GPT-4 held up to level 4; document QA sample was 50 questions; heavy dependence on the model's function-calling. — [MemGPT](https://arxiv.org/html/2310.08560) (PEER)
- A-Mem: LoCoMo multi-hop F1 27.02 vs 25.02 (LoCoMo baseline) and 26.65 (MemGPT) with GPT-4o-mini; the "at least 2x multi-hop" claim matches ROUGE-L appendix numbers (44.27 vs 18.09) rather than the F1 table; DialSim F1 3.45 vs 2.55 and 1.18; no error bars (authors say repeated API calls were too costly). In Mem0's re-run A-Mem scored lowest (48.38 overall J). — [A-Mem](https://arxiv.org/html/2502.12110), [Mem0 paper](https://arxiv.org/html/2504.19413v1)
- MemoryOS claims average gains of 49.11% F1 and 46.18% BLEU-1 on LoCoMo with GPT-4o-mini over baselines. Abstract only; baselines and absolute scores not checked. — [MemoryOS abstract](https://arxiv.org/abs/2506.06326) (VENDOR/PEER)
- Cognee paper: gains from hyperparameter tuning vary across datasets and metrics; authors say this exposes limits of standard metrics; no figures in the abstract; v1 preliminary. — [Cognee abstract](https://arxiv.org/abs/2505.24478)
- Letta sleep-time compute (arXiv 2504.13171): the blog page I could read gave no numbers. Claims "Pareto improvement" on math benchmarks (AIME, GSM variants); conversational benefit is stated as expectation. — [Letta sleep-time blog](https://letta.com/blog/sleep-time-compute) (VENDOR; paper not read)

### Inferences
- Reliable takeaways across disputes: (1) full-context beats most memory systems on short benchmarks, so benchmarks measure cost/latency savings more than accuracy; (2) scores are sensitive to category inclusion, judge, answer model and how competitors are configured; (3) no benchmark here tests coding-agent memory or staleness against a changing codebase.
- A 170-record corpus fits in context many times over. The Mem0, Zep and Letta evidence indicates that at this scale a full-context or grep-plus-search baseline is the correct comparison for any memory eval Wavefoundry builds.

### Gaps
- No peer-reviewed independent reproduction of any LoCoMo number was found. I could not read the primary GitHub issue for the Zep/Mem0 dispute or the Letta sleep-time paper itself.

## Cost (LLM calls, latency)

### Takeaway
Costs are paid at write time (extraction, resolution, linking) in exchange for cheap reads. Zep and Mem0g are heaviest at write; Mem0's own paper reports Zep's stored memory at over 600k tokens vs about 7k for Mem0.

### Cited Findings
- Mem0: per fact, at least one extraction plus one update call implied; search p95 0.200 s (base) and 0.657 s (graph). — [Mem0 paper](https://arxiv.org/html/2504.19413v1)
- Zep: at least five LLM stages per ingest (entity extraction plus reflection, entity resolution, fact extraction, fact resolution, temporal extraction) plus contradiction checks. Retrieval about 1.6k tokens; end-to-end about 2.6-3.2 s on LongMemEval. — [Zep paper](https://arxiv.org/html/2501.13956)
- A-Mem: about 1,200-2,520 tokens per question vs about 16,900 for LoCoMo/MemGPT baselines; under $0.0003 per memory operation (authors' estimate); 5.4 s processing per note with GPT-4o-mini, 1.1 s with Llama 3.2 1B on one GPU. — [A-Mem](https://arxiv.org/html/2502.12110)
- LangMem: Mem0's paper measured p95 total latency of 60.4 s (search p95 59.8 s) and only about 127 retrieved tokens per query. — [Mem0 paper](https://arxiv.org/html/2504.19413v1) (competitor-measured)
- Letta sleep-time: moves memory editing off the user-facing path; costs a second agent, optionally a larger model; docs give no cost figures. — [Letta sleep-time blog](https://letta.com/blog/sleep-time-compute)
- Generative Agents: no cost figures found in the portion read.

### Inferences
- For Wavefoundry, the write path is infrequent and agent-initiated, so per-write LLM cost is largely irrelevant. Read-time cost is local (embedding, BM25, cross-encoder) and has no per-query API cost.

### Gaps
- Per-write call counts are not stated by Mem0 or Zep; the counts above are inferred from described stages.

## Relevance summary for Wavefoundry (local, repo-visible, about 170 records)

### Takeaway
Mechanisms worth borrowing are cheap and non-destructive: non-destructive invalidation (Zep t_invalid, Mem0g), bi-temporal fields (valid time versus recorded time), evidence-citing reflections, a scheduled consolidation pass (Letta sleep-time, LangMem background), and LangMem-style profile-versus-collection distinction. Heavy mechanisms (graph DBs, community summaries, per-write LLM resolution chains, A-Mem link evolution) are poorly matched to this scale and to repo-visible review.

### Cited Findings
- Zep four-timestamp model is the most directly transferable idea. — [Zep paper](https://arxiv.org/html/2501.13956)
- Letta's filesystem-agent result suggests simple tool-driven search over plain files is competitive. — [Letta blog](https://www.letta.com/blog/benchmarking-ai-agent-memory)
- A-Mem's evolution step rewrites existing notes via LLM, which conflicts with a repo-visible, reviewable record and would churn diffs. (Inference from A-Mem's described mechanism.) — [A-Mem](https://arxiv.org/html/2502.12110)

### Inferences
- Gaps in Wavefoundry relative to the literature: (1) no explicit valid-time versus recorded-time distinction (Zep); (2) no importance scalar distinct from confidence (Generative Agents); (3) no reflection step that synthesizes higher-level records citing lower-level ones.
- Novel relative to the literature: git-churn-derived decay on file targets, and the human or agent least-recently-reviewed audit.

### Gaps
- No evidence for how any of these mechanisms scale down to hundreds of records; every published evaluation is on conversational benchmarks, not coding-agent memory.
