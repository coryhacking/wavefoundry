# Changelog

All notable changes to this project are documented in this file and in
the individual wave records under [`docs/waves/`](docs/waves/).

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.16.3] - 2026-08-13

### Fixed

- **The Claude MCP registration names the server file again instead of embedding an inline Python
  program.** `.mcp.json` launched the server through `python3 -c "import os,runpy; …"`, and a
  Git-tracked configuration that executes a code string is flagged by enterprise security tooling: a
  config that names a file is auditable, a config that carries a program is a code-execution surface.
  It now reads `"args": [".wavefoundry/framework/scripts/server.py"]`, matching what the Antigravity
  and Codex registrations already shipped. **Existing repositories migrate on the upgrade that
  installs this** — the surface render rewrites the stale stanza in place rather than merging
  alongside it, and a non-Wavefoundry server in the same file is left untouched.
  Wave 1v7a3 / change 1v7a2.

  Nothing is given up in how the server finds your repository: it anchors on its own install
  location, above any environment variable, so no `--root` and no project anchor belongs in the
  stanza. The inline wrapper only ever helped the interpreter locate the file. The supported contract
  is repository-root launch, which is what MCP clients do; if a client ever spawns the server from
  another directory it now fails at startup with a missing file rather than binding to the wrong
  repository.

  **Hook launchers are deliberately unchanged and still use `CLAUDE_PROJECT_DIR`.** Hooks are
  invoked by the host from an unknown working directory and that failure is reproduced, not
  theoretical, so the two surfaces are treated differently on purpose.

## [1.16.2] - 2026-08-12

### Fixed

- **A broken review-protocol marker now fails the docs gate instead of silently freezing the
  content it guards.** Reviewer role docs carry a framework-rendered `wave:executable-review-evidence`
  region. When its begin and end markers were not properly paired, the renderer left the file
  untouched and printed one line to stderr, while `docs-lint` reported ok and the docs gate passed.
  Downstream this went unnoticed across four role docs and a full upgrade cycle: those docs stopped
  receiving review-protocol updates and nothing reported it. The sibling `wavefoundry:review-policy`
  family already treated a malformed marker pair as a failure; both families now share one
  implementation of that rule, so they cannot drift apart again. **Operator-visible change: a
  repository whose markers are already broken will fail its next docs gate rather than pass
  quietly.** Adopting the shared rule also brings the second half the review-policy family already
  had: a well-formed region whose content no longer matches its registered source now fails too,
  in either drift direction. That case is largely self-correcting during an upgrade, because the
  render runs before the docs gate and re-renders the region; it bites when a region is hand-edited
  and linted without re-rendering, which is what it is for. The failure names the file and the
  specific condition. Nothing is auto-repaired; repair the markers and re-render.
  Wave 1v4mw / change 1v4mt.
- **The upgrade summary reports carriers the render skipped, as `renderer_warnings`.** This finding
  previously existed only as a stderr line among roughly 90 others, absent from the structured
  summary, on a run that reported `failed_phase: null`. It now sits beside `reconciliation` and
  `host_permission_flags`, and prints in the operator summary on every run that produces one,
  including patch upgrades and failed phases. Unlike `renderer_provenance_flags`, these do not
  self-heal. Wave 1v4mw / change 1v4mt.
- **A rejected CoreML probe now says why it was rejected.** The probe runs the production graph in
  a crash-isolated child and captured that child's stderr, then reported only that it had failed.
  Diagnosing one field occurrence cost a full reverse-engineering session and still did not find
  the cause. The warning now carries the child's return code and a bounded, path-scrubbed tail of
  its stderr; absolute paths collapse to basenames so a traceback stays readable without publishing
  the host's filesystem layout. A passing probe stays silent. What the probe decides, and when it
  runs, are unchanged. Wave 1v4mw / change 1v4mu.

- **The upgrade no longer instructs a retired step on every run.** The editing-pass output told
  operators to perform "Journal reconciliation (seed-160 step 0 / Reconcile journals)", which was
  wrong twice over: the journal system is retired, and seed-160's step 0 is pack adoption, not
  journal work. The step is removed and the remaining steps renumbered. Wave 1v4mx / change 1v4mv.
- **The retired-surface reconciliation scan now reports two more surfaces.** Migrations move files
  but nothing reconciled the instructions pointing at them, so a repository that ran every
  prescribed migration still carried instructions naming things that no longer exist. The scan now
  reports references to the retired journal system, and `.md` references to prompt files that now
  carry `.prompt.md`. The prompt check resolves against your tree rather than matching text, so a
  prompt doc that genuinely ends in `.md` is never flagged, and every stale reference on a line is
  reported rather than the first. Findings stay **report-only**: the scan never edits your files,
  and a repository with no stale references reports none. Wave 1v4mx / change 1v4mv.

- **The generated-surface manifest now reconciles against the framework default instead of freezing
  at install time.** `docs/prompts/prompt-surface-manifest.json` is renderer-managed, so the
  reconciliation scan excludes it, and the gardener only ever stamped a date onto an existing file.
  Nothing reconciled it, so its generated-artifact list drifted permanently. The drift runs in both
  directions and the second one is the more consequential: entries retired from the framework
  lingered forever, **and** entries added to the framework never reached a repository installed
  before they existed, leaving the framework's own record of what it generates incomplete. The
  gardening pass now reconciles that list. Keys the default does not model are untouched, a manifest
  that already matches is not rewritten, and a retired `agent_journals` feature entry is pruned.
  Wave 1v79z / change 1v7a0.
- **A reconciliation finding that is correct as written can now be settled once.** The scan had one
  disposition, unresolved, so a sentence *recording* that something was retired could be silenced
  only by rewriting that sentence — which the framework's own seeded policy forbids: seed-160 and
  seed-220 both state that retiring a file removes the file, not the historical record of it. Mark
  such a finding as a historical record in `docs/reconcile-dispositions.json` and it stops being
  reported. The marking is **per finding, not per file**, so a live stale reference in the same file
  still reports; and it is keyed to the matched text, so changing that text reports the new text as a
  new finding rather than inheriting the old judgment. A repository that marks nothing is unaffected.
  Wave 1v79z / change 1v7a1.

### Changed

- **The small-batch CPU routing message no longer reads like a failure.** Routing a sub-batch-sized
  incremental run to the CPU embedder is a deliberate optimization, but printed next to a GPU
  degradation warning it was read as a second fault. It now states that it is an optimization, not
  a failure, and that GPU use is unchanged for larger runs. Wave 1v4mw / change 1v4mu.

## [1.16.1] - 2026-08-12

### Fixed

- **INT8 embedding vectors no longer depend on which other chunks shared their inference
  batch.** This affects CPU-bound hosts only. The INT8 export derives one activation scale per
  tensor across the whole batch, so a chunk's stored vector shifted depending on its neighbours.
  Two things followed: re-indexing the same corpus was not reproducible, because chunk ordering or
  a change in chunk count moved batch boundaries and reassigned neighbours; and every query was
  encoded in a different regime from the bulk index, because a full batch carries no padding rows
  while a query is one row plus 31 of them. Measured against the index it searched, a query sat at
  cos 0.996160. The INT8 path now encodes one row per inference call, so a vector is a function of
  its own text alone and query and index agree exactly. Throughput is unchanged (0.96x of the
  previous batched path) because the graph padded every row to 512 tokens regardless, so batching
  was buying nothing here, and the CPU-bound query path's peak resident memory drops from roughly
  1353 MiB to 245 MiB. **Upgrade cost: CPU-bound repositories re-embed both semantic layers once
  on this upgrade. GPU-class repositories re-embed nothing** and are unaffected, because the FP16
  graph carries no quantization operators and its vectors did not move. Wave 1v454 / change 1v453;
  rationale and the constraints it imposes are recorded in ADR `1v22e`.

## [1.16.0] - 2026-08-11

### Changed

- **Retrieval now uses one supplier-lineage-compliant Snowflake Arctic S
  embedder for documents and code.** CPU uses INT8, supported GPU providers use
  FP16, embedding batch is 32, and MiniLM L6 remains the batch-40 reranker. The
  independently configurable layer selectors share one instance when equal.
  Model set v2 and its matching offline companion are mandatory for release
  builds; upgrades remove only verified Wavefoundry-owned retired BAAI cache
  components after the complete v2 semantic epoch is durable. On hosts without
  the fd-anchored deletion capabilities (native Windows), cleanup uses a
  revalidated no-follow fallback whose check-to-use guarantee is narrower than
  the fd-anchored path. Removal applies to the user-global model cache shared
  by every repository on the machine: sibling repositories still on older
  versions re-fetch the retired models from Hugging Face on their next index
  build, so offline or controlled machines should upgrade all repositories
  together. Wave 1v0r0 / change 1v0qz.
- **The first index build after this upgrade is a one-time full re-embed of
  both semantic layers.** The shared embedding model fingerprint changed with
  model set v2, so documents and code are each re-embedded from scratch once;
  expect operator-visible foreground work proportional to repository size.
  Upgrades now build both index layers in the foreground and the detached
  background code pass is removed, so when the upgrade reports complete, the
  semantic index is fully published. Wave 1v0r0 / change 1v0qz.

### Fixed

- **`code_ask` now puts an exact, source-current declaration first when a
  broader question names a known symbol.** The correction is language-neutral
  wherever the published graph provides a declaration-capable node, preserves
  the rest of the hybrid context, and fails closed to ordinary retrieval when
  the graph or source receipt is stale, ambiguous, or unavailable. Direct
  `code_definition` remains the preferred low-latency lookup tool. Wave 1v08w
  / change 1v08v.

- **A readiness approval that could never satisfy a gate is now refused instead of
  silently accepted.** Recording a readiness approval while a policy input had already
  moved returned `ok` with no diagnostics, wrote a permanently unusable record into the
  append-only review ledger, and left you to discover it only when the next Prepare
  lapsed the approval. It is now refused, and the refusal names the current receipt, the
  pending receipt, which receipt fields differ, and which change documents were digested.
  Recovery is one `wf_prepare_wave(mode='ready')` plus one approval per readiness lane.
  This covers every receipt-bound readiness key, not just the council key -- specialist
  lanes were accepting stale binds too. An idempotent retry of an already-recorded
  approval still replays without appending, as before.
- **Closing a wave no longer requires less review after the refusal than before it.** The
  close-time carve-out for waves that predate the review policy keyed on approval absence,
  and a refused approval is also absent -- so doing the right thing produced a weaker close
  gate than ignoring the problem. It now keys on whether the wave was ever prepared under
  the policy, and both branches of that gate are covered.
- **A lapsed approval now tells you why it lapsed.** Every failure of the approval-validity check
  reported the same reason, "invalid actor or independence", even when both were fine and the real
  cause was a superseded receipt -- so the message sent you to re-check the recording agent when
  the fix was one re-Prepare. The reason now names the condition that actually failed, and the
  no-current-receipt and malformed-context cases each get their own message. Re-deriving the
  review state of every approval ever recorded in this repository produced zero changes: only the
  reasons get truthful, no approval flips.
- **`wf_prepare_wave(mode='dry_run')` now tells you a receipt mint is pending.** The
  preview was the one surface silent about the mutation it previews; the signal existed
  only buried in the response payload. It is reported as an advisory, so a pending mint --
  the ordinary state after any change-doc edit -- does not turn your preview into a failure.
- **`wf_mark_ac(state='~')` now says when it superseded your receipt.** Deferring an
  acceptance criterion publishes a new receipt and moves any current readiness approval to
  non-current; that was reported only as a payload field, so it read as a silent success.
- **Recordkeeping edits no longer lapse your review approvals.** Editing a boilerplate
  `## Session Handoff`, a Windows checkout, a stray trailing space, an editor that strips
  whitespace on save, a missing or extra newline at end of file, or reordering the `## Changes`
  entries in a wave record all moved the review-policy digest and lapsed every approval the wave had
  collected, with no claim changed. None of them do now. The `## Session Handoff` exclusion is
  deliberately conditional: it applies only when the section body is exactly the shipped template
  sentence, so the 5% of change docs that use that section substantively stay fully reviewable.
  Trailing whitespace inside a fenced block is preserved, because there it can be the subject rather
  than the formatting. Measured across every change document in this repository: zero lost review
  lanes, zero changed council triggers, zero changed council seats.

  **Lane selection no longer depends on invisible whitespace.** Four kind triggers were matched with
  a literal trailing space, so a line ending `-bug ` recruited a lane and a line ending `-bug` did
  not. The trigger is the token. This widens matching slightly and only ever adds review: one
  document in this repository gains `qa-reviewer`, none loses anything.

  **One-time re-Prepare on upgrade.** `REVIEW_POLICY_EVALUATOR_VERSION` advances to `7` -- its final
  value in this release -- so the permanent `events.jsonl` history can tell a plan edit apart from
  this canonicalization change. Upgrading from 1.15.4 pays for this once, together with the other
  evaluator steps below, not separately; see the net transition under **Changed**. Any
  wave that is readied or open when this lands goes stale once at its next `wf_prepare_wave` and its
  READINESS-phase approvals lapse once; re-record them and the receipt settles. Delivery-phase
  approvals, finding heads, and repair records are untouched, and CLOSED waves are untouched. Note
  the re-digest happens because the canonicalizer changed, not because of the bump; the bump is what
  lets the ledger attribute it.

  **A heading that disables its own exclusion now says so.** `## Progress Log (delivery)`,
  `### Progress Log`, a duplicated heading, or any near-miss variant silently switched that section
  back into the digest, so narration started superseding the receipt with nothing naming the cause.
  Prepare now reports it by name. No document in this repository is currently in that state.

