# Render explicit-invocation policy for operator skills

Change ID: `21fgq-enh codex-explicit-invocation-skill-policy`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-22
Wave: 21fgr audit-detector-and-skill-invocation-policy

## Rationale

Audit A9 found no agents/openai.yaml policy for operator-owned skills. Official OpenAI guidance now documents policy.allow_implicit_invocation: false, while the renderer only emits the Claude frontmatter equivalent.

## Product Intent

Codex receives its documented explicit-invocation metadata for the existing operator-only Wavefoundry skills. This is skill-selection guidance, not tool authorization or proof that all host versions enforce it. AC-1 verifies the shipped metadata contract.

## Requirements

1. Render agents/openai.yaml with policy.allow_implicit_invocation: false for eligible operator_only registry skills under active .codex/skills and .agents/skills roots. The latter is the currently documented Codex path; retain legacy compatibility. Do not emit this file to Claude skills or change SKILL.md bodies/frontmatter.
2. Treat these new sidecars as missing-only unless their full bytes match the renderer-owned version. Preserve existing custom metadata byte-for-byte and report a bounded actionable notice rather than silently claiming the policy was applied. Do not add a YAML dependency or merge arbitrary operator YAML.
3. Preflight all new output paths, including the agents directory and leaf file, for symlinks before any host writes. Preserve existing containment protections, doc gates and absent-host behavior. Repeated renders are byte-stable and report no unchanged paths.
4. Document canonical ownership, current Codex discovery paths, explicit invocation behavior, custom-file reconciliation and the boundary that this is not permission enforcement. Antigravity shares .agents but no unsupported policy-enforcement claim is made.

5. When the existing stale-skill migration retires a default operator-skill path after a profile rename, remove only its exact renderer-owned agents/openai.yaml; remove the agents and skill directories only when empty. Recover an owned sidecar stranded after SKILL.md was already removed. Preserve custom, invalid, unreadable or concurrently changed metadata and unknown files with a bounded notice. Preflight stale sidecar parent/leaf symlinks before any host writes, and use contained identity/content checks before removal so a replaced path or same-file customization is preserved. Do not remove a path reused by the current profile.

## Scope

In scope: renderer, tests, generated metadata for four eligible operator-only skills in each active Codex-compatible root, and platform mapping documentation. Out of scope: tool authorization, removing duplicate carriers, editing installed plugins, new per-host abstraction, YAML merge, automatic overwrite of custom sidecars and unsupported runtime guarantees.

## Acceptance Criteria

- [x] AC-1: The public render_skills path produces the exact hand-authored YAML literal for all four operator-only skills in both active compatible roots, none for ordinary skills/Claude, and respects missing-doc and absent-host gates. The prior renderer fails this check.
- [x] AC-2: A second render is idempotent; custom sidecars are preserved with actionable diagnostics and symlinked agents/leaf destinations fail before writes to any host. Known-bad controls detect omitted containment or custom-file protection.
- [x] AC-3: Existing skill bodies and Claude frontmatter remain byte-identical, and platform guidance accurately distinguishes invocation metadata from tool permissions and unqualified hosts.
- [x] AC-4: Focused renderer tests and the canonical framework suite pass; generated project outputs match the renderer and independent review plus full docs validation completes.

- [x] AC-5: Public profile-renaming render/migration removes exact owned sidecars and empty retired folders, including stranded-sidecar recovery, while preserving current-name reuse, custom metadata and unknown files. Stale parent/leaf links fail before any host write; path replacement and same-file customization are preserved. Known-bad cleanup, ownership and containment controls are detected.

## Tasks

- [x] T-1: Implement sidecar rendering and complete preflight with focused regression tests.
- [x] T-2: Regenerate eligible local metadata from canonical source and update platform guidance.
- [x] T-3: Verify preservation, containment and known-bad controls; obtain independent review and run required validation.

- [x] T-4: Repair profile-rename sidecar retirement and compatibility fixtures; verify custom/unknown-file preservation, interrupted cleanup, symlink refusal and concurrent replacement/customization through the public paths.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Implementation | implementer | readiness | Single writer |
| Verification | independent reviewer lanes | implementation | Frozen source; public-path and known-bad checks |

