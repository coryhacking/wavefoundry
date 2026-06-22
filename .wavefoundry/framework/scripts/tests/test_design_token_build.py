"""Tests for the design-token build pipeline (wave 12atj, AC-10).

Self-contained: the framework test suite must pass WITHOUT a Node /
Style-Dictionary install (CI has no Node). The built-in pure-Python transform
is exercised directly; the wrapper's config-contract parsing and tool dispatch
(``custom`` path with a trivial shell command) are exercised via subprocess; an
actual ``style-dictionary`` run is skip-when-absent, never a hard dependency.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT))

import design_token_build as dtb
from wave_lint_lib.design_system_validators import check_design_system

REPO_ROOT = SCRIPTS_ROOT.parent.parent.parent
WRAPPER = REPO_ROOT / "docs" / "design-system" / "bin" / "build-tokens"


# ---------------------------------------------------------------------------
# Minimal valid DTCG fixtures
# ---------------------------------------------------------------------------

_PRIMITIVES = {
    "color": {
        "blue": {"500": {"$value": "#1976d2", "$type": "color"}},
        "ink": {"$value": "#212529", "$type": "color"},
    },
    "space": {"4": {"$value": "1rem", "$type": "dimension"}},
}

_SEMANTIC = {
    "color": {
        "action": {"primary": {"$value": "{color.blue.500}", "$type": "color"}},
        "text": {"$value": "{color.ink}", "$type": "color"},
    },
    "space": {"md": {"$value": "{space.4}", "$type": "dimension"}},
}

_LIGHT = {
    "color": {
        "blue": {"500": {"$value": "#1976d2", "$type": "color"}},
        "ink": {"$value": "#212529", "$type": "color"},
    },
    "space": {"4": {"$value": "1rem", "$type": "dimension"}},
}

_DARK = {
    "color": {
        "blue": {"500": {"$value": "#40A3E9", "$type": "color"}},
        "ink": {"$value": "#e4e2de", "$type": "color"},
    },
    "space": {"4": {"$value": "1rem", "$type": "dimension"}},
}


def _write_design_root(base: Path, *, broken: bool = False) -> Path:
    design = base / "docs" / "design-system"
    tokens = design / "tokens" / "modes"
    tokens.mkdir(parents=True, exist_ok=True)
    semantic = json.loads(json.dumps(_SEMANTIC))
    if broken:
        semantic["color"]["action"]["primary"]["$value"] = "{color.does.not.exist}"
    (design / "tokens" / "primitives.tokens.json").write_text(
        json.dumps(_PRIMITIVES), encoding="utf-8")
    (design / "tokens" / "semantic.tokens.json").write_text(
        json.dumps(semantic), encoding="utf-8")
    (design / "tokens" / "modes" / "light.tokens.json").write_text(
        json.dumps(_LIGHT), encoding="utf-8")
    (design / "tokens" / "modes" / "dark.tokens.json").write_text(
        json.dumps(_DARK), encoding="utf-8")
    return design


# ---------------------------------------------------------------------------
# Built-in transform (AC-2..AC-6, AC-10)
# ---------------------------------------------------------------------------

class BuiltinTransformTest(unittest.TestCase):
    def test_emits_four_targets_with_structure(self):
        with tempfile.TemporaryDirectory() as td:
            design = _write_design_root(Path(td))
            written = dtb.build(design)
            names = {p.name for p in written}
            self.assertEqual(
                names, {"tokens.css", "theme.config.js", "tokens.ts", "tokens.json"})
            for p in written:
                self.assertTrue(p.exists())
                self.assertIn(dtb.GENERATED_HEADER, p.read_text(encoding="utf-8"))

            css = (design / "exports" / "css" / "tokens.css").read_text(encoding="utf-8")
            # AC-2: custom properties + mode override block.
            self.assertIn("--ds-color-action-primary: #1976d2;", css)
            self.assertIn("prefers-color-scheme: dark", css)
            self.assertIn('[data-theme="dark"]', css)
            self.assertIn("#40A3E9", css)  # dark override value present

            ts = (design / "exports" / "ts" / "tokens.ts").read_text(encoding="utf-8")
            # AC-4: per-mode maps, typed, no `any`.
            self.assertIn("export const tokens", ts)
            self.assertIn("export const tokensByMode", ts)
            self.assertNotIn(": any", ts)

            flat = json.loads(
                (design / "exports" / "json" / "tokens.json").read_text(encoding="utf-8"))
            # AC-5: aliases resolved to raw values.
            self.assertEqual(flat["tokens"]["color.action.primary"], "#1976d2")
            self.assertEqual(flat["modes"]["dark"]["color.action.primary"], "#40A3E9")

            tw = (design / "exports" / "tailwind" / "theme.config.js").read_text(encoding="utf-8")
            # AC-3: colors + spacing extension present.
            self.assertIn("colors", tw)
            self.assertIn("spacing", tw)

    def test_idempotent_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            design = _write_design_root(Path(td))
            dtb.build(design)
            first = {
                p.name: p.read_bytes()
                for p in (design / "exports").rglob("*")
                if p.is_file()
            }
            dtb.build(design)
            second = {
                p.name: p.read_bytes()
                for p in (design / "exports").rglob("*")
                if p.is_file()
            }
            self.assertEqual(first, second)

    def test_broken_ref_raises(self):
        with tempfile.TemporaryDirectory() as td:
            design = _write_design_root(Path(td), broken=True)
            with self.assertRaises(dtb.TokenBuildError):
                dtb.build(design)


# ---------------------------------------------------------------------------
# Manifest export-parity + stale lint (AC-8)
# ---------------------------------------------------------------------------

class ManifestParityTest(unittest.TestCase):
    def _seed_manifest(self, design: Path) -> Path:
        manifest = {
            "schemaVersion": "1.0.0",
            "validationSummary": {"passed": 1, "failed": 0},
        }
        path = design / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_build_records_parity_fields(self):
        with tempfile.TemporaryDirectory() as td:
            design = _write_design_root(Path(td))
            manifest_path = self._seed_manifest(design)
            dtb.build(design)
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            summary = data["validationSummary"]
            self.assertTrue(summary["exportsGenerated"])
            self.assertIn("exportsAt", summary)
            self.assertFalse(summary["exportsStale"])

    def test_stale_detection_when_source_newer(self):
        with tempfile.TemporaryDirectory() as td:
            design = _write_design_root(Path(td))
            dtb.build(design)
            self.assertFalse(dtb.exports_stale(design))
            # Bump token source mtime past exports.
            src = design / "tokens" / "semantic.tokens.json"
            future = src.stat().st_mtime + 100
            os.utime(src, (future, future))
            self.assertTrue(dtb.exports_stale(design))

    def test_lint_warns_on_stale(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            design = _write_design_root(root)
            # A full extraction contract is needed for the lint to reach manifest
            # checks without unrelated failures; seed a minimal valid manifest with
            # exportsStale=true and assert the warning fires.
            manifest = {
                "schemaVersion": "1.0.0",
                "extractionVersion": "1.0.0",
                "extractedAt": "2026-01-01",
                "canonicalRoot": "docs/design-system",
                "sourceStrategy": "repo-evidence-only",
                "evidenceTypes": [],
                "artifactCounts": {},
                "modes": ["light", "dark"],
                "validationSummary": {
                    "passed": 0, "failed": 0,
                    "exportsGenerated": True, "exportsStale": True,
                },
            }
            (design / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            _failures, warnings = check_design_system(root)
            self.assertTrue(
                any("exportsStale" in w for w in warnings),
                f"expected stale-exports warning, got: {warnings}",
            )


# ---------------------------------------------------------------------------
# Wrapper: config-contract parsing + tool dispatch (AC-1, AC-7)
# ---------------------------------------------------------------------------

class WrapperDispatchTest(unittest.TestCase):
    def _run(self, root: Path, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(WRAPPER), "--root", str(root), *extra],
            capture_output=True, text=True, cwd=str(root),
        )

    def test_missing_config_exits_nonzero_actionable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".wavefoundry").mkdir()
            _write_design_root(root)
            proc = self._run(root)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("build.config.json", proc.stderr)

    def test_builtin_tool_generates_exports(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".wavefoundry").mkdir()
            design = _write_design_root(root)
            (design / "build.config.json").write_text(
                json.dumps({"tool": "builtin", "version": "1.0.0",
                            "targets": [{"format": "css"}, {"format": "json"}]}),
                encoding="utf-8")
            proc = self._run(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((design / "exports" / "css" / "tokens.css").exists())
            self.assertTrue((design / "exports" / "json" / "tokens.json").exists())

    def test_custom_tool_runs_command(self):
        # tool='custom' with a trivial shell command that emits a fixture file.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".wavefoundry").mkdir()
            design = _write_design_root(root)
            # command runs with cwd = design_root, so a relative path lands there.
            marker = design / "custom-ran.txt"
            (design / "build.config.json").write_text(
                json.dumps({
                    "tool": "custom", "version": "1.0.0",
                    "command": f"echo ok > {marker.name}",
                }), encoding="utf-8")
            proc = self._run(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(marker.exists())

    def test_custom_tool_missing_command_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".wavefoundry").mkdir()
            design = _write_design_root(root)
            (design / "build.config.json").write_text(
                json.dumps({"tool": "custom", "version": "1.0.0"}), encoding="utf-8")
            proc = self._run(root)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("command", proc.stderr)

    def test_builtin_broken_ref_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".wavefoundry").mkdir()
            design = _write_design_root(root, broken=True)
            (design / "build.config.json").write_text(
                json.dumps({"tool": "builtin", "version": "1.0.0"}), encoding="utf-8")
            proc = self._run(root)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("broken token reference", proc.stderr)

    def test_style_dictionary_absent_exits_actionable(self):
        # Skip-when-present: only meaningful when style-dictionary is NOT installed.
        if shutil.which("style-dictionary") or shutil.which("npx"):
            self.skipTest("style-dictionary/npx present — actual run is install-time")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".wavefoundry").mkdir()
            design = _write_design_root(root)
            (design / "build.config.json").write_text(
                json.dumps({"tool": "style-dictionary", "version": "1.0.0",
                            "targets": []}), encoding="utf-8")
            proc = self._run(root)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("npm install", proc.stderr)


if __name__ == "__main__":
    unittest.main()
