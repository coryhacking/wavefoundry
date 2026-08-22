# 178 - Refresh TechDocs (Shortcut)

Use this when you want a single command-style request such as:

- `Refresh TechDocs`
- `Author TechDocs`

Intent:

- Make the project's generated documentation eligible for Backstage catalog ingestion and TechDocs generation, then author or refresh the published pages for the humans who read a TechDocs site, from verified sources and without forking the source of truth. Three steps: generate the missing-only baseline with `wf_techdocs_baseline` over MCP (CLI fallback `wf techdocs-baseline`), run the technical-writer-coordinated collaboration that authors the published pages, and validate.

**Two branches.** By default this workflow **authors**: it generates the missing-only baseline and then writes the published pages. On an explicit read-only request ("review the TechDocs", "audit the published pages", "what would you change"), run the **read-only procedure** at the end of this document instead: it reports findings and proposed edits and writes nothing at all.

The generated baseline is a starting point, never a claim: nothing here registers an entity with a Backstage instance, renders or publishes a site, or invents an owner, system, domain, API, or CI topology. Wavefoundry does not render or preview the downstream site. Rendering and publication are owned by the operator's chosen Backstage/CI environment; the follow-up checklist at the end of this seed is the canonical list of what remains for the operator, and the install/upgrade prompts point here.

The `wf-techdocs` skill (Claude Code, Codex, Antigravity) is a thin pointer to this workflow; either invocation runs the identical steps.

---

## Contract

### Input

