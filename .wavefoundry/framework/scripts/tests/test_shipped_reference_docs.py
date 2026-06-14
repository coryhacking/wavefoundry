from __future__ import annotations

import unittest
from pathlib import Path

# tests/ -> scripts/ -> framework/ -> .wavefoundry/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[4]

# Shipped framework template -> canonical project copy. Each pair must stay BYTE-IDENTICAL:
# the framework copy is what build_pack carries in the distribution zip and the install/upgrade
# seeds provision into target projects; the project copy is the canonical the self-host uses.
# (1p4dc for install-log-format; 1p455 for scan-findings-format. 1p591 consolidated the shipped
# templates: install-log-format under .wavefoundry/framework/install/ with the other install assets,
# scan-findings-format under .wavefoundry/framework/docs/ — see docs/references/install-assets.md.)
SHIPPED_TEMPLATE_PAIRS = {
    "install-log-format.md": (
        ".wavefoundry/framework/install/install-log-format.md",
        "docs/references/install-log-format.md",
    ),
    "scan-findings-format.md": (
        ".wavefoundry/framework/docs/scan-findings-format.md",
        "docs/references/scan-findings-format.md",
    ),
}


class ShippedReferenceDocParityTests(unittest.TestCase):
    """Wave 1p591: every reference doc shipped as a framework template must stay BYTE-IDENTICAL to
    its canonical project copy. If the two drift, every installed/upgraded target receives a stale
    schema. This guards the shipped-template <-> provisioned-canonical invariant documented in
    ``docs/references/install-assets.md`` — it is NOT accidental duplication."""

    def test_shipped_templates_are_byte_identical_to_canonical(self) -> None:
        for name, (shipped_rel, canonical_rel) in SHIPPED_TEMPLATE_PAIRS.items():
            with self.subTest(doc=name):
                shipped = REPO_ROOT / shipped_rel
                canonical = REPO_ROOT / canonical_rel
                self.assertTrue(shipped.is_file(), f"missing shipped template: {shipped_rel}")
                self.assertTrue(canonical.is_file(), f"missing canonical copy: {canonical_rel}")
                self.assertEqual(
                    shipped.read_bytes(),
                    canonical.read_bytes(),
                    f"{name}: the shipped framework template ({shipped_rel}) has drifted from the "
                    f"canonical copy ({canonical_rel}) — they must stay byte-identical so installed "
                    f"targets receive the current schema (see docs/references/install-assets.md).",
                )

    def test_all_provisioned_format_schemas_are_guarded(self) -> None:
        """Every canonical ``*-format.md`` under ``docs/references/`` is a provisioned schema and must
        have a parity pair — a new one without a guard would silently drift from its shipped template."""
        guarded = set(SHIPPED_TEMPLATE_PAIRS)
        for canonical in sorted((REPO_ROOT / "docs" / "references").glob("*-format.md")):
            with self.subTest(doc=canonical.name):
                self.assertIn(
                    canonical.name, guarded,
                    f"{canonical.name} is a provisioned *-format schema but has no parity pair in "
                    f"SHIPPED_TEMPLATE_PAIRS — add one so its shipped template cannot drift.",
                )


if __name__ == "__main__":
    unittest.main()
