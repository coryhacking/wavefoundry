# Publish behavior contracts in TechDocs

Change ID: `248o4-enh publish-behavior-contracts-in-techdocs`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-24
Wave: 248o5 behavior-contracts-and-spec-vocabulary

## Rationale

Readers use a change spec to understand one delivery and a behavior contract to learn what a product promises across deliveries. A contract can describe an API, a CLI result or behavior a user sees. Moving these pages under architecture helps readers only if the published site gives them a way to find the promises. Existing sites may already include all architecture descendants while excluding the old contracts folder.

## Product Intent

An engineer browsing a component in Backstage can open Behavior contracts and find the current authoritative description of a behavior. A project owner can see and control which pages a folder migration adds to that audience.

## Requirements

1. Use `docs/architecture/contracts/` as the default home for standing behavior contracts. Link its index from the architecture hub. Explain when to write a change spec, update a standing contract, or record an architecture decision. Keep pre-admission plans in their existing location. Discover the legacy directory throughout the transition, migrate maintained relative links, and report ambiguous mixed layouts without overwriting files.
2. For a new TechDocs baseline with contracts, provide a visible Behavior contracts entry and working links to the published pages. Support both collections of contract pages and a curated index that points to canonical pages elsewhere. Preserve one maintained source for each promise.
3. During migration from `docs/specs/`, preview additions to the published site using the project's actual inclusion rules, including inherited architecture wildcards. Preserve existing exclusions until the owner chooses wider publication. If existing or proposed exposure cannot be determined, leave affected pages in their legacy locations, preserve their exclusions and explain what the owner must resolve. Establish effective exclusions before moving a private page. Every durable intermediate state must preserve its publication boundary. Preserve maintained navigation, existing catalog ownership and repeat-run behavior.
4. Check site navigation and link destinations during TechDocs verification. Identify a repository-only reference as such and give readers a usable destination when the project supplies one. Report unresolved internal links. A repository without TechDocs can adopt the layout independently.

5. Use the same layout in the shipped installation seeds, templates, refresh instructions and upgrade runner. On a fresh install, create the behavior contract index under `docs/architecture/contracts/` and link it from the architecture hub. Keep staged specs in the configured plans root and admitted specs inside their wave. A subsequent refresh must preserve project-authored content and must not recreate the retired directory.
6. On upgrade, inventory the target checkout before writing. Preview source and destination paths, link edits, publication changes and anything requiring an owner decision. Recheck the source, destination, publication configuration and approved scope immediately before each write and on resume. Defer a conflicting move for a new preview if those inputs changed. On the first hop, use a supported preview hook when available. If the installed runner and incoming pack cannot preview the migration together, complete the framework upgrade with the affected contracts in place and give an executable preview/apply route through the installed incoming runner. Preserve downstream hook ownership. Preserve project-authored content and identify unresolved paths in the upgrade summary. An interrupted or repeated upgrade must be safe to resume without duplicate contracts or lost edits.

## Scope

Cover contract discovery through the architecture hub, baseline generation, repository-owned navigation, migration boundaries and publication verification. Coordinate the move with consumers of the legacy path, including review routing and statistics. Keep closed wave records readable. Deployment, Backstage access policy and rewriting downstream contracts are outside this change.

## Acceptance Criteria

- [x] AC-1: In a clean local TechDocs build, follow the component documentation landing page to Behavior contracts and open a product behavior page. The test follows generated HTML links and verifies the destination content.
- [x] AC-2: An index-only fixture links to an authoritative API page outside the folder. Its published link resolves, a repository-only reference is labeled, and a deliberately broken internal link is reported.
- [x] AC-3: On a custom site that includes architecture descendants and excludes legacy contracts, preview identifies the exposure. The default migration keeps an excluded fixture out of the built output. Selecting one contract publishes only the selected addition. A second run preserves custom navigation and catalog metadata.
- [x] AC-4: Exercise a legacy collection, a destination collision and a repository without TechDocs. Verify contract discovery, link handling and counts across the transition, and show that standing contracts remain distinct from change specs and ADRs.