- **A change-doc template that declares review targets is now a lint error, and the upgrade repairs
  it for you.** Reported from the field by a repository running an earlier build: its `docs/plans/plan-template.md`
  carried an example under `**Review targets (repo-relative paths):**` that was **not** fenced, so the
  template itself declared `path/to/file.swift` and `docs/specs/`. Every plan created from it was born
  in declared mode and silently lost review lanes it should have had: reproduced here, a plan scored
  against a clean template recruits three lanes, and the same plan against the contaminated template
  recruits one. The reporting operator also saw a lane recruited by a placeholder path they never
  chose. docs-lint now fails when a scaffold declares anything, naming the targets it found and the
  fix. **In the shapes the framework itself teaches, you do not need to repair the template by
  hand:** the upgrade that installs this rule fences the example block for you before the docs gate
  runs, and prints what it changed, so an already affected repository upgrades cleanly rather than
  halting. (That report goes to the console as the upgrade runs; it is not written to
  `.wavefoundry/logs/upgrade.log`.) This covers a plain example bullet, a `**Review targets…**` block, several of either, and
  any of those sitting beside an example you had already fenced. If your template is shaped in a way
  the upgrade does not recognize, it changes nothing and tells you so, naming the file and the fix
  rather than guessing at your content. The same repair also runs on `--resume-after-gate`, which is
  the path the upgrade's own halt message directs you to.

  **Scope is deliberately narrow.** Only the template is checked and only the template is repaired.
  Your authored change docs are never blocked and never rewritten, because the repair cannot safely
  edit content you wrote and a closed wave's history is not rewritable at all. No placeholder
  detection ships: measured across this repository's change documents, every literal placeholder
  pattern matched none of the real declared targets, so such a rule would have caught nothing. The
  one heuristic with any reach, "the declared target no longer exists on disk", matched a single
  path, and that match was a legitimately deleted historical file rather than a placeholder. Zero
  catches and a false positive is the combination that teaches you to ignore a warning.

- **One sentence of prose in `## Serialization Points` no longer removes required review lanes.**
  Any path-shaped token found in that section was read as proof the author had adopted the
  declared-target contract, so a narrative mention of a directory switched the change doc out of
  prose scoring. Measured worst case: a plan whose section said "shared with the wave that also
  touches the docs/ folder" went from two required lanes to **none**. Worse, adoption was decided
  per WAVE, so one plan declaring targets silently emptied an un-migrated sibling's coverage in the
  same wave. Adoption is now decided per **document** and the results union, so migrating one plan
  can never reduce another's review. A target is declared by a bullet whose content is entirely
  repo-relative paths, or inside an explicit `**Review targets (repo-relative paths):**` block whose
  backtick-quoted entries may contain spaces; prose declares nothing in any shape, including prose
  written as a bullet. Across this repository's 814 change docs the stricter rule reclassifies 101
  documents from declared to whole-document scoring, **95 gain lanes and none lose any**.

- **A declared path containing a space no longer yields zero required lanes.** Path extraction had
  no space in its character class, so a real wave-owned target such as
  `docs/waves/<id> <slug>/wave.md` shredded into fragments, and a fragment was accepted as a
  declared target: it matched no risk trigger, suppressed the fallback, and left the document with
  an empty roster. Declaring a genuine on-disk artifact was therefore actively harmful. Spaced
  targets are now declarable inside the explicit block, and a shredded fragment declares nothing.
  A related parse defect is repaired with it: `git status --porcelain` rename entries quote each
  side independently, so a renamed spaced path never matched the wave footprint.

- **A freshly scaffolded change doc no longer declares a target its author never wrote.** The
  shipped template's placeholder bullet extracted `src/app/handler.py`, so every new change document
  was born in declared mode with a code-reviewer-only roster before anyone had declared anything.

- **The review-policy digest stops rewriting body prose it promises to leave alone.** The leading
  metadata carrier was bounded by line SHAPE, so any body line reading `Word: text` held the region
  open and a later `Status:` line in the document body was normalized away. A contract edit on that
  line was invisible to the receipt, meaning an operator could change a document's meaning and the
  recorded approvals would not lapse. The carrier is now bounded by a known-key allowlist, and a
  blockquote inside it no longer truncates it early. One document in this repository is affected and
  its wave is closed.

- **Upgrade note (one-time re-Prepare).** These two fixes move lane semantics and the digest
  boundary together and ship as a single evaluator-version bump, one of the intermediate steps
  folded into this release's net `4`-to-`7` transition. Every **non-closed**
  wave needs exactly one re-Prepare to publish the current version; repeated Prepare is idempotent
  after it. Approvals recorded against the old receipt lapse once at that re-Prepare and must be
  re-recorded. **Closed waves and their event ledgers stay byte-immutable.** Change docs need no bulk
  re-authoring: an undeclared plan keeps whole-document scoring, which is more review, not less. A
  plan whose Serialization Points are prose sentences is now treated as undeclared; re-declare it in
  one of the two supported forms to get its precise roster back.

- **A repository whose `wave_review` is an empty object can upgrade again.** The migration treated
  only an absent key as unset, so a config carrying `"wave_review": {}` hard-failed the preflight
  with `wave_review.enabled must be boolean` before any change was made, and the upgrade could not
  proceed at all. An empty object now means what an absent key means. Genuinely malformed policy is
  still rejected exactly as before.

- **The upgrade no longer asks you to hand-edit files it ships.** The retired-prose preflight scanned
  the `.wavefoundry/` root, where the pack delivers `README.md` and `CHANGELOG.md`, and refused to
  proceed until the operator rewrote prose they did not author and must not maintain. The whole
  `.wavefoundry/` tree is now treated as framework-owned; your authored surface under `docs/` is
  still scanned exactly as before. The changelog case was the more serious half and had not yet been
  hit: a release history must name retired concepts to do its job, so the first note that did would
  have blocked every target repository.

- **Admitting a change fills in an `<wave-id>` placeholder.** The `Wave:` repair recognized only
  `[wave-id or TBD]` and bare `TBD`, so an angle-bracket placeholder was left for the operator to
  correct by hand. Recognition widens to bracketed forms only: an operator-authored `Wave:` value is
  still never overwritten, and dry-run still writes nothing.

  **When these take effect depends on your upgrade path.** Crossing from a pre-1.15 protocol-1
  installation, the bridge installs the new framework and then runs the upgrade from it, so all three
  fixes apply on that same run and no manual repair is needed. On an ordinary protocol-2 to
  protocol-2 upgrade the review-policy preflight deliberately runs before any extraction, using the
  framework already installed, so these fixes take effect from the **next** upgrade. If that preflight
  is what is blocking you today on a protocol-2 install, repair it once by hand and the following
  upgrade will not ask again.

- **Validation errors now state the values that would satisfy them.** Failures whose validity is
  defined by a fixed set render that set from the same constant the check used, so the printed
  values cannot drift from the rule. Status shape checks name the full vocabulary; rejected
  transitions and blocked dependencies name the subset valid from the current value and name that
  value; the watchpoint message no longer lists three of its six markers. Publishing a set is
  guidance, not a gate: no membership check was added and nothing that linted clean before this
  change fails after it.

- **`wf_review_wave` accepts the approval-phase vocabulary.** `readiness` and `delivery` now map onto
  the `prepare` and `implementation` review phases instead of being rejected, and the invalid-phase
  message states the mapping in both directions.

- **`wf_prepare_wave(mode='evaluate')` is documented where callers can find it.** The read-only alias
  was already accepted but appeared in no tool docstring and in no shipped lifecycle prompt.

- **A change document that cannot be read no longer crashes the tool you reach for first.** A file
  that is not valid UTF-8 -- a bad checkout, a mangled paste, a wrong-encoding save -- raised a stack
  trace out of `wf_prepare_wave` instead of telling you which document was broken. Twelve read sites
  were involved, not the two originally reported, and the recovery tools were among them --
  `wf_get_change` and `wf_list_plans` are exactly where the diagnostic sends you, so the crash
  repeated one tool over. Every lifecycle boundary now returns a `change_doc_unreadable` diagnostic
  naming the document and the cause: prepare, implement, close, `wf_get_change`, `wf_list_plans`,
  `wf_add_change`, and the `wavefoundry://change/{change_id}` resource, which renders
  `# Unreadable Change` rather than an empty body. A bulk `wave_id` lookup still returns the readable
  siblings, and `wf_list_plans` still lists the readable plans, each unreadable entry carrying a
  `read_error` instead of parsed content. No failure message carries your absolute filesystem path.

  **Two behavior changes are deliberate rather than incidental.** An unreadable admitted document used
  to be skipped silently at close, so the close hard gate passed over a document it could not verify;
  it is now a blocker. And one unreadable document no longer disables the retrieval-posture scan for
  an entire wave -- that check reads per document instead of aborting the whole pass. Waves whose
  documents all decode normally are unaffected.

  **`wf_add_change` refuses before it moves.** Making the resolver honest about unreadable documents
  also let `wf_add_change(mode='create')` reach the relocation step and move a file it could not read.
  It now checks readability first and refuses without touching anything.

- **A wave record that cannot be read no longer crashes every lifecycle tool.** The companion gap
  to the change-document fix above: an undecodable `wave.md` raised a stack trace out of every
  tool probed, including the enumeration tools you would reach for to diagnose it, and a
  permission-broken record was reported as `wave_not_found` at every by-id boundary -- the wave
  exists, and the tools said it did not. Wave-record reads now flow through a single seam: twelve
  by-id lifecycle tools plus `wf_create_wave` refuse with a `wave_record_unreadable` diagnostic
  naming the record and the cause, `wf_list_waves` and `wf_current_wave` list the readable waves
  and carry a per-entry `read_error` for the broken one, wave resolution reports what it actually
  found instead of swallowing the failure, and the `wavefoundry://wave/{wave_id}` resource renders
  `# Unreadable Wave`. No message carries your absolute filesystem path. Healthy records are
  unaffected, verified byte-identical across sixteen enumeration and lifecycle surfaces.

- **A missing admitted change document now blocks close instead of vanishing from it.** The close
  hard gate verified the checkboxes of every document it could find and silently skipped an
  admitted document whose file was gone, and the close summary then fabricated an empty delivered
  record for it. Close now refuses with a `change_doc_missing` diagnostic naming the document,
  the summary raises rather than recording work nobody verified, and docs-lint reports the
  missing file as soon as the wave is implementing, so the discovery does not wait for close.

- **The upgrade's rollback-failure detail no longer embeds absolute filesystem paths.** When a
  rollback itself failed, the double-fault report interpolated raw exception text -- exactly where
  the operating system embeds the full path -- defeating the path-stripping helper this release
  ships everywhere else. The detail is now composed path-free at the raise site, and the
  review-ledger read path that produces the same class of detail was made path-free with it.

- **The receipt-authority documentation matches what the code does.** Five statements in the
  architecture reference described the system as it was before the previous release: that Prepare is
  the sole writer of the review roster and receipt (`wf_mark_ac(state='~')` is a second writer), the
  evaluator version, the count of tools that report avoided context, the count of lifecycle tools
  that record telemetry debits, and the event-ledger ownership row that omitted both receipt
  writers. The closure rule in the shipped review-system seed also described a carve-out no
  predicate implements. All are corrected, and installed repositories see the seed correction at
  their next upgrade.

- **An unreadable wave record no longer weakens the review gates it should be blocking.** When a
  declared wave's `wave.md` could not be read, the review authority resolver silently reclassified
  the wave as legacy prose with empty text on a permission failure, and crashed outright on a
  wrong-encoding one. In the worst case the close-time gate read the silent downgrade as "this wave
  predates the review policy" and dropped the council-readiness requirement from the close roster,
  so a broken record demanded less review than a healthy one. Both causes now return a structured
  refusal that every downstream gate treats as fail-closed, the readiness requirement stays on the
  close roster, and the diagnostic names the file and the cause without your absolute filesystem
  path. Readable records classify exactly as before, verified by a zero-diff comparison across
  every wave record in this repository.

- **The dashboard now shows you the broken records you opened it to investigate.** A wave record
  that was not valid UTF-8 crashed the entire snapshot, a permission-broken one vanished from the
  list with no trace, and whether either happened depended on the server's working directory. A
  change document with the same encoding problem crashed the snapshot from one function away. Each
  broken entry now renders as a degraded row that names the cause (path-free), healthy siblings
  are unaffected, path resolution is anchored to the repository root instead of the working
  directory, and a healthy corpus renders a byte-identical snapshot before and after the change.

- **Review findings that cite code now anchor by symbol.** The citation rule that already governed
  plans and implementation reaches the surfaces where review evidence is authored: the evidence
  record's `artifact_or_test_id` and prose, the council seat's finding-authoring guidance, and the
  runtime prepare-council brief a seat actually receives at readiness. A symbol anchor resolves to
  today's text; a bare line number drifts hardest exactly when a sibling wave edits the target.
  The five deliberate line-anchor cases (constant blocks, data files, generated artifacts,
  hand-authored prose, historical citations) stay legitimate and must be named inline. Installed
  repositories see the seed half at their next upgrade. Every shipped carrier of this rule,
  across the planning, implementation, evidence, and council surfaces, is now pinned by a test,
  so a drifted copy can no longer reach target repositories through an upgrade unnoticed; that
  is how an earlier weakening of this rule escaped.

- **docs-lint now catches a rendered review-policy region that drifted from its source block.**
  A policy block edited without re-rendering, or a hand-edit inside a rendered marker region,
  passed lint with the two carriers disagreeing. The new check compares each rendered region
  against its block using the renderer's own composition -- never a second implementation of it --
  and names the destination and the repair. Target repositories already self-heal at every
  upgrade; this closes the drift window in between.

### Changed

