"""Tests for wave_lint_lib/design_system_validators.py (AC-16, AC-17)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))

from wave_lint_lib.design_system_validators import check_design_system


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_MANIFEST = {
    "schemaVersion": "1.0.0",
    "extractionVersion": "1",
    "extractedAt": "2026-05-01T00:00:00Z",
    "canonicalRoot": "docs/design-system",
    "sourceStrategy": "repo-evidence-only",
    "evidenceTypes": [],
    "artifactCounts": {},
    "modes": ["light", "dark"],
    "validationSummary": {"passed": 0, "failed": 0},
}

_VALID_PRIMITIVES = {
    "color": {
        "primary": {
            "500": {"$value": "#2563EB", "$type": "color"}
        }
    }
}

_VALID_SEMANTIC = {
    "color": {
        "action": {
            "primary": {
                "background": {"$value": "{color.primary.500}", "$type": "color"}
            }
        }
    }
}

_VALID_MODE = {
    "color": {
        "primary": {
            "500": {"$value": "#2563EB", "$type": "color"}
        }
    }
}

_VALID_SPEC = {
    "id": "button",
    "name": "Button",
    "category": "actions",
    "status": "stable",
    "description": "A clickable button.",
    "figma": None,
    "codeConnect": None,
    "anatomy": [],
    "variants": ["primary", "secondary"],
    "props": [],
    "slots": [],
    "tokens": [],
    "doNotUse": [],
    "preferOver": [],
    "states": None,
    "responsive": None,
    "motion": None,
    "accessibility": None,
    "content": None,
}

_GAPS_VALID = (
    "# Design System Gaps\n\n"
    "## Summary\n\n"
    "- Critical: 0\n"
    "- Important: 0\n"
    "- Nice-to-have: 0\n"
)


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_design_root(tmp: Path) -> Path:
    """Create a minimal valid docs/design-system/ tree."""
    d = tmp / "docs" / "design-system"

    _write_text(d / "README.md", "# Design\n")
    _write_text(d / "DESIGN.md", "# DESIGN\n")
    _write_text(d / "AGENTS.md", "# Agents\n")
    _write_text(d / "VALIDATION.md", "# Validation\n")
    _write_json(d / "manifest.json", _VALID_MANIFEST)
    _write_text(d / "gaps.md", _GAPS_VALID)

    _write_json(d / "tokens" / "primitives.tokens.json", _VALID_PRIMITIVES)
    _write_json(d / "tokens" / "semantic.tokens.json", _VALID_SEMANTIC)
    _write_json(d / "tokens" / "modes" / "light.tokens.json", _VALID_MODE)
    _write_json(d / "tokens" / "modes" / "dark.tokens.json", _VALID_MODE)
    _write_text(d / "tokens" / "README.md", "# Tokens\n")

    _write_text(d / "exports" / "README.md", "# Exports\n")
    (d / "exports" / "css").mkdir(parents=True, exist_ok=True)
    (d / "exports" / "tailwind").mkdir(parents=True, exist_ok=True)
    (d / "exports" / "ts").mkdir(parents=True, exist_ok=True)
    (d / "exports" / "json").mkdir(parents=True, exist_ok=True)

    _write_json(d / "components" / "_index.json", {"components": []})

    _write_text(d / "foundations" / "color.md", "# Color\n")
    _write_text(d / "foundations" / "typography.md", "# Typography\n")
    _write_text(d / "foundations" / "spacing.md", "# Spacing\n")
    _write_text(d / "foundations" / "radius.md", "# Radius\n")
    _write_text(d / "foundations" / "elevation.md", "# Elevation\n")
    _write_text(d / "foundations" / "motion.md", "# Motion\n")

    _write_json(d / "accessibility" / "contrast-report.json", {"checks": []})
    _write_text(d / "accessibility" / "README.md", "# A11y\n")

    _write_json(d / "version.json", {"schemaVersion": "1.0.0"})
    _write_json(d / "source-map.json", [])
    _write_text(d / "proposed-additions.md", "# Proposals\n")

    return d


# ---------------------------------------------------------------------------
# No docs/design-system/ → no-op
# ---------------------------------------------------------------------------

class NoDesignRootTests(unittest.TestCase):
    def test_no_design_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "docs").mkdir()
            failures, warnings = check_design_system(root)
            self.assertEqual(failures, [])
            self.assertEqual(warnings, [])


# ---------------------------------------------------------------------------
# Required path presence
# ---------------------------------------------------------------------------

class RequiredPathTests(unittest.TestCase):
    def test_valid_tree_passes(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            failures, _ = check_design_system(root)
            self.assertEqual(failures, [])

    def test_missing_manifest_emits_bootstrap_warning(self):
        # docs/design-system/ without manifest.json is a valid pre-extraction state;
        # should warn with a guidance message, not fail.
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            (root / "docs" / "design-system" / "manifest.json").unlink()
            failures, warnings = check_design_system(root)
            self.assertEqual(failures, [])
            self.assertTrue(any("extraction contract not yet bootstrapped" in w for w in warnings))

    def test_missing_gaps_md_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            (root / "docs" / "design-system" / "gaps.md").unlink()
            failures, _ = check_design_system(root)
            self.assertTrue(any("gaps.md" in f for f in failures))

    def test_missing_primitives_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            (root / "docs" / "design-system" / "tokens" / "primitives.tokens.json").unlink()
            failures, _ = check_design_system(root)
            self.assertTrue(any("primitives.tokens.json" in f for f in failures))

    def test_missing_proposed_additions_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            (root / "docs" / "design-system" / "proposed-additions.md").unlink()
            failures, _ = check_design_system(root)
            self.assertTrue(any("proposed-additions.md" in f for f in failures))

    def _strip_subtrees(self, root: Path) -> None:
        """Remove all optional subtree dirs from a full design root."""
        import shutil
        d = root / "docs" / "design-system"
        for sub in ("tokens", "exports", "foundations", "accessibility", "components"):
            p = d / sub
            if p.is_dir():
                shutil.rmtree(p)

    def test_no_subtrees_no_subtree_failures(self):
        # A bootstrapped manifest with none of the optional subtrees should
        # produce zero subtree-related failures.
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            self._strip_subtrees(root)
            failures, _ = check_design_system(root)
            subtree_keys = ("tokens/", "exports/", "foundations/", "accessibility/", "components/")
            subtree_failures = [f for f in failures if any(k in f for k in subtree_keys)]
            self.assertEqual(subtree_failures, [], subtree_failures)

    def test_tokens_subtree_present_but_missing_child_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            (root / "docs" / "design-system" / "tokens" / "primitives.tokens.json").unlink()
            failures, _ = check_design_system(root)
            self.assertTrue(any("primitives.tokens.json" in f for f in failures))

    def test_exports_subtree_present_but_missing_child_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            import shutil
            shutil.rmtree(root / "docs" / "design-system" / "exports" / "css")
            failures, _ = check_design_system(root)
            self.assertTrue(any("exports/css" in f for f in failures))

    def test_foundations_subtree_present_but_missing_child_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            (root / "docs" / "design-system" / "foundations" / "color.md").unlink()
            failures, _ = check_design_system(root)
            self.assertTrue(any("foundations/color.md" in f for f in failures))

    def test_accessibility_subtree_present_but_missing_child_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            (root / "docs" / "design-system" / "accessibility" / "contrast-report.json").unlink()
            failures, _ = check_design_system(root)
            self.assertTrue(any("accessibility/contrast-report.json" in f for f in failures))

    def test_components_subtree_present_requires_index(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            (root / "docs" / "design-system" / "components" / "_index.json").unlink()
            failures, _ = check_design_system(root)
            self.assertTrue(any("components/_index.json" in f for f in failures))

    def test_subtree_dir_as_file_does_not_trigger_subtree_checks(self):
        # If "tokens" is a file (not a dir), subtree checks must not fire.
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            self._strip_subtrees(root)
            # Write "tokens" as a regular file, not a directory
            _write_text(root / "docs" / "design-system" / "tokens", "not a dir\n")
            failures, _ = check_design_system(root)
            token_failures = [f for f in failures if "tokens/" in f]
            self.assertEqual(token_failures, [], token_failures)


# ---------------------------------------------------------------------------
# manifest.json
# ---------------------------------------------------------------------------

class ManifestTests(unittest.TestCase):
    def test_canonical_root_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            bad = dict(_VALID_MANIFEST, canonicalRoot="design")
            _write_json(root / "docs" / "design-system" / "manifest.json", bad)
            failures, _ = check_design_system(root)
            self.assertTrue(any("canonicalRoot" in f for f in failures))
            self.assertTrue(any("docs/design-system" in f for f in failures))

    def test_missing_schema_version_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            bad = {k: v for k, v in _VALID_MANIFEST.items() if k != "schemaVersion"}
            _write_json(root / "docs" / "design-system" / "manifest.json", bad)
            failures, _ = check_design_system(root)
            self.assertTrue(any("schemaVersion" in f for f in failures))

    def test_invalid_source_strategy_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            bad = dict(_VALID_MANIFEST, sourceStrategy="magic")
            _write_json(root / "docs" / "design-system" / "manifest.json", bad)
            failures, _ = check_design_system(root)
            self.assertTrue(any("sourceStrategy" in f for f in failures))

    def test_valid_manifest_passes(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            failures, _ = check_design_system(root)
            self.assertEqual(failures, [])


# ---------------------------------------------------------------------------
# gaps.md summary
# ---------------------------------------------------------------------------

class GapsSummaryTests(unittest.TestCase):
    def test_missing_summary_lines_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            _write_text(root / "docs" / "design-system" / "gaps.md", "# Gaps\n\nNo summary here.\n")
            failures, _ = check_design_system(root)
            self.assertTrue(any("gaps.md" in f for f in failures))

    def test_valid_gaps_passes(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            failures, _ = check_design_system(root)
            self.assertEqual(failures, [])


# ---------------------------------------------------------------------------
# spec.json identity and behavioral fields
# ---------------------------------------------------------------------------

class SpecJsonTests(unittest.TestCase):
    def _setup_with_spec(self, tmp: Path, spec: dict) -> Path:
        root = tmp
        d = _make_design_root(root)
        comp_dir = d / "components" / "button"
        comp_dir.mkdir(parents=True, exist_ok=True)
        _write_json(comp_dir / "spec.json", spec)
        # Update _index.json to include the component
        _write_json(d / "components" / "_index.json", {"components": [{"id": "button"}]})
        return root

    def test_valid_spec_passes(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._setup_with_spec(Path(t), _VALID_SPEC)
            failures, _ = check_design_system(root)
            self.assertEqual(failures, [])

    def test_missing_identity_field_fails(self):
        with tempfile.TemporaryDirectory() as t:
            bad = {k: v for k, v in _VALID_SPEC.items() if k != "category"}
            root = self._setup_with_spec(Path(t), bad)
            failures, _ = check_design_system(root)
            self.assertTrue(any("category" in f for f in failures))

    def test_missing_behavioral_field_fails(self):
        with tempfile.TemporaryDirectory() as t:
            bad = {k: v for k, v in _VALID_SPEC.items() if k != "states"}
            root = self._setup_with_spec(Path(t), bad)
            failures, _ = check_design_system(root)
            self.assertTrue(any("states" in f for f in failures))

    def test_behavioral_field_null_passes(self):
        with tempfile.TemporaryDirectory() as t:
            spec = dict(_VALID_SPEC, states=None)
            root = self._setup_with_spec(Path(t), spec)
            failures, _ = check_design_system(root)
            self.assertEqual(failures, [])


# ---------------------------------------------------------------------------
# Token dot-path naming
# ---------------------------------------------------------------------------

class TokenNamingTests(unittest.TestCase):
    def test_invalid_dot_path_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            bad_tokens = {"Color/Primary/500": {"$value": "#2563EB", "$type": "color"}}
            _write_json(
                root / "docs" / "design-system" / "tokens" / "primitives.tokens.json",
                bad_tokens,
            )
            failures, _ = check_design_system(root)
            self.assertTrue(any("dot-path" in f for f in failures))

    def test_valid_dot_path_passes(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            failures, _ = check_design_system(root)
            self.assertEqual(failures, [])


# ---------------------------------------------------------------------------
# Broken token references
# ---------------------------------------------------------------------------

class BrokenTokenRefTests(unittest.TestCase):
    def test_broken_alias_ref_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            bad_semantic = {
                "color": {
                    "action": {
                        "background": {"$value": "{color.nonexistent.500}", "$type": "color"}
                    }
                }
            }
            _write_json(
                root / "docs" / "design-system" / "tokens" / "semantic.tokens.json",
                bad_semantic,
            )
            failures, _ = check_design_system(root)
            self.assertTrue(any("broken alias" in f for f in failures))

    def test_valid_alias_ref_passes(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            failures, _ = check_design_system(root)
            self.assertEqual(failures, [])


# ---------------------------------------------------------------------------
# Orphan primitives
# ---------------------------------------------------------------------------

class OrphanPrimitiveTests(unittest.TestCase):
    def test_orphan_primitive_produces_warning(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            # Add a primitive not referenced by semantic
            extra_primitives = {
                "color": {
                    "primary": {"500": {"$value": "#2563EB", "$type": "color"}},
                    "orphan": {"999": {"$value": "#FF0000", "$type": "color"}},
                }
            }
            _write_json(
                root / "docs" / "design-system" / "tokens" / "primitives.tokens.json",
                extra_primitives,
            )
            _, warnings = check_design_system(root)
            self.assertTrue(any("orphan" in w for w in warnings))

    def test_primitive_only_flag_suppresses_warning(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            flagged_primitives = {
                "color": {
                    "primary": {"500": {"$value": "#2563EB", "$type": "color"}},
                    "debug": {
                        "red": {
                            "$value": "#FF0000",
                            "$type": "color",
                            "$extensions": {"primitive-only": True},
                        }
                    },
                }
            }
            _write_json(
                root / "docs" / "design-system" / "tokens" / "primitives.tokens.json",
                flagged_primitives,
            )
            _, warnings = check_design_system(root)
            self.assertFalse(any("color.debug.red" in w for w in warnings))


# ---------------------------------------------------------------------------
# Mode parity
# ---------------------------------------------------------------------------

class ModePairityTests(unittest.TestCase):
    def test_key_missing_in_dark_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            light = {
                "color": {
                    "primary": {"500": {"$value": "#fff", "$type": "color"}},
                    "extra": {"100": {"$value": "#eee", "$type": "color"}},
                }
            }
            dark = {"color": {"primary": {"500": {"$value": "#000", "$type": "color"}}}}
            _write_json(root / "docs" / "design-system" / "tokens" / "modes" / "light.tokens.json", light)
            _write_json(root / "docs" / "design-system" / "tokens" / "modes" / "dark.tokens.json", dark)
            failures, _ = check_design_system(root)
            self.assertTrue(any("dark.tokens.json" in f and "extra" in f for f in failures))

    def test_key_missing_in_light_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            light = {"color": {"primary": {"500": {"$value": "#fff", "$type": "color"}}}}
            dark = {
                "color": {
                    "primary": {"500": {"$value": "#000", "$type": "color"}},
                    "extra": {"100": {"$value": "#111", "$type": "color"}},
                }
            }
            _write_json(root / "docs" / "design-system" / "tokens" / "modes" / "light.tokens.json", light)
            _write_json(root / "docs" / "design-system" / "tokens" / "modes" / "dark.tokens.json", dark)
            failures, _ = check_design_system(root)
            self.assertTrue(any("light.tokens.json" in f and "extra" in f for f in failures))

    def test_matching_keys_passes(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            _make_design_root(root)
            failures, _ = check_design_system(root)
            self.assertEqual(failures, [])


# ---------------------------------------------------------------------------
# _index.json <-> folder parity (AC-17)
# ---------------------------------------------------------------------------

class IndexFolderParityTests(unittest.TestCase):
    def _setup(self, tmp: Path, folders: list[str], entries: list[str]) -> Path:
        root = tmp
        d = _make_design_root(root)
        comp_dir = d / "components"
        for name in folders:
            (comp_dir / name).mkdir(parents=True, exist_ok=True)
        _write_json(
            comp_dir / "_index.json",
            {"components": [{"id": e} for e in entries]},
        )
        return root

    def test_folder_without_index_entry_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._setup(Path(t), ["button"], [])
            failures, _ = check_design_system(root)
            self.assertTrue(any("button" in f and "_index.json" in f for f in failures))

    def test_index_entry_without_folder_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._setup(Path(t), [], ["button"])
            failures, _ = check_design_system(root)
            self.assertTrue(any("button" in f for f in failures))

    def test_matching_index_and_folders_passes(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._setup(Path(t), ["button"], ["button"])
            failures, _ = check_design_system(root)
            self.assertEqual(failures, [])

    def test_empty_index_and_no_folders_passes(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._setup(Path(t), [], [])
            failures, _ = check_design_system(root)
            self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