- [x] AC-5: Install from a built framework pack into a fresh target using the documented installation flow. Verify the new contract index, its hub link, the template guidance and the absence of a newly scaffolded `docs/specs/`. Create and admit a spec and check both locations. Repeat refresh after adding a project-authored contract and verify its contents and links survive.
- [x] AC-6: Start the first upgrade with the actual v1.51.0 runner and a built incoming pack. Test both the stock preview bridge and a custom pack without a cooperating hook. Verify the latter defers safely and follow its printed recovery route. Preview may write existing local diagnostic logs only; compare project content and configuration before and after. Verify the applied tree, owned links and effective TechDocs exposure against the preview. Build the site at interruption points on either side of each publication-affecting move and prove an excluded sentinel stays absent. Exercise indeterminate rules, a conflicting destination and a source or configuration edit after preview. Resolve, re-preview or resume as directed, then rerun and verify no lost content, duplicate pages or stale generated guidance.

## Tasks

- [x] Inventory contract path consumers and confirm migration, link and collision handling before moving files.
- [x] Update the architecture hub, authoring guidance, baseline and refresh workflow for both collection shapes.
- [x] Compare publication scope before and after migration. Surface ambiguous or broken links in the audit.
- [x] Build representative sites and check navigation, file presence, exclusions and repeat runs.

- [x] Trace the built pack from install through seeding, upgrade reconciliation and refresh. Exercise the clean-install and legacy-upgrade fixtures through those entry points.

## Agent Execution Graph

Inventory consumers and establish fixture baselines, implement discovery and publication, then verify the generated sites against those baselines.

## Serialization Points

