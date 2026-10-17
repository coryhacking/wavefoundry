# Make release verification and qualification provenance explicit

Change ID: `20qvs-enh release-provenance-verification`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-17
Wave: `20wq7 distribution-release-follow-ups`

## Disposition

Deferred by operator scope direction on 2026-10-15. Revived on 2026-10-17 by operator direction after a downstream distribution report (its items K1, K2 and G16), and narrowed: signing and attestation stay deferred because no authority has been chosen. This change delivers the parts that need no signing authority.

## Rationale

A distribution that builds and ships packs from our source needs three things it cannot get today. First, a pack built from an untagged commit after a release carries no record of the commit it came from, so it cannot be told apart from the release by its contents. Second, `build_pack.py --release` publishes without checking any qualification report, so a release can go out with the renamed `second` profile red, and nothing in the release says which failures were accepted. Third, a downloaded pack is verified only against itself; nothing published outside the archive lets a consumer check the bytes before running or extracting them.

## Requirements

1. **Release qualification gate.** `build_pack.py --release` and `--release-dry-run` run a qualification gate as the last step of the release preflight block, after the changelog-claim checks and before the docs gate and any build or stamp. It reads `.wavefoundry/cache/qualification/default.json`, `second.json` and `declared.json` only through `qualification_report.read_report(repo_root, path)`. The current framework inputs hash is `lifecycle_gate_support._load_framework_test_runner(<repo>/.wavefoundry/framework/scripts/run_tests.py)._hash_inputs()`; when the runner is absent or cannot be loaded, the gate refuses, and it never inherits the close gate's no-op. A direct `import run_tests` is not used, because importing it changes process bytecode settings and can exit while activating the tool environment. The default report must pass `qualification_report.validate`, name profile `default`, have full scope, and carry `identity.source_hash` equal to the current hash. The `second` and `declared` reports must each pass `qualification_report.compare(default, candidate, profile, root=repo_root)`. The gate recomputes the inputs hash immediately before `build_zip` and refuses when it changed since preflight, so the gardener cannot make the pack differ from the qualified tree. Each refusal names the profile and the reason, and names the command that regenerates the report.
2. **Named exceptions.** `--accept-qualification-exception PROFILE=REASON`, repeatable, applies only to `second` or `declared`, at most once per profile. `REASON` is one line of 1 to 500 characters with no C0 or C1 control character and no `str.splitlines` boundary. An exception admits only a report that is present, readable and owned, names its profile, whose `identity.source_hash` equals the current hash, and whose `executed_identity` is present with `profile` equal to that profile and a well-formed 64-hex `source_hash` (that hash covers the profile-rewritten copy, so it never equals the original tree's hash and is not compared), where `validate` or `compare` then refuses with a `ValueError` (a failing worker or a skip difference). Tests pin which refusals an exception can admit. A missing, unreadable, unowned, linked, malformed, stale, wrong-profile or scope-mismatched report refuses even with an exception, and any exception other than `ValueError` from `validate` or `compare` refuses without being embedded. An exception for a profile whose report passes is refused as stale. The default report never takes an exception. The gate does not detect forgery: any process running as the maintainer can write these reports, so it prevents accidents and is not an attestation.
3. **Qualification in the release notes.** The gate returns a `### Qualification` section that `main` appends after the assembled notes, so `_assemble_release_notes` is unchanged. It has one line per profile with its result, its test, worker-file and skip counts, and the 12-character prefix of the source hash. A profile under an exception gets a line naming the exception, the operator's reason and the comparator's `ValueError` text. `--release-dry-run` prints this section in full.
4. **Build provenance in every pack.** `build_zip` gains a keyword-only `release_tag=None`, which only `main` sets, to `vMAJOR.MINOR.PATCH` under `--release` (not under `--release-dry-run`, which creates no tag). At the top of `build_zip`, before `write_pack_version`, it reads `source_commit` from `git rev-parse HEAD` and `source_tree_clean` from `git status --porcelain`, both run with argument lists, `cwd=repo_root`, no shell, and only when `git rev-parse --show-toplevel` resolves to the repository root, so a parent repository or an inherited `GIT_DIR` cannot supply the commit. Output that is not exactly 40 lowercase hex characters, a missing Git, a failing command or a non-checkout makes both fields `null`, and Git's stderr is never written. It then writes `.wavefoundry/framework/BUILD-PROVENANCE.json` with exactly `schema_version` (1), `release_version` (the stamped `MAJOR.MINOR.PATCH+<build>`), `build_id`, `source_commit`, `source_tree_clean` and `release_tag`, so it is collected and listed in MANIFEST like `UPGRADE-PROTOCOL.json`. `MANIFEST`, `UPGRADE-PROTOCOL.json` and `BUILD-PROVENANCE.json` are all removed from the source tree in one `finally`, so none lingers after a failed build. In release mode the docs gate runs before the build, so gardener output makes `source_tree_clean` false, which is accurate, and `source_commit` is the parent of the stamp commit that the tag points at. Protocol and selection metadata keep their exact field sets, because older runners validate them strictly. The bridge and combined archives carry the file as built; after a bridge-only stop, the installed file names the feature build while VERSION is still the old one, which is accepted. The file holds no paths, user names or remote URLs.
5. **Published checksums.** Before step 1 of release orchestration, digests are computed for every asset, so a read error leaves the tree untouched. A fresh temporary folder (from `tempfile.mkdtemp`, never inside the repository or the output folder) receives a file named exactly `SHA256SUMS` with one `<sha256>  <filename>` line per asset, sorted by filename, LF endings, written as bytes. It is uploaded as one more asset in step 5. On success the folder is removed. On a step-5 failure the folder and a copy of the notes file are kept, and the recovery command names both paths. Asset basenames must match `[A-Za-z0-9._+-]+` or orchestration refuses before step 1. `--release-dry-run` prints the lines.
6. **Verification guidance.** Every surface that tells a person or agent to obtain a release pack carries one verification step: seed 160 at its "Operator mental model" and step 0 adoption text, seed 010, the local `docs/prompts/upgrade-wavefoundry.prompt.md` at the matching places (it is maintained locally, not rendered from the seed), `.wavefoundry/framework/install/install-block.md` (prepended to every release's notes), and the README Quick start. The step: verify each asset you download, including the combined `.with-models.zip` and the model companion, immediately after download and before placing it in any discovery folder, extracting it, running it with `python3 <zip>` or running Upgrade Wavefoundry. Compare against that asset's single line in the release's `SHA256SUMS`, and stop when the digest differs or the asset has no line or more than one. Commands: `shasum -a 256 <zip>` on macOS, `sha256sum <zip>` on Linux and WSL2, and `(Get-FileHash -LiteralPath <zip> -Algorithm SHA256).Hash -eq '<hex>'` in Windows PowerShell, where `-eq` ignores case. The guidance says this checks the downloaded bytes against a digest published in the same GitHub release: it detects corruption, truncation and a copy altered after it left the release, and it does not detect a replacement by anyone able to edit the release, who could edit `SHA256SUMS` too. It is not a signature, and signing remains deferred. No new upgrade carrier is added; consumer-local prompt copies reconcile through the normal upgrade pass.
7. **Release docs.** `docs/prompts/package-wavefoundry.prompt.md` changes "optional release evidence" to say the three reports are required by `--release` and `--release-dry-run`, and documents the exception flag, the notes section, `BUILD-PROVENANCE.json` and `SHA256SUMS`. `docs/references/release-flow.md` and `docs/contributing/build-and-verification.md` update their preflight lists, their uploaded-asset statements and the "opt-in" qualification sentence. The threat model's distribution-archive row names `SHA256SUMS` and says it is not a signature.
8. **Platforms.** Packaging runs on the maintainer's machine; Git is invoked with argument lists and no shell everywhere, and `SHA256SUMS` is written as LF bytes with bare filenames. Consumer verification commands cover Windows PowerShell, macOS, Linux and WSL2. Upgrade and install behavior is unchanged apart from one new framework file arriving with the pack. `build_pack.py`, `qualification_report.py`'s comparator and `tests/` are source-host only (excluded from packs), which is why the comparator's import of `tests.record_layout_support` is acceptable here.

## Scope

**In scope:** Requirements 1 to 8 and their tests in `tests/test_build_pack.py`.

**Out of scope:** signing or attestation authority and any trust root (see Open Decisions), automatic verification inside the upgrade runner, changes to protocol or selection metadata, a VERSION commit after every source commit, timing investigation and threshold changes, and the release itself (no tag, push or publish in this wave). The release owner adds CHANGELOG bullets for the gate and exceptions, `BUILD-PROVENANCE.json`, and `SHA256SUMS` with its guidance, under the next release section.

## Acceptance Criteria

- [x] AC-1: Fixture reports are built like `ExactReaderTests.report` in `tests/test_qualification_report.py` (full scope, `applied_profile` and `profile_input_hash` from `load_profile`, `executed_identity`) in a temporary repository carrying a copy of `tests/fixtures/profiles`, and the inputs hash is patched only through the one function the gate calls. The gate passes when all three qualify, and its section lists all three. It refuses, naming profile and reason: a missing default report, a red default, a default with non-full scope, a default naming another profile, a stale default hash, a runner that cannot be loaded, and a failing `second` or `declared` report without an exception. With an exception a failing current report, whose `executed_identity.source_hash` differs from the original hash as in a real profile run, passes and the section names the reason and refusal. Even with an exception, it refuses a missing report and a stale-hash report. It refuses an exception for a passing profile, for `default`, for an unknown profile, a duplicate, an empty reason, a 501-character reason and a multi-line reason, and accepts a 500-character reason. A hash change between preflight and build refuses. `main()` with `--release-dry-run --with-models` in a temporary repository, with Git and gh checks patched to pass, exits non-zero naming the missing profile, without calling `build_zip` or `check_docs_gate`, and leaves VERSION bytes unchanged.
- [x] AC-2: A built pack contains `BUILD-PROVENANCE.json` with exactly the six fields, and MANIFEST lists it. In a fixture Git checkout built like `ProfileRunTests._tiny_repo`, `source_commit` equals `HEAD`, `source_tree_clean` is false for a dirty fixture, and two commits give two values. `release_tag` is set only when passed. In a folder where `git rev-parse` first fails, and in a folder nested inside another checkout, both source fields are `null`. A build forced to fail after the file is written (a `zipfile.ZipFile` side effect that first asserts the file exists) leaves none of MANIFEST, `UPGRADE-PROTOCOL.json` or `BUILD-PROVENANCE.json` on disk. Build, verified-pack and upgrade tests pass unchanged; release-orchestration and release-main tests keep every assertion and change only by patching the new gate, using real asset files, and expecting the appended notes section.
- [x] AC-3: Release orchestration under the existing recorder, with `extra_assets` holding a model and a combined file so that sorted order differs from input order, uploads a file whose basename is exactly `SHA256SUMS`. Its bytes, captured when `gh` is called, hold one line per other asset, digests equal to `hashlib` over each file, sorted, LF only, with no line for itself. After success the temporary folder is gone. A forced step-5 failure keeps it, and the recovery text names it and the kept notes file. A non-conforming asset name refuses before step 1. Dry-run prints the same lines.
- [x] AC-4: Every surface in Requirement 6 carries the step with all platform commands and the not-a-signature statement; the docs in Requirement 7 are updated; tests that reference the upgrade prompt or the install block pass; full docs validation passes.
- [x] AC-5: Run `run_tests.py --no-cache --qualification-report .wavefoundry/cache/qualification/default.json`, then `--qualify-profile second --qualification-report .wavefoundry/cache/qualification/second.json`, then the same for `declared`, one at a time on the final tree. Both `qualification_report.py --compare` runs pass, and the new gate function, called read-only on the final tree with the real hash, accepts all three with no exception. This single run also satisfies 20wq6 AC-4.

## Tasks

- [x] Implement the qualification gate, exception parsing and notes section in `build_pack.py`, with the pre-build hash recheck.
- [x] Write `BUILD-PROVENANCE.json` in `build_zip` and move generated-file cleanup into one `finally`.
- [x] Write and upload `SHA256SUMS` from a temporary folder, with the recovery text, asset-name check and dry-run printing.
- [x] Add the AC-1 to AC-3 tests to `tests/test_build_pack.py` and adjust release tests only as AC-2 allows.
- [x] Update seed 160 and seed 010 under the seed gate, then the local upgrade and package prompts, the install block, the README and the release docs.
- [x] Run the full suite, then the two profile qualifications sequentially, then the read-only gate check, and record results in wave.md.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Packaging behavior and tests | Implementer | Readiness | Single write owner of `build_pack.py` |
| Guidance and docs | Implementer | Packaging behavior | Seed gate open only for the two seed edits |
| Verification and review | QA and required reviewers | Implementation | Read-only review; coordinator records evidence |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `.wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md`
- `.wavefoundry/framework/install/install-block.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `docs/prompts/package-wavefoundry.prompt.md`
- `docs/references/release-flow.md`
- `docs/contributing/build-and-verification.md`
- `docs/architecture/threat-model.md`

- The root `README.md` Quick start.

Write ownership: the implementer owns all edits. Reviewers are read-only. Protect publication guards, existing release recovery messages and the exact protocol and selection metadata field sets.

## Affected Architecture Docs

`docs/architecture/threat-model.md` (distribution-archive row). Release references and contributing docs are listed in Requirement 7. No boundary or flow change: `build_pack` gates, and `qualification_report.compare` stays the only judge of a profile report.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The release gate is the core of K2. |
| AC-2 | required | Build provenance is the core of K1. |
| AC-3 | required | Published checksums are the deliverable part of G16. |
| AC-4 | required | Consumers act only on guidance. |
| AC-5 | required | The next release must be able to pass its own gate. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-15 | Planned only; implementation and approvals pending | This plan and wave record |
| 2026-10-17 | Qualification on the final tree, one run at a time: canonical default `--no-cache` 11,890 tests / 200 files / 12 skips, receipt inputs_hash `fc8af1b262ad8b54c413e8155d3c62f8d9f8d23f7a4ed8e02b234f4351a49da7`; `--qualify-profile second` 11,882 / 200 / 28 skips; `--qualify-profile declared` 11,890 / 200 / 12 skips; both scopes `full fallback: coverage unproven`. `qualification_report.py --compare` passes for both (second: 16 default-only skips; declared: equal). The new gate, called read-only on the real tree, lists all three as passed with no exception. A first attempt was invalid: a reviewer's concurrent focused run held the runner lock and raced the live-tree build's generated files during a profile copy, and the declared run exposed two wave-caused census failures (a timed git call outside the tree-kill routing census, and a patched loader not asserted), both fixed and confirmed by code and security before the rerun. | scratchpad 20wq7-qual-{default,second,declared}.log; .wavefoundry/cache/qualification/{default,second,declared}.json |
| 2026-10-17 | Implemented. `build_pack.py`: `_read_source_provenance`, `build_provenance`, `_parse_qualification_exceptions`, `_current_framework_inputs_hash`, `_check_release_qualification`, `build_zip` split into `build_zip` plus `_build_zip_body` with one `finally` removing MANIFEST, `UPGRADE-PROTOCOL.json` and `BUILD-PROVENANCE.json`, `release_tag` keyword, `--accept-qualification-exception`, gate last in preflight with a pre-build hash recheck, `_release_checksum_lines` and a `SHA256SUMS` staging folder kept on upload failure. Release tests changed only by patching the gate, using real asset files and expecting the appended section. Two pre-existing release-main rejection tests (`test_release_main_rejects_extra_current_build_public_package`, `test_release_main_rejects_preexisting_special_upgrade_artifact`) exit at the missing `--with-models` check before preflight, so they never reached the code they name; left as they were, follow-up. Guidance and release docs updated per Requirements 6 and 7. Delivery finding DEL-1 (code and red-team, independently): an exception admitted a report with top-level returncode 1 and every worker green (runner or repository guard failure), outside Requirement 2; repaired so such a report refuses, and the notes record any excused skip difference. Reviewer notes applied: format characters refused in reasons, `--no-cache` in the default regenerate hint, `SHA256SUMS` in the dry-run gh line, missing gh becomes the step-5 failure with recovery text, older releases without `SHA256SUMS` compare against the digest GitHub shows. Focused after repair: `test_build_pack` 151/151 with shipped-reference, upgrade-protocol, vocabulary-prompt and docs-lint files, 681 tests. Mutants: 12 initial guards and 7 repair guards killed by the intended tests. Red-team alternative not taken: keying exceptions to named workers (`PROFILE=WORKER[,WORKER]:REASON`); the smaller repair meets Requirement 2. Gapfill: shell reads and Python edit scripts, as for 20wq6. | scratchpad 20wq7-mutants.log, 20wq7-mutants2.log, 20wq7-repair-1.log; events.jsonl DEL-1 |
| 2026-10-17 | Red-team confirmation round: an exception required `executed_identity.source_hash` to equal the current hash, which a profile run never satisfies (`run_tests._run_profile` copies the inner report's identity, hashed over the rewritten copy). Requirement 2 now requires only a well-formed executed identity naming the profile; AC-1 uses a differing executed hash. | `run_tests._run_profile`; `20st7-second.json` executed hash `24467c66ab20` vs source `ea4a92805292` |
| 2026-10-17 | Readiness corrections folded in before approval: exceptions limited to present, current reports; hash from the loaded runner with refusal when unloadable; `compare` with root; pre-build hash recheck; `release_tag` keyword and dry-run null; Git provenance bound to the repository root; single `finally` cleanup; `SHA256SUMS` in a temporary folder kept on upload failure; guidance extended to the install block, README and step 0 with honest wording and exact commands; release docs and the threat-model row added; AC controls made specific. | Readiness reports from red-team, code and architecture, QA, security, docs-contract and release |
| 2026-10-17 | Revived and narrowed by operator direction after the distribution report. Checked at HEAD `3c6416d6`: `build_pack.py` reads no qualification report in release mode; protocol and selection metadata are exact-field validated by older runners (`upgrade_protocol.validate_protocol_metadata`, `upgrade_bridge_bootstrap`), so provenance goes in a new file; packs already get a fresh time-based build stamp, so only the source commit is missing. | `build_pack.py` release preflight; `upgrade_protocol.py`; `upgrade_bridge_bootstrap.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-15 | Choose artifact provenance tied to source and explicit release qualification. | Coherent contract with focused regression coverage | Self-hashing archives alone: no independent authenticity. Per-commit VERSION churn alone: does not authenticate artifacts or explain exceptions. |
| 2026-10-17 | Narrow to the gate, provenance file and published checksums; defer signing. | No signing authority is chosen, and these parts stand alone. | Choose an authority now (rejected: an outward-facing security decision the operator has not made). |
| 2026-10-17 | Provenance in a new `BUILD-PROVENANCE.json`, not in protocol or selection metadata. | Older runners refuse any extra field in those files. | A zip comment (rejected: invisible after install). |
| 2026-10-17 | Exceptions only for `second` and `declared`, never for `default`. | The default suite already gates close through the receipt; the renamed profiles are where accepted timing failures have occurred. | Allow any profile (rejected: a red default must never ship). |

## Open Decisions

Signing or attestation authority, and the offline trust root that consumers would use to verify it, remain undecided. They are outside this narrowed change.

## Risks

| Risk | Mitigation |
| --- | --- |
| A consumer reads `SHA256SUMS` as authenticity. | The guidance states it is not a signature; signing stays an open decision. |
| The provenance file lingers after a failed build and changes the receipt hash. | Removal runs in a `finally`; AC-2 covers the failure path. A leftover file is not gitignored, so the clean-tree preflight would catch it. |
| Release notes are read as attestation. | The gate prevents accidents only; Requirement 2 says any maintainer process can write the reports. |
| The gate blocks a release when reports are merely old. | Refusals name the stale report and the command that regenerates it. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