- **Advancing a change's `Change Status` no longer lapses the readiness approvals.** Marking a change
  `complete` is progress, not a change to the agreed contract: it edits no Requirement, Scope,
  Acceptance Criteria, or AC Priority text, so it is now digest-neutral and the readiness roster it
  was granted against stays current. This continues the direction set by the Progress Log exclusion
  and by making AC completion and task marks progress-only, while an AC `[~]` still counts as a
  contract change and still lapses approvals. **Verification of the work is unaffected:** closing a
  wave still requires the delivery lane approvals and operator signoff regardless of any status
  value. Previously, advancing a change superseded the review-policy receipt and forced a re-Prepare
  plus a full re-record of readiness approvals against plan text that had not changed by a byte.

- **Review-policy receipts move to evaluator version 7, which costs one re-Prepare in total.** The
  last released version was 4, and this release carries every intermediate step, so upgrading from
  1.15.4 is a single 4-to-7 transition and not three. Any wave that is readied or open when this
  lands goes stale once at its next `wf_prepare_wave`; re-record the readiness approvals and the
  receipt settles. Closed waves are untouched. The notes under **Fixed** describe each intermediate
  step and what it changed; versions 5 and 6 never reached a release, so you never pay for them
  separately.

- **The retrieval-posture advisory is now bounded to the wave's declared files.** It counts only
  changed files matching the `## Serialization Points` of the wave's admitted change docs, so
  unrelated working-tree dirt can no longer become evidence about your wave. The consequence worth
  knowing: a wave whose changes declare no Serialization Points has no trustworthy signal, so the
  advisory stays **silent** for it rather than guessing.

- **Automatic review lanes are no longer recruited by prose that merely mentions a path.** For waves
  predating the Serialization Points contract, the legacy fallback now requires a genuine
  path-shaped match. Required lanes can therefore **drop** for an undeclared wave whose only trigger
  was a bare file extension or a Progress Log line. Declaring Serialization Points replaces the
  fallback with exact per-path reasons for the declaring change doc; adoption is decided per
  document, so an un-migrated sibling in the same wave keeps its own fallback coverage.

## [1.15.4] - 2026-08-06

### Fixed

- **Installations from 1.8.0 onward now upgrade directly to the current release.** The upgrade
  bridge previously accepted only an exact 1.14.0 source, which forced every other supported
  installation to stage through an intermediate release before it could move. The bridge now
  enforces a 1.8.0 minimum-source floor instead, so any protocol-1 installation at or above that
  version crosses in a single run. The integrity boundary is unchanged: a source below 1.8.0, a
  source this release would not advance, and an installation already on protocol 2 are each still
  refused with their own distinct message, and a missing or malformed source version still fails
  closed.

- **Admitting a change now fills in its `Wave:` field, and preparing a declared wave no longer
  reports absent legacy prose as a defect.** `wf_add_change(mode='create')` replaces only an exact
  `Wave: [wave-id or TBD]` or `Wave: TBD` scaffold value with the containing wave ID, so docs
  validation stops failing on a value the tool already knew. An operator-authored `Wave:` value is
  never overwritten, and dry-run stays read-only. For waves declaring
  `review-evidence-source: events.jsonl`, `wf_prepare_wave` now derives readiness from the current
  typed `wave-council-readiness` approval and its review-policy receipt instead of also demanding a
  hand-authored `## Review Checkpoints` verdict, which previously made a successful readiness pass
  look invalid. Legacy prose-only waves keep their existing structured `prepare-council` authority
  and validation unchanged.

- **Upgrades now reconcile all scalar docs-vs-code facts they own.** The
  snapshot/reconcile guard covers embedding and reranker model names, chunker,
  state-store, and graph-builder versions across extraction and crash-resume;
  edited, duplicate, or missing claims remain fail-safe for docs-lint.

- **Deferring a required acceptance criterion now refreshes the review receipt in the same operation.**
  `wf_mark_ac(state="~")` publishes the changed contract and returns fresh review actions without
  carrying approvals forward; failed publication rolls back the AC, receipt ledger, and projection.
  Ordinary completion and task marks remain receipt-neutral. Wave 1uj12 / 1ulnu.

- **Routine checkbox tracking no longer reopens review, while an acceptance-criterion deferral still does.**
  The receipt canonicalizer now treats AC completion and every task marker as progress-only, but
  preserves an AC `[~]` and its rationale as a reviewable contract change. `wf_mark_ac` and
  `wf_mark_task` supply the same narrow write path: each changes one unambiguous item, while the AC
  tool applies exactly the existing docs-lint rationale rule for required-priority deferrals.

- **Automatic review lanes now come only from declared `## Serialization Points` paths, not plan
  prose.** This removes false lanes triggered by quoted filenames and change IDs, keeps extension
  matching boundary-aware, and makes the existing wave-level `Requested review lanes` field the
  explicit route for security and performance risks. Evaluator version 4 marks only non-closed waves
  with an older current receipt for one re-Prepare during upgrade; a newly planned no-receipt wave is
  untouched.

- **Guided review actions now include the caller schema once per response and carry the current
  judgment template for reverification.** The response names the blocking constraint without
  weakening the evidence validator or duplicating the schema onto every action.

- **Recording a repair in a change doc's `## Progress Log` no longer lapses the approvals that the
  repair did not touch.** The review-policy receipt digests change-doc bytes, and `AGENTS.md`
  requires every repairer to log what they did, so the mandated act of logging a trivial repair
  moved the digest, superseded the receipt, and forced a re-Prepare plus a re-record of the whole
  readiness signoff roster. The digest now replaces the Progress Log body with a stable sentinel,
  exactly as it already does for the gardener-owned `Last verified:` date. This is the only new
  exclusion, it is hash-only (the section stays in the file verbatim, and the `Gapfill:` retrieval
  advisory still reads it), and every requirement-bearing section (Rationale, Requirements, Scope,
  Acceptance Criteria, Tasks, AC Priority, Decision Log, Risks, Session Handoff) still lapses
  approvals on edit. Review coverage is unchanged: the same lanes run and the same findings block.
  **One-time re-Prepare on upgrade.** `REVIEW_POLICY_EVALUATOR_VERSION` moves from 2 to 3 so the
  permanent `events.jsonl` history can tell a plan edit apart from a canonicalization change. Any
  wave that is readied or open when this lands goes stale once at its next `wf_prepare_wave` and its
  READINESS-phase approvals (the council readiness approval and the prepare lanes) lapse once;
  re-record them and the receipt settles, proven by a convergence test. Delivery-phase approvals,
  finding heads, and repair records are untouched, and CLOSED waves are untouched because
  receipt-chain validation re-derives ids from the fields stored on each record rather than from
  change-doc bytes, so every sealed archive keeps validating. On a wave already open for review, the
  stale receipt gates guided signoff recording until that one re-Prepare; recorded findings and
  delivery approvals are unaffected. The change is server-resident and is NOT immediate: it takes
  effect after either `wf_reload_mcp` or a full host restart (`gardener_metadata` is in the
  reload-purge set, so a reload genuinely suffices).

- **The review seeds now state when an editorial delivery-review finding stays inline, and that the
  Progress Log narrates rather than amends.** An editorial-only finding (imprecise but true wording,
  drifted citations, formatting) does not by itself open another repair cycle; every finding needing
  verification, a boundary repair, or escalation retains its existing action-matrix route. An
  editorial finding that makes a shipped claim false counts as a correctness defect. Paired with it:
  a scope, requirement, or AC change is recorded in the
  section that owns it, with the Progress Log row pointing at that edit, which is what keeps the new
  digest exclusion safe. The rule also states plainly that a re-Prepare depends on WHERE a repair
  lands: a repair confined to `## Progress Log` needs none, and a repair that edits any digested
  section still supersedes the receipt even when the finding was editorial.
  **Transition run (class (b) carrier).** The behavioral rule is live in the seeds as soon as the
  pack extracts, so fresh installs and every agent reading the seeds get it immediately. The
  project-local `docs/prompts/review-wave.prompt.md` copy is rewritten by the review-policy
  reconciler, whose replacement plan is built before extraction and deliberately frozen for the
  whole upgrade, so the upgrade that INSTALLS this release still runs the previous release's
  replacement set and leaves that file unchanged; the NEXT upgrade applies the sentence, and a third
  is a no-op. That one-run lag is the frozen-plan preflight working as designed, not the reconciler
  failing: do not report it as the rule not landing.

### Changed

- **Newly scaffolded change docs are told to fill the AC Priority table at plan time, not at
  Prepare.** The scaffold and `docs/plans/plan-template.md` previously carried
  `(Populated at Prepare wave.)`, which instructed an edit at exactly the moment it invalidated the
  readiness approval just collected: AC Priority is requirement-bearing and correctly stays in the
  digest, so the remedy is ordering rather than exclusion. `170-plan-feature.prompt.md` now states
  that AC Priority is populated and Tasks are fully enumerated before the prepare council runs, and
  the upgrade prompt migrates an existing repository's plan template. The `ac_priority_unpopulated`
  Prepare advisory is unchanged and remains the backstop. Existing change docs keep their text.

## [1.15.3] - 2026-08-04

### Fixed

- **Every upgrade summary the cleanup phase prints now carries the `summary_schema_version`
  freshness token, so a missing token means something specific.** The token used to be emitted only
  by the delegated primary-phase producer, which left the runs that deviated (a memory-checkpoint
  pause, `--resume-after-memory`, and every ordinary cleanup) indistinguishable from a run whose
  token had drifted or been dropped. The cleanup emit site now sets it on both the success and the
  failure branch, so a paused run reaches a token-bearing summary at its recovery `--cleanup`. The
  token is a claim about the code that rendered the summary, not about whether the upgrade
  succeeded; `failed_phase` remains the success discriminator and `summary_source_degraded` remains
  the sole degradation discriminator, which the in-process fallback still carries without a token.
  The seed-160 upgrade prompt and the session-handoff reporting hook now state the three causes of
  token absence so a report names the right one instead of a bare "absent". `summary_schema_version`
  is also registered as a terminal summary key so response bounding can never make a present token
  read as absent; that half is server-resident and takes effect after a full host restart, while
  emission takes effect on the upgrade that installs it.

- **Four documentation surfaces no longer promise a heavier review posture than the upgrade
  actually configures.** The upgrade prompt, the build-and-verification guide, and the project
  overview each claimed that enabled review maps to `delivery_mode=universal` (full Council on
  every wave) when it has mapped to `targeted` since delivery review became risk-tiered; the
  overview also named `universal` as the shipped fresh-install default. All three now state the
  delivered modes in the same wording the upgrade itself reports, and the review-policy decision
  record carries an inline amendment naming the wave that superseded its original default while
  preserving that original text as history. An executable census pins the corrected claim so the
  drift cannot silently return: it keys on the three claim-shaped phrasings rather than the word
  `universal`, which remains a legal delivery mode with legitimate uses everywhere, and it now
  reads `docs/references/` where one of the drifted surfaces had been sitting outside every
  automated check.

- **The secrets scan no longer walks native Windows virtual environments, and neither the scan nor
  the index walks Graphify's default output directory.** The shipped virtual-environment exclusion
  matched only `venv/lib/...` after path normalization, so a native Windows
  `.venv/Lib/site-packages` tree was selected and read: an entire dependency tree scanned, with the
  worker processes to match. The path pattern now accepts the dot-prefixed layout, in both the
  active Python allowlist and the Betterleaks prefilter, which are kept in step so they cannot
  drift apart. The same two rules now also exclude `graphify-out/`, the directory Graphify
  documents as its generated-artifact home, and the shared semantic-and-graph repository walker
  prunes that directory before descending into it. Existing indexes do not need a rebuild: one
  ordinary incremental update detects the former Graphify paths as removed and reaps them from both
  semantic and graph state. The exclusions stay narrow by design. Only virtual-environment library
  trees and the exact default `graphify-out` directory segment are skipped, so an ordinary source
  file such as `src/graphify-output.ts` remains scannable, and custom `GRAPHIFY_OUT` locations stay
  project-owned configuration.

## [1.15.2] - 2026-08-04

### Fixed

- **The five `integrity_checks` booleans now have defined phase-aware semantics.** Seed 209's
  Executable Evidence Record table gives each boolean a distinct plain-language definition, one
  readiness/delivery phase rule (a readiness approval attests to the review of the current tree,
  plan, census, or feasibility probe, not unimplemented product behavior; a non-executed finding
  may honestly carry `false`), and a readiness-safe known-bad control. Both validator messages
  now teach the attestation contract (affirm honestly, or do not record the claim as executed)
  instead of demanding `=true`; validator semantics are unchanged. The `wf_review_event`
  description and MCP tool spec carry the same phase-aware meaning. Wave 1uf65 / change 1uf64.

- **The docs-constants lint now states the exact one-line fix, unstranding docs gates after a
  `GRAPH_BUILDER_VERSION` bump.** When a documented fact does not match its code constant, the
  failure names the file, line, both values, and the instruction to change the current value to
  the expected value on that line; when the claim line is missing, the failure names the exact
  line to add (with the expected value) and where. Every conservative-advancer precondition miss
  now resolves through the gate message; the advancer itself is unchanged. Wave 1uf65 / change
  1uf66.

- **A routine memory-checkpoint pause no longer prints `Upgrade failed` prose or stamps a
  failure marker over its checkpoint state.** The upgrade runner's exit handling recognizes the
  typed action-required pause (action-required exit code plus a token/run-id-bearing
  `action_required` block in the lock), keeps `failed_phase`/`failed_at` untouched, and prints
  checkpoint wording naming the memory work and `wf_upgrade(phase='resume_after_memory')`.
  Genuine failures keep the existing retained-lock failure report. One transition-run residue:
  the upgrade that INSTALLS this fix still runs the pre-fix parent, so if that one run pauses at
  the memory checkpoint it may print the old failure prose a final time; the typed state and
  `resume_after_memory` are unaffected, so do not report that one run as this fix failing. Every
  later upgrade prints the corrected wording. Wave 1uf65 / change 1uf67.

