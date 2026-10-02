# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 1.28.x (latest release) | Yes |
| < 1.28 | No |

Only the latest minor release line receives security fixes. Upgrade to the
latest release before reporting, and check it against the affected versions
listed in a published advisory.

## Reporting a vulnerability

**Do not open a public issue for security vulnerabilities.**

Use GitHub's private vulnerability reporting instead:
[Report a vulnerability](https://github.com/coryhacking/wavefoundry/security/advisories/new)

Include:

- Description of the vulnerability
- Steps to reproduce
- Affected version(s) (`cat .wavefoundry/framework/VERSION`)
- Any suggested fix, if you have one

Fixes for confirmed vulnerabilities will be released as patch versions. Credit
is given in the release notes unless you request otherwise.

## Scope

Wavefoundry runs locally as a subprocess of an AI agent host. It has no
network-facing service in the current architecture; the optional repository
dashboard listens on loopback only. The primary risk
surface is:

- **File-system access** — MCP tools read and write within declared
  repository roots. Path-escape vulnerabilities are in scope.
- **Seed prompt injection** — seed prompts are executed by AI agents.
  Prompt injection that causes unintended mutations is in scope.
- **Dependency supply chain** — compromised or vulnerable Python
  dependencies are in scope. The setup script enforces a 21-day package
  age guard via `uv --exclude-newer` to reduce exposure to newly published
  malicious packages, and installs its own `uv` only from hash-verified
  wheels.
- **Local concurrency and lock integrity** — defects that let two local
  processes mutate the same wave state at once, or that corrupt index or
  lifecycle records, are in scope.

For the internal threat model and trust boundary analysis, see
[`docs/architecture/threat-model.md`](docs/architecture/threat-model.md).