## Serialization Points

Coordinator owns records; implementer owns the following files only. Generated surfaces must come from their owning renderer.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_agent_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_declared_extension_skills.py`
- `.wavefoundry/framework/scripts/tests/test_vocabulary_prompt_names.py`
- `.codex/skills/`
- `.agents/skills/`
- `docs/agents/platform-mapping.md`

## Affected Architecture Docs

Update docs/agents/platform-mapping.md for the host metadata contract; other architecture docs N/A because this extends existing generated skill output without a new runtime component.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the bounded correction and preservation contract |
| AC-2 | required | Establishes the bounded correction and preservation contract |
| AC-3 | required | Establishes the bounded correction and preservation contract |
| AC-4 | required | Establishes the bounded correction and preservation contract |
| AC-5 | required | Preserve profile migration and operator metadata ownership |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-22 | Planned from current audit and inspected owning source; no implementation edits. | Audit findings and declared source paths |
| 2026-10-22 | Readback: extend the existing registry renderer with literal Codex explicit-invocation sidecars for eligible operator-only skills in active .codex and .agents roots. Before, wf-close-wave has only SKILL.md on those roots; after, agents/openai.yaml declares allow_implicit_invocation false. AC-1–3 preserve skill bytes, custom sidecars and doc/host gates, and reject nested/leaf symlinks before any host writes. Scope is renderer, focused tests, generated sidecars and platform mapping; this is invocation metadata, not tool authorization or a host-runtime guarantee. | MCP source read confirms render_skills, _skill_output_destinations and existing contained exclusive byte publisher; memory advisories rechecked for lexical symlink preflight, doc gates and LF/custom preservation. AC-4 remains pending coordinated suite and independent review. |
| 2026-10-22 | Implemented literal sidecar rendering with missing-only atomic publication, exact-byte ownership detection, actionable custom-file notice, and direct/full-render lexical preflight. Generated eight local sidecars; all 48 SKILL.md files remain byte-identical and second render returns no changes. Platform guidance states discovery compatibility and invocation-only limits. | OperatorSkillPolicyTests: 6 passing tests cover literal outputs, ordinary/Claude exclusions, doc/host gates, repeated rendering, custom bytes including invalid UTF-8, nested/leaf links, legacy-wrapper migration ordering, publication races and unchanged skill documents. Generation used approved escalation for protected host roots; no permissions/config changes. |
| 2026-10-22 | Verification: final renderer file passes 178 tests in 18.617s, no skips. Original renderer fails literal output check. Known-bad controls detect direct policy preflight deletion (8 assertion failures), full-render policy preflight deletion (2 failures before native legacy-wrapper migration), and custom overwrite (3 failures); all controls fail by assertions, without errors. An initial full-file diagnostic exposed changed legacy symlink wording; strict new preflight was narrowed to policy sidecars and existing tests now pass unchanged. | /private/tmp/wf-audit-remediation/skill-policy-original.log; skill-policy-controls.log; skill-policy-renderer-file.log. Mutants live only in temporary in-memory modules. git diff --check passes. Canonical suite, full docs validation and independent review remain coordinator-owned under AC-4/T-3; no host runtime enforcement claim. |

| 2026-10-22 | Initial canonical qualification failed: 12,067 tests across 206 files, 12 existing skips, 710.965s. Five files report one failure each: declared-extension skill output roster, actor-token census, profile-literal census, legacy session-start timeout assertion and renamed-skill cleanup. Source-wave completion/approval remains pending repair; no failures waived. Earlier progress sampling missed three FAIL lines; final tracebacks are authoritative. | /private/tmp/wf-audit-remediation/canonical-initial.log; independent typed findings and bounded repair planning underway |

| 2026-10-22 | Repair amendment: Requirement5/AC5/T4 add bounded retirement of renderer-owned sidecars at existing stale skill paths, including partial prior cleanup and protection against symlinks, replacement and customization. Declared two additional compatibility-test targets. Keep SKILL.md byte oracle and independently assert exact sidecar roster/bytes; derive the legacy wrapper fixture from existing rename metadata instead of adding actor-census literals. No census relaxation, custom YAML merge or active carrier removal. Re-Prepare before edits. | Three failures reproduced independently in a9-repair-original.log; initial canonical tracebacks; amended owning sections |

| 2026-10-23 | Readback: repair Requirement5/AC5/T4 after refreshed readiness and both cycle-1 repair_start records. Before, a profile rename removes SKILL.md but leaves its owned policy and old directory; after, exact owned policy and empty directories retire, including stranded-policy recovery. Custom/unknown content and changed identities/content survive with notices; stale policy links fail before host writes, and current names stay excluded. Extend the existing contained removal helper with an optional content check; do not claim atomic compare-and-unlink. Correct the two compatibility fixtures without relaxing byte or census assertions. | QA-A9-RENAME-1 and QA-A9-FIXTURES-1; pre-repair three-test reproduction; affected renderer, three test files and platform mapping only. |

| 2026-10-23 | Repair implementation frozen: exact-owned retirement now covers stranded policies, empty-directory cleanup, custom/unreadable metadata and unknown-file preservation notices. Stale policy links are preflighted on direct and full render; current-name reuse is excluded. Existing judged removal accepts an optional exact-content recheck at the removal boundary; existing callers retain the default. Compatibility fixtures retain the SKILL.md byte oracle, add a literal sidecar oracle and derive the legacy actor fixture from existing migration metadata. | Focused 14 tests passed in 4.662s; 13 existing removal/reversion/interruption checks passed in 43.147s; final strengthened removal-boundary check passed in 1.143s. New retirement tests failed on the pre-repair source with 17 assertion failures and no errors. Logs: /private/tmp/wf-audit-remediation/a9-repair-focused.log, a9-existing-removal-regressions.log, a9-removal-boundary-final.log and a9-retirement-before.log. |
| 2026-10-23 | Seven known-bad retirement controls detected by assertion failures, no errors: omitted cleanup (2), loosened ownership checks (2), omitted direct stale preflight (4), omitted global stale preflight (4), omitted content recheck (2), omitted parent identity (2), and removed current-name exclusion (1). Mutation injection is at the actual removal-helper entry; same-inode customization and replacement preserve data on both supported branches. | RetiredOperatorPolicyTests; /private/tmp/wf-audit-remediation/a9-retirement-controls.log. No full suite rerun here. No atomic compare-and-unlink guarantee, native-Windows execution proof or runtime-host guarantee; platform mapping documents residual OS concurrency windows. Fresh QA and final canonical qualification remain pending. |

| 2026-10-22 | Final canonical run completed red: 12,072 tests across206files,12skips,1056.567s. All five original failing files now pass. Two other files fail: registered reload ownership reports second writer; TechDocs escaping-symlink fixture lacks unsafe_survivor_targets. Fresh independent QA/code/security/docs reviews found no new admitted-scope blocker; repaired findings are terminal, but delivery approvals and qualification ACs remain pending the required green suite. No test waiver, threshold change or unchanged retry. | /private/tmp/wf-audit-remediation/canonical-final.log; final-code-architecture-review.md; final-security-review.md; fresh-qa-docs reports; final-source-preservation.json |

| 2026-10-23 | Qualification completed after the operator-requested retry: canonical suite passes12,072tests across206files with12existing skips in648.998s; a fresh green receipt is recorded. Both formerly failing files pass. Reviewed implementation fingerprints unchanged. All specialist delivery approvals are current, all required ACs/tasks met, changes implemented. Operator signoff and closure remain pending; no commit or close performed. No new memory candidate warranted: bounded lessons remain in canonical tests/guidance and existing records. | .wavefoundry/framework/scripts/run_tests.py; /private/tmp/wf-audit-remediation/canonical-requested-requalification.log; typed delivery approvals and post-requalification-source-check.json |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-22 | Add the documented Codex sidecar with conservative custom-file preservation | Smallest bounded correction | Broad parser or host abstraction redesign is outside scope |

## Risks

| Risk | Mitigation |
| --- | --- |
| A shared carrier or customized sidecar could be overwritten or overstated | Public-path regressions and independent review |

## Session Handoff

Prepare before source edits. Implement, review and pause; no commit or closure authorized.
