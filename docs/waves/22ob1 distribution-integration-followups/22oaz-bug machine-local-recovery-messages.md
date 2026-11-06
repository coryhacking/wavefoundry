# Make setup recovery commands specific and actionable

Change ID: `22oaz-bug machine-local-recovery-messages`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-11-05
Wave: 22ob1 distribution-integration-followups

## Rationale

Distribution feedback reports three recovery traps: bare wf can open Windows Firewall; the WindowsApps python3 alias can emit Store text followed by a generic launcher error; model-bundle notices omit explicit selection for a bundle with another basename. These are reported cases, not native Windows or model-installation qualification here. Source verification and bounded reproductions are implementation prerequisites.

## Product Intent

Operators should receive a usable command for their repository and a precise remedy for a missing interpreter or unused compatible bundle, without changing provider choice, starting setup automatically or weakening host policy. AC-1 through AC-3 test the delivered commands and diagnostics. This supports dependable operation across machines without a new setup workflow.

## Requirements

1. Use one pure helper for the absolute repository launcher in setup-readiness action argv and related setup-check, session-start and server-dry-run messages: .wavefoundry/bin/wf on POSIX, .wavefoundry/bin/wf.cmd on native Windows. Preserve structured argv, root arguments and correct shell rendering for spaces and special path characters.
2. In rendered wf.cmd, distinguish a selected WindowsApps python3 placeholder from an ordinary interpreter. Only that alias path receives the extra silent probe. If it cannot run Python, emit one actionable message about disabling the Python/Python3 App execution aliases and placing a real python3 on PATH, without administrator instructions, then exit 2.
3. Preserve Python 3.11+ checks, canonical python3 registration and existing errors for real interpreters. Do not switch to python.exe, bypass PowerShell policy or add startup probes for ordinary interpreter paths.
4. Model recovery notices explain the existing --model-bundle option and actual supported environment variable, validated from source, for a bundle under any name. State the required compatible model-set rather than implying all framework releases require a new model set.
5. For a relevant misnamed model archive in existing search folders, emit one bounded found-but-not-used hint without adopting it. Treat its basename as untrusted: quote it, reduce to printable ASCII and cap at 120 characters. Preserve bundle authentication/compatibility validation, default search precedence and selected model/provider identities.

## Scope

In scope: setup_readiness.py and its command consumers, render_platform_surfaces.py's wf.cmd producer, model_bundle.py/setup_index.py recovery notices and focused tests/docs. Regenerate the existing managed bootstrap/session-start consumers listed below from those producers, preserving unrelated content; their shared bootstrap body carries the same recovery helper. This is separate from the completed 22l9k setup semantic-work fix. Out of scope: new fallback providers, downloading models, changing model sets, automatic setup or machine configuration.

## Acceptance Criteria

- [x] AC-1: JSON and human setup remedies name the correct absolute launcher and retain valid arguments for representative POSIX/Windows paths; no check starts setup.
- [x] AC-2: The rendered Windows launcher distinguishes the placeholder failure from real/missing/too-old Python, emits the intended single remedy and preserves ordinary startup behavior. Evidence explicitly identifies native versus simulated coverage.
- [x] AC-3: Compatible explicitly named bundles remain selectable; a misnamed candidate receives a bounded safe hint without automatic selection, while malformed or incompatible archives retain their refusal.

## Tasks

- [x] Verify current consumers, interpreter-selection behavior and bundle option/environment names.
- [x] Implement the shared remedy and narrowly scoped messages.
- [x] Run controlled command/bundle fixtures, record native limits and update recovery guidance.

## Agent Execution Graph

