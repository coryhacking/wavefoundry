"""Tests for wave_lint_lib/design_system_governance_validators.py (Requirement 13)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))

from wave_lint_lib.design_system_governance_validators import check_design_governance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_design_root(tmp: Path) -> Path:
    """Create a minimal valid docs/design/ tree for governance tests."""
    d = tmp / "docs" / "design"

    _write_json(
        d / "manifest.json",
        {
            "schemaVersion": "1.0.0",
            "canonicalRoot": "docs/design",
            "sourceStrategy": "repo-evidence-only",
            "targetSurfaces": ["web"],
        },
    )
    _write_json(d / "components" / "_index.json", {"components": []})
    _write_json(d / "tokens" / "semantic.tokens.json", {})
    _write_json(d / ".design-system" / "source-map.json", [])

    return d


# ---------------------------------------------------------------------------
# No manifest.json → no-op
# ---------------------------------------------------------------------------

class NoManifestTests(unittest.TestCase):
    def test_skips_when_missing(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "docs" / "design").mkdir(parents=True, exist_ok=True)
            failures, warnings = check_design_governance(root)
            self.assertEqual(failures, [])
            self.assertEqual(warnings, [])


# ---------------------------------------------------------------------------
# 1. sourceStrategy enum check
# ---------------------------------------------------------------------------

class SourceStrategyEnumTests(unittest.TestCase):
    def test_passes_on_valid_input(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            for strategy in ("figma-extract", "repo-evidence-only", "visual-bootstrap", "hybrid"):
                manifest_path = root / "docs" / "design" / "manifest.json"
                data = json.loads(manifest_path.read_text())
                data["sourceStrategy"] = strategy
                _write_json(manifest_path, data)
                failures, _ = check_design_governance(root)
                self.assertFalse(
                    any("sourceStrategy" in f for f in failures),
                    f"Expected no sourceStrategy failure for '{strategy}', got: {failures}",
                )

    def test_fails_on_invalid_input(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "manifest.json",
                {
                    "schemaVersion": "1.0.0",
                    "canonicalRoot": "docs/design",
                    "sourceStrategy": "magic-bootstrap",
                    "targetSurfaces": ["web"],
                },
            )
            failures, _ = check_design_governance(root)
            self.assertTrue(
                any("sourceStrategy" in f and "magic-bootstrap" in f for f in failures),
                f"Expected sourceStrategy failure, got: {failures}",
            )

    def test_skips_when_missing(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            # Remove sourceStrategy field entirely
            _write_json(
                d / "manifest.json",
                {
                    "schemaVersion": "1.0.0",
                    "canonicalRoot": "docs/design",
                    "targetSurfaces": ["web"],
                },
            )
            failures, _ = check_design_governance(root)
            self.assertFalse(
                any("sourceStrategy" in f for f in failures),
                f"Expected no sourceStrategy failure when field absent, got: {failures}",
            )


# ---------------------------------------------------------------------------
# 2. targetSurfaces non-empty check
# ---------------------------------------------------------------------------

class TargetSurfacesTests(unittest.TestCase):
    def test_passes_on_valid_input(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            # Default helper sets targetSurfaces: ["web"]
            _, warnings = check_design_governance(root)
            self.assertFalse(
                any("targetSurfaces" in w for w in warnings),
                f"Expected no targetSurfaces warning, got: {warnings}",
            )

    def test_fails_on_invalid_input(self):
        """Empty targetSurfaces list produces a warning."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "manifest.json",
                {
                    "schemaVersion": "1.0.0",
                    "canonicalRoot": "docs/design",
                    "sourceStrategy": "repo-evidence-only",
                    "targetSurfaces": [],
                },
            )
            _, warnings = check_design_governance(root)
            self.assertTrue(
                any("targetSurfaces is empty" in w for w in warnings),
                f"Expected targetSurfaces empty warning, got: {warnings}",
            )

    def test_skips_when_missing(self):
        """Missing targetSurfaces key produces a different warning (not a failure)."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "manifest.json",
                {
                    "schemaVersion": "1.0.0",
                    "canonicalRoot": "docs/design",
                    "sourceStrategy": "repo-evidence-only",
                },
            )
            failures, warnings = check_design_governance(root)
            self.assertEqual(failures, [])
            self.assertTrue(
                any("targetSurfaces missing" in w for w in warnings),
                f"Expected targetSurfaces missing warning, got: {warnings}",
            )


# ---------------------------------------------------------------------------
# 3. platformStandards referenceVersion check
# ---------------------------------------------------------------------------

class PlatformStandardsRefVersionTests(unittest.TestCase):
    def test_passes_on_valid_input(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "manifest.json",
                {
                    "schemaVersion": "1.0.0",
                    "canonicalRoot": "docs/design",
                    "sourceStrategy": "repo-evidence-only",
                    "targetSurfaces": ["web", "ios"],
                    "platformStandards": [
                        {"surface": "ios", "referenceVersion": "HIG-2024"},
                        {"surface": "android", "referenceVersion": "MD3"},
                    ],
                },
            )
            _, warnings = check_design_governance(root)
            self.assertFalse(
                any("referenceVersion" in w for w in warnings),
                f"Expected no referenceVersion warnings, got: {warnings}",
            )

    def test_fails_on_invalid_input(self):
        """Entry without referenceVersion produces a warning."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "manifest.json",
                {
                    "schemaVersion": "1.0.0",
                    "canonicalRoot": "docs/design",
                    "sourceStrategy": "repo-evidence-only",
                    "targetSurfaces": ["web", "ios"],
                    "platformStandards": [
                        {"surface": "ios"},  # no referenceVersion
                    ],
                },
            )
            _, warnings = check_design_governance(root)
            self.assertTrue(
                any("referenceVersion" in w and "ios" in w for w in warnings),
                f"Expected referenceVersion warning for ios, got: {warnings}",
            )

    def test_skips_when_missing(self):
        """No platformStandards key → no referenceVersion warnings."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            # Default helper has no platformStandards
            _, warnings = check_design_governance(root)
            self.assertFalse(
                any("referenceVersion" in w for w in warnings),
                f"Expected no referenceVersion warnings when platformStandards absent, got: {warnings}",
            )

    def test_null_referenceVersion_produces_warning(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "manifest.json",
                {
                    "schemaVersion": "1.0.0",
                    "canonicalRoot": "docs/design",
                    "sourceStrategy": "repo-evidence-only",
                    "targetSurfaces": ["web"],
                    "platformStandards": [
                        {"surface": "android", "referenceVersion": None},
                    ],
                },
            )
            _, warnings = check_design_governance(root)
            self.assertTrue(
                any("referenceVersion" in w and "android" in w for w in warnings),
                f"Expected referenceVersion warning for null value, got: {warnings}",
            )


# ---------------------------------------------------------------------------
# 4. visual-bootstrap proposal guard
# ---------------------------------------------------------------------------

class VisualBootstrapProposalGuardTests(unittest.TestCase):
    def test_passes_on_valid_input(self):
        """visual-bootstrap with no proposed entries in source-map passes."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "manifest.json",
                {
                    "schemaVersion": "1.0.0",
                    "canonicalRoot": "docs/design",
                    "sourceStrategy": "visual-bootstrap",
                    "targetSurfaces": ["web"],
                },
            )
            # source-map has entries but none are proposed
            _write_json(
                d / ".design-system" / "source-map.json",
                [{"id": "color", "confidence": "high"}],
            )
            # semantic has the same key but source-map entry is not proposed
            _write_json(d / "tokens" / "semantic.tokens.json", {"color": {"$value": "#fff"}})
            failures, _ = check_design_governance(root)
            self.assertFalse(
                any("proposed-from-best-practices" in f for f in failures),
                f"Expected no proposal guard failures, got: {failures}",
            )

    def test_fails_on_invalid_input(self):
        """Proposed entry in source-map that is also in semantic.tokens.json fails."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "manifest.json",
                {
                    "schemaVersion": "1.0.0",
                    "canonicalRoot": "docs/design",
                    "sourceStrategy": "visual-bootstrap",
                    "targetSurfaces": ["web"],
                },
            )
            _write_json(
                d / ".design-system" / "source-map.json",
                [
                    {
                        "id": "spacing",
                        "confidence": "proposed",
                    }
                ],
            )
            # "spacing" is also a top-level key in semantic tokens
            _write_json(
                d / "tokens" / "semantic.tokens.json",
                {"spacing": {"$value": "4px"}},
            )
            failures, _ = check_design_governance(root)
            self.assertTrue(
                any("spacing" in f and "proposed-from-best-practices" in f for f in failures),
                f"Expected proposal guard failure for 'spacing', got: {failures}",
            )

    def test_fails_on_extensions_flag(self):
        """Entry with $extensions.proposed-from-best-practices: true that is in semantic fails."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "manifest.json",
                {
                    "schemaVersion": "1.0.0",
                    "canonicalRoot": "docs/design",
                    "sourceStrategy": "visual-bootstrap",
                    "targetSurfaces": ["web"],
                },
            )
            _write_json(
                d / ".design-system" / "source-map.json",
                [
                    {
                        "id": "radius",
                        "$extensions": {"proposed-from-best-practices": True},
                    }
                ],
            )
            _write_json(d / "tokens" / "semantic.tokens.json", {"radius": {"$value": "4px"}})
            failures, _ = check_design_governance(root)
            self.assertTrue(
                any("radius" in f and "proposed-from-best-practices" in f for f in failures),
                f"Expected proposal guard failure for 'radius', got: {failures}",
            )

    def test_skips_when_missing(self):
        """Non-visual-bootstrap strategy skips the proposal guard."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            # Default helper uses repo-evidence-only
            failures, _ = check_design_governance(root)
            self.assertFalse(
                any("proposed-from-best-practices" in f for f in failures),
                f"Expected no proposal guard failures for non-visual-bootstrap, got: {failures}",
            )

    def test_skips_when_semantic_empty(self):
        """visual-bootstrap with empty semantic.tokens.json skips the check."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "manifest.json",
                {
                    "schemaVersion": "1.0.0",
                    "canonicalRoot": "docs/design",
                    "sourceStrategy": "visual-bootstrap",
                    "targetSurfaces": ["web"],
                },
            )
            _write_json(
                d / ".design-system" / "source-map.json",
                [{"id": "color", "confidence": "proposed"}],
            )
            # Empty semantic tokens → check is skipped
            _write_json(d / "tokens" / "semantic.tokens.json", {})
            failures, _ = check_design_governance(root)
            self.assertFalse(
                any("proposed-from-best-practices" in f for f in failures),
                f"Expected no failure when semantic tokens empty, got: {failures}",
            )


