"""Canonical setup dependencies and CLI grammar; safe before tool-environment activation."""

import argparse
from pathlib import Path

# Qualified shared semantic runtime; migration owns the retired Lance reader.
APSW_REQUIREMENT = "apsw==3.53.4.0"
SQLITE_VEC_REQUIREMENT = "sqlite-vec==0.1.9"
REQUIRED_IMPORTS = {
    "fastembed": "fastembed",
    "httpx[socks]": "socksio",
    "igraph>=0.11": "igraph",
    "leidenalg>=0.10": "leidenalg",
    "numpy": "numpy",
    "mcp[cli]": "mcp",
    # Tree-sitter grammars for AST-accurate code chunking. chunker.py falls back to regex /
    # line-window chunkers when a grammar is absent.
    "tree-sitter>=0.24,<0.26": "tree_sitter",
    "tree-sitter-typescript": "tree_sitter_typescript",
    "tree-sitter-javascript": "tree_sitter_javascript",
    "tree-sitter-go": "tree_sitter_go",
    "tree-sitter-rust": "tree_sitter_rust",
    "tree-sitter-java": "tree_sitter_java",
    "tree-sitter-c": "tree_sitter_c",
    "tree-sitter-cpp": "tree_sitter_cpp",
    "tree-sitter-c-sharp": "tree_sitter_c_sharp",
    "tree-sitter-bash": "tree_sitter_bash",
    "tree-sitter-kotlin": "tree_sitter_kotlin",
    "tree-sitter-sql": "tree_sitter_sql",
    "tree-sitter-swift": "tree_sitter_swift",
    "tree-sitter-objc": "tree_sitter_objc",
    "tree-sitter-hcl": "tree_sitter_hcl",
    "tree-sitter-scss": "tree_sitter_scss",
    "tree-sitter-make": "tree_sitter_make",
    "tree-sitter-scala": "tree_sitter_scala",
    "tree-sitter-html": "tree_sitter_html",
    "tree-sitter-xml": "tree_sitter_xml",
    "tree-sitter-ruby": "tree_sitter_ruby",
    "tree-sitter-php": "tree_sitter_php",
    "tree-sitter-yaml": "tree_sitter_yaml",
    "tree-sitter-toml": "tree_sitter_toml",
    "tree-sitter-json": "tree_sitter_json",
    "tree-sitter-css": "tree_sitter_css",
    "tree-sitter-powershell": "tree_sitter_powershell",
    APSW_REQUIREMENT: "apsw",
    SQLITE_VEC_REQUIREMENT: "sqlite_vec",
    "networkx>=3.0": "networkx",
}
CUDA_DEPENDENCY_IMPORTS = {
    "fastembed-gpu": "fastembed",
}
# Wave 1p517/1p52p: `onnx` pins model input dims to a static shape. GPU embedders need it for the
# FP16 acceleration path; the CPU INT8 reranker also needs it to build its static 40x512 graph.
GPU_ACCEL_IMPORTS = {
    "onnx": "onnx",
}



def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Set up the Wavefoundry semantic index", allow_abbrev=False)
    p.add_argument("--root", default=None, help="Repository root (default: current directory)")
    p.add_argument("--model-bundle", type=Path, help="Validate and materialize an offline model-set asset before setup")
    p.add_argument("--model-bundle-model-set-version", help="Expected independently versioned model set")
    p.add_argument("--full", action="store_true", help="Force full rebuild")
    p.add_argument("--prewarm-only", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--rechunk", action="store_true", help="Re-chunk every file but reuse embeddings by content hash (no version change; only new/changed chunks re-embed)")
    p.add_argument("--include-code", action="store_true", help="Build semantic code embeddings synchronously (default; kept for explicit CI/full-build callers)")
    p.add_argument("--background-code", action="store_true", help="Build docs index synchronously (unblocks MCP immediately), then spawn a detached background process for code embedding")
    p.add_argument("--background-docs", action="store_true", help="Build code index synchronously, then spawn a detached background process for docs embedding")
    p.add_argument("--docs-only", action="store_true", help="Build only docs/seed semantic embeddings in the foreground")
    p.add_argument("--code-only", action="store_true", help="Build only semantic code embeddings in the foreground")
    p.add_argument("--graph-only", action="store_true", help="Rebuild only the graph index without re-embedding semantic vectors")
    p.add_argument("--include-tests", action="store_true", help="Include target test files in semantic code indexing")
    p.add_argument("--include-generated", action="store_true", help="Include generated platform hook files in semantic code indexing")
    p.add_argument(
        "--deps-only",
        action="store_true",
        help="Provision the tool environment without warming models or publishing indexes.",
    )
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args(argv)

