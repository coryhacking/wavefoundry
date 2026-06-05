"""Tests for `wave_lint_lib.canonical_names` — the canonical-names manifest
loader shipped in wave `1p3iv` change `1p3j6`.

The loader is the single source of truth for framework-shipped renames (role
slugs and config keys with deprecated aliases). Tests cover:

- happy-path load from a valid manifest
- fail-safe behavior on absent / malformed / wrong-schema input
- alias-map extraction skips malformed entries silently
- canonical-to-aliases inversion produces sorted lists
- removed_in lookups return strings or None correctly
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parent.parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from wave_lint_lib import canonical_names  # noqa: E402


class ManifestPathTests(unittest.TestCase):
    def test_manifest_path_under_dot_wavefoundry(self):
        root = Path("/some/repo")
        self.assertEqual(
            canonical_names.manifest_path(root),
            root / ".wavefoundry/framework/canonical-names.json",
        )

    def test_framework_repo_root_resolves_from_module_location(self):
        # The function should return SOMETHING and that something should be a
        # directory containing `.wavefoundry/framework/canonical-names.json`
        # (proving the parent-count is right for this repo's actual layout).
        root = canonical_names.framework_repo_root()
        self.assertTrue(
            (root / ".wavefoundry/framework/canonical-names.json").exists()
            or (root / ".wavefoundry/framework").exists(),
            f"framework_repo_root() returned {root}; expected to contain "
            f".wavefoundry/framework/ subtree.",
        )


class LoaderFailSafeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="canon-names-"))

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_manifest(self, body: str) -> None:
        path = self._tmp / ".wavefoundry/framework"
        path.mkdir(parents=True, exist_ok=True)
        (path / "canonical-names.json").write_text(body, encoding="utf-8")

    def test_load_returns_empty_when_manifest_absent(self):
        result = canonical_names.load_manifest(self._tmp)
        self.assertEqual(result["schema_version"], canonical_names.SUPPORTED_SCHEMA_VERSION)
        self.assertEqual(result["role_renames"], {})
        self.assertEqual(result["config_key_renames"], {})

    def test_load_returns_empty_when_manifest_malformed_json(self):
        self._write_manifest("{not valid json")
        result = canonical_names.load_manifest(self._tmp)
        self.assertEqual(result["role_renames"], {})
        self.assertEqual(result["config_key_renames"], {})

    def test_load_returns_empty_when_manifest_wrong_schema_version(self):
        self._write_manifest(json.dumps({
            "schema_version": 99,
            "role_renames": {"foo": {"canonical": "bar"}},
        }))
        result = canonical_names.load_manifest(self._tmp)
        self.assertEqual(result["role_renames"], {})

    def test_load_returns_empty_when_manifest_root_is_not_object(self):
        self._write_manifest(json.dumps(["unexpected", "shape"]))
        result = canonical_names.load_manifest(self._tmp)
        self.assertEqual(result["role_renames"], {})


class AliasMapExtractionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="canon-alias-"))
        (self._tmp / ".wavefoundry/framework").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_manifest(self, manifest: dict) -> None:
        (self._tmp / ".wavefoundry/framework/canonical-names.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

    def test_role_alias_map_extracted_from_valid_manifest(self):
        self._write_manifest({
            "schema_version": 1,
            "role_renames": {
                "council-moderator": {"canonical": "wave-council", "removed_in": None},
                "code-insight-agent": {"canonical": "guru", "removed_in": None},
            },
            "config_key_renames": {},
        })
        result = canonical_names.role_alias_to_canonical(self._tmp)
        self.assertEqual(result, {
            "council-moderator": "wave-council",
            "code-insight-agent": "guru",
        })

    def test_config_key_alias_map_extracted_from_valid_manifest(self):
        self._write_manifest({
            "schema_version": 1,
            "role_renames": {},
            "config_key_renames": {
                "wave_council_policy": {"canonical": "wave_review", "removed_in": None},
            },
        })
        result = canonical_names.config_key_alias_to_canonical(self._tmp)
        self.assertEqual(result, {"wave_council_policy": "wave_review"})

    def test_alias_map_skips_entry_without_canonical_field(self):
        self._write_manifest({
            "schema_version": 1,
            "role_renames": {
                "good": {"canonical": "ok"},
                "bad-no-canonical": {"removed_in": None},
                "bad-empty-canonical": {"canonical": ""},
                "bad-non-string-canonical": {"canonical": 42},
            },
            "config_key_renames": {},
        })
        result = canonical_names.role_alias_to_canonical(self._tmp)
        self.assertEqual(result, {"good": "ok"})

    def test_alias_map_skips_entry_that_is_not_dict(self):
        self._write_manifest({
            "schema_version": 1,
            "role_renames": {
                "good": {"canonical": "ok"},
                "bad": "not-a-dict",
            },
            "config_key_renames": {},
        })
        result = canonical_names.role_alias_to_canonical(self._tmp)
        self.assertEqual(result, {"good": "ok"})

    def test_canonical_to_aliases_inverts_and_sorts(self):
        alias_map = {
            "alias-c": "canonical-1",
            "alias-a": "canonical-1",
            "alias-b": "canonical-2",
        }
        result = canonical_names.canonical_to_aliases(alias_map)
        self.assertEqual(result, {
            "canonical-1": ["alias-a", "alias-c"],
            "canonical-2": ["alias-b"],
        })


class RemovedInLookupTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="canon-removed-"))
        (self._tmp / ".wavefoundry/framework").mkdir(parents=True)
        (self._tmp / ".wavefoundry/framework/canonical-names.json").write_text(
            json.dumps({
                "schema_version": 1,
                "role_renames": {
                    "no-removal": {"canonical": "new", "removed_in": None},
                    "scheduled": {"canonical": "renamed", "removed_in": "2.0.0"},
                },
                "config_key_renames": {
                    "key-with-removal": {"canonical": "new_key", "removed_in": "1.7.0"},
                },
            }),
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_role_removed_in_returns_version_string(self):
        self.assertEqual(
            canonical_names.role_removed_in(self._tmp, "scheduled"),
            "2.0.0",
        )

    def test_role_removed_in_returns_none_when_not_scheduled(self):
        self.assertIsNone(canonical_names.role_removed_in(self._tmp, "no-removal"))

    def test_role_removed_in_returns_none_for_unknown_alias(self):
        self.assertIsNone(canonical_names.role_removed_in(self._tmp, "does-not-exist"))

    def test_config_key_removed_in_returns_version_string(self):
        self.assertEqual(
            canonical_names.config_key_removed_in(self._tmp, "key-with-removal"),
            "1.7.0",
        )


class FrameworkManifestSelfHostTests(unittest.TestCase):
    """Verify the framework's own shipped manifest is well-formed and contains
    the renames the rest of the framework (constants.py, docs-lint) depends on.
    This is the integration anchor: if someone edits the manifest and breaks
    the canonical entries, this test catches it before the rest of the suite
    fails with confusing errors."""

    def test_framework_manifest_contains_known_role_renames(self):
        result = canonical_names.role_alias_to_canonical(
            canonical_names.framework_repo_root()
        )
        self.assertEqual(result.get("council-moderator"), "wave-council")
        self.assertEqual(result.get("code-insight-agent"), "guru")

    def test_framework_manifest_contains_known_config_key_renames(self):
        result = canonical_names.config_key_alias_to_canonical(
            canonical_names.framework_repo_root()
        )
        self.assertEqual(result.get("wave_council_policy"), "wave_review")
        self.assertEqual(result.get("wave_execution"), "wave_implement")

    def test_constants_RETIRED_ROLE_NAMES_matches_manifest(self):
        """The public `RETIRED_ROLE_NAMES` constant is now manifest-derived;
        verify it stays in sync with the manifest content."""
        from wave_lint_lib import constants
        manifest_renames = canonical_names.role_alias_to_canonical(
            canonical_names.framework_repo_root()
        )
        self.assertEqual(constants.RETIRED_ROLE_NAMES, manifest_renames)

    def test_constants_WORKFLOW_REQUIRED_KEYS_carries_manifest_aliases(self):
        """The required-keys tuple should contain alias tuples for canonical
        keys that have aliases in the manifest. Verify `wave_review` has
        `wave_council_policy` as an alias and `wave_implement` has
        `wave_execution`."""
        from wave_lint_lib import constants
        # Find the alias tuples in WORKFLOW_REQUIRED_KEYS
        tuples = [k for k in constants.WORKFLOW_REQUIRED_KEYS if isinstance(k, tuple)]
        wave_review_tuple = next((t for t in tuples if t[0] == "wave_review"), None)
        wave_implement_tuple = next((t for t in tuples if t[0] == "wave_implement"), None)
        self.assertIsNotNone(wave_review_tuple, "wave_review tuple missing")
        self.assertIsNotNone(wave_implement_tuple, "wave_implement tuple missing")
        self.assertIn("wave_council_policy", wave_review_tuple)
        self.assertIn("wave_execution", wave_implement_tuple)


if __name__ == "__main__":
    unittest.main()