# ---------------------------------------------------------------------------
# 5. Deprecated component check
# ---------------------------------------------------------------------------

class DeprecatedComponentTests(unittest.TestCase):
    def test_passes_on_valid_input(self):
        """Deprecated component with supersededBy passes."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "components" / "_index.json",
                {
                    "components": [
                        {"id": "old-button", "deprecated": True, "supersededBy": "button"},
                    ]
                },
            )
            failures, _ = check_design_governance(root)
            self.assertFalse(
                any("old-button" in f for f in failures),
                f"Expected no deprecated failure when supersededBy present, got: {failures}",
            )

    def test_passes_with_sunset(self):
        """Deprecated component with sunset date passes."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "components" / "_index.json",
                {
                    "components": [
                        {"id": "legacy-card", "deprecated": True, "sunset": "2027-01-01"},
                    ]
                },
            )
            failures, _ = check_design_governance(root)
            self.assertFalse(
                any("legacy-card" in f for f in failures),
                f"Expected no deprecated failure when sunset present, got: {failures}",
            )

    def test_fails_on_invalid_input(self):
        """Deprecated component without supersededBy or sunset fails."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "components" / "_index.json",
                {
                    "components": [
                        {"id": "bare-deprecated", "deprecated": True},
                    ]
                },
            )
            failures, _ = check_design_governance(root)
            self.assertTrue(
                any("bare-deprecated" in f and "supersededBy or sunset" in f for f in failures),
                f"Expected deprecated component failure, got: {failures}",
            )

    def test_skips_when_missing(self):
        """No _index.json → no deprecated component failures."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            (d / "components" / "_index.json").unlink()
            failures, _ = check_design_governance(root)
            self.assertFalse(
                any("supersededBy or sunset" in f for f in failures),
                f"Expected no deprecated failures when _index.json absent, got: {failures}",
            )

    def test_non_deprecated_not_flagged(self):
        """Components without deprecated: true are not flagged."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "components" / "_index.json",
                {
                    "components": [
                        {"id": "button"},
                        {"id": "input", "deprecated": False},
                    ]
                },
            )
            failures, _ = check_design_governance(root)
            self.assertFalse(
                any("supersededBy or sunset" in f for f in failures),
                f"Expected no deprecated failures for non-deprecated components, got: {failures}",
            )


# ---------------------------------------------------------------------------
# 6. per-surface deltas files exist
# ---------------------------------------------------------------------------

class PlatformStandardsOverridesTests(unittest.TestCase):
    def test_passes_on_valid_input(self):
        """platformStandards overrides path that exists passes."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            overrides_file = root / "docs" / "design" / "platforms" / "ios.json"
            _write_json(overrides_file, {})
            _write_json(
                d / "manifest.json",
                {
                    "schemaVersion": "1.0.0",
                    "canonicalRoot": "docs/design",
                    "sourceStrategy": "repo-evidence-only",
                    "targetSurfaces": ["web", "ios"],
                    "platformStandards": [
                        {
                            "surface": "ios",
                            "referenceVersion": "HIG-2024",
                            "overrides": "docs/design/platforms/ios.json",
                        }
                    ],
                },
            )
            failures, _ = check_design_governance(root)
            self.assertFalse(
                any("overrides" in f for f in failures),
                f"Expected no overrides failure when file exists, got: {failures}",
            )

    def test_fails_on_invalid_input(self):
        """platformStandards overrides path that does not exist fails."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "manifest.json",
                {
                    "schemaVersion": "1.0.0",
                    "canonicalRoot": "docs/design",
                    "sourceStrategy": "repo-evidence-only",
                    "targetSurfaces": ["web", "android"],
                    "platformStandards": [
                        {
                            "surface": "android",
                            "referenceVersion": "MD3",
                            "overrides": "docs/design/platforms/android.json",
                        }
                    ],
                },
            )
            # File does NOT exist
            failures, _ = check_design_governance(root)
            self.assertTrue(
                any(
                    "android" in f and "docs/design/platforms/android.json" in f
                    for f in failures
                ),
                f"Expected overrides path failure, got: {failures}",
            )

    def test_skips_when_missing(self):
        """No platformStandards → no overrides failures."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            failures, _ = check_design_governance(root)
            self.assertFalse(
                any(".overrides" in f or "overrides path" in f for f in failures),
                f"Expected no overrides failures when platformStandards absent, got: {failures}",
            )

    def test_entry_without_overrides_key_passes(self):
        """platformStandards entry with no overrides field produces no failure."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            d = _make_design_root(root)
            _write_json(
                d / "manifest.json",
                {
                    "schemaVersion": "1.0.0",
                    "canonicalRoot": "docs/design",
                    "sourceStrategy": "repo-evidence-only",
                    "targetSurfaces": ["web"],
                    "platformStandards": [
                        {"surface": "web", "referenceVersion": "WCAG-2.2"},
                    ],
                },
            )
            failures, _ = check_design_governance(root)
            self.assertFalse(
                any("overrides" in f for f in failures),
                f"Expected no overrides failure for entry without overrides key, got: {failures}",
            )


if __name__ == "__main__":
    unittest.main()
