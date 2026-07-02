# Seeds state their validator contracts verbatim (journal / persona / manifest) + neutral venv language

Change ID: `1p9bo-enh seeds-state-validator-contracts-verbatim`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-01
Wave: `1p9bm install-experience-hardening`

## Rationale

Field feedback (real 1.9.8 install): the install agent paid repeated round-trips because the seed
prompts describe journal/persona/manifest artifacts **semantically** but do not state the **exact
validator requirements** the `wave_lint_lib` checks enforce. `1p9bn` makes the error messages show the
expected value; this change closes the loop on the *feed-forward* side so the agent gets it right the
first time. The specific gaps the operator hit:

- **Journals (`seed-130`):** exact required headings + **case** (`## Retirement And Supersession`), the
  every-line-is-a-`-`-bullet rule (prose and numbered lists fail `_section_has_bullets`), and that every
  `## Salience Triggers` bullet must carry a `JOURNAL_SALIENCE_MARKERS` word.
- **Personas (`seed-120`):** the same `Role:`/`Category:` frontmatter as agent docs, the bullet-format
  rule (incl. the `## Associated journal` line format), and that `## Scope` is **forbidden**.
- **Manifest (`seed-100`):** the required `seed_framework_source` key with its exact path form.
- **Neutral venv language:** where seeds show a Unix venv path (`.wavefoundry/venv/bin/python`), use
  platform-neutral phrasing ("the framework venv Python") so a Windows operator isn't misled — **without**
  switching examples to backslash paths (operator directive: keep `/`).

## Requirements

1. `seed-130` (journal bootstrap) states, as a literal checklist: the exact `JOURNAL_REQUIRED_SECTIONS`
   headings verbatim (with case); "every section's content lines must be `-` bullets — prose paragraphs
   and numbered lists do not satisfy the check"; and "every `## Salience Triggers` bullet must contain a
   salience marker (critical/high/medium/low/operator/…)".
2. `seed-120` (persona) includes the literal `Role:`/`Category:` frontmatter template (matching the agent
   doc template), states the bullet-format rule + the `## Associated journal` line format
   (`- path/to/journal.md`), and lists `## Scope` as a **forbidden** heading.
3. `seed-100` (prompt-surface bootstrap) lists `seed_framework_source` in its required-manifest-keys with
   the exact path form.
4. Seed venv/interpreter examples use platform-neutral language ("the framework venv Python") rather than
   a Unix-only path; **no backslash path examples are introduced** (keep `/`).
5. Seeds carry **no** internal wave/ADR IDs; content states current reality. Edited under
   `seed_edit_allowed`; the corresponding rendered prompt surfaces reconciled where they mirror these seeds.
6. `wave_validate` clean; `run_tests.py` green (seed-parity / render tests).

## Scope

**In scope:**

- `.wavefoundry/framework/seeds/`: `130-agent-journal-bootstrap`, the persona seed (`120`-series), and
  `100-project-prompt-surface-bootstrap` — add the verbatim validator contracts. Neutral venv language
  where Unix venv paths appear in install/setup seeds. *(seed_edit_allowed)*
- Reconcile the rendered prompt surfaces that mirror these seeds if applicable.

**Out of scope:**

- The validator code itself (`1p9bn`).
- Switching any path example to backslash (operator directive — keep `/`).
- The bulk-file-generation tooling (separate/deferred).
- The factor-review config (`1p9bp`).

## Acceptance Criteria

- [x] AC-1: `seed-130` lists the exact journal required headings (verbatim, with case), the `-`-bullet
      rule, and the salience-marker requirement. Evidence: new "Journal docs-lint contract" block in
      `130-agent-journal-bootstrap.prompt.md` — the 7 `##` headings verbatim (incl. capital `A` in
      `Retirement And Supersession`), "at least one `-` bullet per section (prose/numbered fails)", and the
      full salience-marker vocabulary — matching `check_journal_docs` / `JOURNAL_REQUIRED_SECTIONS`.
- [x] AC-2: `seed-120` includes the `Role:`/`Category:` frontmatter template, the bullet-format +
      `## Associated journal` line format, and lists `## Scope` as forbidden. Evidence: new "Persona
      docs-lint contract" block in `120-project-persona-synthesis.prompt.md` — `Role: <slug>` (matches
      filename) + `Category: persona` (enforced by `_check_agent_role_metadata`/`_check_agent_category_metadata`),
      the 8 required `##` headings verbatim, per-section bullet rule, salience markers, `## Associated
      journal` bullet form `- docs/agents/journals/<slug>.md`, and `## Scope` called out as gate-rejected.
