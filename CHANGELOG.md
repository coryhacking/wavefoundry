# Changelog

All notable changes to this project are documented in this file and in
the individual wave records under [`docs/waves/`](docs/waves/).

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.9.2] - 2026-06-26

### Changed

- **Windows and no-PATH setup guidance leads with `wf`.** Operator-facing install, upgrade, prompt index, framework-operator, dashboard, and install-seed guidance now treats `wf setup` and `wf` subcommands as the primary command surface, with repo-local `wf.cmd` / POSIX shim paths only as no-PATH fallbacks. This closes the guidance hole where agents guessed `python .wavefoundry/bin/wf` on native Windows. Wave 1p7pk / native-Windows field follow-up.

### Fixed

- **Native-Windows MCP stdio framing hardening.** The MCP runner now configures stdin/stdout/stderr to UTF-8 with LF-only newlines before building the server and entering the stdio transport, with stdout/stderr write-through enabled. This keeps Wavefoundry's side of the JSON-RPC stdio boundary byte-stable on native Windows text streams while preserving stderr-only diagnostics. Wave 1p7pk / native-Windows field follow-up.

## [1.9.1] - 2026-06-26

### Fixed

- **Native-Windows MCP server reliability (broken pipe on startup).** The tool venv is now activated **in-process** (`site.addsitedir`) instead of re-execing into the venv interpreter. The re-exec used a subprocess child on Windows (no in-place exec there), which became a second process holding the same stdout pipe the MCP host owns — causing an intermittent broken pipe when the tool list arrives and orphaned processes across reconnects. In-process activation keeps a single host-spawned process on every OS while preserving the byte-identical `command: "python"`. If the venv was built for a different Python `(major, minor)` than the running interpreter (e.g. after a system Python upgrade), normal entries fail loud with a clear "run `wf setup` to rebuild" message, while `wf setup` bypasses activation and recreates the stale tool venv. Wave 1p7pk / 1p802.

## [1.9.0] - 2026-06-25

> **Native Windows (no WSL2), and a single runtime surface.** Every committed launcher and config now names one byte-identical `command: "python"` and runs from a single checkout on macOS, Linux, and native python.org-Windows for CLI hosts. Upgrading retires the nine `.wavefoundry/bin/*` wrappers for one cross-OS `wf` CLI and flips the MCP/hook commands to `python` — so **`setup` / upgrade makes `python` resolve**: a `~/.local/bin/python` → `python3` symlink on macOS/Linux (a symlink, never a shell alias, and never clobbering an existing `python`), native on Windows. Drive the upgrade with `wave_upgrade()` (MCP) or `wf upgrade`. GUI-launched hosts that don't inherit the shell PATH use the printed absolute-venv-path fallback.

### Added

- **Native Windows support without WSL2 (CLI hosts).** The MCP server, hooks, git hooks, and operator CLI run from a single committed checkout on native python.org-Windows. The committed `command` is the byte-identical `python`; the tool venv is activated **in-process** (`site.addsitedir`) so the server stays a single host-spawned process on every OS (no re-exec/child — see *Fixed* above); the venv layout (`Scripts\python.exe` vs `bin/python`) resolves in one place; rendered surfaces are written with byte-fixed line endings on every host; and a repo `.gitattributes` pins shebang-bearing files to LF (and `wf.cmd` to CRLF) so `autocrlf` can't corrupt them.
- **Host-agent TLS CA discovery for model downloads.** The model-fetch trust-store fallback now also honors the host coding agent's own CA bundle — `CODEX_CA_CERTIFICATE` (Codex) and `CLAUDE_CODE_CERT_STORE` (Claude Code) — ahead of `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`, used proactively when set, with the OS platform stores and the `certifi` default as the ordered fallbacks. Verification stays on throughout; only the trusted CA bundle changes.

### Changed

- **One cross-OS `wf` operator CLI replaces the nine `.wavefoundry/bin/*` wrappers.** The bash-only `docs-lint`, `docs-gardener`, `wave-gate`, `update-indexes`, `lifecycle-id`, `wave-dashboard`, `upgrade-wavefoundry`, `setup-wavefoundry`, and `mcp-server` launchers are retired in favor of a single self-bootstrapping `wf` dispatcher behind a `wf` (bash) + `wf.cmd` (Windows) shim pair, so the operator CLI runs identically on macOS, Linux, and native Windows. Use `wf docs-lint`, `wf docs-gardener`, `wf gate open|close|status`, `wf dashboard`, `wf update-indexes`, `wf lifecycle-id`, `wf upgrade`, and `wf setup` (run `wf --help` for the list). `wf setup` stays on the system interpreter pre-symlink so a fresh bootstrap still works.
- **Single runtime execution surface.** Every framework entry point — the MCP server, setup, upgrade, indexer, hooks, git hooks, and the `wf` CLI — self-bootstraps into the shared tool venv through one resolver; no config, launcher, hook body, or spawner re-derives the venv path (enforced by a standing scan). Inner spawns use the running interpreter, so the whole fleet stays on the venv Python.
- **MCP-first upgrade routing.** The upgrade guidance now leads with the `wave_upgrade()` MCP tool (poll/inspect with `wave_upgrade_status()`); the manual procedure is relabeled the no-MCP `wf upgrade` CLI fallback. `wave_upgrade` and `wave_upgrade_status` are now listed in the available-tools surface, and `wave_upgrade_status` is documented in the MCP tool spec.
- **Minor-bump reconciliation recommendation.** A major/minor framework upgrade now surfaces a recommendation to reconcile local surfaces that referenced a changed or retired framework surface (e.g. the `.wavefoundry/bin/*` → `wf` cutover); patch bumps do not surface it.
- **Git hooks, line endings, and the dashboard daemon are cross-OS.** The commit/merge incremental-reindex git hooks route through the shared bootstrap (so native-Windows git fires them), and the local dashboard self-daemonizes in Python with an OS-correct detach instead of a bash-only `nohup`.

## [1.8.1] - 2026-06-23

