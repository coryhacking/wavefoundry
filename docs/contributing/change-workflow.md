# Change Workflow

Owner: Engineering
Status: active
Last verified: 2026-04-30

## Default Change Path

All non-trivial work follows this sequence. Do not edit repository code before step 4 (Prepare wave).

1. **Plan feature** — write a consolidated change doc at `docs/plans/<change-id>.md` using `docs/plans/plan-template.md`. Generate a change ID: `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>`.
2. **Create wave** — create `docs/waves/<wave-id>/wave.md`. Generate a wave ID: `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind wave --slug <slug>`.
3. **Add change to wave** — admit the change into the wave and relocate the active change doc from `docs/plans/` into `docs/waves/<wave-id>/`.
4. **Prepare wave** — confirm readiness: validate admitted-doc placement, repair any staged-only doc, confirm all admitted changes are documented, select review lanes, record AC priority. The wave must have a clean Prepare wave pass before implementation begins.
5. **Implement wave / Implement feature** — execute the admitted changes. Coordinator manages reviewer lanes during implementation.
6. **Review wave** — all required review lanes (code, QA, architecture, etc.) must produce findings or be explicitly deferred with rationale.
7. **Close wave / Finalize feature** — mark all changes complete or deferred; distill journals; promote memory to canonical docs; clear session handoff.

## Documentation-Only Changes

Changes confined to `docs/` with no impact on framework behavior, seed prompts, or platform surfaces may skip the stage gate with an explicit operator waiver recorded in the session handoff or change doc.

## Git Commits

**Operator-owned.** Agents hand off a diff and suggested commit message for the operator to commit locally. Agents do not run `git commit` unless the operator explicitly requests it in the current session.

See `docs/contributing/build-and-verification.md` for the full Git commits policy.

## Related Docs

- `docs/prompts/index.md` — shortcut phrase catalog
- `docs/contributing/feature-wave-lifecycle-overview.md` — full lifecycle explanation
- `docs/contributing/agent-team-workflow.md` — review lane and persona routing
- `AGENTS.md` **Stage Gate (repository code)** — gate requirements
