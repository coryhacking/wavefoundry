#!/usr/bin/env python3
"""Check index dependencies and build the Wavefoundry semantic index."""
from __future__ import annotations

import argparse
import importlib.util
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


def _run_indexer(
    root: Path,
    full: bool,
    content: str,
    verbose: bool,
    include_tests: bool,
    include_generated: bool,
) -> None:
    cmd = [sys.executable, str(SCRIPTS_DIR / "indexer.py"), "--root", str(root), "--content", content]
    if full:
        cmd.append("--full")
    if include_tests:
        cmd.append("--include-tests")
    if include_generated:
        cmd.append("--include-generated")
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


def build_index(
    root: Path,
    full: bool,
    include_code: bool,
    verbose: bool,
    include_tests: bool = False,
    include_generated: bool = False,
) -> None:
    print("Building docs/seed semantic index...", flush=True)
    _run_indexer(
        root,
        full=full,
        content="docs",
        verbose=verbose,
        include_tests=include_tests,
        include_generated=include_generated,
    )
    if include_code:
        print("Building code semantic index...", flush=True)
        _run_indexer(
            root,
            full=full,
            content="code",
            verbose=verbose,
            include_tests=include_tests,
            include_generated=include_generated,
        )


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
    print("Building semantic index...", flush=True)
    build_index(
        root,
        full=args.full,
        include_code=args.include_code,
        verbose=args.verbose,
        include_tests=args.include_tests,
        include_generated=args.include_generated,
    )
    print(f"\nDone. MCP server: python3 {SCRIPTS_DIR / 'server.py'} --root {root}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
