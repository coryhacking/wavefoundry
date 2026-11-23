# Agent memory lifecycle: consolidation, forgetting, staleness, contradiction, and whether memory helps (2024-2026)

Owner: Engineering
Status: active
Last verified: 2026-11-23

The body below is copied unchanged from wave 245na's work folder on 2026-11-23 as the evidence base for arc `244cm-arc memory-quality`.

Research date: 2026-11-23. Evidence strength is labeled per bullet: [STRONG] = controlled study, multiple tasks/models or peer-reviewed; [MODERATE] = single study or vendor/self-reported; [WEAK] = secondary source, preprint with limited detail, or single anecdote. Many cited arXiv papers are 2026 preprints I could read only at abstract level; I flag where numbers could not be verified.

## Surveys: what do recent surveys conclude?

### Takeaway
Surveys agree the field is fragmented and organize memory by forms, functions and dynamics (formation, evolution, retrieval). They are taxonomies, not evidence about which lifecycle mechanism works; the only survey-adjacent empirical analysis found says benchmarks often do not require external memory and that forgetting is barely evaluated.

### Cited Findings
- "Memory in the Age of AI Agents: A Survey" (Hu et al., arXiv Dec 2025, v2 Jan 2026) organizes the field by forms (token-level, parametric, latent), functions (factual, experiential, working) and dynamics (how memory is "formed, evolved, and retrieved over time"); it says the long-term/short-term taxonomy is insufficient, and lists open directions: memory automation, RL integration, multimodal, multi-agent, trustworthiness. The abstract does not describe specific consolidation or forgetting mechanisms (full text not read). — [arXiv 2512.13564](https://arxiv.org/abs/2512.13564)
- Other 2025-2026 surveys exist: "Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers" (2603.07670), "Rethinking Memory Mechanisms of Foundation Agents / A Survey of Agent Memory in the Second Half" (2602.06052), and "AI Meets Brain" cognitive-neuroscience-to-agents survey (2512.23343). The 2602.06052 survey notes that forgetting/retention policies are mostly heuristic (recency decay, importance thresholds), with learned removal emerging. — [search listing](https://arxiv.org/abs/2512.13564) ; [2602.06052](https://arxiv.org/html/2602.06052v3); [2512.23343](https://arxiv.org/html/2512.23343v1)
- "Anatomy of Agentic Memory" (arXiv 2602.19320, 2026): many benchmarks fit inside a 128k window (HotpotQA ~1k tokens, LoCoMo ~20k, MemBench ~100k); only LongMemEval-M (>1M) structurally requires external memory; it does not show memory systems beating full-context prompting, and says simple full-context or retrieval baselines often suffice. Lexical F1 can misrank systems versus an LLM judge. Swapping gpt-4o-mini for Qwen-2.5-3B dropped Nemori's score 0.781 to 0.447 and raised memory-update format errors from 17.91% to 30.38% ("silent failure": corrupted memory writes go unnoticed). Per-turn latency ranged from ~0.3 s to ~32.4 s; AMem took ~15 h to build its index. No dedicated forgetting evaluation; asynchronous consolidation can leave memory stale. Analysis covers six systems, mainly LoCoMo. — [arXiv 2602.19320](https://arxiv.org/html/2602.19320)
- Mem0 (Apr 2025, vendor paper): reports 91% lower p95 latency and >90% token savings versus full-context on LOCOMO, and 26% relative LLM-as-judge improvement over OpenAI's memory. A third-party write-up says the savings cover only retrieval, not extraction costs (unverified). Vendor-reported. — [arXiv 2504.19413](https://arxiv.org/abs/2504.19413); [dev.to critique](https://dev.to/crabtalk/mem0-what-three-memory-scopes-actually-cost-1kpc)

### Inferences
- Surveys give vocabulary (experiential vs factual vs working memory; formation/evolution/retrieval) but no ranking of lifecycle mechanisms. Wavefoundry's records are "experiential" memory in token space; the relevant evidence is the experience-reuse and harm literature below, not conversational-memory benchmarks.
- Conversational memory benchmark gains (LoCoMo) are weak evidence for repository lesson stores, because those benchmarks may not need memory at all.

### Gaps
- I could not read the full text of any survey, so their specific claims on consolidation/forgetting are not captured.

## Experience reuse: does reusing past failures and successes help coding tasks, and when does it hurt?

### Takeaway
Experience stores show consistent gains when the stored items are curated or verified (SWE-bench gains of roughly 4.65-9.4 points reported; strong gains on web agents), but unfiltered "add everything" memory is measurably worse than a small fixed memory. Agents tend to follow retrieved experience closely, so quality of what is stored matters more than quantity.

### Cited Findings
- ExpeL (Zhao et al., 2023/2024): agent gathers experiences and extracts natural-language insights, recalled at inference without parameter updates; abstract reports "consistent enhancement" as experience accumulates. No figures obtained. — [arXiv 2308.10144](https://arxiv.org/abs/2308.10144)
- Agent Workflow Memory (ICML 2025): 24.6% relative gain on Mind2Web and 51.1% relative on WebArena, with fewer steps; up to 22.5 points on WebArena after tens of examples; on Mind2Web cross-website and cross-domain splits +8.9 and +14.0 absolute, with larger margins as the train/test gap widens. [MODERATE, authors' numbers] — [ICML listing](https://icml.cc/virtual/2025/poster/45496) (figures via search summary)
- Dynamic Cheatsheet (Suzgun et al., 2025): reported Claude gains of ~9% on GPQA-Diamond and ~8% on MMLU-Pro Engineering/Physics; larger gains from retaining reusable solver code (e.g. GPT-4o Game of 24 10% to 99% per a secondary summary). Reasoning/math/puzzle tasks, not coding repos. — [arXiv 2504.07952](https://arxiv.org/pdf/2504.07952)
- SWE-Exp (2025): experience bank from successful and failed repair attempts; v1 41.6% on SWE-bench Verified with DeepSeek-V3-0324, v2 reports 73.0% Pass@1 with Claude 4 Sonnet (backbones differ, baselines not captured). Self-reported. — [arXiv 2507.23361](https://arxiv.org/html/2507.23361v2)
- MemGovern (Jan 2026): converts GitHub issue/PR history into 135K governed "experience cards"; +4.65% resolve rate on SWE-bench Verified (points vs relative not stated). The abstract names an explicit "governance" (cleaning) step; details not read. — [arXiv 2601.06789](https://arxiv.org/abs/2601.06789)
- MemCoder: +9.4% resolve rate over DeepSeek-V3.2 on SWE-bench Verified, storing human-verified solutions in persistent memory. Detail from a search summary only. [WEAK] — [search result summary](https://arxiv.org/html/2507.23361v2)
- Faithfulness problem: "LLM Agents Are Not Always Faithful Self-Evolvers" (Jan 2026) intervened causally on raw vs condensed experience across 4 frameworks, 13 backbones, 9 environments: agents consistently depend on raw experience but often disregard or misinterpret condensed experience (summaries/lessons), even when it is the only experience given. No effect sizes obtained. — [arXiv 2601.22436](https://arxiv.org/abs/2601.22436)
- Repository context files (the closest analogue to always-loaded lessons): Gloaguen et al., "Evaluating AGENTS.md" (arXiv 2602.11988, ICLR 2026 venue): across coding agents and LLMs, context files give no improvement in task success and raise inference cost by over 20%; agents follow the instructions (more exploration and testing); repository overviews do not help; context files are useful for non-standard practices. A search summary says LLM-generated files tended to hurt while developer-written ones slightly helped, but the abstract I fetched gives no per-condition deltas. [STRONG on direction, numbers unverified] — [arXiv 2602.11988](https://arxiv.org/abs/2602.11988)

### Inferences
- Gains cluster where memory carries information the model cannot derive from the repo (non-obvious workflows, human-verified fixes, distribution shift in AWM). Lessons that restate what the code already shows are low value and cost tokens (AGENTS.md result).
- Failure-based memories (failed_attempt, fragile_file) match SWE-Exp's use of failed trajectories, but no ablation isolating failure memories on coding tasks was found.
- Verified/human-confirmed sources (MemCoder, MemGovern governance) are the ones reporting gains; this is consistent with Wavefoundry deriving records from review findings rather than raw agent self-summaries.

### Gaps
- ExpeL and Reflexion quantitative results were not retrievable here; Agent KB and a Reflexion number are not covered.
- No controlled study of a "lessons learned" store for a single long-lived repository (as opposed to cross-task benchmark pools) was found.
- Baselines in SWE-Exp, MemGovern, MemCoder not compared head-to-head; all self-reported.

## Harm: stale or wrong memories, error propagation, poisoning, distraction

### Takeaway
The best controlled evidence shows that unfiltered self-generated memory reduces performance below a no-growth baseline, that retrieved bad experience is imitated ("experience-following"), and that agents trust stale instruction text over contradicting evidence. Poisoning attacks are effective at very low poison rates, though some results come from idealized settings.

### Cited Findings
- Xiong et al., "How Memory Management Impacts LLM Agents" (arXiv May 2025, ACL 2026): documents "experience-following" (similar retrieved record yields similar output), error propagation and misaligned experience replay. Using GPT-4o-mini over four agent tasks, add-all memory was worse than a small fixed memory on every task (-12.1, -3.7, -7.8, -11.6 points) while growing memory 2-41x. Strict (human-style) selective addition beat fixed memory by +3.4, +21.8, +10.9, +13.9 points. Coarse LLM judges (gpt-4o-mini) captured only part of the gain; a fine-tuned judge was closer. [STRONG; not coding tasks (regression, EHR code generation, driving, IoT traffic)] — [arXiv 2505.16067](https://arxiv.org/html/2505.16067v2)
- Same paper, deletion: history-based deletion (remove records that harm when retrieved) cut memory 13-28% with accuracy changes of -1.2, +3.4, +0.8, +4.2 points; periodic deletion cut 60-70% with -3.3, -0.1, -0.1, -4.6; combined cut ~70-79% with -4.4, +3.7, -1.0, +0.1. Deleted records had lower correctness than retained ones on two agents, but on AgentDriver with one judge retained memory scored lower than deleted. Mixed, small effects. — [arXiv 2505.16067](https://arxiv.org/html/2505.16067v2)
- Stale instruction files: "When Instruction Files Go Stale" (arXiv 2611.09802, Nov 2026): 22 maintenance tasks, 3 stale instructions (test command, code location, component procedure), 732 trajectories, two models incl. Claude Sonnet 5.5. Agents follow stale guidance when relevant, sometimes even when correct information is available elsewhere; the stale test command cost ~2 extra tool calls per run (a third more than corrected); no detectable difference for the other two; agents recovered from immediate failures but none repaired the underlying file. Removing the instruction prevented most obsolete-path operations. Small preprint. [MODERATE] — [arXiv 2611.09802](https://arxiv.org/abs/2611.09802)
- "The Working Set of a Coding Agent: Coherence Debt in Repository-Scale Tasks" (Aug 2026): agents follow a convention file's standard even when it prescribes worse code, so a stale file "costs more than no file"; treated as authoritative when it conflicts with code. Seven models, five harnesses. Abstract only; no numbers for stale vs none. [WEAK-MODERATE] — [arXiv 2608.16630](https://arxiv.org/abs/2608.16630)
- "Context rot" in AI config files (arXiv 2606.09090): a README consistency checker found stale code-element references in 23.0% of 356 sampled repositories. — [arXiv 2606.09090](https://arxiv.org/html/2606.09090)
- AgentPoison (NeurIPS 2024): poisoning memory/RAG knowledge base with <0.1% poison rate gave ~80% average attack success (v1 abstract: 82% retrieval success, 63% end-to-end) with <1% benign-performance drop; requires white-box access to the embedder; triggers transfer across embedders. Tested on driving, QA and EHR agents. — [arXiv 2407.12784](https://arxiv.org/html/2407.12784v1) ; [NeurIPS poster](https://neurips.cc/virtual/2024/poster/94715)
- MINJA (NeurIPS 2025, ICLR 2026 listing): injects malicious records via ordinary queries and outputs only; 98.2% average injection success and 76.8% average attack success. A 2026 follow-up (arXiv 2601.05504) says such results come largely from idealized settings and calls for realistic testing. Figures vary by arXiv version. — [arXiv 2503.03704](https://arxiv.org/abs/2503.03704) ; [follow-up](https://arxiv.org/pdf/2601.05504)
- Chroma "Context Rot" (July 2025, 18 models): degradation grows with input length even on simple tasks; semantically similar but incorrect passages (distractors) hurt, and more distractors hurt more; performance drops faster as the target-query semantic gap widens. Vendor (vector DB) with a retrieval-favoring incentive; mechanism unexplained. LMU/Adobe NoLiMa corroborates. — [Chroma report](https://research.trychroma.com/context-rot) ; [coverage](https://the-decoder.com/yet-another-study-finds-that-overloading-llms-with-information-leads-to-worse-results/)
- Memory poisoning/defense: "Memory Poisoning Attack and Defense on Memory Based LLM-Agents" (2601.05504) and MemPoison (2605.29960, bypassing selective memory mechanisms) exist; details not read. — [arXiv 2601.05504](https://arxiv.org/pdf/2601.05504); [arXiv 2605.29960](https://arxiv.org/pdf/2605.29960)

### Inferences
- The strongest finding for Wavefoundry: write-side selectivity beats retrieval-side or deletion-side cleanup. Add-all hurt; strict admission helped; deletion gave only small, mixed gains.
- Stale-path and stale-command records are the most documented repo-specific harm; file-churn decay and evidence links directly target this. Evidence that a stale record is worse than none is moderate (one abstract, one small study).
- Poisoning risk depends on who can write memory. A record store drafted from internal review findings has a smaller attack surface than memory written from arbitrary user-facing queries (MINJA) or external knowledge bases (AgentPoison); the risk is mainly if review findings ingest untrusted content (e.g. issue text, dependency output).
- Wavefoundry records that agents can verify against files (evidence-linked) address "silent failure" (corrupted writes unnoticed).

### Gaps
- No quantitative study of memory distraction specifically on coding agents with irrelevant retrieved lessons was found; Chroma's distractor result is the nearest proxy.
- Exact magnitude of stale-vs-no-file harm is not available (abstract only).
- Whether poisoning results (AgentPoison/MINJA) transfer to code-repo lesson stores is untested.

## Consolidation and forgetting: summarization, merging, decay, utility-based eviction, small memories, human review

### Takeaway
There is little head-to-head evidence on consolidation methods. Available data suggests keeping memory small and quality-gated at write time matters most, history/utility-based deletion helps modestly, summarization of experience is often ignored or misread by agents, and conflict resolution (revising memories) remains weak.

### Cited Findings
- Condensed (summarized) experience is often disregarded or misinterpreted; agents lean on raw experience. — [arXiv 2601.22436](https://arxiv.org/abs/2601.22436)
- Quality-gated addition with a small memory outperformed add-all with 2-41x larger memory; stricter judges gave better results than coarse ones (+21.8 points on EHR code generation with strict gating). Human-style strict evaluation was the best addition policy tested, which is the nearest evidence on verification value; "strict" there means an evaluator with ground-truth-like feedback, not literally a human reviewer. — [arXiv 2505.16067](https://arxiv.org/html/2505.16067v2)
- "Forgetful but Faithful" (arXiv 2512.12856): proves greedy marginal-utility-per-weight eviction has approximation guarantees and that LRU is optimal when usefulness decays exponentially with age; introduces FiFA benchmark for narrative agents; theory plus a synthetic/generative-agent benchmark, not coding. [MODERATE] — [arXiv 2512.12856](https://arxiv.org/pdf/2512.12856)
- "When to Forget: A Memory Governance Primitive" (arXiv 2604.12007): argues agent memory lacks a principled trust/deprecation signal; tested in a synthetic environment and a small stale-memory retrieval experiment. [WEAK] — [arXiv 2604.12007](https://arxiv.org/pdf/2604.12007)
- Conflict resolution/selective forgetting: MemoryAgentBench (ICLR 2026) includes a conflict-resolution competency (revise or remove information given contradictions). A third-party run (2606.15903) reported multi-hop conflict accuracy of 28-37% at 6K and 17-19% at 32K contexts, with single-hop near-perfect. A Salesforce paper (2610.09193) questions whether the scores measure forgetting versus a last-write rule, and 2607.20553 notes a shared answer model may override memory with parametric knowledge. Interpretation disputed. — [arXiv 2507.05257](https://arxiv.org/html/2507.05257v3); [2606.15903](https://arxiv.org/pdf/2606.15903); [2610.09193](https://arxiv.org/pdf/2610.09193)
- Other 2026 stale-memory work: Memora (ACL Findings 2026) adds a forgetting-aware accuracy metric penalizing obsolete memory use; TEPA (2608.07429) revokes stale memories when newer conflicting evidence arrives; AgingBench (2605.26302) measures time-dependent reliability loss across 7 scenarios and 14 models. Results not read. — [Memora](https://aclanthology.org/2026.findings-acl.1337.pdf); [TEPA](https://arxiv.org/pdf/2608.07429); [AgingBench](https://arxiv.org/html/2605.26302)
- Community practice: verify memory against the repo on write and recall, withholding memories whose cited code has changed (Kage); Stratum proposes structural, historical and agent-written tiers. Blog/preprint, no controlled results. [WEAK] — [dev.to](https://dev.to/kage18/your-coding-agents-memory-should-have-to-prove-itself-2m80); [Stratum](https://arxiv.org/pdf/2610.36153)

### Inferences
- Age-plus-churn decay is directionally supported by the theory (decaying usefulness favors recency eviction) and by stale-file harm, but the coupling to target-file change is more targeted than recency alone and no study tests it. Churn-triggered invalidation looks stronger than pure age because staleness in code is event-driven, not time-driven.
- Merging/summarizing lessons carries a risk: condensed lessons may be ignored (faithfulness result). Keeping records short, specific and evidence-linked (raw anchor) may help usage.
- Evidence for periodic audits: history-based deletion produced small gains (+3.4 and +4.2 on two tasks) and "periodic" deletion often lost accuracy; audits driven by observed harm beat blind periodic pruning. Human review of memories is not directly tested in any study found; the closest evidence is that stricter verification at admission wins.

### Gaps
- No direct experiments comparing summarization vs merging vs decay vs eviction on coding agents.
- No study found on human-in-the-loop review of memory records versus agent-only validation.
- The three 2026 papers on stale-memory revocation were not read beyond summaries.

## Context size: always-in-context instructions vs retrieved memory

### Takeaway
Long inputs degrade reliability even on simple tasks, instruction-following declines as instruction count grows, and always-loaded repo files have shown no net success benefit while costing 20%+ more. Anthropic's guidance favors small curated context plus just-in-time retrieval and external notes.

### Cited Findings
- Anthropic, "Effective context engineering for AI agents" (2025): context is a finite attention budget; recall accuracy falls as the window fills ("context rot"); agents retrieve just in time via tools rather than preloading, write notes to memory outside the context window, and use sub-agents with clean contexts. Read via search excerpts/summaries, not the full post. — [Anthropic](https://anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Chroma Context Rot (July 2025): degradation with input length across 18 models, worsened by distractors and semantic gap (details above). — [Chroma](https://research.trychroma.com/context-rot)
- IFScale (Jaroslawicz et al., July 2025, NeurIPS 2025): 20 models, keyword instructions scaled from 10 to 500; best frontier models reach only ~68% accuracy at 500; reasoning models show threshold decay (near-perfect then drop); models favor earlier instructions; reasoning models have higher variance at extreme densities. Task is synthetic keyword inclusion, not repo rules. — [arXiv 2507.11538](https://arxiv.org/abs/2507.11538)
- AGENTS.md study: no success gain and >20% higher cost from context files; agents obey them, which increases exploration and tests; repository overviews do not help. — [arXiv 2602.11988](https://arxiv.org/abs/2602.11988)
- Stale instruction lines are followed even when correct info exists elsewhere (see Harm). — [arXiv 2611.09802](https://arxiv.org/abs/2611.09802)

### Inferences
- A capped briefing is consistent with the evidence (small, relevant, budgeted). The relevant risk is rule-count: IFScale suggests compliance decays gradually with count, so the cap matters more than the briefing's total tokens, and order/position matters (earlier instructions favored).
- Because agents obey injected context, every surfaced record is effectively an instruction; wrong or irrelevant records cost steps (AGENTS.md cost +20%, stale command +1/3 tool calls).
- Retrieving by task (file/area match) rather than loading every record aligns with just-in-time guidance and with distractor sensitivity; non-matching records add distractors.

### Gaps
- No study measures how many repo-specific lessons can be surfaced before coding-agent performance drops; IFScale is the only scaling proxy.
- Anthropic post and Chroma report not read in full via fetch here.

## Cross-cutting implications for Wavefoundry's design

- Supported by evidence: quality gate at admission (Xiong et al.: strict addition big gains; add-all harmful), evidence links for verification (silent-failure and stale-file findings), capped retrieval (context rot, IFScale, AGENTS.md cost), human-verified/governed sources reporting SWE-bench gains (MemCoder, MemGovern).
- Weakly supported: age/churn decay and periodic audits (theory plus indirect staleness harms; no direct test), failure-lesson types specifically (SWE-Exp uses failures but no ablation).
- Risks to watch: lessons that restate repo-visible facts (no benefit, extra cost); condensed lesson wording being ignored; stale path/command records followed over live code; agent-validated records inheriting the agent's own errors (error propagation; coarse LLM judges recovered only part of the gain from strict evaluation); memory eval itself (benchmarks that do not need memory, lexical metrics misranking).
- Unknown: measured net benefit of a lesson store on one long-lived repo. Wavefoundry's own memory eval would add primary evidence the literature lacks.
