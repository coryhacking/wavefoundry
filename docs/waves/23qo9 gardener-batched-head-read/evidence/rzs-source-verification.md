# Rust practices: source verification notes

Owner: Engineering
Status: active
Last verified: 2026-11-18

- Date of verification: 2026-11-18.
- Rust stable: **1.100.0**, released 2026-11-12. Established from the official stable channel manifest `https://static.rust-lang.org/dist/channel-rust-stable.toml` (`date = "2026-11-12"`, `[pkg.rustc] version = "1.100.0 (0ef1bc386 2026-11-09)"`) and the first entry of `https://raw.githubusercontent.com/rust-lang/rust/stable/RELEASES.md` ("Version 1.100.0 (2026-11-12)").
- Clippy: **0.1.100**, the version shipped with Rust 1.100.0 (same manifest, `[pkg.clippy-preview] version = "0.1.100"`). Cargo in that release is 0.101.0.
- Lint data was read from the **stable** Clippy lint list `https://rust-lang.github.io/rust-clippy/stable/index.html` (downloaded and parsed per lint article: group label, level label, "Added in" label, first paragraph of "What it does"). The highest "Added in" value on that page is 1.99.0, consistent with a page built for the 1.100 release. Each lint's "View Source" link on that page points to the master branch declaration.
- rustc lint data was read from `https://doc.rust-lang.org/rustc/lints/listing/allowed-by-default.html` and `.../warn-by-default.html` (stable documentation).
- Clippy configuration keys were read from the Clippy book source `https://raw.githubusercontent.com/rust-lang/rust-clippy/master/book/src/lint_configuration.md` (master branch; the stable lint page shows the same keys under each lint's "Configuration" block).

## Part 1. Lints

All Clippy rows below: source page `https://rust-lang.github.io/rust-clippy/stable/index.html#<lint>`; declaration file given in the last column.

| Lint | Tool | Group | Default level | Since | Description (from "What it does") | Declaration | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `unwrap_used` | Clippy | restriction | allow | 1.45.0 | Checks for `.unwrap()` or `.unwrap_err()` calls on `Result`s and `.unwrap()` call on `Option`s. | `clippy_lints/src/methods/mod.rs` | VERIFIED |
| `expect_used` | Clippy | restriction | allow | 1.45.0 | Checks for `.expect()` or `.expect_err()` calls on `Result`s and `.expect()` call on `Option`s. | `clippy_lints/src/methods/mod.rs` | VERIFIED |
| `panic` | Clippy | restriction | allow | 1.40.0 | Checks for usage of `panic!`. | `clippy_lints/src/panic_unimplemented.rs` | VERIFIED |
| `todo` | Clippy | restriction | allow | 1.40.0 | Checks for usage of `todo!`. | `clippy_lints/src/panic_unimplemented.rs` | VERIFIED |
| `unimplemented` | Clippy | restriction | allow | pre 1.29.0 | Checks for usage of `unimplemented!`. | `clippy_lints/src/panic_unimplemented.rs` | VERIFIED |
| `unreachable` | Clippy | restriction | allow | 1.40.0 | Checks for usage of `unreachable!`. | `clippy_lints/src/panic_unimplemented.rs` | VERIFIED |
| `dbg_macro` | Clippy | restriction | allow | 1.34.0 | Checks for usage of the `dbg!` macro. | `clippy_lints/src/dbg_macro.rs` | VERIFIED |
| `print_stdout` | Clippy | restriction | allow | pre 1.29.0 | Checks for printing on stdout; purpose is to catch debugging remnants. | `clippy_lints/src/write/mod.rs` | VERIFIED |
| `print_stderr` | Clippy | restriction | allow | 1.50.0 | Checks for printing on stderr; purpose is to catch debugging remnants. | `clippy_lints/src/write/mod.rs` | VERIFIED |
| `indexing_slicing` | Clippy | restriction | allow | pre 1.29.0 | Checks for usage of indexing or slicing that may panic at runtime. | `clippy_lints/src/indexing_slicing.rs` | VERIFIED |
| `undocumented_unsafe_blocks` | Clippy | restriction | allow | 1.58.0 | Checks for `unsafe` blocks and impls without a `// SAFETY: ` comment explaining why the unsafe operations are safe. | `clippy_lints/src/undocumented_unsafe_blocks.rs` | VERIFIED |
| `unnecessary_safety_comment` | Clippy | restriction | allow | 1.67.0 | Checks for `// SAFETY: ` comments on safe code. | `clippy_lints/src/undocumented_unsafe_blocks.rs` | VERIFIED |
| `allow_attributes_without_reason` | Clippy | restriction | allow | 1.61.0 | Checks for attributes that allow lints without a reason. | `clippy_lints/src/attrs/mod.rs` | VERIFIED |
| `allow_attributes` | Clippy | restriction | allow | 1.70.0 | Checks for usage of the `#[allow]` attribute and suggests replacing it with `#[expect]` (RFC 2383). | `clippy_lints/src/attrs/mod.rs` | VERIFIED |
| `disallowed_types` | Clippy | style | warn | 1.55.0 | Denies the configured types in `clippy.toml`. | `clippy_lints/src/disallowed_types.rs` | VERIFIED |
| `disallowed_methods` | Clippy | style | warn | 1.49.0 | Denies the configured methods and functions in `clippy.toml`. | `clippy_lints/src/disallowed_methods.rs` | VERIFIED |
| `disallowed_macros` | Clippy | style | warn | 1.66.0 | Denies the configured macros in `clippy.toml`. | `clippy_lints/src/disallowed_macros.rs` | VERIFIED |
| `must_use_candidate` | Clippy | pedantic | allow | 1.40.0 | Checks for public functions that have no `#[must_use]` attribute but return something not already must-use, have no mutable arg and mutate no statics. | `clippy_lints/src/functions/mod.rs` | VERIFIED |
| `exhaustive_enums` | Clippy | restriction | allow | 1.51.0 | Warns on any exported enums that are not tagged `#[non_exhaustive]`. | `clippy_lints/src/exhaustive_items.rs` | VERIFIED |
| `exhaustive_structs` | Clippy | restriction | allow | 1.51.0 | Warns on any exported structs that are not tagged `#[non_exhaustive]`. | `clippy_lints/src/exhaustive_items.rs` | VERIFIED |
| `missing_errors_doc` | Clippy | pedantic | allow | 1.41.0 | Checks doc comments of publicly visible functions returning `Result` and warns if there is no `# Errors` section. | `clippy_lints/src/doc/mod.rs` | VERIFIED |
| `missing_panics_doc` | Clippy | pedantic | allow | 1.51.0 | Checks doc comments of publicly visible functions that may panic and warns if there is no `# Panics` section. | `clippy_lints/src/doc/mod.rs` | VERIFIED |
| `missing_safety_doc` | Clippy | style | warn | 1.39.0 | Checks doc comments of publicly visible unsafe functions and warns if there is no `# Safety` section. | `clippy_lints/src/doc/mod.rs` | VERIFIED |
| `too_long_first_doc_paragraph` | Clippy | **nursery** | allow | 1.82.0 | Checks if the first paragraph in the documentation of items listed in the module page is too long. | `clippy_lints/src/doc/mod.rs` | VERIFIED |
| `wildcard_imports` | Clippy | pedantic | allow | 1.43.0 | Checks for wildcard imports `use _::*`. | `clippy_lints/src/wildcard_imports.rs` | VERIFIED |
| `map_err_ignore` | Clippy | restriction | allow | 1.48.0 | Checks for instances of `map_err(\|_\| Some::Enum)`. | `clippy_lints/src/methods/mod.rs` | VERIFIED |
| `clone_on_ref_ptr` | Clippy | restriction | allow | pre 1.29.0 | Checks for `.clone()` on a ref-counted pointer (`Rc`, `Arc`, `rc::Weak`, `sync::Weak`) and suggests `Rc::clone(foo)` style. | `clippy_lints/src/methods/mod.rs` | VERIFIED |
| `unused_result_ok` | Clippy | restriction | allow | 1.82.0 | Checks for calls to `Result::ok()` without using the returned `Option`. | `clippy_lints/src/unused_result_ok.rs` | VERIFIED |
| `redundant_clone` | Clippy | **nursery** | allow | 1.32.0 | Checks for a redundant `clone()` (and relatives) of an owned value that is dropped without further use. | `clippy_lints/src/redundant_clone.rs` | VERIFIED |
| `implicit_clone` | Clippy | pedantic | allow | 1.52.0 | Checks for `_.to_owned()`, `vec.to_vec()` or similar when `_.clone()` would be clearer. | `clippy_lints/src/methods/mod.rs` | VERIFIED |
| `needless_collect` | Clippy | **nursery** | allow | 1.30.0 | Checks for functions collecting an iterator when collect is not needed. | `clippy_lints/src/methods/mod.rs` | VERIFIED |
| `large_types_passed_by_value` | Clippy | pedantic | allow | 1.49.0 | Checks for functions taking `Copy` arguments by value that are large enough to pass by reference; skips exported functions, `mut` params and `self`. | `clippy_lints/src/pass_by_ref_or_value.rs` | VERIFIED |
| `too_many_lines` | Clippy | pedantic | allow | 1.34.0 | Checks for functions with a large amount of lines. | `clippy_lints/src/functions/mod.rs` | VERIFIED |
| `wrong_self_convention` | Clippy | style | warn | pre 1.29.0 | Checks for methods with certain name prefixes or suffixes that do not take `self` per standard conventions. | `clippy_lints/src/methods/mod.rs` | VERIFIED |
| `new_without_default` | Clippy | style | warn | pre 1.29.0 | Checks for public types with a `pub fn new() -> Self` method and no `Default` implementation. | `clippy_lints/src/new_without_default.rs` | VERIFIED |
| `ptr_arg` | Clippy | style | warn | pre 1.29.0 | Checks for function arguments of type `&String`, `&Vec`, `&PathBuf` and `Cow<_>`. | `clippy_lints/src/ptr/mod.rs` | VERIFIED |
| `borrowed_box` | Clippy | complexity | warn | pre 1.29.0 | Checks for usage of `&Box<T>` anywhere in the code. | `clippy_lints/src/types/mod.rs` | VERIFIED |
| `missing_docs_in_private_items` | Clippy | restriction | allow | pre 1.29.0 | Warns if there is missing documentation for any private documentable item. | `clippy_lints/src/missing_doc.rs` | VERIFIED |
| `multiple_crate_versions` | Clippy | cargo | allow | pre 1.29.0 | Checks to see if multiple versions of a crate are being used. | `clippy_lints/src/cargo/mod.rs` | VERIFIED |
| `wildcard_dependencies` | Clippy | cargo | allow | 1.32.0 | Checks for wildcard dependencies in the `Cargo.toml`. | `clippy_lints/src/cargo/mod.rs` | VERIFIED |
| `cargo_common_metadata` | Clippy | cargo | allow | 1.32.0 | Checks to see if common metadata is defined in `Cargo.toml` (links API Guidelines C-METADATA). | `clippy_lints/src/cargo/mod.rs` | VERIFIED |
| `unsafe_code` | rustc | (none listed) | allow | not shown | Catches usage of `unsafe` code and other potentially unsound constructs like `no_mangle`, `export_name` and `link_section`. | allowed-by-default listing | VERIFIED |
| `unsafe_op_in_unsafe_fn` | rustc | (none listed) | allow on editions up to 2021; **warn from edition 2024** | not shown | Detects unsafe operations in unsafe functions without an explicit `unsafe` block. | allowed-by-default listing | VERIFIED |
| `missing_docs` | rustc | (none listed) | allow | not shown | Detects missing documentation for public items. | allowed-by-default listing | VERIFIED |
| `missing_debug_implementations` | rustc | (none listed) | allow | not shown | Detects missing implementations of `fmt::Debug` for public types. | allowed-by-default listing | VERIFIED |
| `unused_must_use` | rustc | (none listed) | warn | not shown | Detects unused result of a type flagged as `#[must_use]`. | warn-by-default listing | VERIFIED |
| `unknown_lints` | rustc | (none listed) | warn | not shown | Detects unrecognized lint attributes. | warn-by-default listing | VERIFIED |
| `non_exhaustive_omitted_patterns` | rustc | (none listed) | allow | not shown | Helps consumers of a `#[non_exhaustive]` struct or enum match all fields or variants explicitly. **Unstable:** the listing's example requires `#![feature(non_exhaustive_omitted_patterns_lint)]`, so it is nightly-only. | allowed-by-default listing | VERIFIED (nightly-only) |

rustc listing URLs: `https://doc.rust-lang.org/rustc/lints/listing/allowed-by-default.html#<lint-with-hyphens>` and `https://doc.rust-lang.org/rustc/lints/listing/warn-by-default.html#<lint-with-hyphens>`. The rustc listing does not show an "added in" version; the "Since" column is therefore "not shown".

Notes:
- `too_long_first_doc_paragraph`, `redundant_clone` and `needless_collect` are in **nursery**, not a default-on group, in stable 0.1.100.
- `disallowed_types`, `disallowed_methods`, `disallowed_macros` are style/warn but do nothing until configured in `clippy.toml`.

### Clippy configuration keys (`clippy.toml`)

Source: `https://doc.rust-lang.org/clippy/lint_configuration.html` (book source `book/src/lint_configuration.md`, master). Stable lint page shows the same keys in each lint's Configuration block.

| Key | Meaning (source wording) | Default | Affected lint | Status |
| --- | --- | --- | --- | --- |
| `allow-unwrap-in-tests` | Whether `unwrap` should be allowed in test functions or `#[cfg(test)]` | `false` | `unwrap_used` | VERIFIED |
| `allow-expect-in-tests` | Whether `expect` should be allowed in test functions or `#[cfg(test)]` | `false` | `expect_used` | VERIFIED |
| `allow-panic-in-tests` | Whether `panic` should be allowed in test functions or `#[cfg(test)]` | `false` | `panic` | VERIFIED |
| `allow-indexing-slicing-in-tests` | Whether `indexing_slicing` should be allowed in test functions or `#[cfg(test)]` | `false` | `indexing_slicing` | VERIFIED |
| `disallowed-types` | List of disallowed types, as fully qualified paths. Fields: `path` (required), `reason` (optional), `replacement` (optional), `allow-invalid` (optional, default `false`) | `[]` | `disallowed_types` | VERIFIED |
| `disallowed-methods` | List of disallowed methods, as fully qualified paths. Fields: `path` (required), `reason` (optional), `replacement` (optional), `allow-invalid` (optional, default `false`) | `[]` | `disallowed_methods` | VERIFIED |

Related keys seen on the stable lint page (not asked, for completeness): `allow-dbg-in-tests` (`dbg_macro`), `allow-print-in-tests` (`print_stdout`, `print_stderr`), `allow-unwrap-in-consts`, `allow-unwrap-types`, `disallowed-macros`.

### Cargo manifest lint tables

Sources: `https://doc.rust-lang.org/cargo/reference/manifest.html#the-lints-section`, `https://doc.rust-lang.org/cargo/reference/workspaces.html#the-lints-table`, `https://doc.rust-lang.org/cargo/reference/lints.html`, `https://doc.rust-lang.org/cargo/reference/unstable.html`.

- `[lints]` (package): sets lint levels per tool table (`[lints.rust]`, `[lints.clippy]`, `[lints.cargo]`). Short form `unsafe_code = "forbid"` equals `{ level = "forbid", priority = 0 }`. Levels: forbid, deny, warn, allow. `priority` is a signed integer; lower numbers are overridden by higher ones. Applies only to the current package, not dependencies. "MSRV: Respected as of 1.74". VERIFIED.
- `[workspace.lints]`: defines lint configuration inherited by members; members opt in with `[lints]` then `workspace = true`. "MSRV: Respected as of 1.74". VERIFIED.
- `[lints.cargo]`: the unstable-features page now says "Cargo's linting system and the `[lints.cargo]` table have been stabilized in Rust 1.100." VERIFIED (stable as of 1.100.0, i.e. the current release).
- Cargo lint groups (lints chapter): `cargo::default` (warn/deny), `cargo::correctness` (deny), `cargo::style` (warn), `cargo::suspicious` (warn), `cargo::pedantic` (allow), `cargo::restriction` (allow). VERIFIED.
- Cargo's own lints (lints chapter), all VERIFIED as listed:

| Default level | Lints |
| --- | --- |
| allow | `manual_readme` (pedantic), `non_kebab_case_bins` (pedantic), `non_kebab_case_features` (restriction), `non_kebab_case_packages` (restriction), `non_snake_case_features` (restriction), `non_snake_case_packages` (restriction) |
| warn | `blanket_hint_mostly_unused` (suspicious), `missing_lints_inheritance` (suspicious; flags a package without `[lints]` while `workspace.lints` exists), `redundant_homepage` (style), `unknown_lints`, `unused_dependencies`, `unused_workspace_dependencies`, `unused_workspace_package_fields` |
| deny | `text_direction_codepoint_in_comment` (correctness), `text_direction_codepoint_in_literal` (correctness) |

Groups for `unknown_lints`, `unused_dependencies`, `unused_workspace_dependencies` and `unused_workspace_package_fields` were not extracted from their detail entries: UNVERIFIED (group only).

## Part 2. Tools

| Tool | Official location | Purpose (source wording or close paraphrase) | Status |
| --- | --- | --- | --- |
| cargo-deny | `https://github.com/EmbarkStudios/cargo-deny`, book `https://embarkstudios.github.io/cargo-deny/` | "Cargo plugin for linting your dependencies" | VERIFIED |
| cargo-deny `[advisories]` | book `checks/advisories/cfg.md` | `yanked`: what happens when a crate version yanked from its registry is encountered; values `deny`, `warn` (default), `allow` | VERIFIED |
| cargo-deny `[licenses]` | book `checks/licenses/cfg.md` | Configuration for `cargo deny check license`; keys include `allow`, `exceptions`, `confidence-threshold`, `clarify`, `include-dev`, `include-build`, `version` | VERIFIED |
| cargo-deny `[bans]` | book `checks/bans/cfg.md` | `wildcards`: what happens when a dependency uses the `*` version; `deny`, `warn` (default), `allow`; related `allow-wildcard-paths` | VERIFIED |
| cargo-deny `[sources]` | book `checks/sources/cfg.md` | `unknown-registry`: crate from a registry not in `allow-registry` (`deny`/`warn` default/`allow`); `unknown-git`: crate from a git repo not in `allow-git` (`deny`/`warn` default/`allow`); `allow-git`: list of exact git URLs allowed (`.git` stripped); related `private`, `required-git-spec` | VERIFIED |
| cargo-audit | `https://github.com/rustsec/rustsec/tree/main/cargo-audit` (crate `cargo-audit`) | "Audit your dependencies for crates with security vulnerabilities reported to the RustSec Advisory Database." | VERIFIED |
| cargo-about | `https://github.com/EmbarkStudios/cargo-about`, book `https://embarkstudios.github.io/cargo-about/` | "Cargo plugin for generating a license listing for all dependencies of a crate" | VERIFIED |
| cargo-hack | `https://github.com/taiki-e/cargo-hack` | "Cargo subcommand to provide various options useful for testing and continuous integration" (e.g. `--each-feature`, `--feature-powerset`) | VERIFIED |
| cargo-udeps | `https://github.com/est31/cargo-udeps` | "Find unused dependencies in Cargo.toml." Compiles on stable but needs nightly to run. | VERIFIED |
| cargo-machete | `https://github.com/bnjbvr/cargo-machete` | "Remove unused Rust dependencies with this one weird trick!" | VERIFIED |
| Miri | `https://github.com/rust-lang/miri` | "an Undefined Behavior detection tool for Rust"; runs binaries and test suites and detects unsafe code that fails its safety requirements | VERIFIED |
| cargo-nextest | `https://github.com/nextest-rs/nextest`, site `https://nexte.st/` | "a new, faster Cargo test runner" ("next-generation test runner for Rust") | VERIFIED |
| `rust-toolchain.toml` | rustup book `https://rust-lang.github.io/rustup/overrides.html` ("The toolchain file") | Pins a toolchain per project directory; `[toolchain]` section mandatory with at least one property (`channel`, `components`, `targets`, `profile`, or `path`); `channel` and `path` mutually exclusive; if both `rust-toolchain` and `rust-toolchain.toml` exist, the legacy `rust-toolchain` wins | VERIFIED |
| `rust-version` | `https://doc.rust-lang.org/cargo/reference/rust-version.html` | Optional `[package]` key stating the supported Rust toolchain version; bare version, no semver operators; unsupported toolchain is an error unless `--ignore-rust-version`; "MSRV: Respected as of 1.56" | VERIFIED |

All repositories above were confirmed live and not archived via the GitHub API on 2026-11-18.

## Part 3. Source passages by practice

Google: `https://google.github.io/styleguide/rustguide.html` (source `https://github.com/google/styleguide/blob/gh-pages/rustguide.md`). Anchors below are the page's own `<a id>` or heading slugs.
Microsoft: `https://microsoft.github.io/rust-guidelines/` (source `https://github.com/microsoft/rust-guidelines`, files under `src/guidelines/`). Published section pages: `.../guidelines/universal/`, `.../guidelines/libs/ux/`, `.../guidelines/libs/resilience/`, `.../guidelines/libs/building/`, `.../guidelines/libs/interop/`, `.../guidelines/apps/`, `.../guidelines/correctness/`, `.../guidelines/docs/`, `.../guidelines/project/`, `.../guidelines/ffi/`, `.../guidelines/ai/`; each guideline is anchored `#M-ID`.

**Identifier note:** panic and unsafe guidelines now live in a **Correctness** section (`src/guidelines/correctness/`), and the `safety/` section is empty. All identifiers you named exist with those exact spellings, including `M-PANIC-CONTINUATION`. The guard rule is `M-STRONG-TYPES-GUARD`. The test-placement rule is `M-INTEGRATION-TESTS`; the tautological-test rule is `M-TAUTOLOGICAL-TESTS` (AI section). Re-export and prelude rules: `M-NO-GLOB-REEXPORTS`, `M-FOREIGN-REEXPORTS`, `M-NO-PRELUDE`, `M-SINGLE-ITEM-PATH`, `M-DOC-INLINE`. Minimum version: `M-MSRV`. Source inconsistency: `M-MODULE-DOCS` links to `M-DOC-FIRST-SENTENCE`, but the real identifier is `M-FIRST-DOC-SENTENCE`.

### Panic for bugs and violated invariants

| Google | Microsoft |
| --- | --- |
| "Reporting errors" (`#reporting-errors`): "**Use `panic!` to report bugs and violated invariants.**" Defects must be fixed in code, not handled at runtime; coarse-grained recovery might be possible with `catch_unwind`. Notes some codebases avoid panics entirely and report broken invariants via `Result`; exceptions for developer-facing binaries and tests. | M-PANIC-ON-BUG "Detected programming bugs are panics, not errors" (`correctness/#M-PANIC-ON-BUG`): contract violations are programming errors and must panic; no `Error` type should be returned for them; tip "Make it 'Correct by Construction'". M-PANIC-IS-STOP "Panic means 'stop the program'": "Panics are not exceptions." Not valid to use panics to communicate errors upstream or to assume panics will be caught. M-PANIC-MESSAGE: intentional panics must carry a helpful message. |

### Prefer `expect` over `unwrap`

| Google | Microsoft |
| --- | --- |
| "Prefer `expect` over `unwrap`" (`#prefer-expect-over-unwrap`): "If a panic is necessary because an invariant cannot be expressed in the type system, prefer `expect` over `unwrap` to document the reason." | No dedicated rule found. M-PANIC-IS-STOP gives `x.expect("must never happen")` as a valid programming-error panic and `unwrap()` on a lock result as valid on poison. |

### Catching panics (`catch_unwind`): the sources differ

| Google | Microsoft |
| --- | --- |
| "Don't call `panic::catch_unwind`" (`#dont-call-paniccatch_unwind`): "Use of `panic::catch_unwind` is prohibited in first-party Rust code." Exception: defense in depth at critical entry points, never relied upon, only where `panic=unwind` is possible; Chrome, Android and Fuchsia require `panic=abort`. | M-PANIC-CONTINUATION "Panic continuation is last resort": "Panic recovery via `catch_unwind()` is a matter of last resort and must generally be followed by a controlled application restart." Library code should not catch and continue; servers may use it per request so other requests finish, but should still restart. |

Difference: Google prohibits it with a narrow defense-in-depth exception; Microsoft permits it as a last resort (notably per-request in servers) provided a restart follows.

### Poisoned locks

| Google | Microsoft |
| --- | --- |
| "Handling poison" (`#poison`): "Never reach inside a poisoned mutex to get at its insides, no matter how tempting the use case may seem." | M-PANIC-IS-STOP: a valid reason to panic is "when encountering a poison, e.g., by calling `unwrap()` on a lock result". |

### Unsafe code and SAFETY comments

| Google | Microsoft |
| --- | --- |
| "Unsafe code" (`#unsafe`): don't write unsafe unless no safe way exists; encapsulate in a safe abstraction, ideally a separate crate; "Add a safety comment starting with `SAFETY:` that explains why the code is correct."; add a technical justification (why not safe, benchmarks if performance). | M-UNSAFE "Unsafe needs reason, should be avoided": valid reasons are novel abstractions, performance, FFI and platform calls; no ad-hoc `unsafe` to shorten code, bypass `Send` or lifetimes; any use needs plain-text safety reasoning; must pass Miri; follow the Unsafe Code Guidelines. M-UNSOUND "All code must be sound": "unsound code is never acceptable" (no exceptions; soundness boundaries are module boundaries). M-UNSAFE-IMPLIES-UB: `unsafe` on functions and traits only when misuse risks UB, not for otherwise dangerous functions. M-STATIC-VERIFICATION enables `undocumented_unsafe_blocks`, `unnecessary_safety_comment`, `unnecessary_safety_doc`, and rustc `unsafe_op_in_unsafe_fn`. |

### `#[must_use]`

| Google | Microsoft |
| --- | --- |
| "`#[must_use]` on functions" (`#must-use-on-functions`) when the caller cannot use the function correctly while ignoring the return (including pure functions such as `HashMap::get()`) or the return represents an error or critical information, unless the type is already `#[must_use]`. "`#[must_use]` on types" (`#must-use-on-types`): error types, lazily evaluated computations. | No dedicated guideline found. UNVERIFIED as absent (searched guideline titles only). |

### `#[non_exhaustive]`

| Google | Microsoft |
| --- | --- |
| "Apply `#[non_exhaustive]` to publicly-exposed enums": "If an enum is part of a public API used by other teams, mark it `#[non_exhaustive]`." Exceptions for fixed ontologies and two-state enums; cites Clippy `exhaustive_enums`. "Apply `#[non_exhaustive]` to public structs with public fields" (`#non-exhaustive-structs`), with an FRU exception. "Don't omit patterns on `non_exhaustive` enums when matching" (`#non-exhaustive-enum-matching`): list all variants. | No dedicated guideline found. M-ERRORS-CANONICAL-STRUCTS: an inner `ErrorKind` enum "should not be exposed directly for future-proofing reasons"; expose `is_xxx()` methods instead. |

### Newtypes and strong types

| Google | Microsoft |
| --- | --- |
| "Newtypes versus type aliases" (`#newtypes-vs-type-aliases`): use a newtype for semantic differences, own API, flexibility to change the representation, and type safety when values are easy to mix up (e.g. `Day`, `Month`, `Year`). | M-STRONG-TYPES "Use the proper type family": "use the strongest type available, as early as possible in your API flow" (e.g. `PathBuf` over `String` for OS paths). M-STRONG-TYPES-GUARD "Newtypes guard their invariants": non-total newtypes need at least one fallible constructor; conversions from weaker types must be fallible (`TryFrom`/`FromStr`); infallible `From` may not be offered; panicking `new` allowed, preferably `const`. |

### Enum over bool

| Google | Microsoft |
| --- | --- |
| "Prefer `enum` over `bool` in APIs" (`#prefer-enum-over-bool-in-apis`): "Use `enum` function parameters instead of `bool` in cases where the purpose of the parameter is not obvious." | No dedicated guideline found. |

### Glob imports, re-exports and preludes

| Google | Microsoft |
| --- | --- |
| "Don't use glob imports" (`#dont-use-glob-imports`): allowed only for `use super::*` in inline modules, `use enum::*` in enum-focused bodies, `pub use submodule::*` for non-leaf modules, and private C++ namespace merges. "This also means that defining preludes should be avoided." Third-party preludes at reviewer discretion. | M-NO-GLOB-REEXPORTS: "Don't `pub use foo::*` from other modules, especially not from other crates" (HAL platform re-exports excepted). M-NO-PRELUDE: "Crates must not define a `prelude` or any namespace intended to be imported as `use foo::*`." M-FOREIGN-REEXPORTS: crates should generally not re-export items from other crates (umbrella, technical-split and macro `__private` exceptions). M-SINGLE-ITEM-PATH (AI): public items reachable through only one path. M-DOC-INLINE: mark `pub use` items with `#[doc(inline)]`. Note Google permits `pub use submodule::*` for non-leaf modules, which M-NO-GLOB-REEXPORTS discourages. |

### Documenting public APIs and panics

| Google | Microsoft |
| --- | --- |
| "When and how to write documentation" (`#documentation`): "Add documentation comments to public APIs, potentially using the `missing_docs` lint to help with this." "Always document panic cases for functions which may panic due to malformed input." Document invariants for unsafe functions and traits; `//!` for modules; Markdown. | M-CANONICAL-DOCS "Documentation has canonical sections": summary sentence always; `# Examples`, `# Errors`, `# Panics`, `# Safety`, `# Abort` when applicable; no parameter tables. M-FIRST-DOC-SENTENCE "First sentence is one line; approx. 15 words": "the first sentence should not exceed **15 words**". M-MODULE-DOCS "Has comprehensive module documentation": every public library module needs `//!` docs. M-STATIC-VERIFICATION enables `too_long_first_doc_paragraph`. M-NO-META-DESIGN-DOCUMENTATION (AI): document the end state, not the design journey. |

### No unstable features

| Google | Microsoft |
| --- | --- |
| "No unstable features" (`#unstable-features`): "Don't use unstable features." Exceptions for Android embedded, Chrome blanket approvals, Fuchsia guidance. | No dedicated guideline found. M-MSRV and M-LATEST-EDITION assume stable toolchains. |

### rustfmt settings

| Google | Microsoft |
| --- | --- |
| "Use the appropriate formatting tool" (`#formatting-other`): options `max_width = 100`, `hex_literal_case = Lower`, `format_macro_matchers = true`, escapes for invisible characters; a codebase on stable may skip options unavailable there. "Opting out of automatic formatting" (`#formatting-optout`): `#[rustfmt::skip]` only for manual alignment or generated code. | M-STATIC-VERIFICATION lists rustfmt "ensures consistent source formatting"; no settings given. |

### Static verification and lint groups: the sources differ

Microsoft M-STATIC-VERIFICATION "Use static verification" (`universal/#M-STATIC-VERIFICATION`): tools compiler lints, Clippy, rustfmt, cargo-audit, cargo-hack, cargo-udeps, Miri, used "as part of check-in gates". Exact lints:

- `[lints.rust]`, all `"warn"`: `ambiguous_negative_literals`, `missing_debug_implementations`, `redundant_imports`, `redundant_lifetimes`, `trivial_numeric_casts`, `unsafe_op_in_unsafe_fn`, `unused_lifetimes` (all confirmed allow-by-default rustc lints).
- `[lints.clippy]` groups at `{ level = "warn", priority = -1 }`: `cargo`, `complexity`, `correctness`, `pedantic`, `perf`, `style`, `suspicious`; `nursery` commented out as optional.
- Individual lints at `"warn"`: `allow_attributes_without_reason`, `as_pointer_underscore`, `assertions_on_result_states`, `clone_on_ref_ptr`, `deref_by_slicing`, `disallowed_script_idents`, `empty_drop`, `empty_enum_variants_with_brackets`, `empty_structs_with_brackets`, `fn_to_numeric_cast_any`, `if_then_some_else_none`, `map_err_ignore`, `redundant_type_annotations`, `renamed_function_params`, `semicolon_outside_block`, `undocumented_unsafe_blocks`, `unnecessary_safety_comment`, `unnecessary_safety_doc`, `unneeded_field_pattern`, `unused_result_ok`, `too_long_first_doc_paragraph` (all restriction except `too_long_first_doc_paragraph`, nursery, on the stable list).
- `literal_string_with_formatting_args = "allow"` (nursery) "May cause issues with structured logging otherwise."

Microsoft M-LINT-OVERRIDE-EXPECT "Lint overrides should use `#[expect]`": local overrides use `#[expect]`, not `#[allow]`, and "Overrides should be accompanied by a `reason`"; `#[allow]` still fine for generated code and macros.

Google: names no lint groups or check-in lint set; it mentions only `missing_docs` (documentation) and Clippy `exhaustive_enums` (context for `#[non_exhaustive]`). Difference: Microsoft prescribes all major groups including `pedantic` and `cargo` at warn; Google prescribes none.

### `Debug` on public types

| Google | Microsoft |
| --- | --- |
| "Use `#[derive()]` if possible" exists (`#use-derive-if-possible`); no specific `Debug` rule extracted. UNVERIFIED as to content. | M-PUBLIC-DEBUG "Public types are Debug": all public types implement `Debug`; types holding sensitive data use a custom impl with unit tests proving nothing leaks. |

### Error type shape: the sources differ

| Google | Microsoft |
| --- | --- |
| "Reporting errors": choose `Option` for simple failures, `Result` for recoverable failures needing context (e.g. `io::Error`), `panic!` for bugs. No prescription of struct versus enum shape. | M-ERRORS-CANONICAL-STRUCTS "Errors are canonical structs": "Errors should be a situation-specific `struct` that contain a `Backtrace`, a possible upstream error cause, and helper methods." Inner `ErrorKind` not exposed; `Display` required. M-APP-ERROR "Applications may use Anyhow or derivatives": applications may use `anyhow`, `eyre`, `ohno::AppError` or similar; libraries always follow M-ERRORS-CANONICAL-STRUCTS. M-FROM-ERROR: canonical conversion uses `From`, not `map_err`. |

### Builders

Microsoft M-INIT-BUILDER "Complex type construction has builders": types with 4 or more initialization permutations provide `FooBuilder`, chainable, ending in `.build()`, entry `Foo::builder()`, setters named `x()`; required parameters passed when creating the builder. Related M-BUILD-RESULT, M-INIT-CASCADED. Google: "Options structs should implement Default" (`#options-structs-should-implement-default`) exists; content not extracted (UNVERIFIED).

### Wrappers in APIs

| Google | Microsoft |
| --- | --- |
| "Avoid `Rc` and `Arc`" (`#avoid-rc-and-arc`) exists under Ownership and borrowing; content not extracted (UNVERIFIED). | M-AVOID-WRAPPERS "Avoid smart pointers and wrappers in APIs": `Rc<T>`, `Arc<T>`, `Box<T>`, `RefCell<T>` should be avoided in public APIs unless fundamental to the API or justified by benchmarks. |

### Structured logging

Microsoft M-LOG-STRUCTURED "Use structured logging with message templates": structured events with named properties and message templates per messagetemplates.org; event names `<component>.<operation>.<state>`; OTel semantic conventions. Related M-LOG-NOT-PRINT "Production code uses telemetry, not println". Google: no logging rule found.

### Features are additive

Microsoft M-FEATURES-ADDITIVE "Features are additive": "All library features must be additive, and any combination must work"; no `no-std` feature (use `std`); a feature must not disable or modify public items. Google: no rule found.

### Test utilities, test placement and tautological tests: the sources differ

| Google | Microsoft |
| --- | --- |
| "Use the right per-codebase test framework": "Most codebases use their own specific test framework rather than `#[test]`" (Chrome `rust_gtest_interop`, Fuchsia `#[fuchsia::test]`). No placement rule found. | M-TEST-UTIL "Test utilities are feature gated": mocking, sensitive-data inspection, safety overrides and fake data behind a feature, recommended name `test-util`. M-INTEGRATION-TESTS "Integration tests live under `tests/`": "Tests that only touch public API surface are _integration tests_ and belong under `tests/`, not `mod tests {}`"; integration tests preferred when either works. M-TAUTOLOGICAL-TESTS "Tests do not assert ground truth" (AI section): "Unit tests should verify meaningful behavior instead of repeating foundational definitions." |

### Async: the sources differ

| Google | Microsoft |
| --- | --- |
| "Don't use `async` / `.await` [chrome]" (`#async-await-chrome`): "Don't use `async` / `.await` in Chromium." (Chrome-scoped only.) | M-ASYNC-FN "Functions are `async` over returning a Future": prefer `async fn foo()` over `fn foo() -> impl Future` when both work. Also M-ASYNC-STACK-SIZE, M-YIELD-POINTS (performance). |

### Minimum supported Rust version

Microsoft M-MSRV "MSRV is conservatively updated": set an MSRV when a library is created, keep it "a few versions behind the most recent compiler release"; bumping MSRV needs only a minor release. Google: no MSRV rule found.

### FFI

Microsoft FFI section: M-FFI-NAMING (`-sys` for import crates, `-ffi` for export crates); M-FFI-TRANSLATES "Business logic belongs in core crates, FFI only translates"; M-ISOLATE-DLL-STATE "Isolate DLL state between FFI libraries" (share only portable `#[repr(C)]` data with no statics, thread locals or `TypeId` interaction). M-UNSAFE FFI checklist: prefer established interop libraries, document generated bindings. Also M-SYS-CRATES (libs/building). Google: C++ interop glob-import exception only; no FFI section found.

### Microsoft AI section rules

Identifiers and titles: M-DESIGN-FOR-AI "Design with AI use in mind" (idiomatic API patterns, thorough docs per C-CRATE-DOC, C-FAILURE, C-LINK, M-MODULE-DOCS); M-NO-META-DESIGN-DOCUMENTATION "Avoid meta design documentation"; M-RUST-SHAPED "Rust code solves Rust problems" (ports must not copy C#, Java, C++ constructs 1-on-1); M-SINGLE-ITEM-PATH "Items are only visible through one path"; M-TAUTOLOGICAL-TESTS "Tests do not assert ground truth".

## Part 4. Licences

| Source | Licence (from its own file) | Attribution requirement for paraphrase with links |
| --- | --- | --- |
| Google style guide repository (`google/styleguide`) | `LICENSE` is "Creative Commons Legal Code, Attribution 3.0 Unported". README "Licensing": style guides are CC-By 3.0; code samples are Apache 2.0. The page links CC BY 3.0. | CC BY 3.0 section 4(b): when distributing the work or an adaptation, keep copyright notices and credit the original author or designated party, the title, the licensor's URI where practicable, and for an adaptation a credit identifying the use of the work. Paraphrase that is an adaptation should credit "Google Rust Style Guide", link the page and the CC BY 3.0 licence. Whether pure paraphrase of ideas is an adaptation is a legal question not verified here. |
| Microsoft Pragmatic Rust Guidelines (`microsoft/rust-guidelines`) | `LICENSE.md`: MIT License, "Copyright (c) Microsoft Corporation." Each guideline file carries the header comment "Copyright (c) Microsoft Corporation. Licensed under the MIT license." | MIT requires the copyright and permission notice in copies or substantial portions. For paraphrase with links, a credit line naming Microsoft's Pragmatic Rust Guidelines (MIT) with the URL is the conservative practice; the licence text itself only mandates the notice for copies. |
| Rust API Guidelines (`rust-lang/api-guidelines`) | README "License": dual Apache License 2.0 or MIT, at your option (`LICENSE-APACHE`, `LICENSE-MIT`). | Same as MIT or Apache 2.0: notices required for copies; credit with link recommended for paraphrase. |
| Clippy documentation (`rust-lang/rust-clippy`, lint list and book in the same repository) | README "License" and `COPYRIGHT`: "Copyright (c) The Rust Project Contributors", Apache 2.0 or MIT at your option. (The lint page loads mdBook CSS from a CDN under MPL-2.0; that is styling, not lint text.) | Same as MIT or Apache 2.0: notices required for copies; credit "Clippy documentation, The Rust Project Contributors" with link recommended for paraphrase. |

## UNVERIFIED items and why

1. Groups of Cargo lints `unknown_lints`, `unused_dependencies`, `unused_workspace_dependencies`, `unused_workspace_package_fields`: names and default level (warn) verified; their group fields were not extracted.
2. Microsoft has no `#[must_use]`, `#[non_exhaustive]`, enum-over-bool, unstable-features, logging-free or FFI-free counterpart to the Google rules listed: absence was established from guideline titles only, not a full-text search of every page.
3. Google content for "Use `#[derive()]` if possible", "Options structs should implement Default" and "Avoid `Rc` and `Arc`": headings confirmed, bodies not extracted.
4. Legal reach of attribution for pure paraphrase (whether it is an "Adaptation" under CC BY 3.0 or a "substantial portion" under MIT): licence texts quoted, legal interpretation not verified.
5. The rustc lint listing shows no "added in" version for any rustc lint, so "Since" is not available for those seven lints.

All 41 Clippy lints and all 7 rustc lints exist under the exact names given. No lint name was wrong.
