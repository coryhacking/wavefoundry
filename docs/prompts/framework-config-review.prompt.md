# Framework Config Review

Owner: Engineering
Status: active
Last verified: 2026-06-16

**Shortcut phrases:** `Framework config review` · `Config review` · `Review agent config`

Audit the agent operating surface — the configuration that steers how agents work in this repository — and recommend what to **keep**, **revise**, or **retire**. Agent config accretes over time: duplicate-of-default blocks, orphaned primitives, constraints tied to a superseded model era or a one-off incident, oversized context files, and docs that have drifted from the code. Left unattended it wastes tokens and degrades agent decisions. This review is the standing, removal-biased pass that keeps the surface lean and current.

> **Note:** This review **recommends**; it never auto-deletes. Findings feed a normal reviewed change/wave. It does not record any lifecycle signoff.

---

## Who runs it, and when

- **Owner:** in a multi-user repository this review is **recommended to a senior / principal architect or engineer** — it retires standing constraints, which is judgment-heavy and authority-bearing. That person **initiates** it; it is never executed automatically. In a single-maintainer repo it applies to the maintainer.
- **Cadence:** evaluate it on **every major/minor framework upgrade**. The upgrade surfaces a one-line recommendation to run this review; the owner decides each time whether to do so. There is no time-threshold or wave-count state — "evaluate it at each major/minor upgrade" *is* the cadence. It is also fine to run on demand whenever the surface feels heavy.

---

## Inventory (what to audit)

Walk whichever of these exist in the repository:

- **`AGENTS.md` / `CLAUDE.md`** — root **and** per-folder/per-area files.
- **Seeds** (`.wavefoundry/framework/seeds/`) and **rendered prompts** (`docs/prompts/`).
- **Standing guardrails / constraints** — stage gates, edit gates, review requirements, commit/close policies.
- **The memory index** — the persistent agent-memory store, if present.
- **Planning / spec / architecture docs** — `docs/architecture/`, decision records, per-area `AGENTS.md` intent sections.

## Audit checks (removal-biased)

For each item, look for:

1. **Duplicate-of-default** — content that merely restates a framework default. Retire; the default already covers it.
2. **Orphaned / undiscoverable primitives** — a prompt, agent, tool, or constraint nothing points to and nobody invokes. Retire or wire up discoverability.
3. **Superseded-model-era constraints** — guidance written for an older model's limitations that no longer applies. Retire or rewrite for current capability.
4. **One-off-incident constraints** — a rule added to prevent a specific past mistake that is now obsolete or generalized elsewhere. Retire or fold into the general rule.
5. **Stale cross-references** — links/pointers to files, tools, or sections that have moved or been removed. Fix or cut.
6. **Context bloat** — oversized root `AGENTS.md`/`CLAUDE.md` that wastes tokens and degrades decisions. Flag content that belongs in a per-area file, or that should simply be cut. Smaller, scoped context beats a giant root file.

## Doc-sync verification

Self-updating docs are unreliable; **verifying sync is the reliable move.** For planning / spec / architecture docs and per-area `AGENTS.md`, check that each load-bearing section still matches the code it describes. Surface drifted sections as findings (`revise`) — do **not** auto-rewrite them. Spot-check against the actual code (use the `code_*` tools / `code_ask`); a doc that confidently describes a structure that no longer exists is worse than no doc.

---

## Output (structured, recommend-only)

Produce a findings list. Each finding:

- **Target** — file + section/line.
- **Verdict** — `keep` · `revise` · `retire`.
- **Rationale** — one line; for `retire`, which audit check it failed; for `revise`, what drifted or bloated.
- **Suggested action** — concrete next step (cut these lines / move to `payments/AGENTS.md` / update to match `X`).

Group by verdict. Lead with `retire` (the removal bias). End with a one-line summary: counts per verdict + the single highest-value change. The findings are a recommendation set suitable to admit as a change/wave; nothing is deleted by this review.

---

## Relationship to Other Commands

| Command | When to use |
|---|---|
| **Framework config review** | Audit + prune the agent operating surface; recommended each major/minor upgrade |
| **Codebase cleanup review** | Prune **code** (dead code, duplication, complexity, debt) — the code counterpart to this agent-surface review |
| **Council review** | Adversarial + council pass on a specific artifact (a plan, change, design) |
| **Evaluate decision** | An architectural/technology decision specifically — produces an ADR |
| **Upgrade wave framework** | Surfaces the recommendation to run this review on a major/minor upgrade |