- **A no-op review-policy migration no longer marks every readied wave for re-Prepare.** When the
  migrated `wave_review` config is byte-identical to the existing config and the carrier
  reconciliation plans zero edits, the upgrade's wave sweep skips the re-Prepare marker, the
  reprojection, and every wave write, and the structured result reports an empty
  `waves_marked_for_reprepare`. A genuine policy delta still marks and reprojects every
  non-closed declared wave; the plan-phase validation walk (unreadable waves and ledger errors
  failing preflight) is unchanged, so both resume paths keep their preflight. One transition-run
  residue: the wave sweep is planned and applied from the pre-extraction module, so the upgrade
  that INSTALLS this fix still marks each readied wave one final time. That same run re-renders
  the target's surfaces from the new code, so `docs/prompts/upgrade-wavefoundry.prompt.md` will
  already state that a no-op migration marks nothing while the marker that run just wrote is
  still on the wave; the new prose is correct from the next upgrade onward, not for the run that
  wrote it. Recovery is unchanged: `wf_prepare_wave(mode='ready')` re-readies the wave and the
  typed `wave-council-readiness` approval survives, so no re-review is needed. Do not report that
  one run as this fix failing; every later upgrade honors the guard. Wave 1uf65 / change 1uf69.

## [1.15.1] - 2026-08-03

### Added

- **Verified online model downloads now converge with the offline model-set identity.** Every
  feature package carries the release-pinned verification manifest (without model bytes). After a
  normal download, setup writes the same v1 identity marker as offline materialization only when
  every declared file hash and revision matches; incomplete, altered, mixed, or incompatible
  caches remain unmanaged. Wave 1uas8 / change 1uas7.

## [1.15.0] - 2026-08-03

### Fixed

- **Historical-memory publication checkpoints no longer report as `index_update` failures.** A
  ready-for-publication checkpoint retains action-required recovery state and exits 4 without an
  `ERROR`; this also works when the installing pghn/pgi7 runner is still the parent. Reload or
  reconnect before reading the distinct publication-ready MCP state, then use
  `wf_upgrade(phase='resume_after_memory')`.

### Upgrading to 1.15.0

**From 1.14.0 or earlier** (protocol change — treat it as a short maintenance window):

1. Stop the dashboard and disconnect every attached MCP/agent host for the repository, including
   the one you are working in.
2. Run the upgrade with `wavefoundry-1.15.0.<build>.zip` as usual. If `wf_upgrade` refuses, let
   the agent execute the exact argv the refusal returns; the single package handles verification,
   install, and rollback on its own.
3. When it finishes, **fully restart every attached host**, then follow the returned recovery
   action (complete any reported memory work via `wf_upgrade(phase='resume_after_memory')`, then
   `wf_upgrade(phase='cleanup')`).

**Already on a 1.15.0 prerelease:** run the ordinary upgrade. Fully restart hosts when the
response says a cutover-active run occurred.

**What changes for you after upgrading:**

- `wf_review_evidence` is renamed **`wf_review_event`** (no alias), and `wf_reopen_wave` now
  requires `purpose` (`"review"` or `"implement"`). Update host permission rules that pin old
  `wave_*`/`wf_review_evidence` names (notably `.claude/settings.local.json`); the upgrade's
  reconciliation output lists them. Renderer-managed rules in the committed `.claude/settings.json`
  self-heal from this release forward.
- The upgrade writes a read-only wavefoundry allowlist into your committed `.claude/settings.json`
  and names the delta. Review that diff deliberately — it changes agent permission posture. The
  mutating tool tier stays off unless you set `wavefoundryAllowWriteTools` yourself.
- After upgrading, check `wf_server_info`: `runner_stale: true` (or `null` right after an
  upgrade) means a full host restart is still owed.
- The transition run itself may show one benign, one-time summary quirk: an unmarked old-schema
  summary (coming from 1.14.0 or early prereleases), or a single
  `summary_source_degraded: unrecognized_schema_token_None` run (coming from the pg8h/pg9m
  prereleases, due to the pre-freeze rename of the summary envelope key to
  `summary_schema_version`). Neither is a failure; the next upgrade reports normally. If index
  publication is refused on a prerelease transition run, recover with `resume_after_memory`, then
  `cleanup`, then `index_build`.
- Offline model assets ship separately as `wavefoundry-models-<set>.zip` (attached to this
  release), downloaded once per model set; setup validates hashes and licenses before use.

### Added

- **Offline model assets are independently versioned.** The standard
  `wavefoundry-<version>.<build>.zip` remains the sole feature-upgrade input.
  When the pinned embedding/reranker set changes, `--with-models` additionally
  publishes `wavefoundry-models-<set>.zip`; framework-only releases do not
  duplicate model bytes. Upgrade and freshly extracted setup search the normal
  distribution locations for the exact set declared by the selected feature,
  validate its provenance, hashes, licenses, and compatibility fingerprint,
  then materialize it atomically. This also works on the first upgrade from a
  pre-model-bundle runner. Wave 1u95o / change 1uat8.

- **Model warm failures print the manual recovery path.** When setup cannot download a required
  model, the failure message now names the exact `wavefoundry-models-<set>.zip` asset and the
  standard placement locations, so an offline operator can recover without guessing; setup still
  validates hashes and licenses before replacing a verified cache. Wave 1ua8v / change 1ua8u.

- **Memory maintenance now has a deployable public shortcut.** **Review memories** (alias **Memory review**) runs the existing reviewed validation, bounded consolidation, history-worthy archive, and irreversible purge workflow with measurable before/after results; an explicit read-only branch performs no mutation. Consolidation preflights every source, caps each apply at five records with deterministic continuation metadata, creates the replacement through the normal forbidden-content checks, and restores its pre-apply snapshot after a caught multi-source failure. Purge is advertised as destructive and stores only SHA-256 source identities in the repo-visible, non-indexed `.wavefoundry/memory-purge-dispositions.json`, so deleted history cannot regenerate after an index reset or fresh clone. The compact archive register remains searchable while full archive bodies remain excluded. Setup and upgrade migrate the retired generated `memory/pointers/` directory into that register before indexing; index walks exclude any residue and lint rejects the old schema. Retired records have no bulk archival path—the archive-versus-purge judgment remains per record. Fresh setup and every upgrade backfill the missing prompt without replacing project-authored prompt prose, and upgrade may recommend the shortcut after a memory brief but never runs curation automatically. Wave 1u8r2 / changes 1u75c and 1u8r1.

- **The one Wavefoundry package is also the protocol-bridge executable.** The release builder emits only `wavefoundry-<version>.zip`; after explicit dashboard and host shutdown, that same package verifies its embedded bridge and exact feature payload, installs protocol 2 with rollback, and runs the feature hop in one invocation. Native Windows, WSL2, macOS, and Linux share the structured argv contract; no special upgrade package or bridge composition files are operator-facing release assets. Wave 1tz6l / change 1txh7.

- **Docs-lint detects orphaned review ledgers.** A non-empty `events.jsonl` in a wave-shaped directory whose sibling `wave.md` is missing, unreadable, or carries neither the events source declaration nor the legacy inline marker now fails lint with an actionable message. Enumeration is directory-driven, so deleting or renaming `wave.md` while its ledger survives is detected rather than walked around; empty ledgers (fresh scaffolds) and non-wave folders pass. The honest undetected boundary narrows to whole-ledger rollback, empty-ledger declaration removal, and co-deletion of ledger plus declaration.

- **Verification now matches the events-only claims.** The residue census covers the tests tree with per-file load-bearing allowances (a stale allowance fails the census), and the crash matrix gains true-termination cuts: a spawned child process is killed at each named boundary around the ledger's atomic replace, with the parent asserting the surviving on-disk state, canonical parseability, and exact-replay convergence. The existing exception-injection cuts remain as fast equivalents.

- **Memory-retrieval quality is measurable in any project.** The eval engine now ships with the framework instead of living in the test tree, and a new read-only `wf_memory_eval` tool runs the curated live-corpus pass over the repository's own memory records. It reports aggregate metrics, kind/status counts, a content fingerprint, and the fusion adoption verdict — never record bodies, summaries, or ids — and returns an explicit unavailable report rather than failing when the semantic backend or corpus is missing. The hermetic invariant pass remains a test, with its golden fixture as test-only scaffolding.

- **The wavefoundry MCP allowlist in `.claude/settings.json` is now rendered and self-healing.** Install and upgrade merge the read-only tier of the canonical tool roster into `permissions.allow` and record exactly the entries they emitted under a top-level `wavefoundryManagedAllow` provenance key, so a tool rename no longer leaves a stale rule that prompts on every call. Ownership is never inferred from the `mcp__wavefoundry__` name prefix: operator-authored rules, including ones that happen to name a wavefoundry tool, plus all deny and ask entries and unknown keys, survive every render. The mutating tier (lifecycle writes, both edit gates, memory, index, dashboard, sensors, upgrade) renders only when the operator sets `wavefoundryAllowWriteTools` in the same file, and it is all or nothing. Because this mutates a committed file, the upgrade names the rendered delta as an explicit consent line. A fresh install and a protocol-bridge upgrade render the block immediately, and an ordinary upgrade renders it during the upgrade that installs this release. Wavefoundry rules a repo already hand-maintained are left unclaimed and reported as such: they get rename self-heal only after the operator deletes them and lets the renderer re-emit them. Wave 1u2b0 / change 1u2az.

### Changed

- **Each wave's `events.jsonl` ledger is now the sole review-evidence authority.** The retired project-global review-evidence adoption and migration sidecars are removed one-way on upgrade, with no receipt, hash, or replacement authority written anywhere; historical `wave.md` and `events.jsonl` files stay byte-for-byte untouched. Upgrading across this boundary is a maintenance window: every attached MCP/agent host, including the invoking one, must fully restart before lifecycle mutation resumes, because an in-process reload alone leaves a pre-upgrade host writing state the new implementation no longer reads.

- **Gate derivation on declared waves is typed-exclusive.** On a wave declaring `review-evidence-source: events.jsonl`, every gate read of review-evidence content (operator signoff presence, per-lane and council signoff currency, max severity) derives solely from typed ledger records through a single authority facade; prose signoff lines and standalone severity words in `wave.md` are inert narrative in both directions, so a prose-only signoff satisfies nothing and a severity word in prose trips nothing. Legacy waves without the declaration keep the prose mechanism unchanged, and the required-lane roster parsing is untouched.

- **The cutover restart requirement is scoped to runs that actually crossed the boundary.** `restart_required` is true only when the run removed a sidecar or the stale root lock, or the installed version predates 1.15 (an unknown version fails safe to true); a rerun on an already-converged repository reports it false. On cutover-active runs the upgrade suppresses its automatic in-process reload at both automatic-reload phases, drops `wf_reload_mcp` from the suggested next tools, and instructs the full host restart instead; ordinary later upgrades keep the established reload flow.

- **Upgrade cleanup holds both publication locks through sidecar deletion.** The probe-then-release window is gone: the current lock and the v1.13 root lock stay held across the deletions so no concurrent acquirer can interleave, and the root-lock file is released and then unlinked last, with the residual platform slivers (Windows open-file deletion, POSIX split lock domain) stated plainly rather than claimed away. Refusal semantics for a held or unprovable lock are unchanged.

- **Retired inline-ledger compatibility machinery is deleted.** The unused inline parsing, rendering, and scaffolding paths are gone; fail-closed detection remains, so an inline-marker wave still fails validation with an actionable message naming the manual migration path instead of silently reclassifying as legacy prose.

- **`wf_review_evidence` is now `wf_review_event`.** The tool inspects and appends typed review events (`list`, `finding`, `run`, `approval`); an Evidence Record is only one of the record types it writes, so the old name mislabelled the abstraction. This is a clean rename with **no alias**: upgrades reconcile stale references in rendered surfaces automatically, but host permission allowlists that pin exact tool names need a one-time update, and the MCP host must be fully restarted after upgrading so the client picks up the renamed surface.
- **`wf_reopen_wave` now requires an explicit `purpose`.** Pass `"review"` or `"implement"` to select the context-efficiency stage the following work is attributed to. Omitting it previously defaulted to `implement`, which silently recorded pre-close reviews as implementation work; there is **no fallback and no alias**, so callers written against the 1.14.0 signature must pass the argument. An empty or unrecognized value returns a typed `invalid_purpose` error with recovery hints, and an omitted argument is rejected by the published schema before the tool body runs — both leave the wave status, the telemetry seal, and the focus stage untouched.

### Fixed

- **Graph-builder upgrades no longer fail their own docs gate on an exact reliability-version transition.** The incoming upgrade extension snapshots a unique `docs/RELIABILITY.md` claim only when it matches the pre-extract `GRAPH_BUILDER_VERSION`, retains that guarded observation in the existing upgrade lock across interruption/recovery, then advances the unchanged claim to the newly installed version before docs-lint. Missing, ambiguous, previously mismatched, or mid-upgrade customized claims remain untouched and continue to be reviewed normally. Wave 1u8r2 / change 1u8r1.

- **Gardener-only drift evaluation now handles Wavefoundry's space-containing document paths.** Git terminates an unquoted `+++` filename containing spaces with a tab before any timestamp metadata; the parser retained that tab in the blob path, so `git cat-file` failed and drift evaluation stayed stale on repositories following the framework's own `<id> <slug>` naming convention. The parser now strips the unquoted terminator, keeps C-quoted control-character paths fail-closed, and is pinned by a real-git space-named living-doc regression. Wave 1u8r2 / change 1u91n.

