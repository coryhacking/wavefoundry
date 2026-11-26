# Inspect behavior contract drift without editing

Spec ID: `24c3s-enh inspect-behavior-contract-drift`
Spec Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-25
Wave: 24c3o review-comprehension-isolation-and-contract-drift

## Rationale

Author behavior contract already traces promises to source and tests. Maintainers also need to inspect disagreements while deciding whether code, tests or the contract should change.

## Product Intent

A maintainer can ask wf-contract to inspect a selected boundary and receive a cited list of disagreements and missing evidence without starting an edit.

## Requirements

1. Add an explicit read-only inspection to the existing contract workflow. Resolve a named contract or a bounded selection using the project’s configured paths and existing links. Account for legacy or unindexed contracts selected by the operator. Preserve the normal authoring path.
2. Trace each disputed promise to a production entry point and relevant independent assertions. Distinguish supported, contradicted and insufficient evidence. Name the examined scope and any unreadable or unexamined portions.
3. Check both directions inside the chosen boundary. Flag an observable interface, invariant or side effect absent from the contract as a candidate for maintainer judgment. Distinguish an internal detail from a public promise. Report discrepancies and gaps first with concise coverage.
4. Return the report in the response. Leave contracts, navigation, TechDocs, configuration and indexes untouched. No background sweep or new lifecycle gate.

## Scope

Return the report in the response. Leave contracts, navigation, TechDocs, configuration and indexes untouched. No background sweep or new lifecycle gate.

## Acceptance Criteria

- [x] AC-1: A fixture with a contradicted promise, a matching tested promise and a promise missing verification produces distinct conclusions with resolvable evidence.
- [x] AC-2: A documented operation with an externally visible undocumented side effect yields a cited coverage question. A private refactor with identical behavior yields none.
- [x] AC-3: A missing artifact or unreadable contract prevents a clean conclusion for that scope. Run a no-drift case, verify read-only operation and verify ordinary authoring and renamed project paths still work.

## Tasks

- [x] Extend the canonical contract prompt, generated skill description and self-hosted prompt.
- [x] Use one small contract example. Inspect a mixed selection, a supported promise alone and a missing reference. Compare the project files before and after inspection. Reuse existing authoring and renamed-profile checks.

## Agent Execution Graph

1. Implementer updates the named guidance or qualification procedure.
2. The assigned reviewer checks the observations against the acceptance criteria during normal delivery review.

## Serialization Points

- `.wavefoundry/framework/seeds/230-author-spec.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/author-behavior-contract.prompt.md`
- `docs/prompts/author-behavior-contract.prompt.md`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py`

## Affected Architecture Docs

N/A. This change extends an existing workflow within its current authority.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the stated outcome or its scope boundary. |
| AC-2 | required | Establishes the stated outcome or its scope boundary. |
| AC-3 | required | Establishes the stated outcome or its scope boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-25 | Planned for wave admission. | Requirements and acceptance criteria above. |
| 2026-11-25 | Implemented the inspection branch in seed 230, the install and self-hosted prompts, and all three rendered skills. | Fixture and observations below. The default missing-only contract prompt and skill test passed. The second-profile renderer file passed 247 tests with three skips. |

**Inspection walkthrough**

The implementer followed seed 230 on one temporary project. The selected operations were lookup and save. The project setting led to a custom index, whose link resolved to the legacy owner. Removing that index entry in a copy still allowed direct selection of the legacy page by path.

| Mixed selection | Observed evidence |
| --- | --- |
| Contradicted | Contract line 3 promises null for a missing key. The production lookup at service.py:4–5 returns "unknown". The independent assertion at test_service.py:5 expects "unknown". |
| Coverage question | Should callers rely on save appending a ("saved", key) event? Contract line 4 describes storage and the return value. The append at service.py:9 changes the supplied events list and test_service.py:11 asserts its contents. |
| Insufficient evidence | Contract line 4 promises the return value. The implementation returns it at service.py:10, but the call at test_service.py:9 discards it. The test needs an assertion on the result. |
| Supported | Contract line 2 promises whitespace handling. The public lookup at service.py:4–5 passes the key through strip at line 2. The assertion at test_service.py:4 exercises a padded key. Contract line 4 also promises storage, implemented at service.py:8 and asserted at test_service.py:10. |

Selecting only lookup for an existing padded key yielded one supported promise, with no discrepancy or coverage question in that condition. Selecting legacy/missing.md yielded insufficient evidence for its entire scope because the file was absent. In a copy, inlining the private normalization helper at its two call sites preserved the results of both tests and introduced no public coverage question.

The five-file fixture below is the complete project examined. Both test functions ran successfully under Python with bytecode writing disabled. SHA-256 over sorted relative file names and file contents, each followed by a NUL byte, was identical before and after the inspection: `5af94856d062c325264fb6b4eaef7d16c5e6881ecb571f94251c8b34261b2351`. Ordinary authoring in a separate copy corrected the missing-key promise on the selected legacy page and linked it from the custom index. All four numbered authoring steps and the reporting instruction in both project prompts matched their previous contents.

**guide/edges/index.md**

```text
[Lookup and save](../../legacy/lookup.md)
```

**legacy/lookup.md**

```text
# Lookup and save
1. Lookup ignores surrounding spaces.
2. Missing keys return null.
3. Save stores the value and returns it.
```

**project.toml**

```text
contract_index = "guide/edges/index.md"
```

**service.py**

```python
def _normalize(key):
    return key.strip()

def lookup(key, records):
    return records.get(_normalize(key), "unknown")

def save(key, value, records, events):
    records[_normalize(key)] = value
    events.append(("saved", key))
    return value
```

**test_service.py**

```python
from service import lookup, save

def test_lookup():
    assert lookup(" A ", {"A": "alpha"}) == "alpha"
    assert lookup("B", {}) == "unknown"

def test_save():
    records, events = {}, []
    save("A", 2, records, events)
    assert records == {"A": 2}
    assert events == [("saved", "A")]
```

After review found a retained writer-only prompt, the rendered skill now routes explicit inspection directly to seed 230. On the repaired tree, all three hosts preserved both the previous shipped prompt and a customized writer prompt byte-for-byte. The prior skill body failed the focused regression.

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-25 | Add inspection to wf-contract. | Author behavior contract already traces promises to source and tests. Maintainers also need to inspect disagreements while deciding whether code, tests or the contract should change. | A repository-wide scanner needs a reliable denominator and raises noise. Running the writer could silently settle which side is right. |

## Risks

Implementation quirks can be mistaken for policy. Report an undocumented observation as a question until the owner confirms intent.

## Session Handoff

See the wave record for coordination.
