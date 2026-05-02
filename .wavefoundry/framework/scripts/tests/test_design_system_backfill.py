"""Tests for design-system install/upgrade backfill logic (AC-7, AC-8).

These tests verify the seeded backfill contract directly — not by calling a
seed prompt but by exercising the backfill helper that seed-010 and seed-160
instruct agents to apply.  The helper is described in the seed and validated
here against the contract spec.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Minimal backfill implementation that mirrors what seed-010 / seed-160 instruct.
# ---------------------------------------------------------------------------

_MANIFEST_STUB = {
    "schemaVersion": "1.0.0",
    "extractionVersion": "1.0.0",
    "extractedAt": None,
    "canonicalRoot": "docs/design",
    "sourceStrategy": "repo-evidence-only",
    "evidenceTypes": [],
    "artifactCounts": {},
    "modes": ["light", "dark"],
    "validationSummary": {"passed": 0, "failed": 0},
}

_GAPS_STUB = (
    "# Design System Gaps\n\n"
    "Generated at install. Fill in during extraction.\n\n"
    "## Summary\n\n"
    "- Critical: 0\n"
    "- Important: 0\n"
    "- Nice-to-have: 0\n\n"
    "## Critical\n\n"
    "## Important\n\n"
    "## Nice-to-have\n\n"
    "## Meta\n"
)

_EXPORTS_README_BODY = (
    "This directory contains generated token outputs (CSS custom properties, "
    "Tailwind theme, TypeScript constants, flat JSON). "
    "These files are **generated** — do not edit them directly.\n\n"
    "## Subdirectories\n\n"
    "- `css/` — CSS custom properties (`tokens.css`)\n"
    "- `tailwind/` — Tailwind theme config (`theme.config.js`)\n"
    "- `ts/` — TypeScript token constants (`tokens.ts`)\n"
    "- `json/` — Flat resolved token map (`tokens.json`)\n\n"
    "## Generating outputs\n\n"
    "Run the token-build pipeline configured in "
    "`.design-system/build.config.json` (see plan `12atj-feat design-token-build-pipeline`).\n"
    "The contents of these subdirectories are **out of scope** for wave `12as1 design-system-extraction`.\n"
)

def _md(title: str, body: str, *, today: str = "2026-01-01") -> str:
    """Return a minimal Wave Framework compliant markdown stub."""
    return (
        f"# {title}\n\n"
        f"Owner: Engineering\n"
        f"Status: stub\n"
        f"Last verified: {today}\n\n"
        f"{body}"
    )


_REQUIRED_FILES: list[tuple[str, str | dict | None]] = [
    ("README.md", None),   # content built dynamically using today's date
    ("DESIGN.md", None),
    ("AGENTS.md", None),   # content set separately
    ("manifest.json", _MANIFEST_STUB),
    ("VALIDATION.md", None),
    ("gaps.md", _GAPS_STUB),
    ("tokens/primitives.tokens.json", {}),
    ("tokens/semantic.tokens.json", {}),
    ("tokens/components.tokens.json", {}),
    ("tokens/modes/light.tokens.json", {}),
    ("tokens/modes/dark.tokens.json", {}),
    ("tokens/README.md", None),
    ("exports/README.md", None),   # content built dynamically using today's date
    ("exports/css/.keep", ""),
    ("exports/tailwind/.keep", ""),
    ("exports/ts/.keep", ""),
    ("exports/json/.keep", ""),
    ("components/_index.json", {"components": []}),
    ("foundations/color.md", None),
    ("foundations/typography.md", None),
    ("foundations/spacing.md", None),
    ("foundations/radius.md", None),
    ("foundations/elevation.md", None),
    ("foundations/motion.md", None),
    ("accessibility/contrast-report.json", {"checks": []}),
    ("accessibility/README.md", None),
    (".design-system/version.json", {"schemaVersion": "1.0.0"}),
    (".design-system/source-map.json", []),
    (".design-system/proposed-additions.md", None),
]

_DYNAMIC_MD: dict[str, tuple[str, str]] = {
    "README.md":         ("Design System", "Machine-readable extraction contract.\n"),
    "DESIGN.md":         ("DESIGN", "<!-- Generated — do not edit directly. -->\n"),
    "VALIDATION.md":     ("Validation", "Populate after first extraction run.\n"),
    "tokens/README.md":  ("Tokens", "DTCG-format token files.\n"),
    "exports/README.md": ("exports/", _EXPORTS_README_BODY),
    "foundations/color.md":      ("Color", ""),
    "foundations/typography.md": ("Typography", ""),
    "foundations/spacing.md":    ("Spacing", ""),
    "foundations/radius.md":     ("Radius", ""),
    "foundations/elevation.md":  ("Elevation", ""),
    "foundations/motion.md":     ("Motion", ""),
    "accessibility/README.md":   ("Accessibility", ""),
    ".design-system/proposed-additions.md": ("Proposed Additions", ""),
}

_AGENTS_MD_BODY = """\
## Before building any UI component
1. Check `components/_index.json` — use an existing component if one matches.
2. Never create a duplicate component without checking the index first.
3. If no match exists, append a proposal to `.design-system/proposed-additions.md`.

