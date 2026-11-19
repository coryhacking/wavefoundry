# Delivery Workflow

Owner: Engineering
Status: active
Last verified: 2026-11-18

## Single-Change Delivery Path (Implement spec)

Use **Implement spec** for a single docs-first change that doesn't require multi-workstream coordination:

1. **Plan spec** → author spec
2. **Create wave** → create wave record
3. **Add spec to wave** → admit the single change
4. **Prepare wave** → confirm readiness and repair placement drift if admission left any staged-only docs behind
5. **Implement spec** → implement and run computational verification
6. **Review wave** → independently review delivery
7. **Close spec** (optional) → mark the reviewed change `complete` with `wf_close_change`
8. **Close wave** → closure reconciliation; the only wave close

Full path: Plan spec -> Create wave -> Add spec to wave -> Prepare wave -> Implement spec -> Review wave -> Close spec (per change, optional) -> Close wave.

## Multi-Change Delivery Path (Implement wave)

Use **Implement wave** for multiple admitted changes with dependencies or parallel workstreams:

1. **Plan spec** (repeated for each change) → multiple specs
2. **Create wave** → one wave record for the bundle
3. **Add spec to wave** (repeated) → all changes admitted
4. **Prepare wave** → coordinator confirms all changes ready, repairs any placement drift, and records AC priority
5. **Implement wave** → coordinator manages implementation and computational verification
6. **Review wave** → all required lanes complete
7. **Close wave** → closure reconciliation

## Shortcut: Review Plan

After authoring a spec, use **Review plan** to stress-test unresolved decision branches in that change, or in the current wave record when no change is named. It may run before or after admission, but before implementation. **Interrogate this plan** and **Stress-test this plan** remain natural-language aliases. This optional workflow records no typed signoff and satisfies no lifecycle gate; **Review wave** is the separate delivery step that runs required lanes and records typed evidence.