The current repository. The workflow reads `mkdocs.yml` (after step 1) as the publication boundary: the `nav` entries plus the paths that survive `exclude_docs`. It writes only inside that boundary, with exactly one exception named in step 2 (removing the generated-by line from the trio's root members when the writer takes ownership of the trio).

### Step 1: baseline (`wf_techdocs_baseline`, CLI `wf techdocs-baseline`)

Run the baseline: when the Wavefoundry MCP is attached, call `wf_techdocs_baseline(mode='dry_run')` first (it reports what a run would write, writes nothing) and then `wf_techdocs_baseline(mode='run')`; otherwise run the CLI dispatcher (POSIX `./.wavefoundry/bin/wf techdocs-baseline`, native Windows `.\.wavefoundry\bin\wf.cmd techdocs-baseline`) (add `--json` for the typed envelope; the CLI is also what install-log row 2.13.5 names for hosts without MCP). Both entries call the same function and behave identically. It:

- runs only when `docs/references/project-overview.md`, `docs/ARCHITECTURE.md`, and `docs/prompts/index.md` exist as regular files; otherwise it writes nothing, prints one `techdocs-baseline: ERROR` line naming the missing targets, and exits 1. **Stop the workflow** and report the missing targets; do not author pages against a landing page that would link to absent documents.
- generates the root `catalog-info.yaml` (a standalone-documentation `Component`: `spec.type: documentation`, `spec.lifecycle: experimental`, `spec.owner: engineering`, `backstage.io/techdocs-ref: dir:.`, entity name `<repo>-docs`), the root `mkdocs.yml` (`docs_dir: docs`, `techdocs-core`, a four-entry `nav`, deny-by-default `exclude_docs` that publishes only `index.md`, `ARCHITECTURE.md`, `architecture/**`, `references/**`, and `prompts/index.md`), and `docs/index.md` (landing page with `Owner` / `Status` / `Last verified` metadata), **missing-only**: any existing member is preserved byte-for-byte, whether or not it carries the generated-by stamp.
- writes a one-line generated-by stamp into each generated file (`# wavefoundry: generated missing-only Backstage/TechDocs baseline; project-owned, edit freely.` in the YAML files; the same text as an HTML comment after the metadata block in `docs/index.md`). The stamp is the only ownership signal: a file that carries it is generated, a file without it is project-owned.
- prints one `techdocs-baseline: WARNING` when the trio is **mixed** (some members generated, some project-owned), naming the project-owned files in canonical order (`catalog-info.yaml`, `mkdocs.yml`, `docs/index.md`); the `--json` envelope carries the same `partial` record. The warning is a fact about the tree, not a validity claim: verify `backstage.io/techdocs-ref: dir:.`, the root `mkdocs.yml` `docs_dir` / `nav` / `exclude_docs`, and `docs/index.md` against each other before registration or publication; align the files or remove the generated-by lines to take ownership. A rerun recomputes the same warning until the operator reconciles the trio.
- exits 2 without writing when a destination is an escaping symlink, a directory, a dangling symlink, or another non-regular object (an in-root symlink to a regular file counts as present and is preserved); over MCP the same cases are `status: error` with `techdocs_precondition_unmet` / `techdocs_destination_refused`, and a mixed trio surfaces as the advisory diagnostic `backstage_techdocs_partial`.

Report what the command generated, what it preserved, and any warning verbatim.

### Step 2: collaboration (the technical-writer coordinates)

The `technical-writer` specialist coordinates this step (its role doc: precision and findability over completeness; verify before restating; summarize and link rather than duplicate). When the target does not enable that specialist, the coordinating agent adopts its stance directly and says so in the report. Request the following inputs, in isolation and with fresh contexts where the project's council policy requires it; each named lane degrades as stated when the target does not have it, and the report names every degradation:

| Supplier | Provides | When the lane is not available |
| --- | --- | --- |
| `guru` (with the Wavefoundry MCP) | Cited code facts for every behavior claim: `code_ask` with symbol anchors, per the citation rule in `docs/agents/guru.md` | The writer performs its own `code_read` / `code_search`-grounded verification and records it as such; no claim ships uncited |
| `software-architect` or `architecture-reviewer` | The current-state and boundary narrative; verification of every dogfood edit under `docs/architecture/` | The writer restates only what `docs/ARCHITECTURE.md` and its children already state, with citations |
| `security-reviewer` | The security posture summary, sourced from `docs/SECURITY.md` and the threat model when present; never inventing controls | Omit the posture section rather than guessing; say so |
| `qa-reviewer` or `reality-checker` | Verification of every claim that names behavior | The writer verifies against the tree and marks each claim as writer-verified |
| `docs-contract-reviewer` (existing-only per seed 100) | Signoff that the pages match the code and the specs, including the audience invariant below | `qa-reviewer` or the writer performs and names the docs-contract check |

The writer then authors or refreshes the published pages: `docs/index.md` (landing narrative), `docs/references/project-overview.md`, `docs/ARCHITECTURE.md` and its `docs/architecture/*` children, `docs/references/*`. Rules:

- **Audience invariant.** `docs/references/project-overview.md` and `docs/ARCHITECTURE.md` are agent startup-order surfaces (`AGENTS.md` Start Here) and MCP resources (`wavefoundry://overview`, `wavefoundry://architecture/current-state`). A reader-facing revision adds framing and summaries around their agent-orientation content and never removes or reorders it: the pre-revision heading sequence must remain a subsequence of the post-revision file. The docs-contract check verifies this explicitly.
- **Framing-only under `docs/architecture/`.** The Boundary Invariants, Interaction Edges, Dependency Direction, and State Ownership tables are review authority; the writer may frame and summarize them, never change their substance. The architecture lane verifies every edit there.
- **Link boundary.** `exclude_docs` removes agent surfaces (`agents/**`, prompt bodies, `waves/**`, plans, reports, memory) from the built site. Published pages link only inside the publication boundary and name agent surfaces by repository path in prose (or through `repo_url` when the operator has configured it), never as relative links that would 404 in TechDocs.
- **Summarize and link.** Pages do not duplicate `AGENTS.md`, role docs, wave records, or prompt bodies.
- **Citations and metadata.** Every behavior claim carries a citation from the supplier that verified it. Prefer the symbol form (`module.symbol`, file named without a line number): a line range goes stale the moment anything above it moves, including edits made later in the same wave, and nothing validates it. Use `path:start-end` only where no symbol names the fact, and recompute every such range against the final tree at Step 3. Every touched page keeps `Owner` / `Status` / `Last verified` metadata and passes the project's citation and link rules.
- **Ownership.** While `docs/index.md` is still the generated page its stamp stays. When the writer authors the landing page it removes the generated-by line from **all three** trio members, so the project owns the whole trio and a rerun of `wf techdocs-baseline` stays silent instead of warning about a mixed trio; an operator who prefers to keep the YAML members generated may leave their stamps and accept the warning. This marker-line removal on `catalog-info.yaml` and `mkdocs.yml` is the only write outside the publication boundary this workflow itself makes.

### Step 3: validation

These required checks stay inside Wavefoundry's declared Python tool environment; do not probe for or condition success on external renderers. An unavailable external renderer is neither a finding nor a degraded lane and does not belong in the workflow report.

- Run full docs validation (`wf_validate_docs` over MCP, or the CLI dispatcher `./.wavefoundry/bin/wf docs-lint`; native Windows `.\.wavefoundry\bin\wf.cmd docs-lint`); it must pass.
- Confirm every `nav` target in `mkdocs.yml` exists.
- Run the publication audit (`wf_techdocs_audit` over MCP once the host has reconnected, or the CLI dispatcher `./.wavefoundry/bin/wf techdocs-audit`; add `--json` for the envelope). It computes the publication boundary, `nav` target existence, relative links that dangle or escape that boundary, published-page metadata, the trio's ownership, and the audience invariant. Report `clean` with an empty `degraded` list, or explain each remaining finding **and each degrade reason**: a run that could not compute something reports `degraded` rather than `clean`, and silence about an unevaluated check would read as a clean site. The audit is **additive** to the citation re-resolve rule below, which it does not perform.
- Re-resolve every `path:start-end` citation added or touched in Step 2 against the tree as it now stands, after all other edits in this session are complete, including edits made by a later step or a sibling repair in the same session. Read each cited range and confirm it still covers the fact it is cited for; recompute the range when it does not, or replace it with the symbol form where a symbol names that fact. A citation whose file changed after the range was computed is stale until re-read, not until it looks wrong.
- Report what was written, what each supplier verified, which lanes degraded and how, and what remains for the operator (the checklist below).

### Recording boundary

The writer and every supplier return facts to the coordinating agent; none of them writes wave state. Outside an open wave, the docs-contract check is reported to the operator as a fact. Inside an open wave, the lifecycle coordinator records the facts through `wf_review_event` as executed evidence: inside the `observed` / `artifact_or_test_id` of that lane's whole-wave delivery approval, or as an executed `finding` record when there is a proposition to record. Never record a standalone page-only `approval:docs-contract-reviewer` for this workflow, which would pre-satisfy a required lane, and never treat a `run` event as evidence (it is an empty cycle marker).

### Install and upgrade

- On a fresh install the workflow runs at install-log row 2.13.5 (end of Phase 2, after the navigation targets exist). Mark the row `[~]` when the precondition is unmet (for example row 2.6 was `[~]`) or when the operator declines TechDocs for this project; the command is explicit and missing-only, so nothing runs by accident.
- Upgrade never generates or rewrites the trio; it points operators here. The `wf-techdocs` skill renders wherever `docs/prompts/refresh-techdocs.prompt.md` exists (every target after seed-100 reconciliation); on the upgrade that first ships this seed, backfill that prompt and re-run `wf render-surfaces` so the skill renders in the same upgrade.

## Read-only procedure (review branch)

Selected by an explicit read-only request. The deliverable is a report, not an edit.

**The rule is the invariant, not a tool list: any read-only operation is fine; nothing may write.** Run the audit, read whatever you need to judge the pages (published pages, `mkdocs.yml`, `catalog-info.yaml`, the security and threat-model documents the supplier table names, wave state when you need to know whether one is open), and use read-only retrieval freely.

**Never, in this branch:** write or edit any page; call `wf_techdocs_baseline` in either mode (its CLI has no dry-run flag, so on a host without MCP it would generate the trio, which is the one thing this branch promises never to do; the audit already reports the trio state and the `not_applicable` verdict, which is the same information); remove a generated-by marker line, which the authoring branch alone may do; call `wf_garden_docs`, `wf_sync_surfaces`, any other docs mutation, or any index mutation; call an external renderer or site-preview command.

Steps:

1. Run the audit: `wf_techdocs_audit` over MCP, or the CLI dispatcher (POSIX `./.wavefoundry/bin/wf techdocs-audit`, native Windows `.\.wavefoundry\bin\wf.cmd techdocs-audit`; add `--json` for the envelope). **The MCP tool appears only after the agent host reconnects following the upgrade that ships it, so the CLI is the interim path** rather than an equal free choice. A CLI exit code of 1 is an informative result, not a failed command: it means findings were reported, or the run degraded. Read `degraded` from the envelope directly rather than inferring it from the verdict, because a run with findings reports `findings` even when it also degraded.
2. Report the verdict, the `degraded` list, the finding count, each finding verbatim, **and the `publication` block** (`survivor_count`, the `nav` entries, the `exclude_docs` patterns): the boundary itself carries site-quality facts that no finding code covers, such as published pages that no navigation entry reaches. A `not_applicable` verdict means no `mkdocs.yml` exists; report the per-member trio state from the report's `trio` block rather than asserting the baseline was never generated, since a partly present trio also yields `not_applicable`. Then stop, because there is no publication boundary to review. Over MCP the report is **bounded**: read `truncated`, and when it is true say so and give `findings_total`, plus `findings_omitted` when that key is present (it appears only when the findings cap itself fired, and the survivor cap can truncate on its own), rather than presenting the capped `findings` array as the whole result, because `summary.finding_count` carries the TRUE total and will otherwise contradict the list you just enumerated. Take the boundary counts from `publication.survivor_count`, never from the length of `survivor_pages`, which is capped the same way. The CLI dispatcher returns the report uncapped, so prefer it when you need every finding. `nav` and `exclude_docs` are never capped and `truncated` says nothing about them.
3. Re-resolve the `path:start-end` citations on the published pages you are reviewing, exactly as the authoring branch's Step 3 requires: read each cited range and confirm it still covers the fact it is cited for. The audit does not do this, and a read-only review is the only pass positioned to catch a range invalidated by a later edit.
4. Gather the same supplier inputs as the authoring branch's step 2. The degrade rules there are written as authoring outcomes, so in this branch they read as: evaluate the lane's question yourself and label the answer with the substitute that produced it, or decline it explicitly and record the gap as a finding. Never imply a lane ran that did not.
5. Return a **findings and proposed-edits table** — page, claim or rule at issue, evidence with anchors, the proposed edit, and the supplier that verified it (naming the degraded substitute where a lane was absent) — followed by the audit report and the operator follow-up checklist below. Write nothing.

On a clean committed tree the audit reports `audience_not_informative`, because the baseline is then byte-identical to the working file and the heading check can prove nothing. That is the expected steady state of a committed repository, not a defect: say so and move on. The `clean` verdict is reachable while an uncommitted authoring edit exists, or when `--compare-to` names an older ref.

## Operator follow-up checklist (canonical)

The generated baseline is a conservative, project-owned starting point. Before registering or publishing:

1. **Owner.** Replace `spec.owner: engineering` with a real Group or User reference in your Backstage instance when `engineering` does not exist there.
2. **Catalog-unique name.** Confirm the generated `metadata.name` (`<repo>-docs`, at most 63 characters) does not collide with an existing entity; the `-docs` suffix reduces collision with a later product `Component` but cannot guarantee uniqueness.
3. **Rendering and publication.** Wavefoundry does not render or preview the downstream site. Rendering and publication are owned by the operator's chosen Backstage/CI environment; use that environment's established process rather than treating local rendering as a Wavefoundry validation step.
4. **Production architecture.** Prefer CI generation plus external storage with a read-only TechDocs reader, per Backstage's recommended architecture; the baseline generates no provider-specific CI YAML, `app-config.yaml`, catalog `Location`, storage configuration, or credentials.
5. **Edit links.** Add verified `repo_url` / `edit_uri` to `mkdocs.yml` when you want the GitHub/GitLab edit and feedback affordances; the baseline never guesses a remote, provider, or branch.
6. **Publication boundary.** `exclude_docs` publishes only the landing page, `ARCHITECTURE.md`, `architecture/**`, `references/**`, and `prompts/index.md`; widen or narrow it deliberately, and keep agent surfaces (`agents/**`, prompt bodies, `waves/**`, plans, reports, memory) out of the built site unless you mean to publish them.
7. **Not generated on purpose.** `API`, `Resource`, `System`, `Domain`, `Group`, `User`, and `Location` entities, OpenAPI/AsyncAPI/GraphQL/gRPC contracts, and any organization-specific ownership, lifecycle, or source-control facts are yours to add once verified.
