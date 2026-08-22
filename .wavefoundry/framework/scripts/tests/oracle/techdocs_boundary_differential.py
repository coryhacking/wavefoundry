#!/usr/bin/env python3
"""Pinned external oracle for the TechDocs exclusion boundary.

This harness is deliberately outside the ordinary ``tests/test_*.py`` runner.
It requires MkDocs 1.6.1 and pathspec 1.1.1 in a disposable environment and
never makes either package a framework runtime or unit-suite dependency.

Exact invocation from the repository root::

    python3 -m venv /tmp/1vry5-oracle-env
    /tmp/1vry5-oracle-env/bin/pip install "mkdocs==1.6.1" "pathspec==1.1.1"
    /tmp/1vry5-oracle-env/bin/python -B \
      .wavefoundry/framework/scripts/tests/oracle/techdocs_boundary_differential.py \
      --baseline-module /tmp/1vry5-baseline/techdocs_audit_lib.py \
      --cost-output "docs/waves/1vry5 techdocs-pattern-fidelity/techdocs-pattern-cost-results.json"

The fixture contains exactly these 19 Markdown pages:

``index.md``, ``ARCHITECTURE.md``, ``a.md``, ``b.md``, ``z.md``,
``.hidden.md``, ``draft.tmp.md``, ``agents/guru.md``,
``architecture/index.md``, ``architecture/runtime.md``, ``deep/a/b/c.md``,
``prompts/index.md``, ``prompts/plan.md``, ``references/project-overview.md``,
``references/public.md``, ``references/deep/guide.md``,
``references/deep/index.md``, ``templates/index.md``, and
``templates/card.md``.

The publication-boundary pass compares 1,200 translator-supported,
oracle-loadable blocks for each seed 20260819 through 20260824. A separate
seed-20260819 collapse differential generates exactly 6,000 single-pattern
blocks from the declared ``COLLAPSE_ATOMS`` alphabet, compares at least 15,000
before/after block-and-subject answers, and requires at least 400 changed regex
emissions. The cost pass implements AC-5's closed six-pattern by two-subject by
three-depth protocol against the byte-copied baseline and delivered module,
and writes all three results to the retained JSON artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[2]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import techdocs_audit_lib as delivered  # noqa: E402

SEEDS = tuple(range(20260819, 20260825))
BLOCKS_PER_SEED = 1200
PATTERN_POOL = (
    "/*", "!/index.md", "!/ARCHITECTURE.md", "!/architecture/",
    "!/architecture/**", "!/references/", "!/references/**", "!/prompts/",
    "/prompts/*", "!/prompts/index.md", "*.tmp.md", "**/*.md",
    "!**/index.md", "/references/**", "!/references/public.md", "templates/",
    "!templates/index.md", "[a-c]*.md", "?.md", "**/deep/*.md",
    "**/**/index.md", "architecture/*.md", "!architecture/runtime.md",
    "deep/**/c.md", "[!z]*.md", "a?*.md",
)
ORACLE_REFUSED = (
    r"/a\/b", r"a\/b", r"!a\/b", r"a\/b/", r"pre\/post.md",
    r"\/a", r"**/a\/b", r"a/\/b", r"a\\\/b",
)
ORACLE_ACCEPTED = (r"a\\/b", r"\\/x.md", r"a\\/b/c", r"x/\\/y")
COST_PATTERNS = (
    "**/**/*aX", "**/a/**/*aX", "**/**/a/**/*aX",
    "**/a/**/b/**/*aX", "*/*/*/*.md", "/*?*?*?*?*?*?x.md",
)
COST_DEPTHS = (201, 401, 801)
SUBJECT_BUILDERS = {
    "deep_aY": lambda depth: "a/" * (depth - 1) + "aY",
    "deep_markdown": lambda depth: "a/" * (depth - 1) + "z.md",
}
COLLAPSE_SEED = 20260819
COLLAPSE_PATTERN_COUNT = 6000
COLLAPSE_CHANGED_FLOOR = 400
COLLAPSE_SUBJECTS = ("a.md", "deep/a/b/c.md", "templates/index.md")
COLLAPSE_ATOMS = (
    "alpha", "beta", "/", "**/", "**/**/", "*", "?", "[a-c]", "[!z]",
    "\\", r"\*", r"\?", r"\\",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _write_page(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {title}\n", encoding="utf-8")


def _build_fixture(root: Path) -> tuple[Path, Path]:
    docs = root / "docs"
    pages = (
        "index.md", "ARCHITECTURE.md", "a.md", "b.md", "z.md", ".hidden.md",
        "draft.tmp.md", "agents/guru.md", "architecture/index.md",
        "architecture/runtime.md", "deep/a/b/c.md", "prompts/index.md",
        "prompts/plan.md", "references/project-overview.md",
        "references/public.md", "references/deep/guide.md",
        "references/deep/index.md", "templates/index.md", "templates/card.md",
    )
    for page in pages:
        _write_page(docs / page, page)
    config_path = root / "mkdocs.yml"
    config_path.write_text(
        "site_name: Oracle\n"
        f"docs_dir: {docs.as_posix()}\n"
        f"site_dir: {(root / 'site').as_posix()}\n",
        encoding="utf-8",
    )
    return docs, config_path


def _generated_blocks(seed: int, count: int):
    rng = random.Random(seed)
    seen: set[tuple[str, ...]] = set()
    while len(seen) < count:
        block = tuple(rng.choice(PATTERN_POOL) for _ in range(rng.randint(1, 6)))
        if block in seen or delivered.unsupported_patterns(list(block)):
            continue
        seen.add(block)
        yield list(block)


def _mkdocs_survivors(config, block: list[str]) -> set[str]:
    from mkdocs.structure.files import get_files
    from pathspec.gitignore import GitIgnoreSpec

    config["exclude_docs"] = GitIgnoreSpec.from_lines(block)
    return {
        file.src_uri for file in get_files(config)
        if file.src_uri.endswith(".md") and file.inclusion.is_included()
    }


def _oracle_accepts(pattern: str, docs: Path) -> dict[str, bool]:
    from mkdocs.config import load_config
    from pathspec.gitignore import GitIgnoreSpec

    try:
        GitIgnoreSpec.from_lines([pattern])
        pathspec_ok = True
    except Exception:
        pathspec_ok = False
    config_text = (
        "site_name: Oracle\n"
        f"docs_dir: {docs.as_posix()}\n"
        "exclude_docs: |\n"
        f"  {pattern}\n"
    )
    try:
        load_config(config_file=io.StringIO(config_text))
        mkdocs_ok = True
    except Exception:
        mkdocs_ok = False
    return {"pathspec": pathspec_ok, "mkdocs": mkdocs_ok}


def run_boundary(blocks_per_seed: int) -> dict:
    import mkdocs
    import pathspec
    from mkdocs.config import load_config

    failures: list[dict] = []
    compared = 0
    with tempfile.TemporaryDirectory(prefix="techdocs-oracle-") as tmp:
        root = Path(tmp)
        docs, config_path = _build_fixture(root)
        config = load_config(str(config_path))
        for seed in SEEDS:
            for block_index, block in enumerate(_generated_blocks(seed, blocks_per_seed)):
                expected = _mkdocs_survivors(config, block)
                observed = set(delivered.survivor_pages(root, docs, block))
                compared += 1
                if expected != observed:
                    failures.append({
                        "seed": seed, "block_index": block_index, "patterns": block,
                        "fail_open": sorted(observed - expected),
                        "fail_closed": sorted(expected - observed),
                    })
        escaped = []
        for pattern in ORACLE_REFUSED + ORACLE_ACCEPTED:
            verdict = _oracle_accepts(pattern, docs)
            derived_expected = (
                "ok" if verdict["pathspec"] and verdict["mkdocs"] else "refused"
            )
            verdict.update({
                "pattern": pattern,
                "declared_partition": (
                    "refused" if pattern in ORACLE_REFUSED else "ok"
                ),
                "expected": derived_expected,
                "translator": delivered._translate_pattern(pattern)[0],
            })
            escaped.append(verdict)
    return {
        "mkdocs_version": mkdocs.__version__, "pathspec_version": pathspec.__version__,
        "seeds": list(SEEDS), "blocks_per_seed": blocks_per_seed,
        "blocks_compared": compared,
        "fail_open": sum(len(item["fail_open"]) for item in failures),
        "fail_closed": sum(len(item["fail_closed"]) for item in failures),
        "failures": failures[:20], "escaped_slash_oracle": escaped,
    }


def _collapse_patterns() -> list[tuple[str, str]]:
    """Return AC-2's deterministic 6,000-pattern before/after corpus."""
    patterns = [("oracle_control", pattern)
                for pattern in ORACLE_REFUSED + ORACLE_ACCEPTED]
    for index in range(32):
        prefix = ("", "/", "!")[index % 3]
        patterns.append(("directed", f"{prefix}**/**/collapse-{index}.md"))

    rng = random.Random(COLLAPSE_SEED)
    while len(patterns) < COLLAPSE_PATTERN_COUNT:
        atom_count = rng.randint(1, 6)
        atoms = []
        for _ in range(atom_count):
            atom = rng.choice(COLLAPSE_ATOMS)
            # The single-backslash alphabet member exercises the escape branch,
            # but the random neutrality partition must not invent additional
            # oracle-unloadable `\/` cases outside the explicit oracle table.
            if atom == "/":
                rendered_so_far = "".join(atoms)
                trailing_backslashes = (
                    len(rendered_so_far) - len(rendered_so_far.rstrip("\\"))
                )
                if trailing_backslashes % 2:
                    atom = "alpha"
            atoms.append(atom)
        body = "".join(atoms)
        prefix = "!" if len(patterns) % 11 == 0 else ""
        patterns.append(("random", f"{prefix}{body}case-{len(patterns)}.md"))
    if len({pattern for _, pattern in patterns}) != COLLAPSE_PATTERN_COUNT:
        raise RuntimeError("collapse differential generator produced duplicates")
    return patterns