Admission and readiness may proceed while another wave is open. Activation follows the existing single-OPEN rule; serialize overlapping renderer and setup-message implementation edits after the current setup wave completes. This plan adds no restriction on parallel planning or readiness.

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/setup_readiness.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/model_bundle.py`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/setup_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/references/native-windows-support.md`
- `docs/contributing/build-and-verification.md`
- `.claude/hooks/pre-edit.py`
- `.claude/hooks/post-edit.py`
- `.claude/hooks/session-capture.py`
- `.claude/hooks/context-efficiency-project.py`
- `.claude/hooks/simulate-hooks.py`
- `.cursor/hooks/seed-warn.py`
- `.cursor/hooks/framework-plan-warn.py`
- `.cursor/hooks/docs-lint.py`
- `.cursor/hooks/after-file-edit.py`
- `.github/hooks/pre-tool-use.py`
- `.github/hooks/post-tool-use.py`
- `.windsurf/hooks/seed-protect.py`
- `.windsurf/hooks/docs-lint.py`
- `.claude/hooks/wf-session-start.py`
- `.wavefoundry/bin/wf.cmd`

Test scope is limited to the named recovery paths and their actual consumers, identified before implementation. CHANGELOG.md records behavior and qualification limits.

## Affected Architecture Docs

Update the canonical onboarding/recovery guidance in docs/contributing/build-and-verification.md and native-windows-support.md; primary setup/provider ownership is unchanged.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes ambiguous executable lookup. |
| AC-2 | required | Gives an actionable interpreter remedy. |
| AC-3 | required | Explains safe bundle recovery. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-05 | Reuse canonical setup and explicit selectors with precise diagnostics. | Commands and bounded messages address the reported confusion while preserving choice. | PATH-dependent bare commands retain ambiguity; automatic alias repair or bundle adoption exceeds scope. |
| 2026-11-05 | Regenerate the named managed consumers of the shared bootstrap remedy. | Producer changes affect fourteen existing hook copies and wf.cmd; naming them before regeneration makes review scope explicit. | Leaving generated consumers stale would fail convergence and retain old remedies. |

## Risks

Windows batch quoting and interpreter resolution need execution evidence. Simulated rendering does not qualify native Windows. Model diagnostics must not expose arbitrary paths/content or turn a candidate filename into trusted selection.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-05 | Implemented absolute launcher remedies, narrow WindowsApps probe, filename-only bounded model hint and compatible-model-set selectors. Four guard mutants detected;15 named consumers regenerated and183 renderer/session checks pass. Compile/test bytecode outputs positively identified and preserved in ignored work; no source caches remain. Native Windows remains unqualified. | delivery-evidence.json; named production tests and guard mutants; full canonical qualification and independent delivery review pending. |
| 2026-11-05 | Readback: deliver absolute repository setup commands, WindowsApps-only interpreter diagnostics and bounded explicit model-bundle recovery hints without automatic selection/setup. AC-1–3; setup implementer owns named setup/platform/model producers and focused tests, preserving22l9k. Native Windows remains unqualified unless actually executed; coordinator owns server_impl integration if needed. | Current receipt review-policy-9f3ca64efa19fe8cfee4; Implement wave activation succeeded. |
| 2026-11-05 | Staged from the distribution's offered fixes; native reproduction and exact environment selector remain to be verified. | Distribution feedback against bc9cfc8e; no host changes or bundle downloads performed. |
| 2026-11-05 | Corrected the sequencing note: admission/readiness may proceed in parallel; activation and overlapping implementation remain serialized. | Existing readiness-versus-activation contract in docs/specs/mcp-tool-surface.md. |
| 2026-11-05 | Named the generated consumers derived from existing R1/R2 before their first edit; dependent regeneration held for focused readiness refresh. Requirements and AC outcomes are unchanged. | Setup builder's canonical producer inventory; no generated writes yet. |
| 2026-11-05 | Final delivery passed: canonical suite 12,369 tests / 217 files / 12 reported skips; full docs validation and independent required lanes plus Council approve. Four supporting test-fixture repairs were independently verified in cycle 1; no product repair or scope change was needed. | delivery-evidence.json and typed events.jsonl; current receipt 92ad0645. Wave remains open for operator signoff. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
