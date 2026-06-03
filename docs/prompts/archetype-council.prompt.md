# Archetype Review

Owner: Engineering
Status: active
Last verified: 2026-06-03

**Shortcut phrases:** `Archetype review` · `Archetype council`

Run a stance-based council review on an artifact whose load-bearing surface is text precision, prose, decision narrative, naming, or AC formulation. Complementary to the role-based Wave Council; optional and operator-invoked.

---

## When to use this

Reach for Archetype Council when the artifact under review is **text precision**, **prose**, **decision narrative**, **naming**, or **AC formulation** — situations where the Wave Council's specialist seats (architecture, security, qa, reality-checker) are in the wrong shape and the role-based lens leaves orthogonal axes unexercised.

Reach for **`red-team`** when a single sharp adversarial challenge is the right shape.

Reach for the **Wave Council** when the artifact is code, architecture, trust-boundary, or implementation-shaped. Wave Council remains mandatory at Prepare wave and Review wave when `wave_review.enabled` is true — Archetype Council does not replace it.

| You need to … | Use this |
|---|---|
| Pressure-test an AC table for testable propositions | **Archetype review** |
| Sharpen a README draft for visitor reception | **Archetype review** (with Hemingway swap) |
| Stress-test an ADR's comparison logic | **Archetype review** (with Munger swap) |
| Get one sharp adversarial challenge before commit | **`red-team`** |
| Satisfy `wave-council-readiness` for Prepare wave | **Wave Council** (`Council review`) — Archetype Council does not record this signoff |
| Review a code change for architecture / security / qa | **Wave Council** (`Council review`) |

---

## What this does

`wave-council` chairs five archetypes, each running in isolation against the artifact, then synthesizes across orthogonal stances. Default seats:

- **Sun Tzu** — strategic positioning; unforced losses; pre-positioning ("what ground is undefended?")
- **Yoda** — cognitive readiness; commitment threshold; reader orientation ("what state must the reader be in?")
- **Spock** — logical precision; testable propositions; falsification ("what evidence would falsify this?")
- **Marcus Aurelius** — durability; dichotomy of control; time-axis; scope-of-self ("will this still be right in 18 months?")
- **Feynman** — essentiality; simplicity from understanding; curse-of-knowledge ("what is the simplest version that still does the job?")

The fifth seat (Feynman) may be swapped when the artifact rewards a different stance. Documented swap-ins:

- **Hemingway** — prose craft; "cut every sentence that doesn't move the story" (prose-heavy artifacts)
- **Charlie Munger** — invert; "what would guarantee this fails?" (decision narratives, ADR comparisons)

Operators may invoke other archetypes ad hoc (e.g., `Archetype review with Da Vinci swapped in for Feynman`). Declare the swap up front so the recorded verdict reflects the actual axes exercised.

---

## How to invoke

1. Provide the artifact: a change doc, AC table, README draft, ADR, naming decision, or any text-precision-heavy surface.
2. State the invocation: `Archetype review` (default five seats) or `Archetype review with <swap-in> swapped in for <default>` (declared swap).
3. The council runs Phase 0 (moderator declaration) → Phase 1 (optional primer) → Phase 2 (seats in isolation) → Phase 3 (synthesis + verdict).
4. Record the verdict line in the artifact's review section.

---

## Verdict line

Structurally consistent with the existing `prepare-council` verdict so future validator integration is straightforward. **No validator consumes this line in v1** — it is forward-compat scaffolding.

```
- **Archetype Council [archetype-review] — <date>: PASS** (moderator: wave-council; seats: sun-tzu, yoda, spock, marcus-aurelius, feynman; rotating-seat: feynman; strongest-axis: <which seat's findings bound the most must-fixes>; must-fix-count: <n>; advisory-count: <n>)
```

Verdict values: **PASS**, **PASS WITH IN-SESSION FIXES**, **NOT READY**.

---

## Worked example

The Archetype Council was first run during wave `1p31b` against `1p318-enh public-launch-surface-doc-rewrite`'s AC-20 / AC-21 (install walkthrough + Python prerequisite). The pass produced five non-overlapping must-fix findings on ACs that two role-based reviews had already cleared:

- **Sun Tzu** added agent-host MCP-support precheck and named disqualifying download patterns.
- **Yoda** added a walkthrough preview line and closed the abandoned-reader loop on prerequisite-fail branches.
- **Spock** bound AC-20 to named operator-visible signals, bound AC-21 to a testable imperative, and declared the MCP-register inline-vs-handoff scope boundary.

The findings are preserved in `1p318`'s Decision Log under "Three-persona review applied to Req-16 / Req-17 / AC-20 / AC-21" and the individual must-fix decision entries. Re-reading the seed's seat descriptions against those finding IDs is the audit trail for protocol drift.

---

## Relationship to other commands

| Command | When to use |
|---|---|
| **Archetype review** | Optional, operator-invoked, stance-based; AC text / prose / decision narrative / naming |
| **`red-team`** | Single adversarial stance, in isolation; or Phase 1 primer to Wave Council |
| **Wave Council** (`Council review`) | Role-based specialist seats; required at Prepare wave / Review wave when `wave_review.enabled`; code / architecture / trust-boundary work |
| **Prepare wave** | Lifecycle gate — Wave Council readiness pass is embedded; records `wave-council-readiness` signoff |
| **Review wave** | Lifecycle gate — Wave Council delivery pass is embedded; records `wave-council-delivery` signoff |
| **Evaluate decision** | Architecture / technology decision specifically — produces an ADR |
| **Interrogate this plan** | Stress-test a plan's unresolved decision branches before admission |

---

## Protocol

See the framework seed `.wavefoundry/framework/seeds/236-archetype-council.prompt.md` for the full protocol: phase shape, seat output schema, moderator synthesis schema, the canonical five seats' stance descriptions, the swap protocol, and the operating invariants.
