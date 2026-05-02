# Design-system bootstrap and governance

Change ID: `12arn-enh design-system-bootstrap-and-governance`
Change Status: `done`
Owner: Engineering
Status: done
Last verified: 2026-05-01
Wave: `12as1 design-system-extraction`

## Rationale

The core extraction contract (`12akr-enh`) and the pattern/surface depth layer (`12arn-enh design-system-pattern-and-surface-depth`) assume a target repo has at least some formal design system to extract from, and treat the target as a single-platform product. Real repos hit three failure modes those plans do not cover:

1. **Greenfield / no formal design system.** No Figma variables library, no token repo, no shared component library. Extraction currently has no path — it either produces an empty tree with no signal, or silently invents a full semantic system. Neither is acceptable.
2. **Multi-surface products.** Web-only evidence applied silently to iOS/Android/macOS/Windows leads to web-centric defaults (hover states, pointer interactions, CSS-shaped tokens) on surfaces where they make no sense. Evidence provenance and platform HIG cross-checks are missing.
3. **Lifecycle governance.** Deprecated components/tokens have nowhere to live in `_index.json` or `manifest.json`. HIG revisions invalidate extractions with no version tracking. Conditional product classes (email-heavy, print/PDF, offline-first, notification-heavy) have no guidance.

This change adds a bootstrap-and-governance layer on top of the core contract. It depends on `12akr-enh` for the tree and `manifest.json` schema; it is largely independent of Split B and can land in parallel once `12akr-enh` is in.

## Requirements

1. **No-design-system bootstrap path.** When inventory (`seed-030`) finds no coherent design-system source — no Figma link, no token package, no shared component library — the workflow must not silently invent a full semantic system. Instead:
   - **Substitute evidence collection.** Operator supplies: canonical marketing or product URLs, competitor/reference apps the team wants to emulate, timestamped screen captures (mobile + desktop if relevant), brand PDFs, email templates, app-store screenshots, Loom stills. Each item stored under `docs/design/images/raw/` (hash-named) or referenced by stable URL in `manifest.json.provenance` and `source-map.json`.
   - **Sparse skeleton.** Emit the same `docs/design/` directory skeleton as the core contract, but semantic files use explicit `null` / empty collections. `gaps.md` and `VALIDATION.md` carry large sections describing what is unknown.
   - **Non-normative proposals only.** Optional "starter system" suggestions (color ramps, type steps, spacing grid) may appear in `gaps.md` or an appendix markdown referenced from `VALIDATION.md`, clearly tagged `proposed-from-best-practices`. They must never be merged into `semantic.tokens.json` until a follow-up wave or explicit operator edit promotes them.
   - **Operator gate.** `docs/design/README.md` must state that visual-bootstrap outputs require human sign-off before implementation waves treat tokens as normative.
2. **`manifest.json.sourceStrategy` semantics.** The `sourceStrategy` field (reserved in `12akr-enh`) gains full semantics here:
   - `figma-extract` — primary evidence is Figma variables/styles/components.
   - `repo-evidence-only` — primary evidence is checked-in code (tokens, theme config, components).
   - `visual-bootstrap` — primary evidence is screenshots / reference URLs / decks (no-DS path).
   - `hybrid` — combination; `evidenceTypes` array lists all active sources.

   Seeded guidance must explain when each applies and how to promote `visual-bootstrap` outputs to normative status.
3. **Multi-surface adaptation.** `manifest.json.targetSurfaces` (reserved in `12akr-enh`) becomes required. Values from the enum: `web`, `ios`, `android`, `macos`, `windows`, `watchos`, `tvos`, `linux`, `other`. Discovery:
   - Infer from `docs/repo-profile.json` `ui_roots` and stack fields.
   - Inspect native project folders (`*.xcodeproj`, `android/`, `App.xaml`, `Package.swift`, etc.).
   - Accept operator-declared targets.
   - Default unknown surfaces to gaps rather than guessing.
4. **Platform HIG cross-checks.** For each `targetSurfaces` entry, `manifest.json.platformStandards[]` records:
   - `surface` (matches `targetSurfaces` entry).
   - `standard` (e.g. `apple-hig`, `material-design`, `material-design-3`, `fluent`, `wcag-2.1-aa`, `wcag-2.2-aa`).
   - `referenceVersion` (freeform string, e.g. `"2024"` or `"3.1"`). Required so extractions can be invalidated when a HIG revises.
   - `departures` (array of documented intentional HIG departures with rationale pointers into `docs/design/design-language.md` Platform/Framework Conventions).
