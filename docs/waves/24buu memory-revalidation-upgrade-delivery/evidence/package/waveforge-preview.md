Owner: Engineering
Status: active
Last verified: 2026-11-24

Draft for operator review. Unsent. This letter describes rehearsal build q5u1.

Waveforge maintainers,

We have a Wavefoundry 1.53.0 preview ready for downstream testing. The build identifier is `1.53.0+q5u1`. We would especially value a rehearsal against a copy of your last installed release with your normal vocabulary, prompt overrides and host permission settings.

- A spec describes one proposed change. A behavior contract describes behavior the project maintains across changes. New contracts live under `docs/architecture/contracts/` and the `wf-contract` skill helps maintainers write or update them. The migration previews the affected documents, links and TechDocs navigation.
- The five stock create, get, add, remove and close tools now use `*_spec` names. For example, call `wf_get_spec(spec_id=...)`. Upgrade and setup migrate eligible repository rules, preserve constraints and report remaining holds. Please check your served names and rules after restarting the MCP host. If you manage restrictions through MDM, the registry, server policy or host launch flags, verify the effective rules in that host before using the renamed tools.
- Upgrade refreshes registered lifecycle prompts and the plan template when it can prove the installed copy matches its old baseline. It preserves local edits and points to the incoming template for a hand merge. Please try one unedited prompt and one customized prompt. Review memories and Close wave now carry the keep rule, and `memory_brief` reports which active memories need checking. Upgrade leaves the records themselves alone.
- This preview includes the four items we took from your hardening note. The rules preview uses isolated Python and restricts its environment. Line-ending preservation bounds expensive matching. The statistics guidance describes SQLite sidecar behavior. The public trust-bundle accessor lets callers use the framework’s trust-source order. The reranker-role and provider-precision proposals remain outside this preview.

We rehearsed two successive upgrades from stock 1.51.0 through the direct ZIP, the installed CLI and live MCP. All six upgrades passed 108 checks on an offline Apple Silicon fixture. The direct ZIP cleaned up on both hops. The installed 1.51.0 launcher needed one explicit cleanup on the first hop. MCP retained its separate cleanup step on both. When automatic provider discovery suggested a precision change, the upgrade kept the existing index. Selecting its original CPU provider allowed the upgrade to continue.

Please let us know where your actual migration differs: a hook or tool still using its retired name, an edited prompt that changed unexpectedly, a missing permission hold, or a contract link or TechDocs page that no longer resolves.

ZIP SHA-256: `c0b771482678830533d6660c11c40f391b537a417c19bb319a083fa2cd1b0043`.
