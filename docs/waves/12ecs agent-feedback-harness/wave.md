# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-06

wave-id: `12ecs agent-feedback-harness`
Title: Agent Feedback Harness

## Objective

Add a complete feedback harness layer to Wavefoundry: post-edit computational sensors, behaviour harness test-generation, architecture/security/performance reviewers as declarable required review lanes, hotfix bypass detection, harnessability assessment, harness coverage metrics, coherence checking across the seed surface, and sensor finding severity triage.

## Changes

Change ID: `12ecs-feat post-edit-computational-sensors`
Change Status: `complete`

Change ID: `12ecs-enh behaviour-harness-test-generation`
Change Status: `complete`

Change ID: `12ecs-enh inferential-sensors-as-required-review-lanes`
Change Status: `complete`

Change ID: `12ecv-feat architecture-reviewer`
Change Status: `complete`

Change ID: `12ed1-feat hotfix-bypass-detection`
Change Status: `complete`

Change ID: `12ed1-feat harnessability-assessment`
Change Status: `complete`

Change ID: `12ed1-feat harness-coverage-metrics`
Change Status: `complete`

Change ID: `12ed1-feat harness-coherence-check`
Change Status: `complete`

Change ID: `12ed1-enh sensor-finding-severity-triage`
Change Status: `complete`

Completed At: 2026-05-06

## Wave Summary

Adds a complete feedback harness layer to Wavefoundry: post-edit computational sensors, behaviour harness test-generation loop, architecture/security/performance reviewers as project-declarable required review lanes, hotfix bypass detection, harnessability assessment, harness coverage metrics, coherence checking across the seed surface, and sensor finding severity triage.

## Journal Watchpoints

- **Watchpoint:** All sensor/lane changes share a `workflow-config.json` schema dependency — `required_review_lanes` and `sensors` config keys must be designed together to avoid conflicting conventions.
- **Watchpoint:** `12ecs-enh inferential-sensors-as-required-review-lanes` and `12ecv-feat architecture-reviewer` both modify `007-review-system-overview.md` and `190-finalize-feature.prompt.md` — implement together or serialize carefully.
- **Watchpoint:** `12ed1-feat harness-coverage-metrics` and `12ed1-enh sensor-finding-severity-triage` depend on the sensors/lanes config schema and seed `214` respectively — implement after those are stable.
- **Watchpoint:** `wave_review_response` and `wave_close_response` are modified by both the inferential sensors change and the severity triage change — coordinate to avoid conflicts.
- **Follow-up:** After this wave ships, evaluate surfacing harnessability and coverage scores in `wave_current` or the MCP status line.

## Review Evidence

- operator-signoff: approved

## Dependencies

- No external wave dependencies.