5. **Cross-surface gap reporting.** When evidence covers only one class of client (e.g. web-only assets for a mobile ship), `gaps.md` must flag unverified cross-surface assumptions under the `governance` or surface-specific categories. The gap entry must list: surface missing evidence, assumed-from surface, HIG-driven checks required (layout density, navigation patterns, system chrome, touch vs pointer, icon metaphors, typography/linking rules).
6. **Per-surface deltas.** When tokens or components differ by surface, record them in a `platforms/` subtree under `docs/design/` with per-surface markdown + optional token overrides, and link from `manifest.json.platformStandards[].overrides` pointers. Seeded guidance must describe the split: the subtree holds narrative + overrides; the manifest entry is the machine index.
7. **Deprecation and lineage — `manifest.json`.** Optional `deprecations` field: array of `{ kind: "token" | "component" | "pattern", id: string, supersededBy?: string, sunset?: ISO-8601 date, reason: string }`. Seeded guidance describes when to populate.
8. **Deprecation and lineage — `components/_index.json`.** Each component entry may include `deprecated: true`, `supersedes: <component-id>`, `sunset: <ISO-8601 date>`. Extraction must preserve these fields when reconciling with existing repos — never strip them.
9. **Governance expectations doc.** `docs/design/DESIGN.md` (or `docs/design/README.md`, whichever is the primary owner per `12akr-enh`) must state ownership / approval expectations for token and pattern changes, or record a `governance`-category gap when unknown.
10. **Conditional product-class extensions.** When `docs/repo-profile.json` or inventory implies specific product classes, seeds instruct targeted stubs rather than inventing full contracts:
    - **Email-heavy** — `patterns/email/_index.json` with fields: `maxWidth` (pixels), `safeFonts` (array), `darkModeStrategy` (`none` | `prefers-color-scheme` | `client-detection`), `supportedClients` (array of client IDs), `imageHandling` (`inline` | `cid` | `hosted`). `README.md` documents client-specific caveats (Outlook vs Gmail vs Apple Mail).
    - **Print / PDF** — `patterns/print/_index.json` with fields: `pageSize`, `margins`, `colorMode` (`cmyk` | `rgb` | `grayscale`), `bleed`, `fontEmbedding`.
    - **Offline-first** — `patterns/offline/_index.json` with fields: `offlineIndicator` (pattern ref), `conflictResolution`, `syncStates` (array of state-pattern refs), `cacheStrategy`.
    - **Notification-heavy** — `patterns/notifications/_index.json` with fields: `channels` (`push` | `in-app` | `email` | `sms`), `priorityLevels`, `groupingRules`, `sounds`, `badgeBehavior`.

    Each stub is only required when inventory signals the product class. Otherwise the seed guidance records the category as not-applicable in `manifest.json.productClasses` (new field).
11. **Best-practice proposal appendix.** When `sourceStrategy: "visual-bootstrap"` is active, a `gaps.md` appendix (`gaps-proposals.md` or an explicit section) may list best-practice starter defaults (palette ramps, type scale, spacing rhythm) tagged `proposed-from-best-practices`. Explicitly not in `semantic.tokens.json`. Promotion to normative status requires an operator edit in a follow-up wave.
12. **Evidence confidence for bootstrap paths.** All items extracted from `visual-bootstrap` sources default to `low` confidence in `source-map.json` unless the operator marks them higher. Low-confidence items are not presented as high-trust tokens without an explicit operator acknowledgment line in `manifest.json.provenance.acknowledgments`.
13. **Validators for bootstrap and governance.** Extend `wave_lint_lib`:
    - `sourceStrategy` value is one of the enum.
    - `targetSurfaces` is non-empty when `canonicalRoot` is set.
    - When `sourceStrategy: "visual-bootstrap"`, `semantic.tokens.json` must not contain any value marked `proposed-from-best-practices` in `source-map.json`.
    - `platformStandards[].referenceVersion` present for every `targetSurfaces` entry.
    - Deprecated components carry `supersededBy` or `sunset` (at least one).
    - Unverified cross-surface assumption check: when more than one `targetSurfaces` entry exists, `gaps.md` must contain at least one entry per surface that has only inherited evidence.
    - Per-surface deltas: `platformStandards[].overrides` paths exist and parse.
