# 031 - Tech Stack Detection Catalog (Reference Appendix)

Intent:

- Reference catalog consumed by `seed-030` task 6 (stack, toolchain, CI/CD, and framework detection) and task 7 (design surface detection). Keep detection patterns, schemas, and stack-specific signals synchronized here when adding new stack support. Agents do **not** need to load this file for a typical Init or Upgrade run — `seed-030` carries a short illustrative list and cites this catalog only when disambiguation is required.

How to use:

- Used by `seed-030` task 6 when scanning IDE configuration, build toolchain, and language manifest files for signals that are not always visible in primary build manifests alone, and by `seed-030` task 7 when scanning for design-surface artifacts.
- The `design_evidence` schema (the named output contract for the design-surface scan) lives in `seed-030` task 7, not here. This catalog is detection-pattern reference only.
- When adding support for a new IDE, language, build system, CI platform, cloud scripting surface, framework, test runner, or design-system pattern, add the detection evidence to the appropriate subsection below.

## IDE configuration

Check for the presence of any of the following and extract evidence where found:

- **JetBrains family (`.idea/`)** — used by IntelliJ IDEA (Java/Kotlin), WebStorm (JS/TS), GoLand (Go), CLion (C/C++), Rider (C#/.NET), PyCharm (Python), Android Studio (Android), and others: `misc.xml` (SDK version, language level, framework exclusions), `compiler.xml` (annotation processors, which modules enable annotation processing), `runConfigurations/` (application entry points, VM args, env vars, test runner settings, debug arguments), `codeStyles/` (enforced formatting standards), `inspectionProfiles/` (static analysis configuration), `modules.xml` / `.iml` files (source roots, test roots, excluded paths), `jsLibraryMappings.xml` / `prettier.xml` / `eslint.xml` / `typescript-compiler.xml` (JS/TS-specific toolchain config when present)
- **VS Code (`.vscode/`)**: `settings.json` (language server SDK, null analysis, formatter), `launch.json` (debug entry points, env vars, program args — often the most explicit record of how to start the application), `tasks.json` (build, test, and custom task definitions), `extensions.json` (recommended extensions reveal toolchain, e.g. Checkstyle, SonarLint, rust-analyzer, clangd, Go tools, C# Dev Kit)
- **Visual Studio / MSBuild**: `.sln`, `.csproj`, `.vbproj`, `.fsproj` (target framework, NuGet packages, project type, output paths), `Directory.Build.props` / `Directory.Build.targets` (repo-wide MSBuild overrides), `NuGet.config` (package sources)
- **Xcode**: `.xcodeproj` / `.xcworkspace` (iOS/macOS/tvOS/watchOS target, schemes, deployment target, signing config), `Podfile` / `Podfile.lock` (CocoaPods dependencies), `Cartfile` (Carthage dependencies), `Fastfile` / `Appfile` / `Matchfile` (Fastlane CI/CD automation), `.xcode-version` (pinned Xcode version)
- **Eclipse**: `.classpath`, `.project` (source and test roots, classpath entries, build path)

## Language and build toolchain manifests

Scan for language-specific project files and extract SDK version, dependencies, entry points, and build targets:

- **Go**: `go.mod` (module path, Go version, dependencies), `go.sum`, `.golangci.yml` / `.golangci.yaml` (linter config and enabled rules)
- **Rust**: `Cargo.toml` (package name, edition, features, workspace members, binary targets), `Cargo.lock`, `rust-toolchain.toml` / `rust-toolchain` (pinned toolchain channel and components), `.cargo/config.toml` (target platform, build flags, aliases, registry config)
- **Swift / Swift Package Manager**: `Package.swift` (targets, products, dependencies, Swift tools version), `.swiftlint.yml` (SwiftLint rules), `.swiftformat` (SwiftFormat config)
- **JavaScript / TypeScript**: `package.json` (scripts, engines field for Node version, workspaces, dependencies vs devDependencies), `tsconfig.json` / `tsconfig.*.json` (target, strict mode, module resolution, path aliases, lib), `.eslintrc.*` / `eslint.config.*` (lint rules and plugins), `.prettierrc.*` (formatter config), bundler configs (`vite.config.*`, `webpack.config.*`, `rollup.config.*`, `esbuild.*`), framework configs (`next.config.*`, `nuxt.config.*`, `remix.config.*`, `astro.config.*`), test configs (`jest.config.*`, `vitest.config.*`), monorepo orchestration (`nx.json`, `turbo.json`, `pnpm-workspace.yaml`, `lerna.json`)
- **C / C++**: `CMakeLists.txt` (targets, compiler requirements, options), `compile_commands.json` (compilation database used by clangd and IDEs), `vcpkg.json` (vcpkg dependencies and features), `conanfile.txt` / `conanfile.py` (Conan packages), `.clang-format` (formatting style), `.clang-tidy` (tidy checks and config), `.clangd` (clangd server config), `meson.build` (Meson project definition), `xmake.lua` (xmake build rules)
- **C# / .NET**: `global.json` (pinned SDK version — authoritative for the repo), `*.csproj` / `*.fsproj` (target framework, nullable, implicit usings, package references), `.editorconfig` (code style enforced by Roslyn analyzers), `Directory.Packages.props` (central package version management)
- **Java / JVM**:
  - *Maven*: `pom.xml` — extract `groupId`, `artifactId`, `version`, Java version (`maven.compiler.source` / `maven.compiler.target` / `maven.compiler.release` properties or `<release>` in compiler plugin config), `<modules>` list for multi-module builds, `<dependencyManagement>` BOM imports, key plugins (`maven-surefire-plugin` for tests, `maven-failsafe-plugin` for integration tests, `spring-boot-maven-plugin`, `maven-shade-plugin` / `maven-assembly-plugin` for fat JARs, `jacoco-maven-plugin` for coverage, `checkstyle-maven-plugin`, `spotbugs-maven-plugin`, `maven-enforcer-plugin`), `<profiles>` (note environment-specific profiles), `<distributionManagement>` (artifact publish target); `.mvn/wrapper/maven-wrapper.properties` (pinned Maven version — authoritative); `.mvn/extensions.xml` (build extensions, e.g. Takari lifecycle or custom wagon providers); `.mvn/jvm.config` and `.mvn/maven.config` (per-project JVM and CLI flag defaults)
  - *Gradle*: `build.gradle` / `build.gradle.kts` (distinguish Groovy vs Kotlin DSL by extension — extract `sourceCompatibility`, `targetCompatibility`, `java.toolchain.languageVersion`, applied plugins including `java`, `java-library`, `application`, `spring-boot`, `com.google.protobuf`, `com.diffplug.spotless`), `settings.gradle` / `settings.gradle.kts` (root project name, `include`d sub-projects, plugin management), `gradle/wrapper/gradle-wrapper.properties` (pinned Gradle version — authoritative), `gradle.properties` (project-wide properties, JVM args for the daemon via `org.gradle.jvmargs`), `buildSrc/` (convention plugins — note if team uses precompiled script plugins), composite builds via `includeBuild()`
- **Python**: `pyproject.toml` (build backend, tool configs for pytest/black/ruff/mypy, `requires-python`), `setup.cfg` / `setup.py`, `requirements.txt` / `requirements-dev.txt`, `poetry.lock` / `Pipfile.lock`, `tox.ini` (test environments and Python version matrix); **PyCharm** uses `.idea/` (see JetBrains above) plus `.idea/python-path-provider.xml` and `.idea/misc.xml` Python SDK entry for the interpreter path and version; **Jupyter**: scan for `.ipynb` notebook files (extract kernel name and language from metadata — `kernelspec.language`, `kernelspec.name`), `jupyter_notebook_config.py` / `jupyter_lab_config.py` (server config), `.jupyter/` directory, and note any notebooks that serve as runnable entry points or data-pipeline definitions rather than exploratory scratch work
- **Scala**: `build.sbt` (sbt project definition — `scalaVersion`, `libraryDependencies`, `scalacOptions`, sub-project structure), `project/build.properties` (sbt launcher version), `project/plugins.sbt` (sbt plugins — e.g. sbt-assembly, sbt-native-packager, Akka gRPC, Play), `project/Dependencies.scala` or shared dependency files, `.scalafmt.conf` (Scalafmt formatting config), `.scalafix.conf` (Scalafix rewrite rules); for Maven/Gradle Scala projects extract `scala.version` property and Scala plugin config
- **Groovy**: `build.gradle` / `settings.gradle` (Gradle DSL — distinguish Groovy vs Kotlin DSL by extension; note Groovy-specific plugins and closures), `Jenkinsfile` (Jenkins declarative or scripted pipeline — extract stages, agent config, environment blocks, shared library imports), `*.groovy` scripts in `src/` or `scripts/`, Grails projects (`grails-app/` directory structure with `grails-app/controllers/`, `grails-app/services/`, `grails-app/domain/`, `application.yml`), Spock testing (`spock-core` in dependencies — note Groovy-based test specs in `src/test/groovy/`)
- **Ruby**: `Gemfile` / `Gemfile.lock` (gem dependencies, Ruby version via `ruby` directive), `Rakefile` (task definitions), `.ruby-version`
- **Assembly**: `Makefile` / `GNUmakefile` (assembler invocation, target architecture, output format — look for NASM, MASM, GAS, LLVM/clang assembler flags)

## Cross-cutting build systems and version pinning

Extract build topology and pinned runtime versions regardless of language:

- **Make**: `Makefile` / `GNUmakefile` / `makefile` — extract named targets, especially `all`, `build`, `test`, `clean`, `install`, `lint`, `fmt`, `run`; flag recursive sub-makes and included fragment files; note variables that pin compiler or tool versions
- **CMake**: top-level `CMakeLists.txt` — `cmake_minimum_required`, `project()` name and languages, `add_executable` / `add_library` targets
- **Bazel / Buck**: `WORKSPACE` / `WORKSPACE.bazel`, `BUILD` / `BUILD.bazel` files (Bazel — workspace name, external deps, primary build and test targets); `BUCK` files, `.buckconfig` (Buck / Buck2)
- **Pants / Earthly**: `pants.ini` / `pants.toml` with `BUILD` files (Pants build system); `Earthfile` (Earthly — combines Dockerfile and Makefile semantics; extract targets and `FROM` references)
- **Ant**: `build.xml` — extract target names and dependencies; note if used alongside Maven/Gradle (legacy hybrid)
- **just / Task / Makefile alternatives**: `justfile` / `Justfile` (just runner recipes), `Taskfile.yml` / `Taskfile.yaml` (Task runner targets)
- **Version pinning files** (record the pinned version and tool): `.tool-versions` (asdf — may pin multiple runtimes), `.nvmrc` / `.node-version` (Node.js), `.python-version` (pyenv), `.ruby-version`, `.go-version`, `rust-toolchain.toml`, `global.json` (.NET SDK), `.java-version` (jenv)
- **Dev containers**: `.devcontainer/devcontainer.json` or `.devcontainer.json` — base image, features, port forwards, VS Code extensions (authoritative record of the expected development environment)

## CI/CD pipelines and cloud delivery

Extract pipeline structure, deployment targets, environment strategy, and secrets surface; these are high-value signals for factor-review applicability (factors 05, 10, 14, 15) and persona synthesis:

- **GitHub Actions**: `.github/workflows/*.yml` / `*.yaml` — extract trigger events (`on:`), job names and runner labels, matrix strategy (OS/version combinations), environment and environment protection rules, secrets references (`${{ secrets.* }}`), reusable workflow calls (`uses:`), artifact upload/download steps, deployment steps and target environments
- **GitLab CI**: `.gitlab-ci.yml` — stages, job definitions, `extends:` inheritance, `include:` external configs, environment deployments (`environment:` keyword), `artifacts:` paths and expiry, cache configuration, protected variable references, `needs:` DAG dependencies
- **Jenkins**: `Jenkinsfile` (declarative or scripted pipeline — see Groovy above); also scan for `jenkins/` or `ci/jenkins/` shared library definitions; note `@Library` imports and agent labels
- **CircleCI**: `.circleci/config.yml` — orb imports (reveal external integrations), workflow graph, executor types (Docker/machine/macOS), context references (secrets surface), approval gates
- **Azure Pipelines**: `azure-pipelines.yml` / `.azure/pipelines/*.yml` — stages, jobs, task steps, variable group references, environment deployments, service connection names, agent pool labels
- **Bitbucket Pipelines**: `bitbucket-pipelines.yml` — pipeline triggers (branches, tags, PRs), step images, service containers, deployment environments, caches
- **Travis CI**: `.travis.yml` — language, version matrix (`rvm`, `go`, `node_js`, `python`), `before_install` / `install` / `script` / `deploy` sections, provider deployments
- **TeamCity**: `.teamcity/settings.kts` (Kotlin DSL project settings) or XML under `.teamcity/` — build configurations, triggers, artifact rules
- **Drone CI**: `.drone.yml` — pipeline kind, steps, services, trigger conditions, secrets
- **ArgoCD**: Application CRD yamls (`apiVersion: argoproj.io/v1alpha1, kind: Application`), `apps/` app-of-apps pattern, `ApplicationSet`; extract source repo, target cluster/namespace, sync policy
- **Flux (GitOps)**: `flux-system/` bootstrap directory, `Kustomization` resources, `HelmRelease` resources, `GitRepository` / `OCIRepository` sources — extract reconciliation intervals and health checks
- **Tekton**: `tekton/` directory with `Pipeline`, `Task`, `PipelineRun`, `TriggerTemplate` resources
- **Skaffold**: `skaffold.yaml` — profiles, build artifacts (Docker or Jib), deploy methods (kubectl/helm/kustomize), port-forward config; primarily used for inner-loop dev-to-cluster workflows
- **Tilt**: `Tiltfile` — local dev orchestration; extract services managed, live-update rules, resource dependencies
- **Helm charts**: `Chart.yaml` (chart name, version, appVersion, type — `application` vs `library`), `values.yaml` (default config — extract image repository/tag pattern, replica counts, resource limits, ingress config, secrets references), `templates/` (resource kinds generated), `Chart.lock` / `charts/` (chart dependencies); for umbrella/parent charts note sub-chart structure; flag if the repo both builds the app and packages the chart vs chart-only repos
- **Kustomize**: `kustomization.yaml` — resources, patches, images (image tag replacement), namespace, commonLabels; note overlay structure (`base/`, `overlays/dev/`, `overlays/prod/`)
- **Cloud artifact registries and image references**: scan CI configs, `docker-compose.yml`, Helm `values.yaml`, and Kubernetes manifests for image references — note registry domains (ECR, GCR/Artifact Registry, ACR, Docker Hub, GHCR, Quay) as cloud-provider and trust-boundary signals; record any `latest` or unpinned image tags encountered so `seed-070` can classify reliability/reproducibility risk

## Cloud scripting and platform tooling

Detect cloud-provider CLI usage, serverless/FaaS runtimes, IaC scripting layers, secrets management, and observability config; each is a signal for factor-review applicability (factors 03, 04, 10, 14, 15) and trust-boundary mapping:

- **Azure IaC and scripting**: `*.bicep` files (Bicep — Azure-native IaC; extract `targetScope`, resource types, module references), `azuredeploy.json` / `template.json` with `"$schema": "...deploymentTemplate"` (ARM templates), `az` CLI invocations in shell scripts or CI steps, `Connect-AzAccount` / `Az.*` cmdlets in PowerShell scripts, `az bicep` or `az deployment group create` calls, `AzurePublishSettings` or `azure.json` service principal files
- **Google Cloud scripting**: `cloudbuild.yaml` / `cloudbuild.json` (Cloud Build — extract steps, substitutions, artifact destinations), `gcloud` CLI invocations in Makefiles or CI, `app.yaml` (App Engine — runtime, handlers, scaling), `cron.yaml` (App Engine scheduled tasks), `dispatch.yaml` (App Engine routing), Deployment Manager configs (`*.yaml` with `resources:` + `type: gcp-types/...`), `google-cloud-*` / `google-api-*` SDK dependencies
- **AWS scripting**: `aws` CLI invocations in shell scripts, Makefiles, or CI steps (extract service names — `s3`, `lambda`, `ecs`, `eks`, `secretsmanager`, `ssm`, `cloudwatch`); `.aws/config` patterns (note if committed — security signal); `boto3` / `botocore` (Python AWS SDK), `@aws-sdk/*` (JS), `software.amazon.awssdk:*` (Java SDK v2); note cross-account or cross-region patterns
- **Serverless and FaaS runtimes**:
  - *Azure Functions*: `host.json` (runtime version, extension bundle), per-function `function.json` (bindings — trigger type, input/output), `local.settings.json` (note if committed — security signal), `AzureFunctions` package references
  - *Google Cloud Functions / Cloud Run*: `functions_framework` in Python requirements or `@google-cloud/functions-framework` in npm; `Dockerfile` with `CMD` invoking a Cloud Run service; `service.yaml` with `apiVersion: serving.knative.dev`
  - *Cloudflare Workers / Pages*: `wrangler.toml` / `wrangler.json` (worker name, compatibility date, bindings — KV namespaces, Durable Objects, R2 buckets, D1 databases, AI bindings); `wrangler` in package.json scripts
  - *AWS Lambda (non-SAM/Serverless)*: `handler` references in CloudFormation or CDK, `Runtime:` field in function definitions, Lambda Layers references, `LAMBDA_TASK_ROOT` in Dockerfiles
  - *Vercel*: `vercel.json` (rewrites, redirects, edge function config, build commands, environment variable references), `.vercel/` directory
  - *Netlify*: `netlify.toml` (build command, publish dir, redirects, edge functions, function directory), `netlify/functions/` or `netlify/edge-functions/`
  - *Deno Deploy*: `deno.json` / `deno.jsonc` (import maps, tasks, lint/format config), `deno.lock`
  - *SST (Ion)*: `sst.config.ts` — extract app name, providers, linked resources
- **Secrets and configuration management**:
  - *HashiCorp Vault*: `vault` CLI invocations in scripts or CI, `VAULT_ADDR` / `VAULT_TOKEN` env var references, `vault` provider in Terraform, `vault.hashicorp.com/agent-inject` annotations in Kubernetes pod specs
  - *SOPS*: `.sops.yaml` (key provider config — KMS, age, PGP), `*.enc.yaml` / `*.enc.json` / `*.enc.env` encrypted files, `sops` invocations in CI or Makefiles
  - *External Secrets Operator*: `ExternalSecret`, `ClusterExternalSecret`, `SecretStore`, `ClusterSecretStore` Kubernetes CRD kinds — extract provider type (AWS, GCP, Azure, Vault, Doppler)
  - *Doppler*: `doppler.yaml` (project/config mapping), `doppler run` invocations in scripts or CI
  - *AWS SSM / Secrets Manager*: `aws ssm get-parameter` / `aws secretsmanager get-secret-value` in scripts; `ssm:GetParameter` in IAM policies; `{{resolve:ssm:...}}` / `{{resolve:secretsmanager:...}}` in CloudFormation
  - *Azure Key Vault*: `@Microsoft.KeyVault(...)` in App Service config references, `azure/keyvault-secrets` SDK, `SecretClient` usage, Key Vault references in Bicep / ARM
- **Observability and APM platform config**:
  - *Datadog*: `datadog.yaml` (agent config), `DD_*` env vars in Docker or CI, `dd-trace-*` / `ddtrace` dependencies, `datadog_checks/` (custom checks), Datadog provider in Terraform
  - *Grafana / Prometheus*: `prometheus.yml` (scrape configs, alerting rules path), `alertmanager.yml` (route and receiver config), `grafana/provisioning/` (datasource and dashboard YAML — note if dashboards are code-managed), `recording_rules.yml`
  - *OpenTelemetry Collector*: `otelcol-config.yaml` / `otel-collector-config.yaml` (receivers, processors, exporters, pipelines), `otelcol-contrib` image references, `OTEL_*` env var patterns in app config
  - *New Relic*: `newrelic.yml` / `newrelic.js` agent config, `NEW_RELIC_LICENSE_KEY` env var, `newrelic-*` dependencies
  - *PagerDuty / alerting*: `alertmanager.yml` with PagerDuty receiver, `pagerduty_*` Terraform resources, webhook endpoint patterns in CI or monitoring config

## Project framework and platform detection

Scan dependency manifests and config files to identify which frameworks, platforms, and runtime models are in use. Record detected frameworks as archetype signals in `docs/repo-index.md` and `docs/repo-profile.json`; they inform domain boundaries, factor-review applicability, and persona synthesis:

- **Low-code / no-code / enterprise platforms**:
  - *Microsoft Power Platform / PowerApps*: `.msapp` files (canvas app binary — ZIP archive), unpacked canvas app source via `pac` CLI (`CanvasManifest.json`, `*.fx.yaml` / `*.pa.yaml` Power Fx formula files, `Connections/`, `DataSources/`, `Assets/`), Power Platform solution structure (`solution.xml`, `customizations.xml`, `.cdsproj` Dataverse project file, `CanvasApps/`, `CloudFlows/` with Power Automate flow JSON, `Entities/`, `WebResources/`), `pac` CLI config, environment `.env` with `POWER_PLATFORM_*` variables — note whether the repo uses source-control integration (`pac solution unpack`) or stores binary `.msapp` directly
  - *Salesforce*: `sfdx-project.json` (SFDX / Salesforce DX project), `force-app/` directory structure (`main/default/classes/`, `lwc/`, `aura/`, `objects/`, `flows/`), `.salesforceignore`, `package.xml` (metadata manifest), `scratch-def.json` (scratch org definition)
  - *ServiceNow*: `sn-project.yaml`, `now.json`, `sys_script` or `sys_ui_script` XML files in a scoped application folder structure
  - *Mendix*: `.mpr` project file (Mendix Studio Pro project)
  - *OutSystems*: `.oap` / `.osp` files, `OutSystems.runtime.core` dependencies

- **Web / mobile frontend frameworks** (detect from dependency manifests — `package.json`, `pom.xml`, `build.gradle`, etc.):
  - *React*: `react` dependency; distinguish CRA (`react-scripts`), Vite, Next.js (`next`), Remix, Gatsby
  - *Vue*: `vue` dependency; note Vue 2 vs Vue 3, Nuxt (`nuxt`), Vite vs Vue CLI
  - *Angular*: `@angular/core`, `angular.json` workspace config, `nx.json` when using Nx
  - *Svelte / SvelteKit*: `svelte`, `svelte.config.*`, `@sveltejs/kit`
  - *Astro*: `astro.config.*`, `astro` dependency
  - *Ember*: `ember-cli-build.js`, `ember-source`
  - *React Native / Expo*: `react-native`, `expo` dependency, `app.json` / `app.config.*`, `metro.config.*`
  - *Flutter*: `pubspec.yaml` with `flutter` SDK (also covers Dart projects — note `dart` SDK constraint, `pub.dev` dependencies)
  - *Ionic / Capacitor / Cordova*: `ionic.config.json`, `capacitor.config.*`, `config.xml` with Cordova namespace
  - *Xamarin / .NET MAUI*: `.csproj` with `Microsoft.Maui.*` or `Xamarin.*` package references

- **Backend service frameworks** (detect from dependency manifests):
  - *Java / Kotlin*: Spring Boot (`spring-boot-starter-*`), Micronaut (`micronaut-*`), Quarkus (`quarkus-*`), Vert.x (`vertx-*`), Helidon (`helidon-*`), Jakarta EE (`jakarta.*`)
  - *Scala*: Play Framework (`play` in `plugins.sbt`), Akka / Pekko (`akka-actor`), ZIO (`zio`), http4s, Tapir
  - *Python*: Django (`django` in requirements — note `manage.py`, `settings.py`, `urls.py`), FastAPI (`fastapi`), Flask (`flask`), Starlette, Litestar, Tornado
  - *Ruby*: Rails (`rails` in Gemfile — note `config/routes.rb`, `app/` structure), Sinatra, Hanami
  - *C# / .NET*: ASP.NET Core (`Microsoft.AspNetCore.*`), Blazor (`Microsoft.AspNetCore.Components`), gRPC (`Grpc.AspNetCore`), Minimal API (no controller base, `MapGet`/`MapPost` in `Program.cs`)
  - *Go*: Gin (`gin-gonic/gin`), Echo, Fiber, Chi, net/http stdlib, gRPC (`google.golang.org/grpc`)
  - *Rust*: Actix-web (`actix-web`), Axum (`axum`), Rocket (`rocket`), Warp, Tonic (gRPC)
  - *Node.js*: Express (`express`), NestJS (`@nestjs/core`), Fastify, Hapi, Koa, tRPC
  - *PHP*: Laravel (`laravel/framework`), Symfony (`symfony/*`), Slim, WordPress (`wp-includes/`)

- **Data, ML, and analytics frameworks**:
  - *Machine learning*: TensorFlow / Keras (`tensorflow`), PyTorch (`torch`), scikit-learn (`scikit-learn`), JAX (`jax`), Hugging Face (`transformers`, `datasets`)
  - *Data pipeline / ETL*: Apache Airflow (`apache-airflow`, `dags/` directory), dbt (`dbt_project.yml`, `models/` directory), Prefect, Dagster, Luigi
  - *Big data*: Apache Spark (`pyspark`, `spark-core`, `org.apache.spark`), Flink (`apache-flink`), Kafka Streams (`kafka-streams`)
  - *Data science*: pandas, NumPy, SciPy in requirements — note alongside Jupyter notebooks for data-pipeline vs exploration intent

- **Infrastructure, IaC, and cloud frameworks**:
  - *Terraform*: `*.tf` files, `terraform.tfvars`, `versions.tf` (required provider versions), `.terraform.lock.hcl`, `terraform.tfstate` (note if state is committed — security signal)
  - *Pulumi*: `Pulumi.yaml` (runtime, main entry), `Pulumi.*.yaml` (stack configs)
  - *AWS CDK*: `cdk.json`, `aws-cdk-lib` in `package.json` or `requirements.txt`
  - *AWS CloudFormation / SAM*: `template.yaml` with `AWSTemplateFormatVersion` or `Transform: AWS::Serverless`
  - *Serverless Framework*: `serverless.yml` / `serverless.ts`
  - *Ansible*: `playbook.yml`, `site.yml`, `inventory/`, `roles/` directory
  - *Helm*: `Chart.yaml`, `values.yaml`, `templates/` — note whether chart is an app chart or library chart
  - *Kubernetes manifests*: `k8s/`, `kubernetes/`, `deploy/`, or `manifests/` directories with `*.yaml` containing `apiVersion:` and `kind:` — extract resource kinds (Deployment, StatefulSet, DaemonSet, CronJob, Ingress, HPA) and namespace strategy
  - *OpenShift*: `DeploymentConfig`, `Route`, `BuildConfig`, `ImageStream` kinds in manifests; `oc` CLI references in Makefiles or CI scripts; `.openshift/` directory; OpenShift-specific operators
  - *Docker*: `Dockerfile` / `Dockerfile.*` — extract `FROM` base image and tag, multi-stage build stages, `EXPOSE` ports, `ENTRYPOINT` / `CMD`; `docker-compose.yml` / `compose.yml` — extract services, port mappings, volume mounts, dependency graph, environment variable patterns; `.dockerignore`; note whether images are built in CI or committed
  - *Dev containers*: `.devcontainer/devcontainer.json` — base image, features, lifecycle scripts, forwarded ports (authoritative dev environment definition)
  - *Nix*: `flake.nix`, `shell.nix`, `default.nix` — note if used for reproducible dev environments or deployment

## Testing tools and frameworks

Identify test infrastructure in use; feeds QA reviewer scope, factor-review applicability (factor 05, 10), and build-and-verification docs:

- **Unit and integration test frameworks** (detect from dependency manifests and config files):
  - *Java / Kotlin / Scala / Groovy*: JUnit 4 (`junit:junit`), JUnit 5 / Jupiter (`junit-jupiter-*`, `junit-platform-*`), TestNG (`testng`), Spock (`spock-core` — Groovy-based BDD), Kotest (Kotlin), ScalaTest / MUnit (Scala), Mockito (`mockito-core`), MockK (Kotlin), AssertJ, Hamcrest; note `@SpringBootTest` for Spring integration tests
  - *Python*: pytest (`pytest` in requirements — extract `pytest.ini` / `pyproject.toml [tool.pytest.ini_options]`, note fixtures and plugins like `pytest-django`, `pytest-asyncio`, `pytest-cov`), unittest (stdlib), nose2, Hypothesis (property-based)
  - *JavaScript / TypeScript*: Jest (`jest.config.*`, `@jest/core`), Vitest (`vitest.config.*`), Mocha + Chai, Jasmine, AVA, Tape; note `@testing-library/*` for component testing
  - *Go*: built-in `testing` package (`*_test.go` files), Testify (`github.com/stretchr/testify`), Ginkgo + Gomega (BDD), `go test -race` flag in CI (concurrency testing signal)
  - *Rust*: built-in `#[test]` / `#[cfg(test)]`, Proptest / QuickCheck (property-based), `cargo-tarpaulin` (coverage), `mockall`
  - *C# / .NET*: xUnit (`xunit`), NUnit (`NUnit`), MSTest (`Microsoft.VisualStudio.TestPlatform`), Moq, NSubstitute, FluentAssertions; note `[Fact]` vs `[Theory]` for parameterized tests
  - *C / C++*: Google Test / Google Mock (`gtest`, `gmock`), Catch2, doctest, CppUTest, Boost.Test; note `ctest` integration in `CMakeLists.txt`
  - *Swift / iOS*: XCTest (`XCTestCase` subclasses), Quick + Nimble (BDD), `XCUITest` (UI automation)
  - *Ruby*: RSpec (`rspec` in Gemfile), Minitest, FactoryBot, VCR (HTTP interaction recording)
  - *PHP*: PHPUnit (`phpunit/phpunit`), Pest, Mockery
- **Browser and UI automation** (detect from dependencies, config, or test directory structure):
  - *Selenium*: `selenium-java`, `selenium-webdriver` (npm), `selenium` (Python pip), `Selenium.WebDriver` (NuGet) — extract WebDriver initialization patterns and note if local drivers or Grid/cloud services (Sauce Labs, BrowserStack) are used; look for `WebDriverManager` or `selenium-manager`
  - *Playwright*: `@playwright/test` (npm), `playwright` (Python pip), `Microsoft.Playwright` (NuGet) — extract browser targets (Chromium, Firefox, WebKit), base URL, test directory
  - *Cypress*: `cypress` dependency, `cypress.config.*` — extract `baseUrl`, custom commands in `cypress/support/`, note if Component Testing mode is enabled
  - *WebdriverIO*: `@wdio/cli`, `wdio.conf.*` — extract services (Selenium, Chrome, Appium), capabilities
  - *Puppeteer*: `puppeteer` / `puppeteer-core` — often used for scraping or screenshot testing
  - *Appium*: `appium` dependency or `io.appium:java-client` — mobile UI automation; extract platform capabilities (iOS/Android)
  - *Robot Framework*: `robotframework` Python package, `*.robot` test files — extract libraries used (SeleniumLibrary, Browser, RequestsLibrary)
- **API and contract testing**:
  - *REST Assured* (Java): `rest-assured` dependency — extract base URI patterns and authentication config
  - *Pact* (consumer-driven contracts): `pact-jvm-*`, `@pact-foundation/pact` (npm), `pact-python` — note provider and consumer names; flag as a strong factor-13 (API first) signal
  - *Postman / Newman*: `newman` in package.json scripts or CI, `*.postman_collection.json` / `*.postman_environment.json` files
  - *K6 / Gatling / Locust / JMeter*: `k6` in CI scripts or `k6/` directory, `gatling-charts-highcharts` dependency, `locustfile.py`, `*.jmx` JMeter plan files — these are load/performance testing signals (factor-14)
  - *WireMock / MockServer*: `wiremock` dependency or `__files/` + `mappings/` directory — note stubs and whether used in unit or integration test scope
- **Code coverage and quality gates**: `jacoco` plugin in Gradle/Maven (Java coverage), `.coveragerc` / `coverage.xml` (Python), `lcov.info` or `.nyc_output/` (JS), `tarpaulin` (Rust), `coverlet` (C#) — note whether coverage thresholds are enforced in CI

## Design and UI surface (stack-specific patterns)

Scan for design artifacts and component infrastructure; the output of this scan is the `design_evidence` schema recorded in `docs/repo-profile.json` under `design_system`. The schema itself lives in `seed-030` task 7 as the named output contract; this section lists the stack-specific detection patterns that feed the schema:

- **Web projects (React, Angular, Vue, Svelte, Next.js, Remix, Astro, and similar)**:
  - *Design tokens*: `tokens.json`, `design-tokens.json`, `tokens/` directory, `*.tokens.json`, Style Dictionary source files, Theo token files, Figma Tokens plugin output, or CSS/SCSS custom property files with a `--color-` / `--spacing-` / `--font-` naming convention — set `has_design_tokens: true` and record paths in `token_files`
  - *Component library*: `shadcn/ui` (`.components.json`), Radix UI (`@radix-ui/*` in `package.json`), MUI / Material UI (`@mui/material`), Ant Design (`antd`), Chakra UI (`@chakra-ui/react`), Headless UI (`@headlessui/*`), Flowbite, Bootstrap — set `has_component_library: true` and record library name in `component_library`
  - *Storybook*: presence of `.storybook/` directory **and** at least one `*.stories.tsx`, `*.stories.ts`, `*.stories.jsx`, or `*.stories.js` file anywhere in the repo — set `has_storybook: true` and record `.storybook/` config dir in `storybook_config_path`; record `false` if either condition is unmet
  - *Typography system*: `@fontsource/*` packages, Google Fonts import in CSS, custom `fontFamily` in Tailwind `theme.extend`, or a dedicated `typography.ts` / `fonts.ts` file — set `has_typography_system: true` and describe the source in `typography_source`
  - *CSS methodology* (record as a **list**, not a single string, to handle projects using multiple approaches): `tailwind` (presence of `tailwind.config.*`), `css-modules` (`.module.css` / `.module.scss` files), `styled-components` (`styled-components` in package.json), `emotion` (`@emotion/react` or `@emotion/styled`), `sass` (`.scss` / `.sass` files), `vanilla-extract` (`@vanilla-extract/css`), `linaria` (`@linaria/core`), `plain-css` (no framework detected) — populate `detected_methodology` list
  - *Source roots*: derive `ui_roots` from `src/`, `app/`, `pages/`, `components/`, or framework-specific roots (`app/` in Next.js app router, `src/app/` for Angular) — list directory paths relative to the repo root
- **Android projects**:
  - *Design tokens*: `res/values/colors.xml`, `res/values/dimens.xml`, `res/values/styles.xml`, `res/values/themes.xml` — set `has_design_tokens: true`; record paths in `token_files`
  - *Component library*: Material Components for Android (`com.google.android.material:material`) in `build.gradle` / `build.gradle.kts` — set `has_component_library: true`, `component_library: "Material Components for Android"`; check also for Jetpack Compose Material (`androidx.compose.material3`) — record `component_library: "Compose Material 3"` when found
  - *Storybook*: `false` (no native Android Storybook support; set `has_storybook: false`)
  - *CSS methodology*: record `detected_methodology: ["xml-layouts"]` for View-system projects or `detected_methodology: ["jetpack-compose"]` when `androidx.compose.*` is the primary UI layer
  - *Source roots*: `app/src/main/java/`, `app/src/main/kotlin/`, `app/src/main/res/` — populate `ui_roots`
- **Flutter projects**:
  - *Design tokens*: `lib/theme/` directory with `theme.dart`, `colors.dart`, `typography.dart`, or a `ThemeData` definition — set `has_design_tokens: true`; record paths in `token_files`
  - *Component library*: Flutter Material (`material` in `pubspec.yaml` flutter SDK entry), Cupertino widgets (`cupertino_icons` package), or third-party (`flutter_bloc`, `get`, `riverpod` not component libraries — look for `get_widget`, `flutter_easyloading`, `flutter_staggered_grid_view`) — record in `component_library`
  - *Storybook*: `false` (no Flutter Storybook; check for `widgetbook` package as a functional equivalent — if present, note in `storybook_config_path` as `widgetbook/`)
  - *CSS methodology*: record `detected_methodology: ["flutter-material"]` or `detected_methodology: ["flutter-cupertino"]` based on dominant widget usage
  - *Source roots*: `lib/` and `lib/widgets/` — populate `ui_roots`
- **React Native projects**:
  - *Design tokens*: `src/theme/`, `app/theme/`, `theme.ts`, `tokens.ts` — set `has_design_tokens: true`; record paths in `token_files`
  - *Component library*: React Native Paper (`react-native-paper`), NativeBase (`native-base`), NativeWind (`nativewind`), Gluestack UI (`@gluestack-ui/*`) — record in `component_library`
  - *Storybook*: `@storybook/react-native` in package.json — set `has_storybook: true` and record config dir; otherwise `false`
  - *CSS methodology*: record `detected_methodology: ["react-native-stylesheet"]` (default StyleSheet API) or `detected_methodology: ["nativewind"]` when NativeWind is present
  - *Source roots*: `src/`, `app/`, `components/` — populate `ui_roots`
- **Swift / SwiftUI / AppKit / UIKit projects**:
  - *Design tokens*: `*.xcassets/Colors.xcassets` or named color sets under `*.xcassets/`, a Swift file with a `Color` extension or `Colors.swift` / `Theme.swift` defining named colors or spacing constants — set `has_design_tokens: true`; record paths in `token_files`
  - *Component library*: SwiftUI standard library (no package needed — detect from `.swift` files importing `SwiftUI`), UIKit (files importing `UIKit`), AppKit (files importing `AppKit`) — record the dominant framework name in `component_library`
  - *Storybook*: `false` (no Swift/Apple-native Storybook; set `has_storybook: false`)
  - *CSS methodology*: record `detected_methodology: ["swiftui"]` when SwiftUI is the dominant UI layer; `detected_methodology: ["uikit"]` or `detected_methodology: ["appkit"]` for the older toolkits; list multiple if mixed
  - *Source roots*: Swift source directories under the app target (`<AppTarget>/Sources/`, `<AppTarget>/Views/`, `Sources/<TargetName>/`) — populate `ui_roots`
- **No-UI / CLI-only projects**: when none of the above signals are found, set `detected: false` and `ui_roots: []`; do not populate component-library or methodology fields

**Mode evidence bar (1p799) — distinguish a declared external source-of-truth from in-repo CSS.** The mode verdict (`bootstrap` / `extract-mirror` / `adopt` / `ambiguous`) is decided by `classify_design_system_mode(design_evidence)` (in `wave_lint_lib/design_system_governance_validators.py`), not by judgment. To feed it correctly, the scan must separate a **declared, maintained external design system that owns its own build** from mere in-repo styling. The **adopt / external-reference** bar requires at least one of:

  - *External token package* — a published or packaged token dependency that is the source of truth (e.g. a `@scope/design-tokens`-style dependency in `package.json`, a workspace-published token package, or a vendored package whose tokens are built elsewhere). Record the package identifier in `external_token_package`.
  - *Style-Dictionary / DTCG source + build* — a token **source** directory plus a build that compiles it (a `style-dictionary` / Theo / `token-transformer` config with a build script that generates platform outputs, where the repo treats the source — not the generated output — as canonical). Record the build command/config in `style_dictionary_build`.
  - *Figma library links* — declared Figma library/variable URLs treated as the source of truth (in a design config, a `figma.config.*`, or a documented library link). Record the links in `figma_library_links`.

  Signals that do **NOT** by themselves clear the adopt bar (they are in-repo evidence → `extract-mirror`): CSS/SCSS custom properties (`--color-*` / `--spacing-*`), a `tailwind.config.*` theme, in-repo `theme.ts` / `*.xcassets` / `res/values/*.xml` token files with no external build. **Self-hosting guard:** a repo whose only design evidence is an in-repo `dashboard.css` (Wavefoundry's own shape) must classify as `extract-mirror`, never `adopt`. When evidence is genuinely weak or mixed (something detected but no concrete in-repo evidence and no external source-of-truth), the verdict is `ambiguous` — install/upgrade then asks the operator.
