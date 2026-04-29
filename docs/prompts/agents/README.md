# Agent-Oriented Prompt Bodies

Owner: Engineering
Status: active
Last verified: 2026-04-28

Supporting agent-oriented prompt bodies for Wavefoundry. These are checked-in context helpers for agents executing Wave Framework commands. They are **not public commands** and are not listed in `docs/prompts/index.md`.

## Contents

| File | Purpose |
|------|---------|
| `init-wave-context.md` | Agent body for Init wave framework |
| `upgrade-wave-context.md` | Agent body for Upgrade wave framework |
| `plan-feature.md` | Agent body for Plan feature |
| `prepare-wave.md` | Agent body for Prepare wave |
| `implement-wave.md` | Agent body for Implement wave |
| `implement-feature.md` | Agent body for Implement feature |
| `review-wave.md` | Agent body for Review wave |
| `close-wave.md` | Agent body for Close wave |
| `finalize-feature.md` | Agent body for Finalize feature |

## Usage

These bodies are consumed during wave execution to provide agents with the project-specific procedure context they need to execute Wave Framework commands correctly against Wavefoundry's repository and workflow configuration.