- **MCP reload reporting no longer equates queued notification work with client adoption.** Tool-list changes now report `tool_list_changed_notification_dispatch` as `not_needed`, `queued`, `completed`, or `failed`; the compatibility boolean remains additive, while diagnostics distinguish an active-loop queue from a completed server-side send. Successful automatic upgrade reloads preserve those diagnostics. Upgrade guidance checks a fresh model turn first, then reconnects MCP, then restarts the host, instead of diagnosing a host defect from a tool schema captured at the start of the invoking turn. Wave 1u8r2 / change 1u8r1.

- **Rendering `.aiignore` no longer grows two blank lines per render.** The renderer's meta-line filter recognized only the index block's non-blank members, so the block's interior blank and the appended separator survived into the project-owned region on every render, forever (one fielded repository accumulated 189 blank lines in four months). The leading blank run is now collapsed to the single canonical separator, already-accumulated debris self-heals in one render, and intentional blank lines inside project-owned content are preserved.

- **Orphaned graph and sidecar store rows now reconcile on incremental index builds.** Store rows whose registry entry was gone (out-of-band cleanup, older-pack residue) survived every zero-change build in the graph file table and the `file_freshness` / `secret_scan_cache` sidecars, and the secret-scan cache leaked on every build shape. Each incremental build now plans a read-only store-minus-authority reconciliation and executes it inside the build epoch at the existing reap seam: ENOENT removes, unreadable paths are preserved, a mass-removal circuit breaker defers wholesale retirements loudly, graph retirement routes through the normal merge so store, payload, and clusters stay consistent, and a removal-only pass opens and finalizes a build epoch.

- **A deleted living doc no longer freezes the doc-drift classifier, and a frozen evaluation can no longer read as clean.** A commit deleting (or, with rename detection pinned off, renaming) a living doc emitted a `+++ /dev/null` frame the patch parser rejected, failing the whole classification closed for the lifetime of the commit window while `wf_audit` kept reporting an evaluated-looking zero. Deletion frames are now parsed as the material changes they are; every fail-closed return site in the history walk and the gardener classifier carries a per-site reason threaded into the skip log (replacing the static three-way parenthetical); the store records consecutive failures, stage, reason, and last-success age from the first failure; and `wf_audit`'s `doc_drift` gains an additive `evaluation` object distinguishing evaluated-clean from stale from never-evaluated, with a `doc_drift_evaluation_stale` advisory. Drift still never blocks `ready`.

- **The coherence scan no longer flags pack-owned migration text as stale tool references.** The `wf_cli` module reference (already module-path form in every seed) joins the non-tool identifier allowlist, both retired gate names that upgrade migration instructions must keep citing (`wave_open_gate`, `wf_close_wave_gate`) are exempt symmetrically, and remaining `harness_coherence` findings carry a `classification` field (`pack_internal` for vendored-pack paths, non-blocking for target repositories; `project` otherwise) with additive per-class counts, so downstream audits lose the permanent unfixable noise while a genuinely stale tool name still flags on both sides. The upgrade seed's transition-debris guidance now also names the `payload/*.json` manifest criterion and states that removal is safe once every identification criterion holds.

- **The primary-phase upgrade summary is now produced by the freshly extracted code behind a pinned entry-point contract.** The pre-extraction parent spawns the extracted tree's `upgrade_wavefoundry.py --emit-summary` (pinned flag, argv, sentinel prefix, and `summary_schema_version` token; upgrade lock as the old-schema-tolerant state carrier; pinned timeout; the pins guard against silent drift while deliberate versioned evolution bumps the token), captures the child's sentinel, and re-emits the payload byte-verbatim through its own logger, so the reconciliation scan runs on the producer's own module version and the silent empty-channel skew (a `[]` reconciliation report from an old orchestrator unpacking a newer scan module) cannot recur. Any delegation failure (entry point absent, non-zero exit, malformed or absent sentinel, timeout, unrecognized token) degrades to the parent's own in-process summary carrying a `summary_source_degraded` marker that bounding never drops, with exactly one sentinel per run and the upgrade's exit status unchanged; a fallback summary is never presented as new-schema output. A permanent contract test guards the surface for every fielded runner. Wave 1u5vl / change 1u44o.

- **Phase 4 index publication is no longer refused by the upgrade's own checkpoint, and the summary no longer reports a failed publication as success.** The `setup_index.py` children spawned for the blocking docs and graph passes now hold value-bound authorized-publisher status (a `publisher_grant` token recorded in the upgrade checkpoint and matched against the child environment), on the primary phase and both standalone index phases; the detached background code child never carries a grant. The new pack's `pre_index_update` hook establishes the same grant when the upgrade is still driven by an old parent runner, so the fix takes effect on the upgrade that installs it. The summary's `index_update` field now derives from the observed publication outcome at every writer, a failed docs-layer child exit is reported instead of silently swallowed (the standalone index phases exit non-zero), the refusal message states the complete recovery branched on the actual pending count (`resume_after_memory`, then `cleanup`, then `index_build`, confirmed by `index_health`, at zero pending; backfill plus validation otherwise), and the MCP response carries an `index_publication_failed` diagnostic naming `index_health` whenever publication did not complete.

- **The upgrade no longer extracts the release zip's installer members into the project root.** Phase 0b extraction is allowlist-filtered to `.wavefoundry/**` plus the transient bootstrap file, so the combined package's zipapp runner members (`payload/*`, `__main__.py`, `upgrade_bridge_bootstrap.py`, `subprocess_util.py`) never land in a target repository and can never overwrite same-named project files; the upgrade log records the withheld-member count. Manual install and upgrade instructions now use scoped extraction (`unzip -o <zip> '.wavefoundry/*' -d .`); never delete those member names from a project root to compensate. Wave 1tz6l / change 1u0cc.
- **Gardener-only dates no longer stale review-policy receipts.** The admitted-change digest normalizes exactly one canonical top-level `Last verified` value while keeping every other byte significant. Evaluator version 2 gives non-closed waves one deterministic re-Prepare transition; closed Markdown and ledgers remain immutable. Wave 1tz6l / change 1tz6k.

- **`wf_reopen_wave` no longer reports a focus stage it did not apply.** A failed context-efficiency focus write was swallowed while the response still claimed the requested stage had been set. Reopening still succeeds, because telemetry is observational, but the response now returns `data.focus_stage: null` alongside `data.focus_error` and a `focus_stage_not_applied` diagnostic naming how to recover.

- **Repair-chain guidance leads to the right call.** The lane-clearing recipe — in both the agent-harness prompt and the tool's own description — now names the `repair_start` prerequisite, states that `repair_start` and `reverification` are finding events rather than run events, and distinguishes the implementer who records the repair from the blocking reviewer lane that independently reverifies it. The two sequence errors are self-correcting: submitting a repair run kind as a run event, or a reverification with no preceding repair start, now names the corrective call instead of only restating the constraint.

- **Memory candidates no longer target the test runner.** Decision-log drafting applied no verification-harness filter, so a decision whose rationale mentioned the test runner could be recorded against it instead of the module it governs. Runner entries are now excluded on both drafting paths, and illustrative placeholder tokens are rejected everywhere.

- **`wf_server_info` can tell a stale MCP runner from a current one.** `server_runner_version` was a constant that never changed, including across releases that replaced the runner file, so the one field whose job is to say "a full host restart is needed" could never say it. It is now a content hash captured at process launch over the un-reloadable runner set (`server.py` plus `venv_bootstrap.py`) and compared against the same hash recomputed from disk at query time. `runner_stale` is tri-state: true with a recovery diagnostic and detail, false when the process matches disk, and null when either side is genuinely unknown (no runner process, an unreadable or torn tree mid-upgrade, or a pre-hash runner), never a fabricated value. An in-process reload deliberately leaves the launch identity untouched, because the runner is exactly the part a reload does not replace. Wave 1u2b0 / change 1u2ay.

## [1.14.0] - 2026-07-21

### Added

- **The MCP tool surface uses subsystem-prefixed names.** Framework and wave-lifecycle tools are `wf_*` (verb-first: `wf_close_wave`, `wf_open_gate`, `wf_start_dashboard`), agent-memory tools are `memory_*`, and index tools are `index_*`; the old `wave_`-prefixed names are retired with no aliases. Upgrades reconcile stale tool references in rendered surfaces automatically via a complete rename map, but host permission allowlists that pin exact tool names may need a one-time update, and the MCP host must be fully restarted after upgrading so the client picks up the renamed surface.

- **`wf_audit` answers instantly with a bounded index-readiness snapshot.** The default first-call audit no longer cold-loads native vector storage or hashes the working tree — the two unbounded costs behind a field-reported native-Windows hang. The snapshot reads only the index control plane, honestly reports `freshness: "unknown"`, and defers full hash-walk verification to the explicit `index_health` tool; a diagnostic on every healthy audit makes the two-surface split explicit.

- **The review-evidence ledger has a standardized read surface.** `wf_review_evidence(event="list")` returns a compact per-record index, a per-finding chain summary composed from the close gate's own derivations (current head, repair state, unresolved required lanes, terminal flag), and per-signoff approval currency, with filters and bounded output. Chain-state-dependent write rejections now point at the list event, replacing hand-parsing of the ledger file. Accounting is honest by design: the first listing of a ledger version earns source credit; identical-content repeat listings are neutral (no credit, no debit).

- **Wave records render a current-state review projection.** `wave.md` carries a generated signoff table (one `Signoff | State | Why | Next action` row per required key) and a finding-synthesis summary derived from the canonical event ledger, so approval currency and open blocks are readable at a glance while `events.jsonl` remains the only authority.

- **Context-efficiency telemetry measures per-wave token savings end to end.** A three-stage model (plan/implement/review) records every first-party tool call durably per wave, publishes checkpoints into wave records at lifecycle boundaries, and seals/compacts at close. Credits cover derived artifacts (floored per artifact against the request), demonstrably-read state files, and digest tools under a bounded-enumeration rule — a response credits only what it conveys or enumerates as live, and listings never credit closed history. Pre-wave exploration is held in an explicit general bucket and folded into the next wave at creation or preparation. A separately labeled exploration-avoided estimate from memory advisories is reported but never summed into the measured total.

- **An in-band MCP-first retrieval directive with a measuring sensor.** Every wave activation and review response carries the retrieval-posture directive (rule, recorded escape hatch, and the advisory it clears), now covering implementation, review verification, repair work, and briefed subagents; a sensor flags near-zero code-retrieval telemetry against a non-trivial diff, cleared by a recorded rationale.

- **A paired-evaluation scaffold makes the counterfactual measurable.** Registered evaluation scopes accept quality-equivalent paired evidence (with-tooling vs without) through a typed attach/replace/revoke surface, so "what would the agent have spent" claims can graduate from estimates to measurements.

- **Commits trace back to their reasoning.** `code_commit_provenance` maps a commit SHA or a blamed line to the wave(s) that produced it and their recorded decision-log reasoning, honest about conflicts and absences.

- **The agent memory layer supplies, validates, and populates its own records.** Evidence-derived candidates draft conservatively from decision logs and repaired findings (`memory_propose`); duplicate detection is diagnostic, never destructive; wave close requires each candidate to be explicitly validated (promote/retain/reject/rewrite) against its evidence and current target; and deterministic structural criteria may auto-promote a candidate to active — auto-supersede, merge, and delete remain forbidden. A hermetic retrieval eval records the ranking-policy baseline.

- **Historical memory backfill at install and upgrade.** Existing wave history is mechanically drafted into memory candidates with resumable, transactionally unique runs; setup and upgrade refuse semantic-index publication while drafted candidates await validation, and publication is protected by a run-scoped receipt integrated with the index epoch, so it happens exactly once even across interrupted or version-mixed runs.

### Fixed

- **Lifecycle mutations are serialized and forward-recoverable.** An advisory per-repository lock covers the mutating lifecycle tools with a clear busy diagnostic; multi-file wave mutations write their referencing record last so an interruption converges on retry; prepare validates council seat alignment against the generated brief.

- **The test suite and background index builds no longer interfere.** Mutual exclusion with atomic post-acquire rechecks in both directions (suite defers to a running build, hook-spawned builds defer to a running suite) — holding nothing while waiting, so neither side can present as a phantom peer.

- **Public search vocabularies have one source of truth.** A canonical contract module now feeds both the serving handlers and a docs-vs-code constants lint, including the complete five-value fallback-reason set; documented model names, versions, and content values fail the docs gate when they drift from code.

- **Silent telemetry losses repaired.** Non-writing review-evidence responses (previews, errors, listings) record their costs instead of being dropped by a swallowed type error; lifecycle focus can no longer be set from an unresolvable wave argument; one unprojectable telemetry row can no longer block MCP reload or upgrade (unknown wave keys are skipped and surfaced explicitly); per-stage savings reconcile exactly with the displayed total (a net-negative stage floors at zero); and general-bucket savings survive process restarts instead of orphaning.

- **Memory retrieval ranking respects policy tiers.** Semantic similarity now tie-breaks within a confidence tier instead of overriding trust policy wholesale, so high-trust records are never demoted below fresher-but-less-trusted matches; the recorded eval baseline independently confirms the fix.

- **`memory_propose` extracts repair targets from the right fields.** Candidate targets now come from the public path and artifact identifiers, never from the verification command line — a finding repaired in one file no longer gets attributed to the test runner that verified it.

- **Dashboard rendering repairs.** Multi-line acceptance-criteria and task continuation lines render completely (backend list-item extraction, not a CSS patch), and wave-document rendering handles the current record format.

- **The `wf` CLI resolves its repository root independently of the working directory.** Dispatched subcommands work from any cwd inside the checkout.

- **Freshly scaffolded wave records pass docs-lint as generated** and survive their first lifecycle transition without manual repair.

