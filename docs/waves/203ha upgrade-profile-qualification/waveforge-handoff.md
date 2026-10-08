# Waveforge public request handoff

Owner: Engineering
Status: active
Last verified: 2026-10-08

This handoff covers the public October 7 R1–R9 requests and addendum A1–A3 against `404e4950`. The fixes summarized below are included in pushed commit `d8bee00a` and its ancestors. The additional upgrade-test qualification repair in [change 203h9](203h9-bug%20upgrade-profile-fixture-portability.md) is delivered with closed wave `203ha` in the commit containing this handoff. This is a source delivery; no new distribution pack was built.

## Public request coverage

| Request | Delivered behavior | Durable evidence |
| --- | --- | --- |
| R1: names assembled in code | Reconcile prompt keys are literal canonical keys, with a census enforcing profile-name call sites. | [200ew](../200ey%20containment-and-distribution-seams/200ew-enh%20distribution-seams-and-neutral-council-role.md), AC-1 |
| R2: member-document helper | Extensions can use published `read_member_doc_bytes`, `is_change_id`, and `MemberDocRefused`. | [200ew](../200ey%20containment-and-distribution-seams/200ew-enh%20distribution-seams-and-neutral-council-role.md), public helper tests |
| R3: history-literal census | The census scans framework-owned scripts and subpackages, excluding distribution-owned modules by construction. | [200ex](../200ey%20containment-and-distribution-seams/200ex-maint%20distribution-safe-framework-tests.md), AC-1 |
| R4: profile golden isolation | Scratch golden boots reset shipped vocabulary, paths, and declaration constants before applying the requested asset. | [200ex](../200ey%20containment-and-distribution-seams/200ex-maint%20distribution-safe-framework-tests.md), AC-2 |
| R5: archive vocabulary fixture | The fixture uses a distinct archive-only record filename and checks it against live and fixture profiles. | [200ex](../200ey%20containment-and-distribution-seams/200ex-maint%20distribution-safe-framework-tests.md), AC-3 |
| R6: checkout-dependent prompt tests | Lookup tests build fixture prompts from the active profile; retired-token checks inspect the named framework sources. | [200ex](../200ey%20containment-and-distribution-seams/200ex-maint%20distribution-safe-framework-tests.md), AC-4 |
| R7: council naming | `council-chair` is the neutral actor/role; legacy actors and keys remain accepted. Distribution constants control the council display name and extra legacy signoff aliases. | [200ew](../200ey%20containment-and-distribution-seams/200ew-enh%20distribution-seams-and-neutral-council-role.md), requirements 3–10 and 13–16 |
| R8: journal retry guidance | A failed pre-migration hook points to Migrate journals; it no longer promises an automatic retry on a later upgrade. | [200ev](../200ey%20containment-and-distribution-seams/200ev-bug%20inert-upgrade-preview-and-attestation-display.md), requirement 4 |
| R9: lifecycle vocabulary after reload | MCP reload evicts `lifecycle_id` so subsequent imports use the current vocabulary profile. | [200ew](../200ey%20containment-and-distribution-seams/200ew-enh%20distribution-seams-and-neutral-council-role.md), requirement 11 |
| A1: member-doc test reads checkout config | The scratch config uses a known-good literal with targeted review delivery mode. | [200ex](../200ey%20containment-and-distribution-seams/200ex-maint%20distribution-safe-framework-tests.md), AC-8 |
| A2: assembled legacy keys and colliding examples | Council tests derive legacy spellings from the framework registry; historical digest coverage is separately gated. Prompt examples use task/batch naming and retain a slug-reuse chain and alias. | [200ex](../200ey%20containment-and-distribution-seams/200ex-maint%20distribution-safe-framework-tests.md), AC-9–AC-10 |
| A3: old-runner preview imports and log disclosure | Incoming preview code loads its own `history_paths` sibling privately from the pack or source location. Updated runners disclose written preview logs in the final message and summary. | `upgrade_extensions._incoming_history_paths`; [200ev](../200ey%20containment-and-distribution-seams/200ev-bug%20inert-upgrade-preview-and-attestation-display.md), AC-7 |

## Qualification follow-up

Five residual failures were reproduced in `test_upgrade_wavefoundry.py`: two with `second` and three with `prompt-names`. These are fixture/oracle defects: a double-quote-only source substitution, assertions using shipped prompt destinations, and positive render fixtures lacking the readable prompt manifest required by profile migration. Change 203h9 repairs those tests while retaining historical input names, exact byte and manifest assertions, and real rendering before indexing.

| Check | Result |
| --- | --- |
| Shipped-profile focused regression group | 6 tests passed, zero skips |
| Upgrade owner under `second` | 681 tests passed, two existing skips; 43.810 seconds |
| Upgrade owner under `prompt-names` | 681 tests passed, two existing skips; 43.741 seconds |
| Deliberately broken variants | Removed invalid-profile guard, premature downstream step, and corrupted migrated prompt bytes each detected |
| Full canonical suite | 11,885 tests across 173 files passed, 20 existing skips; 431.917 seconds; fresh green receipt |

Canonical receipt: `2026-10-08T19:13:12.019056+00:00`, input hash `dde11ab2ef7918216ee07fa1ab0244033acfd6bc8f590157818322a084e17c2f`. The earlier attempt was rejected for concurrent documentation writes; this quiet-tree run is the delivery evidence. Independent [code](code-delivery.md) and [QA](qa-delivery.md) reports document exact-output mutations and the preserved missing-manifest and unwired-render controls.

No new skips were introduced. Focused profile runs are diagnostic evidence and never write the canonical delivery receipt. The exact profile destination assertions use the declared-profile APIs; they do not independently prove the correctness of those getters.

## Limits and adoption notes

- An unchanged older runner retains its own old final-line wording. The incoming extension reports preview-log writes, while the updated runner also corrects the final line. This is disclosure of the preview log, not a promise that dry runs write no files.
- Scratch declaration resets support the profile system's single-line editable assignments; unsupported multiline declarations fail explicitly.
- The council display constant controls runtime and newly rendered surfaces. Raw seed prose and existing project-authored text still require distribution reconciliation.
- The full suite ran under shipped defaults; the two profile qualifications cover the upgrade test owner. This is not an execution in Waveforge's own renamed checkout. Waveforge should rerun its suite and upgrade rehearsal after merging.
- Broader historical feature-named filenames and the held unknown hook-tool-name work are separate follow-ups, not part of the resolved public addendum.
