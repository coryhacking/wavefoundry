# 012 - Install Wavefoundry, Phase 2 (Project discovery — MCP available)

**Shortcut entry:** Phase 2 begins after the operator restarts their AI agent following Phase 1 (seed-011). The Wavefoundry MCP server is now reachable; this phase uses MCP tools for validation.

**Precondition:** All `.wavefoundry/install-log.md` Phase 1 rows are `[x]`. If any are not, return to `seed-011`.

## State machine

Continue reading `.wavefoundry/install-log.md`. Phase 2 rows live under `## Phase 2 — Project discovery (MCP required)`. Each row points at a seed prompt and an expected artifact. Execute the seed, verify the artifact, mark `[x]`, and **call `wave_install_audit` after every step** — it runs docs-lint, validates checked-row artifacts, and returns the next unchecked row.

Lint-as-you-go is the install-time discipline: lint errors block advancement; missing artifacts on `[x]` rows block advancement. The agent fixes the surface and re-calls.

## Steps (mirror `.wavefoundry/install-log.md` Phase 2)

### 2.1 — Run `wave_install_audit(phase=1)`

**Action:** Call the MCP tool. The expected return is `{status: "next_step", row: "2.2 ...", seed: "seed-030", ...}`.

If the return is `{status: "checked_but_missing", ...}`, Phase 1 didn't actually produce the artifact for some row. Return to seed-011 and fix.

If the return is `{status: "lint_errors", ...}`, fix the lint errors before proceeding.

### 2.2 — Bootstrap the evidence base (seed-030)

**Action:** Read `seed-030` and execute. Outputs go to `docs/repo-profile.json` plus inventory and architecture-grounding artifacts.

**Expected artifact:** `docs/repo-profile.json` with archetype, traits, evidence sources, and `factor_review` applicability.

Call `wave_install_audit` after marking 2.2 done.

### 2.3 — Create canonical `docs/` structure (seed-040)

**Action:** Read `seed-040` and execute. Outputs include `docs/README.md`, `docs/architecture/`, `docs/contributing/`, `docs/plans/`, `docs/references/`, `docs/prompts/`, `docs/waves/`, `docs/agents/`, plus topical artifact homes.

**Expected artifact:** `docs/README.md` exists and the listed directories are present.

> **Provision the install-log-format reference (once):** if `docs/references/install-log-format.md` does not already exist, copy it from the shipped framework template `.wavefoundry/framework/install/install-log-format.md` (verbatim — do not author a thin version). It is the canonical install-log row format + the trustworthy-`[x]`-marker invariant that `seed-011` and `seed-010` reference; the upgrade flow (`seed-160`) refreshes it from the same template.

### 2.3a — Set secrets-scan confirmation threshold in `docs/scan-rules.toml`

> **Provision the findings-format reference (once):** if `docs/references/scan-findings-format.md` does not already exist, copy it from the shipped framework template `.wavefoundry/framework/docs/scan-findings-format.md` (verbatim — do not author a thin version). It documents the `docs/scan-findings.json` schema, the `pending → false-positive / suspected-secret / confirmed-secret` lifecycle, and the `[policy] false_positive_confirmations_required` contract this step sets; the upgrade flow (`seed-160`) refreshes it from the same template.

**Action:**

- Count unique committer emails in the last 24 months:
  ```bash
  git log --format="%ae" --since="2 years ago" | sort -u | wc -l
  ```
  If the command fails (no git repository, no commits, or git not installed), treat the count as **0**. If the command succeeds but returns **0** (no commits in the last 24 months), fall back to all-time history:
  ```bash
  git log --format="%ae" | sort -u | wc -l
  ```
  If the all-time fallback also returns 0 or fails, treat the count as **0**.

- Map the count to a threshold:
  | Committer count | `false_positive_confirmations_required` |
  |---|---|
  | 0–1 | 1 |
  | 2–6 | 2 |
  | 7+ | 3 |

- Check whether `docs/scan-rules.toml` already contains a `[policy]` block. If `false_positive_confirmations_required` is already set, **skip** it — never overwrite an operator-set value. If an existing `[policy]` block lacks `confirmation_valid_days`, **add** `confirmation_valid_days = 365` (with the comment from the template below); never overwrite an existing value. Log: "scan-rules threshold: already set, skipping."

