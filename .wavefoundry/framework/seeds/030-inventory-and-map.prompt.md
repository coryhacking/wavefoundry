# 030 - Inventory And Map

Intent:

- Discover project facts from the repository and assemble the evidence base that init, update, upgrade, and planning flows depend on.
- Separate **cheaply rediscoverable facts** (manifest paths, module layout, build entrypoints) from **durable non-obvious guidance** that belongs in later bootstrap outputs such as `AGENTS.md`.

Tasks:

1. Identify top-level modules, packages, services, apps, and build roots.
2. Detect project archetypes and traits from code, configs, and workflow files in the repository; record under `project_archetypes` and `project_traits` in `docs/repo-profile.json`.
3. Detect runtime, deployment, and sensitivity surfaces; record under `runtime_surfaces`, `deployment_modes`, `security_sensitivity`, `performance_sensitivity`, and `design_sensitivity` in `docs/repo-profile.json`. When a project shape needs a surface the canonical keys do not cover, add a profile key named for the surface rather than forcing evidence into an ill-fitting canonical key — record any such extensions in `docs/repo-index.md` so later seeds can find them.
4. Record architecture clues, operational entrypoints, docs inventory, and agent-entry files in `docs/repo-index.md`.
5. Identify shared hotspots and module boundaries likely to matter for wave partitioning.
6. **Stack, toolchain, CI/CD, and framework detection** — Scan IDE configuration, build toolchain and language manifests, cross-cutting build systems and version pinning, CI/CD pipelines, cloud scripting and platform tooling, project frameworks, and testing tools. Record IDE- and toolchain-derived signals (SDK/runtime version, language level, annotation processors, entry points, env vars, build targets, enforced toolchain, detected frameworks, test infrastructure) in `docs/repo-index.md` alongside primary build-manifest evidence. When IDE config or version-pinning files contradict build manifests, note the discrepancy explicitly — pinning files and IDE SDK settings are usually the developer's authoritative runtime choice. Skip signal categories for which no matching files exist.

 Category coverage (one illustrative example per category; see `seed-031` for the full detection catalog — load it only when disambiguation across multiple stacks is required, and load it once per run rather than re-reading per category):

 - **IDE configuration** — JetBrains `.idea/`, VS Code `.vscode/`, Xcode `.xcodeproj/`; see `seed-031` § IDE configuration.
 - **Language and build toolchain manifests** — e.g. Swift `Package.swift`, JS/TS `package.json`, Python `pyproject.toml`, Java/JVM `pom.xml` / `build.gradle*`, Go `go.mod`, Rust `Cargo.toml`, C#/.NET `*.csproj`; see `seed-031` § Language and build toolchain manifests.
 - **Cross-cutting build systems and version pinning** — Make, CMake, Bazel, `.tool-versions`, `.devcontainer/`; see `seed-031` § Cross-cutting build systems and version pinning.
 - **CI/CD pipelines and cloud delivery** — GitHub Actions, GitLab CI, Jenkins, ArgoCD / Flux, Helm / Kustomize; see `seed-031` § CI/CD pipelines and cloud delivery.
 - **Cloud scripting and platform tooling** — cloud-provider CLIs (Azure / GCP / AWS), FaaS runtimes (Lambda, Cloud Functions, Cloudflare Workers, Vercel), secrets management (Vault, SOPS, Key Vault), observability (Datadog, Prometheus, OpenTelemetry); see `seed-031` § Cloud scripting and platform tooling.
 - **Project framework and platform detection** — low-code (PowerApps, Salesforce), frontend (React, Vue, SwiftUI), backend (Spring Boot, FastAPI, Express), data / ML (PyTorch, Spark), IaC (Terraform, Pulumi, Helm); see `seed-031` § Project framework and platform detection.
 - **Testing tools and frameworks** — unit / integration, browser / UI automation (Selenium, Playwright, Cypress), API / contract (Pact — strong factor-13 signal), load / performance (K6, Gatling — factor-14 signal), coverage gates; see `seed-031` § Testing tools and frameworks.