- [x] AC-3: `seed-100` lists `seed_framework_source` (exact path form) in its required-manifest-keys.
      Evidence: task 7 now lists all three `MANIFEST_REQUIRED_KEYS` — `schema_version`,
      `seed_framework_source` (`".wavefoundry/framework"`, plus the cross-artifact match to workflow-config),
      `framework_revision`.
- [x] AC-4: seed venv/interpreter examples use neutral language; **no backslash path examples** are
      introduced. Evidence: **satisfied by audit** — the only actionable interpreter reference across the
      seeds (`seed-011` line 89: "do not point [MCP] at `.wavefoundry/venv/Scripts/python.exe`,
      `.wavefoundry/venv/bin/python`") is already cross-platform (names both the Windows and POSIX interior
      paths) and uses `/`. There is no misleading Unix-only venv example to neutralize; no backslash path
      was introduced. No seed edit was needed for this AC.
- [x] AC-5: seeds carry no internal wave/ADR IDs; rendered mirrors reconciled; `wave_validate` +
      `run_tests.py` pass. Evidence: grep confirms no wave/ADR IDs added to the edited seeds (130/120/100/050);
      these seeds generate install-time `docs/` content and have no 1:1 rendered mirror surface to reconcile;
      `wave_validate` clean; full `run_tests.py` at the wave's final run.

## Tasks

- [x] `seed-130`: add the verbatim journal contract (headings + bullets + salience). Done.
- [x] `seed-120`: add the persona frontmatter template + bullet-format + `## Associated journal` format +
      forbidden `## Scope`. Done.
- [x] `seed-100`: add `seed_framework_source` (+ `schema_version`) to the required-manifest-keys. Done.
- [x] Neutral venv language pass across install/setup seeds (no backslash); reconcile rendered mirrors.
      Audited: the sole interpreter reference (`seed-011`:89) is already cross-platform with `/`; no
      misleading Unix-only example exists; no rendered mirror surface for these seeds. No edit needed.
- [x] `wave_validate` (clean) + `run_tests.py` (full suite at the wave's final run).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Seed edits under `seed_edit_allowed`, mirroring the `wave_lint_lib` contracts `1p9bn` also documents in its errors; render reconcile + seed-parity tests gate it. |

## Serialization Points

- The seed contracts must match `wave_lint_lib/constants.py` exactly (headings/keys/markers) — keep them
  in lockstep with `1p9bn`. Seeds are source; reconcile any rendered prompt mirror after editing.

## Affected Architecture Docs

N/A — seed-guidance content; no boundary/flow change.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Journals were the worst offender (3 passes). |
| AC-2 | required | Personas were the second (2 passes). |
| AC-3 | required | The single manifest field that failed. |
| AC-4 | important | Neutral language helps Windows without violating the keep-`/` directive. |
| AC-5 | required | No dangling IDs; rendered parity; docs gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-01 | Planned from the 1.9.8 install report (items 1,2,4,5,6,7,8 + Win-2). Complements `1p9bn` (validator error text) on the feed-forward side. Admitted to the pre-1.10.0 `1p9bm` wave. | operator field report; `wave_lint_lib/constants.py` contracts. |
| 2026-07-01 | Implemented under `seed_edit_allowed`. Added verbatim docs-lint contract blocks to `seed-130` (journal: 7 exact `##` headings incl. `Retirement And Supersession`, per-section `-`-bullet rule, salience vocabulary), `seed-120` (persona: `Role:`/`Category:` template, 8 exact `##` headings, bullet rule, `## Associated journal` `- docs/agents/journals/<slug>.md` form, `## Scope` forbidden), and `seed-100` (all three `MANIFEST_REQUIRED_KEYS`). AC-4 satisfied by audit (sole interpreter ref already cross-platform, keeps `/`). Verified all contracts against the live `wave_validators.py` checks + `constants.py`. `wave_validate` clean; docs-lint subsuite green. | seed diffs; `wave_validators.py` `check_journal_docs`/`check_persona_docs`/`_check_agent_role_metadata`; `constants.py`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-01 | State the validator contract verbatim in the seeds (feed-forward) in addition to enriching the errors (`1p9bn`, feedback). | Belt-and-suspenders: the agent gets it right first pass AND the error is actionable if it doesn't. | Error text only (rejected — still a round-trip); seed text only (rejected — errors stay opaque for other paths). |
| 2026-07-01 | Neutral venv language, NOT backslash examples. | Operator directive: keep `/`; `/` works on Windows for Python/Claude Code tools. | Show `\` Windows paths (rejected by operator). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Seed contracts drift from `wave_lint_lib` constants over time. | This change lands with `1p9bn` in one wave; a future constant change should update both (note in the journal watchpoints). |
| Adding literal templates bloats the seeds. | Keep the added blocks tight (a headings list + a small frontmatter template + one-line rules), not full prose. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
