# 210 - Agent Journal Distillation (Internal Helper)

Intent:

- Distill role and persona journals into durable operating memory, promotion candidates, and retirement decisions without losing important evidence.

Tasks:

1. **Delete all activity-log content first — by behavior, not by section name.**
   - Remove any entry that is purely a record of what shipped, what wave closed, or what tests passed. These entries belong in git history and wave docs, not journals. Entries that survive must answer yes to: *"Would this still matter to a new agent inheriting this role with no access to git history?"*
   - If an entire section contains only activity-log entries, delete the whole section — regardless of its heading name (e.g. `## Recent Entries`, `## Recent Captures`, `## Activity Log`, or any other chronological log heading).
   - After deleting any sections, scan all remaining sections for references to the deleted section names and remove or replace those references.
2. Review remaining active signals and journal entries for repetition, salience, evidence quality, and current validity.
3. Merge duplicate or near-duplicate lessons.
4. Add missing distillation metadata when useful: memory type, confidence, valid from, valid until, retirement condition, supersedes, superseded by, promotion target, sensitivity, and tags.
5. Move stable lessons into the Distillation section or promote them to prompt docs, role/persona docs, repo-local memory, or canonical docs.
6. Mark stale entries that are no longer supported by current evidence from the repository.
7. Retire or supersede entries when canonical docs now own the guidance, the risk is structurally fixed, or the context no longer applies.
8. Confirm high-salience entries still deserve high retrieval priority; otherwise decay, retire, or promote them.
9. **Ensure `## Distillation` exists:** if the journal has no Distillation section, create one. Review Incidents and any remaining entries for lessons not yet extracted as concise bullets; promote qualifying lessons. Do not invent lessons — extract only from existing entries.
10. Verify section order: Operating Identity and Distillation must appear before Active Signals. Rename any `Recent Captures` section to `Active Signals`.

Guardrails:

- Do not turn journals into noisy transcripts.
- Do not promote unvalidated lessons.
- Do not require full distillation metadata for hot-path immediate captures; enrich during this step.
- Do not anthropomorphize operational salience cues. Preserve observed engineering impact signals, not claimed agent emotions.
- Do not delete standing directives, operator constraints, or security/release-sensitive cautions without explicit evidence and review.
