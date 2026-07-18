# 1p8t4-adr — Keep the stage gate canonically structured; add an anti-drift guard; decline consolidation and anchors

Owner: Engineering
Status: accepted
Last verified: 2026-07-17

## Context

`seed-050` prescribes the agent-entry stage gate as two named sections — `## Stage Gate (repository code)` (task 17) and `## Implementation guard (product code)` (task 19). The upgrade seeds (`150`/`160`) instruct installed repos to "preserve useful repo-grown behavior" and reconcile in place. These pull opposite ways: a repo that consolidates the two gates into one section/table follows the upgrade instruction yet diverges from the prescribed headings.

A consumer (**teton**) surfaced a proposal to (1) validate the gate by documented per-surface preconditions rather than heading strings, (2) bless a consolidated-table form as an alternative template, and (3) add a reconciliation line preserving a consolidated section on upgrade. A second consumer (**javaagent**, a two-section install) countered that the headings are a **cross-document anchor/API** referenced by literal name (13 files in teton, 23 in javaagent — host entry docs + lifecycle prompts), so blessing free consolidation turns those into soft-resolving (eventually dangling) references; it proposed an HTML-comment anchor convention instead.

Verified against the framework:

- **No validator enforces the gate headings** (or any root `AGENTS.md` content) today — `wave_lint_lib` has zero gate checks and `AGENTS.md` is not even a required file. The contradiction is **latent** (no failure today); the only required-section checks target wave/change/journal/persona docs.
- The `wave:` markers cited as anchor precedent are **all begin/end RENDER-REGION delimiters** for renderer-injected generated content (`auto-guru`, `root-bridge`, `repo-index-modules`) — **not** cross-document addressing anchors; nothing resolves to one by id. "Anchors already exist here" is not accurate for addressing.
- **Grounding:** wavefoundry is the framework's heaviest user (99 waves, 530 changes) and uses the prescribed two-section form with **zero** consolidation and resolving references — the canonical form is frictionless at scale. **Load-bearing caveat:** that is the *authors* not drifting from their own design, so our corpus cannot measure *consumer* drift. teton — a low-experience consumer (few waves) — drifted to consolidation **early and unprompted**, which is the relevant signal for the typical user base and proves the contradiction is **active** (it already misled a consumer), not merely latent.

## Decision

1. **The stage gate stays canonically structured.** The two named sections are a **fixed cross-document contract**, referenced by name across host entry docs and lifecycle prompts. They are the canonical render target for new installs and the form maintained on upgrade.
2. **Decline the proposal's structural halves.** Do **not** bless a consolidated-table alternative template; do **not** add an anchor/marker convention or a validate-by-policy semantic check. The marker convention is render-region-only, and adding an addressing convention for a latent problem would establish a new standard to accommodate one consumer's divergence.
3. **Add a small anti-drift guard-rail** (implemented as seed wording, riding the next seed-touching wave behind `seed_edit_allowed`): `seed-050` tasks 17/19 + the `seed-160` reconciliation step state that the gate is **exempt from the "preserve repo-grown / consolidate in place" license** — the two named sections are a fixed contract, do not consolidate them — with a one-line *why* ("they are referenced by name across host docs and lifecycle prompts, so the names must stay resolvable").
4. **Record a standing decision:** never add a validator that asserts the literal gate heading strings. The gate is policy agents read; a brittle heading-string check is the foot-gun this decision forecloses.

## Consequences

- **wavefoundry:** no change — already canonical.
- **Consumers:** the prescribed two-section form is a rule, not merely a default. **teton** should re-align (split its consolidated table back into the two named sections) — backed now by an explicit framework rule; its by-name references resolve again and the recurring upgrade judgment call disappears. Its "wave-admitted surfaces" need is handled as a local waiver within the canonical structure or raised as a separate, independently-evaluated enhancement. **javaagent:** no change — already canonical; it is the model.
- The guard-rail prevents the next teton by closing the license-gap that invited the drift.
- Doc/seed-wording only; no lifecycle behavior change. This ADR is **accepted**; the seed guard-rail is the linked, pending implementation.

## Alternatives considered

- **Bless consolidation** (the reconciliation line / a second template). Rejected — it resolves the contradiction in the direction that **worsens** drift (legitimizing the form a naive consumer already drifted to), doubles the maintenance surface, and (per teton's own 13 references) accumulates soft-dangling references.
- **Anchor / marker convention** (javaagent's counter). Rejected — the cited precedent is render-regions, not addressing; adopting addressing-anchors establishes a new standard for a latent problem, and the gate is hand-authored policy that does not fit the render-region model. Reconsider only if a concrete machine-consumer of the gate ever appears.
- **Validate-by-policy** (a semantic precondition check). Rejected — not implementable without NLP; it collapses to a structural-anchor check, and there is no gate validator today and none proposed. The cheaper, equivalent defense is the standing decision in Decision 4.
- **Adopt consolidation as the new canonical form.** Rejected at N=1 — teton drifted, javaagent did not, and our authoring use shows two sections is frictionless. **Revisit only if drift recurs across multiple consumers** — that would signal consolidation is the true natural form and worth a deliberate re-canonicalization (with the cross-doc-API migration done properly).
- **Do nothing.** Rejected — the drift proves the contradiction is active (it misled a consumer), and the guard-rail is cheap.

## Methodology note (reusable)

Evaluate framework-change proposals against wavefoundry's **own heaviest-usage corpus first** — but **weight consumer-drift signals heavily**, because the authors do not drift from their own design (our zero-drift cannot see what a naive consumer does). A single early drift at a low-experience repo is a leading indicator worth a cheap preventive fix; pervasive drift across consumers is the signal to reconsider the design itself.

## References

- Change (the seed guard-rail implementation, admitted into wave `1p8t7`, pending implementation under `seed_edit_allowed`): `docs/waves/1p8t7 stage-gate-anti-drift-guard/1p8t5-enh stage-gate-anti-drift-guard.md`.
- Related: `1p5be-adr retire-canonical-names-rename-manifest` — the canonical-naming policy family.
- Origin: consumer proposals from teton (consolidation + anchors) and javaagent (anchor counter), evaluated 2026-06-29 against the framework's own corpus and the teton drift signal.
- Separate, deferred: a standalone evaluation of whether the gate taxonomy needs a third "wave-admitted surfaces" dimension (do not couple it to this decision).
