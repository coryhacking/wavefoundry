# Agent Journal System Overview

## Purpose

Explain how the Wave Framework uses journals as low-noise operating memory for software-engineering agents, roles, personas, and coordinators across waves and sessions.

## What Journals Are For

Journals are not transcripts, status logs, or personal diaries. They are compact operating-memory records for software delivery work: role/persona identity, active cautions, hard-to-rediscover observations, reusable lessons, promotion candidates, and current watchpoints that would be lost during compaction, restart, or handoff.

They help the framework:

- preserve how an actor should work: stance, priorities, judgment style, non-negotiables, success criteria, and what that actor is responsible for noticing
- keep persona- or role-specific observations close to the actors who need them
- capture critical signals immediately when waiting for closure would risk losing context
- surface durable guidance that may need promotion into canonical docs or workflow memory
- avoid repeating the same local discovery every wave

## Shared Model

- **Immediate capture is allowed:** agents and coordinators may stop and journal any time a durable operating-memory signal appears. Closure is a distillation/reconciliation point, not the only write point.
- **Use a hot-path threshold:** critical signals are written before continuing; high signals are written before handoff or lifecycle transition; medium signals can go to recent captures or handoff; low signals are skipped unless they recur.
- **Keep structure progressive:** immediate captures need only the minimal envelope (`date`, `actor`, `salience`, `why it matters`, `future behavior`). Distillation/reindex can add richer metadata such as validity, supersession, retirement, sensitivity, and promotion target.
- **Prefer distillation over chronological noise:** do not log routine success, transcript fragments, or duplicate canonical policy.
- **Route memory by type:** procedural memory belongs in role/prompt/workflow docs; episodic memory belongs in journals/waves/handoff; semantic memory belongs in canonical docs or repo memory; working memory belongs in handoff or active wave records.
- **Govern checked-in memory:** do not store secrets, credentials, private personal details, raw chat transcripts, sensitive production/customer data, or unrelated operator context. Prefer summaries and evidence refs over verbatim private text.
- **Promote or retire:** stable repo-wide lessons move into canonical docs or long-lived memory; stale cautions and superseded assumptions are retired when later evidence no longer supports them.

## Operational Salience

Operational salience cues are metadata about engineering impact, not claims that agents have emotions. Use them when they help decide whether to preserve or retrieve a memory:

- salience bands: `critical`, `high`, `medium`, `low`
- impact signals: `surprise`, `confusion`, `friction`, `trust-risk`, `urgency`, `relief/resolution`, `confidence-shift`, `operator-signal`
- retrieval inputs: task relevance, current validity, recency, salience band, and evidence confidence

Write "operator frustration was observed" or "trust-risk signal" rather than "the agent felt frustrated."

## Relationship To Wave Closure

- During a wave, journal immediately when a durable signal meets the hot-path threshold.
- At the end of a wave, distill recent captures, validate lessons, merge duplicates, add retrieval metadata, and identify promotion/retirement actions.
- During finalization, promote durable lessons into canonical docs, persona guidance, or workflow memory when appropriate.
- Journal maintenance is part of the lifecycle, not an optional closure afterthought.

## Seeded Repository Expectations

Init and upgrade should seed or refresh journal homes in the repository under:

- `docs/agents/journals/`

The local journal docs define the exact schema, governance, retention expectations, low-noise rules, and upgrade/migration handling for that project. Upgrade must preserve standing directives and active cautions, avoid bulk-rewriting historical entries, and reconcile local journals/roles/personas to the current operating-memory contract.

## Related Docs

- `.wavefoundry/framework/seeds/001-feature-wave-framework-overview.md`
- `.wavefoundry/framework/seeds/130-agent-journal-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/210-agent-journal-distillation.prompt.md`
- `docs/agents/journals/README.md`
