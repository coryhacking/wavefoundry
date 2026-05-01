#!/usr/bin/env python3
"""Check index dependencies and build the Wavefoundry semantic index."""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

SCRIPTS_DIR = Path(__file__).resolve().parent
REQUIRED_IMPORTS = {
    "fastembed": "fastembed",
    "numpy": "numpy",
    "mcp[cli]": "mcp",
}

INDEXING_WORKFLOW_KEY = "indexing"
INCLUDE_FRAMEWORK_CODE_KEY = "include_framework_code_for_code_search"  # compatibility shim
PROJECT_INCLUDE_PREFIXES_KEY = "project_include_prefixes"
DOCS_PREFIXES_KEY = "docs"
CODE_PREFIXES_KEY = "code"


def _installed(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _tool_venv_python() -> Path:
    base = Path(os.environ.get("WAVEFOUNDRY_TOOL_VENV", "~/.cache/wavefoundry/indexer-venv"))
    venv = base.expanduser()
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _dependency_help(missing: list[str]) -> str:
    venv_python = _tool_venv_python()
    venv_dir = venv_python.parent.parent
    quoted_deps = " ".join(f'"{dep}"' if "[" in dep else dep for dep in REQUIRED_IMPORTS)
    return (
        f"Missing dependencies: {', '.join(missing)}\n\n"
        "Install them into an isolated tool environment, then rerun setup_index.py "
        "with that Python:\n\n"
        f"  python3 -m venv {venv_dir}\n"
        f"  {venv_python} -m pip install --upgrade pip\n"
        f"  {venv_python} -m pip install {quoted_deps}\n"
        f"  {venv_python} {SCRIPTS_DIR / 'setup_index.py'} --root . --full\n\n"
        "Set WAVEFOUNDRY_TOOL_VENV to choose a different shared tool venv."
    )


def ensure_deps() -> None:
    missing = [dist for dist, module in REQUIRED_IMPORTS.items() if not _installed(module)]
    if not missing:
        print(f"Dependencies satisfied ({', '.join(REQUIRED_IMPORTS)})", flush=True)
        return
    print(_dependency_help(missing), file=sys.stderr)
    raise SystemExit(2)


def _indexer_models(include_code: bool) -> list[str]:
    indexer_path = SCRIPTS_DIR / "indexer.py"
    spec = importlib.util.spec_from_file_location("wavefoundry_indexer_for_setup", indexer_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    models = [mod.DOCS_MODEL]
    if include_code:
        models.append(mod.CODE_MODEL)
    deduped: list[str] = []
    for model in models:
        if model not in deduped:
            deduped.append(model)
    return deduped


@contextlib.contextmanager
def _offline_env():
    prior = os.environ.get("HF_HUB_OFFLINE")
    os.environ["HF_HUB_OFFLINE"] = "1"
    try:
        yield
    finally:
        if prior is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = prior


def _warm_model(model_name: str, *, local_files_only: bool) -> None:
    from fastembed import TextEmbedding

    embedding = TextEmbedding(model_name=model_name, local_files_only=local_files_only)
    next(iter(embedding.embed(["wavefoundry cache verification"])))


def prewarm_models(*, include_code: bool) -> None:
    models = _indexer_models(include_code)
    for model_name in models:
        print(f"Prewarming semantic model cache: {model_name}", flush=True)
        _warm_model(model_name, local_files_only=False)
        with _offline_env():
            _warm_model(model_name, local_files_only=True)
        print(f"Verified offline semantic model cache: {model_name}", flush=True)


def _run_indexer(
    root: Path,
    full: bool,
    content: str,
    verbose: bool,
    include_tests: bool,
    include_generated: bool,
    project_include_prefixes: tuple[str, ...],
) -> None:
    cmd = [sys.executable, str(SCRIPTS_DIR / "indexer.py"), "--root", str(root), "--content", content]
    if full:
        cmd.append("--full")
    if include_tests:
        cmd.append("--include-tests")
    if include_generated:
        cmd.append("--include-generated")
    for prefix in project_include_prefixes:
        cmd.extend(["--project-include-prefix", prefix])
    if verbose:
        cmd.append("--verbose")
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as exc:
        if exc.returncode < 0:
            signal_number = -exc.returncode
            print(
                f"Index build was killed by signal {signal_number}. "
                "If this happened during code embedding, rerun without --include-code.",
                file=sys.stderr,
            )
        raise


def _merge_project_include_prefixes(
    docs_prefixes: tuple[str, ...],
    code_prefixes: tuple[str, ...],
) -> tuple[str, ...]:
    """Stable union of docs and code workflow prefixes for a single ``indexer.py --content all`` pass."""
    merged: list[str] = []
    for group in (docs_prefixes, code_prefixes):
        for raw in group:
            token = raw.strip().replace("\\", "/").strip("/")
            if token and token not in merged:
                merged.append(token)
    return tuple(merged)


def build_index(
    root: Path,
    full: bool,
    include_code: bool,
    verbose: bool,
    include_tests: bool = False,
    include_generated: bool = False,
    project_include_prefixes_for_docs: tuple[str, ...] = (),
    project_include_prefixes_for_code: tuple[str, ...] = (),
) -> None:
    if include_code:
        print("Building docs and code semantic index (single indexer pass)...", flush=True)
        content = "all"
        prefixes = _merge_project_include_prefixes(
            project_include_prefixes_for_docs,
            project_include_prefixes_for_code,
        )
    else:
        print("Building docs/seed semantic index...", flush=True)
        content = "docs"
        prefixes = project_include_prefixes_for_docs
    _run_indexer(
        root,
        full=full,
        content=content,
        verbose=verbose,
        include_tests=include_tests,
        include_generated=include_generated,
        project_include_prefixes=prefixes,
    )


def _coerce_prefix_list(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        token = item.strip().replace("\\", "/").strip("/")
        if token and token not in out:
            out.append(token)
    return tuple(out)


def _workflow_project_include_prefixes(root: Path) -> dict[str, tuple[str, ...]]:
    cfg = root / "docs" / "workflow-config.json"
    if not cfg.exists():
        return {DOCS_PREFIXES_KEY: (), CODE_PREFIXES_KEY: ()}
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {DOCS_PREFIXES_KEY: (), CODE_PREFIXES_KEY: ()}
    if not isinstance(data, dict):
        return {DOCS_PREFIXES_KEY: (), CODE_PREFIXES_KEY: ()}
    indexing = data.get(INDEXING_WORKFLOW_KEY, {})
    if not isinstance(indexing, dict):
        return {DOCS_PREFIXES_KEY: (), CODE_PREFIXES_KEY: ()}

    configured = indexing.get(PROJECT_INCLUDE_PREFIXES_KEY, {})
    docs_prefixes: tuple[str, ...] = ()
    code_prefixes: tuple[str, ...] = ()
    if isinstance(configured, list):
        prefixes = _coerce_prefix_list(configured)
        docs_prefixes = prefixes
        code_prefixes = prefixes
    elif isinstance(configured, dict):
        docs_prefixes = _coerce_prefix_list(configured.get(DOCS_PREFIXES_KEY))
        code_prefixes = _coerce_prefix_list(configured.get(CODE_PREFIXES_KEY))

    # Backwards compatibility: old boolean opt-in maps to framework scripts code prefix.
    if not code_prefixes and bool(indexing.get(INCLUDE_FRAMEWORK_CODE_KEY, False)):
        code_prefixes = (".wavefoundry/framework/scripts",)
    return {DOCS_PREFIXES_KEY: docs_prefixes, CODE_PREFIXES_KEY: code_prefixes}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Set up the Wavefoundry semantic index")
    p.add_argument("--root", default=None, help="Repository root (default: current directory)")
    p.add_argument("--full", action="store_true", help="Force full rebuild")
    p.add_argument("--include-code", action="store_true", help="Also build semantic code embeddings (slower and more memory-intensive)")
    p.add_argument("--include-tests", action="store_true", help="Include target test files in semantic code indexing")
    p.add_argument("--include-generated", action="store_true", help="Include generated platform hook files in semantic code indexing")
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).expanduser().resolve() if args.root else Path.cwd().resolve()

    print(f"Wavefoundry index setup: root={root}", flush=True)
    ensure_deps()
    include_prefixes = _workflow_project_include_prefixes(root)
    docs_prefixes = include_prefixes.get(DOCS_PREFIXES_KEY, ())
    code_prefixes = include_prefixes.get(CODE_PREFIXES_KEY, ())
    if docs_prefixes or code_prefixes:
        print(
            "Workflow policy: project include-prefixes enabled "
            f"(docs={list(docs_prefixes)}, code={list(code_prefixes)})",
            flush=True,
        )
    prewarm_models(include_code=args.include_code)
    build_index(
        root,
        full=args.full,
        include_code=args.include_code,
        verbose=args.verbose,
        include_tests=args.include_tests,
        include_generated=args.include_generated,
        project_include_prefixes_for_docs=docs_prefixes,
        project_include_prefixes_for_code=code_prefixes,
    )
    print(f"\nDone. MCP server: python3 {SCRIPTS_DIR / 'server.py'} --root {root}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
