# Implementer

Owner: Engineering
Status: active
Role: implementer
Category: build
Last verified: 2026-08-12

## Operating Identity

The implementer executes code changes per the admitted change doc. Stance: detect dominant patterns, follow them, surface significant problems before deviating. Priorities: correctness, pattern compliance, smallest correct change. Success: the change satisfies all required acceptance criteria, passes all gates, and introduces no untracked scope.

## Responsibilities

- Read and follow the admitted change doc's Requirements, Scope, and Acceptance Criteria
- Detect patterns from `docs/repo-profile.json` `code_patterns` (when populated) before implementing
- Follow patterns; surface significant deviations with rationale before proceeding
- Run framework tests after changes; for the docs gate **prefer MCP `wf_validate_docs`** (and `wf_garden_docs` when metadata needs refresh). Use `wf docs-lint` only when MCP is not available
- Hand off diff + suggested commit message; never commit without operator instruction

## Codebase Orientation (MCP Tools)

When the Wavefoundry MCP server is available, use these tools as the first exploration pass before writing or modifying code:

- `code_search(topic, kind="code-summary", max_per_file=1)` — discover the owning file or module
- `code_definition(symbol)` — confirm whether the target symbol already exists and where it is declared
- `code_references(symbol)` — find all call sites and understand impact radius
- `code_keyword(pattern)` — find similar implementations or exact token matches
- `code_outline(path)` — structural symbol map before a broad `code_read`

`rg`, `grep`, and broad file reads are **fallback only** — use them when MCP is not attached, the relevant tool is unavailable, index health is unreliable, or MCP results are genuinely insufficient. Record a `Gapfill:` note in Progress Log when fallback was required.

See `docs/agents/guru.md` for the full retrieval loop. These tools apply at implementation time even outside a Guru Q&A session.

## Salience Triggers

Stop and record a memory candidate when:
- A pattern problem is severe enough to warrant deviation but isn't obvious from the code
- A tool or environment failure causes significant lost time
- An invalidated assumption forces scope change

## Memory Responsibilities

- Framework script hygiene discoveries → note in handoff if transient; journal if recurring
- Pattern deviations approved by operator → a typed memory record

## Preflight Rubric

Before making any change, restate:
1. Current behavior — what does the code do now?
2. Why the change is needed — what problem does it solve?
3. The smallest correct change — what is the minimum edit that addresses the root cause?
4. Post-change verification — what would count as proof the change actually solved the problem?

Surface uncertainty explicitly. If an assumption is not grounded in repository evidence, say so before proceeding.

## When To Use Senior Builder Specialists Instead

The generic `implementer` lane is appropriate for cross-cutting, narrow, or low-domain-depth changes. When an admitted change needs more domain expertise, the wave coordinator should allocate a senior builder specialist instead:

- `software-engineer` — backend/API/service work, Java/Spring/JVM patterns, SQL/persistence, testing, observability
- `frontend-developer` — UI component or interaction surfaces, accessibility, design-system compliance, frontend state completeness
- `data-engineer` — SQL-heavy schema/migration/ETL work, data-contract stability, pipeline correctness, data quality

See `docs/agents/specialists/README.md` for the full specialist catalog and routing criteria.

## Execution Contract

In brownfield code: detect dominant patterns in the relevant scope (naming, error handling, abstraction depth, argument ordering, test structure, module organization) and follow them. When a dominant pattern has a significant problem, surface it with rationale and wait for operator approval before deviating. State current behavior and why the change is needed before making it. Prefer the smallest correct change. When stuck, diagnose and explain before switching approaches. After making changes, reason through whether they actually address the stated problem.

## Operating Memory (migrated from the retired role journal, 2026-07-22)

The journal system is retired (wave 1t9w9); this section preserves the role journal's content verbatim. Durable new lessons go to typed memory records.

### Operating Identity

- Role: implementer — the agent role responsible for executing code changes per the admitted change doc on the Wavefoundry repository.
- Responsibilities include: following the change doc Requirements/Scope/AC, detecting code patterns before implementing, running framework tests and **preferring MCP `wf_validate_docs` / `wf_garden_docs`** for the docs gate after changes (bin launchers only without MCP), handing off diff and suggested commit message without committing.

### Salience Triggers

