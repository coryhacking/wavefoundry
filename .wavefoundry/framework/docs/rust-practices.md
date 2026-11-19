# Rust practices baseline

Owner: Engineering
Status: active
Last verified: 2026-11-18

This baseline is a menu, not a policy. A project's own record of its Rust decisions, `docs/contributing/rust-best-practices.md`, governs that project; where the record is silent, the project's existing configuration and dominant patterns govern, and this baseline only informs proposals. An agent may propose an entry to the operator, but an agent never enables a lint, adds a tool, or creates or edits a configuration file for a practice without the operator's direction through an admitted change. Lints stay opt-in, guidance that holds in every language stays in the all-stacks builder and reviewer text, and nothing here adds a sensor, gate, approval or review lane.

Read the index, then only the entry you need. Each entry gives the practice, where it applies, a default stance, the exact setting as text, a check that fails when the practice is not followed, its cost and its sources. The stance is `adopt` when a named public source recommends the practice, no named source disagrees and it holds wherever the entry applies; `situational` when sources disagree or it holds only in some contexts; otherwise `propose`. A stance is a starting point for the project's decision, not a decision.

Sources were consulted on 2026-11-18, and the sources table says for each whether its text was read or it is only linked; every lint was checked against Rust 1.100.0 and Clippy 0.1.100. A later change in a source is a reason for a scoped decision in a project, not an automatic change to this baseline or to any project's record. The links are for people; nothing here requires fetching a source at work time. An agent drafting a project's record re-checks each lint it names on that project's pinned toolchain.

## Index

