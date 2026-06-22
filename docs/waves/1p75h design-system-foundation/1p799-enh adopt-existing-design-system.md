# Design-system adopt-existing (external-reference) mode

Change ID: `1p799-enh adopt-existing-design-system`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-22
Wave: `1p75h design-system-foundation`

## Rationale

The design-system extraction contract (`seed-040` task 14) mandates a single fixed canonical shape rooted at `docs/design-system/`: `manifest.json`'s `canonicalRoot` **must equal `"docs/design-system"`**, the full DTCG tree (`tokens/*.json`, `components/`, `exports/`, `foundations/`) is required, and the seeded `AGENTS.md` tells agents to consume the generated `--ds-*` exports and "never hard-code."

For a target repo that **already owns a mature design system** — its own token source, a Figma source-of-truth, a Tailwind preset, or a published token package — install/upgrade therefore produces a **second, parallel, extracted mirror** at `docs/design-system/` instead of deferring to the existing system in place. There is no `external-reference` source strategy expressing "the canonical system lives elsewhere — index it, don't re-extract it."

Net risk: duplication and drift between the mirror and the real source, and agents steered to consume our parallel `--ds-*` namespace instead of the project's actual tokens. The framework is strong at **bootstrapping** a system that doesn't exist; this change makes it equally able to **defer to** one that does — without imposing our structure on projects that already made these decisions.

## Requirements