## Before writing any hard-coded value
1. Check `tokens/semantic.tokens.json` for the appropriate semantic token.
2. Reference semantic tokens only — never primitives or raw hex/px/z-index/duration.
3. Token naming follows dot-path convention: `category.subcategory.scale.variant`.

## Token usage
- Use semantic token references (`{color.action.primary.background}`), not raw values.
- Never bypass semantic layer to reference primitives directly.
- Never use raw hex codes, px values, z-index integers, or duration ms in component code.

## Extract, don't invent
- When source evidence is missing, record `null` + a `gaps.md` entry.
- Do not silently default to a value not found in evidence.
- Low-confidence items (`source-map.json` confidence: low) must have a corresponding gap.

<!-- Split B will extend this file with: microcopy lookup rules (content/microcopy.json),
     icon lookup rules (icons/_index.json), form validation rules, state pattern rules. -->
"""


def _backfill(design_root: Path, existing_manifest: dict | None = None, today: str | None = None) -> None:
    """Minimal backfill that mirrors the seed-010 / seed-160 contract."""
    import datetime
    _today = today or datetime.date.today().isoformat()
    for rel, content in _REQUIRED_FILES:
        path = design_root / rel
        if path.exists():
            continue  # merge-safe: never overwrite
        path.parent.mkdir(parents=True, exist_ok=True)
        if rel == "AGENTS.md":
            path.write_text(_md("Design System Agent Rules", _AGENTS_MD_BODY, today=_today), encoding="utf-8")
        elif isinstance(content, (dict, list)):
            path.write_text(json.dumps(content, indent=2), encoding="utf-8")
        elif content is None:
            # Dynamic markdown stub: include Wave Framework metadata header
            if rel in _DYNAMIC_MD:
                title, body = _DYNAMIC_MD[rel]
                path.write_text(_md(title, body, today=_today), encoding="utf-8")
            else:
                path.write_text("", encoding="utf-8")
        else:
            path.write_text(content, encoding="utf-8")

    # seed-160: schema version reconciliation
    if existing_manifest is not None:
        manifest_path = design_root / "manifest.json"
        if manifest_path.exists():
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            added = []
            for field, default in _MANIFEST_STUB.items():
                if field not in data:
                    data[field] = default
                    added.append(field)
            if added:
                manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                # Append meta gap entry
                gaps_path = design_root / "gaps.md"
                if gaps_path.exists():
                    gaps_text = gaps_path.read_text(encoding="utf-8")
                    entry = (
                        f"\n### [meta] Schema fields added by upgrade: {', '.join(added)}\n"
                        "**Severity:** nice-to-have\n"
                        "**Recommended action:** Review added fields and populate as needed.\n"
                    )
                    gaps_path.write_text(gaps_text + entry, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class InstallBackfillTests(unittest.TestCase):
    """AC-7: install creates all required paths when docs/design/ is absent."""

    def test_backfill_creates_all_required_paths(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            design_root = root / "docs" / "design"
            design_root.mkdir(parents=True)
            _backfill(design_root)
            for rel, _ in _REQUIRED_FILES:
                path = design_root / rel
                # .keep files mean the directory exists
                if rel.endswith("/.keep"):
                    self.assertTrue(path.parent.exists(), f"Directory missing: {rel}")
                else:
                    self.assertTrue(path.exists(), f"Required path missing after backfill: {rel}")

    def test_backfill_does_not_overwrite_existing_files(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            design_root = root / "docs" / "design"
            design_root.mkdir(parents=True)

            # Pre-create gaps.md with operator content
            original = "# My Custom Gaps\n\nImportant stuff.\n"
            gaps_path = design_root / "gaps.md"
            gaps_path.parent.mkdir(parents=True, exist_ok=True)
            gaps_path.write_text(original, encoding="utf-8")

            _backfill(design_root)

            # Operator content must be byte-identical after backfill
            self.assertEqual(gaps_path.read_text(encoding="utf-8"), original)

    def test_backfill_design_language_md_is_never_touched(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            design_root = root / "docs" / "design"
            design_root.mkdir(parents=True)

            original = "# Design Language\n\nOperator-owned narrative.\n"
            dl_path = design_root / "design-language.md"
            dl_path.write_text(original, encoding="utf-8")

            _backfill(design_root)

            self.assertEqual(dl_path.read_text(encoding="utf-8"), original)

    def test_exports_subdirs_exist_after_backfill(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            design_root = root / "docs" / "design"
            design_root.mkdir(parents=True)
            _backfill(design_root)
            for subdir in ("css", "tailwind", "ts", "json"):
                self.assertTrue((design_root / "exports" / subdir).exists())

    def test_exports_readme_mentions_pipeline(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            design_root = root / "docs" / "design"
            design_root.mkdir(parents=True)
            _backfill(design_root)
            readme = (design_root / "exports" / "README.md").read_text(encoding="utf-8")
            self.assertIn("12atj-feat design-token-build-pipeline", readme)

    def test_manifest_json_has_required_fields(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            design_root = root / "docs" / "design"
            design_root.mkdir(parents=True)
            _backfill(design_root)
            data = json.loads((design_root / "manifest.json").read_text(encoding="utf-8"))
            for field in ("schemaVersion", "canonicalRoot", "sourceStrategy", "modes"):
                self.assertIn(field, data, f"manifest.json missing field: {field}")

    def test_agents_md_contains_required_rules(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            design_root = root / "docs" / "design"
            design_root.mkdir(parents=True)
            _backfill(design_root)
            content = (design_root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("_index.json", content)
            self.assertIn("proposed-additions.md", content)
            self.assertIn("semantic tokens", content)
            self.assertIn("Split B", content)


class UpgradeBackfillTests(unittest.TestCase):
    """AC-8: upgrade backfill adds missing schema fields and logs meta gap."""

    def test_upgrade_adds_missing_manifest_fields(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            design_root = root / "docs" / "design"
            design_root.mkdir(parents=True)

            # Create a stale manifest missing several fields
            stale = {
                "schemaVersion": "0.9.0",
                "canonicalRoot": "docs/design",
            }
            manifest_path = design_root / "manifest.json"
            manifest_path.write_text(json.dumps(stale), encoding="utf-8")
            gaps_path = design_root / "gaps.md"
            gaps_path.write_text(_GAPS_STUB, encoding="utf-8")

            _backfill(design_root, existing_manifest=stale)

            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertIn("sourceStrategy", data)
            self.assertIn("evidenceTypes", data)

    def test_upgrade_appends_meta_gap_when_fields_added(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            design_root = root / "docs" / "design"
            design_root.mkdir(parents=True)

            stale = {"schemaVersion": "0.9.0", "canonicalRoot": "docs/design"}
            manifest_path = design_root / "manifest.json"
            manifest_path.write_text(json.dumps(stale), encoding="utf-8")
            gaps_path = design_root / "gaps.md"
            gaps_path.write_text(_GAPS_STUB, encoding="utf-8")

            _backfill(design_root, existing_manifest=stale)

            gaps_text = gaps_path.read_text(encoding="utf-8")
            self.assertIn("[meta]", gaps_text)

    def test_upgrade_does_not_overwrite_existing_fields(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            design_root = root / "docs" / "design"
            design_root.mkdir(parents=True)

            existing = dict(_MANIFEST_STUB, canonicalRoot="docs/design", schemaVersion="1.0.0")
            manifest_path = design_root / "manifest.json"
            manifest_path.write_text(json.dumps(existing), encoding="utf-8")
            gaps_path = design_root / "gaps.md"
            gaps_path.write_text(_GAPS_STUB, encoding="utf-8")

            _backfill(design_root, existing_manifest=existing)

            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(data["canonicalRoot"], "docs/design")
            self.assertEqual(data["schemaVersion"], "1.0.0")


if __name__ == "__main__":
    unittest.main()