14. **Discovery globs in `seed-030` for bootstrap.** Extend `seed-030` to detect signals: presence of `*.xcodeproj`, `android/`, `App.xaml`, `Package.swift`, `electron/`, `tauri.conf.*`; marketing-site evidence under `marketing/`, `landing/`, `www/`; email templates under `emails/`, `templates/*.mjml`, `templates/*.html.erb`; print-relevant under `print/`, `pdf/`, `@page`; offline signals in service worker / sync libraries; notification signals in push libraries. Discoveries feed `source-map.json` and drive which conditional extensions apply.
15. **Install + upgrade updates.** `seed-010` and `seed-160` must extend the install/upgrade backfill checklist from `12akr-enh` with:
    - `sourceStrategy` default (`repo-evidence-only` when evidence exists; `visual-bootstrap` when operator opts in; `figma-extract` when Figma link present).
    - `targetSurfaces` inference and gap-when-unknown.
    - `platformStandards[]` entries for every declared surface (with `referenceVersion` required).
    - Conditional product-class subtrees only when inventory signals the class.

## Scope

**Problem statement:** Current plans assume a target has a formal design system and ships a single surface. Greenfield teams, multi-surface products, and products with lifecycle churn (deprecations, HIG revisions, product-class-specific patterns like email) have no path — either they get an empty tree with no signal, or they get invented content with no provenance. Governance metadata (deprecation/lineage) has no slot in the contract.

**In scope:**

- No-design-system bootstrap with substitute evidence, sparse skeleton, non-normative proposals, operator gate.
- `sourceStrategy` full semantics (`figma-extract`, `repo-evidence-only`, `visual-bootstrap`, `hybrid`).
- `targetSurfaces` inference and reporting.
- `platformStandards[]` with `referenceVersion`, `departures`.
- Cross-surface gap reporting.
- Per-surface deltas via `platforms/` subtree + manifest overrides pointers.
- Deprecation/lineage on `manifest.json.deprecations` and `components/_index.json`.
- Governance ownership expectations doc.
- Conditional product-class extensions (email, print, offline, notifications) with worked shapes.
- Best-practice proposal appendix for visual-bootstrap mode.
- Evidence confidence defaults for bootstrap paths.
- Bootstrap/governance validators in `wave_lint_lib`.
- Discovery globs in `seed-030` for platform signals.
- Install/upgrade checklist extensions.

**Out of scope:**

- Core tree, schema, and install/upgrade backfill mechanics (owned by `12akr-enh`).
- Pattern/state/validation/content/foundations depth, deep a11y, assets, extended tokens, skills (owned by Split B).
- Figma MCP integration.
- Generating screenshots or capture tooling.
- Print production workflows beyond the stub contract.

**Depends on:** `12akr-enh design-system-directory-structure-extraction` must be implemented first.

**Independent of:** `12arn-enh design-system-pattern-and-surface-depth` — can land in parallel.

## Acceptance Criteria

- **AC-1** (No-DS bootstrap): seed guidance describes the substitute-evidence flow, sparse skeleton, and operator gate. `docs/design/README.md` includes the sign-off language.
- **AC-2** (`sourceStrategy` semantics): the four enum values are documented with selection criteria and promotion rules.
- **AC-3** (`targetSurfaces`): field is required in `manifest.json`; discovery path from `docs/repo-profile.json` + native folder inspection + operator input is documented; unknown surfaces land as gaps.
- **AC-4** (Platform HIG): `platformStandards[]` with `surface`, `standard`, `referenceVersion`, `departures` is required per declared surface.
- **AC-5** (Cross-surface gaps): when evidence covers only one surface but more are declared, `gaps.md` has at least one entry per missing-evidence surface.
- **AC-6** (Per-surface deltas): `platforms/` subtree + `manifest.json.platformStandards[].overrides` pointers are documented with a seed example.
- **AC-7** (Deprecation fields — manifest): `manifest.json.deprecations` schema documented; seed example shows a deprecated token.
- **AC-8** (Deprecation fields — components): `components/_index.json` entries accept `deprecated`, `supersedes`, `sunset`; extraction preserves these across runs.
- **AC-9** (Governance doc): `docs/design/DESIGN.md` or `README.md` includes ownership/approval expectations or records a gap.
- **AC-10** (Conditional extensions — email): when email evidence exists, `patterns/email/_index.json` with the fields from Requirement 10 is seeded; worked example in seed guidance.
- **AC-11** (Conditional extensions — print/offline/notifications): same pattern for each of the other three classes with their respective field shapes.
- **AC-12** (Best-practice proposals): appendix/section approach is documented; validator rejects any `proposed-from-best-practices` value reaching `semantic.tokens.json`.
- **AC-13** (Evidence confidence defaults): visual-bootstrap items default to `low`; operator acknowledgment path documented.
- **AC-14** (Validators): each check from Requirement 13 has pass/fail/missing-evidence tests under `.wavefoundry/framework/scripts/tests/`.
- **AC-15** (Discovery globs): `seed-030` globs detect the platform and product-class signals from Requirement 14; hits drive conditional extension inclusion.
- **AC-16** (Install/upgrade): `seed-010` and `seed-160` checklists extend with `sourceStrategy`, `targetSurfaces`, `platformStandards[]`, and conditional subtree creation.