- **Operational contracts rewritten from measured evidence.** RELIABILITY and the performance budget now cite recorded measurements with lint-bound claim lines, and performance-test budgets are contention-safe: a registered budget table, a slowdown guard that exercises the real thresholds, and a permissiveness invariant that fails on inflated budgets.

- **Upgrades crossing the tool rename no longer fail at the pre-extract dashboard stop.** The lock-cutover hook resolves the dashboard-stop entry point with a fallback to the retired pre-rename symbol and raises a legible error only when neither exists.

- **Post-extraction upgrade hooks run the newly extracted code, not a stale cache.** The docs-gate projection reloads a pre-extraction `review_evidence` module in place before running, and the memory-backfill loader applies the same in-place reload, so a pre-upgrade runner's cached modules can no longer shadow the just-installed implementation.

- **A recovered memory resume clears its own failure marker.** A successful `--resume-after-memory` removes the retained `failed_phase` marker when it names the phase the resume just recovered, so cleanup proceeds without a full re-run; markers naming other phases are never cleared by an unrelated success.

- **Memory-publication success survives trailing index passes.** Publication is recorded at the moment the authorized build epoch commits instead of being re-derived from the last-build row, and follow-on passes in the same publication scope (graph extraction, lexical derived rebuilds, optimization) finalize normally instead of being refused by the memory gate — previously a validated resume deterministically failed with the index left looking mid-build, forcing a manual workaround. The validation gate and every crash-recovery window are unchanged.

- **Opening a wave directly from prepare attributes work to the implement stage.** Context-efficiency focus advances on any activation path, so implementation retrieval no longer counts against planning and the retrieval-posture sensor no longer false-fires on prepare-activated waves.

### Changed

- **MCP-first retrieval guidance covers the full lifecycle.** The in-band directive, the canonical exploration-order seed, and the rendered implement/review/close prompts now name review verification, repair work, and briefed subagents explicitly — investigation at any stage routes through the retrieval tools first.

- **`wf_sync_surfaces` reports a structured changed-file manifest** (written/skipped, per file) instead of an opaque render log.

- **Dedicated lock files are consolidated under `.wavefoundry/locks/`** with a one-way migration; every lock creator owns its parent directory, and the dashboard launch mutex is preserved as a persistent file.

- **Short operational subprocesses are time-bounded.** Gardener and surface-render spawns carry configurable timeouts with truncation-flagged captured output; upgrade, setup, and index builds remain intentionally unbounded.

## [1.13.0] - 2026-07-16

### Added

- **Java static and instance initializer blocks are now indexed as their own code chunks.** Literal-rich `static { … }` / `{ … }` bodies — message and error tables, lookup-map registration, enum bootstrap — were previously in no chunk at all and invisible to search; they are now emitted as stable, size-bounded chunks in both the tree-sitter and regex-fallback Java paths, across class/enum/record containers. Java records also become first-class in the tree-sitter path. An upgrade re-chunks the code index, reusing embeddings for unchanged chunks.

- **A prior-learning memory layer surfaces relevant lessons before risky actions.** Typed, evidence-backed memory records attached to the code graph are surfaced at action time, and retrieval is now churn-aware: index-time freshness/churn metadata and doc↔code drift detection let every retrieval response distinguish current documentation from documentation that has drifted from the code it describes.

- **Ranked search reports index freshness and degrades gracefully when the embedding model is unavailable.** `code_ask` carries an honest three-state freshness verdict computed from a cheap per-layer signal (replacing an expensive, incorrect per-question corpus walk), and semantic-path failure now degrades to full-text search with preserved filters and a uniform, typed `search_mode` / `fallback_reason` contract instead of disabling search or silently dropping filters.

- **Reviewers now verify changed work against an independent reference.** A framework-owned review protocol asks reviewers to test material claims through public paths, state transitions, and exact repair replays, and — for any changed implementation — to verify behavior against a reference that does not share the implementation's assumptions (a specification, the independently-read acceptance criteria, a materially independent implementation, or a metamorphic invariant), never relabeling implementer-authored evidence as independent approval. Executable review evidence is recorded in a typed, machine-readable event ledger.

- **Security severity now requires a grounded, attacker-reachable threat.** A conjunctive credible-threat gate drives security severity, blocking, and approval-freshness only from findings reachable under the documented threat model — cutting false-positive security escalation without weakening discovery.

### Changed

- **A single SQLite store is now the authority for semantic-index state.** `meta.json` is retired; index state lives in `index-state.sqlite` with a durable build-generation contract and reset/rebuild-or-fail semantics, while Lance remains the chunk/vector authority. Every MCP, dashboard, health, upgrade, and setup consumer reads the one authority — no dual-format fallback.

### Fixed

- **Incremental code indexing no longer freezes on hook-enabled repositories.** A content-scoped build stamped broad file hashes while embedding only its own content type, freezing the other type's index — so automatic post-edit indexing had effectively never kept the code index current, and the documented `content=code` recovery was a no-op. Change detection is now coherent under any build scope, and the automatic hook path keeps both semantic layers fresh.

- **`code_ask` no longer reports a permanent false "stale" index on repositories with a generated codebase map.** The freshness check compared recorded index state against ignore-filtered inputs, so the always-regenerated codebase map read as "gone" forever — every query reported stale and the prescribed rebuild was a no-op. The ignore filter is now applied uniformly; the fix heals an already-built index in place, no rebuild required.

- **Upgrading no longer halts at the documentation gate on freshly rendered specialist agent files.** Newly rendered specialist reviewer carriers lacked the role/category frontmatter that the same release's docs-lint enforces; the seeds now carry it and the render path injects it as a destination-aware fallback.

## [1.12.0] - 2026-07-11

### Added

