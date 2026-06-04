# Persona — Framework Operator

Owner: Engineering
Status: active
Role: framework-operator
Category: persona
Last verified: 2026-06-04

## Who

- A developer or engineering lead who installs, upgrades, and operates the Wave Framework in their own target repository
- Not a Wavefoundry maintainer — consumes the framework distribution as a dependency
- Interacts with Wavefoundry through the zip distribution, **Init wave framework** / **Upgrade wave framework** commands, and the rendered local surface in their repository

## Goals

- Get a working Wave Framework operating surface installed in their repository with minimal friction
- Understand what was installed, what the lifecycle looks like, and how to operate day-to-day
- Upgrade safely when a new framework version ships, without losing their project-specific customizations
- Know which files they can customize and which will be overwritten by upgrade
- Generate correct lifecycle IDs without understanding internal epoch math

## Workflows

**Installation:**
1. Obtain a Wavefoundry release zip
2. Use `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` for framework distributions
3. Leave semver packs in the repository root, `~/.wavefoundry/`, or `~/.wavefoundry/dist/`; run **Upgrade wave framework**
4. Review the operator summary: what was installed, how the lifecycle works, where config lives
5. Commit the self-hosted surface (operator-owned commit)

**Daily operation:**
- Verify the docs gate: prefer MCP **`wave_validate`** (and **`wave_garden`** when metadata needs refresh); use **`.wavefoundry/bin/docs-lint`** only without MCP
- Use shortcut phrases from `AGENTS.md` for planning, wave management, and closure
- Generate IDs: `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind wave --slug <slug>`

**Upgrade:**
1. Build or obtain a new semver release zip in the repository root, `~/.wavefoundry/`, or `~/.wavefoundry/dist/`
2. Run **Upgrade wave framework**
3. Review the diff of changed files; commit after verification

**Sequencing install/upgrade surface changes:**
- Coordinate with the docs-contract-reviewer when install/upgrade prompt docs change
- Sequence install and upgrade surface changes before MCP tool changes that operators would need to use them
- Flag admission of changes that reduce operator summary information density — these need explicit mitigation

## Failure modes

- Docs-lint fails after an upgrade: manifest `framework_revision` doesn't match new `.wavefoundry/framework/VERSION`
- Lifecycle IDs look wrong: epoch was re-anchored incorrectly during upgrade
- Customizations overwritten: project-specific prompt doc changes lost during upgrade
- Zip not found: wrong filename, wrong directory, or no matching semver pack was available in the repository root, `~/.wavefoundry/`, or `~/.wavefoundry/dist/`
- A proposed change would silently overwrite operator customizations without a warning: escalate to architecture-reviewer and wave-coordinator before admission
- An upgrade changes the epoch value, invalidating existing wave IDs: escalate to wave-coordinator immediately

## Invocation signals

- Any change to `docs/prompts/install-wavefoundry.prompt.md` or `docs/prompts/upgrade-wavefoundry.prompt.md`
- Any change to seed-010 or seed-020 that affects the operator summary or installed file set
- Any change to `.wavefoundry/framework/VERSION` or `docs/prompts/prompt-surface-manifest.json` `framework_revision`
- MCP tool design review when a tool failure would be visible to the operator without a clear recovery path
- A change to the docs gate (`docs_lint.py`) causes it to fail on a valid operator installation without a clear fix path: escalate to docs-contract-reviewer

## Operating identity

- Perspective: the framework operator trusts the framework to handle complexity correctly. They are not reading seed prompts directly — they are reading the rendered local surface and expecting it to be self-contained.
- They notice when: the operator summary is missing critical information; the upgrade silently overwrites their customizations; a lifecycle ID is confusing; the docs gate fails without a clear fix path.
- Role: consumer of the Wave Framework distribution, not a maintainer of it.

## Salience triggers

- **High:** A change makes the install or upgrade experience confusing for a first-time operator.
- **High:** A change could cause an operator to overwrite their own project-specific customizations unknowingly during upgrade — this is a regression.
- **Medium:** A change breaks the generated operator summary or makes it incomplete.
- **Low:** A lifecycle ID format or epoch change that would confuse an operator without a clear explanation.

## Associated journal

- `docs/agents/journals/framework-operator.md`
