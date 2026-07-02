# 130 - Agent Journal Bootstrap

Intent:

- Create the journal system used by roles, personas, and coordinators to preserve operating memory across waves, sessions, compaction, restart, and handoff.
- Frame journals for software-engineering delivery work, not generic personal memory, companion-agent memory, or transcript logging.
- When a closed `wave-0` baseline exists, use it as the initial historical source for journal seeding and promotion candidates.

Required target-repo outputs:

- `docs/agents/journals/README.md`
- journal files for enabled generic roles
- journal files for synthesized personas

Required journal semantics:

- purpose and scope
- operating identity (stance, priorities, judgment style, success criteria, memory responsibilities)
- salience triggers (what this actor must stop and journal before context is lost)
- distillation (synthesized bullets — the durable, authoritative view of this actor's operating memory)
- active signals (minimal immediate entries awaiting distillation — see filter gate below)
- active watchpoints and cautions (risks still present; retire when risk no longer exists)
- incidents or episodic memories (specific events, review findings, rework loops, tool failures, or invalidated assumptions)
- promotion queue / promotion evidence (what should move to canonical docs or repo memory, and what was promoted where)
- retirement / supersession notes (what no longer applies and why)
- sensitivity and governance notes for checked-in memory

**Section order matters.** Operating Identity and Distillation come before Active Signals. The durable identity of an actor is the primary purpose of a journal; recent activity is secondary. A reader should encounter what defines this actor before they encounter what happened lately.

Journal docs-lint contract (exact structure the docs gate enforces — author to these literally, not paraphrases):

- **Required `##` headings, verbatim and case-sensitive** — every journal file must contain each of these headings exactly (note the capital `A` in `Retirement And Supersession`):
  - `## Operating Identity`
  - `## Salience Triggers`
  - `## Active Signals`
  - `## Distillation`
  - `## Promotion Evidence`
  - `## Retirement And Supersession`
  - `## Governance`
- **Bullets, not prose or numbered lists.** Each of those sections must contain at least one `-` bullet. A section with only prose paragraphs, or only a numbered (`1.`) list, fails the check — lead every content line under these sections with `- `.
- **`## Operating Identity`** bullets must name the role/persona/agent, its responsibility, or its perspective (one of: role, persona, agent, responsibility, perspective, job).
- **`## Salience Triggers`** must contain at least one salience-marker word: `critical`, `high`, `medium`, `low`, `operator`, `compaction`, `restart`, `regression`, `security`, `release`, or `trust`.
- **`## Promotion Evidence`** must reference a stable artifact or identifier in backticks (e.g. `` `docs/references/...` ``).
- **`## Retirement And Supersession`** must describe retirement, supersession, invalidation, or an explicit none (one of: retire, supersede, stale, replace, invalid, none).
- **`## Governance`** must define allowed/disallowed memory, review, deletion, retirement, or sensitivity rules (one of: allowed, disallowed, sensitive, secret, credential, review, retire, delete, supersede) — and must **not** paste raw transcript content or secret values. A Governance line that *forbids* such content by name ("Do not include raw transcript content or secrets") is fine; a line that *contains* a pasted transcript or a `secret: <value>` is not.

Active Watchpoints example format (every bullet must contain one of the required keywords):

```
- Watchpoint: <risk or thing to monitor>
- Follow-up: <action needed in a future wave>
- Escalate: <item that requires escalation>
- Review: <thing that needs to be checked>
```

Capture trigger rule:

Write immediately when the signal is important to the actor's future operation and could be lost by compaction, restart, or handoff. Routine successful execution still does not produce journal entries.

**Filter gate:** Before writing any entry, ask: *"Would this still matter to a new agent inheriting this role with no access to git history?"* If no — skip it. Wave IDs, change IDs, "wave X closed", test-pass counts, and routine success notes almost never pass this test. That information belongs in git and wave docs.

Use this hot-path threshold:

- **Critical:** write before continuing when the signal is compaction-sensitive, operator-directed, safety/security/release-sensitive, trust-risking, or required to avoid imminent wrong work.
- **High:** write before the next lifecycle transition, handoff, subdelegation, or review request.
- **Medium:** queue in Active Signals, `session-handoff.md`, or the active wave record for close-time distillation.
- **Low:** skip unless it recurs or becomes useful during closure review.

Entry triggers include: role/persona operating-identity clarification; operator directive affecting engineering workflow; review cycle that caused rework; hard-to-discover constraint; invalidated assumption; tool/environment failure causing meaningful delay; recurring anti-pattern; sensitive governance edge; confidence shift; trust-risk; or a memory-worthy observation from the actor's perspective.

Skip entries when the fact is already obvious from canonical docs, the work completed normally, the issue was fully fixed with no remaining recurrence risk, or the entry would only duplicate a transcript/status update.

Progressive entry semantics:

- **Required immediate fields:** date, actor, salience, why it matters, future behavior.
- **Recommended immediate fields:** memory type, scope, impact signal, evidence refs.
- **Distillation fields:** trigger, lesson/observation, confidence, valid from, valid until, retirement condition, supersedes, superseded by, promotion target, sensitivity, tags.
- `wave-id` and `change-id` are optional when applicable, not globally mandatory.
- Free-form reflection is allowed inside the structured envelope when it preserves nuance that fields would flatten.

Memory taxonomy and routing:

- **Procedural memory:** role behavior, workflow rules, reviewer heuristics, repeatable practices. Promote to role docs, prompt docs, skills, or canonical workflow docs.
- **Episodic memory:** specific incidents, review findings, rework loops, tool failures, wave events. Store in journals, wave records, or handoff while active.
- **Semantic memory:** durable facts, decisions, constraints, operator preferences relevant to engineering. Promote to canonical docs or `docs/references/project-context-memory.md`.
- **Working memory:** active blockers, next actions, temporary handoff. Store in `docs/agents/session-handoff.md` or active wave records, not long-lived journals.

Bootstrap expectations:

- seed initial observations, cautions, and promotion candidates from the `wave-0` baseline when legacy corpora were harvested during init
- treat `docs/waves/00000 wave-zero-plans-and-specs/wave.md` as the single baseline record; all corpus inventory, captured plan files, and normalization notes live in the wave folder as separate flat files alongside `wave.md` — do not look for `legacy/` or `evidence/` subdirectories inside the wave folder
- expect the baseline record for `wave-0` to carry a legacy-prefixed title and explicit closure refs so journal seeding can prove the baseline wave was fully reconciled rather than merely captured
- convert repeated historical lessons into durable distillation bullets rather than replaying every migrated legacy document as a raw journal entry
- promote stable workflow lessons from the baseline corpus into `docs/references/project-context-memory.md` and other shared core docs when they are broadly reusable
- make journal-derived promotion candidates concrete enough to improve seeded project policies and procedures, not just narrative summaries

Retention decision model:

When evaluating whether a journal entry or promoted memory item should be kept, retired, or promoted:

- **Keep and promote:** lesson is reusable, the risk still exists, the constraint still applies, or the mistake is still easy to make — even if the specific incident was long ago.
- **Keep in journal only:** lesson is project-specific, was a one-time incident, has not recurred, and is not yet structurally resolved — worth watching but not yet stable enough to promote.
- **Retire:** the root cause was structurally fixed (code removed, tool replaced, process changed), the constraint no longer exists, or the lesson only made sense in a context that has since been superseded. Remove it from both journal and memory rather than leaving stale cautions.
- **Never** let retired lessons accumulate as noise. A stale caution is worse than no caution because it trains future agents to distrust the journal.

Memory governance:

- Checked-in journals must not store secrets, credentials, tokens, private personal data, confidential operator details unrelated to repository work, raw chat transcripts, or sensitive production/customer data.
- Operator directives may be recorded only when they affect engineering workflow, repository governance, review expectations, or project delivery; summarize sensitive directives minimally.
- Agents may add or update operating-memory entries within active scope, but deleting or retiring standing directives, operator constraints, or security/release-sensitive cautions requires explicit evidence and review.
- Retirement must record why a memory no longer applies or cite the canonical doc that supersedes it.
- Prefer summaries and evidence refs over verbatim private text.

Operational salience cues:

- Use salience bands `critical`, `high`, `medium`, and `low`.
- Use impact signals `surprise`, `confusion`, `friction`, `trust-risk`, `urgency`, `relief/resolution`, `confidence-shift`, and `operator-signal` only when they affect capture, retrieval, routing, or promotion.
- Do not anthropomorphize the agent. Record observed operational impact, not claimed agent emotion.
- Retrieval priority combines relevance to current engineering task, recency/current validity, salience, and evidence confidence.
- High-salience entries must decay, retire, or promote during closure/reindex when current evidence changes.

Guardrails:

- Journals are advisory and should not replace canonical docs.
- Keep immediate entries concise enough to happen before context is lost; add rich metadata during distillation.
- Distill repeated lessons rather than allowing journals to grow into noisy transcripts.
- Keep journal retention bounded and explicit so long-lived repositories do not accumulate unreviewed or overly sensitive history indefinitely.
- Do not leave durable procedure updates trapped only in journals when they belong in canonical workflow, verification, or review docs.
- Do not journal routine success. The absence of a journal entry is the signal that work completed normally. If journals fill with success records, they lose their signal value for future agents.
- Do not make every lifecycle artifact verbose with salience. Add `Salience / Impact` only where it changes routing, escalation, handoff, preservation, or future behavior.
