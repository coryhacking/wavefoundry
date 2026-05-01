# Journal — Implementer

Owner: Engineering
Status: active
Last verified: 2026-04-28

Actor: implementer
Schema version: 1.0
Last distilled: 2026-04-28

## Operating Identity

- Role: implementer — the agent role responsible for executing code changes per the admitted change doc on the Wavefoundry repository.
- Responsibilities include: following the change doc Requirements/Scope/AC, detecting code patterns before implementing, running framework tests and **preferring MCP `wave_validate` / `wave_garden`** for the docs gate after changes (bin launchers only without MCP), handing off diff and suggested commit message without committing.

## Salience Triggers

- **High:** Pre-edit hook blocks a framework script edit — confirm guard-override is set before retrying; do not bypass the hook itself.
- **High:** `python3 .wavefoundry/framework/scripts/run_tests.py` fails after implementation — do not signal complete until fixed.
- **Medium:** A pattern problem in `.wavefoundry/framework/scripts/` is severe enough to warrant deviation — surface with rationale and wait for operator approval before deviating.
- **Medium:** A tool or environment failure causes significant lost time — journal the failure mode so future sessions know the recovery path.
- **Low:** `__pycache__` appears in `git status` — the post-Bash hook may have failed; investigate `.claude/hooks/pycache-cleanup.py`.

## Recent Captures

- None at init. This journal was seeded at framework install with no prior wave history.

## Distillation

- **Framework edit guard pattern:** To edit protected framework files, set `framework_edit_allowed: true` in `.wavefoundry/guard-overrides.json` (gitignored). Remove the override after the implementation session ends. The guard is not a shortcut to skip — it is the authorized bypass path.
- **Run tests before handoff:** `python3 .wavefoundry/framework/scripts/run_tests.py` must pass before signaling implementation complete. Do not rely on type checking or docs-lint alone.

## Promotion Evidence

- No lessons promoted yet at init. Future promotions: reference `docs/references/project-context-memory.md` when an implementer-discovered pattern deviation becomes recurring.

## Retirement And Supersession

- No entries are retired at init.
- Retire the guard-override lesson if the pre-edit hook mechanism is replaced by a different guard in a future wave.
- Retire the run_tests lesson if the test runner command changes — update the lesson rather than letting it go stale.

## Governance

- No secrets, credentials, or PII in journals.
- Guard-override files (`.wavefoundry/guard-overrides.json`) are gitignored and must never appear in journal entries as raw content — note only that the override was set, not its contents.
- Review: distill at wave closure; promote approved pattern deviations to `docs/references/project-context-memory.md`.
- Delete retired entries after one wave cycle.

## Active Watchpoints

- **Watchpoint:** All framework scripts in `.wavefoundry/framework/scripts/` are protected by the pre-edit hook. Any edit attempt will be blocked unless `seed_edit_allowed` or `framework_edit_allowed` is set in `.wavefoundry/guard-overrides.json`. Verify the guard-override is set before attempting edits; do not bypass by editing the hook itself.
- **Watchpoint:** After any framework script edit, run `python3 .wavefoundry/framework/scripts/run_tests.py` before signaling implementation complete. Do not skip this step.
- **Watchpoint:** `__pycache__` directories are cleaned by the post-Bash hook. If a `__pycache__` appears in `git status`, the hook may have failed — check `.claude/hooks/pycache-cleanup.py`.