| Practice | Stance |
| --- | --- |
| [Default lints and formatting pass in the gate](#default-lints-and-formatting-pass-in-the-gate) | adopt |
| [Lint exceptions state a reason](#lint-exceptions-state-a-reason) | adopt |
| [Lint groups or individually named lints](#lint-groups-or-individually-named-lints) | situational |
| [Disallowed types and methods carry a reason](#disallowed-types-and-methods-carry-a-reason) | propose |
| [Panics report bugs and errors report expected failures](#panics-report-bugs-and-errors-report-expected-failures) | adopt |
| [Intentional panics carry a message](#intentional-panics-carry-a-message) | adopt |
| [Unwrap, todo and unimplemented are denied outside tests](#unwrap-todo-and-unimplemented-are-denied-outside-tests) | propose |
| [Panic, unreachable and expect are denied outside tests](#panic-unreachable-and-expect-are-denied-outside-tests) | situational |
| [Catching a panic and continuing](#catching-a-panic-and-continuing) | situational |
| [No recovery of data from a poisoned lock](#no-recovery-of-data-from-a-poisoned-lock) | adopt |
| [Error type shape](#error-type-shape) | situational |
| [Libraries return their own error types](#libraries-return-their-own-error-types) | adopt |
| [Errors keep their cause](#errors-keep-their-cause) | adopt |
| [Indexing that can panic on untrusted input](#indexing-that-can-panic-on-untrusted-input) | propose |
| [Every unsafe block states why it is sound](#every-unsafe-block-states-why-it-is-sound) | adopt |
| [Crates that need no unsafe code forbid it](#crates-that-need-no-unsafe-code-forbid-it) | propose |
| [Unsafe marks only a risk of undefined behaviour](#unsafe-marks-only-a-risk-of-undefined-behaviour) | adopt |
| [Unsafe code runs under Miri](#unsafe-code-runs-under-miri) | situational |
| [FFI crates only translate](#ffi-crates-only-translate) | adopt |
| [Results a caller must use are marked must_use](#results-a-caller-must-use-are-marked-must_use) | adopt |
| [Public enums and structs with public fields are non_exhaustive](#public-enums-and-structs-with-public-fields-are-non_exhaustive) | adopt |
| [Newtypes guard their invariants](#newtypes-guard-their-invariants) | adopt |
| [Builders validate when they build](#builders-validate-when-they-build) | propose |
| [No smart pointers in public signatures](#no-smart-pointers-in-public-signatures) | propose |
| [Public types implement Debug and redact secrets](#public-types-implement-debug-and-redact-secrets) | propose |
| [Enums instead of unclear bool parameters](#enums-instead-of-unclear-bool-parameters) | adopt |
| [No glob imports](#no-glob-imports) | adopt |
| [One public path per item](#one-public-path-per-item) | situational |
| [Errors, Panics and Safety sections in API docs](#errors-panics-and-safety-sections-in-api-docs) | adopt |
| [Module docs and a short first sentence](#module-docs-and-a-short-first-sentence) | adopt |
| [Missing documentation as a project decision](#missing-documentation-as-a-project-decision) | propose |
| [Documentation describes the end state](#documentation-describes-the-end-state) | adopt |
| [Diagnostics use structured logging, not printing](#diagnostics-use-structured-logging-not-printing) | adopt |
| [Cancellation guards live as long as the work](#cancellation-guards-live-as-long-as-the-work) | propose |
| [One module owns process spawning](#one-module-owns-process-spawning) | propose |
| [Lint levels live in manifest tables inherited from the workspace](#lint-levels-live-in-manifest-tables-inherited-from-the-workspace) | propose |
| [Cargo manifest lints are set by name](#cargo-manifest-lints-are-set-by-name) | propose |
| [The toolchain is pinned per repository](#the-toolchain-is-pinned-per-repository) | propose |
| [Libraries state a minimum Rust version](#libraries-state-a-minimum-rust-version) | adopt |
| [Features are additive and test utilities are feature gated](#features-are-additive-and-test-utilities-are-feature-gated) | adopt |
| [Stable language features only](#stable-language-features-only) | situational |
| [Dependencies are checked against the advisory database](#dependencies-are-checked-against-the-advisory-database) | adopt |
| [Dependency and source policy](#dependency-and-source-policy) | propose |
| [Unused dependencies are detected](#unused-dependencies-are-detected) | adopt |
| [One task-runner entry point is the whole gate](#one-task-runner-entry-point-is-the-whole-gate) | propose |
| [Generated artifacts are checked for drift](#generated-artifacts-are-checked-for-drift) | propose |
| [Crate layering is checked](#crate-layering-is-checked) | propose |
| [Files embedded at compile time have fixed line endings](#files-embedded-at-compile-time-have-fixed-line-endings) | propose |
| [Continuous-integration actions are pinned by commit](#continuous-integration-actions-are-pinned-by-commit) | propose |
| [Where tests of the public API live](#where-tests-of-the-public-api-live) | situational |
| [Tests do not restate the implementation](#tests-do-not-restate-the-implementation) | adopt |
| [Whether and how to use async](#whether-and-how-to-use-async) | situational |
| [Rust code solves Rust problems](#rust-code-solves-rust-problems) | adopt |
| [Copies added only to satisfy the borrow checker](#copies-added-only-to-satisfy-the-borrow-checker) | propose |

## Composing settings

The fenced settings are fragments. Several entries put keys in the same manifest lint table or the same `clippy.toml` list, such as `disallowed-methods`; a project that takes more than one merges them into one table or one list per file, never repeating a table header or a key. A member crate either inherits the workspace lint table or sets its own lint table, not both, and its own table replaces inheritance for every lint. Where an entry needs a level for one crate only, it shows an attribute at the crate root instead, which leaves inheritance in place. A crate-root attribute is not expected to lower a lint the workspace sets to `forbid`; a project confirms that on its toolchain before relying on it.

## Entries

### Default lints and formatting pass in the gate

**Practice:** The gate runs rustfmt and Clippy's default lint groups over every target and fails on any warning.

**Applies when:** any

**Stance:** adopt

**Setting:**

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
```

**Check:** An unformatted file, or a default Clippy lint warning in a checked target, makes the gate exit non-zero.

**Cost and caveats:** A toolchain update can add warnings, so the gate can fail without a code change; the pinned toolchain entry controls when that happens. Google lists rustfmt options of its own, some of which need a nightly rustfmt; a stable project can skip those.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-STATIC-VERIFICATION (rustfmt, compiler lints and Clippy in check-in gates); Google Rust Style Guide, "Use the appropriate formatting tool".

### Lint exceptions state a reason

**Practice:** A local lint override uses `#[expect]` with a `reason`, and `#[allow]` is kept for generated code and macros.

**Applies when:** any

**Stance:** adopt

**Setting:**

```toml
[workspace.lints.clippy]
allow_attributes_without_reason = "deny"
allow_attributes = "warn"
```

```rust
#[expect(clippy::indexing_slicing, reason = "the length is checked two lines above")]
```

**Check:** Deny `allow_attributes_without_reason` and omit the reason from an `#[allow]` or `#[expect]` on a function. Both trigger the lint on Clippy 1.100. A supplied reason can be irrelevant and still pass. The reviewer judges whether it justifies the exception. Denying `unfulfilled_lint_expectations` separately catches an expectation whose lint has stopped firing.

**Cost and caveats:** Existing `allow` attributes need a reason or a move to `expect` before the lint can be denied. A project with an older minimum Rust version checks that its toolchain accepts `#[expect]` and lint reasons.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-LINT-OVERRIDE-EXPECT; Clippy documentation, allow_attributes_without_reason and allow_attributes.

### Lint groups or individually named lints

**Practice:** The project decides whether to turn on Clippy's pedantic and cargo groups as groups, or to name each lint it wants individually.

**Applies when:** any

**Stance:** situational

**Setting:**

```toml
# Option A: groups, with individual lints overriding them
[workspace.lints.clippy]
pedantic = { level = "warn", priority = -1 }
cargo = { level = "warn", priority = -1 }
```

```text
Option B: no group above its default level; each wanted lint is named in the
lint table by the entry that recommends it.
```

**Check:** With option A, a new pedantic or cargo lint finding fails the gate run with warnings denied. With option B, a review finds no group raised above its default level in any lint table.

**Cost and caveats:** One position, Microsoft's, enables the cargo, complexity, correctness, pedantic, perf, style and suspicious groups at warn with a lower priority and names a set of restriction lints individually. The other position names individual lints only: Google prescribes no lint groups and names only two lints, and a project's existing policy may defer the groups until their baseline cost is known. Groups pick up new lints on every toolchain update, which can fail the gate without a code change; named lints change only when the project changes them. Neither source enables the restriction group as a group.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-STATIC-VERIFICATION; Google Rust Style Guide (no lint-group rule); Clippy documentation, lint groups.

### Disallowed types and methods carry a reason

**Practice:** Types and methods the project forbids are listed in the Clippy configuration, each with the reason and the replacement to use.

**Applies when:** any

**Stance:** propose

**Setting:**

```toml
# clippy.toml
disallowed-types = [
  { path = "std::collections::HashMap", reason = "iteration order must be stable here", replacement = "std::collections::BTreeMap" },
]
disallowed-methods = [
  { path = "std::env::set_var", reason = "the process environment is set once at start-up" },
]
```

```toml
[workspace.lints.clippy]
disallowed_types = "deny"
disallowed_methods = "deny"
```

**Check:** With the two lints denied, a new use of a listed type or method fails Clippy. The diagnostic includes the configured reason. On Clippy 1.100, an unresolved method path emits a configuration warning and the command can still succeed with `-D warnings`. Enabling `allow-invalid` on that entry suppresses the warning.

**Cost and caveats:** The two lints do nothing until the configuration lists paths. The examples show the shape only; each project chooses its own list. Each intended use needs an `#[expect]` with a reason.
  Touches: none

**Sources:** Clippy documentation, disallowed_types, disallowed_methods and the `disallowed-types` and `disallowed-methods` configuration keys.

### Panics report bugs and errors report expected failures

**Practice:** Unless the project's record states that it avoids panics entirely, a detected programming bug or violated invariant panics, and a failure the caller can expect and handle, such as malformed input, returns an error.

**Applies when:** any

**Stance:** adopt

**Setting:**

```text
Review question: does any error variant exist only for a caller's contract
violation, or can malformed external input reach a panic?
```

**Check:** A reviewer who finds an error variant that only a caller bug can produce, or a panic reachable from malformed external input, records a finding.

**Cost and caveats:** Google notes that some codebases avoid panics entirely and report broken invariants through `Result`; that is a project choice the record states, the exception named in the practice, and the entry on denying panic, unreachable and expect covers its lints. Microsoft adds that a panic means stop the program, not an exception to catch.
  Touches: none

**Sources:** Google Rust Style Guide, "Reporting errors"; Microsoft Pragmatic Rust Guidelines, M-PANIC-ON-BUG and M-PANIC-IS-STOP.

### Intentional panics carry a message

**Practice:** Every intentional panic, including `expect`, `panic!`, `unreachable!` and assertions, states the invariant that was violated.

**Applies when:** any

**Stance:** adopt

**Setting:**

```rust
let header = parts.next().expect("split always yields at least one part");
assert!(len <= MAX_LEN, "length {len} exceeds MAX_LEN after validation");
```

**Check:** A reviewer who finds an intentional panic with an empty or generic message, or a bare `unwrap` standing for an invariant, records a finding; the unwrap entry adds a mechanical check for `unwrap`.

**Cost and caveats:** Messages cost little; the effort is in stating the invariant precisely.
  Touches: none

**Sources:** Google Rust Style Guide, "Prefer expect over unwrap"; Microsoft Pragmatic Rust Guidelines, M-PANIC-MESSAGE.

### Unwrap, todo and unimplemented are denied outside tests

**Practice:** Production code contains no `unwrap`, `todo!` or `unimplemented!`; tests may unwrap.

**Applies when:** any

**Stance:** propose

**Setting:**

```toml
[workspace.lints.clippy]
unwrap_used = "deny"
todo = "deny"
unimplemented = "deny"
```

```toml
# clippy.toml
allow-unwrap-in-tests = true
```

**Check:** A new `unwrap()` in production code, or any `todo!` or `unimplemented!`, fails Clippy; the same `unwrap()` inside a `#[test]` function or `#[cfg(test)]` module passes.

**Cost and caveats:** The three are restriction lints, allowed by default. The test key covers test functions and `#[cfg(test)]` code as the Clippy documentation words it; a shared helper outside those still reports. No test key for `todo` or `unimplemented` was found among the configuration keys read for this baseline, so unless the configuration page shows one, tests may not use them either. The stance is `propose` because no named source recommends denying these lints; Google's preference for `expect` over `unwrap` supports it.
  Touches: none

**Sources:** Clippy documentation, unwrap_used, todo, unimplemented and `allow-unwrap-in-tests`; Google Rust Style Guide, "Prefer expect over unwrap".

### Panic, unreachable and expect are denied outside tests

**Practice:** The project decides whether production code may call `panic!`, `unreachable!` and `expect`, or must express every invariant without them.

**Applies when:** any

**Stance:** situational

**Setting:**

```toml
[workspace.lints.clippy]
panic = "deny"
unreachable = "deny"
expect_used = "deny"
```

```toml
# clippy.toml
allow-panic-in-tests = true
allow-expect-in-tests = true
```

**Check:** With the three lints denied, unsuppressed production uses of `panic!()`, `unreachable!()` and `expect` fail Clippy. A matching expectation suppresses the corresponding lint. Reviewers check whether the project permits the exception and whether its reason applies. With the two test keys enabled on Clippy 1.100, panic and expect pass in test functions and test modules. Unreachable still fails in both.

**Cost and caveats:** Google and Microsoft both say to panic on bugs and to use `expect` with a message, so denying these lints works against their advice; it fits a project that has chosen to report every broken invariant through `Result`. Unless the configuration page shows a test key for `unreachable`, a test that uses it carries an `#[expect]` with a reason.
  Touches: none

**Sources:** Clippy documentation, panic, unreachable, expect_used, `allow-panic-in-tests` and `allow-expect-in-tests`; Google Rust Style Guide, "Reporting errors"; Microsoft Pragmatic Rust Guidelines, M-PANIC-ON-BUG.

### Catching a panic and continuing

**Practice:** The project decides whether any code may catch a panic with `catch_unwind` and continue, and if so where and what must follow.

**Applies when:** application, library

**Stance:** situational

**Setting:**

```toml
# clippy.toml
disallowed-methods = [
  { path = "std::panic::catch_unwind", reason = "panics stop the program; see the project's record" },
]
```

**Check:** With the method listed and `disallowed_methods` denied, a bare call to `catch_unwind` fails Clippy. A matching lint expectation suppresses that diagnostic. Reviewers check that each exception is permitted and justified.

**Cost and caveats:** One position, Google's, prohibits `catch_unwind` in first-party code except as defence in depth at a critical entry point that is never relied on. The other position, Microsoft's, permits it as a last resort, for example per request in a server so other requests finish, provided a controlled restart follows; library code does not catch and continue. Catching a panic does not restore the invariants it broke. When the build profile uses the abort panic strategy, nothing can be caught.
  Touches: none

**Sources:** Google Rust Style Guide, "Don't call panic::catch_unwind"; Microsoft Pragmatic Rust Guidelines, M-PANIC-CONTINUATION.

### No recovery of data from a poisoned lock

**Practice:** Code never reads or repairs the data inside a poisoned lock; a poisoned lock stops the operation as a bug.

**Applies when:** any

**Stance:** adopt

**Setting:**

```toml
# clippy.toml
disallowed-methods = [
  { path = "std::sync::PoisonError::into_inner", reason = "a poisoned lock is a bug; do not resume" },
]
```

**Check:** With the method listed and `disallowed_methods` denied, a call to `std::sync::PoisonError::into_inner` triggers the lint. A matching expectation suppresses it even with an irrelevant reason. Reviewers check the argument for trusting the data and inspect other ways to access or reset poisoned state.

**Cost and caveats:** A project can list further paths in the same list after checking them on its toolchain. A project with a proved repair for one lock records that exception and its proof in its record. Microsoft names unwrapping a lock result as a valid panic, which agrees with this entry.
  Touches: none

**Sources:** Google Rust Style Guide, "Handling poison"; Microsoft Pragmatic Rust Guidelines, M-PANIC-IS-STOP.

### Error type shape

**Practice:** The project decides whether its error types are situation-specific structs with helper methods or enums whose variants callers match.

**Applies when:** library, application

**Stance:** situational

**Setting:**

```text
Review question: does a new public error type follow the shape the project's
record chose, and does it implement Display and Error?
```

**Check:** A reviewer who finds a public error type that does not follow the recorded shape, or lacks `Display`, records a finding.

**Cost and caveats:** One position, Microsoft's, makes each error a situation-specific struct holding a backtrace, an optional upstream cause and helper methods, with any inner kind enum kept private and exposed through `is_` methods. The other position is a public error enum whose variants callers match; no source reviewed here prescribes it, Google prescribes no shape, and if a project chooses it the `non_exhaustive` entry applies to that enum. A struct keeps the type open to change; an enum lets callers match exhaustively.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-ERRORS-CANONICAL-STRUCTS; Google Rust Style Guide, "Reporting errors".

### Libraries return their own error types

**Practice:** A library's public functions return the library's own error types, not a general-purpose application error type; an application may use one general error type.

**Applies when:** library

**Stance:** adopt

**Setting:**

```text
Review question: does a public function of the library return a
general-purpose error type, such as one from an application error crate,
instead of one of the library's own error types?
```

**Check:** A reviewer who finds a public library function whose error type is a general-purpose application error type records a finding.

**Cost and caveats:** The practice limits public signatures only; private code inside the library may still use a general error type. A Clippy `disallowed-types` entry for the general type would refuse every use in the crate, public or private, which is stricter than this practice, so it is not the setting here.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-APP-ERROR and M-ERRORS-CANONICAL-STRUCTS.

### Errors keep their cause

**Practice:** Converting an error keeps the original as its cause, using `From` where a canonical conversion exists, and a discarded `Result` is visible.

**Applies when:** any

**Stance:** adopt

**Setting:**

```toml
[workspace.lints.clippy]
map_err_ignore = "warn"
unused_result_ok = "warn"
```

**Check:** Probe a `Result<(), String>` with `r.map_err(|_| 1)` and a bare `r.ok();` statement. Each raises the corresponding lint. Binding the result of the latter to the wildcard pattern passes that lint. Review conversions for loss of the underlying cause.

**Cost and caveats:** Both are restriction lints, allowed by default. Wrapping a cause can expose internal detail in a message; the debug entry covers redaction.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-FROM-ERROR and M-STATIC-VERIFICATION (map_err_ignore and unused_result_ok).

### Indexing that can panic on untrusted input

**Practice:** Code that indexes or slices with values derived from untrusted input uses checked access such as `get`, not indexing that can panic.

**Applies when:** untrusted input

**Stance:** propose

**Setting:**

```rust
// at the crate root (lib.rs or main.rs) of the crate that parses untrusted input
#![deny(clippy::indexing_slicing)]
```

```toml
# clippy.toml
allow-indexing-slicing-in-tests = true
```

**Check:** A new index or slice expression that Clippy cannot prove in bounds fails Clippy in that crate; with the test key set, the same expression in test functions and `#[cfg(test)]` code passes.

**Cost and caveats:** A restriction lint, allowed by default, and noisy across a whole workspace, so this entry scopes it to the crates that handle untrusted input. The crate-root attribute keeps that crate inheriting the workspace lint table. A rule stated in prose without the lint has nothing that fails.
  Touches: none

**Sources:** Clippy documentation, indexing_slicing and `allow-indexing-slicing-in-tests`.

### Every unsafe block states why it is sound

**Practice:** Unsafe code is used only for a stated reason that safe code cannot meet, such as a call into another language, a platform call, a new abstraction or a performance need shown by measurement, is wrapped in a safe abstraction, and each unsafe block or impl carries a `SAFETY:` comment explaining why it is correct.

**Applies when:** any

**Stance:** adopt

**Setting:**

```toml
[workspace.lints.clippy]
undocumented_unsafe_blocks = "deny"
unnecessary_safety_comment = "warn"
missing_safety_doc = "deny"

[workspace.lints.rust]
unsafe_op_in_unsafe_fn = "deny"
```

**Check:** An unsafe block or impl without a `SAFETY:` comment, an unsafe operation inside an `unsafe fn` without its own `unsafe` block, or a public `unsafe fn` without a `# Safety` section fails the build or Clippy.

**Cost and caveats:** The lints check that a comment exists, not that it is right; review checks the reasoning (initialization, validity, alignment, bounds, lifetimes, aliasing, concurrency and unwinding as they apply). `unsafe_op_in_unsafe_fn` warns by default from edition 2024 and is allowed on earlier editions.
  Touches: none

**Sources:** Google Rust Style Guide, "Unsafe code"; Microsoft Pragmatic Rust Guidelines, M-UNSAFE, M-UNSOUND and M-STATIC-VERIFICATION.

### Crates that need no unsafe code forbid it

**Practice:** Each crate that contains no unsafe code forbids it, so unsafe code stays in the few crates that need it.

**Applies when:** any

**Stance:** propose

**Setting:**

```rust
// at the crate root (lib.rs or main.rs) of each crate that needs no unsafe code
#![forbid(unsafe_code)]
```

**Check:** A new `unsafe` block, `no_mangle` or `export_name` attribute in such a crate fails to compile. That a local `allow` cannot lower the `forbid` level is the reason to use `forbid` over `deny`; the project confirms it once on its pinned toolchain.

**Cost and caveats:** The level is per crate, so the crates that need unsafe code leave the attribute out. The crate-root attribute keeps each crate inheriting the workspace lint table; a member that set its own manifest lint table for this lint instead would replace inheritance for every lint.
  Touches: none

**Sources:** Google Rust Style Guide, "Unsafe code" (encapsulate unsafe code, ideally in a separate crate); rustc lint listing, unsafe_code.

### Unsafe marks only a risk of undefined behaviour

**Practice:** A function or trait is marked `unsafe` only when misuse can cause undefined behaviour, not because it is dangerous in some other way.

**Applies when:** library

**Stance:** adopt

**Setting:**

```text
Review question: can misuse of each new unsafe function or trait cause
undefined behaviour, and does its # Safety section say how?
```

**Check:** A reviewer who finds an `unsafe` function or trait whose misuse cannot cause undefined behaviour records a finding.

**Cost and caveats:** Dangerous operations that are memory safe, such as deleting files, are expressed through naming and documentation instead.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-UNSAFE-IMPLIES-UB.

### Unsafe code runs under Miri

**Practice:** Tests that exercise unsafe code also run under Miri, the undefined-behaviour detector.

**Applies when:** any

**Stance:** situational

**Setting:**

```sh
rustup +nightly component add miri
cargo +nightly miri test
```

**Check:** A test run under Miri fails when Miri detects undefined behaviour in the code it runs.

**Cost and caveats:** The setting runs Miri on a nightly toolchain, and interpreting the program makes a run slower than a normal test run. How far Miri can run code that calls foreign functions was not checked for this baseline, so the entry is `situational`: it fits pure-Rust unsafe code, and a project with FFI code checks Miri's own documentation first. Microsoft requires that unsafe code passes Miri.
  Touches: ffi
  Platforms: The command is the same on Windows, macOS, Linux and WSL2. Whether Miri's support, including for foreign calls, differs by host was not checked. Not run on any platform for this baseline.

**Sources:** Microsoft Pragmatic Rust Guidelines, M-UNSAFE; Miri.

### FFI crates only translate

**Practice:** Business logic lives in core crates; FFI crates only translate, import crates are named `-sys` and export crates `-ffi`, and libraries share only portable `#[repr(C)]` data across a DLL boundary.

**Applies when:** FFI

**Stance:** adopt

**Setting:**

```sh
cargo test -p <core-crate>
```

```text
Review question: does any FFI crate contain logic beyond conversion, or share
statics, thread locals or TypeId-based state across the boundary?
```

**Check:** A reviewer who finds logic beyond conversion, or shared state, in an FFI crate records a finding. The test run of the core crate in the setting shows that the logic tested there passes in the core crate; it cannot see logic left in the FFI crate, so it supports the review and does not replace it.

**Cost and caveats:** The translation layer adds a crate and a conversion step. Microsoft prefers established interop libraries and documented generated bindings.
  Touches: ffi, linking
  Platforms: Linking differs: Windows links import libraries and DLLs (with different conventions on the MSVC and GNU targets), macOS links dynamic libraries and frameworks, and Linux links shared objects; WSL2 builds and links Linux binaries. The translate-only rule is the same on all four. Verified by reading only; not built on any platform.

**Sources:** Microsoft Pragmatic Rust Guidelines, M-FFI-TRANSLATES, M-FFI-NAMING, M-ISOLATE-DLL-STATE and M-UNSAFE.

### Results a caller must use are marked must_use

**Practice:** A function whose return value the caller cannot ignore and still use the function correctly, or whose return reports an error or critical information, is marked `#[must_use]` unless its return type is already `#[must_use]`, and error types and lazily evaluated values are marked too.

**Applies when:** any

**Stance:** adopt

**Setting:**

```toml
[workspace.lints.rust]
unused_must_use = "deny"

[workspace.lints.clippy]
must_use_candidate = "warn"
```

**Check:** Deny `unused_must_use` and call a marked function as a bare statement, such as `guard();`. That call fails. Binding the result to the wildcard pattern or calling `drop(guard());` compiles. The separate `must_use_candidate` lint suggests public functions to review.

**Cost and caveats:** `must_use_candidate` is a pedantic lint with a broader rule than the practice, so its findings are proposals, each settled by review. Google is the only guide that states the practice; that Microsoft's guidelines do not disagree was established from their titles only.
  Touches: none

**Sources:** Google Rust Style Guide, "#[must_use] on functions" and "#[must_use] on types"; rustc lint listing, unused_must_use; Clippy documentation, must_use_candidate.

### Public enums and structs with public fields are non_exhaustive

**Practice:** A public enum, and a public struct with public fields, that is part of a public API used by other teams is marked `#[non_exhaustive]`, except an enum over a fixed set of values or with two states, and a struct meant to be built with functional record update syntax.

**Applies when:** library

**Stance:** adopt

**Setting:**

```toml
[workspace.lints.clippy]
exhaustive_enums = "warn"
exhaustive_structs = "warn"
```

**Check:** An exported enum or a struct with all fields public raises the corresponding lint when it lacks `#[non_exhaustive]`. A struct with a private field passes `exhaustive_structs`. Use an `#[expect]` with a reason where an intended exception actually triggers the lint.

**Cost and caveats:** The lints can also report types with no external consumers. Reviewers decide which of those findings merit an exception. Callers must add a wildcard arm and cannot build the struct with a literal, which can be awkward inside the defining workspace. Google also asks callers to list every variant when matching; the rustc lint that checks this is nightly-only, so it is not part of this setting. Google is the only guide that states the practice; that Microsoft's guidelines do not disagree was established from their titles only.
  Touches: none

**Sources:** Google Rust Style Guide, "Apply #[non_exhaustive] to publicly-exposed enums" and "Apply #[non_exhaustive] to public structs with public fields"; Clippy documentation, exhaustive_enums and exhaustive_structs.

### Newtypes guard their invariants

**Practice:** Values that are easy to mix up or that carry an invariant get their own type, and a newtype that does not accept every value of its inner type has a fallible constructor and no infallible conversion from the weaker type.

**Applies when:** any

**Stance:** adopt

**Setting:**

```text
Review question: can a new newtype be built from an invalid value through
From, a public field or an unchecked constructor?
```

**Check:** A unit test that builds the type from an invalid value expects an error; the test fails if a conversion accepts the value. A reviewer who finds an infallible `From` from the weaker type records a finding.

**Cost and caveats:** Each newtype adds conversions at boundaries. Microsoft permits a panicking constructor in addition to the fallible one.
  Touches: none

**Sources:** Google Rust Style Guide, "Newtypes versus type aliases"; Microsoft Pragmatic Rust Guidelines, M-STRONG-TYPES and M-STRONG-TYPES-GUARD.

### Builders validate when they build

**Practice:** A type with many optional settings is constructed through a builder that takes required values up front and validates in `build`.

**Applies when:** library

**Stance:** propose

**Setting:**

```text
Review question: does a type with four or more construction permutations offer
a builder, and does build() return an error for an invalid combination?
```

**Check:** A unit test that builds an invalid combination expects an error from `build`; it fails if the builder accepts it.

**Cost and caveats:** A builder is more code than a constructor. Google has a rule that options structs implement `Default`, whose text was not read for this baseline; until it is, the stance stays `propose`.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-INIT-BUILDER.

### No smart pointers in public signatures

**Practice:** Public APIs do not expose `Rc`, `Arc`, `Box` or `RefCell` unless the wrapper is fundamental to the API or justified by measurement.

**Applies when:** library

**Stance:** propose

**Setting:**

```text
Review question: does a new public signature expose a smart pointer or
interior-mutability wrapper, and is the reason recorded?
```

**Check:** A reviewer who finds a new public signature exposing such a wrapper without a recorded reason records a finding.

**Cost and caveats:** Hiding a shared pointer can cost a clone or an extra type. Google has a rule titled "Avoid Rc and Arc", whose text was not read for this baseline; until it is, the stance stays `propose`, as for the builders entry.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-AVOID-WRAPPERS.

### Public types implement Debug and redact secrets

**Practice:** Every public type implements `Debug`; a type holding sensitive data has a hand-written implementation and a unit test showing the secret does not appear.

**Applies when:** library

**Stance:** propose

**Setting:**

```toml
[workspace.lints.rust]
missing_debug_implementations = "warn"
```

**Check:** A public type without `Debug` raises the warning; the redaction test fails when the formatted output contains the secret value.

**Cost and caveats:** The lint does not know which fields are secret; the redaction test does. Google has a rule titled "Use #[derive()] if possible", whose text was not read for this baseline; until it is, the stance stays `propose`, as for the builders entry.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-PUBLIC-DEBUG; rustc lint listing, missing_debug_implementations.

### Enums instead of unclear bool parameters

**Practice:** A function parameter whose purpose is not obvious from the call site is an enum, not a `bool`.

**Applies when:** any

**Stance:** adopt

**Setting:**

```text
Review question: does a call such as open(path, true) leave the meaning of the
bool unclear?
```

**Check:** A reviewer who finds a new public function taking a `bool` whose meaning is unclear at the call site records a finding.

**Cost and caveats:** One small type per parameter. Google is the only guide that states the practice; that Microsoft's guidelines do not disagree was established from their titles only.
  Touches: none

**Sources:** Google Rust Style Guide, "Prefer enum over bool in APIs".

### No glob imports

**Practice:** Code does not import with `use path::*`, except where Google's rule permits it: `use super::*` in inline modules, an enum's variants within code about that enum, private namespace merges for C++ interop and glob re-exports of submodules in non-leaf modules, which the one-public-path entry covers.

**Applies when:** any

**Stance:** adopt

**Setting:**

```toml
[workspace.lints.clippy]
wildcard_imports = "warn"
```

**Check:** A new `use some_module::*` import of an ordinary module raises a Clippy warning that fails a gate run with warnings denied. The lint has default exemptions, which the reader confirms on the lint's page for the pinned toolchain before relying on the check for any other case.

**Cost and caveats:** A pedantic lint. Where it reports a case this practice permits, an `#[expect]` with a reason records the exception. Third-party preludes are left to the reviewer.
  Touches: none

**Sources:** Google Rust Style Guide, "Don't use glob imports"; Clippy documentation, wildcard_imports.

### One public path per item

**Practice:** The project decides whether each public item is reachable through one path only, with no glob re-exports and no prelude module.

**Applies when:** library

**Stance:** situational

**Setting:**

```text
Review question: does a new pub use re-export an item already public
elsewhere, re-export with a glob, or define a prelude?
```

**Check:** A reviewer who finds a new second public path, a glob re-export or a prelude, against the project's recorded choice, records a finding.

**Cost and caveats:** Microsoft forbids glob re-exports from other modules, forbids preludes and wants items visible through one path, marking re-exports `#[doc(inline)]`. Google also avoids preludes but permits `pub use submodule::*` in a non-leaf module, which Microsoft's rule discourages; that difference is why this entry is `situational`.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-NO-GLOB-REEXPORTS, M-NO-PRELUDE, M-SINGLE-ITEM-PATH and M-DOC-INLINE; Google Rust Style Guide, "Don't use glob imports".

### Errors, Panics and Safety sections in API docs

**Practice:** Public API documentation has a summary sentence and, where they apply, `# Examples`, `# Errors`, `# Panics`, `# Safety` and `# Abort` sections, without parameter tables.

**Applies when:** library

**Stance:** adopt

**Setting:**

```toml
[workspace.lints.clippy]
missing_errors_doc = "warn"
missing_panics_doc = "warn"
missing_safety_doc = "deny"
```

**Check:** Check three public functions with the relevant section omitted. Returning a standard `Result` triggers `missing_errors_doc`, an explicit `panic!()` triggers `missing_panics_doc`, and an `unsafe fn` triggers `missing_safety_doc`. Review other panic paths separately. A panic reached through a private helper passed the documentation lint on Clippy 1.100.

**Cost and caveats:** The first two are pedantic lints. The lints check that a section exists, not that it is accurate; review compares the section with the code. A `# Panics` section cannot promise panic-free behaviour for code the project does not control.
  Touches: none

**Sources:** Google Rust Style Guide, "When and how to write documentation"; Microsoft Pragmatic Rust Guidelines, M-CANONICAL-DOCS; Rust API Guidelines, C-FAILURE; Clippy documentation, missing_errors_doc, missing_panics_doc and missing_safety_doc.

### Module docs and a short first sentence

**Practice:** Every public library module has `//!` documentation, and each item's first sentence fits on one line, about 15 words.

**Applies when:** library

**Stance:** adopt

**Setting:**

```sh
cargo doc --workspace --no-deps
```

```text
Review question: does each new public module open with a //! summary, and
does each new item's first sentence stay within about 15 words?
```

**Check:** In the generated documentation, a reviewer who finds a public module without a summary or an item whose first sentence runs past one line records a finding.

**Cost and caveats:** The Clippy lint for a long first paragraph is in the nursery group, so it is not part of this setting.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-MODULE-DOCS and M-FIRST-DOC-SENTENCE; Google Rust Style Guide, "When and how to write documentation".

### Missing documentation as a project decision

**Practice:** The project decides whether every public item must be documented and enforces that decision with the compiler's lint.

**Applies when:** library

**Stance:** propose

**Setting:**

```toml
[workspace.lints.rust]
missing_docs = "warn"
```

**Check:** With the lint on, a new undocumented public item raises a warning that fails a gate run with warnings denied.

**Cost and caveats:** Turning the lint on in an existing library usually needs a documentation pass first. Google mentions the lint as an aid, and a project may defer it until that pass is planned.
  Touches: none

**Sources:** Google Rust Style Guide, "When and how to write documentation"; rustc lint listing, missing_docs.

### Documentation describes the end state

**Practice:** Code documentation describes what the code does now, not the history of how its design was reached.

**Applies when:** any

**Stance:** adopt

**Setting:**

```text
Review question: does new documentation narrate earlier designs, rejected
options or the order of changes instead of the current behaviour?
```

**Check:** A reviewer who finds design-history narrative in code documentation records a finding.

**Cost and caveats:** Design history belongs in the project's change and decision records.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-NO-META-DESIGN-DOCUMENTATION.

### Diagnostics use structured logging, not printing

**Practice:** Diagnostic output from production code goes through structured logging, as events with named properties; printing is kept for a program's own user-facing output, and `dbg!` never ships.

**Applies when:** library, application

**Stance:** adopt

**Setting:**

```rust
// at the crate root (lib.rs) of each library crate
#![deny(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]
```

```toml
# clippy.toml
allow-print-in-tests = true
allow-dbg-in-tests = true
```

**Check:** A `println!`, `eprintln!` or `dbg!` in a library crate whose root carries the attribute fails Clippy. With both test keys enabled on Clippy 1.100, all three calls pass those lints in a test function and in a function inside a `#[cfg(test)]` module.

**Cost and caveats:** All three are restriction lints. A command-line application's user-facing output is printing by design, so the print lints belong in library crates and the binary crate states its own choice. The crate-root attribute keeps each library crate inheriting the workspace lint table. Microsoft's rule goes further, with message templates, event names and telemetry conventions; those are one way to structure events, suited to a logging stack that supports them, and they are not part of this practice. Microsoft is the only guide that states the practice; Google was found to have no logging rule.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-LOG-STRUCTURED and M-LOG-NOT-PRINT; Clippy documentation, print_stdout, print_stderr and dbg_macro.

### Cancellation guards live as long as the work

**Practice:** Hold the guard until the work should end. Mark its type `#[must_use]` so the compiler diagnoses a bare call that returns it.

**Applies when:** async, application, library

**Stance:** propose

**Setting:**

```text
Review question: on every exit path, including errors and early returns, is
each cancellation or resource guard held until the work ends?
```

**Check:** Exercise the operation while it owns the guard. Assert that work stays active until the intended cancellation point and that dropping the guard then cancels it. Move the drop earlier or remove cancellation from the destructor to make the corresponding assertion fail. The `unused_must_use` lint checks bare calls, while the behavior test checks the lifetime.

**Cost and caveats:** Cancellation ends the Rust side of the work; it does not promise to interrupt native or kernel work already in progress.
  Touches: none

**Sources:** Google Rust Style Guide, "#[must_use] on types"; rustc lint listing, unused_must_use.

### One module owns process spawning

**Practice:** One module spawns child processes, and it gives each a deadline, drains and caps its output, and terminates the whole process tree on timeout.

**Applies when:** application

**Stance:** propose

**Setting:**

```toml
# clippy.toml
disallowed-methods = [
  { path = "std::process::Command::new", reason = "spawn through the process module" },
]
```

**Check:** With the method listed and `disallowed_methods` denied, `Command::new` triggers the lint in both the owning module and a different module. A matching expectation suppresses it in either. A reviewer checks where the exception appears and why it belongs there. Test the owner with a child that exceeds the output cap and deadline. Use an independent timeout and check the captured size and surviving descendants.

**Cost and caveats:** The module needs platform-specific code for tree termination, and a process spawn from a dependency is not covered by the lint.
  Touches: processes
  Platforms: Windows has no POSIX process groups or signals; whole-tree termination there needs a job object that the child is assigned to at spawn. macOS and Linux can start the child in its own process group and signal the group. WSL2 behaves like Linux for Linux processes, but a Windows executable started from WSL2 runs as a Windows process outside that group. Verified by reading only; not run on any platform.

**Sources:** Clippy documentation, disallowed_methods; Rust standard library documentation, std::process.

### Lint levels live in manifest tables inherited from the workspace

**Practice:** Lint levels are set in the manifest's lint tables, defined once for the workspace and inherited by every member.

**Applies when:** any

**Stance:** propose

**Setting:**

```toml
# workspace Cargo.toml
[workspace.lints.rust]
unknown_lints = "deny"
```

```toml
# each member's Cargo.toml
[lints]
workspace = true
```

**Check:** A lint attribute with a misspelled name at a member's crate root fails that member's build while the member inherits the workspace table, where `unknown_lints` is denied; with the member's inheritance line removed, the same attribute only warns, because `unknown_lints` warns by default. The difference shows that the member inherits; the result is worth confirming once on the project's pinned toolchain. The Cargo lint for a member with no lint table is in the next entry.

**Cost and caveats:** Manifest lint tables are respected from Rust 1.74. A member inherits the workspace table or states its own lint table, not both, and its own table replaces inheritance for every lint; a crate-root attribute changes one lint's level and keeps inheritance. Microsoft gives its lint lists as manifest lint tables, but no named source recommends workspace inheritance as such, so the stance is `propose`.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-STATIC-VERIFICATION (lint levels in manifest lint tables); Cargo reference, the lints section and workspace lints.

### Cargo manifest lints are set by name

**Practice:** The workspace sets Cargo's own manifest lints by name, including the one that reports a member with no lint table while the workspace defines lints.

**Applies when:** any

**Stance:** propose

**Setting:**

```toml
[workspace.lints.cargo]
missing_lints_inheritance = "deny"
redundant_homepage = "warn"
blanket_hint_mostly_unused = "warn"
text_direction_codepoint_in_comment = "deny"
text_direction_codepoint_in_literal = "deny"
```

**Check:** The `missing_lints_inheritance` lint, which warns by default, reports a member manifest with no lint table while the workspace defines lints; a member that states its own lint table instead of inheriting is not what this lint reports. On Cargo 1.100 the missing table produced a warning and the build succeeded despite the workspace deny setting. To require inheritance, have the gate inspect the member manifests and fail when a required inheritance setting is missing.

**Cost and caveats:** The `[lints.cargo]` table is stable only from Rust 1.100, so a project with an older pinned toolchain cannot use it. Cargo also has lints for unused dependencies and unused workspace entries; their groups were not verified for this baseline, so they are not named here, and a project re-checks them on its toolchain before adopting them.
  Touches: none

**Sources:** Cargo reference, lints chapter.

### The toolchain is pinned per repository

**Practice:** The repository pins its Rust toolchain and components in a toolchain file, so every developer and the gate use the same compiler and Clippy.

**Applies when:** any

**Stance:** propose

**Setting:**

```toml
# rust-toolchain.toml
[toolchain]
channel = "1.100.0"
components = ["clippy", "rustfmt"]
```

**Check:** A gate step that compares the reported compiler version with the pinned channel fails when they differ. What rustup does when the pinned toolchain is not installed depends on the rustup version and its settings, and is confirmed on the project's machines.

**Cost and caveats:** Toolchain updates become explicit changes. If both a legacy `rust-toolchain` file and `rust-toolchain.toml` exist, the legacy file wins, so a repository with both is pinned by the legacy file.
  Touches: none

**Sources:** rustup book, the toolchain file.

### Libraries state a minimum Rust version

**Practice:** A library states its minimum supported Rust version when it is created and raises it conservatively, a few releases behind the newest compiler.

**Applies when:** library

**Stance:** adopt

**Setting:**

```toml
[package]
rust-version = "1.85"
```

```sh
cargo +1.85 check --workspace --all-targets
```

**Check:** The gate builds with the stated version; code that needs a newer compiler or standard library fails that build. Checking all targets also compiles development dependencies, so one of those that needs a newer compiler fails the step too, even when the library itself would pass.

**Cost and caveats:** The version shown is an example. Holding back the version delays newer language features; raising it is a minor release.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-MSRV; Cargo reference, the rust-version field.

### Features are additive and test utilities are feature gated

**Practice:** Every library feature only adds, any combination of features builds, no feature removes or changes a public item, and mocking or test-only helpers sit behind a feature such as `test-util`.

**Applies when:** library

**Stance:** adopt

**Setting:**

```sh
cargo hack check --workspace --feature-powerset
```

```toml
[features]
test-util = []
```

**Check:** A feature combination that does not build fails the powerset check; a test-only helper reachable without the feature is a review finding.

**Cost and caveats:** The powerset grows quickly with the number of features; `--each-feature` is a cheaper check. Off-by-default features need their own pass in the gate, or nothing builds them.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-FEATURES-ADDITIVE and M-TEST-UTIL; cargo-hack.

### Stable language features only

**Practice:** Code uses no unstable language or library features.

**Applies when:** any

**Stance:** situational

**Setting:**

```sh
cargo +stable check --workspace --all-targets
```

**Check:** A `#![feature(...)]` attribute fails to compile on the stable channel.

**Cost and caveats:** The one named source, Google's rule, carries its own exceptions: embedded work on Android, blanket approvals in Chrome and separate guidance for Fuchsia. A project that needs an unstable feature, for example for embedded or platform work, records that choice; the stance is `situational` because the source itself limits where the rule holds. Tools that need nightly, such as Miri or some unused-dependency checkers, are separate from the code and do not break this rule.
  Touches: none

**Sources:** Google Rust Style Guide, "No unstable features".

### Dependencies are checked against the advisory database

**Practice:** The gate checks every dependency against the RustSec advisory database.

**Applies when:** any

**Stance:** adopt

**Setting:**

```sh
cargo audit
```

```toml
# deny.toml, as an alternative with cargo-deny
[advisories]
yanked = "deny"
```

**Check:** A dependency with a security vulnerability reported to the RustSec advisory database fails the audit; with cargo-deny and `yanked` set to deny, a yanked crate version fails the check. How each tool treats other kinds of advisory is confirmed in its own documentation before the gate relies on it.

**Cost and caveats:** The advisory database is fetched over the network; an offline gate needs a local copy refreshed by a separate step. A newly reported vulnerability can fail the gate without a code change. A stated reason beside each ignored advisory keeps the ignores reviewable; no named source states that part, so it is a project choice.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-STATIC-VERIFICATION (cargo-audit); cargo-audit; cargo-deny.

### Dependency and source policy

**Practice:** A dependency policy file allows only listed licences and registries, denies wildcard versions and unknown Git sources, Git dependencies are pinned by commit, and each vendored patch names its upstream issue and when it will be removed.

**Applies when:** any

**Stance:** propose

**Setting:**

```toml
# deny.toml
[licenses]
allow = ["MIT", "Apache-2.0"]

[bans]
wildcards = "deny"

[sources]
unknown-registry = "deny"
unknown-git = "deny"
allow-git = []
```

```toml
# Cargo.toml
some-crate = { git = "https://example.invalid/some-crate", rev = "<full commit hash>" }
```

**Check:** A dependency with an unlisted licence, a `*` version or a source outside the allowed lists fails the cargo-deny check; a review or a manifest test finds a Git dependency without `rev`, and a `[patch]` entry without a removal note, as findings.

**Cost and caveats:** The licence list needs upkeep as dependencies change, and every allowed Git source is listed by URL.
  Touches: none

**Sources:** cargo-deny (licenses, bans and sources checks); Cargo reference, specifying dependencies from Git and overriding dependencies.

### Unused dependencies are detected

**Practice:** The gate reports dependencies that no code uses.

**Applies when:** any

**Stance:** adopt

**Setting:**

```sh
cargo machete
cargo +nightly udeps --workspace --all-targets
```

**Check:** A dependency declared in a manifest and never used is reported by the chosen tool; whether that tool exits non-zero on a report is confirmed for it before the gate step relies on the exit status.

**Cost and caveats:** cargo-udeps compiles the project and needs a nightly toolchain to run; cargo-machete runs on stable but searches the source text, so it can miss or misreport a dependency used only through a macro. A project chooses one and records it.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-STATIC-VERIFICATION (cargo-udeps); cargo-udeps; cargo-machete.

### One task-runner entry point is the whole gate

**Practice:** One task-runner command runs the whole gate, including formatting, lints, tests, passes for off-by-default features and drift checks, and continuous integration calls that same command.

**Applies when:** any

**Stance:** propose

**Setting:**

```sh
cargo xtask check
```

**Check:** A check that continuous integration runs but the task runner does not is a review finding; a failing step inside the task runner makes the command exit non-zero.

**Cost and caveats:** The task runner is code the project maintains. A task runner written in Rust runs the same way on every platform; a shell script does not.
  Touches: processes
  Platforms: The task runner spawns the tools it runs. A POSIX shell script does not run in a native Windows shell, while a Rust task runner builds and runs on Windows, macOS, Linux and WSL2. Executable names differ on Windows (`.exe`). Verified by reading only; not run on any platform.

**Sources:** Microsoft Pragmatic Rust Guidelines, M-STATIC-VERIFICATION (tools as part of check-in gates); Rust standard library documentation, std::process.

### Generated artifacts are checked for drift

**Practice:** Each checked-in generated file is regenerated in the gate and compared with the committed copy.

**Applies when:** any

**Stance:** propose

**Setting:**

```sh
cargo xtask codegen
git diff --exit-code
```

**Check:** A change to the generator or its input without the regenerated file fails the comparison.

**Cost and caveats:** Generation must be deterministic, with stable ordering and no timestamps, or the check fails on every run.
  Touches: line-endings
  Platforms: On Windows, Git may be configured to convert line endings on checkout, so a generator that writes LF can differ from a CRLF working copy; a rule in the attributes file can fix the line endings of the generated files. On macOS and Linux, conversion likewise depends on the Git configuration. In WSL2 the result depends on which Git made the checkout. Verified by reading only; not run on any platform.

**Sources:** Git documentation, gitattributes.

### Crate layering is checked

**Practice:** A table of allowed dependencies between workspace crates is checked mechanically, and the check fails closed when it cannot read a manifest.

**Applies when:** any

**Stance:** propose

**Setting:**

```sh
cargo metadata --format-version 1 --no-deps
```

```text
A gate step reads the metadata and fails on any workspace dependency edge the
layering table does not allow, and on any manifest it cannot parse.
```

**Check:** A new dependency from a lower crate to a higher one fails the step, and so does an unreadable manifest.

**Cost and caveats:** The table is project code to maintain. A check that skips a manifest it cannot read passes a broken layering silently.
  Touches: none

**Sources:** Cargo reference, cargo metadata.

### Files embedded at compile time have fixed line endings

**Practice:** Text files embedded with `include_str!` or `include_bytes!` have their line endings fixed in the Git attributes file, so the compiled bytes are the same on every checkout.

**Applies when:** any

**Stance:** propose

**Setting:**

```text
# .gitattributes: one line per embedded text type, never a pattern that matches binary files
*.sql text eol=lf
*.json text eol=lf
```

**Check:** A unit test asserts that each embedded text contains no carriage return; it fails on a checkout that converted the file.

**Cost and caveats:** Files already committed need a renormalization commit. The patterns name text file types only, so binary files embedded with `include_bytes!` are not converted; a project lists its own embedded text types.
  Touches: line-endings
  Platforms: Git for Windows commonly converts text files to CRLF on checkout, which changes embedded bytes; macOS and Linux do not convert by default. In WSL2 a checkout made by Windows Git under a Windows drive can carry CRLF, while one made by Linux Git does not. The attributes rule gives the same bytes on all four. Verified by reading only; not run on any platform.

**Sources:** Git documentation, gitattributes; Rust standard library documentation, include_str and include_bytes.

### Continuous-integration actions are pinned by commit

**Practice:** Every third-party or shared workflow action is referenced by a full commit hash, not a branch or tag, most of all in release workflows that hold signing secrets.

**Applies when:** any

**Stance:** propose

**Setting:**

```text
uses: owner/action@<full 40-character commit hash>
```

**Check:** A gate step that reads every workflow file fails on a `uses:` reference to an action or shared workflow in another repository that is not a full commit hash. Local actions referenced by a path in the same repository are not pinned by commit and are left out of the check.

**Cost and caveats:** Pinned actions need deliberate updates.
  Touches: none

**Sources:** GitHub Actions documentation.

### Where tests of the public API live

**Practice:** The project decides whether tests that touch only the public API live under `tests/` or in inline test modules.

**Applies when:** library, application

**Stance:** situational

**Setting:**

```text
Review question: does a new test that uses only the public API live where the
project's record says such tests live?
```

**Check:** A reviewer who finds a public-API test placed against the recorded choice records a finding.

**Cost and caveats:** One position, Microsoft's, puts tests that touch only the public API under `tests/` as integration tests and prefers them where either form works. The other position keeps them in inline test modules next to the code; Google states no placement rule and leaves the test framework to each codebase. Each file under `tests/` is a separate crate, which adds build time, while inline modules can reach private items.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-INTEGRATION-TESTS; Google Rust Style Guide, "Use the right per-codebase test framework".

### Tests do not restate the implementation

**Practice:** A unit test checks meaningful behaviour, not a restatement of a definition or of the code under test.

**Applies when:** any

**Stance:** adopt

**Setting:**

```text
Review question: would the test still pass if the behaviour it names were
broken?
```

**Check:** Changing the code under test so that the named behaviour breaks must fail the test; a test that still passes is a finding.

**Cost and caveats:** The check is a manual mutation of the code; mutation-testing tools can automate it at a cost in run time.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-TAUTOLOGICAL-TESTS.

### Whether and how to use async

**Practice:** The project decides whether it uses async code at all and, if it does, which runtime and which function forms.

**Applies when:** async

**Stance:** situational

**Setting:**

```text
Review question: does new async code follow the runtime and forms the
project's record chose, and does it avoid blocking calls inside async functions?
```

**Check:** A reviewer who finds async code against the recorded choice, or a blocking call inside an async function, records a finding.

**Cost and caveats:** One position, Microsoft's, uses async and prefers `async fn` over a function that returns `impl Future`, with guidance on stack size and yield points. The other position avoids async: Google bans async in Chromium, a rule that binds that codebase only and is listed under "Not included". Async adds a runtime dependency and makes cancellation and guard lifetimes part of every API.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-ASYNC-FN, M-ASYNC-STACK-SIZE and M-YIELD-POINTS; Google Rust Style Guide, "Don't use async / .await [chrome]".

### Rust code solves Rust problems

**Practice:** Code ported from another language is redesigned around Rust's ownership and types, not copied construct for construct.

**Applies when:** any

**Stance:** adopt

**Setting:**

```text
Review question: does ported code keep another language's class hierarchies,
null handling or exception patterns where Rust has its own form?
```

**Check:** A reviewer who finds a one-to-one port of another language's construct records a finding.

**Cost and caveats:** The all-stacks builder text already asks for redesign over literal ports; this entry adds the Rust source.
  Touches: none

**Sources:** Microsoft Pragmatic Rust Guidelines, M-RUST-SHAPED and M-DESIGN-FOR-AI.

### Copies added only to satisfy the borrow checker

**Practice:** A copy, a field check-out or a runtime-checked cell added only to pass the borrow checker carries a one-line reason, and Clippy's clone lints point at candidates.

**Applies when:** any

**Stance:** propose

**Setting:**

```toml
[workspace.lints.clippy]
implicit_clone = "warn"
large_types_passed_by_value = "warn"
```

**Check:** Use an owned `String` as the receiver of `to_owned()` to exercise `implicit_clone`. The same call on `&String` passed this lint on Clippy 1.100. For `large_types_passed_by_value`, pass a `Copy` struct containing `[u64; 100]` by value to a private function with an immutable parameter. Reviewers assess why each copy is needed.

**Cost and caveats:** Both are pedantic lints. Clippy's redundant-clone and needless-collect lints are in the nursery group, so they are not part of this setting.
  Touches: none

**Sources:** Clippy documentation, implicit_clone and large_types_passed_by_value.

## Lints named

Every lint named in a `Setting` field, checked against Rust 1.100.0 and Clippy 0.1.100. Clippy groups are shown as Clippy labels them; rustc lints belong to no Clippy group. Cargo lint groups are Cargo's own.

| Lint | Tool | Group | Default level | Checked against |
| --- | --- | --- | --- | --- |
| `allow_attributes` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `allow_attributes_without_reason` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `dbg_macro` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `disallowed_methods` | Clippy | style | warn | Rust 1.100.0, Clippy 0.1.100 |
| `disallowed_types` | Clippy | style | warn | Rust 1.100.0, Clippy 0.1.100 |
| `exhaustive_enums` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `exhaustive_structs` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `expect_used` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `implicit_clone` | Clippy | pedantic | allow | Rust 1.100.0, Clippy 0.1.100 |
| `indexing_slicing` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `large_types_passed_by_value` | Clippy | pedantic | allow | Rust 1.100.0, Clippy 0.1.100 |
| `map_err_ignore` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `missing_errors_doc` | Clippy | pedantic | allow | Rust 1.100.0, Clippy 0.1.100 |
| `missing_panics_doc` | Clippy | pedantic | allow | Rust 1.100.0, Clippy 0.1.100 |
| `missing_safety_doc` | Clippy | style | warn | Rust 1.100.0, Clippy 0.1.100 |
| `must_use_candidate` | Clippy | pedantic | allow | Rust 1.100.0, Clippy 0.1.100 |
| `panic` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `print_stderr` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `print_stdout` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `todo` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `undocumented_unsafe_blocks` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `unimplemented` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `unnecessary_safety_comment` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `unreachable` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `unused_result_ok` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `unwrap_used` | Clippy | restriction | allow | Rust 1.100.0, Clippy 0.1.100 |
| `wildcard_imports` | Clippy | pedantic | allow | Rust 1.100.0, Clippy 0.1.100 |
| `missing_debug_implementations` | rustc | none | allow | Rust 1.100.0 |
| `missing_docs` | rustc | none | allow | Rust 1.100.0 |
| `unknown_lints` | rustc | none | warn | Rust 1.100.0 |
| `unsafe_code` | rustc | none | allow | Rust 1.100.0 |
| `unsafe_op_in_unsafe_fn` | rustc | none | allow before edition 2024; warn from edition 2024 | Rust 1.100.0 |
| `unused_must_use` | rustc | none | warn | Rust 1.100.0 |
| `blanket_hint_mostly_unused` | Cargo | suspicious | warn | Rust 1.100.0 |
| `missing_lints_inheritance` | Cargo | suspicious | warn | Rust 1.100.0 |
| `redundant_homepage` | Cargo | style | warn | Rust 1.100.0 |
| `text_direction_codepoint_in_comment` | Cargo | correctness | deny | Rust 1.100.0 |
| `text_direction_codepoint_in_literal` | Cargo | correctness | deny | Rust 1.100.0 |

## Topic dispositions

| Topic area | Disposition |
| --- | --- |
| Lint policy and exception reasons | Default lints and formatting pass in the gate; Lint exceptions state a reason; Lint groups or individually named lints; Disallowed types and methods carry a reason |
| Panic-family lints by name with test exemptions | Unwrap, todo and unimplemented are denied outside tests; Panic, unreachable and expect are denied outside tests; Indexing that can panic on untrusted input |
| Panics, expect and assertion messages | Panics report bugs and errors report expected failures; Intentional panics carry a message; Catching a panic and continuing |
| Error types for libraries and applications | Error type shape; Libraries return their own error types; Errors keep their cause |
| Unsafe justification and FFI layout | Every unsafe block states why it is sound; Crates that need no unsafe code forbid it; Unsafe marks only a risk of undefined behaviour; Unsafe code runs under Miri; FFI crates only translate |
| API design | Results a caller must use are marked must_use; Public enums and structs with public fields are non_exhaustive; Newtypes guard their invariants; Builders validate when they build; No smart pointers in public signatures; Public types implement Debug and redact secrets; Enums instead of unclear bool parameters; No glob imports; One public path per item |
| Documentation sections and module docs | Errors, Panics and Safety sections in API docs; Module docs and a short first sentence; Missing documentation as a project decision; Documentation describes the end state |
| Logging in production code | Diagnostics use structured logging, not printing |
| Cancellation, guard lifetimes and lock poisoning | Cancellation guards live as long as the work; No recovery of data from a poisoned lock |
| Process spawning | One module owns process spawning |
| Workspace inheritance, manifest lints, toolchain and minimum version, additive features | Lint levels live in manifest tables inherited from the workspace; Cargo manifest lints are set by name; The toolchain is pinned per repository; Libraries state a minimum Rust version; Features are additive and test utilities are feature gated; Stable language features only |
| Dependency and source policy | Dependencies are checked against the advisory database; Dependency and source policy; Unused dependencies are detected |
| Task-runner entry point and drift checks | One task-runner entry point is the whole gate; Generated artifacts are checked for drift |
| Crate layering checks | Crate layering is checked |
| Line endings for embedded files | Files embedded at compile time have fixed line endings |
| Continuous-integration actions pinned by commit | Continuous-integration actions are pinned by commit |
| Test placement and tests that restate the implementation | Where tests of the public API live; Tests do not restate the implementation |
| Async | Whether and how to use async |
| Guidance aimed at coding agents | Rust code solves Rust problems; Documentation describes the end state; One public path per item. Left out as a separate entry: Microsoft's advice to design APIs for agent use repeats the documentation and strong-type entries. |
| Nursery and nightly-only lints | Left out: the lints for redundant clones, needless collects and long first doc paragraphs are in Clippy's nursery group, which Clippy marks as still in development, and the rustc lint for omitted patterns on non-exhaustive types needs a nightly toolchain; none of them is recommended here as a setting. |
| Cargo lints with unverified groups | Left out: Cargo's lints for unused dependencies and unused workspace entries, whose groups were not verified against the stated toolchain. |
| Company-specific rules | Not included; see the next section. |

## Not included

These rules bind one company's codebase and are not entries:

- Google's ban on async and on standard threads in Chromium: it serves that browser's own task and threading model.
- Google's requirement that Chrome, Android and Fuchsia build with the abort panic strategy: a platform build decision for those products, not a general practice.
- Codebase-specific test frameworks such as Chrome's and Fuchsia's: a project uses its own test harness.
- Required allocators and internal build-system rules of any one company: they depend on that company's toolchain.
- Google's rustfmt options that need a nightly rustfmt: a stable project cannot apply them.

## Outline of a project record

A project's Rust policy lives in `docs/contributing/rust-best-practices.md`, owned by the project. An agent may draft it from this baseline as an ordinary planned change, leaving every row's decision to the operator. A record has these parts:

1. Metadata lines: `Owner:`, `Status:` and `Last verified:`.
2. A preface stating that passing the project's checks does not establish full compliance with any guide, or memory safety.
3. A table with one row per practice the project considered: the practice, the decision (adopt, adapt, defer or decline) with the project's own rationale, and how it is verified.
4. The mechanical checks the project runs, and their known limits.
5. A review checklist for each reviewer lane, recorded in the project's existing review record, with no new approval workflow.
6. Links to the project's canonical contracts that the policy must not contradict.

A project that already has this document keeps it unchanged: nothing in the framework rewrites, reorders or re-dates it. Bringing an existing record in line with this baseline is that project's own change.

## Sources and attribution

All sources were consulted on 2026-11-18. This baseline paraphrases them; it copies no text beyond short identifiers, titles and lint names. The last column says what was read: "linked only" means the source's text was not read for this baseline.

| Source | Link | Licence | Date | Text read |
| --- | --- | --- | --- | --- |
| Google Rust Style Guide | https://google.github.io/styleguide/rustguide.html | CC BY 3.0 | 2026-11-18 | Read: the rules cited by title; three rules named in entries were seen by title only, as those entries say |
| Microsoft Pragmatic Rust Guidelines | https://microsoft.github.io/rust-guidelines/ | MIT | 2026-11-18 | Read: the guidelines cited by identifier |
| Rust API Guidelines | https://rust-lang.github.io/api-guidelines/ | Apache-2.0 or MIT | 2026-11-18 | Licence read; C-FAILURE seen only as cited by Microsoft's guidelines, its text not read |
| Clippy documentation | https://rust-lang.github.io/rust-clippy/stable/index.html | Apache-2.0 or MIT | 2026-11-18 | Read: the stable lint list entry for each named lint, and the configuration keys |
| rustc lint listing | https://doc.rust-lang.org/rustc/lints/listing/index.html | Not checked | 2026-11-18 | Read: the allowed-by-default and warn-by-default listings |
| Cargo reference | https://doc.rust-lang.org/cargo/reference/ | Not checked | 2026-11-18 | Read: the lints section, workspace lints, the lints chapter, the rust-version field and the unstable-features page, the source for the release that stabilized the `[lints.cargo]` table; other pages linked only |
| rustup book | https://rust-lang.github.io/rustup/overrides.html | Not checked | 2026-11-18 | Read: the toolchain file |
| Rust standard library documentation | https://doc.rust-lang.org/std/ | Not checked | 2026-11-18 | Linked only |
| Miri | https://github.com/rust-lang/miri | Not checked | 2026-11-18 | Read: its own statement of purpose only |
| cargo-deny | https://embarkstudios.github.io/cargo-deny/ | Not checked | 2026-11-18 | Read: the advisories, licenses, bans and sources configuration pages |
| cargo-audit | https://github.com/rustsec/rustsec/tree/main/cargo-audit | Not checked | 2026-11-18 | Read: its own statement of purpose only |
| cargo-hack | https://github.com/taiki-e/cargo-hack | Not checked | 2026-11-18 | Read: its own statement of purpose only |
| cargo-udeps | https://github.com/est31/cargo-udeps | Not checked | 2026-11-18 | Read: its own statement of purpose and toolchain needs only |
| cargo-machete | https://github.com/bnjbvr/cargo-machete | Not checked | 2026-11-18 | Read: its own statement of purpose only |
| Git documentation | https://git-scm.com/docs/gitattributes | Not checked | 2026-11-18 | Linked only |
| GitHub Actions documentation | https://docs.github.com/en/actions | Not checked | 2026-11-18 | Linked only |

For a source whose licence was not checked, or whose text is linked only, the baseline states facts in its own words and quotes nothing.

Attribution:

- Google Rust Style Guide, by Google, https://google.github.io/styleguide/rustguide.html, licensed under the Creative Commons Attribution 3.0 Unported licence (https://creativecommons.org/licenses/by/3.0/). The guidance used here is paraphrased and changed from the original.
- Microsoft Pragmatic Rust Guidelines, https://microsoft.github.io/rust-guidelines/. Copyright (c) Microsoft Corporation. Licensed under the MIT license (https://github.com/microsoft/rust-guidelines/blob/main/LICENSE.md). The guidance used here is paraphrased; guideline identifiers are cited as `M-` names.
- Rust API Guidelines, by the Rust Project Contributors, https://rust-lang.github.io/api-guidelines/, licensed under the Apache License 2.0 or the MIT license, at your option. Cited by guideline identifier only.
- Clippy documentation, Copyright (c) The Rust Project Contributors, https://github.com/rust-lang/rust-clippy, licensed under the Apache License 2.0 or the MIT license, at your option. Lint names, groups and levels are cited; descriptions are paraphrased.
