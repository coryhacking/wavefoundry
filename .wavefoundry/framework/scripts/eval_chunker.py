#!/usr/bin/env python3
"""Chunker evaluation — walks all repo files and reports chunking statistics.

Usage:
    python3 .wavefoundry/framework/scripts/eval_chunker.py [--root .] [--top N] [--slow N]

Outputs:
  - Chunker dispatch summary (which path each file took: tree-sitter / regex / line-window)
  - Chunk counts by language and kind
  - Chunk size distribution (lines, chars)
  - Slowest files
  - Files with zero chunks (potential gaps)
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True

SCRIPTS_DIR = Path(__file__).resolve().parent


def _load(name: str):
    path = SCRIPTS_DIR / f"{name}.py"
    unique = f"_eval_{name}"
    spec = importlib.util.spec_from_file_location(unique, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique] = mod
    spec.loader.exec_module(mod)
    return mod


def _determine_dispatch(chunker, suffix: str) -> str:
    """Map a file extension to the dispatch path name."""
    s = suffix.lower()
    if s in chunker.PYTHON_EXTENSIONS:
        return "python-ast"
    if s in chunker.MARKDOWN_EXTENSIONS:
        return "markdown"
    if s in chunker.JS_TS_EXTENSIONS:
        return "tree-sitter (js/ts)" if chunker._TS_AVAILABLE else "regex (js/ts)"
    if s in chunker.GO_EXTENSIONS:
        return "tree-sitter (go)" if chunker._TS_AVAILABLE else "regex (go)"
    if s in chunker.RUST_EXTENSIONS:
        return "tree-sitter (rust)" if chunker._TS_AVAILABLE else "regex (rust)"
    if s in chunker.JAVA_EXTENSIONS:
        return "tree-sitter (java)" if chunker._TS_AVAILABLE else "regex (java)"
    if s in chunker.CSHARP_EXTENSIONS:
        return "tree-sitter (csharp)" if chunker._TS_AVAILABLE else "regex (csharp)"
    if s in chunker.C_CPP_EXTENSIONS:
        return "tree-sitter (c/cpp)" if chunker._TS_AVAILABLE else "regex (c/cpp)"
    if s in chunker.KOTLIN_EXTENSIONS:
        return "tree-sitter (kotlin)" if chunker._TS_AVAILABLE else "line-window (kotlin)"
    if s in chunker.SHELL_EXTENSIONS:
        if s == ".fish":
            return "regex (shell)"
        return "tree-sitter (bash)" if chunker._TS_AVAILABLE else "regex (bash)"
    if s in getattr(chunker, "SCALA_EXTENSIONS", set()):
        return "tree-sitter (scala)" if chunker._TS_AVAILABLE else "regex (scala)"
    if s in getattr(chunker, "SWIFT_EXTENSIONS", set()):
        return "tree-sitter (swift)" if chunker._TS_AVAILABLE else "regex (swift)"
    if s in getattr(chunker, "OBJC_EXTENSIONS", set()):
        return "tree-sitter (objc)" if chunker._TS_AVAILABLE else "regex (objc)"
    if s in getattr(chunker, "SQL_EXTENSIONS", set()):
        return "tree-sitter (sql)" if chunker._TS_AVAILABLE else "regex (sql)"
    if s in getattr(chunker, "HTML_EXTENSIONS", set()):
        return "tree-sitter (html)" if chunker._TS_AVAILABLE else "regex (html)"
    if s in getattr(chunker, "XML_EXTENSIONS", set()):
        return "tree-sitter (xml)" if chunker._TS_AVAILABLE else "regex (xml)"
    if s in getattr(chunker, "RUBY_EXTENSIONS", set()):
        return "tree-sitter (ruby)" if chunker._TS_AVAILABLE else "line-window"
    if s in getattr(chunker, "PHP_EXTENSIONS", set()):
        return "tree-sitter (php)" if chunker._TS_AVAILABLE else "line-window"
    if s in getattr(chunker, "YAML_EXTENSIONS", set()):
        return "tree-sitter (yaml)" if chunker._TS_AVAILABLE else "line-window"
    if s in getattr(chunker, "TOML_EXTENSIONS", set()):
        return "tree-sitter (toml)" if chunker._TS_AVAILABLE else "line-window"
    if s in getattr(chunker, "JSON_EXTENSIONS", set()):
        return "tree-sitter (json)" if chunker._TS_AVAILABLE else "line-window"
    if s in getattr(chunker, "CSS_EXTENSIONS", set()):
        return "tree-sitter (css)" if chunker._TS_AVAILABLE else "line-window"
    if s in getattr(chunker, "SCSS_EXTENSIONS", set()):
        return "tree-sitter (scss)" if chunker._TS_AVAILABLE else "line-window"
    if s in getattr(chunker, "POWERSHELL_EXTENSIONS", set()):
        return "tree-sitter (powershell)" if chunker._TS_AVAILABLE else "line-window"
    if s in getattr(chunker, "HCL_INDEX_EXTENSIONS", set()):
        return "tree-sitter (hcl)" if chunker._TS_AVAILABLE else "line-window"
    if s in getattr(chunker, "TEXT_EXTENSIONS", set()):
        return "plain-text"
    if s in chunker.CODE_EXTENSIONS:
        return "line-window"
    return "line-window"


def _hbar(value: float, max_value: float, width: int = 30) -> str:
    if max_value == 0:
        return " " * width
    filled = int(round(value / max_value * width))
    return "█" * filled + "░" * (width - filled)


def run(root: Path, top_n: int, slow_n: int) -> None:
    print(f"Loading indexer and chunker from {SCRIPTS_DIR} ...", flush=True)
    indexer = _load("indexer")
    chunker = _load("chunker")

    ts_available = getattr(chunker, "_TS_AVAILABLE", False)
    chunker_version = getattr(chunker, "CHUNKER_VERSION", "?")
    print(f"CHUNKER_VERSION={chunker_version}  tree-sitter={'available' if ts_available else 'NOT INSTALLED'}\n",
          flush=True)

    print("Walking repo ...", flush=True)
    t0 = time.perf_counter()
    files = indexer.walk_repo(root)
    walk_time = time.perf_counter() - t0
    print(f"  {len(files)} files in {walk_time:.2f}s\n", flush=True)

    # Per-file results
    dispatch_counts: dict[str, int] = defaultdict(int)
    lang_counts: dict[str, int] = defaultdict(int)
    kind_counts: dict[str, int] = defaultdict(int)
    chunk_lines: list[int] = []
    chunk_chars: list[int] = []
    zero_chunk_files: list[str] = []
    file_timings: list[tuple[float, str, int]] = []  # (elapsed, rel_path, n_chunks)
    # (chars, lines, rel_path, section, kind, language)
    large_chunks: list[tuple[int, int, str, str, str, str]] = []
    errors: list[tuple[str, str]] = []

    total_chunks = 0
    print(f"Chunking {len(files)} files ...", flush=True)
    t_start = time.perf_counter()

    for path in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            errors.append((rel, str(e)))
            continue

        t1 = time.perf_counter()
        try:
            raw = chunker.chunk_file(source, rel)
        except Exception as e:
            errors.append((rel, f"chunk_file raised: {e}"))
            continue
        elapsed = time.perf_counter() - t1

        chunks = [c.to_dict() for c in raw]
        suffix = path.suffix.lower()
        dispatch = _determine_dispatch(chunker, suffix)

        dispatch_counts[dispatch] += 1
        file_timings.append((elapsed, rel, len(chunks)))

        if not chunks:
            zero_chunk_files.append(rel)
            continue

        total_chunks += len(chunks)
        for c in chunks:
            lang = c.get("language") or "unknown"
            kind = c.get("kind") or "unknown"
            section = c.get("section") or ""
            lang_counts[lang] += 1
            kind_counts[kind] += 1
            lines = c.get("lines") or [0, 0]
            nlines = max(0, lines[1] - lines[0] + 1)
            nchars = len(c.get("text") or "")
            chunk_lines.append(nlines)
            chunk_chars.append(nchars)
            large_chunks.append((nchars, nlines, rel, section, kind, lang))

    total_time = time.perf_counter() - t_start
    print(f"  done in {total_time:.2f}s  ({total_chunks} total chunks)\n", flush=True)

    # -----------------------------------------------------------------------
    # Dispatch summary
    # -----------------------------------------------------------------------
    print("=" * 68)
    print("CHUNKER DISPATCH")
    print("=" * 68)
    total_files = sum(dispatch_counts.values())
    max_dc = max(dispatch_counts.values(), default=1)
    for name, count in sorted(dispatch_counts.items(), key=lambda x: -x[1]):
        pct = count / total_files * 100 if total_files else 0
        bar = _hbar(count, max_dc)
        print(f"  {name:<30} {count:>5}  {pct:5.1f}%  {bar}")
    print()

    # -----------------------------------------------------------------------
    # Chunks by language
    # -----------------------------------------------------------------------
    print("=" * 68)
    print("CHUNKS BY LANGUAGE")
    print("=" * 68)
    max_lc = max(lang_counts.values(), default=1)
    for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1])[:top_n]:
        pct = count / total_chunks * 100 if total_chunks else 0
        bar = _hbar(count, max_lc)
        print(f"  {lang:<20} {count:>6}  {pct:5.1f}%  {bar}")
    if len(lang_counts) > top_n:
        print(f"  ... ({len(lang_counts) - top_n} more languages)")
    print()

    # -----------------------------------------------------------------------
    # Chunks by kind
    # -----------------------------------------------------------------------
    print("=" * 68)
    print("CHUNKS BY KIND")
    print("=" * 68)
    for kind, count in sorted(kind_counts.items(), key=lambda x: -x[1]):
        pct = count / total_chunks * 100 if total_chunks else 0
        print(f"  {kind:<12} {count:>6}  {pct:5.1f}%")
    print()

    # -----------------------------------------------------------------------
    # Chunk size distribution
    # -----------------------------------------------------------------------
    print("=" * 68)
    print("CHUNK SIZE DISTRIBUTION")
    print("=" * 68)
    if chunk_lines:
        sorted_lines = sorted(chunk_lines)
        n = len(sorted_lines)
        def pct_val(p): return sorted_lines[int(p / 100 * n)]
        print(f"  Lines per chunk:   min={min(sorted_lines)}  p25={pct_val(25)}  "
              f"median={pct_val(50)}  p75={pct_val(75)}  p90={pct_val(90)}  "
              f"p99={pct_val(99)}  max={max(sorted_lines)}")
    if chunk_chars:
        sorted_chars = sorted(chunk_chars)
        n = len(sorted_chars)
        def pct_c(p): return sorted_chars[int(p / 100 * n)]
        print(f"  Chars per chunk:   min={min(sorted_chars)}  p25={pct_c(25)}  "
              f"median={pct_c(50)}  p75={pct_c(75)}  p90={pct_c(90)}  "
              f"p99={pct_c(99)}  max={max(sorted_chars)}")
    print()

    # -----------------------------------------------------------------------
    # Largest chunks
    # -----------------------------------------------------------------------
    print("=" * 68)
    print(f"LARGEST {slow_n} CHUNKS BY CHARS")
    print("=" * 68)
    print(f"  {'chars':>7}  {'lines':>5}  {'kind':<6}  {'lang':<12}  {'file / section'}")
    print(f"  {'-'*7}  {'-'*5}  {'-'*6}  {'-'*12}  {'-'*40}")
    for nchars, nlines, rel, section, kind, lang in sorted(large_chunks, key=lambda x: -x[0])[:slow_n]:
        loc = f"{rel}  {section}" if section else rel
        if len(loc) > 60:
            loc = "..." + loc[-57:]
        print(f"  {nchars:>7,}  {nlines:>5}  {kind:<6}  {lang:<12}  {loc}")
    print()

    # -----------------------------------------------------------------------
    # Slowest files
    # -----------------------------------------------------------------------
    print("=" * 68)
    print(f"SLOWEST {slow_n} FILES")
    print("=" * 68)
    for elapsed, rel, n in sorted(file_timings, key=lambda x: -x[0])[:slow_n]:
        print(f"  {elapsed*1000:7.1f}ms  {n:>5} chunks  {rel}")
    print()

    # -----------------------------------------------------------------------
    # Zero-chunk files
    # -----------------------------------------------------------------------
    if zero_chunk_files:
        print("=" * 68)
        print(f"ZERO-CHUNK FILES ({len(zero_chunk_files)})")
        print("=" * 68)
        for rel in zero_chunk_files[:top_n]:
            print(f"  {rel}")
        if len(zero_chunk_files) > top_n:
            print(f"  ... ({len(zero_chunk_files) - top_n} more)")
        print()

    # -----------------------------------------------------------------------
    # Errors
    # -----------------------------------------------------------------------
    if errors:
        print("=" * 68)
        print(f"ERRORS ({len(errors)})")
        print("=" * 68)
        for rel, msg in errors[:top_n]:
            print(f"  {rel}: {msg}")
        print()

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("=" * 68)
    print("SUMMARY")
    print("=" * 68)
    print(f"  Files walked:       {len(files)}")
    print(f"  Files chunked:      {total_files}")
    print(f"  Zero-chunk files:   {len(zero_chunk_files)}")
    print(f"  Errors:             {len(errors)}")
    print(f"  Total chunks:       {total_chunks}")
    print(f"  Walk time:          {walk_time:.2f}s")
    print(f"  Chunk time:         {total_time:.2f}s")
    if total_files:
        print(f"  Avg per file:       {total_time/total_files*1000:.1f}ms")
    if total_chunks:
        print(f"  Avg chunks/file:    {total_chunks/total_files:.1f}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Evaluate Wavefoundry chunker across the repo")
    p.add_argument("--root", default=None, help="Repository root (default: cwd)")
    p.add_argument("--top", type=int, default=20, metavar="N",
                   help="Max rows to show in language/zero-chunk tables (default: 20)")
    p.add_argument("--slow", type=int, default=15, metavar="N",
                   help="Number of slowest files to show (default: 15)")
    args = p.parse_args(argv)
    root = Path(args.root).expanduser().resolve() if args.root else Path.cwd().resolve()
    run(root, top_n=args.top, slow_n=args.slow)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
