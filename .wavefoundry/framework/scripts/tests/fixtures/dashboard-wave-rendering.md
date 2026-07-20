# Wave Record

wave-id: `1test dashboard-wave-rendering`
Title: Dashboard Wave Rendering Fixture

## Objective

This paragraph is deliberately hard wrapped across
four physical source lines so the renderer must join
the lines into one semantic paragraph and let the
browser choose the visual wrapping width.

<!-- wave:context-efficiency begin -->
<!-- wave:context-efficiency state {"tool_calls": 4} -->

## Context Efficiency

Machine-owned markers stay in the raw document but do not become visible
dashboard paragraphs.

<!-- wave:context-efficiency end -->

## Changes

- `1test-enh long-identifier-that-must-wrap-without-page-overflow`
  continues on another physical source line inside the same list item.

| Column | Intrinsically wide content |
| --- | --- |
| table | `a-very-long-table-token-that-may-use-local-overflow-or-wrap` |

```text
<!-- wave:literal-example begin -->
The marker-looking example remains visible inside a fence.
<!-- wave:literal-example end -->
```
