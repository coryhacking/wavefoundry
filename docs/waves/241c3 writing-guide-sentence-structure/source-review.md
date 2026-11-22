# Has Wavefoundry adopted enough of ASD-STE100?

Owner: Engineering
Status: reference
Last verified: 2026-11-21

Wave 241c3 retained this original assessment when it closed. The [measurement instructions and scripts](evidence/README.md) reproduce its baseline. References below to “this folder” describe the original working directory.

Date: 2026-11-21. Read-only review. No repository file was edited.

## Answer

Nearly. The writing guide adopted the STE practices that carry the most meaning: consistent terms, active voice, present tense, explicit actor and condition, and no open hedges in obligations. The writing produced since adoption follows them, and it improved in ways the guide does not even ask for (noun stacks and telegraphic fragments both fell by half or more in specs and review findings).

Three STE areas remain where the writing still falls short and the guide is silent or soft: overloaded sentences, checklist items that hold several actions, and noun stacks. A fourth, complete sentences, is uneven across artifact types. I recommend four sentences for the guide (ADOPT 1 to 4 below) and decline the rest of STE, including the dictionary and the hard 20 and 25 word limits.

The remaining gap is mostly guidance, not practice. Where the guide states a rule, the new writing follows it. The two practice gaps are the changelog and the session handoff, which did not improve on length or voice.

## Method and limits

- Scripts and data are in this folder: `measure.py` (main table and term counts), `newprose.py` and `newprose2.py` (new seed and prompt prose), `validate.py`, `extra.py`, `extra2.py`, and `measures.json`, `measures.md`, `terms.md`, `newprose2.json`.
- Sentences come from Markdown prose only. The script drops fenced code, tables, headings and metadata lines, and replaces each inline code span, file path, snake_case name and URL with one token.
- Every measure except sentence length is a heuristic. I checked each against samples:
  - Passive voice: about 10 of 12 sampled hits were true passives. About half the handoff hits are result states ("Both edit gates are closed"), which the guide permits.
  - Noun stacks of 4+ words: about half the sampled hits were true stacks, in both periods. Read the rates as relative, and halve them for an absolute estimate.
  - Multiple instructions: a sentence that starts with an imperative verb and has a second imperative verb after "and", "then", a comma or a semicolon. Sampled hits were true.
- The STE rule list in Step 1 is from memory of Issue 8. I did not check rule numbers against the standard, so I cite rules by topic.
- The pre and post samples differ in topic and size, so a difference of a few points is not evidence of change.
- Pre-adoption sample: nine waves created 2026-10-10 to 2026-10-16 (20b39, 20e12, 20k0e, 20lkx, 20ngc, 20np5, 20oqx, 20qvn, 20st7), changelog 1.32.0 to 1.38.0, all seeds at 189a2502^, the handoff at 189a2502^.
- Post-adoption sample: waves 23z45, 23z46, 23zbf, 23zbg, 23xo7, 23ve6; changelog Unreleased and 1.43.0 to 1.47.0; seed and prompt text in the working tree that was absent at 189a2502.
- `git diff 189a2502` over the seeds mixes new prose with old blocks that a term sweep touched (change to spec). `newprose2.py` separates them: a block is NEW when no block at 189a2502 shares half its words, otherwise TOUCHED.

## Step 1. STE baseline against the guide

