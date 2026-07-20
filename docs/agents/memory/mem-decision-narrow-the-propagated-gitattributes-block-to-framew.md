# Decision: **Narrow the propagated `.gitattributes` block** to framewo…

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-narrow-the-propagated-gitattributes-block-to-framew`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p9hm-enh windows-line-endings-and-paths:6c2c5466a944d548`
Validation: reject
Validated by: agent
Action delta: None; historical glob targets cannot be verified as current files, so inspect the present renderer and repository policy directly.
Validation rationale: The generated candidate carries non-file glob targets and fails the current-target proof; preserving it would weaken the validation boundary.
Evidence verified: true
Current target verified: false
Canonical overlap: duplicates
## Summary

Decision (wave 1p9hn): **Narrow the propagated `.gitattributes` block** to framework-rendered paths only (dropped the self-host's broad `* text=auto` / `*.py eol=lf` / global `*.cmd`). Rationale: Those broad rules are correct for the self-host repo (it owns its whole tree) but would OVERREACH into a consuming target repo — forcing the operator's own `*.py`/`*.cmd` line endings and, for an appended `* text=auto`, potentially overriding operator binary declarations (last-match precedence). The narrow set fixes the actual L-2 breakage (LF shebang in `.wavefoundry/bin/*`) without touching the target's sources. Deviation from the change doc's literal entry list; safest-default per org security guidance..

## Evidence

- `1p9hm-enh windows-line-endings-and-paths`
- `1p9hn`

## Targets

- `*.cmd`
- `*.py`
