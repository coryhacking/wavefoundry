"""Tests for wave_lint_lib/design_system_surface_validators.py (Requirement 13, Split B)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))

from wave_lint_lib.design_system_surface_validators import check_design_surface


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_design_root(tmp: str) -> Path:
    """Create docs/design/ with minimal stubs so validators don't trip on missing core paths."""
    root = Path(tmp)
    d = root / "docs" / "design"

    # Mode token files (empty stubs)
    _write_json(d / "tokens" / "modes" / "light.tokens.json", {})
    _write_json(d / "tokens" / "modes" / "dark.tokens.json", {})

    # Accessibility stub
    _write_json(d / "accessibility" / "contrast-report.json", {"checks": []})

    # Components directory
    (d / "components").mkdir(parents=True, exist_ok=True)

    return d


# ---------------------------------------------------------------------------
# Validator 1: WCAG contrast check
# ---------------------------------------------------------------------------

class WcagContrastTests(unittest.TestCase):
    def test_wcag_contrast_passes_on_valid_input(self):
        """All checks passed=true → no failures or warnings."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            _write_json(d / "accessibility" / "contrast-report.json", {
                "checks": [
                    {"id": "text-on-bg", "passed": True, "level": "AA"},
                    {"id": "icon-on-bg", "passed": True, "level": "AAA"},
                ]
            })
            failures, warnings = check_design_surface(Path(t))
            self.assertFalse(
                any("contrast-report.json" in f for f in failures),
                f"Unexpected failures: {failures}",
            )
            self.assertFalse(
                any("contrast-report.json" in w for w in warnings),
                f"Unexpected warnings: {warnings}",
            )

    def test_wcag_contrast_fails_on_invalid_input(self):
        """A check with passed=false and level=AA → failure."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            _write_json(d / "accessibility" / "contrast-report.json", {
                "checks": [
                    {"id": "text-on-bg", "passed": False, "level": "AA"},
                ]
            })
            failures, warnings = check_design_surface(Path(t))
            self.assertTrue(
                any("WCAG AA failure for 'text-on-bg'" in f for f in failures),
                f"Expected AA failure, got: {failures}",
            )

    def test_wcag_contrast_fails_aaa(self):
        """A check with passed=false and level=AAA → failure."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            _write_json(d / "accessibility" / "contrast-report.json", {
                "checks": [
                    {"id": "icon-contrast", "passed": False, "level": "AAA"},
                ]
            })
            failures, _ = check_design_surface(Path(t))
            self.assertTrue(
                any("WCAG AAA failure for 'icon-contrast'" in f for f in failures),
                f"Expected AAA failure, got: {failures}",
            )

    def test_wcag_contrast_unknown_level_is_warning(self):
        """A check with passed=false and unknown level → warning, not failure."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            _write_json(d / "accessibility" / "contrast-report.json", {
                "checks": [
                    {"id": "some-check", "passed": False, "level": "A"},
                ]
            })
            failures, warnings = check_design_surface(Path(t))
            self.assertFalse(
                any("contrast-report.json" in f for f in failures),
                f"Unexpected failure for unknown level: {failures}",
            )
            self.assertTrue(
                any("contrast-report.json" in w for w in warnings),
                f"Expected warning for unknown level, got: {warnings}",
            )

    def test_wcag_contrast_skips_when_file_missing(self):
        """No docs/design/ directory → empty result."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "docs").mkdir()
            failures, warnings = check_design_surface(root)
            self.assertEqual(failures, [])
            self.assertEqual(warnings, [])

    def test_wcag_contrast_skips_empty_stub(self):
        """contrast-report.json with empty checks list → skip silently."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            _write_json(d / "accessibility" / "contrast-report.json", {"checks": []})
            failures, warnings = check_design_surface(Path(t))
            self.assertFalse(any("contrast-report.json" in f for f in failures))
            self.assertFalse(any("contrast-report.json" in w for w in warnings))

    def test_wcag_contrast_skips_empty_object_stub(self):
        """contrast-report.json as {} → skip silently."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            _write_json(d / "accessibility" / "contrast-report.json", {})
            failures, warnings = check_design_surface(Path(t))
            self.assertFalse(any("contrast-report.json" in f for f in failures))
            self.assertFalse(any("contrast-report.json" in w for w in warnings))


# ---------------------------------------------------------------------------
# Validator 2: Extended mode parity
# ---------------------------------------------------------------------------

class ExtendedModeParityTests(unittest.TestCase):
    def test_extended_mode_parity_passes_on_valid_input(self):
        """Extended token file keys present in both light and dark → no failures."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            token_data = {
                "border": {
                    "radius": {"sm": {"$value": "4px", "$type": "dimension"}}
                }
            }
            _write_json(d / "tokens" / "borders.tokens.json", token_data)
            _write_json(d / "tokens" / "modes" / "light.tokens.json", token_data)
            _write_json(d / "tokens" / "modes" / "dark.tokens.json", token_data)
            failures, _ = check_design_surface(Path(t))
            self.assertFalse(
                any("borders.tokens.json" in f for f in failures),
                f"Unexpected failures: {failures}",
            )

    def test_extended_mode_parity_fails_on_invalid_input(self):
        """Key in extended file but missing from light.tokens.json → failure."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            ext_data = {
                "border": {
                    "radius": {"sm": {"$value": "4px", "$type": "dimension"}}
                }
            }
            _write_json(d / "tokens" / "borders.tokens.json", ext_data)
            # light and dark remain as {}
            failures, _ = check_design_surface(Path(t))
            self.assertTrue(
                any("borders.tokens.json" in f and "border.radius.sm" in f for f in failures),
                f"Expected mode parity failure, got: {failures}",
            )

    def test_extended_mode_parity_skips_when_file_missing(self):
        """No docs/design/ → empty result."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "docs").mkdir()
            failures, warnings = check_design_surface(root)
            self.assertEqual(failures, [])
            self.assertEqual(warnings, [])

    def test_extended_mode_parity_skips_empty_extended_file(self):
        """Extended file is empty dict → skip silently."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            _write_json(d / "tokens" / "focus.tokens.json", {})
            failures, _ = check_design_surface(Path(t))
            self.assertFalse(
                any("focus.tokens.json" in f for f in failures),
                f"Unexpected failure on empty extended file: {failures}",
            )

    def test_extended_mode_parity_missing_from_dark(self):
        """Key present in extended and light but missing from dark → failure."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            ext_data = {
                "z": {"modal": {"$value": "100", "$type": "number"}}
            }
            _write_json(d / "tokens" / "z-index.tokens.json", ext_data)
            _write_json(d / "tokens" / "modes" / "light.tokens.json", ext_data)
            # dark remains {}
            failures, _ = check_design_surface(Path(t))
            self.assertTrue(
                any("z-index.tokens.json" in f and "dark.tokens.json" in f for f in failures),
                f"Expected dark mode failure, got: {failures}",
            )


