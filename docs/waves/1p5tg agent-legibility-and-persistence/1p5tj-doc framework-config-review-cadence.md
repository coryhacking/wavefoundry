# Framework-config review prompt + cadence policy

Change ID: `1p5tj-doc framework-config-review-cadence`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-16
Last verified: 2026-06-16
Wave: `1p5tg agent-legibility-and-persistence`

## Rationale

The large-codebase best-practices guidance warns that agent configuration — `CLAUDE.md`/`AGENTS.md`, seeds, prompts, and standing constraints — accretes over time, and recommends a periodic review to **retire stale constraints** rather than letting them pile up. This framework has hit exactly that: council review repeatedly flags over-accretion (duplicate-of-default config blocks, orphaned primitives, constraints tied to a superseded model era or a one-off incident). There is no standing, structured prompt to audit and prune the agent operating surface, so cruft is removed only opportunistically.

This change delivers the **review itself**: a generic, seed-rooted review prompt (a removal-biased audit producing keep/revise/retire findings) plus the **cadence policy** — that it is evaluated on every major/minor upgrade, who should run it, and that it's human-initiated. The recommendation that surfaces it at upgrade is a separate, deliberately stateless line (`1p5tk`); this change owns the human-facing prompt and the policy it implements. Everything ships in framework seeds so every downstream project inherits the same review on upgrade — nothing project-specific.

## Requirements

1. **Generic + seed-rooted.** The review prompt lives in the framework seeds and is registered in the public prompt catalog/manifest, so it renders into every project on upgrade. No wavefoundry-repo-specific content; the prompt audits *whatever project it runs in*.
2. **Removal-biased audit.** The prompt walks the agent-config inventory — seeds, `AGENTS.md`/`CLAUDE.md` (root **and** per-folder), rendered prompts, standing guardrails/constraints, the memory index — with concrete checks and a bias toward *retirement*: duplicate-of-default config, orphaned/undiscoverable primitives, constraints scoped to a superseded model era, one-off-incident constraints now obsolete/generalized, stale cross-references, and **context bloat** (oversized root `AGENTS.md`/`CLAUDE.md` that wastes tokens and degrades decisions — flag content that belongs in a per-area file or should be cut).
3. **Doc-sync verification.** The prompt includes a step to verify that planning / spec / architecture docs (and per-area `AGENTS.md`) are still **in sync with the code** — surfacing drifted sections as findings — rather than assuming docs auto-update (practitioner consensus: self-updating docs are unreliable; verifying sync is the reliable move).
4. **Structured, recommend-only output.** The prompt yields keep / revise / **retire** findings (each with rationale), suitable to feed a follow-up wave. It recommends; it never auto-deletes.
5. **Cadence policy — evaluated each major/minor upgrade.** Documented policy: the review is recommended for evaluation on **every** major/minor upgrade install (the recommendation line is implemented in `1p5tk`); the owner decides each time whether to run it. No time thresholds, wave-count, or state — "evaluate it at each major/minor upgrade" is the cadence.
6. **Role + initiation policy.** In a multi-user repository the review is **recommended to a senior / principal architect or engineer** (judgment-heavy, authority-bearing), and **initiated by that person** — never executed automatically. The policy states this explicitly; in a single-user context it still applies to the maintainer.
7. **Discoverable, not orphaned.** Cross-referenced from the release/upgrade and contributing surfaces and woven into related seeds (seed-first), so it's found at its natural trigger points.

## Scope

**Problem statement:** Agent config accretes and stale constraints persist because there's no standing, structured, removal-biased review — and no policy for when it runs and who runs it.

**In scope:**

- The review prompt (seed) + registration in the prompt catalog/manifest.
- The removal-biased audit checklist + structured keep/revise/retire output format.
- The cadence policy text: evaluated each major/minor upgrade, senior/principal role, human-initiated.
- Cross-references from release/upgrade + contributing surfaces; seed-first rendering.

**Out of scope:**

