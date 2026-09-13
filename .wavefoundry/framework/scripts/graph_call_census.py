"""Read persisted call-edge populations without rebuilding or changing an index.

Usage (the database defaults to ROOT/.wavefoundry/index/index.sqlite)::

    python3 -B graph_call_census.py --root /path/to/repository
    python3 -B graph_call_census.py --root /path/to/repository --database index.sqlite

Counts describe persisted SQL rows, not candidates before extraction deduplication.
Callable/constant identity collisions cannot be recovered from these rows; use
the builder's merge diagnostics for that population. No vector extension or
embedding runtime is loaded.

WAL databases must already have both -wal and -shm sidecars. Otherwise SQLite
may create them even in read-only mode, so this helper refuses before connecting.
Use the current index while its owning application has it open, then retry.
The check does not protect against simultaneous external replacement of files;
SQLite still coordinates readers through existing shared memory in the usual way.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path, PurePath


_LANGUAGES_BY_SUFFIX = {
    ".py": "python", ".pyi": "python",
    ".java": "java", ".php": "php", ".swift": "swift", ".scala": "scala",
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".go": "go", ".rs": "rust", ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp",
    ".cs": "csharp", ".kt": "kotlin", ".kts": "kotlin", ".rb": "ruby",
    ".m": "objc", ".mm": "objc", ".sh": "bash", ".bash": "bash",
}


def _source_language(path: str | None) -> str:
    """File-extension attribution, with unknowns explicit rather than guessed."""
    if not path:
        return "unknown"
    return _LANGUAGES_BY_SUFFIX.get(Path(path).suffix.lower(), "other")


# Exported predicates let tests and consumers reproduce each reported population.
# Calls are grouped by the caller's language; node kinds use the node's own file.
CENSUS_QUERIES = {
    "node_kinds": """
        SELECT source_language(source_file) AS language, kind, COUNT(*) AS count
        FROM graph_nodes GROUP BY language, kind ORDER BY language, kind
    """,
    "calls_by_target_kind_and_confidence": """
        SELECT COALESCE(n.kind, 'missing') AS target_kind, e.confidence, COUNT(*) AS count
        FROM graph_edges e LEFT JOIN graph_nodes n ON n.node_id = e.target_id
        WHERE e.relation = 'calls'
        GROUP BY target_kind, e.confidence ORDER BY target_kind, e.confidence
    """,
    "non_callable_call_targets": """
        SELECT source_language(s.source_file) AS language, n.kind AS target_kind,
               e.confidence, COUNT(*) AS count
        FROM graph_edges e JOIN graph_nodes n ON n.node_id = e.target_id
        LEFT JOIN graph_nodes s ON s.node_id = e.source_id
        WHERE e.relation = 'calls' AND n.kind IN ('variable', 'constant')
        GROUP BY language, target_kind, e.confidence
        ORDER BY language, target_kind, e.confidence
    """,
    "callable_call_targets": """
        SELECT source_language(s.source_file) AS language, n.kind AS target_kind,
               e.confidence, COUNT(*) AS count
        FROM graph_edges e JOIN graph_nodes n ON n.node_id = e.target_id
        LEFT JOIN graph_nodes s ON s.node_id = e.source_id
        WHERE e.relation = 'calls' AND n.kind IN ('function', 'class')
        GROUP BY language, target_kind, e.confidence
        ORDER BY language, target_kind, e.confidence
    """,
    "calls_by_language_and_confidence": """
        SELECT source_language(s.source_file) AS language, e.confidence, COUNT(*) AS count
        FROM graph_edges e LEFT JOIN graph_nodes s ON s.node_id = e.source_id
        WHERE e.relation = 'calls'
        GROUP BY language, e.confidence ORDER BY language, e.confidence
    """,
    "reads_defines": """
        SELECT relation, COUNT(*) AS count FROM graph_edges
        WHERE relation IN ('reads', 'defines') GROUP BY relation ORDER BY relation
    """,
    "external_call_targets": """
        SELECT source_language(s.source_file) AS language, e.confidence,
               COUNT(*) AS count, COUNT(DISTINCT e.target_id) AS distinct_targets
        FROM graph_edges e LEFT JOIN graph_nodes s ON s.node_id = e.source_id
        WHERE e.relation = 'calls' AND e.target_id LIKE 'external::%'
        GROUP BY language, e.confidence ORDER BY language, e.confidence
    """,
    "malformed_external_call_targets": """
        SELECT source_language(s.source_file) AS language, e.target_id, e.confidence,
               COUNT(*) AS count
        FROM graph_edges e LEFT JOIN graph_nodes s ON s.node_id = e.source_id
        WHERE e.relation = 'calls' AND e.target_id LIKE 'external::%'
          AND (substr(e.target_id, -1) = '-' OR instr(e.target_id, '->') > 0
               OR instr(e.target_id, '?.') > 0 OR instr(e.target_id, '!.') > 0
               OR instr(e.target_id, '(') > 0 OR instr(e.target_id, '[') > 0
               OR instr(e.target_id, '<') > 0)
        GROUP BY language, e.target_id, e.confidence
        ORDER BY language, e.target_id, e.confidence
    """,
}


def _read_only_uri(path: PurePath) -> str:
    """Encode an already resolved absolute path, including URI metacharacters."""
    return path.as_uri() + "?mode=ro"


def _validate_wal_sidecars(root: Path, database: Path) -> None:
    """Refuse static WAL layouts that would create sidecars or escape root."""
    with database.open("rb") as stream:
        header = stream.read(20)
    # SQLite's header bytes 18/19 select write/read format (2 means WAL).
    if 2 not in header[18:20]:
        return
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(database) + suffix)
        try:
            resolved = sidecar.resolve(strict=True)
        except FileNotFoundError as error:
            raise ValueError(
                "WAL census requires existing -wal and -shm files; "
                "retry while the owning application has the current index open"
            ) from error
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise ValueError("WAL sidecars must resolve to regular files beneath the supplied root")


def census(root: Path | str, database: Path | str | None = None) -> dict:
    """Count one read-only SQLite snapshot confined to the caller-supplied root.

    Relative database paths are relative to root. Resolution precedes confinement
    and URI encoding, so parent traversal and symlink escapes are both refused.
    Missing databases raise without creating a file or parent directory.
    """
    resolved_root = Path(root).resolve(strict=True)
    if not resolved_root.is_dir():
        raise ValueError("root must be an existing repository directory")
    path = Path(database) if database is not None else Path(".wavefoundry/index/index.sqlite")
    if not path.is_absolute():
        path = resolved_root / path
    path = path.resolve(strict=True)
    if not path.is_relative_to(resolved_root):
        raise ValueError("database must resolve beneath the supplied root")
    if not path.is_file():
        raise ValueError("database must be an existing file")
    _validate_wal_sidecars(resolved_root, path)
    connection = sqlite3.connect(_read_only_uri(path), uri=True)
    try:
        connection.row_factory = sqlite3.Row
        connection.create_function("source_language", 1, _source_language, deterministic=True)
        connection.execute("BEGIN")
        return {
            "database": str(path),
            "counting_basis": "persisted graph_edges rows; language inferred from source-file extension",
            **{name: [dict(row) for row in connection.execute(query)]
               for name, query in CENSUS_QUERIES.items()},
        }
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--database", type=Path, help="absolute path or path relative to --root")
    args = parser.parse_args(argv)
    try:
        result = census(args.root, args.database)
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"graph_call_census: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