| STE rule (by topic) | Status | Guide text |
| --- | --- | --- |
| Controlled dictionary: approved words, one meaning, one part of speech | Not adopted (stated) | "It is not ... an implementation of the full STE dictionary" |
| Technical names and technical verbs are allowed and kept | Adopted | "Retain necessary technical vocabulary; explain it for the audience instead of replacing it with an inaccurate everyday word." |
| Use one term for one thing, consistently | Adopted | "Keep a term consistent for the same concept, and distinguish concepts that have different effects." |
| Noun clusters of no more than three words; clarify longer ones | Not adopted | none |
| Use articles; do not omit words | Not adopted | none |
| Active voice (always in procedures, where possible in descriptions) | Adopted, as a preference | "Prefer active voice throughout project writing. Name who acts, decides or verifies. ... Use passive voice when the actor is unknown or immaterial and the reader needs the result." |
| Simple tenses; present tense | Adopted, as a preference | "Prefer present tense throughout project writing. Describe what people and systems do." |
| No -ing forms except in technical names | Not adopted | none |
| Use a verb for an action, not a noun | Partial | "Use familiar words and direct verbs." and "Replace vague phrases with the action or result they describe." |
| Procedures: at most 20 words per sentence | Not adopted (stated) | "There is no universal word or sentence limit." |
| Descriptions: at most 25 words per sentence | Not adopted (stated) | same sentence |
| One instruction per sentence | Partial | "Give each step one coherent instruction; separate independent actions when order or verification matters." |
| Imperative form for instructions | Not stated | The Prompt row asks for "ordered instructions" only |
| State the condition before the instruction | Partial | "Put a condition or exception close to the statement it qualifies." and "preserve who acts, the triggering conditions, the action and required outcome" |
| Vertical lists for complex text | Partial | "Use paragraphs for connected reasoning, lists for sequences or genuinely parallel items, and tables for comparisons." |
| One topic per paragraph, topic sentence first | Partial | "What single point should the reader take away?" and "Give the main point first" |
| Paragraph of at most six sentences | Not adopted | none |
| Warnings and cautions: specific, placed before the step | Partial | "Make prerequisites, expected results, failure handling and authority boundaries visible where readers act." |
| Notes give information, not instructions | Not adopted | none |
| No contractions; standard punctuation; one spelling | Not adopted | none |
| Beyond STE: no hedge in an obligation; named setting, number and unit | Adopted | "A requirement must not contain a hedge that leaves the obligation open, such as 'if feasible', 'as needed' or 'where possible'." |