7. **Design surface detection** — Scan for design artifacts and component infrastructure per the stack-specific patterns in `seed-031` § Design and UI surface (Web, Android, Flutter, React Native, Swift/SwiftUI/AppKit/UIKit, or no-UI). Record the result under `design_system.design_evidence` in `docs/repo-profile.json` using the schema below. This schema is the named output contract consumed by `seed-010` (seeding), `seed-040` (docs structure), and `seed-160` (upgrade backfill); field names must match exactly.

 ```
 design_evidence:
 detected: bool # true if any design artifact was found
 stack_specific_source: string # one-line summary of where design artifacts were found
 has_design_tokens: bool
 token_files: [string] # relative paths; empty list when none
 has_component_library: bool
 component_library: string | null # library name when present
 has_storybook: bool
 storybook_config_path: string | null # e.g. ".storybook/"
 has_typography_system: bool
 typography_source: string | null # description of the typography source
 ui_roots: [string] # relative directory paths
 detected_methodology: [string] # list (never a single string); e.g. ["tailwind"], ["css-modules", "sass"], ["swiftui"]
 ```

 **Extended scan: pattern and product-class signals.** After recording the `design_evidence` schema above, scan for the following signal groups and record results under `design_system.pattern_signals` and `design_system.product_class_signals` in `docs/repo-profile.json`. These outputs inform which Split B subtrees (`patterns/`, `state-patterns/`, `validation-patterns/`, `content/`) and Split C subtrees (`platforms/`, conditional product-class extensions) to seed during the extraction contract step (`seed-040` task 14).

 **Pattern signals** (record each as `true`/`false` with evidence path):
 - `has_navigation_patterns` — nav/sidebar/drawer/breadcrumb/shell component files
 - `has_feedback_patterns` — toast/snackbar/notification/alert/banner component files
 - `has_data_patterns` — table/list/grid/pagination/sort/filter component or hook files
 - `has_trust_patterns` — auth/login/signin/mfa/oauth UI components or flows
 - `has_chart_patterns` — chart/graph/d3/recharts/chart-js/victory/data-vis imports or components
 - `has_a11y_artifacts` — a11y/accessibility/contrast config, audit files, or linter rules
 - `has_motion` — animation/transition/framer-motion/react-spring imports or CSS keyframes
 - `has_responsive_tokens` — breakpoints/responsive/grid design tokens or utility files
 - `has_form_validation` — forms/validation/schema/zod/yup/valibot imports or validation hooks
 - `has_state_patterns` — loading/empty/error/success/skeleton component or state files

 **Product-class signals** (record each as `true`/`false` with evidence path):
 - `is_multi_platform` — `*.xcodeproj`, `android/`, `App.xaml`, `Package.swift`, `electron/main.*`, `tauri.conf.*`, or React Native `ios/`/`android/` subdirectories
 - `has_marketing_surface` — `marketing/`, `landing/`, `www/` top-level directories
 - `has_email_templates` — `emails/`, `templates/*.mjml`, `templates/*.html.erb`, or mjml/react-email imports
 - `has_print_surface` — `print/`, `pdf/`, or CSS `@page` rules in source files
 - `has_offline_support` — service worker registration, `workbox.*` imports, background-sync libraries
 - `has_notification_patterns` — push notification libraries (web-push, firebase-messaging, OneSignal, Expo notifications) or rich notification component files

 When a signal is present, include a concise evidence reference (file path or import). When no evidence is found for a group, record `false` rather than omitting the key.