- If absent, create `docs/scan-rules.toml` with this content (substituting the computed N):
  ```toml
  # wavefoundry project scan rules
  # false_positive_confirmations_required: auto-detected from git committer count (last 24 months) at install.
  # Override this value if your team size has changed, then delete this comment.
  # confirmation_valid_days: a false-positive confirmation counts only while it is this many days old (default 365; set 0 to disable expiry).
  #   Solo maintainers (single committer) may set 0 — yearly re-confirmation is a no-op when you are the only reviewer who can re-confirm.
  # Add project-specific [[rules]] entries below to extend the framework default ruleset.

  [policy]
  false_positive_confirmations_required = N
  confirmation_valid_days = 365
  ```

- Log: "scan-rules threshold: detected N committer(s) → false_positive_confirmations_required = M"

**Expected artifact:** `docs/scan-rules.toml` exists and contains a `[policy]` section with `false_positive_confirmations_required` and `confirmation_valid_days`.

### 2.3b — Full-repo secrets baseline scan (wave 1p450)

**Action:** Immediately after the policy is written (step 2.3a), run ONE full-repo secrets baseline scan so every tracked file — not just changed ones — is classified into `docs/scan-findings.json` in a single up-front triage pass:

- With the Wavefoundry MCP attached: `wave_scan_secrets(mode="full")`.
- CLI fallback: `python3 .wavefoundry/framework/scripts/run_secrets_scan.py --mode full`.

Use the **full** entrypoint (`scan_all=True`), NOT the incremental docs-lint hook path — the incremental path scans only git-changed files (`get_scan_files`), so secrets living in untouched files would otherwise stay unclassified and dribble out across later waves. Run this once at install; it is not re-run on every operation.

> Nuance (`run_secrets_scan.py` first-run full-scan): the MCP subprocess path auto-escalates to a full scan on its FIRST run (no prior `scan-state.json`), but the docs-lint hook path stays incremental. This explicit baseline is belt-and-suspenders — a guaranteed full scan that must not depend on incidental first-run state.

**Expected artifact:** `docs/scan-findings.json` contains the consolidated baseline findings (or is absent/empty when the repo is clean); each finding awaits the security-reviewer triage (seed-213).

### 2.4 — Generate per-role agent docs (seed-050)

**Action:** Read `seed-050` and execute. Generate `docs/agents/<role>.md` for each role in `enabled_agent_roles` (workflow-config.json). For applicable factors, generate `docs/agents/factor-<nn>-<name>.md`.

**Critical requirement:** Every generated role doc MUST include `Role: <role-name>` in its frontmatter. The dashboard classifies agents by this field; a doc without `Role:` is invisible. Per the lint rule introduced in wave 1p35d (1p35l), missing `Role:` fails docs-lint, which `wave_install_audit` will surface.

**The three councils are always surfaced as specialist agents, regardless of project archetype.** Canonical fresh-install location is `docs/agents/specialists/` (shown in the examples below). Established repos with a flat `docs/agents/` layout may keep their existing location — `docs-lint` accepts either, and `platform-mapping.md` records the actual paths in either case. The presence of the three role docs is load-bearing for council invocation; their location is a convention, not an enforced contract:

- `docs/agents/specialists/red-team.md` — multi-perspective adversarial challenge surface; read **seed-225** in full to incorporate its modes, stances, and operating identity (do not generate a thin generic version).
- `docs/agents/specialists/wave-council.md` — Wave Council protocol coordinator (framework-default council); read **seed-215** in full to incorporate the protocol, fixed seats, rotating-seat policy, synthesis rubric.
- `docs/agents/specialists/archetype-council.md` — Archetype Council protocol coordinator (operator-invoked, NOT default-required, but the role doc must exist so the surface is discoverable). Read **seed-236** in full to incorporate the **broader scope** (general-purpose thinking lenses applicable to plans, design docs, code, prose, decision narratives, naming, AC formulation — not text-only), the protocol shape, and the documented seat composition + swap-ins.

For richer per-role content on the other roles, consult the authoritative per-role seeds:

- `seed-214` — architecture-reviewer
- `seed-215` — wave-council (always surfaced; see above)
- `seed-216` — reality-checker
- `seed-221` — code-reviewer
- `seed-222` — software-engineer
- `seed-223` — frontend-developer
- `seed-224` — data-engineer (if applicable)
- `seed-225` — red-team (always surfaced; see above)
- `seed-236` — archetype-council (always surfaced; see above)

**Reading authoritative seeds is the difference between shipping a generic-template role doc and shipping a doc that conveys the role's actual depth.** A thin archetype-council.md that says "stance-based council for prose review" misses the framework's intent. Pull from seed-236; preserve the protocol details, the swap-in list, and the broader scope statement.

**Expected artifact:** `docs/agents/<role>.md` for each enabled role, each with `Role:` frontmatter. The three council role docs are present in the fresh-install layout under `docs/agents/specialists/`; established repos may keep a flat `docs/agents/` layout. `docs-lint` accepts either location — the presence of the three role docs is what's load-bearing, not the directory they live in.

