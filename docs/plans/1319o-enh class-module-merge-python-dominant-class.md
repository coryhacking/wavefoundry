# Class/Module Merge — Python (Single Dominant Class Convention)

Change ID: `1319o-enh class-module-merge-python-dominant-class`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-01
Wave: TBD

## Rationale

Wave 13129 deferred Python from the class/module merge family because Python idiom permits many top-level classes per module (`utils.py` containing `Foo`, `Bar`, `Baz`). The basename-match heuristic used for Java/Kotlin/C#/Swift/Scala/PHP/Rust/Ruby would over-trigger if applied naively.

However, a meaningful subset of Python codebases follows a **single-dominant-class convention**: `foo_bar.py` contains exactly one top-level class `FooBar` (or `foo_bar`), with module-level helpers acting as that class's adjunct. Django models, dataclass modules, SQLAlchemy ORM files, and Pydantic schema files all routinely follow this pattern. When this convention holds, merging behaves correctly. When it doesn't, the merge must skip.

This change adds Python to the merge family with a **conservative dominance gate**: only merge when the module has exactly one top-level class declaration and that class's name matches the basename (with snake-to-Pascal conversion).

## Approach

Mirror the Rust extension (`1319i`) for Python with one additional precondition:

1. **Dominance check** — count top-level `class_definition` nodes. If the count is not exactly 1, skip merge. (Functions, constants, and `if __name__ == "__main__"` blocks are ignored — they're not class definitions.)
2. **Basename match** — same snake-to-PascalCase conversion as Rust/Ruby. Try both forms (`foo_bar.py` → `FooBar` or `foo_bar`).
3. **Extension** — `.py`. (`.pyi` stub files are out of scope.)

Python merge-eligible kind: `class`. The Python dispatch already extracts `class` symbols via `class_definition` — no Ruby-style bare-node-type plumbing needed.

## Requirements

1. Python added to `_CLASS_MODULE_MERGE_KINDS_BY_LANG` (`{class}`) and `_CLASS_MODULE_MERGE_EXTS_BY_LANG` (`.py`).
2. New `_CLASS_MODULE_MERGE_DOMINANCE_GATE_LANGS = frozenset({"python"})` — controls the "exactly one top-level class" precondition. Other languages continue to merge regardless of sibling classes (Java/C#/Kotlin enforce one public top-level type by language rules).
3. Shared snake-to-PascalCase derivation (from `1319i`) reused.
4. Tests:
   - `foo_bar.py` with one class `FooBar` → merged.
   - `foo_bar.py` with one class `foo_bar` (snake-case class name, legal but rare) → merged.
   - `Foo.py` with one class `Foo` → merged.
   - `utils.py` with classes `A`, `B`, `C` → NOT merged (dominance gate).
   - `foo_bar.py` with class `FooBar` plus module-level functions → merged (functions don't count toward dominance).
   - `foo_bar.py` with class `Bar` (basename mismatch) → NOT merged.

## Scope

**Problem statement:** Python is the only typed-or-popular language without merge coverage. Single-dominant-class modules (very common in Django/SQLAlchemy/Pydantic codebases) currently produce a fragmented two-node view (file + class) when a unified node is more natural.

**In scope:**

- `.wavefoundry/framework/scripts/graph_indexer.py` — Python dispatch + dominance-gate logic.
- `.wavefoundry/framework/scripts/tests/test_graph_indexer.py` — 6 regression tests.

**Out of scope:**

- `.pyi` stub files (separate convention; defer).
- Nested classes (outer class still wins basename match if it's the only top-level class).
- Dataclass / `attrs` / `pydantic.BaseModel` semantic recognition. The dominance gate is structural, not semantic.
- Multi-class modules with one "primary" class plus helpers (would require heuristics — e.g., size, public-API analysis — out of scope).

## Acceptance Criteria

- [ ] AC-1: Python entries added to dispatch tables.
- [ ] AC-2: Dominance gate skips merge when top-level class count != 1.
- [ ] AC-3: Snake-to-PascalCase derivation works for Python (shared with `1319i`/`1319k`).
- [ ] AC-4: `foo_bar.py` with `class FooBar` → merged.
- [ ] AC-5: `foo_bar.py` with `class foo_bar` → merged (literal basename branch).
- [ ] AC-6: `utils.py` with multiple top-level classes → NOT merged.
- [ ] AC-7: Module-level functions do not block merge when exactly one class is present.
- [ ] AC-8: All existing graph-builder tests pass.

## Tasks

- [ ] Open `framework_edit_allowed` gate
- [ ] Add Python dispatch entries + dominance-gate set
- [ ] Implement top-level class-count check
- [ ] Add 6 regression tests
- [ ] Run framework tests
- [ ] Close gate; mark change `implemented`

## Affected Architecture Docs

- N/A — extends an existing pattern at the same architectural layer as `1319i`/`1319k`. No boundary or data-flow change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Dispatch foundation |
| AC-2 | required | Idiom safety |
| AC-3 | required | Snake convention |
| AC-4 | required | Common Django/Pydantic case |
| AC-5 | important | Edge case (snake-class-name) |
| AC-6 | required | Negative case — false-positive guard |
| AC-7 | required | Functions-don't-block invariant |
| AC-8 | required | No baseline regression |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Dominance gate (exactly-one-class) | Python permits many top-level classes per module; merging would mis-represent multi-class utility modules | Always merge on basename match (rejected — over-triggers); semantic dominance (rejected — heuristic scope creep) |
| 2026-06-01 | Functions don't count toward dominance | Module-level helpers are normal adjuncts to a class file; counting them would defeat the purpose | Count everything top-level (rejected — would block legitimate Django-model files) |

## Risks

| Risk | Mitigation |
|---|---|
| Files with one class + many top-level constants/dataclass instances merge anyway | Documented; dominance gate is structural by design |
| `pytest` fixture modules with `class TestFoo` patterns merge unexpectedly | Test files already excluded by framework conventions; if not, add filter |
| `__init__.py` files with re-exported class | basename is `__init__`; doesn't match any class name — naturally skipped |

## Related Work

- Closes the Python gap left by `13190`/`13196`. Final basename-match coverage.
- Companion to `1319m` (Go directory aggregation) — together these address the two remaining merge exclusions on different terms.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