def _escaped_row_agrees(row: dict) -> bool:
    """Return whether a stored escaped-slash row follows the live oracles."""
    derived = "ok" if row["pathspec"] and row["mkdocs"] else "refused"
    return (
        row["pathspec"] == row["mkdocs"]
        and row["expected"] == derived
        and row["declared_partition"] == derived
        and row["translator"] == derived
    )


def run_collapse_differential(baseline_path: Path) -> dict:
    """Compare baseline and delivered behavior over AC-2's closed corpus."""
    before = _load_module(baseline_path, "techdocs_collapse_baseline")
    patterns = _collapse_patterns()
    intentional = set(ORACLE_REFUSED)
    failures: list[dict] = []
    changed_emissions = 0
    random_changed_emissions = 0
    answer_comparisons = 0
    intentional_deltas = []

    for partition, pattern in patterns:
        before_translation = before._translate_pattern(pattern)
        after_translation = delivered._translate_pattern(pattern)
        before_unsupported = before.unsupported_patterns([pattern])
        after_unsupported = delivered.unsupported_patterns([pattern])

        if pattern in intentional:
            observed = {
                "pattern": pattern,
                "before": before_translation[0],
                "after": after_translation[0],
                "before_unsupported": before_unsupported,
                "after_unsupported": after_unsupported,
            }
            intentional_deltas.append(observed)
            if not (
                before_translation[0] == before._PATTERN_OK
                and after_translation[0] == delivered._PATTERN_REFUSED
                and before_unsupported == []
                and after_unsupported == [pattern]
            ):
                failures.append({"kind": "intentional_delta", **observed})
            continue

        if (before_translation[0] != after_translation[0]
                or before_unsupported != after_unsupported):
            failures.append({
                "kind": "classification", "pattern": pattern,
                "before": before_translation[0], "after": after_translation[0],
                "before_unsupported": before_unsupported,
                "after_unsupported": after_unsupported,
            })
            continue

        before_regex = before_translation[3]
        after_regex = after_translation[3]
        if (before_regex is not None and after_regex is not None
                and before_regex.pattern != after_regex.pattern):
            changed_emissions += 1
            if partition == "random":
                random_changed_emissions += 1
        for subject in COLLAPSE_SUBJECTS:
            before_answer = before.excluded(subject, [pattern])
            after_answer = delivered.excluded(subject, [pattern])
            answer_comparisons += 1
            if before_answer != after_answer:
                failures.append({
                    "kind": "answer", "pattern": pattern, "subject": subject,
                    "before": before_answer, "after": after_answer,
                })

    return {
        "seed": COLLAPSE_SEED,
        "pattern_count": len(patterns),
        "alphabet": list(COLLAPSE_ATOMS),
        "subjects": list(COLLAPSE_SUBJECTS),
        "answer_comparisons": answer_comparisons,
        "changed_regex_emissions": changed_emissions,
        "random_changed_regex_emissions": random_changed_emissions,
        "random_pattern_count": sum(1 for partition, _ in patterns
                                    if partition == "random"),
        "directed_pattern_count": sum(1 for partition, _ in patterns
                                      if partition == "directed"),
        "changed_regex_floor": COLLAPSE_CHANGED_FLOOR,
        "intentional_classification_deltas": intentional_deltas,
        "failure_count": len(failures),
        "failures": failures[:20],
    }


