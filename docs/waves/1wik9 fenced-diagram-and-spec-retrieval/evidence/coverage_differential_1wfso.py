"""Per-format content-coverage differential for change 1wfso-enh (wave 1wik9).

AC-6 / Requirement 7 (the ARCH-DEL-1 standing criterion): a DETECTED file must
never lose content coverage relative to its previous chunking path. For each
committed per-format fixture, every nonblank non-structural source line is
classified as covered/uncovered under detection ON (the new chunkers) and
under detection OFF (WAVEFOUNDRY_SPEC_CHUNKING=0, the previous flat/line-window
path). The invariant: no line covered OFF is uncovered ON. Coverage matching
collapses whitespace and trailing commas so JSON re-serialization in unit
bodies compares fairly (token-level classification, allowed by AC-6);
brace/bracket-only lines are structural and excluded by classification.

Non-vacuity (revert-simulation): for every fixture the checker is re-run with
one ON chunk removed (the widest-coverage chunk); the differential MUST detect
lost lines, proving the oracle can see coverage holes.

Run under the tool venv from the repository root:
    ~/.wavefoundry/venv/bin/python "docs/waves/1wik9 fenced-diagram-and-spec-retrieval/evidence/coverage_differential_1wfso.py" [--out <file.json>]

Prints the report; writes ONLY with --out. Exits nonzero on any failure.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / ".wavefoundry" / "framework" / "scripts"
FIXTURES = SCRIPTS / "tests" / "fixtures" / "retrieval_golden" / "specs"
sys.path.insert(0, str(SCRIPTS))

FORMAT_FIXTURES = {
    "asyncapi": ["asyncapi/order-events.yaml", "asyncapi/telemetry-stream.json"],
    "graphql": ["graphql/storefront.graphql", "graphql/admin.gql"],
    "proto": ["proto/user_service.proto", "proto/inventory.proto"],
}

# RT-DEL-1: inline fixtures keep the frozen golden corpus untouched while the
# oracle permanently exercises the repaired classes (a detached license
# header lost all coverage before the residue repair).
INLINE_FIXTURES = [
    ("proto", "inline/detached-license.proto",
     "// Copyright 2026 Example Corp.\n"
     "// Licensed under Apache 2.0.\n\n"
     'syntax = "proto3";\npackage a.b;\n\n'
     "// Attached doc.\nmessage Thing {\n  string x = 1;\n}\n"),
    ("graphql", "inline/extended.graphql",
     '"""\nBase type.\n"""\ntype User {\n  id: ID!\n}\n\n'
     "extend type User {\n  email: String\n}\n"),
]

_STRUCTURAL_RE = re.compile(r'^[\s{}\[\](),;:"\'`|=-]*$')
# A bare mapping-container key opening a block (`channels:`, `"components": {`):
# its NAME survives as a breadcrumb prefix in the curated units, so the line is
# classified structural-if-breadcrumbed rather than lost.
_CONTAINER_KEY_RE = re.compile(r'^"?([\w-]+)"?\s*:\s*\{?$')
_COMMENT_MARKER_RE = re.compile(r"^(//+|#+|\*+|/\*+)\s*")


def _norm(text: str) -> str:
    return " ".join(text.split())


def _content_lines(source: str) -> list[str]:
    out = []
    for raw in source.splitlines():
        s = raw.strip()
        if not s or _STRUCTURAL_RE.match(s):
            continue
        out.append(_norm(s).rstrip(","))
    return out


def _covered(lines: list[str], texts: list[str]) -> set[str]:
    corpus = _norm("\n".join(texts))
    covered = set()
    for ln in lines:
        if ln in corpus:
            covered.add(ln)
            continue
        # Comment lines: units carry the comment TEXT with the marker
        # stripped; classify on the stripped form.
        stripped = _COMMENT_MARKER_RE.sub("", ln).rstrip("*/ ").strip()
        if stripped and stripped in corpus:
            covered.add(ln)
            continue
        # Container-key lines: classified covered when the key survives as a
        # breadcrumb prefix (`channels.` / `channels:`) in the corpus.
        km = _CONTAINER_KEY_RE.match(ln)
        if km and (f"{km.group(1)}." in corpus or f"{km.group(1)}:" in corpus):
            covered.add(ln)
    return covered


def _chunk_texts(source: str, rel: str, enabled: bool) -> list[str]:
    """Fresh chunker import per gate state: the module reads the env at call
    time through _spec_chunking_enabled, so no reload is needed — but keep the
    env set/unset window tight."""
    import chunker
    prev = os.environ.get("WAVEFOUNDRY_SPEC_CHUNKING")
    try:
        if enabled:
            os.environ.pop("WAVEFOUNDRY_SPEC_CHUNKING", None)
        else:
            os.environ["WAVEFOUNDRY_SPEC_CHUNKING"] = "0"
        return [c.text for c in chunker.chunk_file(source, rel)]
    finally:
        if prev is None:
            os.environ.pop("WAVEFOUNDRY_SPEC_CHUNKING", None)
        else:
            os.environ["WAVEFOUNDRY_SPEC_CHUNKING"] = prev


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    import chunker
    report: dict = {
        "differential": "1wfso AC-6 per-format content-coverage differential",
        "chunker_version": chunker.CHUNKER_VERSION,
        "fixtures": [], "failures": [],
    }
    cases = [
        (fmt, rel, (FIXTURES / rel).read_text(encoding="utf-8"))
        for fmt, rels in FORMAT_FIXTURES.items() for rel in rels
    ] + INLINE_FIXTURES
    for fmt, rel, source in cases:
        lines = _content_lines(source)
        on_texts = _chunk_texts(source, rel, enabled=True)
        off_texts = _chunk_texts(source, rel, enabled=False)
        on_cov = _covered(lines, on_texts)
        off_cov = _covered(lines, off_texts)
        lost = sorted(off_cov - on_cov)
        row = {
            "format": fmt, "path": rel, "content_lines": len(lines),
            "covered_on": len(on_cov), "covered_off": len(off_cov),
            "lost_lines": lost,
        }
        if lost:
            report["failures"].append(f"{rel}: coverage LOST for {lost}")
        # Revert-simulation: drop the widest-coverage ON chunk; the
        # differential must detect the hole.
        if on_texts:
            widest = max(range(len(on_texts)),
                         key=lambda k: len(_covered(lines, [on_texts[k]])))
            sim = [t for k, t in enumerate(on_texts) if k != widest]
            sim_lost = on_cov - _covered(lines, sim)
            row["revert_sim_detects"] = bool(sim_lost)
            if not sim_lost:
                report["failures"].append(
                    f"{rel}: revert-simulation failed to detect loss")
        report["fixtures"].append(row)

    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        Path(__file__).with_name(args.out).write_text(text + "\n",
                                                      encoding="utf-8")
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