- `.wavefoundry/framework/install/plan-template.md`
- `.wavefoundry/framework/seeds/040-docs-structure-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/techdocs_audit_lib.py`
- `.wavefoundry/framework/seeds/178-refresh-techdocs.prompt.md`
- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/project_stats.py`
- `docs/architecture/`

## Affected Architecture Docs

Update `docs/ARCHITECTURE.md` to explain contract ownership and link to the index.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Proves reader discovery. |
| AC-2 | required | Supports existing canonical references. |
| AC-3 | required | Protects project publication choices. |
| AC-4 | required | Preserves existing operating layouts. |
| AC-5 | required | Verifies the layout delivered to new projects. |
| AC-6 | required | Verifies migration and recovery for existing projects. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-24 | Staged for discussion. | Local project documentation inventories and MkDocs configurations. |

| 2026-11-24 | Readback: establish the new contract home and move only when ownership, destination and publication scope are known. Prove reader navigation, installed guidance and safe first-hop preview/apply, including interruptions. Preserve existing publication choices. | AC-1 through AC-6; install seeds, templates, TechDocs renderer/audit and upgrade hook. |
| 2026-11-24 | Inventory found one self-hosted standing contract, `docs/specs/mcp-tool-surface.md`, with existing working-tree edits and no destination collision. The architecture hub and maintained relative links must follow its actual location. Preserve the contract's own relative links when rebasing them. Defer conflicting destinations, mixed indexes and uncertain publication rules for owner review. Exclude the retired change-package subtree `docs/specs/changes/` from contract discovery, movement and counts. | Repository file inventory, current contract, seeds 040/160/170/220. Closed records and historical receipts retain their original paths. |
| 2026-11-24 | The current site excludes the legacy page through `/*` and includes architecture descendants through `!/architecture/**`. A default move therefore needs an effective destination exclusion first. The reader needs a repository reference for a private target. Preserve the maintained navigation and engineering ownership. | Root `mkdocs.yml`, `catalog-info.yaml`, `docs/index.md`, `docs/ARCHITECTURE.md`. |
| 2026-11-24 | Seeds 040, 150 and 230 create the folder, contract files and README index. Seeds 001, 002, 050, 060, 100, 120, 160, 170, 175, 190 and 211 carry vocabulary, evidence discovery, examples and reviewer guidance. The renderer ships `install/plan-template.md` into `docs/plans/plan-template.md` missing-only. TechDocs draws from `catalog-info.template.yaml`, `mkdocs.template.yml` and `techdocs-index.template.md`; seed 178 governs refresh. Preserve operator edits to installed copies. | Shipped install directory, renderer baseline tables, installed project templates, agent guidance and close-wave prompt. |
| 2026-11-24 | Review routing has both path-only and narrative triggers and a writable policy baseline in the MCP contract. Statistics recursively count contract and architecture Markdown. Constants lint and retrieval fixtures name the MCP contract directly. Server retrieval ranks both directory prefixes. Persona evidence configuration and active evaluation oracles also reference the legacy path. Preserve compatibility coverage while updating active path expectations. | `review_policy.py`, `project_stats.py`, `wave_lint_lib/docs_constants_validators.py`, `wf_server/server_impl.py`, `docs/workflow-config.json`, `docs/evals/`, framework benchmark query sets and contract, lifecycle, renderer, indexing and stats tests. |
| 2026-11-24 | The v1.51.0 runner loads the incoming pack's extension and directly calls its optional `post_extract` with `dry_run=True`. It catches preview exceptions and reports newly written diagnostic logs. The absence of a preview therefore cannot authorize movement. A noncooperating pack needs an executable preview and apply route through the newly installed runner. | Actual release archive `wavefoundry-1.51.0.q5hc.zip`, tagged `upgrade_wavefoundry.py::phase_dry_run`, and shipped `scripts/upgrade_extensions.py`. AC-6 still requires execution of both first-hop cases. |
| 2026-11-24 | Implemented fresh-install contract guidance, document counting across both layouts, and missing-only TechDocs navigation. Existing customized site navigation stays under project control. | Pack extraction and admission smoke passed in isolation. Thirty integrated focused tests passed, including hook parity. A built-site publication comparison and upgrade migration are pending. |
| 2026-11-24 | The maintained hub and landing page now lead to a curated Behavior contracts index. Self-host keeps the MCP reference in its legacy location and identifies its repository destination. | MkDocs 1.6.1 with techdocs-core 1.7.1 built both fixtures and this site. Followed the generated links to the product page and API page and checked their contents. Self-host HTML links to the contract index and the repository reference; the excluded MCP contract has no generated page. The deliberately broken link was identified. |
| 2026-11-24 | Exercised migration on a project whose site excludes legacy contracts and includes all architecture descendants. Preview identified both potential additions. | Real MkDocs builds before migration, after apply and after a second apply showed neither private page by default. Selecting one page published exactly that page. Custom navigation and catalog metadata survived. A separate no-site fixture preserved a destination collision and the retired change subtree, and rebased both inbound and outbound relative links. The project statistics migration test passed. |
| 2026-11-24 | Fresh pack install and refresh qualified for the contract scope. Setup, stdio MCP and phase 1 audit succeeded. A real enhancement spec moved from plans into a wave. Two refreshes preserved the edited index, separate contract, linked API page and hub byte for byte. | The generated site contained both target pages; the legacy folder was absent. The phase 2 audit correctly named the next unrelated installation step. |
| 2026-11-24 | Applied the reviewed self-host migration. It installed the exact page exclusion before moving the MCP contract, rebased its links and preserved the original edits. | Verified the destination bytes against the reviewed transformation. The rebuilt site links to the canonical repository URL, with no generated MCP reference. In an interrupted fixture, builds after configuration, copy, link updates and retirement each excluded the private sentinel. Full docs lint passed. |
| 2026-11-24 | The v1.51.0 stock bridge emitted a digest that remained valid after installation; a custom hook deferred the move and the installed runner supplied recovery. | Dry runs changed no project files. Both upgraded targets passed the docs gate and index refresh after a fresh-process retry. Eight interrupted writes resumed through the original receipt, with a built site at each stop. Custom selection published one page, preserved navigation and catalog, and refused a changed configuration. Removing the destination exclusion failed the named migration regression test. |
| 2026-11-24 | Repaired the three delivery findings. Link edits now splice visible Markdown into the original bytes, resume uses the same unsupported-reference checks as preview, and only the root nav section receives page-target edits. | Three new migration tests failed before repair. All 12 tests in test_contract_migration passed afterward, including link/comment CRLF preservation, retention of originals on a changed resume, and preservation of custom MkDocs metadata. |
| 2026-11-24 | Kept the reviewed model-comparison inputs byte-for-byte, including their original document paths. The historical result verifies against its original hashes. | ModelSwapBenchmarkFixtureTests and the retired-model fixture census. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-24 | Use a named contracts collection under architecture. | The directory supports discovery while its index can route readers to existing authoritative material. | A separate top-level collection or individual architecture pages with type markers. |

## Risks

| Risk | Mitigation |
| --- | --- |
| A folder move publishes an internal page or strands a link. | Compare built output on both sides of migration and exercise excluded content. |
| An index becomes a second version of a contract. | Keep summaries short and link to the maintained source. |

## Session Handoff

All six acceptance criteria passed. The contracts layout now supports the dependent tool and skill changes. The wave still needs integrated qualification and delivery review.
