# Independent delivery review — 1z8oz

Owner: Engineering
Status: active
Last verified: 2026-09-29

Verdict: no blocking findings. Delivered behavior meets the admitted objective.
This review supplements the existing typed specialist and council approvals;
it neither records operator signoff nor closes the wave.

## Scope and findings

The coordinator checked the requirements, implementation diff, tests, permission
roster and changed contracts. A fresh code/security reviewer independently
checked registration, replacement isolation, protections and refusal paths.

Aliases copy the fully wrapped canonical callable. Replacements capture the
normalized core tool before substitution and wrap it separately; extractor,
guard and hint choices remain distinct between those passes. Hidden names leave
the served table after alias installation. Roster tiers, structured hints and
published provenance match the declared behavior. Installation and reload
failure retain the fail-closed boundary. No additional implementation repair was
identified. Historical DEL-1 through DEL-4 are terminal in the current ledger.

The documented limits remain intentional: prose and data payloads retain
canonical names; new extension tools and overrides receive hint rewriting;
replacements are trusted distribution code, and their declared tier does not
remove an existing name-keyed guard or lock.

## Executed checks

Coordinator ran these with `python3 -B .wavefoundry/framework/scripts/run_tests.py --file <file>`:

| File | Result |
| --- | --- |
| `test_extension_tool_modules.py` | 57 passed, zero skips |
| `test_mcp_tool_registry.py` | 27 passed, zero skips |
| `test_tool_surface_golden.py` | 13 passed, zero skips |

An initial direct unittest invocation failed its registry reload subprocess
because ambient Python could not import MCP. The canonical runner rerun above
passed without dependency or source changes.

The independent security reviewer ran 23 alias/replacement tests and eight
refusal tests covering 46 declaration cases on scratch server surfaces. Its
initial ambient-interpreter failure was likewise resolved using the existing
tool environment. Four scratch mutants were killed by targeted tests:

| Mutation | Observed failure |
| --- | --- |
| Enable replacement extractors | Extractor ran when zero calls were expected |
| Omit write-replacement guard | Guard marker missing |
| Wrap preserved core with main replacement chain | Core extractor did not run |
| Rewrite replacing-handler hints | Own hint changed to core alias |

The coordinator independently recomputed `run_tests._hash_inputs()`: it matches
the green 10,004-test receipt at 2026-09-29T16:57:03.011069+00:00. This is receipt
verification, not another full-suite run. `git diff --check` passed.
`wf_review_wave` reports current specialist and delivery-council approvals,
passing docs lint and only missing operator signoff; its high-severity advisory
includes the historical repaired findings.

## Frozen reviewed source

Before/after `git hash-object` values matched:

| Path under `.wavefoundry/framework/scripts/` | Hash |
| --- | --- |
| `mcp_tool_extensions.py` | `3c2be97a2d54d8d9e0b05ff144c6b9b1636bd81c` |
| `mcp_tool_roster.py` | `6165c6fbe1a14309647258d83f6108009b68aca7` |
| `wf_server/server_impl.py` | `68dad3939a2481436a119218916c27ec7fbae31f` |
| `tests/test_extension_tool_modules.py` | `b3e3331ffa50e2c591acc0067bd4757fcb856522` |

No source edit, dependency installation, index rebuild, downstream deployment,
close or commit was performed. A second supplemental reviewer could not be
spawned because the host's agent-thread limit was reached; coordinator QA and
contract verification and the existing typed lanes remain separately identified.
