# C5 preservation — fresh focused review

Owner: Engineering
Status: draft
Last verified: 2026-10-08

Fresh independent architecture/docs-contract context `wf-204mp-independent-recursive-04` found seven actual installing/reinstall failures against required 204mn AC-2. Its independently authored 25-case CRLF-byte matrix passed 18 cases, failed seven, and ran in 19.493s. The existing C5 owner passed 16 tests without skips in 26.439s; those tests did not cover the seven counterexamples. All 23 current packet hashes remained unchanged before/after the completed review.

Recursive quote/list alternation, partial omitted markers, lazy paragraphs, wide ordered lists, fenced-body markers and valid multiline code spans pass. New finding ARCH-DOC-204MP-02 groups three adjacent mechanisms within render_agent_surfaces._role_link_mask_code:

- Four live links remain at the old role destination because global backtick pairing crosses blank, heading, quote or list block boundaries.
- A live link surrounded by escaped backticks remains at the old destination because escaped opening punctuation incorrectly starts a code span.
- Root and quoted equals-style setext headings fail to end paragraph state, so the immediately following four-column code destinations are rewritten.

These are ordinary supported syntax. CommonMark parses inline content inside individual blocks, treats escaped punctuation literally outside code spans and recognizes setext headings as blocks; an indented code block can follow a heading. Primary grounding: [parsing strategy](https://spec.commonmark.org/0.31.2/#appendix-a-parsing-strategy), [escapes](https://spec.commonmark.org/0.31.2/#backslash-escapes), [setext headings](https://spec.commonmark.org/0.31.2/#setext-headings), [indented code](https://spec.commonmark.org/0.31.2/#indented-code-blocks).

The actual path is upgrade_wavefoundry.phase_surface_rendering through extracted render_platform_surfaces and render_agent_surfaces.migrate_council_role_renames. Every case exercises installation twice, checks exact bytes and confirms the role move. Reproducer `/tmp/wf-204mp-independent-recursive-04.py`; complete observations `/tmp/wf-204mp-independent-recursive-04-results.json` and `.log`. Its genuine current-tree failures supply negative controls, not new source mutants. No shared source/state mutation, final approval, canonical suite, native-platform qualification or live downstream merge occurred.

Repair remains bounded to the mask and its existing installing test owner: retain original offsets while pairing spans inside inline-bearing blocks, respect escaped opening delimiters, preserve legitimate multiline/lazy spans, and recognize setext transitions before classifying following indentation. The original recursive finding remains open until actual lane reverification, and this new finding requires its own recorded repair start before source mutation. Full canonical qualification and fresh post-repair review remain pending.

## Implemented repair, awaiting reverification

The recorded ARCH-DOC-204MP-02 cycle-1 repair start preceded the repository edit. The existing ordered container classifier now forms inline regions per paragraph/heading, applies escape parity only to opening punctuation outside a span, and recognizes setext transitions before subsequent indentation. Matching delimiters inside legitimate multiline/lazy spans remain active. Original character offsets and CRLF bytes are retained; no I/O, preview-loader or profile authority boundary changed.

The actual C5 upgrade owner passes 17 tests, zero skips, 63.157s, including a durable 35-case installing/reinstall matrix from the 25 fresh counterexamples and ten additional escape, heading, setext, sibling-list and lazy-span controls (`/tmp/wf-204mp-block-c5-owner.log`). All four new source mutants and all six recursive/container mutants are detected through actual incoming-driver byte assertions (`/tmp/wf-204mp-block-mutants.log`, `/tmp/wf-204mp-block-recursive-mutants.log`). The upstream census inventory now includes the admitted graph repair's new test owner: maintainer check verifies 524 files; the three distribution owners pass 107 tests without skips in45.340s. The first owner command lacked the framework import path and is not evidence; the corrected PYTHONPATH run is the reported pass.

AC-2 is complete on implementation evidence only. Both typed preservation findings remain open until fresh architecture/docs-contract reverification; full upgrade-owner, canonical setup/suite and delivery approvals remain pending. No full CommonMark implementation or native/downstream qualification is claimed.

Whole upgrade owner now passes701 tests, two existing native-platform skips,102.854s (`/tmp/wf-204mp-block-upgrade-owner.log`). No source changed after that run. The refreshed23path packet also records the separately admitted graph repair changes to shared data/testing architecture docs; those do not alter the C5 mask contract. Fresh independent delivery review remains pending.
