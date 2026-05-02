# Structure-Aware Code Chunker

Change ID: `12aw5-enh structure-aware-code-chunker`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-05-01
Wave: TBD

## Rationale

All non-Python code files are currently chunked with a dumb 60-line overlapping window with `section=None`. A 300-line TypeScript file produces 5–6 overlapping windows with no structural signal — class names, method names, and doc comments all buried in undifferentiated text. This degrades both retrieval precision (searching for a method name produces the wrong window) and generation quality (no context about what unit the code belongs to).

Python already has AST-based structure-aware chunking, but has two gaps: (1) decorator lines are excluded from code chunks because `node.lineno` points to the `def` line rather than the first `@decorator` line; (2) `section` carries only `ClassName.method_name` with no file/module context, so chunks from different files with the same method name are indistinguishable in search results.

This change adds regex-based structure-aware chunking for Java, C#, JavaScript, TypeScript, C, and C++ — and fixes the two Python gaps — using the same breadcrumb convention as the markdown heading hierarchy change (`12avx`). HTML gets structure-aware chunking via landmark elements rather than declaration detection, since it has no callable units.

**Prior art.** Declaration-boundary chunking with breadcrumb context is the approach used by production code intelligence systems (Sourcegraph, GitHub Copilot's code index). It is the appropriate strategy for code search workloads, as distinct from the overlapping fixed-size windows common in general RAG tutorials. The breadcrumb-in-`text` injection follows Anthropic's Contextual Retrieval technique (2024), which demonstrated measurable retrieval improvements by prepending context to chunk text before embedding. The decision to use regex over tree-sitter is a deliberate scope/dependency tradeoff — tree-sitter is the right upgrade path if full parse accuracy is later required.

## Requirements

1. Each new language chunker must emit `kind="code"` chunks at declaration boundaries (class, method, function) and `kind="doc"` chunks for doc comments attached to those declarations.
2. `section` on every chunk must carry a breadcrumb in the form `{file_stem} > {ClassName} > {method_name}` (depth varies by what is present; file stem is always the outermost level). Both `kind="code"` and `kind="doc"` chunk `text` must be prefixed with the same breadcrumb, separated from the body by `\n\n` — doc chunks benefit from this as much as code chunks since they are the primary embedding target for prose search.
3. Doc comment chunks must contain stripped comment text (decoration removed: `/**`, `*`, `*/`, `///`, `//!` prefixes stripped per-line). Annotation/attribute names must appear as a space-separated prefix line before the prose — `@RequestMapping @Authorized\n\n{prose}`. Annotation arguments are excluded from doc chunk text except where the first argument is a string literal that is itself documentation (e.g. C# `[Obsolete("Use NewMethod instead")]` → include the string).
4. Annotation/attribute blocks must be included verbatim in code chunks (full `@Name(args)` or `[Name("arg")]` lines). For Python, decorator lines must be included by using `node.decorator_list[0].lineno` as the chunk start line when decorators are present.
5. Multiline annotations (Java/Kotlin/TS: `@Annotation(\n  value="..."\n)`) must be accumulated as a unit using a parenthesis-balance counter — no splitting mid-annotation.
6. When a declaration cannot be identified (heavily macro-wrapped C/C++, minified JS, unconventionally formatted code), fall through to `chunk_line_window` — never raise. Inject the file-stem breadcrumb (depth-1 only) into fallback chunk `section` and `text` prefix since file context is always known.
7. All new chunkers must pass their output through the existing `split_large_code_chunks` (4000-char cap) after structure-aware splitting.
8. The existing `chunk_python` function gains the decorator fix (Req 4) and module-context breadcrumb (Req 2); no other behavioral changes.
9. HTML files are chunked by landmark element boundaries (`<section>`, `<article>`, `<nav>`, `<main>`, `<header>`, `<footer>`, `<h1>`–`<h6>` at nesting depth 0–1) and block-level `id` attributes. Each landmark block becomes a `kind="doc"` chunk with `section` carrying `{file_stem} > {landmark tag or id}`. Falls back to line-window when no landmarks are present.
10. **Chunk ID convention.** All new language chunkers must use a consistent, forward-compatible ID scheme. The scheme uses the same separator hierarchy as `12avx` (`/` for nesting, `:` for suffix) and the existing Python convention (`::` for qualified names):
    - Top-level function/class: `{path}::{Name}`
    - Method/nested: `{path}::{ClassName}.{method_name}` (dot for scope within a class, consistent with Python)
    - Doc comment chunk: `{path}::{Name}.__doc__` (consistent with Python's existing convention)
    - Line-window fallback: `{path}:L{start}-L{end}` (consistent with existing fallback)
    - C# with namespace: `{path}::{Namespace}.{ClassName}.{method_name}`
    - HTML landmark: `{path}#{tag-or-id}` (mirrors markdown section anchor convention)
11. **Index rebuild signal.** This change must increment `CHUNKER_VERSION` in `chunker.py` (introduced by `12avx`). The indexer reads this constant into `meta.json` and forces a full rebuild when it changes — ensuring no deployed index goes silently stale after these changes ship.
12. New tests must cover: breadcrumb in `section` and `text` prefix for both code and doc chunks; doc comment extraction and decoration stripping; annotation names in doc chunk; annotation arguments in code chunk; multiline annotation accumulation; decorator fix for Python; line-window fallback breadcrumb (depth-1); HTML landmark chunking; Go receiver method breadcrumb; Rust impl-block method breadcrumb; shell heuristic doc chunk `[inferred from comments]` prefix; PowerShell comment-based help extraction; Scala class/method chunking; SQL DDL-boundary chunking; Jupyter cell routing and cell-indexed IDs; chunk ID shapes for each new language; `split_large_code_chunks` applied after structure-aware split.

## Scope

**Problem statement:** Non-Python code files produce structurally blind line-window chunks, losing class/method/function identity and all doc comment content. Python chunks lose decorator lines and file-level context.

**In scope:**

- `chunker.py` — new `chunk_java`, `chunk_csharp`, `chunk_js_ts`, `chunk_c_cpp`, `chunk_html`, `chunk_go`, `chunk_rust`, `chunk_shell`, `chunk_powershell`, `chunk_scala`, `chunk_sql`, `chunk_notebook`, `chunk_xml` functions; updated `chunk_python` (decorator fix + breadcrumb); updated `chunk_file` dispatcher
- `tests/test_chunker.py` — new test cases per Req 12; any existing tests whose expected `section` or `text` values change due to breadcrumb injection updated with explanatory comments

**Out of scope:**

- Tree-sitter or any compiled grammar dependency — regex + AST only
- Kotlin, Swift, Ruby, PHP — currently line-windowed; separate change if needed
- `####` and deeper HTML nesting — best-effort; falls to line-window
- Cross-file scope resolution or symbol graph construction
- Indexer, server, or embedding pipeline changes

**Language-specific notes:**

- *JavaScript/TypeScript*: one shared `chunk_js_ts` function handles `.js`, `.ts`, `.jsx`, `.tsx`, `.mjs`, `.cjs`. Arrow function declarations (`const foo = () =>`) are detected at top-level and class-body scope only; deeply nested arrow functions fall to line-window within their enclosing chunk.
- *C/C++*: template function signatures spanning multiple lines and heavily macro-wrapped declarations fall to line-window for that declaration. Preprocessor `#define` blocks are not emitted as structured chunks.
- *C#*: `namespace` blocks are detected and used as an additional breadcrumb level between file stem and class — `{file_stem} > {namespace} > {ClassName} > {method}`.
- *HTML (.html, .htm)*: no callable units; landmark-element chunking (`<section>`, `<article>`, `<nav>`, `<main>`, `<header>`, `<footer>`, `<h1>`–`<h6>`) at nesting depth 0–1; `id`-attribute section naming; `kind="doc"` throughout.
- *Go (.go)*: method receiver `func (r *ReceiverType) Name()` — receiver type name (strip `*`) is the breadcrumb second level: `{file_stem} > {ReceiverType} > {method}`. Top-level functions: `{file_stem} > {func_name}`. `type Name struct/interface` chunked as class-equivalents. Doc comments are plain `//` lines immediately before a declaration with no blank line — Go's own documented convention (see golang.org/doc/comment); detected by line adjacency, not by `/**` marker.
- *Rust (.rs)*: `impl TypeName` and `impl Trait for Type` block boundaries tracked as running state while scanning, so enclosed `fn` items inherit the correct breadcrumb (`{file_stem} > {TypeName} > {fn_name}`). Top-level `fn`, `struct`, `trait` declarations: `{file_stem} > {name}`. Rust attributes `#[Name(...)]` are the annotation equivalent — names-only in doc chunk as `#[Name]` prefix line, verbatim in code chunk. Doc comments: `///` stripped of `///` prefix; `//!` inner docs treated as file-level doc chunk.
- *Shell (.sh, .bash, .zsh, .fish)*: POSIX `name() {`, bash `function name() {` / `function name {`, and fish `function name` ... `end` are all detected. No annotation equivalent. Leading `#` comment block immediately before a function (no blank line between) emitted as heuristic doc chunk with text prefixed `[inferred from comments]` — not a standardized format; the prefix makes the heuristic nature explicit. Fish `end`-delimited functions handled separately from brace-delimited shells. Maximum breadcrumb depth: `{file_stem} > {function_name}`.
- *PowerShell (.ps1, .psm1)*: `Function Verb-Noun {`; PS5+ `class Name {` with methods. Comment-based help `<# .SYNOPSIS ... .DESCRIPTION ... #>` is PowerShell's doc-comment standard (documented in `about_Comment_Based_Help`). `.SYNOPSIS` and `.DESCRIPTION` field content is the primary doc chunk text; `.PARAMETER` and `.EXAMPLE` field names preserved as search signals in the doc chunk (not stripped — they are meaningful search terms). Attributes `[Parameter()]`, `[ValidatePattern()]`, `[CmdletBinding()]` — names-only in doc chunk, verbatim in code chunk.
- *Scala (.scala)*: `class`, `object`, `trait`, `case class` declarations; `def` methods inside them. Scaladoc `/** */` shares Java syntax — reuse Javadoc extraction logic. Scala is the primary Spark language; no special Spark-specific detection needed beyond standard Scala class/method boundaries.
- *SQL (.sql)*: DDL-boundary chunking — `CREATE TABLE`, `CREATE VIEW`, `CREATE FUNCTION`, `CREATE PROCEDURE`, `CREATE INDEX` are declaration equivalents. Each DDL block becomes a `kind="code"` chunk. `--` single-line and `/* */` multi-line comments immediately before a DDL statement extracted as `kind="doc"` chunks. DML (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) not individually chunked — falls to line-window within a containing DDL block or file scope.
- *Jupyter notebooks (.ipynb)*: JSON-structured files; each cell has a `cell_type` (`code` or `markdown`) and `source`. Code cells route to the per-language chunker for the notebook's kernel language (detected from `kernelspec.language` in notebook metadata; defaults to Python). Markdown cells route to `chunk_markdown`. Cell index included in all chunk IDs: `{path}::cell[{n}]::{symbol}` for code chunks, `{path}::cell[{n}]#{heading-slug}` for markdown chunks. Cell index `n` is 0-based. Falls back to line-window for cells in unrecognised kernel languages.
- *XML / JSP / markup variants (.xml, .jsp, .xsd, .xsl, .xslt, .svg)*: structural chunking via element names and `id`/`name` attributes at nesting depth 0–2. Named elements (`<bean id="...">`, `<endpoint name="...">`, JSP `<%-- ... --%>` comment blocks) produce `kind="doc"` chunks with `{file_stem} > {element-name-or-id}` breadcrumbs. For JSP: `<jsp:include>`, `<%@ page ... %>` directives chunked as structural markers. Unnamed deep nesting falls to line-window. All XML variants treated as `kind="doc"` — they are markup/config documents, not code.

## Acceptance Criteria

- AC-1: `chunk_file("src/Payment.java", source)` produces at least one `kind="code"` chunk per method/class with `section` starting with `"Payment > "` and `text` prefixed with the same breadcrumb.
- AC-2: `chunk_file("src/Payment.java", source)` with Javadoc produces `kind="doc"` chunks whose `text` is breadcrumb-prefixed, contains stripped prose (no `/**`, `*`, `*/` decoration), and has annotation names as a prefix line before the prose.
- AC-3: A Java method with `@RequestMapping("/api") @Authorized` produces a doc chunk with text starting `"Payment > processPayment\n\n@RequestMapping @Authorized\n\n"` followed by stripped Javadoc prose.
- AC-4: The same method's code chunk includes `@RequestMapping("/api")` and `@Authorized` verbatim in its text.
- AC-5: A multiline Java annotation (`@Annotation(\n  value="x"\n)`) is accumulated as a unit — not split across chunks.
- AC-6: `chunk_python` with a decorated function includes the `@decorator` line in the code chunk text (not in a gap between chunks).
- AC-7: `chunk_python` section field reads `"{file_stem} > {ClassName} > {method_name}"` for a class method; `text` is breadcrumb-prefixed.
- AC-8: C# `[Obsolete("Use NewMethod instead")]` doc chunk text starts with breadcrumb, then `@Obsolete Use NewMethod instead\n\n{prose}`.
- AC-9: A minified JS file (no recognisable declarations) falls through to line-window chunks with no exception raised; each chunk has depth-1 file-stem breadcrumb in `section` and `text`.
- AC-10: An HTML file with `<section id="intro">` produces a `kind="doc"` chunk with `section` containing `"intro"`.
- AC-11: An HTML file with no landmark elements falls through to line-window chunks.
- AC-12: All new structured chunks pass through `split_large_code_chunks` — no single chunk exceeds 4000 characters.
- AC-13: Java method doc chunk ID is `{path}::ClassName.method.__doc__`; code chunk ID is `{path}::ClassName.method`; Python method unchanged convention confirmed.
- AC-14: `CHUNKER_VERSION` is incremented from the value set by `12avx`; indexer triggers full rebuild on changed value.
- AC-15: Go receiver method produces `section == "{file_stem} > {ReceiverType} > {method_name}"`; adjacent `//` comment block (no blank line) produces a doc chunk for the same declaration.
- AC-16: Rust `impl TypeName { fn method() }` produces `section == "{file_stem} > TypeName > method"`; a top-level `fn` outside an impl block produces `section == "{file_stem} > fn_name"`.
- AC-17: Shell function with a leading `#` comment block produces a doc chunk whose text starts with `[inferred from comments]`.
- AC-18: PowerShell `<# .SYNOPSIS ... .DESCRIPTION ... #>` before a function produces a doc chunk containing the `.SYNOPSIS` and `.DESCRIPTION` text; `.PARAMETER` field name is preserved in the doc chunk text.
- AC-19: Scala `class Payment { def process() }` produces `section == "Payment > process"` with Scaladoc stripped of `/**`/`*`/`*/`.
- AC-20: SQL `CREATE TABLE orders (...)` produces a `kind="code"` chunk with `section == "{file_stem} > orders"`; a `-- comment` immediately before the DDL produces a `kind="doc"` chunk.
- AC-21: A Jupyter `.ipynb` Python code cell containing `def my_func():` produces a chunk with ID `{path}::cell[{n}]::my_func`; a markdown cell produces a chunk with ID `{path}::cell[{n}]#{heading-slug}`.
- AC-22: An XML file with `<bean id="paymentService">` produces a `kind="doc"` chunk with `section` containing `"paymentService"`.
- AC-23: All pre-existing `test_chunker.py` tests pass; updated assertions include an explanatory comment.
- AC-24: New tests cover all cases in Req 12.

## Tasks

- [ ] Increment `CHUNKER_VERSION` in `chunker.py` (must be done first; value set by `12avx` — increment it by 1)
- [ ] Fix `chunk_python`: use `node.decorator_list[0].lineno` when decorators present; inject `{file_stem} > ` breadcrumb into `section` and `text` prefix for both code and doc chunks
- [ ] Implement `chunk_java(source, path)`: regex-detect class/interface/enum and method declarations; paren-balance annotation accumulation; Javadoc extraction and stripping; emit code + doc chunks with breadcrumb and `{path}::{Name}.__doc__` / `{path}::{Name}` IDs; fall through to `chunk_line_window` with depth-1 breadcrumb on failure
- [ ] Implement `chunk_csharp(source, path)`: same as Java plus `namespace` breadcrumb level; `[Attribute("string arg")]` doc-chunk string extraction; `///` XML doc comment stripping
- [ ] Implement `chunk_js_ts(source, path)`: `function`, `class`, method, top-level/class-body arrow function declarations; JSDoc extraction; annotation name extraction from JSDoc `@` tags; same ID convention
- [ ] Implement `chunk_c_cpp(source, path)`: function-at-file-scope detection; `struct`/`class` (C++) boundaries; Doxygen `/** */` and `///` extraction; skip `#define` blocks; fall through on template/macro complexity with depth-1 breadcrumb
- [ ] Implement `chunk_html(source, path)`: landmark element detection at nesting depth 0–1; `id`-attribute section naming; `{path}#{tag-or-id}` IDs; `kind="doc"` throughout; fall through to `chunk_line_window` when no landmarks
- [ ] Implement `chunk_go(source, path)`: detect `func (recv *Type) Name()` and `func Name()` declarations; track receiver type for breadcrumb; detect `type Name struct/interface` as class-equivalents; extract adjacent `//` doc comment blocks (no blank line); same ID convention
- [ ] Implement `chunk_rust(source, path)`: track current `impl TypeName` / `impl Trait for Type` block as running state; detect enclosed `fn` items and assign three-level breadcrumb; detect top-level `fn`/`struct`/`trait`; extract `///` and `//!` doc comments; `#[Name]` attribute names in doc chunk, verbatim in code chunk
- [ ] Implement `chunk_shell(source, path)`: detect POSIX `name() {`, bash `function name {`, fish `function name`...`end`; extract leading `#` comment block as heuristic doc chunk prefixed `[inferred from comments]`; fish `end`-delimited detection separate from brace-delimited
- [ ] Implement `chunk_powershell(source, path)`: detect `Function Verb-Noun {` and PS5+ `class Name {` with methods; extract `<# .SYNOPSIS ... .DESCRIPTION ... #>` comment-based help; preserve `.PARAMETER`/`.EXAMPLE` field names in doc chunk; `[Attribute()]` names-only in doc chunk, verbatim in code chunk
- [ ] Implement `chunk_scala(source, path)`: detect `class`, `object`, `trait`, `case class`, `def` boundaries; reuse Javadoc `/** */` extraction logic; same ID convention
- [ ] Implement `chunk_sql(source, path)`: detect `CREATE TABLE/VIEW/FUNCTION/PROCEDURE/INDEX` as declaration boundaries; extract preceding `--` and `/* */` comment blocks as doc chunks; DML falls to line-window
- [ ] Implement `chunk_notebook(source, path)`: parse `.ipynb` JSON; detect kernel language from `metadata.kernelspec.language`; route code cells to per-language chunker; route markdown cells to `chunk_markdown`; prefix all chunk IDs with `cell[{n}]::`; fall through to line-window for unrecognised kernel languages
- [ ] Implement `chunk_xml(source, path)`: element-name + `id`/`name` attribute detection at nesting depth 0–2; JSP directive and comment block detection; `kind="doc"` throughout; fall through to line-window for deeply nested or unnamed content
- [ ] Update `chunk_file` dispatcher: route all new extensions; move `.html`/`.htm`, `.xml`/`.jsp`/`.xsd`/`.xsl`/`.xslt`/`.svg` out of `CODE_EXTENSIONS`; add `.ipynb`, `.scala`, `.sql`, `.go`, `.rs`, `.ps1`, `.psm1` routes
- [ ] Apply `split_large_code_chunks` after each new chunker's output
- [ ] Update `test_chunker.py`: audit all existing Python assertions for `section`, `text`, `id`; update stale values with comments; add AC-24 cases
- [ ] Run full test suite locally

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Python fix (decorator + breadcrumb) | implementer | — | Smallest change; establishes breadcrumb convention used by all others |
| `chunk_java` + `chunk_scala` | implementer | Python fix | Scala reuses Javadoc logic; implement together |
| `chunk_csharp` | implementer | Python fix | Parallel with Java/Scala |
| `chunk_js_ts` | implementer | Python fix | Parallel with others |
| `chunk_c_cpp` | implementer | Python fix | Parallel with others |
| `chunk_go` | implementer | Python fix | Parallel with others |
| `chunk_rust` | implementer | Python fix | Impl-block state tracking is the key complexity |
| `chunk_shell` | implementer | Python fix | Fish detection separate from brace-delimited |
| `chunk_powershell` | implementer | Python fix | Parallel with shell |
| `chunk_sql` | implementer | Python fix | DDL-boundary chunking; no class hierarchy |
| `chunk_html` + `chunk_xml` | implementer | — | Both are markup/doc strategies; implement together |
| `chunk_notebook` | implementer | all per-language chunkers | Routes to them; implement last |
| Dispatcher update | implementer | all chunkers | Routes all new extensions; last edit |
| Tests | implementer | dispatcher update | Requires all chunkers present |

- Breadcrumb format (`{file_stem} > {qualifier} > {name}` with ` > ` separator) and chunk ID scheme (`::` for qualified names, `.` for class-scope nesting, `.__doc__` for doc chunks) must be settled before any chunker is written — all chunkers must use the same convention.
- `CHUNKER_VERSION` must be incremented before any other code change so the version recorded in the index is accurate.
- `chunk_file` dispatcher is edited last, after all per-language functions exist.
- `framework_edit_allowed` guard must be open for all edits to framework scripts.
- This change and `12avx-enh markdown-chunker-heading-hierarchy` both edit `chunker.py` and `test_chunker.py` — they must be sequenced: `12avx` first (introduces `CHUNKER_VERSION`), then this change (increments it).

## Affected Architecture Docs

`docs/architecture/search-architecture.md` — update chunking strategy section to describe per-language structure-aware chunking, breadcrumb convention, annotation/doc-comment handling, HTML landmark strategy, chunk ID scheme, and `CHUNKER_VERSION` rebuild signal.

Otherwise N/A — confined to `chunker.py` and its tests; no module boundaries, control-flow topology, or index schema changes.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | | |
| AC-2 | | |
| AC-3 | | |
| AC-4 | | |
| AC-5 | | |
| AC-6 | | |
| AC-7 | | |
| AC-8 | | |
| AC-9 | | |
| AC-10 | | |
| AC-11 | | |
| AC-12 | | |
| AC-13 | | |
| AC-14 | | |
| AC-15 | | |
| AC-16 | | |
| AC-17 | | |
| AC-18 | | |
| AC-19 | | |
| AC-20 | | |
| AC-21 | | |
| AC-22 | | |
| AC-23 | | |
| AC-24 | | |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-01 | Change created | — |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-05-01 | Regex + AST only; no tree-sitter | Zero new dependencies; failure mode is existing line-window; 85–90% of structural value at no install cost. Tree-sitter noted as the correct upgrade path if full parse accuracy (correct handling of `function` inside string literals, C++ templates, complex macro nesting) is later required — grammar packages are pre-compiled in `tree-sitter-languages` (~80–120MB) or require a C compiler per grammar; API changed significantly between 0.20 and 0.21 creating version-pinning burden. | tree-sitter (deferred, not rejected in principle) |
| 2026-05-01 | Annotations included in both code and doc chunks, differently | Annotations are both machine-directive (runtime behavior) and human-signal (what this method requires). Code chunk needs them verbatim for behavioral accuracy; doc chunk needs names-only so `@Deprecated`, `@Authorized` are discoverable via prose search without argument noise polluting the embedding. | Annotations in code only (rejected: loses doc-search discoverability); annotations stripped entirely (rejected: loses behavioral signal) |
| 2026-05-01 | Multiline annotation accumulation via paren-balance counter, not regex | Balanced parentheses cannot be reliably matched with regular expressions (formal result: balanced-paren languages are not regular). A 10-line state machine is correct, dependency-free, and well-precedented in hand-rolled parsers for this exact case. | Regex (rejected: fails on nested parens in annotation arguments — a formal limitation, not an edge case) |
| 2026-05-01 | HTML chunked by landmark elements as `kind="doc"`, not `kind="code"` | HTML has no callable units. Landmark element chunking (`<section>`, `<article>`, `<nav>`, heading elements) mirrors the approach used by web accessibility tools and semantic search systems that treat HTML as a document rather than code. Line-window on HTML produces no structural signal. | `kind="code"` line-window (rejected: no structural signal; HTML is a document format, not a code format, for chunking purposes) |
| 2026-05-01 | C# namespace added as breadcrumb level | C# namespaces are meaningful scope identifiers that disambiguate same-named classes across assemblies — a well-established C# convention. `Payment` in `Billing.Payment` vs `Refunds.Payment` are genuinely different types; omitting namespace loses that distinction in the index. Java packages serve the same role but are not added here because the file path already encodes the package; C# namespace declarations are explicit in the file and frequently differ from the path. | Omit namespace (rejected: same-named classes across namespaces are a common C# pattern) |
| 2026-05-01 | `12avx` (markdown hierarchy) and this change are serialized: `12avx` first | `12avx` introduces `CHUNKER_VERSION`; this change increments it — sequencing is required, not recommended. | Parallel branches with merge (rejected: `CHUNKER_VERSION` constant diverges on both branches; merge conflict guaranteed; version semantics undefined on merge) |
| 2026-05-01 | Doc chunks receive breadcrumb prefix in `text` as well as code chunks | Doc chunks are the primary embedding target for prose/comment search. Per Anthropic's Contextual Retrieval (2024): context must appear in `text` to influence the embedding vector — metadata fields (`section`) have no embedding effect. Breadcrumb in `section` alone provides no retrieval benefit. | Breadcrumb only in `section` (rejected: `section` is metadata; `text` is what gets embedded) |
| 2026-05-01 | Line-window fallback injects depth-1 file-stem breadcrumb | File context is always known at fallback call time. Consistent with Contextual Retrieval principle: inject all available context. Implementation cost is negligible. | Fallback with `section=None` as today (rejected: discards known context for no benefit) |
| 2026-05-01 | Chunk IDs use `::` + `.` convention, consistent with existing Python chunks | `::` for file-to-symbol boundary follows Sourcegraph's code intelligence ID convention and is consistent with C++ / Rust scope resolution that developers already recognise. `.` for class-scope nesting is the universal qualified-name convention across Java, C#, Python, and JS. Extending both to all new language chunkers gives one consistent scheme across the entire index. `.__doc__` suffix reuses Python's own `__doc__` attribute name — immediately readable by any Python developer. | Language-native separators (rejected: `->` means pointer member access in C/C++ and return type in Rust/Swift; ambiguous in an index that spans languages) |
| 2026-05-01 | Go doc comment detected by line adjacency (`//` with no blank line before declaration) | This is Go's own documented convention (golang.org/doc/comment): "A doc comment is a comment that appears immediately before a top-level declaration, with no intervening blank lines." Detecting by adjacency follows the language spec rather than inventing a heuristic. | Require `//` followed by a specific marker (rejected: Go has no doc-comment marker; adjacency is the standard) |
| 2026-05-01 | Rust impl-block tracked as running state, not by brace matching | Brace-balanced matching is equivalent to the multiline annotation problem — not regular. A running-state approach (set current impl type on `impl` line, clear on matching `}`) handles 95%+ of real Rust code with no nesting issues; deeply nested impls (rare) fall to line-window. | Brace-balanced regex (rejected: not regular; fails on nested generics and lifetimes in impl signatures) |
| 2026-05-01 | Shell heuristic doc chunk prefixed `[inferred from comments]` | Shell has no doc-comment standard. Leading `#` blocks are a strong convention but not guaranteed to be documentation. Labeling the chunk explicitly preserves the signal for search while making the heuristic nature visible — both to users reviewing results and to future agents processing chunks. Without the label, a comment like `# TODO: fix this` would appear as documentation. | Strip the prefix (rejected: misrepresents heuristic inference as authoritative doc); omit shell doc chunks entirely (rejected: loses significant searchable content in shell-heavy repos) |
| 2026-05-01 | PowerShell `.PARAMETER`/`.EXAMPLE` field names preserved in doc chunk text | PowerShell's comment-based help fields are meaningful search terms — a developer searching for `@Parameter verbose` or `@Example` is looking for parameter documentation or usage examples. Stripping field names loses these signals. This mirrors the annotation-name-in-doc-chunk approach used for Java/C#: emit names as search signals, strip non-name content noise. | Strip field names entirely (rejected: loses meaningful search signals); include full field values verbatim (rejected: `.EXAMPLE` blocks can be very long and add noise) |
| 2026-05-01 | Scala reuses Javadoc extraction logic | Scaladoc uses identical `/** */` block comment syntax as Javadoc — this is by design (Scaladoc was modeled on Javadoc). Sharing the extraction function is correct, not a shortcut. | Separate Scala doc extractor (rejected: identical syntax; no divergence expected) |
| 2026-05-01 | SQL DML not individually chunked; falls to line-window within scope | `SELECT`/`INSERT`/`UPDATE`/`DELETE` statements do not have stable names or boundaries analogous to function declarations — a file may contain dozens of unnamed queries. DDL statements (`CREATE TABLE/VIEW/FUNCTION`) are named and declaration-like; they are the right chunking boundary for SQL. This is consistent with how database documentation tools (dbdocs.io, SchemaSpy) treat DDL as the primary structural unit. | Chunk all SQL statements (rejected: DML has no stable names; produces meaningless chunks); line-window entire SQL file (rejected: loses DDL structure which is highly meaningful for schema search) |
| 2026-05-01 | Jupyter cells prefixed `cell[{n}]::` in chunk IDs | Notebooks are documents composed of ordered cells; the cell index is necessary to reconstruct location within the notebook and to distinguish two cells that contain the same function name. `cell[{n}]` is readable, unambiguous, and follows the convention of bracket-indexed items used in JSON Pointer (RFC 6901). Kernel language detected from `metadata.kernelspec.language` — the canonical location per the Jupyter nbformat spec. | Cell hash or content-based ID (rejected: unstable across edits; cell index is stable within a given notebook version) |
| 2026-05-01 | XML/JSP/markup variants all treated as `kind="doc"` with element-name chunking | XML and its variants (XSD, XSLT, JSP, SVG) are markup and configuration documents, not code in the sense of executable logic units. Element names and `id`/`name` attributes are the meaningful structural boundaries — analogous to heading elements in HTML. This is consistent with the HTML decision and with how schema documentation tools (XML Spy, OxygenXML) treat element names as the primary navigation unit. | Treat XML as `kind="code"` with line-window (rejected: no structural signal; XML is not code for chunking purposes) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Regex misidentifies string content as declarations (e.g. `function` inside a JS string literal) | JS/TS chunker scans for declaration patterns at top-level scope only; falls through to line-window within a block where context is unclear |
| C++ template/macro declarations span multiple lines | Explicit fallback: when declaration boundary is not found within N lines of a candidate match, emit as line-window chunk with depth-1 breadcrumb |
| Rust impl blocks with complex generic bounds or lifetimes confuse running-state tracker | Running-state approach handles 95%+ of real Rust; complex generic signatures fall to line-window for that declaration — acceptable degradation, not a crash |
| Shell `#` comment before a function is not documentation (e.g. `# TODO: fix`) | `[inferred from comments]` prefix makes heuristic nature explicit; search results that surface these chunks are still useful contextual signal |
| Jupyter notebooks with mixed kernel languages or missing `kernelspec` metadata | Falls back to Python chunking when `kernelspec` is absent (Python is the dominant notebook language); falls to line-window for unrecognised kernel languages |
| XML files with very deep nesting produce many line-window fallback chunks | Depth-0–2 limit is a deliberate tradeoff; deeply nested XML config is not semantically chunked — acceptable given the document-oriented nature of such files |
| Existing `test_chunker.py` assertions on Python `section`, `text`, or `id` values break with breadcrumb injection | AC-23 requires explicit audit of all Python-related assertions before claiming green; stale expected values must be updated with comments |
| `12avx` and this change conflict on `chunker.py` if sequencing is violated | Serialization point and decision log both record the required order; wave coordinator must admit `12avx` before this change |
| Deployed indexes become stale after shipping | `CHUNKER_VERSION` increment triggers automatic full rebuild on next `build_index` call; no manual intervention needed |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