# ---------------------------------------------------------------------------
# Validator 3: Reduced-motion check
# ---------------------------------------------------------------------------

class ReducedMotionTests(unittest.TestCase):
    def test_reduced_motion_passes_on_valid_input(self):
        """Non-null motion tokens + media-motion.md present → no failures.

        Mode files must also contain the motion token keys to satisfy the
        extended mode parity validator (motion.tokens.json is an extended file).
        """
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            motion_data = {
                "motion": {
                    "duration": {"fast": {"$value": "100ms", "$type": "duration"}}
                }
            }
            _write_json(d / "tokens" / "motion.tokens.json", motion_data)
            _write_json(d / "tokens" / "modes" / "light.tokens.json", motion_data)
            _write_json(d / "tokens" / "modes" / "dark.tokens.json", motion_data)
            _write_text(d / "foundations" / "media-motion.md", "# Reduced Motion\n")
            failures, _ = check_design_surface(Path(t))
            self.assertFalse(
                any("media-motion.md" in f for f in failures),
                f"Unexpected failures: {failures}",
            )

    def test_reduced_motion_fails_on_invalid_input(self):
        """Non-null motion tokens + media-motion.md missing → failure."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            motion_data = {
                "motion": {
                    "duration": {"fast": {"$value": "100ms", "$type": "duration"}}
                }
            }
            _write_json(d / "tokens" / "motion.tokens.json", motion_data)
            # media-motion.md not created
            failures, _ = check_design_surface(Path(t))
            self.assertTrue(
                any("motion.tokens.json" in f and "media-motion.md" in f for f in failures),
                f"Expected reduced-motion failure, got: {failures}",
            )

    def test_reduced_motion_skips_when_file_missing(self):
        """No docs/design/ → empty result."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "docs").mkdir()
            failures, warnings = check_design_surface(root)
            self.assertEqual(failures, [])
            self.assertEqual(warnings, [])

    def test_reduced_motion_skips_all_null_values(self):
        """All motion token $values are null → reduced-motion check not required.

        Note: the extended mode parity validator also checks motion.tokens.json, so
        we must populate the mode files with the same key to avoid unrelated failures.
        Only assert that no media-motion.md failure occurs.
        """
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            motion_data = {
                "motion": {
                    "duration": {"fast": {"$value": None, "$type": "duration"}}
                }
            }
            _write_json(d / "tokens" / "motion.tokens.json", motion_data)
            # Populate mode files with the same key so mode parity passes
            _write_json(d / "tokens" / "modes" / "light.tokens.json", motion_data)
            _write_json(d / "tokens" / "modes" / "dark.tokens.json", motion_data)
            # media-motion.md not created — should still pass because values are null
            failures, _ = check_design_surface(Path(t))
            self.assertFalse(
                any("media-motion.md" in f for f in failures),
                f"Unexpected media-motion.md failure for null-only motion tokens: {failures}",
            )

    def test_reduced_motion_skips_no_motion_file(self):
        """No motion.tokens.json → no failure even without media-motion.md."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            # No motion.tokens.json created
            failures, _ = check_design_surface(Path(t))
            self.assertFalse(
                any("motion" in f for f in failures),
                f"Unexpected motion failure: {failures}",
            )


# ---------------------------------------------------------------------------
# Validator 4: Icon sanity
# ---------------------------------------------------------------------------

class IconSanityTests(unittest.TestCase):
    def test_icon_sanity_passes_on_valid_input(self):
        """Square viewBox and no hardcoded colors → no warnings."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            _write_json(d / "icons" / "_index.json", {
                "icons": [
                    {"id": "check", "viewBox": "0 0 24 24"},
                    {"id": "arrow", "viewBox": "0 0 16 16", "fill": "currentColor"},
                ]
            })
            _, warnings = check_design_surface(Path(t))
            self.assertFalse(
                any("icons/_index.json" in w for w in warnings),
                f"Unexpected warnings: {warnings}",
            )

    def test_icon_sanity_fails_on_invalid_input(self):
        """Non-square viewBox → warning."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            _write_json(d / "icons" / "_index.json", {
                "icons": [
                    {"id": "banner", "viewBox": "0 0 32 24"},
                ]
            })
            _, warnings = check_design_surface(Path(t))
            self.assertTrue(
                any("non-square viewBox" in w and "banner" in w for w in warnings),
                f"Expected non-square warning, got: {warnings}",
            )

    def test_icon_sanity_skips_when_file_missing(self):
        """No docs/design/ → empty result."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "docs").mkdir()
            failures, warnings = check_design_surface(root)
            self.assertEqual(failures, [])
            self.assertEqual(warnings, [])

    def test_icon_sanity_hardcoded_fill_warns(self):
        """Hardcoded hex fill on non-multicolor icon → warning."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            _write_json(d / "icons" / "_index.json", {
                "icons": [
                    {"id": "star", "viewBox": "0 0 24 24", "fill": "#ff0000"},
                ]
            })
            _, warnings = check_design_surface(Path(t))
            self.assertTrue(
                any("hardcoded color" in w and "star" in w for w in warnings),
                f"Expected hardcoded color warning, got: {warnings}",
            )

    def test_icon_sanity_multicolor_skips_fill_check(self):
        """Multicolor icon with hardcoded fill → no warning."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            _write_json(d / "icons" / "_index.json", {
                "icons": [
                    {"id": "logo", "viewBox": "0 0 24 24", "fill": "#ff0000", "multicolor": True},
                ]
            })
            _, warnings = check_design_surface(Path(t))
            self.assertFalse(
                any("logo" in w and "hardcoded" in w for w in warnings),
                f"Unexpected warning for multicolor icon: {warnings}",
            )

    def test_icon_sanity_two_value_viewbox_square(self):
        """Two-value viewBox with equal dimensions → no warning."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            _write_json(d / "icons" / "_index.json", {
                "icons": [
                    {"id": "x", "viewBox": "24 24"},
                ]
            })
            _, warnings = check_design_surface(Path(t))
            self.assertFalse(
                any("non-square" in w for w in warnings),
                f"Unexpected non-square warning: {warnings}",
            )

    def test_icon_sanity_two_value_viewbox_nonsquare(self):
        """Two-value viewBox with unequal dimensions → warning."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            _write_json(d / "icons" / "_index.json", {
                "icons": [
                    {"id": "wide", "viewBox": "32 24"},
                ]
            })
            _, warnings = check_design_surface(Path(t))
            self.assertTrue(
                any("non-square viewBox" in w and "wide" in w for w in warnings),
                f"Expected non-square warning, got: {warnings}",
            )

    def test_icon_sanity_skips_empty_icons_list(self):
        """Empty icons list → no warnings."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            _write_json(d / "icons" / "_index.json", {"icons": []})
            _, warnings = check_design_surface(Path(t))
            self.assertFalse(any("icons/_index.json" in w for w in warnings))


# ---------------------------------------------------------------------------
# Validator 5: Keyboard pattern check
# ---------------------------------------------------------------------------

class KeyboardPatternTests(unittest.TestCase):
    def _make_spec(self, d: Path, comp_id: str, keyboard: object) -> None:
        comp_dir = d / "components" / comp_id
        comp_dir.mkdir(parents=True, exist_ok=True)
        _write_json(comp_dir / "spec.json", {
            "id": comp_id,
            "accessibility": {"keyboard": keyboard},
        })

    def test_keyboard_pattern_passes_on_valid_input(self):
        """Keyboard interactions declared + keyboard.md present → no failures."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            self._make_spec(d, "modal", {"Enter": "confirm", "Escape": "close"})
            _write_text(d / "accessibility" / "keyboard.md", "# Keyboard Interactions\n")
            failures, _ = check_design_surface(Path(t))
            self.assertFalse(
                any("keyboard.md" in f for f in failures),
                f"Unexpected failures: {failures}",
            )

    def test_keyboard_pattern_fails_on_invalid_input(self):
        """Keyboard interactions declared + keyboard.md missing → failure."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            self._make_spec(d, "dropdown", {"ArrowDown": "next option"})
            # keyboard.md not created
            failures, _ = check_design_surface(Path(t))
            self.assertTrue(
                any("keyboard.md" in f and "dropdown" in f for f in failures),
                f"Expected keyboard.md failure, got: {failures}",
            )

    def test_keyboard_pattern_skips_when_file_missing(self):
        """No docs/design/ → empty result."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "docs").mkdir()
            failures, warnings = check_design_surface(root)
            self.assertEqual(failures, [])
            self.assertEqual(warnings, [])

    def test_keyboard_pattern_skips_null_accessibility(self):
        """Null accessibility field → no keyboard check."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            comp_dir = d / "components" / "button"
            comp_dir.mkdir(parents=True, exist_ok=True)
            _write_json(comp_dir / "spec.json", {
                "id": "button",
                "accessibility": None,
            })
            failures, _ = check_design_surface(Path(t))
            self.assertFalse(
                any("keyboard.md" in f for f in failures),
                f"Unexpected keyboard.md failure: {failures}",
            )

    def test_keyboard_pattern_skips_empty_keyboard(self):
        """Empty keyboard value → no keyboard check required."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            self._make_spec(d, "tag", None)
            failures, _ = check_design_surface(Path(t))
            self.assertFalse(
                any("keyboard.md" in f for f in failures),
                f"Unexpected keyboard.md failure: {failures}",
            )

    def test_keyboard_pattern_no_components_no_failure(self):
        """No spec.json files → no failure."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            failures, _ = check_design_surface(Path(t))
            self.assertFalse(
                any("keyboard.md" in f for f in failures),
            )


# ---------------------------------------------------------------------------
# Validator 6: State coverage
# ---------------------------------------------------------------------------

class StateCoverageTests(unittest.TestCase):
    def _make_spec_with_states(self, d: Path, comp_id: str, states: list) -> None:
        comp_dir = d / "components" / comp_id
        comp_dir.mkdir(parents=True, exist_ok=True)
        _write_json(comp_dir / "spec.json", {
            "id": comp_id,
            "states": states,
        })

    def test_state_coverage_passes_on_valid_input(self):
        """States reference resolves to a directory → no warnings."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            self._make_spec_with_states(d, "button", ["hover", "focus"])
            (d / "state-patterns" / "hover").mkdir(parents=True, exist_ok=True)
            (d / "state-patterns" / "focus").mkdir(parents=True, exist_ok=True)
            _, warnings = check_design_surface(Path(t))
            self.assertFalse(
                any("state-patterns" in w for w in warnings),
                f"Unexpected warnings: {warnings}",
            )

    def test_state_coverage_fails_on_invalid_input(self):
        """States reference does not resolve → warning."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            self._make_spec_with_states(d, "input", ["hover", "error"])
            (d / "state-patterns" / "hover").mkdir(parents=True, exist_ok=True)
            # "error" state-pattern directory not created
            _, warnings = check_design_surface(Path(t))
            self.assertTrue(
                any("error" in w and "state-patterns" in w for w in warnings),
                f"Expected state coverage warning, got: {warnings}",
            )

    def test_state_coverage_skips_when_file_missing(self):
        """No docs/design/ → empty result."""
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "docs").mkdir()
            failures, warnings = check_design_surface(root)
            self.assertEqual(failures, [])
            self.assertEqual(warnings, [])

    def test_state_coverage_skips_null_states(self):
        """Null states → no state coverage check."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            comp_dir = d / "components" / "card"
            comp_dir.mkdir(parents=True, exist_ok=True)
            _write_json(comp_dir / "spec.json", {"id": "card", "states": None})
            _, warnings = check_design_surface(Path(t))
            self.assertFalse(
                any("state-patterns" in w for w in warnings),
                f"Unexpected state warnings: {warnings}",
            )

    def test_state_coverage_skips_empty_states(self):
        """Empty states list → no state coverage check."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            self._make_spec_with_states(d, "badge", [])
            _, warnings = check_design_surface(Path(t))
            self.assertFalse(
                any("state-patterns" in w for w in warnings),
                f"Unexpected state warnings: {warnings}",
            )

    def test_state_coverage_warning_includes_component_id(self):
        """Warning message includes component id and missing ref."""
        with tempfile.TemporaryDirectory() as t:
            d = _make_design_root(t)
            self._make_spec_with_states(d, "select", ["disabled"])
            # state-patterns/disabled not created
            _, warnings = check_design_surface(Path(t))
            self.assertTrue(
                any("select" in w and "disabled" in w for w in warnings),
                f"Expected warning with component id and ref, got: {warnings}",
            )


# ---------------------------------------------------------------------------
# No docs/design/ → no-op for all validators
# ---------------------------------------------------------------------------

class NoDesignRootTests(unittest.TestCase):
    def test_no_design_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "docs").mkdir()
            failures, warnings = check_design_surface(root)
            self.assertEqual(failures, [])
            self.assertEqual(warnings, [])

    def test_no_docs_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            failures, warnings = check_design_surface(root)
            self.assertEqual(failures, [])
            self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