## Tasks

- `seed-030` — add platform and product-class discovery globs from Requirement 14; extend `source-map.json` entries with surface and product-class hints.
- `seed-040` — document `sourceStrategy` semantics; specify `targetSurfaces`, `platformStandards[]`, and deprecation fields; describe per-surface-deltas approach; specify conditional product-class subtree shapes with worked examples.
- `seed-010` / `seed-160` — extend install/upgrade backfill checklists; specify enum defaults and conditional inclusion rules.
- `seed-050` — AGENTS contract: agents must check `sourceStrategy` and `targetSurfaces` before assuming web defaults; cross-surface gaps must be surfaced, not silently worked around.
- `seed-100` — prompt-surface notes: `sourceStrategy` selection is a one-time setup decision; `targetSurfaces` drifts with project growth and should be reviewed on upgrade.
- `seed-170` / `seed-190` — planning and closure prompts: when a change touches UI, reference `design-language.md` Platform/Framework Conventions and any relevant `platforms/` surface deltas.
- Framework scripts:
  - `.wavefoundry/framework/scripts/wave_lint_lib/` — add validator module(s) for Requirement 13 checks. Register in lint CLI. Add tests (pass/fail/missing-evidence) per validator.
  - Flip `framework_edit_allowed` and `seed_edit_allowed` guards as needed.
- Docs:
  - `docs/architecture/design-system.md` (seeded by `12akr-enh`) — extend with bootstrap paths, multi-surface, governance sections.
  - `docs/design/DESIGN.md` seed — governance expectations.

## Agent Execution Graph


| Workstream                       | Owner       | Depends On                | Notes                                                                 |
| -------------------------------- | ----------- | ------------------------- | --------------------------------------------------------------------- |
| source-strategy-semantics        | planner     | —                         | Full enum semantics, promotion rules                                  |
| no-ds-bootstrap                  | planner     | source-strategy-semantics | Substitute evidence, sparse skeleton, operator gate                   |
| multi-surface-schema             | planner     | source-strategy-semantics | `targetSurfaces`, `platformStandards[]`, `referenceVersion`           |
| cross-surface-gaps               | planner     | multi-surface-schema      | Missing-evidence gap rules                                            |
| per-surface-deltas               | planner     | multi-surface-schema      | `platforms/` subtree + manifest overrides                             |
| deprecation-lineage              | planner     | —                         | `manifest.json.deprecations` + `components/_index.json` fields        |
| governance-doc                   | planner     | deprecation-lineage       | Ownership/approval expectations                                       |
| conditional-extensions           | planner     | —                         | Email/print/offline/notifications worked shapes                       |
| best-practice-proposals          | planner     | no-ds-bootstrap           | Appendix approach, no-silent-merge rule                               |
| bootstrap-governance-validators  | implementer | all planner workstreams   | `wave_lint_lib` checks from Requirement 13                            |
| discovery-globs                  | implementer | multi-surface-schema, conditional-extensions | `seed-030` glob additions                          |
| seed-integrations                | implementer | all planner workstreams   | `seed-010/040/050/100/150/160/170/190`                                |
| tests                            | implementer | bootstrap-governance-validators | Framework tests                                                 |
| review                           | reviewer    | all above                 | docs-contract + framework-code review lanes                           |


## Serialization Points

- `seed-040` is shared with `12akr-enh` and Split B — sequence edits.
- `manifest.json` schema changes must stay compatible with `12akr-enh` reservations (fields become required here, not renamed).
- `wave_lint_lib` validator additions may collide with Split B validators; coordinate module names.

