# Search Retrieval Friction

Owner: Engineering
Status: active
Last verified: 2026-05-26

## Scope

This note captures a retrieval friction case observed while answering a question about how the build number is generated. The goal is to make future search work faster and more direct for implementation questions that have a clear owning script.

## What Happened

- The question was conceptually about build-number generation, but the first semantic results favored packaging prompts and docs before the owning implementation files.
- The relevant implementation lived in [.wavefoundry/framework/scripts/lifecycle_id.py](/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts/lifecycle_id.py) and [.wavefoundry/framework/scripts/build_pack.py](/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts/build_pack.py).
- The important split was:
- `lifecycle_id.py` generates the full lifecycle prefix with `build_prefix()`.
- `build_pack.py` trims that prefix to the rightmost 4 characters with `_build_suffix()` and uses the result for package filenames and version stamping.

## Why It Was Slower Than It Should Be

- Semantic retrieval over-weighted prompt/docs surfaces such as [docs/prompts/package-wavefoundry.prompt.md](/Users/coryhacking/Developer/wavefoundry/docs/prompts/package-wavefoundry.prompt.md) before the implementation owner files.
- The query wording used implementation verbs like `generated`, `derived`, and `stamped`, but the ranking path did not clearly bias toward code that owns those operations.
- The answer required reading both the prefix generator and the packager to resolve the full-vs-trimmed suffix distinction.

## Search Enhancements To Consider

- Add stronger owner-file bias for implementation verbs like `generated`, `derived`, `stamped`, `computed`, and `written`.
- Demote prompt/docs surfaces when the query is about a concrete implementation artifact such as `VERSION`, `framework_revision`, `build prefix`, or `zip suffix`.
- Add a lightweight exact-token follow-up when semantic retrieval returns packaging docs first and a script path is clearly implied.
- Expand two-hop retrieval for terms like `prefix`, `suffix`, `build`, `stamp`, and `version` so `build_pack.py` and `lifecycle_id.py` surface earlier.
- Prefer code-summary chunks from the owning script before prompt docs for questions about generation, stamping, or derivation mechanics.

## Suggested Agent Behavior

- Start with exact lookup when the question names an artifact or file family.
- Use semantic search only after the likely owner file has been identified or when the owner is genuinely unclear.
- Cross-check docs after the code owner is found, not before.

## Evidence

- [lifecycle_id.py](/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts/lifecycle_id.py:106) generates the lifecycle prefix from the configured epoch and current time.
- [build_pack.py](/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts/build_pack.py:53) calls `lifecycle_id.py --prefix-only`.
- [build_pack.py](/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts/build_pack.py:65) trims the prefix to the rightmost 4 characters.
- [build_pack.py](/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts/build_pack.py:150) stamps `VERSION` with `MAJOR.MINOR.PATCH+<build>`.
- [build_pack.py](/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts/build_pack.py:279) uses the build suffix in the zip filename.

## Follow-Up

- If this pattern repeats, promote the retrieval heuristics into the search-architecture docs or the Guru journal so it can inform future ranking and tool-routing changes. The current canonical note lives in [docs/agents/journals/guru.md](/Users/coryhacking/Developer/wavefoundry/docs/agents/journals/guru.md).
