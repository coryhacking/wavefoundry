# Reduce Sourcegraph noise and make rule overrides effective

Change ID: `22o91-bug scanner-rule-compatibility-and-sourcegraph-noise`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-05
Wave: 22o93 scanner-rule-corrections

## Rationale

The operator requested evaluation of the Gitleaks-derived TOML ruleset. The actual framework asset is adapted from Betterleaks commit 3ac987600af0, downloaded 2026-06-06, with a Python engine and local CEL/policy extensions. It is not an unmodified current Gitleaks engine/configuration. The public README has been corrected to make this distinction.

The evaluation fetched immutable official sources into temporary review storage: [Betterleaks 8f376ff9](https://github.com/betterleaks/betterleaks/blob/8f376ff9c31ed5309ac448fe601c5dd21b376155/config/betterleaks.toml), committed 2026-11-04, and [Gitleaks 5f6ec56c](https://github.com/gitleaks/gitleaks/blob/5f6ec56cfa6f8c67648d863582c7ae2f206d5c1c/config/gitleaks.toml), committed 2026-10-23. Current Wavefoundry has 280 rules; these snapshots have 474 and 222 respectively. A rule count is not a coverage or quality score. The newer Betterleaks snapshot adds 199 IDs, removes 5 and changes 138 common regexes; it also introduces metadata/correlation/validation constructs the local engine does not implement.

Two concrete changes deserve early adoption:

- The current Sourcegraph detector accepts any bare 40-character hex string when a file contains its keyword. The newer Betterleaks detector requires an sgp_ prefix and narrows its keywords accordingly. At this evaluation checkpoint, 42 of 47 recorded findings use the Sourcegraph rule; all 47 are classified false positives. In an actual scan_file_raw replay using only the relevant rule, the current detector flags a synthetic Git commit in Sourcegraph prose; the candidate does not. Both detect modern, local and instance-prefixed synthetic token forms; both reject a short malformed form. This is bounded discrimination evidence, not a general scanner precision claim.
- An actual load_merged_ruleset call against temporary framework/project TOML files with the same synthetic rule ID returns the framework regex OLD instead of the project regex NEW, with no error. The replacement comprehension shadows the intended project rule. This prevents the documented same-ID override behavior and should be repaired before relying on a project-level detector correction.

Wholesale refresh is not ready. All 280 current regexes and their 178 filters compile/parse under the existing shim/parser. The newer Betterleaks regexes compile in the probe, but 17 filter expressions fail the current CEL parser; runtime eval_filter currently treats evaluation failure as do-not-suppress. New components/valueGroup/analyze/validate/revoke semantics are not provided by copying TOML. Compilation alone does not prove regex equivalence or detection coverage. A suspected POSIX-class issue was checked with a synthetic Airtable shape: the current local rule and the equivalent alphanumeric control both match, so no local Airtable defect is claimed.

## Product Intent

Operators should spend less time classifying ordinary source-control evidence while retaining useful credential detection and effective project customization. AC-1 to AC-3 test the specific rule/override outcomes; AC-4 prevents an incompatible upstream import from being mistaken for qualified scanning. This supports Horizon 1's dependable foundation without adding acceptance ceremony or claiming absence of secrets.

## Requirements

1. Make an explicitly same-ID project rule replace the corresponding framework rule while preserving unrelated rules, deterministic ordering, disabled_rules behavior, policy merging and meaningful invalid-input errors. Keep project additions and a missing optional project file working. Exercise the actual loader and scanner, not only a list-replacement helper.
2. Follow the Sourcegraph detector in pinned Betterleaks 8f376ff9: require an sgp_ prefix, including supported modern, local and instance-specific forms, and use its narrowed sgp_ keyword. Preserve boundary checks. By explicit operator choice, this rule no longer detects legacy unprefixed 40-character hexadecimal tokens, including in named Sourcegraph credential settings. Do not add a context-only legacy branch, broadly allowlist hexadecimal strings or disable the whole credential family. Keep rule provenance/local adaptations and this intentional coverage reduction visible. This selects one detector update, not a wholesale upstream refresh.
3. Keep scanning local and execution-free: imported validate/analyze/revoke blocks are untrusted configuration data, not authorization to contact a provider, test a credential or revoke it. Preserve existing local policy, self-exclusions, documented performance rewrites, redaction, JWT treatment, confirmation lifecycle and model-independent execution.
4. Add a bounded compatibility check for the rule fields and filter constructs considered for import. Unsupported semantics and failed filter parsing must be visible in qualification; an upstream rule must not be described as fully supported merely because its regex compiles. This change does not implement the full current Betterleaks/Gitleaks engine. Defer new detector families until their actual extraction, filters, false-positive controls and performance are qualified.
5. Preserve meaningful positive/negative controls: Git commit/checksum prose, token-like malformed strings and synthetic prefixed credential shapes. Use no live credentials or external validation requests. Confirm a ruleset change invalidates incremental scan currency and takes the existing full-rescan route; review existing dispositions through normal tooling rather than silently rewriting their history.
6. Update scanner documentation and changelog with precise source commits, supported behavior, the selected legacy-token treatment and remaining import limitations. Record the project-level broad test/spec path exclusions as an existing coverage limitation, not proof those files contain no credentials. Changing those project exclusions is outside this bounded repair.

## Scope

In scope: effective project overrides, the targeted Sourcegraph detector, a bounded upstream compatibility check, consumer regressions and accurate scanner contracts/provenance.

Out of scope: wholesale 474-rule replacement, network credential validation or revocation, replacing the scanner engine, blanket hash/doc exclusions, automatic triage, changing confirmation authority, broad project path-exclusion changes, real secret handling or release publication. Current work is evaluation/planning only; no scanner rule or engine source was edited.

## Acceptance Criteria

- [x] AC-1: Actual framework/project loading and scanning honors a same-ID replacement, retains unrelated/additional rules and handles disabled rules and malformed input correctly. Restoring the current shadowed replacement reproduces the failed override.
- [x] AC-2: Isolated actual Sourcegraph-rule scanning detects synthetic sgp_<40 hex>, sgp_local_<40 hex> and sgp_<16 hex>_<40 hex> forms and rejects ordinary Git/checksum prose and malformed/boundary controls. It also rejects an unprefixed 40-character hexadecimal value in an explicit Sourcegraph credential assignment, recording intentional legacy coverage loss rather than claiming that value is harmless. The old bare-hash branch fails negatives; removing the token detector fails positives. Other detectors cannot rescue this rule's positive controls. Independent review verifies this exact selected format matrix and downstream coverage wording.
- [x] AC-3: Targeted rule loading/scanning remains local, redacted and bounded; no imported validator/revocation action executes. The normal rule-change full-rescan behavior remains effective and triage history is preserved through its owning workflow.
- [x] AC-4: Compatibility qualification identifies known unsupported upstream filters/fields and detects its own bad controls without treating regex compilation as semantic proof. Documentation states the supported subset and does not claim a full upstream refresh or secret-free repository.

## Tasks

- [x] Preserve the current loader/noise failures and the pinned candidate rule as implementation baselines.
- [x] Repair same-ID override and select the narrowly qualified Sourcegraph update, with explicit legacy treatment.
- [x] Add compatibility and scanner-consumer controls; update provenance/contracts and verify required independent reviews.

## Agent Execution Graph

One source owner integrates the loader, rule and tests after admission/readiness. Independent security, code, QA, architecture and docs-contract lanes check false negatives, authority boundaries and truthful import claims. Tests use temporary files and synthetic values; no network scanner probe is authorized.

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scan-rules.toml`
- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/cel_filter.py`
- `.wavefoundry/framework/scripts/scan_secrets.py`
- `.wavefoundry/framework/scripts/tests/test_secrets_validators.py`
- `.wavefoundry/framework/scripts/tests/test_scan_secrets.py`
- `.wavefoundry/framework/scripts/tests/test_secrets_prefix_collapse.py`
- `.wavefoundry/framework/scripts/tests/test_cel_filter.py`
- `docs/architecture/threat-model.md`
- `docs/contributing/build-and-verification.md`
- `docs/specs/mcp-tool-surface.md`

Only scanner files needed by the bounded requirements may change. CHANGELOG.md records the selected detector/override repair. docs/scan-rules.toml, docs/scan-findings.json classification history, unrelated detector families, seeds and unrelated artifacts are protected except normal scanner-owned observations. test_cel_filter.py is a proposed test file if absent; existing CEL controls may instead stay in test_secrets_validators.py. New evaluation fixtures or additional source targets require declaration before readiness. No source/seed gate is open.

## Affected Architecture Docs

Update the scanner trust/coverage description in the threat model and build/tool contracts. Preserve the distinction between detection, triage and operator authorization; no trust boundary is expanded.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Documented project overrides must actually affect detection. |
| AC-2 | required | Noise reduction must retain qualified credential detection. |
| AC-3 | required | An upstream configuration must not authorize network actions. |
| AC-4 | required | Unsupported semantics must not be represented as working coverage. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-05 | Operator selected the pinned Betterleaks prefixed-only Sourcegraph rule: "let's follow the new betterleaks rules." | The immediately preceding comparison explained that Betterleaks removes bare-hex detection while Gitleaks and the shipped rule retain it. The choice accepts that coverage reduction, including explicit credential assignments; supported prefixed forms remain required. | Context-limited legacy coverage was recommended but not selected. Loader-first splitting is unnecessary now that the compatibility choice is settled. No broader rule import is authorized. |
| 2026-11-05 | Prefer a targeted upstream Sourcegraph update plus the actual override repair before any broad refresh. | Synthetic consumer controls discriminate commit prose from supported token forms, and actual same-ID loading fails. The engine compatibility probe finds 17 newer filters that cannot parse. Success is consumer detection/override behavior and explicit compatibility, not a larger rule count. | A full Betterleaks replacement imports unsupported semantics; direct Gitleaks replacement omits 58 IDs already present locally and changes filtering semantics; blanket hex allowlisting can hide real credentials. |
| 2026-11-05 | Retain the evaluation's evidence limits. | The 47 findings are local historical triage, not measured global precision. Compiling regexes does not establish equivalent semantics; no live validation ran. Legacy unprefixed coverage needs an explicit decision and tests. | Reporting all imports qualified or treating every hash-shaped value as harmless would exceed the evidence. |

## Risks

The operator-selected narrower detector intentionally loses legacy unprefixed credential detection; document it without relying on another rule to cover the gap. A project override fix can affect downstream rules previously ignored, so verify ordering/disable precedence. Betterleaks current filters, components and metadata exceed the local engine subset. Its RE2 assumptions and Python backtracking require differential and bounded-cost checks for any imported pattern. Do not copy network validation into local scanning.

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-06 | All four ACs and three tasks complete, no deferrals. Six technical lane approvals and Council PASS establish the bounded intent; wave stays open for operator review. | Final canonical EXIT 0: 12,411 tests / 218 files / 12 expected skips / 614.796 seconds. Current green inputs_hash 7ad25d4f851118e37ffb85dc82560b9e25438bd328aa61ee0d55d43c1b964161, ran_at 2026-11-06T09:05:21.019783+00:00. No nonignored/MCP/lifecycle writes occurred through exit. Gates closed; no closure, commit, release or live credential action. Broader ruleset adoption remains unadmitted plan22o94. |
| 2026-11-06 | Independent delivery checks support all four ACs with no actionable finding; final canonical qualification remains pending. | Code/architecture/performance14 tests plus old-loader mutant and bounded cost probes; QA39 tests plus independent old/current detector matrix, lost-positive and filter controls; security14 tests plus zero-attempt action traps and detector mutants; docs three compatibility controls; reality two actual-loader observations. All11 target identities remain unchanged. Council unanimously supports the bounded intent after anonymous merits and identity disclosure; native/field/global-coverage claims remain excluded. |
| 2026-11-06 | Implemented the bounded loader, detector and opt-in compatibility changes; froze 11 declared targets for independent review at manifest204cb832c7d8d804fbe23f9d93e89791d7114d2c. Optional CEL tests remain in the existing validator test file. | Six focused scanner modules pass250 tests in29.362 seconds. Maintained TestLoadMergedRuleset, SourcegraphPrefixedRuleTests, RulesetCompatibilityInspectionTests and ActualRulesChangeConsumers cover actual loading/scanning, exact formats, inert action traps, redaction, both real cache producers, unchanged-file rescans and retained dispositions. Baseline commit729c069b2cacb5f698cffcbc9cc83fee5b158f56 supplies old loader/rule controls; old override, bare detector and blind-compatibility controls each fail one assertion; removing the detector fails27 positive subcases, all with zero errors. Freezing the prior rules fingerprint independently loses the new finding through both cache owners. |
| 2026-11-06 | Compatibility inspection is deliberately advisory and separate from runtime loading. The scan remains local and existing policy/triage/exclusions remain unchanged. | Shipped280 rules: complete inspection,87 unsupported fields and one missing-regex rule. Pinned Betterleaks474: complete inspection,882 unsupported fields,123 unsupported filter functions,17 parse errors, one unknown variable, one compile warning and one missing-regex rule. These are unsupported-semantics observations, not new runtime defects or full-engine qualification. No network/provider action ran. The broader upstream refresh is a separate follow-up requested by the operator, outside this wave. |
| 2026-11-06 | Readback: repair actual same-ID override, use the pinned Betterleaks prefixed-only Sourcegraph detector and add opt-in bounded compatibility qualification. Root owns source/tests; coordinator owns scoped docs and independent review. | Canonical Implement opened the fully readied wave after22o92 was delivered and paused. Runtime loading must not newly reject existing inert unsupported metadata; qualification reports it. Synthetic consumer controls must reject old bare-hex detection and lost positives, preserve ordering/disable/policy behavior, redaction and rules-change full scans. No live credentials/network validation or project-exclusion edits. |
| 2026-11-05 | Evaluation only. Downloaded official immutable rule snapshots; parsed TOML, checked local regex/filter compatibility and executed actual raw-scanner/loader controls in temporary roots. Framework rules/source unchanged. | Current 280/new Betterleaks 474/Gitleaks 222 rules; 17 newer filters fail parsing; same-ID override returns OLD instead of NEW. Current/candidate Sourcegraph hit counts: Git hash1/0, modern1/1, local1/1, instance1/1, malformed0/0. Temporary data /private/tmp/wf-rules-review is reproducible from the pinned sources, not sole approval authority. |
| 2026-11-05 | Recorded the operator's prefixed-only choice in R2 and froze its exact positive/negative matrix in AC-2. Ready for focused readiness verification after publication; no source or rule edit. | Earlier initial review was conditional on this choice. Its existing actual consumer controls demonstrate both prefixed detection and legacy coverage loss; they remain baseline observations, not candidate implementation qualification. |
| 2026-11-05 | Focused readiness review passed on review-policy-7548f109ea0a8d6cfaac; six required lane approvals and Council recorded. No implementation or source edit. | Code/architecture and QA separately executed the isolated candidate format matrix; QA old-rule negatives failed as expected. Actual choice resolves the initial condition. Wave Review Checkpoints and events.jsonl retain verdicts, decisive observations and qualification limits. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
