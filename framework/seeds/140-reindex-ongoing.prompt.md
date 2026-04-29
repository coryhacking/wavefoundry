# 140 - Reindex Ongoing

Intent:

- Keep the planted Wave Framework layer synchronized with the project as reflected in the repository over time.

Scope modes:

- `quick` — metadata, links, and prompt-surface consistency refresh
- `targeted` — update only affected docs, prompts, personas, and memory summaries
- `full` — full prompt-system, persona, and memory drift scan

Tasks:

1. Read `seed-020`.
2. Detect drift in canonical docs, prompt surface, persona docs, journal health, and wave artifacts.
3. Refresh `docs/reports/reindex-<YYYY-MM-DD>.md`.
4. Flag promotion candidates from journals and completed waves, including procedural/semantic memories that should move to canonical docs.
5. Flag stale, superseded, or over-broad journal entries, personas, and prompt-surface elements.
6. Update the prompt-surface manifest when repo-local prompt behavior changes.
7. For journal and persona drift, check operating identity, salience triggers, governance, taxonomy/routing, progressive capture fields, validity/retirement cues, and anti-sensitive-data rules.
8. When salience metadata exists, use relevance, current validity, recency, salience band, and confidence to decide whether to keep, promote, decay, or retire the memory.

Guardrails:

- Do not overwrite active wave memory blindly.
- Prefer targeted updates before full regeneration.
- Do not bulk-rewrite historical journal entries just to fit the current schema; add current structure around them and preserve evidence unless a memory is explicitly retired or superseded.
- Do not leave high-salience entries high forever by default; validate, promote, decay, or retire them based on current evidence.
