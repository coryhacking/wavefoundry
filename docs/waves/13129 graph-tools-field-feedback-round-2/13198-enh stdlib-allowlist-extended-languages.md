# Stdlib Allowlist — Extend to JS, TS, Go, Rust, Scala, PHP, Ruby

Change ID: `13198-enh stdlib-allowlist-extended-languages`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: 13129 graph-tools-field-feedback-round-2

## Rationale

Operator direction 2026-06-01: extend `external_name_collision_count` per-language allowlist coverage to ALL supported languages with stable stdlib/framework collision patterns. `1316p`/`13192` shipped Java/C#/Kotlin/Swift/Python. This change adds JS, TS, Go, Rust, Scala, PHP, Ruby.

## Approach

Extend `_STDLIB_COMMON_NAMES_BY_LANG` in `server_impl.py` with seven new entries keyed by file extension.

Per-language curation (~20-30 names each, focused on the dominant collision sources):

**JavaScript (`.js`, `.jsx`, `.mjs`, `.cjs`)** — `toString`, `valueOf`, `hasOwnProperty`, `isPrototypeOf`, `then`, `catch`, `finally`, `forEach`, `map`, `filter`, `reduce`, `find`, `some`, `every`, `includes`, `push`, `pop`, `shift`, `unshift`, `slice`, `splice`, `indexOf`, `join`, `split`, `concat`, `charAt`, `substring`, `toLowerCase`, `toUpperCase`, `trim`.

**TypeScript (`.ts`, `.tsx`)** — same as JS + framework patterns: `toJSON`, `render`, `componentDidMount`, `componentWillUnmount`, `componentDidUpdate`, `shouldComponentUpdate`, `getSnapshotBeforeUpdate`.

**Go (`.go`)** — `Read`, `Write`, `Close`, `String`, `Error`, `Marshal`, `Unmarshal`, `Encode`, `Decode`, `Wait`, `Done`, `Run`, `ServeHTTP`, `Lock`, `Unlock`, `RLock`, `RUnlock`, `Format`, `Scan`, `Reset`.

**Rust (`.rs`)** — `new`, `default`, `clone`, `drop`, `fmt`, `eq`, `ne`, `cmp`, `partial_cmp`, `hash`, `serialize`, `deserialize`, `from`, `into`, `as_ref`, `as_mut`, `unwrap`, `expect`, `iter`, `iter_mut`, `next`, `collect`, `map`, `filter`, `fold`, `len`.

**Scala (`.scala`)** — Java common names (Scala on JVM) + Scala-specific: `apply`, `unapply`, `productElement`, `productArity`, `copy`, `equals`, `hashCode`, `toString`, `foreach`, `map`, `flatMap`, `filter`, `fold`, `reduce`.

**PHP (`.php`)** — magic methods + common stdlib: `__construct`, `__destruct`, `__toString`, `__get`, `__set`, `__call`, `__callStatic`, `__isset`, `__unset`, `__invoke`, `serialize`, `unserialize`, `count`, `getIterator`, `current`, `next`, `key`, `valid`, `rewind`.

**Ruby (`.rb`)** — `initialize`, `to_s`, `inspect`, `to_proc`, `to_a`, `to_h`, `each`, `each_with_index`, `map`, `select`, `reject`, `reduce`, `inject`, `==`, `<=>`, `hash`, `dup`, `clone`, `send`, `method_missing`, `respond_to?`, `is_a?`.

## Requirements

1. `_STDLIB_COMMON_NAMES_BY_LANG` includes entries for all seven new extensions.
2. Multi-extension languages (JS, TS) handled via separate entries per extension that share the same allowlist.
3. Existing Java/C#/Kotlin/Swift/Python tests continue to pass.
4. Tests cover one canonical name per new language firing the allowlist + one regression name not in any allowlist.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server_impl.py` — `_STDLIB_COMMON_NAMES_BY_LANG` table extensions.
- `.wavefoundry/framework/scripts/tests/test_server_tools.py` — 7+ regression tests covering each new language.

**Out of scope:**

- C++ allowlist (defer).
- Per-framework subdivision (.NET BCL vs ASP.NET, etc.).

## Acceptance Criteria

- [x] AC-1: Allowlist includes `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`, `.go`, `.rs`, `.scala`, `.php`, `.rb` entries.
- [x] AC-2: TS extensions inherit JS list + add TS-specific names.
- [x] AC-3: Existing 1316p/13192 tests pass.
- [x] AC-4: Per-language canonical names fire (`forEach` for JS, `Read` for Go, `unwrap` for Rust, `__toString` for PHP, etc.).
- [x] AC-5: 7+ new regression tests.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Add 7 new language entries (with JS sharing across 4 extensions, TS across 2)
- [x] Add 7+ regression tests
- [x] Run framework tests
- [x] Close gate
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Foundation |
| AC-2 | required | TS extends JS |
| AC-3 | required | No regression |
| AC-4 | required | Per-language coverage |
| AC-5 | required | Test coverage |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | TS inherits JS list + framework patterns | TS is a JS superset; most JS stdlib names apply identically. TS-specific names cover the React/Angular/Vue framework lifecycle methods | Independent TS list (rejected — duplicates JS unnecessarily) |
| 2026-06-01 | Scala inherits Java common names | Scala on JVM; project code routinely overrides Java equivalents | Independent Scala list (rejected — misses JDK collision dimension) |
| 2026-06-01 | Rust includes derive-generated names (clone, fmt, eq, hash) | `#[derive(...)]` is the dominant Rust pattern; project methods with those names collide | Trait names only (rejected — derives are the dominant pattern) |

## Risks

| Risk | Mitigation |
|---|---|
| Per-language list omits a common name | Operator reports are the right validation cycle; lists are easy to extend |
| Some languages have looser stdlib boundaries (Ruby's monkey-patching culture) | The flag is verification trigger, not verdict |

## Related Work

- Direct extension of `1316p`/`13192` to remaining supported languages.
- Companion: `13196`, `1319a`.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
