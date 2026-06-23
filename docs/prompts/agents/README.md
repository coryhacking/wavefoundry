# Agent-Oriented Prompt Bodies

Owner: Engineering
Status: active
Last verified: 2026-05-08

Supporting agent-oriented prompt bodies for Wavefoundry. These are checked-in context helpers for agents executing Wave Framework commands. They are **not public commands** and are not listed in `docs/prompts/index.md`.

## Contents

| File | Purpose |
|------|---------|
| `init-wave-context.prompt.md` | Agent body for Init Wavefoundry |
| `upgrade-wave-context.prompt.md` | Agent body for Upgrade Wavefoundry |
| `plan-feature.prompt.md` | Agent body for Plan feature |
| `prepare-wave.prompt.md` | Agent body for Prepare wave |
| `implement-wave.prompt.md` | Agent body for Implement wave |
| `implement-feature.prompt.md` | Agent body for Implement feature |
| `review-wave.prompt.md` | Agent body for Review wave |
| `close-wave.prompt.md` | Agent body for Close wave |
| `finalize-feature.prompt.md` | Agent body for Finalize feature |

## Usage

These bodies are consumed during wave execution to provide agents with the project-specific procedure context they need to execute Wave Framework commands correctly against Wavefoundry's repository and workflow configuration.
