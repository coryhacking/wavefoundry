# Package Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-04-30

Shortcut: **`Package Wavefoundry`** | Legacy: **`Package wave framework`** / **`Package wave context`**

## Purpose

Build a dated distribution zip of the canonical framework tree so other repositories can adopt it through **Upgrade wave framework**.

## Run

From the repository root:

```bash
python3 .wavefoundry/framework/scripts/build_pack.py
```

## Required Packaging Order

1. Ensure intended framework changes are already complete.
2. Run framework tests:

```bash
python3 -B .wavefoundry/framework/scripts/run_tests.py
```

3. Run the packaging command once. It stamps `.wavefoundry/framework/VERSION`, rebuilds `.wavefoundry/framework/index/` by default, and creates the zip.
4. Review the produced zip name and stamped `VERSION` for consistency.
5. Hand off diff + suggested commit message unless the operator explicitly asks to finalize the commit in this request.

## Output

The command writes a zip at repository root:

```text
wavefoundry-YYYY-MM-DDx.zip
```

- `YYYY-MM-DD` defaults to today's local date unless `--date` is provided.
- `x` is the next letter after the highest existing suffix for that date in the output directory.
- `VERSION` is stamped to the same `<YYYY-MM-DD><letter>` revision before zip creation.

## Options

- `--output <dir>`: write zip to an existing directory.
- `--date <YYYY-MM-DD>`: override date for filename, suffix scan, and `VERSION` stamp (tests/exceptional rebuilds only).
- `--skip-framework-index`: skip rebuilding `.wavefoundry/framework/index/` (emergency use only).

## Upgrade Path Coverage

After packaging, target repositories should consume the pack via **Upgrade wave framework** so the upgrade flow can:

- adopt the latest root `wavefoundry-*.zip` (Step 0),
- regenerate host surfaces (`.cursor/mcp.json`, `.mcp.json`, `.junie/mcp/mcp.json`) through `render_platform_surfaces.py`,
- keep `.wavefoundry/bin/docs-lint` and `.wavefoundry/bin/docs-gardener` aligned with the packaged scripts,
- validate MCP recovery paths (`wave_audit`, `wave_index_build`) plus docs gate.

## Notes

- Zip archives at repository root are transport artifacts; do not commit them.
- Use **Upgrade wave framework** (not init) in already-seeded target repositories.