8. **Brownfield pattern catalog** — When the repository has existing implementation history (source files with multiple prior implementations to learn from), scan a representative cross-section of the codebase and catalog dominant patterns under `code_patterns` in `docs/repo-profile.json`. Consumed by `seed-020` pattern-detection obligations at implementation time. At minimum, document:

 - **Naming conventions** — variable, function / method, type, file, and module naming style per primary language (e.g., `camelCase` functions, `PascalCase` types, `kebab-case` files).
 - **Error handling style** — how errors propagate (exceptions vs result types vs sentinel values); how they are logged or surfaced; whether errors are wrapped with context.
 - **Abstraction depth** — thin adapters and direct calls vs layered abstractions with protocols / interfaces; typical method / function length and scope.
 - **Argument ordering and initialization** — positional vs named arguments; builder pattern vs direct construction; preferred injection style (constructor, property, parameter).
 - **Test structure** — test file location convention (co-located vs separate test directory), naming pattern for test files and test cases, use of mocks vs real dependencies, fixture and setup style.
 - **Module organization** — grouping by feature, by layer, or by type; whether modules expose a public API surface or share implementation freely.

 If the repository has fewer than three source files with meaningful implementation to compare, record `code_patterns: { "status": "insufficient_history" }` and skip the catalog.

9. **Module inventory format for `docs/repo-index.md`** — When recording top-level modules, use the structured `## Module: <name>` format below. This makes the inventory machine-readable for the Guru's orientation pass and consistent with `kind="code-summary"` chunks that the semantic index emits per source file:

 ```markdown
 ## Module: <name>

 **Purpose:** One sentence describing what this module does.
 **Entry points:** Primary public functions, classes, or API routes (comma-separated).
 **Key dependencies:** Other modules or external packages this module imports (comma-separated).
 ```

 Emit one `## Module:` section per top-level module, package, service, or app. When the repository has fewer than three source files, record a single `## Module: (root)` entry rather than omitting the section.

10. **Architecture handoff for `seed-060`** — In `docs/repo-index.md` (or a clearly labeled subsection), make the following **easy for a downstream prompt to quote** without re-scanning the whole tree:

 - **Deployable units** — apps, daemons, libraries, CLIs, and how they are built or packaged (paths to build scripts or manifests).
 - **Inter-unit edges** — IPC, HTTP, files, notifications, shared DBs, cloud / vendor SDKs (name the integration and both ends).
 - **Ownership of shared state** — caches, registries, schedulers, coordinators, singletons (path or type references).
 - **Sensitivity** — network exposure, secrets, permissions, entitlements, PII (one line each; detail belongs in threat model later).
 - **Concurrency / single-lane hints** — subtrees that are safe for parallel feature work vs areas that routinely conflict.

 When evidence is missing, add **`TBD`** or **`Unknown`** entries so `seed-060` can record explicit gaps instead of silent omissions.

11. **Persona candidate evidence** — Identify evidence for project-specific personas and record under `persona_candidates` in `docs/repo-profile.json` as a list of objects. Consumed by `seed-120` (project persona synthesis) as a starting shortlist; `seed-120` still performs its own evidence scan and user-confirmation pass before generating persona docs. Each candidate object has:

 - `name` — proposed persona (e.g., `wave-coordinator`, `release-engineer`, `homekit-integration-owner`).
 - `evidence` — concise rationale grounded in repository signals (file paths, recurring review responsibilities, ownership patterns, domain-specific operations).
 - `related_factor_ids` — optional list of factor IDs (strings like `"04"`, `"13"`) from `factor_review` whose review obligations this persona would naturally cover.

 When evidence is thin, record fewer candidates rather than speculative ones. Record `persona_candidates: []` (empty list) rather than omitting the key when no evidence supports any candidate.

12. **Per-factor applicability evaluation** — Evaluate each of the 15 factors defined in the framework README `## Factor Review Model` section against project evidence. For each factor, record one of: `applicable` (concrete evidence meets the applicability signal), `partial` (some evidence; may become relevant as the project grows), or `not-applicable` (no meaningful review pressure). Include a **concise evidence rationale** for each. Record the full evaluation in `docs/repo-profile.json` under `factor_review` as an object keyed by factor number (e.g. `"04"`) with fields `name`, `status`, and `rationale`. Consumed by `seed-050` (agent entry surface bootstrap) to determine which factor-review agent files to generate, and by `seed-070` (quality and debt) for factor-aware review triggers.