- The upgrade recommendation line itself — that is `1p5tk` (this change defines the policy it points at); no shared state between them.
- Actually performing a config audit or deleting any current seeds/constraints — this ships the process; running it is a separate activity.
- Programmatic enforcement of *who* runs it (role is a recommendation/convention, no identity/ACL).
- Automated/programmatic staleness detection (a linter) — this is a guided review.

## Acceptance Criteria

- [x] AC-1: A framework-config review prompt exists in the seeds (`238-framework-config-review.prompt.md`) and is registered in the public catalog (`docs/prompts/framework-config-review.prompt.md` + `index.md` row, mirroring the council-review pattern); lints clean; content is project-agnostic.
- [x] AC-2: The prompt enumerates the removal-biased audit checks (duplicate-of-default, orphaned primitives, superseded-model-era, one-off-incident, stale cross-refs, **context bloat** in root `AGENTS.md`/`CLAUDE.md` root + per-folder) and yields structured keep/revise/retire findings.
- [x] AC-2b: The prompt includes a doc-sync verification step that surfaces planning/spec/architecture/per-area-`AGENTS.md` sections drifted from the code as findings (not auto-updating them).
- [x] AC-3: The cadence policy is documented — evaluated on every major/minor upgrade, recommended to a senior/principal architect/engineer, human-initiated, no state.
- [x] AC-4: The prompt is cross-referenced from the upgrade surface (`upgrade-wavefoundry.prompt.md` + the `1p5tk` upgrade recommendation line) and the council-review seed/public doc (Relationship tables); index.md Public Commands row added; **full suite 3160 OK**; docs-lint clean.

## Tasks

- [x] Author the review prompt seed (inventory + removal-biased checklist + keep/revise/retire output).
- [x] Register it in the prompt catalog/manifest (`docs/prompts/index.md` + `prompt-surface-manifest.json`), seed-first.
- [x] Write the cadence policy (evaluated each major/minor upgrade, senior/principal role, human-initiated).
- [x] Add cross-references (release/upgrade prompts, contributing docs); render to per-project docs; weave pointers; full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| prompt     | Engineering | —          | review prompt seed + checklist + output format |
| policy     | Engineering | —          | cadence policy (evaluated each major/minor upgrade) |
| register   | Engineering | prompt     | catalog/manifest registration + cross-references |


## Serialization Points

- None with `1p5tk` — it points at this prompt by reference only (no shared state). Settle this prompt's name/location so `1p5tk`'s cross-link is stable.

## Affected Architecture Docs

`N/A` — adds an agent-operations prompt + process/policy doc; no runtime architecture, boundary, or flow change.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The review prompt is the deliverable. |
| AC-2 | required | The removal-biased checklist + structured output make the review actionable. |
| AC-2b | required | Doc-sync verification is the reliable alternative to unreliable auto-updating docs. |
| AC-3 | required | The cadence/role/initiation policy is what `1p5tk` points at and what keeps control with a senior owner. |
| AC-4 | required | Seed-first parity + discoverability prevent the prompt from being an orphan. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-15 | Deliver a guided review prompt + policy, not an automated linter | Config staleness is judgment-heavy (era/intent context a linter can't see); a removal-biased prompt is the right tool, and ship the process before automating | Automated staleness linter (deferred — high false-positive risk, can't judge intent); do nothing (rejected — over-accretion is recurring + unowned) |
| 2026-06-15 | Recommend to a senior/principal, human-initiated | The review retires standing constraints — authority-bearing; must stay with an experienced owner, not auto-run or run by anyone | Auto-run at upgrade (rejected — judgment + authority needed); no role guidance (rejected — in multi-user repos it needs a clear owner) |
| 2026-06-15 | Prompt recommends keep/revise/retire; never auto-deletes | Config removal must land through a normal reviewed wave | Auto-prune (rejected — destructive, no review gate) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Review prompt itself becomes orphaned cruft (ironic) | Cross-referenced from release/upgrade + contributing; registered in the catalog; surfaced by `1p5tk` at upgrade |
| Policy documented but never followed | Surfaced on every major/minor upgrade via `1p5tk`, not a standalone timer; the senior/principal role gives it an owner |
| Over-aggressive retirement removes a load-bearing constraint | Recommend-only output; senior/principal owner; changes land through a reviewed wave |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
