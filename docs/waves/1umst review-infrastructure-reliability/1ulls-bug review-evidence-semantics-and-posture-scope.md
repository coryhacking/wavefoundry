# Review Evidence Semantics and Retrieval-Posture Scope

Change ID: `1ulls-bug review-evidence-semantics-and-posture-scope`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-06
Wave: 1umst review-infrastructure-reliability

## Rationale

Solaris supplied documented finding judgment fields that were silently replaced with `unverified`/`none`, changing the actionability gate to blocking `do_now`. After repair and independent reverification, the finding synthesis correctly showed a terminal chain while the approval projection still described it as a blocking finding. Separately, `retrieval_posture_gap` counts all dirty non-doc files in the working tree, so unrelated operator-held changes inflated a five-file wave to 185 files and produced a close-time advisory that could no longer be repaired.

The review ledger must preserve caller-authored classification facts or reject them explicitly, state the actual reason an operator signoff is withheld, and measure review posture against wave-owned work.

## Requirements

1. Every documented caller-supplied judgment field accepted for a finding must persist unchanged into the canonical synthesis, unless a declared derivation rule rejects it with a field-specific diagnostic before append.
2. The actionability gate must evaluate the persisted/validated judgment record, and a caller must never receive a success response whose ledger silently differs from its supplied classification.
3. Approval and operator-signoff projections must distinguish unresolved blocking work from a terminal repaired finding that still requires an explicit operator acceptance; their wording and machine-readable state must agree with chain synthesis.
4. `retrieval_posture_gap` must count only wave-owned implementation scope, using the admitted change scope or wave diff rather than the whole working tree.
5. A retrieval-posture advisory must be available early enough to be acted on, and its message must disclose the selected scope and count source.
6. Regressions must exercise a complete finding → repair → independent reverification → approval/signoff sequence and a dirty-worktree control with unrelated changes.

## Scope

**Problem statement:** Review evidence can be silently reclassified, post-repair projections contradict terminal state, and retrieval-posture feedback measures unrelated repository dirt.

**In scope:**

- Finding validation/synthesis, actionability, and approval-projection semantics.
- Retrieval-posture scope derivation and timing/diagnostics.
- Typed-ledger and context-efficiency regressions.

**Out of scope:**

- Weakening repair-chain independence or the known-bad-detection requirement.
- Removing explicit operator acceptance where policy still requires it; this change makes that reason honest and consistent.
- General git cleanliness enforcement.

## Acceptance Criteria

- [x] AC-1: A valid `dont_do_later` finding persists every documented judgment field byte-for-byte (or returns a field-specific pre-append rejection); no success path silently substitutes defaults.
- [x] AC-2: The synthesized disposition is derived from the persisted judgment and matches the action response and ledger record.
- [x] AC-3: A terminal, repaired, fully reverified finding is not labeled as unresolved blocking work; if operator acceptance remains required, the projection says so and identifies the finding.
- [x] AC-4: A wave with five owned implementation files and 180 unrelated dirty files measures only its wave-owned footprint for `retrieval_posture_gap`.
- [x] AC-5: The advisory identifies its scope/diff basis and is emitted at an actionable lifecycle point.
- [x] AC-6: End-to-end repair-chain and dirty-worktree regression tests pass alongside the full framework suite.

## Tasks

- [x] Trace judgment fields from MCP validation through synthesis and actionability; preserve or explicitly reject every documented field.
- [x] Reconcile chain-summary, finding-table, and approval/signoff projection state and language.
- [x] Derive retrieval scope from admitted changes or a stable wave diff and expose the source in diagnostics.
- [x] Add complete ledger-chain and unrelated-dirty-tree regressions.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| finding semantics | implementer | none | Registry, synthesis, projection |
| posture scope | implementer | none | Context-efficiency seam |
| end-to-end verification | qa-reviewer | both | Typed-ledger and dirty-tree controls |

## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/server_impl.py`
- `.wavefoundry/framework/scripts/context_efficiency.py`
- `.wavefoundry/framework/scripts/tests/test_review_evidence.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

`docs/specs/mcp-tool-surface.md` needs the corrected caller-input and projection contract. The existing repair-chain architecture remains intact.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Silent loss of judgment corrupts recorded review authority. |
| AC-2 | required | Gate decisions must be traceable to persisted facts. |
| AC-3 | required | Prevents false blockers and misleading signoff state. |
| AC-4 | required | Restores a meaningful posture metric. |
| AC-5 | important | Makes advice actionable and auditable. |
| AC-6 | required | Pins the full stateful behavior. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-08-06 | Filed from Solaris 1.15.4+ph68 field report; registry reads show judgment fields are documented while synthesis defaults and blocking state are separate seams. | `review_evidence.py:280-365,943-946,1435-1551,2685-2688`; `server_impl.py:16228` |
| 2026-08-06 | Preserved submitted repair judgments, clarified repaired-vs-unresolved approvals, and scoped posture counts to admitted targets. | `test_review_evidence.py`; `test_server_tools.py` |
| 2026-08-06 | **P2 repaired: declared targets were case-folded while git paths are not.** `serialization_point_paths` lowercases every declared path but `git status --porcelain` preserves case, so `in_wave_footprint`'s exact compare silently dropped every PascalCase target and undercounted the wave's own declared footprint while the advisory still claimed to describe it. Both sides are now folded at the comparison rather than un-lowercasing the shared extractor that lane scoring also uses. | `server_impl.py` `_wave_code_footprint` |
| 2026-08-06 | **P2 repaired: the sensor doc never recorded its own rescoping.** `docs/references/context-efficiency.md` still described the footprint as the whole changed non-docs working tree, and did not mention that a wave declaring no Serialization Points makes the sensor silent rather than firing. Both are now documented. | `docs/references/context-efficiency.md:199-212` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- |
| 2026-08-06 | Preserve valid caller judgment rather than silently derive replacements. | The MCP schema represents these as caller authority; derivation must be explicit or absent. | Keep defaulting and document it; contradicts the public contract. |
| 2026-08-06 | Separate unresolved-work blocking from repaired-finding acceptance. | A terminal chain is not open work, though policy may still require a conscious operator decision. | Continue calling both “blocking findings.” |
| 2026-08-06 | Scope posture to admitted wave work. | Working trees legitimately contain unrelated operator-held changes. | Keep whole-tree count; produces non-actionable false advisories. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Preserving judgments bypasses policy validation | Validate every allowed vocabulary and cross-field rule before append. |
| New projection wording hides a real gate | Keep a machine-readable acceptance-required state and test close gating separately. |
| Wave scope lacks an exact diff in some states | Define and disclose a deterministic fallback based on admitted Serialization Points. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