Required outputs or updates in the target repository:

- `docs/repo-index.md` — top-level modules, runtime surfaces, IDE / toolchain signals, framework / CI / cloud evidence, and the architecture handoff for `seed-060` (task 9).
- `docs/repo-profile.json` — top-level schema owned by this seed:

 | Key | Task | Consumed by |
 | ------------------------------- | ---- | ----------------------------------------------- |
 | `project_archetypes` | 2 | `seed-040`, `seed-050`, `seed-120` |
 | `project_traits` | 2 | `seed-040`, `seed-050`, `seed-120` |
 | `runtime_surfaces` | 3 | `seed-040`, `seed-050`, `seed-060`, `seed-070` |
 | `deployment_modes` | 3 | `seed-040`, `seed-050`, `seed-070` |
 | `security_sensitivity` | 3 | `seed-050`, `seed-070` |
 | `performance_sensitivity` | 3 | `seed-050`, `seed-070` |
 | `design_sensitivity` | 3 | `seed-040`, `seed-050` |
 | `design_system.design_evidence` | 7 | `seed-010`, `seed-040`, `seed-160` |
 | `code_patterns` | 8 | `seed-020` (at implementation time) |
 | `persona_candidates` | 11 | `seed-120` |
 | `factor_review` | 12 | `seed-050`, `seed-070` |

 Profiles may carry additional keys set by other seeds (for example `supported_agent_platforms` from `seed-050`); this table names only the keys `seed-030` is responsible for.

Required semantics:

- top-level modules
- primary technologies and runtime model
- sensitive surfaces
- shared hotspots
- likely wave partition boundaries
- likely persona candidates and evidence
- per-factor applicability evaluation (all 15 factors) with status and rationale, stored in `docs/repo-profile.json` under `factor_review`
- IDE- and toolchain-derived signals when present: SDK / runtime / language level, annotation processors or build plugins, run and debug entry points, version pinning, enforced toolchain and formatter, Jupyter kernel metadata when notebooks are present
- detected project frameworks and platforms: web / mobile frontend, backend service, data / ML, IaC, low-code / enterprise (PowerApps, Salesforce, etc.)
- CI/CD pipeline structure: triggers, environment strategy, secrets surface, deployment targets, container registry references
- cloud scripting and platform tooling: cloud-provider CLI usage, FaaS runtimes (Azure Functions, Cloud Functions, Cloudflare Workers, Lambda, Vercel, Netlify), secrets management (Vault, SOPS, External Secrets, Doppler), observability platform config (Datadog, Grafana / Prometheus, OpenTelemetry Collector)
- test infrastructure: unit / integration frameworks, browser / UI automation tools (Selenium, Playwright, Cypress, Appium), API / contract testing, load testing, coverage tooling

Guardrails:

- Prefer evidence from the repository over assumptions. **Do not invent signals** — a framework, CI platform, or cloud-runtime detection must be grounded in a dependency, config file, or code reference; a name match alone is not sufficient.
- Keep unknowns explicit when evidence is missing: use `TBD` or `Unknown` in prose, and appropriate null / empty-list values in `docs/repo-profile.json`.
- If a repository already has valid canonical inventory docs, update them rather than duplicating them.
- **On upgrade runs, preserve operator-refined values** in `factor_review.*.rationale`, `code_patterns.*`, and `persona_candidates[*].evidence` when the underlying repository evidence still supports them; overwrite only when evidence has materially changed, and prefer additive edits (appending a new evidence line) over wholesale replacement. This parallels `seed-160`'s preservation rule for `lifecycle_id_policy.epoch_utc`; when in doubt, keep the human text and record the new signal as an adjacent evidence bullet.
- Load `seed-031` **at most once per run**, and only when disambiguation across multiple stacks is required; a typical Init or Upgrade run should complete without loading the full detection catalog.