## Affected Architecture Docs

- **Updated:** `docs/architecture/design-system.md` — add bootstrap-path, multi-surface, and governance sections.
- **Updated:** `docs/ARCHITECTURE.md` cross-reference row is sufficient.

## AC Priority

(Populated at Prepare wave.)


| AC    | Priority     | Rationale                                                               |
| ----- | ------------ | ----------------------------------------------------------------------- |
| AC-1  | required     | No-DS path prevents silent invention for greenfield teams.              |
| AC-2  | required     | `sourceStrategy` drives every downstream behavior.                      |
| AC-3  | required     | `targetSurfaces` prevents web-centric defaults on native.               |
| AC-4  | required     | Platform HIG + version tracking survives HIG revisions.                 |
| AC-5  | required     | Cross-surface gaps prevent missing evidence from staying invisible.     |
| AC-6  | important    | Per-surface deltas become real once surfaces diverge.                   |
| AC-7  | important    | Token deprecation is a common real-world need.                          |
| AC-8  | important    | Component deprecation metadata preserves extraction runs.               |
| AC-9  | important    | Governance expectations keep changes auditable.                         |
| AC-10 | important    | Email is the most common conditional product class.                     |
| AC-11 | nice-to-have | Print/offline/notifications are narrower; stubs suffice.                |
| AC-12 | required     | Best-practice proposal discipline is core to extract-don't-invent.      |
| AC-13 | required     | Evidence confidence defaults prevent low-trust tokens from sneaking in. |
| AC-14 | required     | Validators are the enforcement layer.                                   |
| AC-15 | important    | Discovery globs automate surface inference.                             |
| AC-16 | required     | Install/upgrade must carry the new required fields.                     |


## Progress Log


| Date       | Update                                                                                                                                    | Evidence                      |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| 2026-05-01 | Change split off from `12akr-enh` to carry no-DS bootstrap, multi-surface, HIG reference versions, deprecation/lineage, conditional extensions | Reviewer pre-admission notes |


## Decision Log


| Date       | Decision                                                                                                         | Reason                                                                            | Alternatives                                                 |
| ---------- | ---------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| 2026-05-01 | Visual-bootstrap outputs stay non-normative until explicit operator promotion                                    | Screenshots alone are ambiguous; keeps token files trustworthy                    | Allow silent invention into semantic tokens                  |
| 2026-05-01 | `targetSurfaces` required in `manifest.json` (not optional)                                                      | Web-only defaults on native is the most common silent failure                     | Keep `targetSurfaces` optional with a warning                |
| 2026-05-01 | `platformStandards[].referenceVersion` required (freeform string, not enum)                                      | HIG revision tracking is essential; enum would rot faster than HIG vendors update | Strict enum; no version tracking                             |
| 2026-05-01 | Per-surface deltas land in `platforms/` subtree **with** `manifest.json.platformStandards[].overrides` pointers  | Subtree holds markdown/rationale; manifest entry is the machine index             | Subtree-only (hard to index) or manifest-only (hard to read) |
| 2026-05-01 | Conditional extensions required only when inventory signals the product class                                    | Keeps tree size proportional to actual product scope                              | Always require all conditional subtrees                      |
| 2026-05-01 | Email stub chosen as the worked example (Requirement 10)                                                         | Most common conditional class; most client-diversity caveats                      | Generic template; leave others fully prose                   |


## Risks


| Risk                                                              | Mitigation                                                                                |
| ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `sourceStrategy: "visual-bootstrap"` tempts silent invention       | Validator rejects `proposed-from-best-practices` in `semantic.tokens.json`                |
| Operators skip `platformStandards[]` because it feels like paperwork | Install/upgrade checklist makes it mandatory; gap-when-missing is visible in `manifest.json.validationSummary` |
| Conditional extensions balloon the tree for simple products       | Required only on inventory signal; `manifest.json.productClasses` records not-applicable explicitly |
| HIG `referenceVersion` drifts without re-extraction               | Upgrade flow flags mismatch when the operator updates the string; no auto-invalidation     |
| Per-surface deltas diverge silently between markdown and manifest | Validator check that `platformStandards[].overrides` files exist and parse                |
| Deprecated tokens get garbage-collected on next extraction        | Extraction preserves deprecated entries; validator requires `supersededBy` or `sunset`    |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
