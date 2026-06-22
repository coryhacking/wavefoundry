# Framework Config Review

**Applicable when:** an agent-configuration review is being run — recommended for evaluation on every major/minor framework upgrade (see **Cadence**), and runnable on demand at any time.

Owner: Engineering
Status: active
Lane: framework-config-review
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
4. **One-off-incident constraints** — a rule added to prevent a specific past mistake that is now obsolete or has been generalized elsewhere. Retire or fold into the general rule.
5. **Stale cross-references** — links/pointers to files, tools, or sections that have moved or been removed. Fix or cut.
6. **Context bloat** — oversized root `AGENTS.md`/`CLAUDE.md` that wastes tokens and degrades decisions. Flag content that belongs in a per-area file, or that should simply be cut. Smaller, scoped context beats a giant root file.

## Factor-review docs are a governed pair — not orphans

Factor-review agent docs are **framework-governed**, not free-floating primitives. Per `seed-050` task 5, each factor in the operational active-lane set — `docs/workflow-config.json` `factor_review_policy.applicable_factors` — is a **canonical+wrapper pair**: the canonical source is `docs/agents/factor-<nn>-<name>.md` (flat under `docs/agents/`, with `Role: factor-<nn>-<name>` + `Category: factor` headers) and the optional rendered wrapper is the native subagent copy (e.g. `.claude/agents/factor-<nn>-<name>.md`). Both are recorded in `docs/agents/platform-mapping.md`. `docs/repo-profile.json` `factor_review` records the broader applicability *assessment* ("is this factor relevant?"); `applicable_factors` records the operational lane decision ("do we run a review lane for it?"). Only the active-lane set implies a canonical doc.

Apply these rules during the audit — they **override** the generic check 2 (orphaned primitives → relocate/retire) for factor docs:

- **Never treat a factor wrapper as an orphan to relocate or retire.** A `.claude/agents/factor-*.md` wrapper without its canonical source is not a stray primitive — it is a **half-built governed pair**. The real defect is the **missing canonical source**, not the wrapper. Name that defect.
- **Never suggest a `docs/agents/factors/` subdirectory.** The canonical home is `docs/agents/` **flat**. Relocating factor docs into a subdir breaks the renderer/validator contract.
- **On wrappers-without-sources or frontmatter-less wrappers, direct regenerate — not relocate/retire.** The fix is to **regenerate the canonical+wrapper pair via `seed-050` task 5** (or an `Upgrade wave framework` reconciliation — see `seed-160`). The docs-lint factor-surface gate (`check_factor_surface`) already flags these states as ERRORs; this review should echo the gate's recovery, not contradict it.
- **A canonical-only factor surface (no wrappers) is valid.** Wrappers are optional rendered copies; do not flag their absence.
- **A factor with no active lane and no docs is correct.** Do not recommend generating factor docs for factors that are not in `applicable_factors` (including `partial` / `not-applicable` / assessment-only factors). A **retired or narrower lane set** — an emptied or reduced `applicable_factors` even while `repo-profile.json` still assesses factors `applicable` — is a **legitimate operator choice**, not drift to "retire/relocate": do not flag it as a missing surface, and do not push to regenerate docs for retired lanes. The assessment-vs-lane gap (a factor `applicable` in `repo-profile` but absent from `applicable_factors`) is surfaced by the gate as a **non-blocking WARNING** for the operator to reconcile (add a lane, or align the assessment to `partial`) — echo that, never escalate it to an error or a forced regeneration.

When a finding touches a factor doc, its **Verdict** is `revise` (regenerate the missing/malformed half via `seed-050` task 5) — never `retire` the wrapper as if it were an orphan.

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

## Project Harness Extensions

<!-- Fill from target repository evidence during upgrade render. Never add product-specific content to this seed body. -->

## Relationship to Other Commands

| Command | When to use |
|---|---|
| **Framework config review** | Audit + prune the agent operating surface; recommended each major/minor upgrade |
| **Codebase cleanup review** | Prune **code** (dead code, duplication, complexity, debt) — the code counterpart to this agent-surface review |
| **Council review** | Adversarial + council pass on a specific artifact (a plan, change, design) |
| **Evaluate decision** | An architectural/technology decision specifically — produces an ADR |