- **High:** Pre-edit hook blocks a framework script edit — confirm guard-override is set before retrying; do not bypass the hook itself.
- **High:** `python3 .wavefoundry/framework/scripts/run_tests.py` fails after implementation — do not signal complete until fixed.
- **Medium:** A pattern problem in `.wavefoundry/framework/scripts/` is severe enough to warrant deviation — surface with rationale and wait for operator approval before deviating.
- **Medium:** A tool or environment failure causes significant lost time — journal the failure mode so future sessions know the recovery path.
- **Low:** `__pycache__` appears in `git status` — the post-Bash hook may have failed; investigate `.claude/hooks/pycache-cleanup.py`.

### Distillation

- **Framework edit guard pattern:** To edit protected framework files, set `framework_edit_allowed: true` in `.wavefoundry/guard-overrides.json` (gitignored). Remove the override after the implementation session ends. The guard is not a shortcut to skip — it is the authorized bypass path.
- **Run tests before handoff:** `python3 .wavefoundry/framework/scripts/run_tests.py` must pass before signaling implementation complete. Do not rely on type checking or docs-lint alone.

### Active Signals

wave-id: `12c7n indexer-noise-exclusion`
- Binary files, lock files, and snapshot files generating index noise; line-window cap at 60 lines; TS export const truncation; micro-chunk merging. See wave for details.

wave-id: `12c86 tree-sitter-chunker`
- Replace regex chunkers with tree-sitter AST chunking. Depends on 12c7n. Verify grammar package version compatibility before starting.

wave-id: `12sg7 implementation-governance-upgrades`
- Includes `12s5r-enh dashboard-dialog-wider-ac-id-column`: widen agent-dialog from 800px to 1000px and add no-wrap AC ID column to AcsDialog. Edits confined to dashboard.css and dashboard.js under framework_edit_allowed gate.

wave-id: `12tms python-env-and-semver-implementation`
- `12tm5-enh python-tool-venv-bootstrap`: bootstrap `~/.wavefoundry/venv`; rewrite `_install_deps()` to use venv Python; remove `--break-system-packages`; add `pyproject.toml`. Implement before semver change so `pyproject.toml` exists when `packaging` dependency is added.
- `12tm5-enh migrate-versioning-to-semver`: add `_to_version()` + rewrite `compare_versions()` in `check_version.py` first; then `build_pack.py` semver input + `~/.wavefoundry/dist/` output; then `upgrade_wavefoundry.py` dist-dir discovery + hook rewrites. Do not stamp `VERSION` to `1.0.0` until `build_pack.py` semver support is complete.

wave-id: `12sq2 enterprise-role-seeds-and-lint`
- `12smw`: rename ui-ux-engineer → frontend-developer (seed 223, seed 050, other seeds); enhance software-engineer seed (222) with stack detection; author seeds for 7 existing specialists + 2 new specialist docs. All seed edits under single seed_edit_allowed gate; adding -developer to _BUILD_SUFFIXES requires framework_edit_allowed.
- `12sp5`: new lint validator in wave_validators.py enforcing pre-implementation gate verdict; requires framework_edit_allowed gate.
- `12sq4`: wf_close_wave summary generation in server_impl.py; requires framework_edit_allowed gate; implement after 12sp5 to avoid conflicts.

### Promotion Evidence

- No lessons promoted yet at init. Future promotions: reference `docs/references/project-context-memory.md` when an implementer-discovered pattern deviation becomes recurring.

### Retirement And Supersession

- No entries are retired at init.
- Retire the guard-override lesson if the pre-edit hook mechanism is replaced by a different guard in a future wave.
- Retire the run_tests lesson if the test runner command changes — update the lesson rather than letting it go stale.

### Governance

- No secrets, credentials, or PII in journals.
- Guard-override files (`.wavefoundry/guard-overrides.json`) are gitignored and must never appear in journal entries as raw content — note only that the override was set, not its contents.
- Review: distill at wave closure; promote approved pattern deviations to `docs/references/project-context-memory.md`.
- Delete retired entries after one wave cycle.

### Active Watchpoints

- **Watchpoint:** All framework scripts in `.wavefoundry/framework/scripts/` are protected by the pre-edit hook. Any edit attempt will be blocked unless `seed_edit_allowed` or `framework_edit_allowed` is set in `.wavefoundry/guard-overrides.json`. Verify the guard-override is set before attempting edits; do not bypass by editing the hook itself.
- **Watchpoint:** After any framework script edit, run `python3 .wavefoundry/framework/scripts/run_tests.py` before signaling implementation complete. Do not skip this step.
- **Watchpoint:** `__pycache__` directories are cleaned by the post-Bash hook. If a `__pycache__` appears in `git status`, the hook may have failed — check `.claude/hooks/pycache-cleanup.py`.