Count: 4 adopted, 6 partial, 10 not adopted or not stated (2 of them declined in the guide's own words).

## Step 2. Measurements

### Sentence length

| Artifact | Period | Sentences | Median | P90 | Over 20 | Over 25 | Over 40 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Changelog | pre (1.32 to 1.38) | 308 | 12.5 | 32 | 26.9% | 17.2% | 6.8% | 88 |
| Changelog | 1.39 to 1.42 | 252 | 16 | 31 | 33.3% | 22.2% | 3.2% | 60 |
| Changelog | post (1.43 to 1.47, Unreleased) | 285 | 15 | 35 | 33.3% | 22.8% | 6.0% | 63 |
| Seeds | pre (all seeds) | 9310 | 14 | 31 | 27.0% | 17.1% | 4.7% | 180 |
| Seeds and prompts | post, NEW blocks | 631 | 13 | 28 | 20.6% | 12.0% | 4.1% | 90 |
| Seeds and prompts | post, TOUCHED old blocks | 1076 | 19 | 42 | 46.5% | 32.2% | 11.3% | 179 |
| Specs, whole | pre | 738 | 16 | 32 | 32.2% | 18.6% | 4.1% | 89 |
| Specs, whole | post | 2062 | 15 | 31 | 30.9% | 18.0% | 3.2% | 88 |
| Spec requirements and ACs | pre | 276 | 19.5 | 37.5 | 47.5% | 28.6% | 8.0% | 89 |
| Spec requirements and ACs | post | 1139 | 16 | 33 | 35.8% | 22.4% | 4.2% | 88 |
| Spec tasks | pre | 69 | 13 | 27 | 15.9% | 11.6% | 1.4% | 48 |
| Spec tasks | post | 179 | 15 | 30.4 | 28.5% | 15.6% | 3.9% | 72 |
| wave.md | pre | 639 | 13 | 24 | 17.2% | 8.8% | 3.3% | 133 |
| wave.md | post | 465 | 12 | 25 | 15.7% | 9.5% | 2.8% | 61 |
| Handoff | pre | 436 | 13 | 21 | 12.4% | 3.4% | 0.2% | 45 |
| Handoff | post, new blocks | 470 | 12 | 22 | 13.4% | 6.8% | 2.3% | 59 |
| Review `observed` | pre | 786 | 13 | 25 | 22.8% | 9.0% | 1.9% | 123 |
| Review `observed` | post | 1059 | 14 | 28 | 22.1% | 13.3% | 3.7% | 104 |
| The writing guide | current | 116 | 12 | 21.5 | 12.1% | 4.3% | 0% | 32 |

Reading: medians sit at 12 to 16 words everywhere, inside both STE limits. The problem is the tail. About one sentence in five passes 25 words in specs and the changelog, and 3% to 6% pass 40. Adoption shortened requirements and ACs (over 25: 28.6% to 22.4%) and new seed prose (17.1% to 12.0%). It did not shorten the changelog, the handoff, tasks or review findings.

Instruction sentences (start with an imperative verb): the STE limit is 20 words.

| Corpus | Imperative sentences | Median | Over 20 | With a second instruction |
| --- | --- | --- | --- | --- |
| Seeds pre | 1592 | 13 | 20.9% | 12.3% |
| Seeds and prompts post, NEW | 151 | 12 | 13.9% | 11.3% |
| Seeds and prompts post, TOUCHED | 212 | 17 | 36.3% | 13.7% |
| Spec tasks pre | 37 | 13 | 18.9% | 35.1% |
| Spec tasks post | 118 | 14.5 | 24.6% | 36.4% |

### Passive voice, noun stacks, fragments

| Artifact | Passive sentences, pre | post | Noun stacks per 1,000 words, pre | post | Sentences of 8+ words with no article or determiner, pre | post |
| --- | --- | --- | --- | --- | --- | --- |
| Changelog | 20.5% | 21.8% | 20.3 | 10.3 | not measured | not measured |
| Seeds (post = NEW blocks) | 13.6% | 8.2% | 19.9 | 10.9 | not measured | not measured |
| Specs, whole | 17.8% | 11.1% | 27.2 | 11.1 | 18.9% | 2.7% |
| Spec requirements and ACs | 21.7% | 12.7% | 27.9 | 10.8 | not measured | not measured |
| wave.md | 21.8% | 7.5% | 41.2 | 24.2 | not measured | not measured |
| Handoff | 28.2% | 25.3% | 39.5 | 33.3 | 20.6% | 23.6% |
| Review `observed` | 11.7% | 8.1% | 64.5 | 28.3 | 33.0% | 8.4% |

Reading: the active-voice rule took hold in specs, wave records, review findings and new seed prose. It did not in the changelog or the handoff. In the handoff's new text, 120 of 474 sentences match the passive pattern and 2 name the actor with "by". Noun stacks halved without a rule but stay highest in the handoff and review findings. Examples from post-adoption text: "marked credible-threat gate carrier", "renamed-vocabulary known-bad fixture", "old-runner pre-flight test", "wave's review evidence projection", "exact-match memory advisories".

### Hedges in obligations

| Corpus | "should" per 1,000 words | Open hedges per 1,000 words |
| --- | --- | --- |
| Seeds pre | 1.26 | 0.08 |
| Seeds and prompts post, NEW | 0.20 (2 uses) | 0.10 (1 use: "using source control where possible") |
| Seeds and prompts post, TOUCHED | 0.56 (14 uses) | 0.16 (4 uses) |
| Specs pre | 0.07 | 0.07 |
| Specs post | 0.11 | 0 |
| Spec requirements and ACs post | 0 | 0 |
| Changelog, handoff, wave.md, review post | 0 to 0.15 | 0 |

Reading: this rule is followed. The 18 hedges left in the seeds are in pre-adoption blocks that a later edit touched without rewriting, for example "repeated calls should be safe when the doc is already in the target wave".

### Term consistency

Counts per 1,000 words are in `terms.md`.

| Concept | Finding |
| --- | --- |
| spec and change | Two names by design: "spec" is the surface name and "change" stays the machine name. "spec" rose from 0.1 to 1.4 per 1,000 words in specs and from 0.2 to 5.0 in the changelog. "change doc" fell from 101 uses in the old seeds to 1 in new text. In 2,527 post spec sentences, none uses "spec" and "the/this/each change" together. One generated wave summary says "delivered 4 changes" and then "for each spec" (23z46). |
| wave | One term. "batch", "iteration" and "sprint" are at or near zero. |
| readiness | "readiness" and "readied" are the terms. "prepare/prepared" as a synonym fell from 2.0 to 0.2 per 1,000 words in specs. In the changelog it rose (1.0 to 2.9) because entries name the Prepare step. |
| approval | "approval", "approved" and "signoff" all appear, at stable rates. The records use "signoff" for the operator's act and "approval" for a lane or council result. I did not find the two swapped in the passages I read. "attestation" fell from 5 uses to 0 in specs. |

No synonym drift worth a rule.

### Qualitative read (14 passages)

| # | Passage | Clear to a reader who did not write it? |
| --- | --- | --- |
| 1 | Changelog Unreleased, dependency flowcharts | Yes. Four short sentences, actor and result first. |
| 2 | Changelog 1.46.0, `/wf-explain` | Yes. |
| 3 | Changelog 1.46.0, "During upgrade reconciliation, merge the walkthrough invitation into the delivery handoff and route it to the project's Explain prompt." | Partly. A release note switches to an imperative with no stated actor. |
| 4 | Post-adoption changelog, "Every ... response, dry run or write and blocked or not, carries an advisory ... listing each extra file ..." (about 60 words, nested parentheticals) | No. The reader must hold six qualifiers to find the verb's object. |
| 5 | Changelog, "Framework tests now treat ... as the enforced tool inventory: ..." (about 60 words, three "must" clauses) | Partly. Three obligations in one sentence. |
| 6 | Spec 23z90 Rationale | Yes. Observed input, actual result and expected result are separate, and each claim says "executed", "read from the code" or "inferred". This is the guide's defect rule followed exactly. |
| 7 | Spec 23z90 Requirement 1 (7 sentences, about 150 words) | Mostly. Precise, but the fifth sentence holds three rules joined by commas. |
| 8 | Spec 23z90 Requirement 5 | Mostly. Names every token and the helper. Ends with "The quoting and truncation are new behaviour for review", which is a note inside a requirement. |
| 9 | Spec 23z90 Tasks | Partly. "Add AC-1 to AC-5 tests ..., and update any test pinning the old `error` text" is two actions under one checkbox. |
| 10 | Post-adoption spec text on the upgrade pre-flight, "Tests: pre-flight refusal and state, both platform renderings, ..." (among the longest sentences in the sample) | No. A list of about 15 test cases written as one sentence. |
| 11 | wave.md 23z46 Wave Summary, intent outcome | Yes. Each sentence names what the operator can now do, then states what "remain[s] unmeasured". |
| 12 | Handoff, current state and 23zbf block | Yes. Short, actor-first, limits stated. |
| 13 | Review `observed`, 23z46 samples | Yes for three of four. The fourth ("Hook, then snapshot, then lock at lines 5327/5344/5368 ...") is a fragment that only the reviewer can parse. |
| 14 | New seed text, install gate paragraph ("If the operator already opened the gate ...") | Yes. Seven instructions, condition first, one action each. |
| Comparison | Pre spec 20np4 Requirements; pre AC "Declaration-aware parity requires ..." (89 words) | The pre text is dense with slashes ("availability/compatibility", "startup/reload reset or preservation semantics") and dropped articles. The post text is easier. |

Result: 8 clear, 4 partly clear, 2 not clear. Each failure has the same cause: one sentence carries a list or several obligations.

## Step 3. Evaluation

### Where the writing still falls short in ways STE would fix

1. **Overloaded sentences.** 18% to 23% of sentences in specs and the changelog pass 25 words, and the worst hold an inline list or several obligations (passages 4, 5, 7, 10). STE fixes this with length limits, one topic per sentence, and vertical lists.
2. **Several actions in one checklist item.** 36.4% of post-adoption task items hold a second instruction, unchanged from 35.1%. A reader marks the item `[x]` as one unit, so a half-done item has no honest state. STE's rule is one instruction per sentence.
3. **Noun stacks.** Down by half, but the handoff (33 per 1,000 words, heuristic) and review findings (28) still stack four or more modifiers before the head noun. STE's limit is three.
4. **Fragments.** Specs fell from 18.9% to 2.7% article-free sentences and review findings from 33.0% to 8.4%, but the handoff did not move (20.6% to 23.6%). STE says not to omit words.
5. **Passive voice in the changelog and handoff.** Flat at about 22% and 25%. The rule exists.

### Which STE rules add value for these readers

Operators read to decide and authorize. AI agents read to act, and they act on each sentence as written. Maintainers read to reconstruct why. For all three, the valuable STE rules are the structural ones: one action or obligation per sentence, a list for a set of cases, a head noun the reader can find, and a complete sentence with its actor. These rules reduce the chance that an agent drops the third clause of a long instruction or that an operator approves an AC whose scope is buried in a parenthetical.

### Which cost more than they give

- The dictionary. Wavefoundry's precision depends on project terms (wave, lane, receipt, readiness, gate) and on code names. A controlled dictionary would need a term for each and a check for each use.
- Hard word limits. The original plan rejected them, and the measurements support that: medians are already inside the limits, and a count cannot tell a clear 30-word sentence from an overloaded one.
- The -ing ban, the six-sentence paragraph limit, and the contraction and spelling rules. They address translation and second-language reading, which are not the measured problem here.

### Guidance or practice?

| Shortfall | Gap type | Evidence |
| --- | --- | --- |
| Overloaded sentences | Guidance | The guide says "There is no universal word or sentence limit" and gives no test for when a long sentence is a defect. |
| Several actions per checklist item | Guidance | The existing sentence allows "one coherent instruction" and separates actions only "when order or verification matters". It does not mention items a reader marks complete. |
| Noun stacks | Guidance | No rule. |
| Fragments | Guidance | No rule. Improved where reviewers read (specs, findings), not in the handoff. |
| Passive in changelog and handoff | Practice | The rule exists and other artifact types follow it. |
| Hedges left in touched seed blocks | Practice | The rule exists. 18 hedges remain in blocks edited since adoption. |

## Recommendations

### ADOPT

**ADOPT 1. A length check, not a limit** (STE sentence-length rules and vertical lists, adapted).
Add to "Understandable", directly after "There is no universal word or sentence limit.":

> Length is a prompt to check, not a limit. When an instruction passes about 20 words, or any other sentence passes about 25, check that it carries one action or one point. If it carries more, split it, and move three or more parallel cases into a list.

**ADOPT 2. One action per item a reader marks complete** (STE one instruction per sentence).
Add to "Understandable", directly after "Give each step one coherent instruction; separate independent actions when order or verification matters.":

> A task, checklist item or acceptance criterion that a reader marks complete holds one action or one result, unless its parts are always verified together.

**ADOPT 3. Break up noun stacks** (STE noun-cluster rule).
Add to the first paragraph of "Understandable", after "Make pronoun references clear.":

> Do not stack four or more nouns and modifiers before a head noun. Name the thing first and attach the rest with a preposition or a clause, as in "the fixture for the known-bad case with renamed vocabulary". A defined project term counts as one word.

**ADOPT 4. Complete sentences in records** (STE "do not omit words", articles).
Add to the first paragraph of "Understandable", after the ADOPT 3 text:

> Write complete sentences in handoffs, status records and review evidence. Keep the subject, the verb and the articles, so the reader does not have to supply who did what.

### DECLINE

| Candidate STE rule | Verdict | Reason |
| --- | --- | --- |
| Controlled dictionary of approved words | DECLINE | It fights necessary technical vocabulary, needs a checker to mean anything, and term consistency is already good without it. |
| Hard limits of 20 and 25 words | DECLINE | Medians are 12 to 16. A count cannot separate a clear long sentence from an overloaded one, and a limit invites the linter the operator rejected. ADOPT 1 keeps the useful part. |
| Paragraph limit of six sentences | DECLINE | Only 1.3% of spec blocks and 9% of new seed blocks pass six sentences, and connected reasoning is the guide's stated use for paragraphs. |
| Active voice only in procedures | DECLINE | The preference already works (specs 17.8% to 11.1%, wave.md 21.8% to 7.5%). A ban would forbid the result statements the guide permits. |
| Imperative form for instructions | DECLINE | Practice already does it: 151 imperative sentences in 631 new seed sentences. A rule adds words and no change. |
| Condition before the instruction | DECLINE | New seed prose puts the condition first 37 times against 9 trailing "if" or "unless" clauses, and the trailing ones read clearly ("Ask which record they mean if the reference is ambiguous"). The existing "close to the statement it qualifies" is enough. |
| Warnings and cautions placed first | DECLINE | "Make prerequisites, expected results, failure handling and authority boundaries visible where readers act" covers it, and I found no passage where a prohibition arrived too late. |
| No -ing forms | DECLINE | It targets translation ambiguity. No sampled passage was unclear because of an -ing form, and project terms use them (indexing, chunking). |
| Verb, not noun, for actions (as a separate rule) | DECLINE | "Use familiar words and direct verbs" already states it. |
| Notes carry information, not instructions | DECLINE | One instance found (passage 8). Not worth a rule. |
| Contractions, punctuation, single spelling | DECLINE | No effect on meaning for these readers. |
| A project glossary as a controlled vocabulary | DECLINE | The guide already requires defining "a term the reader cannot look up", and the term counts show no drift. |

### Reviewer practice (no guide change)

- The reviewer who reads the changelog entry and the handoff at delivery applies the same reader task used on specs: find the actor and the result in each sentence. These two artifacts are the ones that did not improve.
- When an edit touches a pre-adoption seed block for substance, the author applies the guide to the whole block, including its "should" and "as needed" wording. The guide already says to apply it "to documents naturally touched later". Touched blocks are now the weakest prose in the seeds (46.5% over 20 words, 11.3% over 40).
- Reviewers keep asking for a reconstruction of meaning, as the guide says, and treat the ADOPT 1 word counts as a reason to look, never as a finding by themselves.
