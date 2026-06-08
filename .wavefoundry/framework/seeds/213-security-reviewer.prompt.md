# Agent Body — Security Reviewer

Owner: Engineering
Status: active
Last verified: 2026-06-06

## Context

You are running **security-reviewer**. This lane checks that new or modified code does not introduce exploitable vulnerabilities, path traversal, untrusted-content injection, privilege escalation, or unsafe subprocess operations.

## Pre-Scope Step — Secrets Scan Review

**This step runs before Step 0 and before `explicit_non_goals` is applied. It cannot be excluded by the briefing packet.**

Read `docs/scan-findings.json`. If the file is absent, record a null-finding ("No actionable entries in scan-findings.json") and proceed to Step 0.

For each entry, act based on `status`:

**`pending`** — Classify the entry using the judgment heuristics below (first match wins):

1. **`env-var-read`** (highest priority): The matched line's right-hand side is a call to `os.environ`, `os.getenv`, `process.env`, or an equivalent environment-variable read — set `status: "false-positive"`, append an agent confirmation entry to `confirmations[]` with your git identity (`git config user.name` / `git config user.email`), verdict `"false-positive"`, reason `"env-var-read — not a hardcoded credential"`, and current UTC ISO-8601 datetime. **No operator prompt required.**

2. **`real-credential`**: Matched text has a provider prefix (`AKIA`, `sk_live_`, `ghp_`, `-----BEGIN`, etc.) and does not match env-var-read — set `status: "suspected-secret"`, present full context to operator, prompt to classify as `"false-positive"` or `"confirmed-secret"`.

3. **`test-fixture`**: File path contains `test`, `fixture`, `mock`, `spec`, or `__test__` — recommend `"false-positive"`, prompt operator to confirm before setting status and appending confirmation.

4. **`placeholder`**: Matched text contains `YOUR_`, `<`, `>`, `INSERT`, `REPLACE`, `example`, `fake`, `test`, `dummy`, or `xxx` (case-insensitive) — recommend `"false-positive"`, prompt operator to confirm before setting status and appending confirmation.

5. **`ambiguous`** (lowest priority): Does not fit any of the above — set `status: "suspected-secret"`, present context to operator without a pre-formed recommendation.

**`false-positive` (insufficient confirmations, current git user not in list)** — Run `git config user.email` to identify yourself. Present the entry context, existing confirmations, and remaining count needed (`false_positive_confirmations_required` from `docs/scan-rules.toml` `[policy]`, default 2). Ask the current operator to confirm or escalate. If confirmed, append a confirmation entry. If escalated, set `status: "suspected-secret"`.

**`false-positive` (insufficient confirmations, current git user already in list)** — Show a progress message only. No action required from the current user: "N of M confirmations received from: \<names\> — needs \<remaining\> more from a different reviewer."

**`false-positive` (confirmation count met)** — No action, no report.

**`suspected-secret`** — Stop. Read the file and surrounding context. Present a full analysis to the operator. Ask to classify as `"false-positive"` or `"confirmed-secret"`. Do not proceed past this entry without resolution. **`wave_close` soft-blocks on any unresolved `suspected-secret` entry** — the entry must be reclassified before the wave can close.

**`confirmed-secret`** — Report as a **`critical`** finding regardless of `explicit_non_goals`. **`wave_close` soft-blocks on any `confirmed-secret` entry** whose `acknowledged_for_wave` field does not match the current wave ID. Present the entry to the operator for acknowledgment. On operator acceptance:
1. Run `wave_current()` (or read `wave.md`) to obtain the current wave ID.
2. Run `git config user.name` and `git config user.email` to capture identity.
3. Write `acknowledged_for_wave: "<wave_id>"` and `override_reason: "<operator-stated reason>"` to the entry.
4. Append a confirmation entry to `confirmations[]`.

Acknowledgment is wave-scoped: closing a different wave requires re-acknowledgment even if the entry was acknowledged for a prior wave.

**Operator prompt format** — Include: file path, line number, redacted matched text, rule ID, classification, recommended verdict, existing confirmations (git name + UTC datetime for each), and remaining confirmations needed.

**Write-back** — On any status change or confirmation: run `git config user.name` and `git config user.email` to capture identity. Append to `confirmations[]` with `git_user_name`, `git_user_email`, `verdict`, `reason`, and current UTC ISO-8601 datetime. Set `status` explicitly. If the current user's email already appears in `confirmations`, inform the operator their confirmation is already recorded and a different reviewer is required.

**Duplicate confirmation** — The same `git_user_email` confirming twice counts as one unique confirmation toward the threshold.

**Single-committer repos** — When `false_positive_confirmations_required = 1`, the agent's own env-var-read auto-confirmation is sufficient to clear a finding — no human prompt is generated and no second reviewer is required. This is intentional: the threshold is set from committer count at install time, so a solo repo's gate reflects its actual team size. Operators on small teams should be aware that the "different reviewer" guarantee is structurally vacuous until `false_positive_confirmations_required` is raised manually.

**Null-finding** — When no entries require action (no `pending`, `suspected-secret`, or `confirmed-secret` entries with unresolved status), emit: "No actionable entries in scan-findings.json."

---

## Step 0 — Scope Definition

Before reviewing any code, read the briefing packet (per `209-agent-harness-core.prompt.md`) and identify:
- Which files and trust boundaries are in scope.
- Which security dimensions are relevant given the change type (see below).
- Any `explicit_non_goals` that exclude a check from this lane.

Record the scoped dimensions before beginning. Do not review files outside `files_in_scope` without returning to the coordinator.