### 2.5 — Map architecture (seed-060)

**Action:** Read `seed-060`. Generate `docs/ARCHITECTURE.md` hub plus `docs/architecture/current-state.md`, `domain-map.md`, `layering-rules.md`, `cross-cutting-concerns.md`, `data-and-control-flow.md`, `testing-architecture.md`.

**Expected artifact:** `docs/ARCHITECTURE.md` and the architecture sub-docs.

### 2.6 — Establish posture (seed-070)

**Action:** Read `seed-070`. Generate `docs/QUALITY_SCORE.md`, `docs/RELIABILITY.md`, `docs/SECURITY.md`, `docs/PERFORMANCE.md` (when applicable).

**Expected artifact:** Posture docs exist with project-specific content (not generic boilerplate).

### 2.7 — Wire docs gate (seeds 080 + 090)

**Action:** Read `seed-080` and `seed-090`. Seed-080 spec covers two hooks (pre-edit, post-edit) — wave 1p35d (1p35n) removed the previous third pycache-cleanup hook in favor of fixing docs-lint to exclude pycache. Refresh `.wavefoundry/bin/` launchers and ensure the host configs reflect the current spec.

**Expected artifact:** Two hooks wired in the host config (settings.json or equivalent); `.wavefoundry/bin/` launchers current.

### 2.8 — Generate prompt surface (seed-100)

**Action:** Read `seed-100`. Generate `docs/prompts/*.prompt.md` for every public framework prompt and `docs/prompts/prompt-surface-manifest.json`. Include the public-prompt entries for seeds 175 (interrogate-plan), 176 (evaluate-decision), 210 (distill journals) — these are easy to miss; verify they're present.

**Expected artifact:** `docs/prompts/index.md`, `docs/prompts/prompt-surface-manifest.json`, individual prompt files.

### 2.9 — Bootstrap wave artifacts (seed-110)

**Action:** Read `seed-110`. Create `docs/waves/README.md`, `docs/agents/journals/` directory, and any other wave-coordination artifacts.

**Expected artifact:** `docs/waves/README.md` exists.

### 2.10 — Synthesize project personas (seed-120)

**Action:** Read `seed-120`. Apply the **four-item persona coverage checklist** before declaring done (per wave 1p35d (1p35l)):

1. Is there a user with elevated privilege (admin, superuser, `ROLE_ADMIN`)?
2. Is there someone who installs, deploys, or operates the system?
3. Is there a user who configures or creates the structure others use?
4. Is there an API or integration consumer distinct from the end user?

Answer each explicitly. A "no, this project has no admin role" is a valid answer; silence is not. After generating personas, update `docs/agents/platform-mapping.md` to include the new persona rows (the seed-120 final step covers this).

**Expected artifact:** `docs/agents/personas/<persona>.md` for each persona that applies; `docs/agents/personas/README.md`.

### 2.11 — Bootstrap per-role journals (seed-130)

**Action:** Read `seed-130`. Generate `docs/agents/journals/<role>.md` for each role in `enabled_agent_roles`.

**Expected artifact:** A `<role>.md` file under `docs/agents/journals/` for each enabled role.

### 2.12 — Register drift expectations (seed-140)

**Action:** Read `seed-140`. Wire drift/reindex policy entries in `docs/workflow-config.json`.

**Expected artifact:** Drift entries in workflow-config.

### 2.13 — Final `wave_install_audit()` confirms complete

**Action:** Call `wave_install_audit()` with no arguments. Expected return: `{status: "complete", message: "install complete"}`.

If anything other than `complete` is returned, the install isn't done — work the named blocker and re-call.

## Operator summary (handoff)

After 2.13 returns `complete`, deliver a concise summary to the operator covering:

1. **What was seeded** — paths to canonical `docs/`, `AGENTS.md`, legacy baseline (if applicable), native agent affordances
2. **High-level workflow** — change-doc + wave flow, stage gate
3. **Commands** — shortcut phrases and lifecycle ID generation
4. **Agents and personas** — generic roles, factor agents (when applicable), generated personas
5. **Documentation and gates** — navigation, verification scripts
6. **Important configuration** — `docs/workflow-config.json`, `docs/repo-profile.json`
7. **First-time operator rules** — reading order, plans vs waves, git commits, implementation guard, closing a wave

The operator summary content was originally in seed-010 (lines 148-195) — it remains the authoritative source for the topic structure. Tailor every bullet with this project's actual paths and detection results; avoid generic filler.
