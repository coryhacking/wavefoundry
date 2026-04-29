# 210 - Agent Journal Distillation (Internal Helper)

Intent:

- Distill role and persona journals into durable operating memory, promotion candidates, and retirement decisions without losing important evidence.

Tasks:

1. Review recent captures and journal entries for repetition, salience, evidence quality, and current validity.
2. Merge duplicate or near-duplicate lessons.
3. Add missing distillation metadata when useful: memory type, confidence, valid from, valid until, retirement condition, supersedes, superseded by, promotion target, sensitivity, and tags.
4. Move stable lessons into durable sections or promote them to prompt docs, role/persona docs, repo-local memory, or canonical docs.
5. Mark stale entries that are no longer supported by current evidence from the repository.
6. Retire or supersede entries when canonical docs now own the guidance, the risk is structurally fixed, or the context no longer applies.
7. Confirm high-salience entries still deserve high retrieval priority; otherwise decay, retire, or promote them.

Guardrails:

- Do not turn journals into noisy transcripts.
- Do not promote unvalidated lessons.
- Do not require full distillation metadata for hot-path immediate captures; enrich during this step.
- Do not anthropomorphize operational salience cues. Preserve observed engineering impact signals, not claimed agent emotions.
- Do not delete standing directives, operator constraints, or security/release-sensitive cautions without explicit evidence and review.