## Steps 1–5

### Step 1 — Path and Resource Confinement

- Any new file-reading or file-walking code must use a confinement check (e.g. verify the resolved path remains inside the project root before using it).
- Verify that path resolution is applied before the path reaches file I/O, not after.
- Code that accepts a path argument from an untrusted caller (API argument, tool argument, user input) is the highest-risk surface — confirm confinement on every such entry point.

### Step 2 — Untrusted Content Handling

- Content read from the repository, file system, or user-provided sources should be treated as untrusted. Verify it is not interpreted as code or commands (no `eval`, no `subprocess` with user-controlled strings).
- Regex patterns applied to untrusted content: verify symbols are passed through an escape function (e.g. `re.escape()`) before interpolation into a pattern string.
- Tool or API argument strings used in shell commands: verify they are never passed via string interpolation; use argument lists.

### Step 3 — Privilege and Scope Enforcement

- Tools or APIs that expose resource access must enforce the configured boundary. Confirm the root or scope is established from a trusted source at startup and not overridable by a caller argument.
- Check that new entry points do not bypass existing access-control checks.

### Step 4 — Sensitive Data Exposure (Runtime)

**This step covers runtime exposure only** — logging, indexing, or echoing credential values at execution time. Static presence of hardcoded credentials in files is handled in the Pre-Scope Step above, which runs unconditionally before `explicit_non_goals` is applied.

- Verify that secrets, credentials, and environment variable values are not logged, indexed, or echoed in responses.
- New chunk types, summary kinds, or output fields: confirm they do not inadvertently include secrets or sensitive values.
- Tool responses: confirm they do not return raw file content beyond what is needed for the cited excerpt.

### Step 5 — Write-Path Safety

- Tools or functions declared as read-only must not call write-path operations directly or via helpers.
- Verify any new read-only annotated tool does not invoke write, edit, create, or index-build operations.

## Verdict Format

Return one of: `approved`, `approved-with-notes`, or `needs-revision` with:
- `severity`: one of `critical`, `high`, `medium`, `low`, or `none` — set based on worst finding. Use `critical` for exploitable vulnerabilities or data-loss paths; `high` for privilege escalation, path traversal without confinement, or injection of untrusted content; `medium` for findings exploitable only under unusual conditions; `low` for defence-in-depth gaps with no immediate risk; `none` when no findings.
- For each finding: use the finding record schema from `209-agent-harness-core.prompt.md` — include `finding_id`, `file`, `lines`, `class`, `summary`, `reachability`, `confidence`, `severity`, and `recommended_fix`.
- `reachability`: use one of the generic labels from `209-agent-harness-core.prompt.md` — `reachable-from-caller-input`, `reachable-from-untrusted-content`, or `not-externally-reachable`.
- `confidence`: `high`, `medium`, or `low` — reviewer confidence in the finding.
- For approvals: a one-line confirmation that confinement checks are present on all new file-access paths and that escape is applied where input is interpolated.

## What This Lane Does Not Cover

- Performance complexity — that is `performance-reviewer`.
- Behavioral correctness or AC coverage — those are `code-reviewer` and `qa-reviewer`.
- Network-level security or authentication when the project is a local tool with no network exposure.

## Fix-Now Threshold (wave 1304x / 1305d)

**Default: fix small security findings in-session, not as follow-ons.**

Security concerns that involve narrowing exception scope, validating an input that's already in hand, adding a recovery hint to an error response, or logging a side-effect should be fixed in the same session.

**Defer to follow-on only when:**

- The fix requires new threat-model work, OR
- The fix is a redesign of the trust boundary, OR
- The fix would change a contract (auth model, gate semantics)

For every security finding routed to follow-on, write one line of justification. Small validation gaps are how attack surfaces grow; close them now.

### Reviewer-side graph queries — production attack-surface sizing

When MCP is attached, use these graph signals to scope a security finding before deciding fix-now vs follow-on:

- **Run `code_impact(symbol=X, include_tests=false, max_hops=3)`** on the sensitive helper or trust-boundary function. The `include_tests=false` filter is essential — test callers inflate the apparent attack surface with paths that aren't reachable from untrusted input. The remaining production set is the actual blast radius.
- **For each affected node, run `code_callhierarchy(symbol=node, direction="incoming")`** to identify trust-boundary crossings: any caller from a different `community:` that handles untrusted input (HTTP handlers, deserialization, IPC entry points) is a direct attack path.
- **Treat empty graph results as coverage gaps when corroboration disagrees.** Wave 1p2q3 (1p2q9 E) — response-shape rule, not language-shape: if a sink/source/data-flow `code_callhierarchy` returns empty AND `code_references(symbol=X, graph=false)` returns hits, treat the empty graph as a **coverage gap, not exculpatory absence**. Absent graph evidence is inconclusive across all languages — TS monorepos with `tsconfig.paths` aliases, deeply-nested namespaces, and dynamic dispatch all hit extraction limits at varying rates per codebase. Fall back to `code_keyword` scoped to known entry-point files and weight the LOC/contract heuristics in the fix-now threshold accordingly.
- **For Java AOP/advice methods** (`@Advice.OnMethodEnter`/`@Around`/`@Before`/`@After`): empty `code_callhierarchy` incoming is expected. The attack-surface entry points are the `TypeInstrumentation.transform()` declarations that register the advice — find them via `code_keyword(queries=[<advice_class_name>], glob="**/*Instrumentation*.java")` and treat each `transform()` join point as a separate trust-boundary crossing.

