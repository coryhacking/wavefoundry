# Change Workflow

Owner: Engineering
Status: active
Last verified: 2026-09-25

## Default Change Path

All non-trivial work follows this sequence. Do not edit repository code before step 4 (Prepare wave).

1. **Plan feature** — write a consolidated change doc at `docs/plans/<change-id>.md` using `docs/plans/plan-template.md`. Generate a change ID with the MCP `wave_new_<kind>` tool (it dedupes against on-disk IDs); CLI fallback when MCP is unavailable: `wf lifecycle-id --kind <kind> --slug <slug>`.
2. **Create wave** — create `docs/waves/<wave-id>/wave.md`. Generate a wave ID with the MCP `wf_create_wave` tool; CLI fallback when MCP is unavailable: `wf lifecycle-id --kind wave --slug <slug>`.
3. **Add change to wave** — admit the change into the wave and relocate the active change doc from `docs/plans/` into `docs/waves/<wave-id>/`.
4. **Prepare wave** — confirm readiness: validate admitted-doc placement, repair any staged-only doc, confirm all admitted changes are documented, select review lanes, record AC priority. The wave must have a clean Prepare wave pass before implementation begins.
5. **Implement wave / Implement feature** — execute admitted changes and focused computational verification; use an exceptional named checkpoint only at a high-risk boundary.
6. **Review wave** — after implementation evidence is complete, all required inferential lanes (code, QA, architecture, etc.) must produce findings or be explicitly deferred with rationale; blocking findings return to implementation.
7. **Close wave / Finalize feature** — mark all changes complete or deferred; validate memory candidates; promote memory to canonical docs; clear session handoff.

## Writing Acceptance Criteria

An acceptance criterion asserts an outcome **the change controls** and that a
reviewer can verify from **the change's own evidence**. Repository-wide or
environment state — the whole test suite being green, machine load, another
wave's artifacts, the state of files the change never touches — is a **close-gate**
concern and must not be written as an acceptance criterion.

The reason is locality. A criterion asserting whole-repository state measures the
tree at a moment in time, so whether it can be marked depends on timing and on
work owned by other people. Wave `1wpif` demonstrated both failure modes at once:
three sibling change documents carried the same clause shape in three different
wordings, one was marked complete because the suite happened to be green when
that lane finished, and two could not be marked at all because a *concurrent*
wave's uncommitted document tripped a repository-wide test while `1wpif`'s own
suites were green. It also
creates a standing temptation at close time to reword the criterion until it
passes, which is the gate-shaping the house rules forbid.

Do not write `- [ ] AC-6: ... and the full framework test suite passes.` Write
instead: *the change's own suites and every test it adds pass; the documents this
change authors or edits validate; and no failure elsewhere is attributable to this
change.* Note "the documents this change authors or edits", not "documentation
validation passes": a full validation pass scans every document in the repository
and can be red because somebody else's in-flight document is malformed, which is
the same non-local failure in a new costume.

Two mechanisms back this up. `docs-lint` flags an acceptance criterion that
asserts repository-wide state — an advisory sensor (a `WARNING:` line that never
fails validation; wave `1wuju` registered it advisory in the docs-lint sensor
polarity registry, and wave `1yzj9` recorded the decision to keep it advisory),
reading each AC bullet whole
including its wrapped continuation lines and any loose-list continuation
paragraph. It is scoped by wave `Status`, so it reaches only change documents in
a wave that is `ready`, `active`, or `implementing`, or that carries an explicit
`Activated at:` line; closed records and parked `docs/plans/` drafts are never
retroactively failed. The rule is deliberately asymmetric: it recognises a finite
list of repository-scope words between the quantifier and the noun, so an
unlisted repository-wide adjective (`untouched`, `prior`, `upstream`) passes
silently and is left to review, while a compliant change-local criterion is never
blocked; for a heuristic sensor the silent miss is the cheaper failure. Note that
the incremental `--changed` lint the post-edit hook runs reaches the wave-owned
AC validators only when `wave.md` itself is in the changed set, so a change-doc-only
edit gets its sensor signal from the full validation that Prepare, Review, and
Close run, not from the hook.

**A carrier enters scope the moment its wave is readied or activated.** That is
deliberate — the wave that owns a criterion rewrites it — but it means reopening
an older wave can surface a lint warning on a document that was valid when
it was authored. The fix is the one-line rewrite the diagnostic supplies, applied
by the wave that owns the document. As of wave `1wuju` (re-derived by running the
sensor over every change document in a non-closed wave, regardless of readiness,
and over every parked plan), eight such criteria exist in this repository across
four non-closed waves, plus five in parked plans. And `wf_close_wave`
verifies the framework test receipt, so the whole-suite requirement stays
machine-visible as it leaves the acceptance criteria; see **Close gate** in
`build-and-verification.md` and the `wf_close_wave` entry in
`docs/specs/mcp-tool-surface.md`. That gate has two scope halves: its hash covers
`.wavefoundry/framework/` only, so a documentation edit never makes a standing
receipt stale, but the receipt is written only on a whole-suite pass, so a
docs-triggered failure prevents a new one. A green receipt attests the framework
code, not the tree.

Canonical source: `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`,
*"Acceptance criteria assert what the change controls"*.

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