def _measure_one(module_path: Path, pattern: str, subject: str) -> dict:
    module = _load_module(module_path, "techdocs_cost_subject")
    status = module._translate_pattern(pattern)[0]
    if status != module._PATTERN_OK:
        return {"classification": status, "elapsed_seconds": None, "excluded": False}
    started = time.monotonic()
    answer = module.excluded(subject, [pattern])
    return {"classification": status, "elapsed_seconds": time.monotonic() - started,
            "excluded": answer}


def _isolated_measure(module_path: Path, pattern: str, subject: str) -> dict:
    command = [
        sys.executable, "-B", str(Path(__file__).resolve()), "--measure-one",
        "--module", str(module_path), "--pattern", pattern, "--subject", subject,
    ]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(command, check=True, capture_output=True, text=True, env=env)
    return json.loads(completed.stdout)


def run_cost(baseline_path: Path, delivered_path: Path) -> dict:
    modules = {"before": baseline_path, "after": delivered_path}
    rows = []
    for module_label, module_path in modules.items():
        for pattern in COST_PATTERNS:
            for subject_label, builder in SUBJECT_BUILDERS.items():
                for depth in COST_DEPTHS:
                    subject = builder(depth)
                    _isolated_measure(module_path, pattern, subject)
                    samples = [_isolated_measure(module_path, pattern, subject) for _ in range(3)]
                    classifications = {sample["classification"] for sample in samples}
                    if len(classifications) != 1:
                        raise RuntimeError("classification changed across isolated samples")
                    timings = [sample["elapsed_seconds"] for sample in samples
                               if sample["elapsed_seconds"] is not None]
                    rows.append({
                        "module": module_label, "pattern": pattern,
                        "subject_shape": subject_label, "depth": depth,
                        "classification": samples[0]["classification"],
                        "answers": [sample["excluded"] for sample in samples],
                        "timings_seconds": timings,
                        "median_seconds": statistics.median(timings) if timings else None,
                    })
    maxima = {}
    for label in modules:
        admitted = [row for row in rows
                    if row["module"] == label and row["classification"] == "ok"]
        maxima[label] = max(admitted, key=lambda row: row["median_seconds"])
    return {
        "schema_version": 1,
        "claim_scope": "slowest observed in the named AC-5 corpus; not a universal ceiling",
        "python_version": platform.python_version(), "platform": platform.platform(),
        "modules": {label: {"path": str(path), "sha256": _sha256(path)}
                    for label, path in modules.items()},
        "patterns": list(COST_PATTERNS), "subject_shapes": list(SUBJECT_BUILDERS),
        "depths": list(COST_DEPTHS), "warmups_per_row": 1,
        "timed_runs_per_row": 3, "statistic": "median wall-clock seconds",
        "rows": rows, "slowest_observed_admitted": maxima,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-module", type=Path)
    parser.add_argument("--cost-output", type=Path)
    parser.add_argument("--blocks-per-seed", type=int, default=BLOCKS_PER_SEED)
    parser.add_argument("--measure-one", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--module", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--pattern", help=argparse.SUPPRESS)
    parser.add_argument("--subject", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.measure_one:
        if args.module is None or args.pattern is None or args.subject is None:
            parser.error("--measure-one requires --module, --pattern and --subject")
        print(json.dumps(_measure_one(args.module, args.pattern, args.subject)))
        return 0
    if args.baseline_module is None or args.cost_output is None:
        parser.error("--baseline-module and --cost-output are required")
    if args.blocks_per_seed <= 0:
        parser.error("--blocks-per-seed must be positive")
    boundary = run_boundary(args.blocks_per_seed)
    collapse = run_collapse_differential(args.baseline_module.resolve())
    cost = run_cost(args.baseline_module.resolve(),
                    (SCRIPTS_ROOT / "techdocs_audit_lib.py").resolve())
    cost["publication_boundary"] = boundary
    cost["collapse_differential"] = collapse
    args.cost_output.parent.mkdir(parents=True, exist_ok=True)
    args.cost_output.write_text(json.dumps(cost, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"boundary": boundary, "cost_output": str(args.cost_output),
                      "slowest_observed_admitted": cost["slowest_observed_admitted"]},
                     indent=2, sort_keys=True))
    escaped_known_bad = {
        "pathspec": False, "mkdocs": False, "expected": "ok",
        "declared_partition": "ok", "translator": "ok",
    }
    if _escaped_row_agrees(escaped_known_bad):
        raise RuntimeError("escaped-slash oracle predicate accepted a stale expected label")
    escaped_ok = all(_escaped_row_agrees(row)
                     for row in boundary["escaped_slash_oracle"])
    collapse_ok = (
        not collapse["failures"]
        and collapse["pattern_count"] == COLLAPSE_PATTERN_COUNT
        and collapse["answer_comparisons"] >= 15000
        and collapse["random_changed_regex_emissions"] >= COLLAPSE_CHANGED_FLOOR
    )
    return 0 if not boundary["failures"] and escaped_ok and collapse_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
