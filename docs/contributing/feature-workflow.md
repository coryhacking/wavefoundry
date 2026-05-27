# Feature Workflow

Owner: Engineering
Status: active
Last verified: 2026-05-26

## Single-Change Delivery Path (Implement feature)

Use **Implement feature** for a single docs-first change that doesn't require multi-workstream coordination:

1. **Plan feature** → author change doc
2. **Create wave** → create wave record
3. **Add change to wave** → admit the single change
4. **Prepare wave** → confirm readiness and repair placement drift if admission left any staged-only docs behind
5. **Implement feature** → implement and review in one pass
6. **Finalize feature** → close the wave

## Multi-Change Delivery Path (Implement wave)

Use **Implement wave** for multiple admitted changes with dependencies or parallel workstreams:

1. **Plan feature** (repeated for each change) → multiple change docs
2. **Create wave** → one wave record for the bundle
3. **Add change to wave** (repeated) → all changes admitted
4. **Prepare wave** → coordinator confirms all changes ready, repairs any placement drift, and records AC priority
5. **Implement wave** → coordinator manages execution; reviewers participate during implementation
6. **Review wave** → all required lanes complete
7. **Close wave** → closure reconciliation

## Shortcut: Interrogate Plan

After authoring a change doc, use **Interrogate this plan** to stress-test all unresolved decision branches before admission. This is optional but recommended for complex or high-risk changes.
