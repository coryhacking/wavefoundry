"""Executed census for change 1wgwn-enh (wave 1wip2).

Grounds the implementation through the real machinery, never grep alone:
1. Parity region: extract the `## Index Scope` section from seed-211 and
   docs/agents/guru.md by heading boundaries; record lengths, hashes, equality.
2. Existing oracle: locate the Citation-block parity test and record what it
   guards (the cross-reference target).
3. CHANGELOG homes: the current top-section heading (dated means the docs-gate
   check is a no-op today), every claim-pattern match in the top section, a
   historical-section sweep proving old numerals exist below (the reason for
   top-only scoping), and the packaging home via build_pack's own
   _extract_changelog_section for the current version.
4. Guru divergence: the registration passages where guru.md differs from
   seed-211's corresponding current text.

Prints JSON to stdout; writes a file ONLY with --out (QA-DEL-1 discipline).
Run from the repository root:
    python3 "docs/waves/1wip2 guidance-surface-drift-guards/evidence/census_drift_guards.py" [--out census_drift_guards.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / ".wavefoundry" / "framework" / "scripts"
sys.path.insert(0, str(SCRIPTS))

SEED = REPO_ROOT / ".wavefoundry/framework/seeds/211-guru.prompt.md"
GURU = REPO_ROOT / "docs/agents/guru.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

CLAIM_PATTERNS = {
    "CHUNKER_VERSION": ("chunker.py", "CHUNKER_VERSION"),
    "WALKER_VERSION": ("indexer.py", "WALKER_VERSION"),
    "GRAPH_BUILDER_VERSION": ("graph_indexer.py", "GRAPH_BUILDER_VERSION"),
}
# Backtick-anchored constant name, a bounded prose connector, then a numeral.
_CLAIM_RE = re.compile(
    r"`(CHUNKER_VERSION|WALKER_VERSION|GRAPH_BUILDER_VERSION)`"
    r"[^`\n]{0,80}?\b(?:to|at)\s+(\d+)\b"
)


def extract_section(path: Path, heading: str) -> str:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    in_section = False
    for line in lines:
        if line.startswith("## "):
            if in_section:
                break
            in_section = line.rstrip() == heading
            if in_section:
                out.append(line)
            continue
        if in_section:
            out.append(line)
    return "".join(out)


def module_constant(rel: str, name: str) -> str | None:
    import ast
    tree = ast.parse((SCRIPTS / rel).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name and isinstance(node.value, ast.Constant):
                    return str(node.value.value)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    # 1. Parity region
    seed_sec = extract_section(SEED, "## Index Scope")
    guru_sec = extract_section(GURU, "## Index Scope")
    parity = {
        "seed_bytes": len(seed_sec.encode("utf-8")),
        "guru_bytes": len(guru_sec.encode("utf-8")),
        "seed_sha256": hashlib.sha256(seed_sec.encode("utf-8")).hexdigest()[:16],
        "guru_sha256": hashlib.sha256(guru_sec.encode("utf-8")).hexdigest()[:16],
        "byte_identical": seed_sec == guru_sec,
        "seed_heading_count": (SEED.read_text(encoding="utf-8")).count("\n## Index Scope"),
        "guru_heading_count": (GURU.read_text(encoding="utf-8")).count("\n## Index Scope"),
    }

    # 2. Existing oracle
    lifecycle_tests = (SCRIPTS / "tests/test_server_tools_lifecycle.py").read_text(encoding="utf-8")
    existing_oracle = {
        "class_present": "GuruCitationContractRenderTests" in lifecycle_tests,
        "guards_citation_block": "Citation fields in `code_ask` response:" in lifecycle_tests,
        "module": "tests/test_server_tools_lifecycle.py",
    }

    # 3. CHANGELOG homes
    text = CHANGELOG.read_text(encoding="utf-8")
    headings = [ln for ln in text.splitlines() if ln.startswith("## [")]
    top_heading = headings[0] if headings else None
    # Top-section body via the same boundary rule the checker will use.
    top_start = text.index(top_heading)
    rest = text[top_start + len(top_heading):]
    nxt = rest.find("\n## [")
    top_body = rest if nxt < 0 else rest[:nxt]
    top_claims = [
        {"constant": m.group(1), "claimed": m.group(2),
         "live": module_constant(*CLAIM_PATTERNS[m.group(1)])}
        for m in _CLAIM_RE.finditer(top_body)
    ]
    historical_matches = len(list(_CLAIM_RE.finditer(text))) - len(top_claims)
    import build_pack
    packed_section = build_pack._extract_changelog_section(CHANGELOG, "1.20.0")
    changelog = {
        "top_heading": top_heading,
        "top_is_unreleased": top_heading == "## [Unreleased]",
        "top_claims": top_claims,
        "top_claims_all_match": all(c["claimed"] == c["live"] for c in top_claims),
        "historical_claim_matches_below_top": historical_matches,
        "packed_section_1_20_0_has_claims": bool(_CLAIM_RE.search(packed_section)),
        "packed_section_len": len(packed_section),
    }

    # 4. Guru divergence (registration passages)
    guru_text = GURU.read_text(encoding="utf-8")
    seed_text = SEED.read_text(encoding="utf-8")
    divergence = {
        "guru_setup_wavefoundry_mentions": [
            i + 1 for i, ln in enumerate(guru_text.splitlines())
            if "setup_wavefoundry.py" in ln
        ],
        "seed_setup_wavefoundry_mentions": [
            i + 1 for i, ln in enumerate(seed_text.splitlines())
            if "setup_wavefoundry.py" in ln
        ],
        "seed_wf_setup_registration_lines": [
            i + 1 for i, ln in enumerate(seed_text.splitlines())
            if "wf setup" in ln and ("Enable" in ln or "registration" in ln or "built the index" in ln)
        ],
    }

    results = {
        "census": "1wgwn-enh executed census (parity region, oracle, changelog homes, guru divergence)",
        "parity_region": parity,
        "existing_oracle": existing_oracle,
        "changelog": changelog,
        "guru_divergence": divergence,
    }
    text_out = json.dumps(results, indent=2)
    print(text_out)
    if args.out:
        Path(__file__).with_name(args.out).write_text(text_out + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