1. **`external-reference` source strategy.** Add `external-reference` to the `manifest.json` `sourceStrategy` enum. Under it, the contract records a *pointer* to the existing system rather than a full parallel token tree.
2. **Reference pointer block.** Define a required `externalReference` block in `manifest.json` when `sourceStrategy: external-reference`: `tokenSource` (path or URI to the real source of truth), `buildCommand` (optional — how the project builds its tokens), `namingConvention` / `varPrefix` (the project's real token/var convention agents must use), `consumptionDoc` (where agents read usage), `notes`. Mirror the pointer into `source-map.json`.
3. **`canonicalRoot` stays fixed (interrogation C1).** Do **not** relax the `canonicalRoot == "docs/design-system"` invariant. `canonicalRoot` means *where the contract/index lives*, and consumers (the validator, the `AGENTS.md` docs-map pointer, the semantic index) rely on it. The external source location is expressed **only** via `externalReference.tokenSource`. The thin index always stays discoverable at `docs/design-system/`; only the *pointer* names the external root.
4. **Thin reference tree (decline the full mirror).** Under `external-reference`, the full `tokens/` + `exports/` mirror is **not** required. The contract degrades to a thin index: `manifest.json` (with `externalReference`), `source-map.json` (pointers), `AGENTS.md` (consumption guidance pointing at the real source), `gaps.md`, `README.md`. Absence of `tokens/` and `exports/` must **not** be a validator error under `external-reference` — but only when a **resolvable** `externalReference` is present (see R8).
5. **Three-mode decision + concrete evidence bar (interrogation C2/C4).** Define the evidence bar that separates the modes — the routing must not rest on "a Tailwind config exists":
   - **bootstrap** — no design system found → emit the nulls skeleton (current behavior).
   - **extract-mirror** — **in-repo design *evidence*** (CSS custom properties, stylesheet tokens) but **no** maintained external system with its own source-of-truth/build → extract into `docs/design-system/` (current behavior; this is what Wavefoundry's own dashboard uses — **self-hosting guard**: in-repo `dashboard.css` must route here, never to adopt).
   - **adopt / external-reference** — a **declared source of truth with its own build**: a token package (in `package.json` / published), a Style-Dictionary/DTCG source dir + build, or Figma library links — **not** merely CSS custom properties or a stray Tailwind theme → emit the thin reference index; do **not** re-extract a mirror.
   **Default rule:** strong coherent external evidence → adopt; **ambiguous → ask the operator** (never silently adopt *or* mirror on weak evidence); none → bootstrap.
6. **Codify the mode classification as a tested helper (interrogation C3, refined at prepare).** `repo-profile.json` is **agent-authored** (seed-030) — there is no code generator to host detection (it is only *read* by `dashboard_lib` and the design-system governance validator). So instead add a deterministic, unit-tested classifier — `classify_design_system_mode(design_evidence) -> "bootstrap" | "extract-mirror" | "adopt" | "ambiguous"` — as a pure function in the design-system governance validator module (which already reads `repo-profile.json`'s `design_system.design_evidence`). The seeds instruct the agent to record the evidence in the `design_system` block and to set `design_system.mode` from this classifier; the validator can re-derive/confirm it. The routing logic is therefore code + tested, not agent-judgment.
7. **Retarget agent guidance — derived, not invented (interrogation C7).** Under reference mode the seeded `AGENTS.md` consumption guidance must be **templated from** `externalReference` (`varPrefix`, `consumptionDoc`) and point at the project's `consumptionDoc` — never prescribe a mechanism (CSS-in-JS / SCSS / ThemeProvider are all valid) and never the `--ds-*` namespace. The "never hard-code; consume tokens" rule is preserved but retargeted to their system.
8. **Validator updates (interrogation C5).** The design-system surface/governance validators must accept (a) `sourceStrategy: external-reference`, (b) absent `tokens/`/`exports/` trees under `external-reference`, and (c) the required `externalReference` block; and must **reject** `external-reference` with a missing/empty/**unresolvable** `tokenSource` (path-type: the path must exist in the repo; URI: well-formed) — so reference mode cannot silence a genuinely-missing token tree. `canonicalRoot == "docs/design-system"` stays enforced across all modes.
9. **Seed + migration semantics (interrogation C6).** `seed-040` task 14 (3-mode model + evidence bar + thin reference-tree shape + `externalReference` schema + derived `AGENTS.md` guidance + how `hybrid` composes with `external-reference` + the **extract→adopt migration**: an orphaned `tokens/` mirror moves to `.backup/<ISO-date>/`, never a silent delete); `seed-010` install (consume the profile verdict; ambiguous → ask; decline path); `seed-160` upgrade (respect an existing `external-reference` manifest; **never** convert an adopted reference back into a mirror); `seed-050` (`AGENTS.md` docs-map note for reference mode); `seed-031` detection catalog (the evidence bar from R5).
10. **Architecture doc.** `docs/architecture/design-system.md` describes the three modes, the evidence boundary, the adopt-in-place philosophy, the upgrade-stability guarantee, and the self-hosting note (Wavefoundry's own dashboard stays extract-mirror).

## Scope

**Problem statement:** The design-system contract imposes a fixed canonical location and shape, so a target repo with an existing mature design system gets a parallel extracted mirror rather than a pointer — risking duplication, drift, and agents consuming the wrong (mirrored) tokens.

**In scope:**

- `manifest.json` schema: `external-reference` strategy + `externalReference` pointer block (no `canonicalRoot` change).
- `repo-profile.json` generator: a `design_system` detection block (evidence + mode verdict) + unit tests (incl. a Wavefoundry-shaped extract-mirror fixture).
- Validator changes (surface + governance) + framework tests for the new mode + resolvable-pointer rule.
- `seed-040` / `seed-010` / `seed-160` / `seed-050` / `seed-031` updates for the evidence bar, mode selection (via the profile verdict), the thin reference tree, retargeted agent guidance, hybrid composition, migration, and upgrade stability.
- `docs/architecture/design-system.md` three-mode documentation.

**Out of scope:**

- Auto-importing/transforming an external system's tokens into our DTCG format (that is the mirror path; reference mode *points*, it does not *convert*).
- Tool-specific adapters (Style Dictionary / Figma / Tailwind) beyond the tool-agnostic pointer + build command.
- Auto-migrating an existing extract-mirror project to adopt (operator-initiated only).
- Changing Wavefoundry's own (self-hosted) design system — the dashboard stays **extract-mirror**.
- The claude.ai/design sync (separate follow-on wave).

**Depends on:** `12atj-feat` (the build-pipeline contract this extends), `1p6z6-enh` (the contract shape). Both implemented in this wave.

## Acceptance Criteria

- [x] AC-1: `manifest.json` schema + validator accept `sourceStrategy: external-reference` with a required `externalReference` pointer block (`tokenSource` + naming/var convention + optional `buildCommand`); `external-reference` with a missing/empty/unresolvable `tokenSource` is rejected (path-type must exist in repo; URI well-formed).
- [x] AC-2: `canonicalRoot` remains fixed at `"docs/design-system"` across all modes; the external source location is expressed via `externalReference.tokenSource`, **not** by relaxing `canonicalRoot`. The validator still enforces the `canonicalRoot` invariant. (Interrogation C1.)
- [x] AC-3: under `external-reference`, the contract validates as a thin index (`manifest` + `source-map` + `AGENTS.md` + `gaps` + `README`) with `tokens/` and `exports/` absent — their absence is not an error **only** when a resolvable `externalReference` is present.
- [x] AC-4: a deterministic `classify_design_system_mode(design_evidence)` helper (pure function in the design-system governance validator module) returns the mode verdict ∈ `bootstrap`/`extract-mirror`/`adopt`/`ambiguous`, covered by unit tests — including a **Wavefoundry-shaped fixture** (in-repo `dashboard.css` evidence, no external token package) that classifies as `extract-mirror`, never `adopt` (self-hosting guard, C4). The seeds record the evidence + set `design_system.mode` from this classifier (`repo-profile.json` is agent-authored, not code-generated).
- [x] AC-5: `seed-040` documents the three modes, the concrete evidence bar (declared source-of-truth + build vs in-repo CSS), the ambiguous→ask default, the thin reference tree, `hybrid` composition, and the extract→adopt migration (orphaned `tokens/` → `.backup/`, never silent delete); never overwrites/duplicates an existing system.
- [x] AC-6: `seed-010` (install) and `seed-160` (upgrade) consume the profile verdict and respect the mode; adopt is the default only on strong evidence (ambiguous prompts the operator); upgrade never converts an adopted reference into a mirror.
- [x] AC-7: seeded `AGENTS.md` guidance under reference mode is **derived from** `externalReference` (`varPrefix`, `consumptionDoc`) and points at the project's real source — not `--ds-*` and not a prescribed consumption mechanism. (Interrogation C7.)
- [x] AC-8: `docs/architecture/design-system.md` describes the three modes + evidence boundary + adopt-in-place philosophy + upgrade stability + self-hosting note.
- [x] AC-9: framework tests cover the validator changes (external-reference + thin tree accepted; missing/unresolvable pointer rejected; `canonicalRoot` invariant preserved) **and** the profile-generator detection (incl. the Wavefoundry-shaped extract-mirror fixture), bytecode-free; `docs-lint` / `wave_validate` clean.
- [x] AC-10: all framework/seed/script edits performed under the appropriate gates (`framework_edit_allowed` for validators + profile generator; `seed_edit_allowed` for seeds).

## Tasks

- [x] Open gates per edit-scope (`framework_edit_allowed` for schema/validators/profile generator; `seed_edit_allowed` for seeds) — close immediately after each scope.
- [x] Extend the `manifest.json` schema: `external-reference` strategy + `externalReference` pointer block. (No `canonicalRoot` change.)
- [x] Add a deterministic `classify_design_system_mode(design_evidence)` helper (pure function in the design-system governance validator module) + unit tests, including the Wavefoundry-shaped extract-mirror fixture; the seeds record evidence + set `design_system.mode` from it.
- [x] Update the design-system surface/governance validators: accept external-reference + thin tree; require + resolve the `externalReference` pointer; reject unresolvable/missing; keep the `canonicalRoot` invariant.
- [x] Add validator + framework tests (accept new mode + reject missing/unresolvable pointer + self-hosting routes to extract-mirror).
- [x] Edit `seed-040` (modes + evidence bar + thin tree + schema + derived `AGENTS.md` + hybrid + migration); `seed-010` (consume verdict + ambiguous→ask + decline); `seed-160` (upgrade stability); `seed-050` (docs-map note); `seed-031` (evidence catalog).
- [x] Update `docs/architecture/design-system.md` with the three-mode model + self-hosting note.
- [x] Run framework tests bytecode-free; `wave_validate` clean; close gates.

## Agent Execution Graph


| Workstream             | Owner       | Depends On             | Notes                                                                  |
| ---------------------- | ----------- | ---------------------- | ---------------------------------------------------------------------- |
| schema-and-validators  | implementer | —                      | `external-reference` + `externalReference`; resolvable-pointer rule; keep `canonicalRoot` |
| mode-classifier        | implementer | —                      | `classify_design_system_mode(evidence)` pure helper in the governance validator module + tests (incl. self-hosting fixture) |
| validator-tests        | implementer | schema-and-validators  | accept new mode + reject missing/unresolvable pointer                  |
| seed-updates           | implementer | schema-and-validators, profile-detection | 040/010/160/050/031 — evidence bar, mode selection via verdict, migration, upgrade stability |
| arch-doc               | implementer | seed-updates           | three-mode model + self-hosting note in `design-system.md`             |
| review                 | reviewer    | all above              | docs-contract + framework-code lanes; re-run delivery council          |


## Serialization Points

- The `manifest.json` schema (validator) is the contract the seeds, profile generator, and tests describe — land the schema/validator change first.
- `seed-040` task 14 is a large shared block already edited by `12atj`; coordinate edits to avoid clobbering.
- The profile-generator verdict is the input the seeds consume — its `design_system` block shape must land before the seed prose references it.

## Affected Architecture Docs

- **Update:** `docs/architecture/design-system.md` — add the three-mode model (bootstrap / extract-mirror / adopt-external-reference), the evidence boundary, the adopt-in-place philosophy, the upgrade-stability guarantee, and the self-hosting note. Crosses the framework↔target boundary (changes how the framework interacts with target repos), so an architecture-doc update is required.

## AC Priority


| AC    | Priority   | Rationale |
| ----- | ---------- | --------- |
| AC-1  | required   | The `external-reference` strategy + resolvable pointer is the core deliverable. |
| AC-2  | required   | Keeping `canonicalRoot` fixed (not relaxed) is the load-bearing design decision from interrogation — preserves consumers + discoverability. |
| AC-3  | required   | The thin tree (no parallel mirror) is the whole point — must validate without `tokens/`/`exports/`, but gated on a resolvable pointer. |
| AC-4  | required   | Detection codified + tested (incl. self-hosting guard) is what makes mode-routing verifiable rather than agent-judgment. |
| AC-5  | required   | `seed-040` is the contract every downstream install/upgrade reads; the three-mode behavior + migration must be specified there. |
| AC-6  | required   | Install selects the mode from the verdict; upgrade must never silently convert adopt→mirror (the clobber risk). |
| AC-7  | important  | Retargeted, derived agent guidance prevents agents consuming the wrong (mirrored) tokens. |
| AC-8  | important  | Architecture doc records the model + philosophy + self-hosting note for future maintainers. |
| AC-9  | required   | Validator + detection behavior change must be test-locked, bytecode-free, clean. |
| AC-10 | required   | Seed/validator/generator edits are gated framework changes. |


## Progress Log


| Date       | Update                                                                 | Evidence                          |
| ---------- | --------------------------------------------------------------------- | --------------------------------- |
| 2026-06-22 | Plan created — add an adopt-in-place / `external-reference` mode so the design-system contract defers to an existing mature design system instead of imposing a parallel mirror. Admitted into `1p75h` per operator direction. NOTE: joins `1p75h` after its `wave-council-delivery` signoff — the delivery council must be re-run to cover `1p799`, and it should be readied (it joined post prepare-council). | Operator direction; `seed-040` task 14 + `manifest.json` `canonicalRoot` analysis |
| 2026-06-22 | **Interrogated** (red-team stress-test). Folded 7 findings: C1 keep `canonicalRoot` fixed → express external source via `externalReference` only (drops the relaxation, shrinks scope); C2 concrete evidence bar (declared source-of-truth+build vs in-repo CSS) + ambiguous→ask default; C3 codify detection in the `repo-profile.json` generator (testable) not seed prose; C4 self-hosting guard + test (wavefoundry `dashboard.css` → extract-mirror, not adopt); C5 reject unresolvable `externalReference` pointers; C6 specify `hybrid` composition + extract→adopt migration (orphaned mirror → `.backup`); C7 `AGENTS.md` reference-mode guidance derived from `externalReference`, not invented. | Interrogation verdict: accept-with-revisions |
| 2026-06-22 | **Implemented.** Schema/validator (`design_system_validators.py`): `external-reference` enum, required `externalReference` block, resolvable-pointer rule (path-exists / well-formed URI), thin-tree required-path set gated on a resolvable pointer, `canonicalRoot` invariant preserved. Classifier (`design_system_governance_validators.py`): pure `classify_design_system_mode(design_evidence)` (bootstrap/extract-mirror/adopt/ambiguous) + enum extended. Seeds 030/031/040/010/160/050 updated (evidence bar, `mode` verdict, three-mode model, thin tree, derived `AGENTS.md`, hybrid, migration, upgrade-stability guard, docs-map note). Arch doc three-mode section + self-hosting note. Tests: +20 (11 classifier incl. Wavefoundry-shaped extract-mirror fixture; 9 external-reference validator). Suite 3347→3367 green bytecode-free; docs-lint ok; `aceiss|teton|solaris`=0. Gates opened/closed per scope. | `run_tests.py` (3367 OK); `.wavefoundry/bin/docs-lint` ok |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-22 | Address in `1p75h` rather than a separate wave | Operator direction — ship the design-system foundation with adopt-in-place so it doesn't impose structure on existing-system targets. | Defer to a follow-on wave (rejected — would ship the inflexible contract first). |
| 2026-06-22 | **Reference (point-at), not import (convert)** | Under `external-reference` the contract *indexes* the existing system; converting their tokens into our DTCG tree would re-introduce the exact parallel-mirror drift this change removes. | (B) Full import/transform (rejected — drift, two sources of truth). (C) Per-tool adapters (rejected — scope). |
| 2026-06-22 | **Keep `canonicalRoot` fixed; express the external source via `externalReference.tokenSource` only** (interrogation C1) | Relaxing `canonicalRoot` overloads the field (index location vs source location) and risks breaking consumers (docs-map pointer, validator, semantic index). The thin index stays discoverable at `docs/design-system/`; only the pointer moves. | Relax `canonicalRoot` to name the external root (rejected — semantic overload + consumer breakage). |
| 2026-06-22 | **Concrete evidence bar + ambiguous→ask default** (interrogation C2) | Routing on "a Tailwind config exists" is too loose; silently adopting or mirroring on weak evidence mis-routes projects. Adopt requires a declared source-of-truth with its own build. | Default-to-adopt-on-any-evidence (rejected — false positives); default-to-extract (rejected — re-imposes structure). |
| 2026-06-22 | **Codify the mode classification as a tested pure-function helper** (interrogation C3, refined at prepare) | Mode-routing must be verifiable; prose-only detection has no test gate. But `repo-profile.json` is **agent-authored** (seed-030), not code-generated — so detection lives as `classify_design_system_mode(design_evidence)`, a pure unit-tested function in the governance validator module, which the seeds consume. | Detection in seed prose only (rejected — untestable); a new code generator for `repo-profile.json` (rejected — out of scope; the profile is agent-authored by design). |


## Risks


| Risk                                                                 | Mitigation                                                                                          |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Detection mis-routes (stray `tailwind.config` read as a maintained system; or our own `dashboard.css` flipped to adopt) | Concrete evidence bar (declared source-of-truth + build, not in-repo CSS) + ambiguous→ask default + profile-generator unit tests including a Wavefoundry-shaped extract-mirror fixture. |
| `external-reference` used to silence a genuinely-missing token tree   | Validator requires a **resolvable** `externalReference.tokenSource` (path exists / URI well-formed) before allowing the thin tree. |
| Upgrade silently converts an adopted reference back into a mirror (clobber) | Explicit AC-6 guarantee + a test; `seed-160` backfill respects an existing `external-reference` manifest. |
| Relaxing structure weakens discoverability                            | `canonicalRoot` stays fixed at `docs/design-system`; the thin index stays there — only the source pointer moves. |
| New mode joined `1p75h` after its delivery review                     | Ready/interrogate (done) + re-run the `wave-council-delivery` council to cover `1p799` before close. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
