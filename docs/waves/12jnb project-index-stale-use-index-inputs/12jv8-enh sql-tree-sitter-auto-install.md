# SQL Tree-Sitter Auto-Install

Change ID: `12jv8-enh sql-tree-sitter-auto-install`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

SQL structural chunking and navigation now support tree-sitter when the grammar is available, but the installer dependency list does not yet pull in the SQL grammar alongside the other tree-sitter packages. That makes SQL support behave differently from the rest of the structurally navigated languages during setup.

## Requirements

1. The index/setup dependency installer should include the SQL tree-sitter grammar package.
2. The existing install flow should continue to auto-install the rest of the tree-sitter grammars as before.
3. The dependency tests should cover the new package so the install list cannot drift.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- related docs if they describe the auto-install list

**Out of scope:**

- Changing SQL chunking or navigation behavior
- Changing the index format or wave lifecycle behavior

## Acceptance Criteria

- SQL grammar is present in the installer dependency list.
- Tests fail if the SQL grammar is removed from the auto-install set.
- Existing dependency handling remains unchanged for the other tree-sitter grammars.

## Tasks

- Add the SQL tree-sitter grammar to the setup dependency list
- Extend the dependency tests to assert the SQL package is included

## AC Priority

| AC | Priority | Rationale |
| -- | -- | -- |
| AC-1 | required | The installer is the actual behavior change |
| AC-2 | required | Regression coverage prevents dependency drift |
| AC-3 | required | Existing setup behavior should remain stable |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The SQL grammar package name differs from the import name | Add coverage for the install string and the import path separately |
| The package is unavailable in some environments | Keep SQL chunking/navigation fallback paths intact |