- **Ranked code search gains a real lexical signal, fused with semantic retrieval.** A new SQLite FTS5 full-text layer indexes every docs and code chunk and feeds BM25 candidates into ranked retrieval before the cross-encoder rerank, closing the documented weak spots of dense-only search — exact identifiers, rare tokens, and error strings. Compound identifiers stay whole search tokens, results found by both passes carry a multi-source agreement marker, hostile query syntax degrades safely to semantic-only, and interpreters whose SQLite lacks FTS5 keep working unchanged. Codebase Q&A (`code_ask`) and code search both use it; exact keyword search is untouched.
- **A transactional state store now backs the semantic index.** One derived-only SQLite sidecar carries per-file freshness/churn data (extracted from local git history in one batched pass per build), per-path build bookkeeping with the index metadata file preserved as an exported snapshot for existing readers, a chunk registry that lets incremental builds skip reading unchanged rows entirely, and the new full-text tables. Everything in it rebuilds from the repository, git, or the vector store — a missing, corrupt, or out-of-date store is repaired automatically with no data loss, and schema upgrades never require migration steps.
- **Secret scanning remembers what it already scanned.** A per-file cache keyed on content and ruleset fingerprints skips files whose exact bytes were already scanned clean under the exact same rules — precise across branch switches, whitespace-only touches, and touch-and-revert — while a differential harness proves the cached path reports findings identical to a full scan, and any cache problem falls back to scanning everything. A repo-wide re-check that took seconds now completes in well under a tenth of one.
- **The graph tools now see classes that implement or extend third-party types.** A class whose only supertypes are external (for example an SDK interface) previously showed no inheritance relationships at all, with no signal that any existed. Impact analysis can now resolve an external interface by name and return every project class that implements or extends it as the blast radius; the implementor side reports its declared supertypes with always-on external counts; and a name shared by several distinct external types returns a grouped breakdown instead of a merged guess. Works against existing graphs immediately — no re-extraction needed.
- **One command now maintains every index.** The index-optimize tool covers the vector tables and both SQLite stores in a single pass — compaction, space reclamation, planner statistics, full-text segment merging, and a two-layer integrity check (structural soundness plus staleness against each store's source of truth) — and still runs automatically at install and upgrade. Index health reporting shows the state store's presence, schema version, and integrity verdict.
- **A new `code_lexical` tool searches the lexical layer directly.** BM25-ranked exact-token search over the same indexed full-text corpus that ranked retrieval fuses — built for exact-identifier lookups (compound identifiers, error strings, rare tokens) and for verifying what the lexical layer actually holds, with per-table coverage reporting so empty results on an unhealed store are never mistaken for absence from the corpus. Regex stays with pattern search; live-file substring match stays with keyword search. Agent guidance now also documents how to read the multi-source citation markers and why compound identifiers must be queried whole.

### Fixed

- **Ruleset changes now actually trigger the promised full secret re-scan.** The scanner's change detector hashed a rules path that never exists, leaving the primary framework ruleset outside the fingerprint entirely — so a rules update (including one delivered by upgrade) silently kept stale per-file scan decisions. The fingerprint now covers the real ruleset locations; the first scan after upgrading performs one full pass, then returns to incremental.
- **The full-text backfill now works against real vector tables (it never had).** The end-of-build reconcile that populates the lexical layer from the vector store projected a column no production table has ever carried, failed on every repository, and was silently swallowed — leaving exact-token search running on a near-empty index while health reported everything fine. The read is now schema-tolerant (absent optional columns default empty; genuinely unreadable tables still take the safe skip path), the store heals in place on the next build with no forced rebuild — including builds where no files changed, so an upgraded-but-idle repository heals too — and the one-time provisioning, repair, and skip diagnostics persist to a bounded log under the local logs directory instead of vanishing with the build process. Index health now reports per-table lexical coverage against the vector store and flags a materially under-covered index instead of reading healthy.
- **A large on-disk search-index leak is closed at its source.** The previous full-text index rebuilt itself wholesale on every build that changed a table and accumulated superseded copies that ordinary compaction could never reclaim — over a hundred megabytes of dead index data on an active repository. That engine is retired: the new lexical layer maintains itself incrementally with no version accumulation, code search's lexical half reads it directly with identical result quality on the recorded evaluation set, and upgrade automatically drops the legacy indexes and reclaims their space.

### Changed

- **Incremental index builds got faster and more crash-consistent.** Provably-unchanged files skip their vector-store reads entirely during re-chunking passes (with drift-repair paths explicitly exempted so out-of-band data loss is still healed), all derived index state commits transactionally ordered after the vector-store writes with an end-of-build reconciliation that repairs any crash window, and first builds after install or upgrade log a calm provisioning note instead of a repair warning.

## [1.11.2] - 2026-07-06

### Fixed

- **Upgrading from an older version now removes the one-time `install-wavefoundry.md` bootstrap file from the project root.** The cleanup added in 1.11.1 only ran during the extract step, which executes the previously-installed code when upgrading through the MCP server — so an upgrade from a version that predated the cleanup left the file behind, and it was cleared only on the following upgrade. The cleanup now also runs during the index-update step, which always executes the freshly installed code, so an upgrade from any prior version removes the file in the same run. The archive still ships the file at its root by design; only the extracted copy is removed.

## [1.11.1] - 2026-07-06

### Fixed

- **Upgrading from a version before 1.10.1 now provisions the collision-resistant lifecycle-ID scheme automatically.** A repository upgraded from an older version through the MCP server could silently keep minting the previous, collision-prone ID scheme, because the code that installs the new scheme was not yet running when the upgrade was orchestrated — so a manual provisioning step was required. The upgrade's index phase, which always runs the freshly installed code, now provisions the new scheme idempotently and fail-safe, so a from-old-version upgrade self-heals without any manual step.
- **Install and upgrade no longer leave the one-time `install-wavefoundry.md` bootstrap file in the project root.** The distribution ships that single-use file at the archive root so the install agent can find it before the framework is unpacked, but nothing removed the extracted copy afterward, and every upgrade re-dropped it. Install and upgrade now delete it once it has been consumed; the archive-root packaging contract is unchanged.

### Changed

- **Closing a wave now reclaims search-index storage that has grown large.** A heavy documentation session could balloon the on-disk docs index, because its full-text index accumulates stale versions that only a deep optimization reclaims — and that optimization previously ran only at install and upgrade. Wave close now runs a bloat-gated, lock-aware optimization that reclaims the leaked storage when the index has grown well beyond its expected size, and does nothing when the index is already compact. It never delays or blocks the close, and never triggers a heavy rebuild.

## [1.11.0] - 2026-07-06

### Added

- **The code graph extracts SQL far more accurately, including Oracle and T-SQL dialects.** SQL graph extraction now recovers data-manipulation edges inside procedural loop bodies (so a routine's writes are no longer lost when they sit inside a `WHILE`/`LOOP`), distinguishes foreign-key / `LIKE` / `CREATE TABLE AS` references from ordinary column-type mentions in `CREATE TABLE`, handles `CREATE TYPE`, `MERGE`, and `SELECT … INTO` (including temp-table sigils so a `#tmp`/`SELECT INTO #x` target is not minted as a permanent table), and recognizes Oracle/T-SQL forms — pseudo-types, built-in scalar types, `DUAL`, `FOR UPDATE SKIP LOCKED`/`NOWAIT`, and bracket-qualified names. Schema DDL and stored-routine bodies now produce correct nodes and edges instead of phantom or missing relations. An upgrade materializes the new extraction automatically.

### Fixed

- **The local dashboard's stop and restart work on a dead instance.** When a dashboard process exited without being reaped it lingered as a zombie that the stop/restart tools mistook for a live process and failed to clear, returning a stop failure with nothing actually stopped. The server now reaps the dashboard children it spawns — including opportunistically during ordinary editing — and classifies a recorded process with a zombie-safe check, so stop and restart reliably clear a dead dashboard and start fresh. Windows process handling is unchanged.
- **The running dashboard no longer silently stops reflecting repository changes.** Three compounding gaps could leave the page stale while the server kept serving: the single watcher thread could wedge on a slow filesystem call with no timeout, its directory-level watch missed edits to files nested inside a watched folder (the common wave-document editing pattern), and the browser had no recovery when the event stream was "connected" but no longer delivering updates. The watcher's snapshot collection is now bounded per cycle and surfaces a staleness signal on the dashboard API and event stream, change detection catches nested-file edits promptly, the client falls back to an active poll when updates stop arriving, and watcher activity is always written to `dashboard.log` so a future stall is diagnosable even under the MCP launch path.

### Changed

- **Reload the MCP server after an upgrade that changes the graph builder, or the graph is silently downgraded.** An already-running MCP server keeps the previous graph extractor in memory for its whole lifetime. An upgrade re-extracts the graph at the new version, but the first graph query on a server that was not reloaded re-extracts the graph back down to the old version using its stale in-memory extractor — reverting the upgrade's graph work. The upgrade instructions now state plainly that reloading the server (`wave_mcp_reload`) or restarting the host after a graph-builder change is mandatory before issuing graph queries, and the upgrade's own code comments were corrected to describe how the graph phase actually works (it re-extracts during the upgrade; the first-query rebuild is only a safety net).

## [1.10.1] - 2026-07-03

### Changed

- **First setup now builds the code index by default and verifies SOCKS proxy support.** `wf setup` validates the `httpx[socks]` dependency through `socksio`, builds docs and code indexes synchronously unless an explicit background-layer flag is used, and preserves the setup-selected CPU provider for accelerator prewarm/index subprocesses. Wave 1p9gr / 1p9gq.
- **FTS indexes use no-position storage with compatible query shaping.** Index rebuild and rewrite paths create FTS indexes without positional data, while docs/code query construction avoids phrase-shaped identifier searches that no-position FTS cannot satisfy. Wave 1p9jn / 1p9j1.
- **Server-side full docs-lint scans have a configurable timeout.** Lifecycle tools now use the full-scan timeout setting and return a clear validation failure on timeout instead of surfacing a raw subprocess timeout. Wave 1p9j0 / 1p9iu.

### Fixed

- **Setup fails closed when `python3` is missing or too old.** Setup now requires `python3 --version` to resolve to Python 3.11 or newer and gives repair guidance instead of implying a tool-venv MCP fallback can bypass the committed launch contract. Wave 1p9hi / 1p9hh.
- **Native Windows lifecycle paths no longer corrupt stdout or fail common process checks.** In-process server helpers keep diagnostics off the MCP JSON-RPC stdout channel, dashboard/process liveness uses Windows-safe checks, install-log reads tolerate non-UTF-8 logs, venv recreation detects failed removal, spaced dashboard roots parse correctly, line endings and cosmetic paths normalize, and server startup detects a missing venv before handshake. Wave 1p9hn / 1p9io, 1p9hi, 1p9hj, 1p9hk, 1p9hl, 1p9hm, 1p9i7.
- **Setup/index child processes are bounded and keep the operator informed.** Phase-1 setup children and model warmup paths now have per-step deadlines, no-progress watchdogs, clean timeout exits, corruption-quarantine bypass for model-warm timeouts, bounded post-EOF indexer waits, and unconditional indexer heartbeat prints during long embed/finalize phases. Wave 1p9j0 / 1p9it.
- **Rendered hooks decode host stdin as UTF-8 across host surfaces.** Generated Claude, Cursor, Windsurf, and GitHub/Copilot hooks reconfigure stdin consistently so non-ASCII file paths no longer mis-decode under cp1252-style host encodings. Wave 1p9j0 / 1p9iv.
- **Windows metadata writes and development test paths are more robust.** Atomic metadata replacement retries Windows sharing violations, rendered surfaces and secret-scan path filters keep forward-slash/line-ending behavior consistent, and the framework test runner uses a cross-platform run lock plus UTF-8 subprocess capture. Wave 1p9j0 / 1p9iw, 1p9ix, 1p9iy.
- **Change and wave lookups report ambiguous lifecycle IDs instead of silently choosing one match.** Lookup tools/resources now return candidate lists for ambiguous change or wave prefixes, keep change and wave namespaces separate, exclude `wave.md` from change lookup, and preserve token-anchored matching. Wave 1p9jn / 1p9ip.
- **Apple Silicon CoreML provider-probe temp-dir failures fall back safely to CPU.** Provider selection retries a bounded private temp-dir repair inside the probe window, records setup-cache/fresh-probe/operator-request provenance consistently, and reports recovery guidance without masking persistent CoreML failure. Wave 1p9j0 / 1p9lj.

## [1.10.0] - 2026-07-01

### Added

- **`wave_index_optimize` — reclaim on-disk index bloat without re-embedding.** The semantic index tables accumulate on-disk bloat from incremental, edit-driven refreshes (superseded data fragments, stale full-text-search artifacts, old index versions). This new tool runs a tiered ladder — compact in place; if in-place compaction fails because of a LanceDB list-column corruption, rewrite the table fresh (which recomputes offsets and sidesteps the bug) and rebuild its vector and full-text indexes; fall back to a full rebuild only if a table is entirely unreadable — reclaiming the space with no embedding cost in the common case. It also runs automatically at the end of install and upgrade. A new MCP tool requires a one-time reconnect after upgrade to appear.
- **Index size is visible in `wave_index_health`.** The health response now includes a `size` object — the total on-disk index size plus a per-component breakdown (the docs and code tables and the graph) — so index growth and bloat are diagnosable without shelling out to `du`.
- **`wave_index_build_status` reports an authoritative build-lock state.** The response now carries a `lock` object whose `held` is determined by testing the real operating-system lock (not the presence of the lock file, which persists by design as a last-owner record), plus the last build's owner and whether it finished cleanly or was interrupted. Read `lock.held` to tell whether a build is actually running — do not read the lock file.

### Changed

- **Index refreshes are coalesced to the end of a turn instead of firing on every edit.** Previously each file edit spawned a background reindex; a session of many edits churned the index — and re-grew its on-disk size — continuously. The post-edit hook now marks the index dirty and a single coalesced refresh runs when the turn ends (on hosts with a turn-end hook; other hosts use a longer debounce). The in-session staleness monitor is now a quiet-period safety net — it refreshes only once editing has settled and a recent build has not just run — so the two triggers no longer compete. A new `indexing.monitor.quiet_period_seconds` setting (default 5 minutes) tunes the safety net. Trade-off: semantic search reflects edits made earlier in the same turn only after the turn ends.
- **Embedding precision is provider-aware: half-precision on a GPU, 8-bit on CPU.** The indexer selects embedding precision from the active hardware — FP16 on a GPU/accelerator, INT8 on CPU — for faster indexing with no quality regression, and the reranker follows the same single machine classification so the two never disagree. Small incremental edit batches are routed to the CPU path to skip GPU padding waste, while full rebuilds always use the accelerator.
- **Switching machines no longer forces a needless full re-embed.** The index records the embedding precision *class* (full-precision vs. quantized), so moving a repository between a GPU and a CPU machine re-embeds only when the class actually changes, not on every provider switch.
- **Dependency sync installs pinned version bumps, not just missing packages.** Setup and upgrade now compare installed versions against the pinned specifications and install a newer pin even when the package is already present — so a bumped dependency (such as the LanceDB upgrade in this release) actually lands on upgrade instead of being skipped as "already installed."
- **Index builds self-heal corruption-driven bloat.** When in-place compaction fails because of the LanceDB list-column corruption, the build and the incremental refresh now automatically reclaim the table by rewriting it fresh — so a corrupted table recovers on the next build instead of growing unbounded.
- **Shipped agent guidance no longer references the removed framework index.** Seed prompts and rendered command docs that still described the retired separate "framework" index layer (removed when the framework's own seeds and docs were folded into each project's single index) now state the current single-index reality, so an upgrading repository's agent no longer follows stale guidance.
- **Seed prompts state the journal/persona/manifest structure contracts verbatim.** The seeds that guide an install agent to author agent journals, personas, and the prompt-surface manifest now list the exact required section headings (with case), the per-section bullet rule, the accepted salience markers, the persona `Role:`/`Category:` frontmatter, and the required manifest keys — so an agent produces a compliant artifact on the first pass instead of discovering the structure through repeated validation failures.
- **Factor-review reconciliation is self-seeding and no longer noisy on a fresh install.** A fresh install now seeds the factor-review lane set from the repository profile's applicable factors as a prunable default; and when the lane set is left empty while the profile still marks several factors applicable, the audit emits one consolidated, actionable advisory (naming the factors and the remediation) instead of a separate warning per factor on every audit. The review gate still keys off the configured lane set, not the profile.
- **The post-edit docs-lint is incremental.** Docs-lint was the last post-edit reaction that still scanned the whole `docs/` tree on every edit (the index refresh and secret scan were already incremental). The post-edit hook now self-detects the git working-tree changed set and runs only the per-file checks on changed docs; a changed config file falls back to the full lint. The authoritative full corpus lint is unchanged and still runs at prepare, close, install, and upgrade — so a large repo gets fast per-edit feedback without weakening the gate.
- **docs-lint has a configurable file-size guard.** A markdown document larger than `docs_lint.max_file_bytes` (default 5 MB, matching the secret-scan and index file caps) now has its content validators skipped with a single loud, non-blocking warning naming the file, its size, and the remedy — so a pathological multi-megabyte generated document can't stall the regex passes or balloon lint memory, while a legitimately large document never fails the gate.
- **docs-lint reads each file once per run and can report per-phase timings.** The full lint previously re-read the same doc several times (once per validator that touches it); a transparent content cache keyed on file identity removes the redundant reads. A new `--timings` flag reports per-phase wall-clock (secrets/corpus/metadata/links) to help diagnose full-scan cost on large repositories.

### Fixed

- **Index tables no longer accumulate unbounded on-disk bloat.** A full rebuild's finalize now compacts and reclaims the stale index artifacts a rebuild leaves behind (old vector/full-text index versions and data fragments), and incremental refreshes clean reliably — so the on-disk index no longer grows far past its working set over repeated builds.
- **The index-build lock correctly detects a crashed or recycled owner.** The lock's liveness check no longer trusts a bare process-exists signal (which a zombie or a recycled PID could pass), and background index builds launched by the long-running MCP server are now reaped instead of lingering as zombies — so a stale lock is reliably reclaimed on the next build and status surfaces stop reporting a dead build as running.
- **The index-build lock recovery guidance no longer tells you to delete the lock file.** The lock file persists by design as a last-owner record; the early-exit message now points at `wave_index_build_status` to check whether a build is actually running, and the "wait for the running build" case stays actionable.
- **Embedding-model downloads succeed behind a corporate TLS proxy outside of `wf setup`.** The corporate-CA trust bundle was previously applied only during setup's model prewarm; a model download triggered later — by `wave_index_build`, a background index refresh, or the first `code_search` / `code_ask` — ran without it and failed certificate verification behind a proxy. The trust bundle (with a reactive fallback ladder) is now applied at every model-download entry point, so first-use downloads succeed behind a proxy too.
- **LanceDB auto-install no longer fails behind a corporate TLS proxy.** When the indexer auto-installs LanceDB via pip on first use, it now applies the same TLS-conflict mitigation setup already used (removing the exclusive certificate-file variable and enabling native trust), so the auto-install succeeds behind a proxy instead of failing certificate verification.
- **The post-edit docs-lint gate no longer hangs or fails early on a large repository.** The docs-lint hook ran the linter unbounded (and was capped too low in an earlier build), so on a large docs tree it could stall the editing agent or reject an edit. It now runs under a generous, configurable timeout (`docs_lint.hook_timeout_seconds` in `docs/workflow-config.json`, default 120 s) and treats a timeout as advisory — the edit proceeds and `wave_validate` / wave-close remain the authoritative docs gate — so a slow lint never blocks or hangs the session.
- **The install audit no longer reports a mis-encoded install log as "complete."** When the install log was written by a non-UTF-8 tool (for example Windows PowerShell without `-Encoding utf8`), its em-dash row separators became mojibake and the parser matched zero rows — which then read as vacuously complete. The row parser now tolerates any separator encoding, the completeness check treats an empty parse as not-complete, and the audit reports a distinct "install log unparseable" error instead of silent success; new logs are written UTF-8.
- **docs-lint no longer stalls on large or link-dense documents (and behaves correctly on Windows).** The link checker called a full path-resolution (realpath) for every link in a document — O(links) filesystem syscalls — which on a link-heavy document (a generated reference, a long changelog) on a slower filesystem (Windows/WSL2/network) could take tens of seconds and trip the post-edit hook timeout. It now uses a single lightweight existence check per link (measured ~67× faster on a large synthetic document) with identical results. Separately, relative paths in lint comparisons and messages are now normalized to forward slashes on all platforms, so the historical-doc link-check skips (which used forward-slash prefixes) actually take effect on Windows and lint messages no longer show backslash paths.
- **A journal can document its own content rules without failing docs-lint.** The check that rejects pasted raw transcripts and secrets no longer fires on a line that is *forbidding* such content — a journal's Governance section naming what it disallows ("Do not include raw transcript content") now passes, while an actual pasted transcript or secret value is still caught. The validator's missing-salience-marker message also now lists the accepted marker vocabulary so the fix is obvious from the error.

## [1.9.8] - 2026-06-29

### Fixed

- **Upgrades no longer abort when a pack-search location is sandboxed.** The upgrade scans common pack-drop folders (including `~/Downloads`) for a newer release zip; on macOS a privacy-sandboxed folder made that scan raise a permission error and stop the whole upgrade. A location it can't read is now logged, skipped, and listed under `skipped_scan_locations` in the upgrade summary — so you can grant access and re-run if a newer pack lives there, while the upgrade proceeds with the best pack it could reach.
- **Shipped seeds no longer point at a wavefoundry-internal decision record.** The stage-gate guidance added in 1.9.7 referenced an internal architecture-decision file that target repositories don't have, so an upgrading project's agent could cite a missing document. The references are removed (the rationale stays inline); the stage-gate reconciliation behavior is unchanged.

## [1.9.7] - 2026-06-29

### Fixed

- **The MCP server no longer hangs on the first model-loading call.** Loading onnxruntime (for the GPU/provider probe behind `wave_gpu_doctor`, and for embedding/reranking on the first `code_search` / `code_ask` / `docs_search`) can make its native execution provider write diagnostics directly to the process's stdout file descriptor — which is the MCP JSON-RPC channel — corrupting the protocol on the first cold call after a host restart. The server now hands the protocol a private copy of stdout and points the real stdout file descriptor at the null device at startup, so no native library write can corrupt the channel; the GPU probe keeps an additional fd-level guard.
- **`uv` dependency install no longer fails behind a corporate TLS proxy.** When `SSL_CERT_FILE` pointed at a single corporate-root certificate (set so the embedding-model download trusts the proxy), `uv` treated that file as its exclusive trust anchor and rejected PyPI. Setup now runs `uv` with the certificate-file variables removed from its environment and native TLS enabled (OS trust store), and assembles a merged superset trust bundle for the certifi/requests consumers — so both dependency install and the model download succeed. The previous per-store model-download trust ladder is unchanged.
- **The runtime `.gitignore` block is written programmatically and self-heals.** The Wavefoundry runtime ignore entries (semantic index, logs, lock/state files, pack-drop archives) are now written by the surface renderer on every install / `wf render-surfaces` / upgrade, instead of relying on an agent following prose. A repository that wasn't a git repo at install time — or whose ignore step was skipped — now gets the block automatically on its next upgrade, with operator-authored entries preserved.
- **Wave-close summaries no longer show stray dashes.** A Markdown table separator row in a change doc's Decision Log no longer leaks a `--------` entry into the generated close summary's key-decisions list.

### Changed

- **Secret-scan finding IDs: the legacy `exc-###` migration was removed.** The one-release shim that auto-converted legacy `exc-###` finding IDs to the lifecycle `<prefix>-sec` form has been removed. The secrets gate keys on a finding's status, not its ID shape, so an existing ledger with old IDs still reads and gates correctly; new findings continue to mint `<prefix>-sec` IDs.
- **The stage-gate sections stay a fixed contract on upgrade.** Upgrade reconciliation now keeps the two named stage-gate sections in `AGENTS.md` (repository-code gate and product-code guard) as separate named sections rather than letting them be consolidated, because they're referenced by name across host entry docs and lifecycle prompts.

## [1.9.6] - 2026-06-29

### Fixed

- **No console windows flash on Windows.** Framework subprocesses that don't need a console — the upgrade/index/graph pipeline spawns, the dashboard server, and the rendered hook bodies — now launch via `pythonw.exe` on Windows when their output is redirected. A console-subsystem `python.exe` could still flash a window despite `CREATE_NO_WINDOW`, especially for long-running detached or rapidly-spawned processes. POSIX and the MCP server launch are unchanged.
- **The dashboard starts cleanly on Windows.** The dashboard server now launches windowless, and the start path no longer false-reports `url_not_ready` or spawns duplicates that climb ports: it reconciles an already-serving dashboard before spawning and accepts a serving dashboard by URL reachability instead of requiring an exact recorded-PID match. The Windows lifetime lock was also moved off the byte the metadata occupies, so the dashboard can publish its URL while holding the lock (Windows mandatory byte-range locking had blocked that write).
- **The dashboard renders horizontal rules.** A `---` (or `***`/`___`) separator line now renders as a horizontal rule in the dashboard's document view instead of as literal dashes.

## [1.9.5] - 2026-06-28

### Added

- **`wf gpu-doctor`.** The GPU/provider diagnostics previously reachable only through the `wave_gpu_doctor` MCP tool now have a `wf gpu-doctor` CLI subcommand, for CLI or no-MCP use. It reuses the same provider detection (no duplicated logic).

### Changed

- **`wave_upgrade` returns its structured `summary` on the primary call.** The `summary` block (versions, files pruned, docs-gate result, index state, and the retired-surface reconciliation findings) is now emitted on the primary `wave_upgrade()` response, not only on the later cleanup phase — so agents read the computed fields, including the reconciliation list, directly from the main upgrade call.
- **Retired-surface reconciliation runs on every upgrade.** The reconciliation scan (stale `.wavefoundry/bin/*` references that should now be `wf` forms) now runs on any upgrade — including patch bumps and same-version build-successors — rather than only on major/minor bumps, since a patch can change or retire a surface during testing. The scan stays report-only and exclusion-aware.
- **Secret-scan finding IDs now use the lifecycle format.** `docs/scan-findings.json` findings use lifecycle-backed `<prefix>-sec` IDs (for example `1p8l0-sec`) instead of the legacy `exc-###` sequence — new findings immediately, and existing findings are migrated once (idempotent and lossless) with a `legacy_id` recorded for traceability. New and migrated IDs are collision-safe against other lifecycle IDs and findings; the secrets-gate behavior and the file/rule/hash finding re-binding are unchanged, and legacy `exc-###` IDs are still tolerated.
- **Reconciliation scan output is cleaner.** Host permission/allow-rule files (e.g. `.claude/settings.local.json`) are now reported in a separate `host_permission_flags` channel in the `wave_upgrade` summary — operator-flagged, kept out of the auto-editable `reconciliation` list — and the scan no longer false-flags `CHANGELOG.md` (at any path) or the generated prompt-surface manifest.
- **The secret scan always writes its ledger.** A clean scan now writes `docs/scan-findings.json` as an empty `[]`, so the file's presence confirms the scan ran; it changes only when findings change (no repeat-scan churn).

### Fixed

- **No more flashing console windows on native Windows.** Every framework-spawned subprocess — including the indexing, graph, and secret-scanning multiprocessing pools (which the earlier per-spawn fix did not cover) — now runs window-free on Windows: the pools launch via the console-free `pythonw.exe`, falling back to serial execution when it is unavailable. No spawn inherits a blocking stdin, which previously could hang the upgrade.
- **Native-Windows upgrade no longer crashes on encoding or paths.** The upgrade uses the platform temp directory instead of a POSIX `/tmp` fallback (absent on Windows), forces UTF-8 on stdout at every CLI entry point so a non-ASCII glyph no longer raises a `UnicodeEncodeError` in a cp1252 console, and gives spawned indexer/graph/secrets children their own UTF-8 stdio — fixing the silent index-build failure and the garbled output.
- **`wave_install_audit` validates artifacts correctly.** The install-log parser no longer misreads an artifact's description text as a file path, so the install-state check verifies real on-disk artifacts again.
- **MCP `handler_not_ready` during upgrade/reload.** The server now lazily builds its handler from the known repository root, so a started server no longer reports `handler_not_ready` in the startup or post-reload window.

## [1.9.4] - 2026-06-27

### Added

- **New `wf` subcommands for agent-run framework scripts.** `wf codebase-map`, `wf render-surfaces`, and `wf secrets-scan` join the cross-OS `wf` dispatcher so operators and agents stop guessing raw `python3 .wavefoundry/framework/scripts/*.py` invocations. Framework upgrade cleanup stays a manual `python3 .wavefoundry/framework/scripts/prune_framework.py` step — it needs the pre-upgrade MANIFEST that only the operator running the upgrade holds.
- **Upgrade-time retired-surface reconciliation.** A minor-or-major `wf upgrade` now scans the repository for stale references to retired framework surfaces (such as the per-command `.wavefoundry/bin/*` wrappers replaced by the cross-OS `wf` dispatcher) and reports an actionable `file:line → suggested wf form` list in place of generic recommend-only prose. The scan is report-only and exclusion-aware (it skips the framework pack, the generated index, historical records, and tests) and matches both forward-slash and backslash path references. Reconciliation guidance also names host permission/allow-rule files (for example `.claude/settings.local.json`) as a surface to flag for the operator rather than self-edit, and clarifies the gate-before-reload window during upgrade.
- **Structured `wave_upgrade` summary.** `wave_upgrade` now returns a parsed `summary` block (from/to version, files pruned, docs-gate result, index-update state, failed phase, and the reconciliation findings) plus a top-level `next_step` and `next_tools`, so agents read computed fields instead of scraping the raw output. The existing `output` and `exit_code` are unchanged and parsing is fail-safe.

### Changed

- **Committed MCP configs standardize on `python3`.** Every generated host MCP config launches the server with `command: "python3"` and the repo-relative `server.py`, byte-identical across macOS, Linux, and native Windows. `wf setup` **verifies** `python3` resolves to Python 3.11+ and, when it does not, fails closed with platform-aware guidance (install via Scoop/Microsoft Store on Windows, or your package manager / a symlink on macOS/Linux) plus the no-PATH per-machine fallback config. Setup does not modify your Python installation or PATH.

### Fixed

- **MCP helper subprocesses no longer contend with the host's JSON-RPC stdio.** Server-side helper processes (docs-lint, gardener, sync-surfaces, upgrade phases, sensors) now run with `stdin` detached and intentional stdout/stderr handling — fixing `wave_validate`/docs-lint-over-MCP timeouts seen on some hosts — and suppress their console window on native Windows.
- **Setup fails loudly instead of silently shipping a dead MCP config.** When `wf setup` finds `python3` does not resolve to Python 3.11+ on PATH, it reports the exact problem and exits non-zero with platform-aware guidance (make `python3` resolve — Scoop/Microsoft Store on Windows, your package manager or a symlink on macOS/Linux — or use the per-machine absolute-venv-path fallback) rather than reporting success for a `command: "python3"` config the host cannot launch. Setup does not modify your Python installation or PATH.

## [1.9.3] - 2026-06-26

### Changed

- **MCP startup no longer starts model prewarm.** The MCP handler no longer launches background embedding/reranker cache work while the host is still negotiating stdio and loading tool schemas; semantic search starts the optional prewarm after startup instead. Install guidance now reinforces the generated config contract: launch MCP with PATH `python3` on `server.py`, not a hardcoded tool-venv Python path, and start a fresh host session after config/Python fixes. `wf setup` now smoke-tests the same `python3 server.py --dry-run` launch shape used by generated MCP configs.
- **Model-fetch CA discovery honors Node's CA bundle env var.** The setup/model-download trust-store fallback now recognizes `NODE_EXTRA_CA_CERTS` after `CODEX_CA_CERTIFICATE` / `CLAUDE_CODE_CERT_STORE` and before `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE`, so native Windows users launched from Node-based agent hosts can reuse the same corporate CA bundle the host process already trusts. Wave 1p7pk / native-Windows field follow-up.

## [1.9.2] - 2026-06-26

### Changed

- **Windows and no-PATH setup guidance leads with `wf`.** Operator-facing install, upgrade, prompt index, framework-operator, dashboard, and install-seed guidance now treats `wf setup` and `wf` subcommands as the primary command surface, with repo-local `wf.cmd` / POSIX shim paths only as no-PATH fallbacks. This closes the guidance hole where agents guessed a plain-Python invocation of `.wavefoundry/bin/wf` on native Windows. Wave 1p7pk / native-Windows field follow-up. Current guidance standardizes launcher commands on `python3`.

### Fixed

- **Native-Windows MCP stdio framing hardening.** The MCP runner now configures stdin/stdout/stderr to UTF-8 with LF-only newlines before building the server and entering the stdio transport, with stdout/stderr write-through enabled. This keeps Wavefoundry's side of the JSON-RPC stdio boundary byte-stable on native Windows text streams while preserving stderr-only diagnostics. Wave 1p7pk / native-Windows field follow-up.

## [1.9.1] - 2026-06-26

### Fixed

- **Native-Windows MCP server reliability (broken pipe on startup).** The tool venv is now activated **in-process** (`site.addsitedir`) instead of re-execing into the venv interpreter. The re-exec used a subprocess child on Windows (no in-place exec there), which became a second process holding the same stdout pipe the MCP host owns — causing an intermittent broken pipe when the tool list arrives and orphaned processes across reconnects. In-process activation keeps a single host-spawned process on every OS while preserving the byte-identical `command: "python3"`. If the venv was built for a different Python `(major, minor)` than the running interpreter (e.g. after a system Python upgrade), normal entries fail loud with a clear "run `wf setup` to rebuild" message, while `wf setup` bypasses activation and recreates the stale tool venv. Wave 1p7pk / 1p802.

## [1.9.0] - 2026-06-25

> **Native Windows (no WSL2), and a single runtime surface.** Every committed launcher and config now names one byte-identical `command: "python3"` and runs from a single checkout on macOS, Linux, and native Windows for CLI hosts. Upgrading retires the nine `.wavefoundry/bin/*` wrappers for one cross-OS `wf` CLI and flips the MCP/hook commands to `python3` — so **`setup` / upgrade makes `python3` resolve** without creating a `python` symlink. Drive the upgrade with `wave_upgrade()` (MCP) or `wf upgrade`. GUI-launched hosts that don't inherit the shell PATH use the printed absolute-venv-path fallback.

### Added

- **Native Windows support without WSL2 (CLI hosts).** The MCP server, hooks, git hooks, and operator CLI run from a single committed checkout on native Windows. The committed `command` is the byte-identical `python3`; the tool venv is activated **in-process** (`site.addsitedir`) so the server stays a single host-spawned process on every OS (no re-exec/child — see *Fixed* above); the venv layout (`Scripts\python.exe` vs `bin/python`) resolves in one place; rendered surfaces are written with byte-fixed line endings on every host; and a repo `.gitattributes` pins shebang-bearing files to LF (and `wf.cmd` to CRLF) so `autocrlf` can't corrupt them.
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