> **Upgrading runs a one-time graph re-extract.** This release bumps the graph builder version (the call graph's edge/node shape changed), so the graph is re-extracted once after upgrade — graph-only and fast (~10–30 s), not a semantic re-embed (`CHUNKER_VERSION` is unchanged, so there is no re-chunk/re-embed). The upgrade's final index phase now does this automatically alongside the semantic update — version-aware, the same way it handles a chunker bump — so no manual step is required. (If the graph step is skipped, the first graph query still rebuilds it in-process as a safety net.)
>
> **Two behavior changes to know:** CPU index builds now use a smaller default embedding batch (much lower peak memory — see below), and the local dashboard is now a read-only viewer that no longer runs index builds (the `auto_index` setting was removed; index updates come from the post-edit hook, the MCP server, and `wave_index_build`).

### Added

- **Config-key → reader edges.** A code site that reads a config key by literal name now links to that key in the graph — Python `.get("KEY")`/`cfg["KEY"]` against JSON config, and Java/Spring `@Value("${key}")`/`getProperty("key")` against `application.{yml,properties}` keys (`.properties`/`.yml`/`.yaml` now contribute config-key nodes). Bounded to real config surfaces and unique, distinctive keys so ordinary dictionary access does not create false links.
- **Instrumentation targets on advice classes.** OpenTelemetry `TypeInstrumentation` classes carry an `instruments` property naming the types their `typeMatcher()` weaves into — including `namedOneOf` lists and matchers nested in `implementsInterface`/`hasSuperType` — so "what does this advice instrument" is answerable from the graph without hand-searching. Method/argument matchers are excluded.
- **Model downloads fall back to the OS trust store.** When a model download fails TLS verification (`CERTIFICATE_VERIFY_FAILED`) — common behind a corporate proxy whose root CA is in the OS trust store but not the bundled `certifi` — the fetch retries against the OS trust store (honoring a preset `SSL_CERT_FILE`/`REQUESTS_CA_BUNDLE`). Verification stays on throughout; only the trusted CA bundle changes.

### Changed

- **Cross-language call-confidence promotion.** A call that resolves to a unique definition by construction (same-file, or an exact cross-file match) is now recorded at full confidence instead of the heuristic tier, across all languages — sharpening blast-radius and change-risk ranking. Only the confidence label changes; no edge target is altered.
- **Transitive blast-radius confidence.** `code_risk_score` propagates edge confidence along the whole path and reports `transitive_extracted_fraction`, so a blast radius reached only through low-trust edges is discounted rather than over-counted.
- **Much lower memory for CPU index builds.** The embedding forward batch is now per-model and defaults to 32 (down from 256), cutting peak RSS of the CPU embedding pass ~3.5–3.8× at equal-or-better throughput (measured on an M2 Max CPU path). Tune per model via `indexing.code_embed_batch_size` / `docs_embed_batch_size`. The GPU/CoreML path is unaffected. On a constrained low-RAM CPU/WSL2 host this is projected to bring the build well under the memory cap and clear the out-of-memory failure — field-confirmation on such a host is still pending.
- **The local dashboard is a read-only viewer.** It no longer triggers index builds; index freshness is owned by the post-edit hook, the MCP server's background refresh, and `wave_index_build`. The dashboard's build-status panel now reflects those builds.

### Fixed

- **Index health no longer hides a missing code layer.** When code sources are in scope but the code index is absent (e.g. an interrupted or OOM-killed code embedding pass), `wave_index_health` now reports `incomplete` with the code layer in `missing_layers` and a remediation diagnostic, instead of `ready`.
- **Out-of-memory index builds fail loudly.** A code embedding pass killed by the OS OOM-killer now surfaces a clear out-of-memory error with remediation (lower the embedding batch, raise host/WSL2 memory) instead of appearing to succeed.

### Removed

- **Dashboard `auto_index` / `auto_index_delay_seconds` settings.** The dashboard no longer runs index builds, so these settings were removed; index updates are background/MCP-owned.

## [1.8.0] - 2026-06-22

> **Upgrading runs a new factor-review surface check.** The docs gate now verifies the factor-review agent docs: every active factor lane needs its canonical `docs/agents/factor-<nn>-<name>.md`, and any `.claude/agents/` wrapper needs a matching canonical source and valid frontmatter. If your factor surface drifted — wrappers without their sources, or wrappers missing frontmatter — the gate flags it, and the upgrade flow regenerates the missing canonical docs. Repos that run no factor lanes are unaffected.

### Added

- **Design-system foundation.** A machine-readable DTCG design-token contract under `docs/design-system/`, extracted from the dashboard's own styling rather than invented; a no-Node token build pipeline (`build.config.json` + `bin/build-tokens`) that emits CSS, Tailwind, TypeScript, and JSON exports; and a reusable dashboard primitive module the dashboard consumes, with its styling bound to the semantic tokens.
- **Adopt an existing design system in place.** When a target repo already maintains its own design system — a published token package, a Style-Dictionary/DTCG source, or Figma libraries — the contract records a thin reference to it instead of extracting a parallel, drift-prone mirror. The framework defers to what is already there rather than imposing its own structure.
- **Factor-review surface gate.** `docs-lint` turns a previously-silent broken factor-review surface into an actionable finding: an active factor lane missing its canonical doc, an orphaned wrapper with no source, or a wrapper that cannot load as a subagent (no frontmatter). The requirement keys off the active review-lane set; a factor assessed as relevant but with no active lane surfaces as a non-blocking warning, not a hard failure.

### Changed

- **Dashboard navigation polish.** The collapsible sidebar gains clearer dark-mode separation, a smaller theme toggle beside the project title, a `Wavefoundry` version + live-status footer (full build in the tooltip), and a more visible active-section highlight in dark mode.
- **Delegated code work prefers the code-navigation tools.** Code investigation and implementation handed to a subagent must run through a role-typed agent or carry the code-navigation directive in its prompt — subagents inherit the available tools, so reaching for shell search by habit in a subagent is the same defect as in the main thread.
- **Vendor-neutral distribution.** Removed references to external consumer projects from the packaged framework — comments, test fixtures, examples, and the shipped changelog — so the distribution names no project outside Wavefoundry.

## [1.7.3] - 2026-06-19

### Added

- **Antigravity host support.** Wavefoundry renders a workspace-local `.agents/mcp_config.json` for the Antigravity CLI (`render_platform_surfaces --platform antigravity`), auto-detected from `.agents/` and using the portable `.wavefoundry/bin/mcp-server` wrapper (no absolute paths). Antigravity reads the project-root `AGENTS.md` natively, so no separate entry file is rendered.

### Fixed

- **Host-support documentation accuracy.** Corrected the hosts badge and split the MCP-attachment tiers in the docs (auto-rendered config vs. manual stdio paste); added Windsurf and Warp rows to the MCP-enabling tables so every listed host has a resolvable attachment path; described Windsurf accurately (hooks are auto-rendered, MCP attachment is manual).

## [1.7.2] - 2026-06-18

### Added

- **GPU / embedding-provider diagnostic.** `setup-wavefoundry --check-gpu` (and the `wave_gpu_doctor` MCP tool) print what embedding backend this host will actually use — platform, onnxruntime, GPU detection, available ONNX execution providers, the provider that would be selected (with reason), and a CUDA 12/13 ABI-gap check. It runs the same bounded provider probe setup uses, so on Apple Silicon it reports CoreML (not CPU); remote/cloud providers (e.g. Azure) are excluded from the listing.
- **Windows via WSL2 is a supported, documented target.** A single Supported Platforms statement (README + project overview), the WSL2 gotchas that matter (keep the repo on the Linux filesystem, venv lives inside the distro, CUDA via GPU passthrough), and a reproducible smoke checklist. WSL2 runs the identical Linux code path — no separate install.

### Fixed

- **Native-Windows execution hardening (forward-compat).** The Python execution layer now branches correctly on Windows — venv interpreter path and re-exec, process liveness via `tasklist`, background-process detachment flags, codebase-map link separators, text encoding, read-only directory removal, and model-cache integrity checks — with zero change to macOS/Linux/WSL2 behavior. Native Windows is not yet runnable end-to-end; this stages the execution layer ahead of the launcher work.
- **Windows dashboard orphan reconciliation.** The dashboard's stale-process cleanup now works on Windows (a command-line process scan via PowerShell) instead of falling back to bare PID checks, so orphaned dashboards no longer accumulate.

### Changed

- **Generated file paths always use forward slashes.** Every path Wavefoundry writes — secrets-scan findings and the shipped allowlist, reindex reports, agent-surface listings, and the rendered launcher/hook commands — now uses `/` on every OS, so an artifact generated on Windows matches one generated on macOS/Linux.

## [1.7.1] - 2026-06-17

> **Upgrading re-extracts the code graph once.** The graph builder advanced (the determinism fix below changes the emitted edge set), so the first index after upgrading re-extracts the graph from scratch — minutes, not a full semantic rebuild. The semantic (docs/code) index is unaffected. The upgrade flow runs it automatically.

### Fixed

- **`code_ask` no longer answers confidently when it found nothing.** On a zero-signal query (retrieval scores all near zero) it now returns `confidence: low`, adds a "no confident match" gap, and flags the weak citations (`weak: true`) instead of presenting off-topic results as evidence — while still returning them as navigation leads (never empty). When the cross-encoder reranker did not run, confidence is capped (never the old count-based "high"), and the response carries a loud gap naming the degraded vector-only fallback and its cause, so a misconfigured reranker is visible rather than silently lowering answer quality. Citation fidelity is unchanged — every citation still points at a real `file:line`. A capitalized leading question word ("Which…", "Where…", "Tell me about…") is no longer mistaken for a code symbol, which had been inflating off-topic results above the relevance floor and defeating abstention for those phrasings.
- **Code-graph extraction is reproducible.** The same source tree now produces the same graph across rebuilds — cross-file call/reference resolution was order-dependent, so identical input could yield different edge counts (and, downstream, different codebase-map areas) from one rebuild to the next. Resolution is now order-independent with explicit, faithful tie-breaks, and each graph carries an input fingerprint so reproducibility is verifiable. Existing correct bindings are unchanged (no wrong-symbol rebinding).
- **Per-area `AGENTS.md` is found at the project root.** The codebase map's area link and the `wavefoundry://area/{id}` resource now walk up from an area's directory to the nearest ancestor `AGENTS.md`, so a single `AGENTS.md` placed at a project root (the conventional location) serves all of that project's deep areas — previously only a file at the area's exact deep path was linked, leaving conventionally-placed files unlinked.

### Changed

- **`code_ask` surfaces implementing code over prose for code questions.** For "how does X work" / "where is X" questions, reference docs (architecture notes, specs, ADRs, plans, journals) are down-weighted so the implementing source ranks above prose — including above a stale spec — while docs still appear as secondary context (a down-weight, not an exclusion).
- **`code_ask` recovers cross-file and enumeration answers.** Cross-file structural neighbors (callers/readers/importers) that semantic search missed are now merged into the citations (flagged `from_graph`), not just listed separately, so a cross-file chain reaches the answer. Enumeration questions ("which/all X are …") widen retrieval and carry a gap noting the list is a ranked sample that may be incomplete, routing exhaustive enumeration to the exact-search tools instead of implying completeness.
- **Faster reranking.** The cross-encoder reranker now uses a batch sized to the query-time candidate pool rather than the embedder's index-time batch, cutting wasted padding — roughly a third faster per query on Apple Silicon with identical ranking output.

## [1.7.0] - 2026-06-17

### Added

- **Codebase map.** A generated, read-only orientation map of the project's own codebase at `docs/references/codebase-map.md` — bounded areas (domain/package/directory) with their key files, entry points, and `code_*` drill-in handles, built offline from the index. It scales from a small repo (compact, near-flat) to a large monorepo (bounded top tier with leveled drill-down) and acts as the index to the index: it routes you to the right area, then the code tools take over. Served as the `wavefoundry://codebase-map` MCP resource.
- **Per-area context.** Major subsystems carry a vendor-neutral `AGENTS.md` (local conventions, gotchas, intent) that the map links and the index surfaces in `code_ask`/`docs_search` when you work in that area. During inventory the agent now authors a grounded initial draft for major areas (humans refine), and upgrades backfill it. Read a specific one via the `wavefoundry://area/{area_id}` MCP resource.
- **Vendored and generated code is kept out of orientation.** The map excludes bundled third-party and generated code from its areas, key files, and drill-in hubs — driven by `docs/repo-profile.json` `vendored_paths` globs, `.gitattributes` `linguist-vendored`/`linguist-generated`, and generated-code detection — so a cold-start agent lands on the product, not on a dependency. Excluded trees stay fully searchable via the `code_*` tools.
- Code-reviewer maintainability and dead-code review mode for surfacing unused or over-complex code during review.
- Session-stop context capture and a framework-config review prompt for keeping long sessions and project config honest.

### Changed

- **TS/JS symbol extraction is faithful.** Interface and object type members and type aliases are no longer mislabeled as functions, and anonymous-function and route-path junk symbols are no longer emitted as graph nodes, so entry-point lists and the map reflect real callables. Consumer graphs re-extract automatically on upgrade.
- **Codebase-map clustering is reproducible and cohesive.** Community detection is seeded for stable results across rebuilds, cross-directory grab-bag areas are split, opaque structural and version directory names (`v1`, `shared`, …) are qualified by a distinctive ancestor, and same-package type-only files collapse into one area. Consumer graphs re-cluster automatically on upgrade.
- **Single dashboard sidecar.** The dashboard's two state files were merged into one lock file that also holds the startup metadata.

### Fixed

- **Dashboard process lifecycle.** `start`/`stop`/`restart` now reconcile against the actual running processes (by command line) instead of trusting a recorded PID: no more orphan dashboards accumulating across restarts, no more climbing ports, and a killed dashboard is no longer reported as still running. The upgrade path's dashboard detection is hardened the same way.
- Index freshness signals are reported more accurately during long sessions.

## [1.6.2] - 2026-06-15

### Fixed

- **The secret scanner no longer reads files outside its scope.** Framework runtime artifacts — the local index (LanceDB segments), caches, logs, and built packs — are excluded before any file is read, in every project. When the working tree isn't a clean git checkout (so file selection falls back to a directory walk), the scanner now honors `.gitignore` via `git check-ignore` instead of sweeping in ignored files. Versioned shared objects (`libfoo.so.13`) are now recognized as binary and skipped. This removes the slow docs-gate scans previously seen on repositories that weren't a usable git worktree; detection of secrets in real source files is unchanged.

## [1.6.1] - 2026-06-15

### Changed

- **Secret findings are enforced only at wave close.** The hardcoded-secrets scan still detects and records findings to `docs/scan-findings.json` continuously, but no longer fails `docs-lint`, the post-edit hook, validation, or upgrades — those run in record-only mode. `wave_close` is the single secrets gate: `pending` and `suspected-secret` (and any unrecognized status) hard-block close until classified; a confirmed real secret is **non-blocking** and surfaces a standing reminder on every close listing the project's confirmed secrets; cleared false positives pass. The per-wave `acknowledged_for_wave`/`override_reason` acknowledgment was dropped (legacy entries are tolerated). Only a malformed inline-suppression directive remains a lint error.

### Fixed

- **GPU acceleration no longer fails silently on CUDA 13 hosts.** On an NVIDIA host where `onnxruntime-gpu` (built for the CUDA 12 ABI) cannot load against a CUDA 13 runtime, indexing previously dropped to CPU with no signal. It now surfaces a clear, one-time warning naming the cause and the remediation — build `onnxruntime-gpu` from source against CUDA 13, or install a CUDA-13 wheel once available (a `.so.13`→`.so.12` symlink does **not** work; CUDA 13's cuBLAS exports different ELF version symbols). The warning fires even when the CUDA provider isn't listed at all. Set `WAVEFOUNDRY_EMBED_PROVIDER=cpu` to silence it and run on CPU intentionally.
- **Secret scanner skips binary and data files by extension.** Known binary/data files (archives, shared objects, LanceDB segments, media, model weights) are now skipped before being read, so repositories with many such files no longer slow the docs gate (previously every file was read for a binary sniff). The existing size, null-byte, and long-line guards still cover files without a recognized extension.

## [1.6.0] - 2026-06-13

> **Upgrading to 1.6.0 forces a full index rebuild.** The embedding models changed — documentation now embeds with `snowflake-arctic-embed-xs` and code with `bge-small-en-v1.5` — and both `CHUNKER_VERSION` and `GRAPH_BUILDER_VERSION` advanced, so the first index build after upgrading re-chunks, re-embeds, and re-extracts the graph from scratch. Expect a full rebuild (minutes, not an incremental update) on the first post-upgrade index. The upgrade flow runs it automatically.

### Changed

- **Nested-type constants are retrievable by their qualified name.** A constant declared inside a type-within-a-type (a Swift `static let` in a nested `struct`/`enum`, or a nested class in other languages) is now chunked under its qualified owner (`Outer.Inner.x`), matching the graph layer — previously it was flattened onto the outermost type. `code_constants` resolves it by the bare leaf, the full qualified name, or any intermediate dotted suffix, and `code_ask` value/where-is questions now surface the declaration (symbol-first injection fires for navigational questions, not just explanatory). The graph-seed extractor also ignores generic decoy words (`value`/`flag`/…) so they don't hijack traversal.
- **Single-index semantic retrieval with split embedding models and a reranker.** The previous two-layer search path is folded into one index. Documentation embeds with `snowflake-arctic-embed-xs` and code with `bge-small-en-v1.5`, each tuned to its content, and a `cross-encoder/ms-marco-MiniLM-L-6-v2` cross-encoder reranks candidates — wired into `code_ask` as the rerank-first path. On Apple Silicon the embedders and reranker run FP16 on a static-shape CoreML graph with an on-disk compile cache under `~/.wavefoundry`; CPU elsewhere.
- **Streaming index build with bounded memory.** A full rebuild streams files through a bounded buffer (chunk → embed → append → flush) instead of materializing every chunk and vector for a layer up front, so peak memory is bounded by the buffer rather than the corpus and progress reports "file N / M". The produced index is identical to the previous batch path. Reindex model loads are cached-first (no Hub round-trip on a warm cache), and an incremental update loads only the embedder for a layer that actually changed.
- **Oversized-file guard in the indexer.** Files larger than a hard cap (default 5 MB) are dropped from the index walk, and files over a tree-sitter parse cap (default 2 MB) skip AST graph extraction — bounding index time on pathological inputs such as a large data dump. Both caps are overridable via `docs/workflow-config.json` (`indexing.max_file_bytes` / `indexing.max_treesitter_parse_bytes`).
- **Portable tracked editor/MCP surfaces.** The rendered hook and MCP-launcher surfaces are committed with project-relative paths instead of absolute author paths, so a fresh clone works for contributors with no per-machine fixups. Install assets are consolidated under `framework/install/` with a discoverability index.
- **Hardware-aware embedding provider selection.** `setup_index.py` now chooses among CUDA, CoreML, explicit named secondary ONNX providers, and CPU fallback using a shared provider policy module. It logs the selected provider and why CPU fallback was used when the active hardware could not be verified as materially faster.

### Added

- **Hardcoded secrets detection.** A Gitleaks-schema TOML ruleset (`.wavefoundry/scan-rules.toml`, seeded from the Gitleaks community rules; operator-overridable at `docs/scan-rules.toml`) drives a pure-Python regex validator in `wave_lint_lib`. Every `docs-lint` run and `wave_scan_secrets` MCP call checks tracked files against the ruleset. Findings are recorded in `docs/scan-findings.json` with a `pending → false-positive / suspected-secret / confirmed-secret` lifecycle: `pending` requires classification, `false-positive` requires multi-user confirmation, and `confirmed-secret` requires operator acknowledgment (wave-scoped, re-acknowledgment required per wave). `wave_close` hard-blocks on any `pending` entry and soft-blocks on any unresolved `suspected-secret` or unacknowledged `confirmed-secret`.
- **`wave_scan_secrets` MCP tool.** On-demand secrets scan with `mode: "incremental"` (default, git-diff scope) or `mode: "full"` (all tracked files). Runs in an isolated subprocess so ProcessPoolExecutor workers and the resource tracker do not bleed into the MCP server process. Auto-escalates to a full scan when the rules hash changes (SHA-256 of both rule files, null-byte separator). Response includes `effective_mode`, `rules_hash_changed`, `escalated_to_full`, `clean`, `elapsed_s`, `total_findings`, `by_status`, `failures_total`, and `failures`.
- **Rules-hash auto-escalation.** Both the indexer path (`scan_secrets.py`) and the MCP path (`run_secrets_scan.py`) compute a SHA-256 hash of the two rule files and persist it in `.wavefoundry/index/scan/scan-state.json`. Any change to either file (framework upgrade, operator edit) triggers a full scan on the next run without operator intervention.
- **Committer-threshold auto-detection for scan-rules.toml.** The required confirmation threshold for reclassifying a `pending` finding is derived from repository committer count (24-month window, all-time fallback): 0–1 committers → 1 confirmation, 2–6 → 2, 7+ → 3.
- **Security-reviewer pre-scope scan step.** `seed-213` (security reviewer) now runs a scan of wave-touched files before entering explicit non-goals, classifies each finding via the heuristic priority order (env-var-read → real-credential → test-fixture → placeholder → ambiguous), and writes or updates entries in `scan-findings.json` before proceeding with the normal review scope.
- **Time-bounded false-positive confirmations.** A `[policy] confirmation_valid_days` window (default `365`; `0` disables) expires stale false-positive confirmations so they must be re-verified yearly. Expired or undated confirmations are ignored for the clear-count (fail-closed) but left in place; re-verifying appends a new dated confirmation rather than mutating the old one.
- **False-positive override and reviewer-count clamp.** A non-empty `override_reason` dismisses a `false-positive` regardless of confirmation count (operator escape, parity with the confirmed-secret acknowledgment path), and the required-confirmation threshold is clamped down to the number of currently-confirmable (recent, non-bot) reviewers so a lone active maintainer is never deadlocked. The clamp never raises the threshold above the configured policy value.
- **JWT expiry awareness.** JWT findings surface a human-readable `exp` claim and mark expired tokens `(EXPIRED)` for triage. Surfacing only — an expired token is still flagged.
- **Full-repo secrets baseline at install and upgrade.** Install and upgrade run one full-tree secrets scan so secrets in untouched files are classified against the current ruleset up front, instead of dribbling out file-by-file across later waves.
- **Resumable upgrade after a docs-gate failure.** When the docs gate fails mid-upgrade (for example on a secrets finding), the upgrade can be resumed after the operator resolves the blocker (`--resume-after-gate`) instead of restarting from scratch; the resume path is idempotent on an already-advanced tree.
- **`scan-findings-format.md` reference doc.** A canonical reference for the `docs/scan-findings.json` schema, the `pending → false-positive / suspected-secret / confirmed-secret` lifecycle, the `[policy]` confirmation contract, and the self-scan/`[allowlist]` self-exclusion. Shipped in the pack and provisioned into every project on install, and refreshed on upgrade.
- **`code_risk_score` MCP tool.** Ranks the symbols in a scope (path, directory, or glob) by how risky they are to change — a composite of upstream blast radius times log-dampened incoming call-degree (`weighted_affected_file_count * log1p(weighted_fan_in)`). Both terms are weighted by call-edge attribution confidence: heuristic name-based edges count fractionally while type-resolved edges count in full, so a ubiquitous accessor name (`getKey`, `getValue`, `toString`) can't top the ranking purely on a name collision with an unrelated symbol. Each result also carries the raw `affected_file_count`/`fan_in` and an `extracted_edge_fraction` so a high-but-mostly-heuristic score is visibly discountable. `fan_out` (what the symbol itself calls) is surfaced as an independent component, not folded into the score. The response carries `score_formula` and `score_components` so the ranking is transparent and re-weightable; `top` caps the result and a candidate-cap guard asks to narrow the scope rather than running an unbounded per-symbol traversal. It ranks *many* symbols across a scope, where `code_impact` sizes *one*.
- **`install-log-format.md` reference doc provisioned to projects.** The install-log row-format and trustworthy-marker reference is now shipped in the pack and provisioned on install / refreshed on upgrade, so the install seeds that point at it resolve in every project instead of dangling (previously the doc existed only in the self-host).
- **Constant retrieval across all languages.** Module-, class-, and type-level constants are now chunked for semantic search and emitted as graph nodes in every supported language, with a function→constant `reads` edge (faithfulness-gated: same-scope or explicitly-imported only, never a coincidental same-name twin). `code_definition` resolves a constant by name, `code_references` lists its readers in a distinct `reads` bucket (not merged into callers), and `code_ask` surfaces constants alongside code. `reads` is opt-in for default graph traversal so a hot constant does not balloon neighbor sets.

### Changed

- **Scan auto-escalation in indexer.** `update_secrets_scan()` escalates to a full scan on scanner-version mismatch, missing findings file, or rules-hash change — previously only version mismatch and missing file triggered escalation.
- **Scanner skips files it should never scan.** Binary files (null-byte sniff), files larger than 5 MB, and individual lines longer than 32 KB are skipped and recorded as skips rather than scanned — bounding scan time and avoiding garbage matches on minified or generated blobs. Default `[allowlist].paths` now also cover common generated artifacts (lockfiles, minified bundles, vendored trees) and binary extensions.
- **Fewer false positives in prose and on structural noise.** The `generic-api-key` rule is scoped in Markdown/docs prose by a path clause plus an entropy ceiling and a prose-shape signal, so ordinary documentation sentences no longer trip it. The global `[allowlist]` `regexes`/`stopwords` value-filters now apply across every rule, suppressing `$VAR`, `{{template}}`, `%FMT%`, `/Users/…`-path and similar structural-noise values. Overlapping matches on the same secret are de-duplicated, and matches on comment lines are flagged for triage rather than auto-suppressed.
- **Tighter redaction of short secrets.** `matched_text` redaction is length-scaled — short values expose at most a 2+2 window and never more than ~40% of characters; the wider 4+4 window applies only at length ≥ 20. Raw secrets are never written to the ledger.
- **Clearer secrets-gate failure handling.** A docs-gate failure on a secrets finding now states which findings block, their status, and how to resolve them, and the upgrade flow routes the operator to the resolution loop before retrying the gate.
- **Project secrets policy is materialized before the first upgrade gate.** The upgrade flow writes `docs/scan-rules.toml` (committer-derived confirmation threshold) before the first docs gate runs, so the common "policy file missing" case can no longer fail the gate. The later editing-pass step is now an audit that only completes the rarer "file exists but lacks the policy key" case.
- **Full-scan reconciliation of stale findings.** A full secrets scan now drops `pending` findings the current ruleset no longer produces — e.g. after a rule or allowlist change has since suppressed them — so a ruleset improvement no longer leaves a phantom `pending` entry blocking `wave_close`. Strictly `pending`-only: operator classifications (`false-positive` / `suspected-secret` / `confirmed-secret`) are never auto-removed, and incremental scans (which re-evaluate only changed files) never prune.
- **Cross-file calls through Python sibling-script loaders now resolve.** Calls reached through the lazy `_load_script("module")` loader idiom — a module obtained via a thin loader wrapper, then called as `loaded.Class.method()` or `loaded.func()` — now resolve to the loaded module's symbols instead of emitting no edge at all. This closes a blast-radius blind spot where heavily-called symbols (reached only through the loader) reported zero incoming calls, so `code_impact` and `code_risk_score` now see their true reach.
- **Ambiguous cross-file receivers are disambiguated by import.** When a method call's receiver type shares its simple name with classes in other packages, the call is now resolved to the class the source file actually imported (using the file's import edges), instead of staying unresolved on the name collision. Applies where a per-type import carries the receiver name — Python `from a import Foo` and Java/Kotlin single-type imports. Unique-name cross-file calls already resolved; this fixes the same-name-collision case.
- **Cross-file method resolution extended to Go, Rust, C#, and same-package Java/Kotlin.** Go methods are keyed by receiver type (`Type.method`), and a package-qualified receiver (`var h foo.Helper`) resolves to the method in the named package — matched by the candidate's package directory, and left external when no project package matches. Rust associated functions (`Bar::build()`) and struct-literal / `::new()` let-bindings resolve to their type. C# calls across namespaces disambiguate by namespace membership — the caller's own declared namespace (read from the file's namespace declarations, so a caller in a nested class resolves correctly) plus its `using` directives. A same-package / same-directory fallback resolves Java/Kotlin/Go receivers used without an import. Every path binds only a unique package- or namespace-faithful candidate and otherwise leaves the call external — it never binds a wrong same-named twin.
- **Cleaner import edges for Rust, Kotlin, Go, Swift, and C.** Import extraction no longer emits junk `external::<keyword>` edges. The grammar root node was being mis-detected as an import (it shares a substring with an import keyword), which regexed entire files into one edge per token; statement keywords such as `import`, `use`, and `as` also leaked. Rust `use` declarations now produce clean dotted module targets with `as` aliases honored.
- **`code_impact` graph mode bounds its edge list.** The `edges` array is capped at `max_results` (with `edges_total` reporting the true count) so a high-fan-in symbol no longer blows the response past the tool's token limit, and the graph-mode `resolved` field is populated instead of returning null.

- **Upgrade lock no longer strands a half-replaced tree.** A docs-gate failure mid-upgrade records the failed phase and leaves a recoverable lock instead of a stuck in-progress marker, so the dashboard and the next upgrade invocation detect and resume the interrupted upgrade rather than reporting a healthy state over a partially-migrated tree.
- **Correct upgrade version resolution and prune reporting.** `from_version` is resolved from the installed framework revision (manifest `framework_revision`, with `VERSION` fallback) consolidated in one place, and the upgrade's prune count is read from the prune step's actual output rather than mis-derived — so the summary reports the real number of removed files.
- **Lifecycle IDs dedup across plans, waves, and ADRs.** ID minting now scans existing plan, wave, and ADR prefixes together when choosing the next available prefix, so a new plan, wave, or ADR can no longer collide with an ID already issued in a sibling family.
- **26 silently-dead secret detectors revived.** The ruleset is Gitleaks-schema (RE2), and 26 of its regexes used syntax Python's `re` rejects — an inline `(?i)` flag placed mid-pattern, and the `\z` end-of-text anchor — so they failed to compile and were silently skipped, leaving their secret types undetected (Adobe, SendGrid, Slack session cookies, Sentry, PlanetScale, Postman, Linear, GoCardless, Facebook page tokens, Alibaba, Authress, and more). A load-time RE2→Python translation shim now adapts these patterns faithfully (inline flags relocated to scoped groups preserving their original scope, `\z`→`\Z`) — applied only to patterns that fail to compile, so the already-valid rules are untouched and the ruleset stays Gitleaks-schema for future imports.

### Removed

- **Canonical-names rename manifest retired.** The `canonical-names.json` rename manifest and its docs-lint alias machinery are removed. `docs/workflow-config.json` must use the canonical keys (`wave_implement`, `wave_review`); docs-lint no longer accepts the legacy spellings, no longer escalates them by version, and no longer warns on retired role slugs. A one-shot convergence migration still rewrites the legacy config keys (`wave_execution` → `wave_implement`, `wave_council_policy` → `wave_review`) to canonical on every upgrade, so existing projects converge automatically; that migration is itself slated for removal at 2.0.0. The runtime `wave_council_policy` reader-fallback is removed. This pulls the previously-published 2.0.0 config-key removal forward. See ADR `1p5be`.

## [1.5.1] - 2026-06-06

### Changed

- **Guru multi-angle research protocol.** Guru now enumerates 2–3 independent angles before retrieval on `explanatory` and `navigational` questions, explicitly falsifies its working hypothesis after initial retrieval, surfaces null results as explicit negative evidence, and names contradictions when angles disagree rather than silently resolving them. Exemptions: single-symbol quick lookups and `instructional` questions. Framing layer around the existing 3-pass structure — passes unchanged.
- **Wave Council and Archetype Council protocol hardening.** Wave Council Phase 2 seats now open with a pre-primer statement (one sentence of independent read + whether the primer confirmed/extended/changed it — explanation mandatory, label alone not valid), explicitly state "No findings in my lane" rather than going silent, and flag same-findings across sequential seats as potentially correlated rather than independent confirmation. Moderator synthesis adds: a pre-primer read quality check (flags verbatim phrase echo of primer framing as contamination signal), a mandatory Recommendations Verdict table with red-team closing reconciliation folded into a single list (every advisory verdicted `fix now` / `defer` / `accept` with rationale and red-team challenge), and a falsification check (condensed on clean PASS, full detail when findings are present). Archetype Council seats declare their axis before reading the artifact; same null-finding, falsification-check, and recommendations verdict requirements apply. Phase 2 seat instructions in both councils are structured as explicit numbered steps with "do not read yet" guards. Both councils specify summary-level output verbosity — seat details internal, operator sees summaries and the recommendations verdict table.

## [1.5.0] - 2026-06-05

### Changed

- **Chunker per-kind size caps.** Doc, seed, JSON, YAML, TOML, HTML, XML chunks now respect the embedder's 512-token budget — previously only code chunks were capped, so the bottom 45-62% of every structured chunk was silently invisible to semantic search. Markdown lists and tables decompose at logical boundaries; section breadcrumbs preserved on every split. `CHUNKER_VERSION` bumped; indexer auto-rebuilds on mismatch.
- **Self-repairing indexer.** Cross-checks `file_meta` against Lance chunks every update and re-chunks drifted files. Closes the legacy mega-chunk pattern that left some files indexed-but-empty until their mtime changed.
- **`Upgrade wave framework` is one step, end-to-end.** Auto-migrates 1.4.x → 1.5.0 (backfills `Role:` in `docs/agents/*.md`, removes orphan `.claude/hooks/pycache-cleanup*` launchers, strips the stale `PostToolUse` row from `.claude/settings.json`). Always runs the index update at the end of the main flow — no separate `--update-index` invocation. Framework version transitions (`CHUNKER_VERSION` / `WALKER_VERSION` / `GRAPH_BUILDER_VERSION`) logged prominently; MCP server reloads in-process after extract. `--dry-run` previews everything with zero filesystem mutations. Supported upgrade floor is now 1.4.0.
- **MCP code-navigation polish.** `code_read` enriched for the read-then-edit flow — range-aware streaming, `read_invocation` hint (exact args for the built-in `Read` tool), `mtime`, `marker_regions`, `edit_governance`, and a `structural` field with containing-symbol + mid-construct flags + clean-range suggestion. Tree-sitter parses share a single LRU cache across all navigation tools — `code_definition` → `code_outline` → `code_callhierarchy` on the same file parses once. `code_keyword` defaults to `limit=50` (matching `code_pattern` / `code_references`); response includes `truncated` and `total_matches_found` when capped. `code_pattern`'s `max_results` parameter renamed to `limit` for cross-tool consistency (alias retained).
- **Auto-Guru routing strengthened.** Pre-flight intent question, positive/negative examples table anchored on the verbatim failure-mode phrase, and a retrieval-intent backstop catching misses the pre-flight skipped. MCP-first rule extends to literal-identifier sweeps across docs, config, and prompts (not only source-code navigation); legitimate shell exceptions (`git status`/`diff`/`log`, byte-level file-state checks, key-presence verification) named explicitly.
- **Drift-convergence lint family.** `docs-lint` warns on retired role slugs (`council-moderator` → `wave-council`; `code-insight-agent` → `guru`) in hand-authored project docs; warns when `docs/workflow-config.json` satisfies a required-keys alias via the legacy spelling (e.g., `wave_council_policy` vs canonical `wave_review`); fails on duplicate seed numeric prefixes; defers all transient Python caches (`__pycache__`, `.pytest_cache`, `.mypy_cache`, etc.) to `.gitignore`. `docs/agents/specialists/` location downgraded from `MUST` to fresh-install convention — established flat-layout repos may keep their existing location. Back-compat preserved everywhere (warnings are informational; returncode unchanged on alias-key usage).
- **Wave MCP tool polish.** Every write-side tool reports post-write `docs-lint` state in `data.lint` (`{clean, error_count, warning_count, first_errors}`); failures don't block the structural write. `wave_create_wave` produces lint-clean output with a pre-populated journal stub. Lifecycle IDs no longer burned by dry_run — `next_available_prefix` and `build_id` gain a `commit: bool` parameter; preview followed by apply returns the same ID.
- **Build & release.** Root `CHANGELOG.md` is now the single canonical release-history source; `build_pack.py` copies it into the pack zip at `.wavefoundry/CHANGELOG.md` so consumers still receive an in-tree changelog on upgrade. `Package Wavefoundry` seed removed from the consumer pack — packaging is wavefoundry-internal; consumer installs auto-prune via MANIFEST-prune. GitHub Release notes prepend an `## Install` block so the install steps appear alongside the download link.
- **JVM and monorepo harnessability detection.** `_audit_harnessability` recognizes JVM build files (`pom.xml`, `build.gradle*`) and source files (`*.java`/`.kt`/`.scala`/`.groovy`) in canonical roots — Spring Boot and JVM-ecosystem projects now report actual type coverage. Monorepo workspace detection added: Nx, Lerna, Rush, pnpm, Bazel, Pants, Buck, npm/yarn workspaces, Cargo workspaces, Maven multi-module POMs.
- **README install walkthrough restructured.** Two-phase shape (Phase 1 harness bootstrap → MCP restart → Phase 2 project discovery) reflects the actual install seeds. Claude Code and Codex CLI recommended as first-install hosts. `For enterprise forks` section names every upstream URL that needs redirecting.
- **Reality-checker routes to the new code-correctness patterns.** `seed-216` (reality-checker) gains a `## State And Assumption Correctness Patterns (Cross-Reference)` section listing the 7 patterns from `seed-221` with their applies-when hints and pointing to `seed-221` for full definitions. Cross-reference, not duplicate — code-reviewer owns the canonical pattern definitions; reality-checker routes assumption-audit findings to them when assumption-falsifiability is the dominant concern.
- **Config-key renames now converge.** `canonical-names.json` sets `removed_in: "2.0.0"` for both `wave_council_policy` → `wave_review` and `wave_execution` → `wave_implement`. `wave_upgrade` runs an unconditional convergence migration in `post_extract` (no `from_version` gate, idempotent) that rewrites legacy keys to canonical in `docs/workflow-config.json`; when both spellings are present, canonical wins and the legacy entry is dropped with its value captured in `.wavefoundry/logs/upgrade-convergence-migration.log` so operators can recover from the log without consulting git history. Dry-run writes `.wavefoundry/logs/upgrade-convergence-migration.preview.log` (parity with the 1.4 → 1.5 migration preview-report shape). Stderr summaries distinguish rename from drop so the both-present case isn't mislabeled. `docs-lint` adds `check_workflow_config_removed_keys` — at or past `removed_in`, legacy spellings produce an ERROR (returncode flips); below, they continue to produce the existing WARNING (now annotated with the removal version). VERSION-file degraded modes (missing / unparseable) defer to no-escalation. Role renames stay at `removed_in: null` — config-key scope only. Closes the indefinite-deprecation gap from field-feedback item #1.
- **Canonical-names manifest is the single source for framework renames.** `.wavefoundry/framework/canonical-names.json` (schema v1) declares every role-slug and config-key rename with its deprecated alias and an optional `removed_in` semver for bounded deprecation. `wave_lint_lib/canonical_names.py` provides the loader (fail-safe to empty on missing/malformed input — `docs-lint` stays operational). `constants.RETIRED_ROLE_NAMES` and `constants.WORKFLOW_REQUIRED_KEYS` now derive from the manifest at module-load time; public surface unchanged for backward compat. Required-key list (`agent_memory`, `project_persona_generation`, etc.) stays in code — manifest scope is renames only. Enables downstream consumers (renderers, upgrade migrator) to migrate to the manifest incrementally. Wave 1p3iv prep for the convergence half of `wave_council_policy` → `wave_review`.
- **Red-team routes to the new failure-path patterns.** `seed-225` (red-team) gains a `## Failure Path And Boundary Correctness Patterns (Cross-Reference)` section listing the 6 patterns from `seed-221` with their applies-when scopes and a one-line adversarial-probe framing per pattern (e.g., "what unbounded input would exhaust a resource?"). Reviewers in `abuse-path-review`, `failure-pressure-test`, and `council-adversarial-primer` modes anchor probes to the canonical patterns without leaving `seed-225`. Cross-reference, not duplicate.
- **Code-reviewer review surface expanded.** `seed-221` `## What to Check` gains 13 generic code-correctness review patterns across two new sections — **State And Assumption Correctness** (7 patterns: re-entrancy, convergence after correction, legitimate-state enumeration, idempotence, cache-key completeness, schema evolution, negation correctness) and **Failure Path And Boundary Correctness** (6 patterns: error handling, resource cleanup, diagnostic quality, boundary arithmetic, trust-boundary input validation, failure-path test coverage). Each pattern carries an "applies when" hint so reviewers route effort by PR scope.

### Fixed

- **`code_search` finds re-export and barrel files.** The chunker gains a symbolless-code-file fallback: when a code file has no docstring AND no extractable symbols (re-export `__init__.py`, TypeScript barrel `index.ts`, Go single-file packages, Rust `mod.rs` re-exports, module-level constants files), it now emits a `kind="code"` module chunk with `id="<path>::__module__"` and the top-level non-comment lines so semantic search can find the public surface. Previously these files emitted zero chunks and were invisible to `code_search` (only `code_keyword` text-backed search found them). Per-language comment-prefix awareness (Python `#`, C-family `//`/`/*`, SQL `--`, HTML `<!--`); cap at 50 lines per module chunk. Files with even one extracted symbol use the existing docstring + symbols summary unchanged — fallback only fires when symbol extraction yields nothing. Marker-region-only files still emit zero chunks and remain outside semantic search. Wave 1p3iw `chunks_emitted` tracking stays accurate: post-fallback, re-export files record `chunks_emitted: 1` and exit the legitimate-zero set. `CHUNKER_VERSION` bumps from `"24"` to `"25"`; `indexer.py` auto-escalates incremental updates to a full rebuild on the version mismatch so consumer indexes regenerate transparently on upgrade.
- **Self-repairing indexer no longer thrashes on legitimately-empty files.** `file_meta` records `chunks_emitted` per file after each indexing run; drift detection skips paths with explicit `chunks_emitted == 0` (empty files, all-whitespace, marker-region-dominated content). Legacy entries (no field) go through the drift check once to learn the count, then skip silently. Real-drift convergence preserved.

### Removed

- **`pycache-cleanup` Claude Code hook surface.** The `PostToolUse` Bash row in `.claude/settings.json` and `.claude/hooks/pycache-cleanup*` launchers are no longer rendered. Existing consumer installs auto-clean on next `Upgrade wave framework`.

## [1.4.1] - 2026-06-03

### Fixed

- Published GitHub Release zips now include the pre-built framework semantic index (`.lance` embeddings, graph state, manifest). Prior 1.4.0 release was missing the index because CI lacked the index-build dependencies (`numpy`/`fastembed`/`lancedb`); consumers had to rebuild the framework index locally on first `docs_search` call. Releases now come from the maintainer's machine via `build_pack.py --release`, which always includes the optimized + vacuumed index.

### Changed

- `build_pack.py` is now the official release CLI. The new `--release` flag handles tag, push, and GitHub Release upload after a successful local build, with pre-flight refusals on dirty working tree, non-main branch, existing tag, missing CHANGELOG section, or unauthenticated `gh`. Bare `build_pack.py --version X.Y.Z` is unchanged for testing and local-only builds. A `--release-dry-run` mode walks the entire pipeline without side effects for smoke-testing.
- `docs/references/release-flow.md` added — operator-facing documentation for the release command, pre-flight gates, and partial-state recovery paths.

### Removed

- `.github/workflows/release.yml` deleted. The CI workflow shipped a strictly worse artifact (no framework index) than the maintainer's local build; replaced by `build_pack.py --release`. PR-tests CI (scoped to lint/tests, not publishing) may be added in a future change if/when needed.

## [1.4.0] - 2026-06-03

### Fixed

- Runtime Wave Council policy reader now accepts the new `wave_review` key in `workflow-config.json` with a legacy fallback to `wave_council_policy`. Consumers who follow upgraded seed guidance and rename the key keep their Wave Council enforcement; consumers who haven't migrated yet continue to work unchanged. A one-line deprecation note fires to stderr at most once per process on legacy-key read.
- docs-lint required-keys check accepts either `wave_implement` (new canonical name) or `wave_execution` (legacy) in `workflow-config.json`. Error message names both acceptable keys when neither is set so the migration path is discoverable inline.

### Changed

- `WORKFLOW_REQUIRED_KEYS` data structure generalized to support alias-tuple entries — future seed-prose key renames can add back-compat without changing the validator logic.
- Active operational docs migrated to the canonical renamed config-key names (`wave_review`, `wave_implement`); two high-traffic operator surfaces carry a `(formerly wave_council_policy)` annotation for migrating-operator discoverability. Historical wave records left untouched per the no-retrofit principle.
- Self-host `docs/workflow-config.json` top-level keys renamed to the canonical names — dogfoods the back-compat fix end-to-end against the canonical example.
- Framework project skeleton now ships `wave_review: { enabled: true }` by default so the Wave Council surface is available in every new install. Enforcement (`required_for_all_waves: true`) stays operator opt-in — the council is enabled, not enforced. Mirrors how red-team is wired in as an always-available council seat. docs-lint required-keys check now names `wave_review` (with `wave_council_policy` as the legacy alias) so installs missing the section fail discoverably.
- Review surfaces unified as specialist agents. The Wave Council moderator role moves from `docs/agents/council-moderator.md` to `docs/agents/specialists/wave-council.md` (named after the surface, matching `red-team.md`). A new `docs/agents/specialists/archetype-council.md` makes the operator-invoked Archetype Council discoverable as a peer — applicable to any artifact (plans, design docs, code, prose, decision narratives, naming, AC formulation) where orthogonal stance-based lenses are what the work rewards, not text-only. Role-string identity flips from `council-moderator` to `wave-council` across seeds, code, tests, and active docs. Historical wave records and in-flight 1p337 council-verdict text preserved verbatim per the no-retrofit principle. No behavior change — verdict shape and protocol mechanics are unchanged.

## [1.3.32] - 2026-06-03

### Added

- Public-launch README rewrite: symptom-first opening, audience qualifier, install walkthrough with named operator-visible signals, "Your first wave" three-turn transcript with intentional close-gate refusal, "What is installed" tree with per-directory roles and gitignore footnote, host coverage table, Design principles, "For teams" evaluation answers, Built-with-Wavefoundry as Contributing introduction
- Auto-syncing version badge derived from GitHub Releases
- Archetype Council review surface — stance-based council with five canonical seats (Sun Tzu, Yoda, Spock, Marcus Aurelius, Feynman) and documented Hemingway / Munger swap-ins; optional, operator-invoked; complements Wave Council
- New shortcut phrase `Archetype review` / `Archetype council` added to public command catalog and AGENTS.md
- `[~]` AC and task checkbox state for "intentionally not met" — required-priority `[~]` ACs lint-require an inline status note; tasks accept `[~]` without note (asymmetric per priority weight)
- `wave_close` close-time hard gate: every AC and task across admitted changes must be `[x]` or `[~]` before close; silent `[ ]` blocks with `silent_unchecked_items_at_close` diagnostic naming change-id + item-type + identifier; `not-this-scope` priority ACs exempt
- Dashboard renders `[~]` items with distinct glyph (`~`), italic muted text, "deferred" badge replacing the priority badge, and "· N deferred" suffix on progress fractions
- Dashboard progress denominators exclude `[~]` items so a fully-met change with deferred ACs renders as complete
- `wave_index_build` response carries `stranded_rows_reaped` and `stranded_rows_reaped_by_table`

### Changed

- `docs/prompts/index.md` opening framing rewritten without internal seed-IDs; Public Commands table and Legacy Aliases table preserved verbatim
- `docs/references/project-overview.md` refreshed
- AC dialog and Task dialog glyphs are bold and slightly larger (1rem) so all three states stand out

### Fixed

- LanceDB orphan-row reaper on incremental index update — reconciles the LanceDB row set against the current eligible set on every `mode='update'` so rows for paths excluded by workflow-config narrowing are removed without requiring a full rebuild; reaps both `docs` and `code` tables regardless of `content` arg
- Project-layer audit eligibility filter (`_layer_current_hashes`) now honors workflow-config `project_include_prefixes` opt-ins, matching the indexer's actual `files_for_meta` computation; eliminates false-positive "removed paths" signal when a repo opts in framework paths via `code.project_include_prefixes`

## [1.0.0] - 2026-05-24

### Added

- Full Wave Framework lifecycle: plan, create, prepare, implement, review, close
- Local MCP server with 47 tools across wave lifecycle, docs/code search, audit, and framework navigation
- Semantic search index built on fastembed and BAAI/bge-base-en-v1.5 (fully offline)
- Three-dimension feedback harness: maintainability (computational sensors), architecture and security/performance (inferential sensor lanes)
- Wave Council protocol for multi-reviewer governance
- 214 seed prompts covering the full agent operating surface
- Stage gates enforced by the server: prepare gate, required reviewer lanes, operator signoff
- Distribution packaging (`build_pack.py`) and upgrade flow (`upgrade_wavefoundry.py`)
- Multi-host agent support: Claude Code, Cursor, Codex, Copilot, Junie, Windsurf, Air, Warp
- Semver versioning with lifecycle-prefix build metadata
- Python tool venv at `~/.wavefoundry/venv` (no system Python modification)
- Dashboard server for portfolio visibility
